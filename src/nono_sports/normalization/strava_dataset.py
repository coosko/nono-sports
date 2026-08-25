"""Strava raw dataset normalization orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import strava_path
from nono_sports.domain.athlete import NormalizedAthlete
from nono_sports.domain.equipment import NormalizedEquipment
from nono_sports.domain.source import SourceReference
from nono_sports.domain.stream import NormalizedStream
from nono_sports.normalization.strava_activity import normalize_strava_activity
from nono_sports.normalization.strava_athlete import normalize_strava_athlete
from nono_sports.normalization.strava_equipment import normalize_strava_equipment
from nono_sports.normalization.strava_stream import normalize_strava_stream
from nono_sports.storage.incremental import (
    build_file_fingerprint,
    is_incremental_state_current,
    state_counts,
)
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SOURCE = "strava"
REQUIRED_OUTPUTS = (
    "athletes.jsonl",
    "equipment.jsonl",
    "activities.jsonl",
    "streams.jsonl",
    "streams_index.jsonl",
    "state.json",
)
FINGERPRINT_PATTERNS = (
    "athlete/*.json",
    "activities/*.json",
    "gear/*.json",
    "laps/*.json",
    "segments/*.json",
    "streams/*.json",
)


@dataclass(frozen=True)
class StravaNormalizationResult:
    athletes: int
    equipment: int
    activities: int
    streams: int
    streams_index: int
    written: tuple[SourceNormalizedWriteResult, ...]
    normalized_root: str
    skipped: bool = False


def normalize_strava_dataset(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> StravaNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    raw_root = strava_path(data_root, "raw")
    normalized_root = strava_path(data_root, "normalizado")
    manifest_index = _read_manifest_index(raw_root / "manifest.jsonl")
    store = SourceNormalizedStore(normalized_root)
    previous_state = _read_optional_json(normalized_root / "state.json")
    input_fingerprint = _strava_dataset_fingerprint(raw_root)
    if is_incremental_state_current(
        previous_state,
        input_fingerprint,
        output_root=normalized_root,
        required_outputs=REQUIRED_OUTPUTS,
    ):
        counts = state_counts(previous_state)
        return StravaNormalizationResult(
            athletes=int(counts.get("athletes") or 0),
            equipment=int(counts.get("equipment") or 0),
            activities=int(counts.get("activities") or 0),
            streams=int(counts.get("streams") or 0),
            streams_index=int(counts.get("streams_index") or 0),
            written=(),
            normalized_root=str(normalized_root),
            skipped=True,
        )

    athletes = _normalize_athletes(raw_root, manifest_index)
    equipment = _normalize_equipment(raw_root, manifest_index)
    activities_result = store.write_jsonl(
        "activities.jsonl",
        _iter_normalized_activities(raw_root, manifest_index),
    )
    streams_result = store.write_jsonl(
        "streams.jsonl",
        _iter_normalized_streams(raw_root, manifest_index),
    )
    streams_index_result = store.write_jsonl(
        "streams_index.jsonl",
        _iter_stream_index_from_jsonl(normalized_root / "streams.jsonl"),
    )
    state = {
        "schema_version": "nono.strava.normalization_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "inputs": {
            "raw_root": str(raw_root),
            "manifest": str(raw_root / "manifest.jsonl"),
            "input_fingerprint": input_fingerprint,
        },
        "outputs": {
            "athletes": "athletes.jsonl",
            "equipment": "equipment.jsonl",
            "activities": "activities.jsonl",
            "streams": "streams.jsonl",
            "streams_index": "streams_index.jsonl",
            "state": "state.json",
        },
        "counts": {
            "athletes": len(athletes),
            "equipment": len(equipment),
            "activities": activities_result.records_written,
            "streams": streams_result.records_written,
            "streams_index": streams_index_result.records_written,
        },
    }

    written = [
        store.write_jsonl("athletes.jsonl", athletes),
        store.write_jsonl("equipment.jsonl", equipment),
        activities_result,
        streams_result,
        streams_index_result,
        store.write_json("state.json", state),
    ]
    return StravaNormalizationResult(
        athletes=len(athletes),
        equipment=len(equipment),
        activities=activities_result.records_written,
        streams=streams_result.records_written,
        streams_index=streams_index_result.records_written,
        written=tuple(written),
        normalized_root=str(normalized_root),
    )


def _strava_dataset_fingerprint(raw_root: Path) -> dict[str, Any]:
    return build_file_fingerprint(
        raw_root,
        FINGERPRINT_PATTERNS,
        manifest_path=raw_root / "manifest.jsonl",
        exclude=lambda path: path.relative_to(raw_root).as_posix()
        in {"activities/activities.json", "segments/starred.json"},
    )


def _normalize_athletes(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> list[NormalizedAthlete]:
    profile_path = raw_root / "athlete" / "profile.json"
    if not profile_path.exists():
        return []
    payload = _read_json(profile_path)
    if not isinstance(payload, dict):
        return []
    athlete_id = str(payload.get("id"))
    reference = _source_reference(
        raw_root,
        profile_path,
        manifest_index,
        entity_type="athlete",
        source_id=athlete_id,
    )
    return [normalize_strava_athlete(payload, source_reference=reference)]


def _normalize_equipment(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> list[NormalizedEquipment]:
    profile_path = raw_root / "athlete" / "profile.json"
    records: dict[str, NormalizedEquipment] = {}
    fallback_types: dict[str, str] = {}
    if profile_path.exists():
        profile = _read_json(profile_path)
        if isinstance(profile, dict):
            for key, fallback_type in (("bikes", "bike"), ("shoes", "shoe")):
                for item in profile.get(key, []):
                    if not isinstance(item, dict) or item.get("id") is None:
                        continue
                    equipment_id = str(item["id"])
                    fallback_types[equipment_id] = fallback_type
                    detail_path = (
                        raw_root
                        / "gear"
                        / f"{_safe_filename(equipment_id)}.json"
                    )
                    has_detail = detail_path.exists()
                    reference_path = detail_path if has_detail else profile_path
                    payload = _read_json(reference_path) if has_detail else item
                    if not isinstance(payload, dict):
                        continue
                    payload = dict(payload)
                    payload.setdefault("type", fallback_type)
                    reference = _source_reference(
                        raw_root,
                        reference_path,
                        manifest_index,
                        entity_type="gear",
                        source_id=equipment_id,
                    )
                    record = normalize_strava_equipment(
                        payload,
                        source_reference=reference,
                        fallback_type=fallback_type,
                    )
                    records[record.equipment_uid] = record
    for gear_path in sorted((raw_root / "gear").glob("*.json")):
        payload = _read_json(gear_path)
        if not isinstance(payload, dict) or payload.get("id") is None:
            continue
        equipment_id = str(payload["id"])
        payload = dict(payload)
        payload.setdefault("type", fallback_types.get(equipment_id))
        reference = _source_reference(
            raw_root,
            gear_path,
            manifest_index,
            entity_type="gear",
            source_id=equipment_id,
        )
        record = normalize_strava_equipment(
            payload,
            source_reference=reference,
        )
        records[record.equipment_uid] = record
    return [records[uid] for uid in sorted(records)]


def _iter_normalized_activities(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
):
    available_segment_files = {
        path.name
        for path in (raw_root / "segments").glob("*.json")
    }
    segment_payload_cache: dict[
        str,
        tuple[dict[str, Any], SourceReference] | None,
    ] = {}
    for activity_path in sorted((raw_root / "activities").glob("*.json")):
        if activity_path.name == "activities.json":
            continue
        payload = _read_json(activity_path)
        if not isinstance(payload, dict) or payload.get("id") is None:
            continue
        activity_id = str(payload["id"])
        activity_reference = _source_reference(
            raw_root,
            activity_path,
            manifest_index,
            entity_type="activity",
            source_id=activity_id,
        )
        stream_reference = _optional_reference(
            raw_root,
            manifest_index,
            relative_path=Path("streams") / f"{activity_id}.json",
            entity_type="stream",
            source_id=activity_id,
        )
        laps_reference, laps_payload = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("laps") / f"{activity_id}.json",
            entity_type="laps",
            source_id=activity_id,
        )
        gear_reference, gear_payload = _gear_payload(raw_root, manifest_index, payload)
        segment_payloads = _segment_payloads(
            raw_root,
            manifest_index,
            payload,
            available_segment_files=available_segment_files,
            segment_payload_cache=segment_payload_cache,
        )
        activity_for_normalization = dict(payload)
        if isinstance(laps_payload, list):
            activity_for_normalization["laps"] = laps_payload
        yield normalize_strava_activity(
            activity_for_normalization,
            source_reference=activity_reference,
            stream_reference=stream_reference,
            laps_reference=laps_reference,
            gear_payload=gear_payload if isinstance(gear_payload, dict) else None,
            gear_reference=gear_reference,
            segment_payloads=segment_payloads,
        )


def _iter_normalized_streams(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
):
    for stream_path in sorted((raw_root / "streams").glob("*.json")):
        payload = _read_json(stream_path)
        if not isinstance(payload, dict):
            continue
        activity_id = stream_path.stem
        stream_reference = _source_reference(
            raw_root,
            stream_path,
            manifest_index,
            entity_type="stream",
            source_id=activity_id,
        )
        yield normalize_strava_stream(
            activity_id,
            payload,
            source_reference=stream_reference,
        )


def _iter_stream_index_from_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                yield _stream_index(payload)


def _optional_reference(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    *,
    relative_path: Path,
    entity_type: str,
    source_id: str,
) -> SourceReference | None:
    path = raw_root / relative_path
    if not path.exists():
        return None
    return _source_reference(
        raw_root,
        path,
        manifest_index,
        entity_type=entity_type,
        source_id=source_id,
    )


def _optional_payload(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    *,
    relative_path: Path,
    entity_type: str,
    source_id: str,
) -> tuple[SourceReference | None, Any | None]:
    path = raw_root / relative_path
    if not path.exists():
        return None, None
    return (
        _source_reference(
            raw_root,
            path,
            manifest_index,
            entity_type=entity_type,
            source_id=source_id,
        ),
        _read_json(path),
    )


def _gear_payload(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    activity: dict[str, Any],
) -> tuple[SourceReference | None, Any | None]:
    gear_id = activity.get("gear_id")
    if gear_id is None:
        return None, None
    return _optional_payload(
        raw_root,
        manifest_index,
        relative_path=Path("gear") / f"{_safe_filename(gear_id)}.json",
        entity_type="gear",
        source_id=str(gear_id),
    )


def _segment_payloads(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    activity: dict[str, Any],
    *,
    available_segment_files: set[str],
    segment_payload_cache: dict[
        str,
        tuple[dict[str, Any], SourceReference] | None,
    ],
) -> list[tuple[dict[str, Any], SourceReference]]:
    payloads = []
    for segment_id in _extract_segment_ids(activity):
        filename = f"{_safe_filename(segment_id)}.json"
        if filename not in available_segment_files:
            continue
        cached = segment_payload_cache.get(segment_id)
        if cached is not None:
            payloads.append(cached)
            continue
        if segment_id in segment_payload_cache:
            continue
        reference, payload = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("segments") / filename,
            entity_type="segment",
            source_id=segment_id,
        )
        if reference is not None and isinstance(payload, dict):
            cached_payload = (payload, reference)
            segment_payload_cache[segment_id] = cached_payload
            payloads.append(cached_payload)
        else:
            segment_payload_cache[segment_id] = None
    return payloads


def _extract_segment_ids(activity: dict[str, Any]) -> list[str]:
    segment_ids: set[str] = set()
    efforts = activity.get("segment_efforts")
    if not isinstance(efforts, list):
        return []
    for effort in efforts:
        if not isinstance(effort, dict):
            continue
        segment = effort.get("segment")
        if isinstance(segment, dict) and segment.get("id") is not None:
            segment_ids.add(str(segment["id"]))
        elif effort.get("segment_id") is not None:
            segment_ids.add(str(effort["segment_id"]))
    return sorted(segment_ids)


def _stream_index(stream: NormalizedStream | dict[str, Any]) -> dict[str, Any]:
    if isinstance(stream, dict):
        return {
            "schema_version": "nono.streams_index.v1",
            "activity_uid": stream.get("activity_uid"),
            "stream_uid": stream.get("stream_uid"),
            "source": stream.get("source"),
            "source_activity_id": stream.get("source_activity_id"),
            "samples": stream.get("samples", {}),
            "source_reference": stream.get("source_reference", {}),
        }
    return {
        "schema_version": "nono.streams_index.v1",
        "activity_uid": stream.activity_uid,
        "stream_uid": stream.stream_uid,
        "source": stream.source,
        "source_activity_id": stream.source_activity_id,
        "samples": stream.samples,
        "source_reference": stream.source_reference,
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
        raw_sha256=manifest.get("sha256"),
        endpoint=manifest.get("endpoint"),
        collected_at=manifest.get("generated_at"),
    )


def _read_manifest_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    index: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
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
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return _read_json(path)


def _safe_filename(value: object) -> str:
    return str(value).replace("/", "_")
