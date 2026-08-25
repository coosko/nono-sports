"""Manual activity imports and normalization."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import manual_path
from nono_sports.domain.activity import NormalizedActivity
from nono_sports.domain.source import SourceReference
from nono_sports.domain.stream import NormalizedStream
from nono_sports.formats.track_xml import TrackPoint, parse_gpx_track_points
from nono_sports.storage.incremental import (
    build_file_fingerprint,
    is_incremental_state_current,
    state_counts,
)
from nono_sports.storage.manifest import RawManifestEntry
from nono_sports.storage.raw_store import MANIFEST_FILENAME, RawWriteResult
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SOURCE = "manual"
SCHEMA_VERSION_ACTIVITY = "nono.normalized_activity.v1"
SCHEMA_VERSION_STREAM = "nono.normalized_stream.v1"
REQUIRED_OUTPUTS = (
    "activities.jsonl",
    "streams.jsonl",
    "streams_index.jsonl",
    "state.json",
)

SPORT_MAP = {
    "bike": ("cycling", "cycling", "endurance_distance"),
    "cycling": ("cycling", "cycling", "endurance_distance"),
    "gravel_cycling": ("cycling", "gravel_cycling", "endurance_distance"),
    "hike": ("walking_hiking", "hiking", "endurance_distance"),
    "hiking": ("walking_hiking", "hiking", "endurance_distance"),
    "mountain_biking": ("cycling", "mountain_biking", "endurance_distance"),
    "ride": ("cycling", "road_cycling", "endurance_distance"),
    "road_cycling": ("cycling", "road_cycling", "endurance_distance"),
    "run": ("running", "road_running", "endurance_distance"),
    "running": ("running", "road_running", "endurance_distance"),
    "trail_running": ("running", "trail_running", "endurance_distance"),
    "walk": ("walking_hiking", "walking", "endurance_distance"),
    "walking": ("walking_hiking", "walking", "endurance_distance"),
    "workout": ("fitness", "general_workout", "strength_skill_or_mixed"),
}


@dataclass(frozen=True)
class ManualGpxImportResult:
    activity_id: str
    raw_path: str
    written: RawWriteResult


@dataclass(frozen=True)
class ManualActivityNormalizationResult:
    activities: int
    streams: int
    streams_index: int
    written: tuple[SourceNormalizedWriteResult, ...]
    normalized_root: str
    skipped: bool = False


def import_manual_gpx_activity(
    data_root: Path,
    source_path: Path,
    *,
    sport: str,
    source_platform: str = "manual",
    title: str | None = None,
    generated_at: datetime | None = None,
) -> ManualGpxImportResult:
    """Copy a GPX file into the manual raw area and register its metadata."""

    generated_at = generated_at or datetime.now(UTC)
    source_path = source_path.expanduser()
    if not source_path.is_file():
        raise FileNotFoundError(f"GPX file not found: {source_path}")
    if source_path.suffix.lower() != ".gpx":
        raise ValueError("manual import-gpx only accepts .gpx files")

    platform_slug = _slug(source_platform)
    raw_root = manual_path(data_root, "raw")
    temporary_path = raw_root / "activities" / f".{source_path.stem}.tmp"
    temporary_path.parent.mkdir(parents=True, exist_ok=True)
    digest, bytes_written = _copy_with_sha256(source_path, temporary_path)
    activity_id = f"{platform_slug}_{digest[:16]}"
    relative_path = Path("activities") / f"{activity_id}.gpx"
    destination = raw_root / relative_path
    temporary_path.replace(destination)

    result = RawWriteResult(
        path=destination,
        relative_path=relative_path.as_posix(),
        sha256=digest,
        bytes_written=bytes_written,
    )
    _append_manifest(
        raw_root,
        RawManifestEntry(
            generated_at=generated_at.astimezone(UTC).isoformat(),
            kind="manual_import",
            endpoint="manual.import_gpx",
            params={
                "activity_id": activity_id,
                "source_filename": source_path.name,
                "source_path": str(source_path),
                "source_platform": source_platform,
                "sport": sport,
                "title": title,
            },
            path=relative_path.as_posix(),
            sha256=digest,
            bytes_written=bytes_written,
        ),
    )
    return ManualGpxImportResult(
        activity_id=activity_id,
        raw_path=relative_path.as_posix(),
        written=result,
    )


def normalize_manual_activities(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> ManualActivityNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    raw_root = manual_path(data_root, "raw")
    normalized_root = manual_path(data_root, "normalizado")
    manifest_index = _read_manifest_index(raw_root / MANIFEST_FILENAME)
    store = SourceNormalizedStore(normalized_root)
    previous_state = _read_json(normalized_root / "state.json")
    input_fingerprint = _manual_activities_fingerprint(data_root)
    if is_incremental_state_current(
        previous_state,
        input_fingerprint,
        output_root=normalized_root,
        required_outputs=REQUIRED_OUTPUTS,
    ):
        counts = state_counts(previous_state)
        return ManualActivityNormalizationResult(
            activities=int(counts.get("activities") or 0),
            streams=int(counts.get("streams") or 0),
            streams_index=int(counts.get("streams_index") or 0),
            written=(),
            normalized_root=str(normalized_root),
            skipped=True,
        )

    with (
        store.open_jsonl("activities.jsonl") as activities_writer,
        store.open_jsonl("streams.jsonl") as streams_writer,
        store.open_jsonl("streams_index.jsonl") as streams_index_writer,
    ):
        activities = 0
        streams = 0
        for gpx_path in sorted((raw_root / "activities").glob("*.gpx")):
            activity, stream = _normalize_gpx_file(raw_root, gpx_path, manifest_index)
            if activity is None:
                continue
            activities_writer.write_record(activity)
            activities += 1
            if stream is not None:
                streams_writer.write_record(stream)
                streams_index_writer.write_record(_stream_index(stream))
                streams += 1

        activity_result = activities_writer.finish()
        streams_result = streams_writer.finish()
        streams_index_result = streams_index_writer.finish()

    state = {
        "schema_version": "nono.manual.activities_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "inputs": {
            "raw_root": str(raw_root),
            "manifest": str(raw_root / MANIFEST_FILENAME),
            "input_fingerprint": input_fingerprint,
        },
        "outputs": {
            "activities": "activities.jsonl",
            "streams": "streams.jsonl",
            "streams_index": "streams_index.jsonl",
            "state": "state.json",
        },
        "counts": {
            "activities": activity_result.records_written,
            "streams": streams_result.records_written,
            "streams_index": streams_index_result.records_written,
        },
    }
    written = (
        activity_result,
        streams_result,
        streams_index_result,
        store.write_json("state.json", state),
    )
    return ManualActivityNormalizationResult(
        activities=activity_result.records_written,
        streams=streams_result.records_written,
        streams_index=streams_index_result.records_written,
        written=written,
        normalized_root=str(normalized_root),
    )


def _manual_activities_fingerprint(data_root: Path) -> dict[str, Any]:
    raw_root = manual_path(data_root, "raw")
    return build_file_fingerprint(
        raw_root,
        ("activities/*.gpx", MANIFEST_FILENAME),
        manifest_path=raw_root / MANIFEST_FILENAME,
    )


def _normalize_gpx_file(
    raw_root: Path,
    gpx_path: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> tuple[NormalizedActivity | None, NormalizedStream | None]:
    relative_path = gpx_path.relative_to(raw_root).as_posix()
    manifest = manifest_index.get(relative_path, {})
    params = manifest.get("params") if isinstance(manifest.get("params"), dict) else {}
    activity_id = str(params.get("activity_id") or gpx_path.stem)
    sport = str(params.get("sport") or "unknown")
    source_platform = str(params.get("source_platform") or "manual")
    source_filename = str(params.get("source_filename") or gpx_path.name)
    title = _optional_str(params.get("title")) or Path(source_filename).stem

    points = _with_cumulative_distance(parse_gpx_track_points(gpx_path))
    if not points:
        return None, None

    stats = _track_stats(points)
    reference = _source_reference(
        raw_root,
        gpx_path,
        manifest_index,
        entity_type="gpx",
        source_id=activity_id,
    )
    activity_uid = f"{SOURCE}:activity:{activity_id}"
    stream_uid = f"{SOURCE}:stream:{activity_id}"
    stream = _normalized_stream(
        activity_id,
        activity_uid,
        stream_uid,
        points,
        reference,
    )
    activity = NormalizedActivity(
        schema_version=SCHEMA_VERSION_ACTIVITY,
        activity_uid=activity_uid,
        source=SOURCE,
        source_activity_id=activity_id,
        athlete_uid=None,
        title=title,
        description=None,
        sport=_sport(sport),
        start={
            "start_at_utc": stats["start_at_utc"],
            "start_at_local": None,
            "timezone": None,
            "utc_offset_s": None,
        },
        duration={
            "moving_time_s": stats["moving_time_s"],
            "elapsed_time_s": stats["elapsed_time_s"],
        },
        distance={"distance_m": stats["distance_m"]},
        elevation={
            "gain_m": stats["elevation_gain_m"],
            "loss_m": stats["elevation_loss_m"],
            "high_m": stats["high_m"],
            "low_m": stats["low_m"],
        },
        energy={},
        metrics={
            "average_speed_mps": stats["average_speed_mps"],
            "average_moving_speed_mps": stats["average_moving_speed_mps"],
        },
        location={
            "start_latlng": stats["start_latlng"],
            "end_latlng": stats["end_latlng"],
        },
        gear={},
        flags={
            "manual": True,
            "manual_import": True,
            "private": None,
        },
        completeness={
            "has_detail": True,
            "has_streams": stream is not None,
            "has_laps": False,
            "has_segments": False,
            "has_zones": False,
            "has_gpx": True,
        },
        laps=[],
        segments=[],
        stream_uid=stream_uid if stream is not None else None,
        source_reference=reference,
        source_links=[reference],
        external_ids={
            "manual_activity_id": activity_id,
            "source_platform": source_platform,
        },
        sport_specific={
            "source_platform": source_platform,
            "original_file_format": "gpx",
            "manual_import": True,
        },
    )
    return activity, stream


def _normalized_stream(
    activity_id: str,
    activity_uid: str,
    stream_uid: str,
    points: list[TrackPoint],
    reference: SourceReference,
) -> NormalizedStream | None:
    if not points:
        return None
    streams: dict[str, dict[str, Any]] = {
        "time": {"unit": "s", "values": _elapsed_seconds(points)},
        "latlng": {
            "unit": "deg",
            "values": [
                [point.lat, point.lng]
                if point.lat is not None and point.lng is not None
                else None
                for point in points
            ],
        },
        "distance": {
            "unit": "m",
            "values": [point.distance_m for point in points],
        },
        "altitude": {
            "unit": "m",
            "values": [point.altitude_m for point in points],
        },
    }
    if any(point.heartrate_bpm is not None for point in points):
        streams["heartrate"] = {
            "unit": "bpm",
            "values": [point.heartrate_bpm for point in points],
        }
    if any(point.cadence is not None for point in points):
        streams["cadence"] = {
            "unit": "rpm",
            "values": [point.cadence for point in points],
        }
    return NormalizedStream(
        schema_version=SCHEMA_VERSION_STREAM,
        stream_uid=stream_uid,
        activity_uid=activity_uid,
        source=SOURCE,
        source_activity_id=activity_id,
        streams=streams,
        samples={
            stream_type: len(stream_data.get("values", []))
            for stream_type, stream_data in streams.items()
            if isinstance(stream_data.get("values"), list)
        },
        source_reference=reference,
    )


def _with_cumulative_distance(points: list[TrackPoint]) -> list[TrackPoint]:
    distance_m = 0.0
    enriched: list[TrackPoint] = []
    previous: TrackPoint | None = None
    for point in points:
        if previous is not None:
            distance_m += _haversine_m(previous, point)
        enriched.append(replace(point, distance_m=round(distance_m, 3)))
        previous = point
    return enriched


def _track_stats(points: list[TrackPoint]) -> dict[str, Any]:
    timestamps = [_parse_datetime(point.timestamp) for point in points]
    first_timestamp = next((item for item in timestamps if item is not None), None)
    last_timestamp = next(
        (item for item in reversed(timestamps) if item is not None),
        None,
    )
    elapsed_time_s = (
        int(max(0.0, (last_timestamp - first_timestamp).total_seconds()))
        if first_timestamp is not None and last_timestamp is not None
        else None
    )
    distance_m = next(
        (
            point.distance_m
            for point in reversed(points)
            if isinstance(point.distance_m, int | float)
        ),
        None,
    )
    moving_time_s = _moving_time(points, timestamps)
    elevations = [
        point.altitude_m
        for point in points
        if isinstance(point.altitude_m, int | float)
    ]
    return {
        "start_at_utc": first_timestamp.isoformat().replace("+00:00", "Z")
        if first_timestamp is not None
        else None,
        "elapsed_time_s": elapsed_time_s,
        "moving_time_s": moving_time_s,
        "distance_m": distance_m,
        "elevation_gain_m": _elevation_delta(points, positive=True),
        "elevation_loss_m": _elevation_delta(points, positive=False),
        "high_m": max(elevations) if elevations else None,
        "low_m": min(elevations) if elevations else None,
        "average_speed_mps": _speed(distance_m, elapsed_time_s),
        "average_moving_speed_mps": _speed(distance_m, moving_time_s),
        "start_latlng": _latlng(points[0]),
        "end_latlng": _latlng(points[-1]),
    }


def _moving_time(
    points: list[TrackPoint],
    timestamps: list[datetime | None],
) -> int | None:
    if len(points) < 2 or all(timestamp is None for timestamp in timestamps):
        return None
    moving_seconds = 0.0
    for index in range(1, len(points)):
        previous_timestamp = timestamps[index - 1]
        timestamp = timestamps[index]
        if previous_timestamp is None or timestamp is None:
            continue
        delta_s = max(0.0, (timestamp - previous_timestamp).total_seconds())
        distance_delta = (
            (points[index].distance_m or 0.0) - (points[index - 1].distance_m or 0.0)
        )
        if distance_delta > 0.5:
            moving_seconds += delta_s
    return int(moving_seconds)


def _elevation_delta(points: list[TrackPoint], *, positive: bool) -> float | None:
    total = 0.0
    found = False
    for index in range(1, len(points)):
        previous = points[index - 1].altitude_m
        current = points[index].altitude_m
        if previous is None or current is None:
            continue
        delta = current - previous
        if positive and delta > 0:
            total += delta
            found = True
        elif not positive and delta < 0:
            total += abs(delta)
            found = True
    return round(total, 3) if found else None


def _elapsed_seconds(points: list[TrackPoint]) -> list[float | None]:
    timestamps = [_parse_datetime(point.timestamp) for point in points]
    first = next((timestamp for timestamp in timestamps if timestamp is not None), None)
    if first is None:
        return [None for _ in points]
    return [
        round((timestamp - first).total_seconds(), 3) if timestamp is not None else None
        for timestamp in timestamps
    ]


def _haversine_m(left: TrackPoint, right: TrackPoint) -> float:
    if (
        left.lat is None
        or left.lng is None
        or right.lat is None
        or right.lng is None
    ):
        return 0.0
    radius_m = 6_371_000.0
    lat1 = math.radians(left.lat)
    lat2 = math.radians(right.lat)
    delta_lat = math.radians(right.lat - left.lat)
    delta_lng = math.radians(right.lng - left.lng)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def _stream_index(stream: NormalizedStream) -> dict[str, Any]:
    return {
        "schema_version": "nono.streams_index.v1",
        "activity_uid": stream.activity_uid,
        "stream_uid": stream.stream_uid,
        "source": stream.source,
        "source_activity_id": stream.source_activity_id,
        "samples": stream.samples,
        "source_reference": stream.source_reference,
    }


def _sport(source_type: str) -> dict[str, str]:
    source = source_type.strip() or "unknown"
    family, discipline, movement_context = SPORT_MAP.get(
        _slug(source),
        ("other", _slug(source), "unknown"),
    )
    return {
        "family": family,
        "discipline": discipline,
        "movement_context": movement_context,
        "source_type": source,
    }


def _source_reference(
    raw_root: Path,
    path: Path,
    manifest_index: dict[str, dict[str, Any]],
    *,
    entity_type: str,
    source_id: str,
) -> SourceReference:
    relative_path = path.relative_to(raw_root).as_posix()
    manifest = manifest_index.get(relative_path, {})
    return SourceReference(
        source=SOURCE,
        entity_type=entity_type,
        source_id=source_id,
        raw_path=relative_path,
        raw_sha256=manifest.get("sha256") or _file_sha256(path),
        endpoint=manifest.get("endpoint") or "manual.raw_file",
        collected_at=manifest.get("generated_at"),
    )


def _append_manifest(raw_root: Path, entry: RawManifestEntry) -> None:
    manifest_path = raw_root / MANIFEST_FILENAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as manifest_file:
        manifest_file.write(
            json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True) + "\n"
        )


def _read_manifest_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    index: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as manifest_file:
        for line in manifest_file:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and isinstance(payload.get("path"), str):
                index[payload["path"]] = payload
    return index


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _speed(distance_m: float | None, duration_s: int | None) -> float | None:
    if distance_m is None or duration_s is None or duration_s <= 0:
        return None
    return round(distance_m / duration_s, 6)


def _latlng(point: TrackPoint) -> list[float] | None:
    if point.lat is None or point.lng is None:
        return None
    return [point.lat, point.lng]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _slug(value: str) -> str:
    normalized = []
    for char in value.strip().lower():
        if char.isalnum():
            normalized.append(char)
        elif normalized and normalized[-1] != "_":
            normalized.append("_")
    slug = "".join(normalized).strip("_")
    return slug or "manual"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_with_sha256(source_path: Path, destination_path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    bytes_written = 0
    with (
        source_path.open("rb") as input_file,
        destination_path.open("wb") as output_file,
    ):
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            output_file.write(chunk)
            digest.update(chunk)
            bytes_written += len(chunk)
    return digest.hexdigest(), bytes_written
