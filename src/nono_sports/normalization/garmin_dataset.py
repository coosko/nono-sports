"""Garmin Connect raw dataset normalization orchestration."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.domain.source import SourceReference
from nono_sports.formats.fit import decode_fit_with_fitdecode
from nono_sports.formats.track_xml import (
    parse_gpx_track_points,
    parse_tcx_track_points,
)
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.normalization.garmin_activity import normalize_garmin_activity
from nono_sports.normalization.garmin_stream import (
    normalize_garmin_stream,
    normalize_garmin_track_stream,
)
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SOURCE = "garmin_connect"
FIT_MESSAGES_USED_FOR_NORMALIZATION = frozenset(
    {"record", "hrv", "lap", "time_in_zone"}
)


@dataclass(frozen=True)
class GarminNormalizationResult:
    activities: int
    streams: int
    laps: int
    splits: int
    typed_splits: int
    processed_activities: int
    reused_activities: int
    written: tuple[SourceNormalizedWriteResult, ...]
    normalized_root: str


@dataclass(frozen=True)
class _PreviousGarminRecords:
    activities: dict[str, dict[str, Any]]
    streams: dict[str, dict[str, Any]]

    @classmethod
    def empty(cls) -> "_PreviousGarminRecords":
        return cls(activities={}, streams={})


def normalize_garmin_dataset(
    data_root: Path,
    *,
    force: bool = False,
    keep_intermediate_files: bool = False,
    generated_at: datetime | None = None,
) -> GarminNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    raw_root = garmin_connect_path(data_root, "raw")
    normalized_root = garmin_connect_path(data_root, "normalizado")
    manifest_index = _read_manifest_index(raw_root / "manifest.jsonl")
    previous_state = _read_json(normalized_root / "state.json")
    previous_inputs = _previous_activity_inputs(previous_state)
    previous_records = _read_previous_records(normalized_root)
    activities, streams, processed, reused, activity_inputs = _normalize_activities(
        raw_root,
        manifest_index,
        previous_inputs=previous_inputs,
        previous_records=previous_records,
        force=force,
        keep_intermediate_files=keep_intermediate_files,
        raw_store=GarminRawStore(data_root) if keep_intermediate_files else None,
    )
    laps = [
        lap
        for activity in activities
        for lap in _activity_laps(activity)
    ]
    splits = _normalize_json_payloads(
        raw_root / "splits",
        "*.json",
        exclude_suffixes=(".summaries.json",),
    )
    typed_splits = _normalize_json_payloads(raw_root / "typed_splits", "*.json")
    state = {
        "schema_version": "nono.garmin_connect.normalization_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "force": force,
        "keep_intermediate_files": keep_intermediate_files,
        "inputs": {
            "raw_root": str(raw_root),
            "manifest": str(raw_root / "manifest.jsonl"),
            "activities": activity_inputs,
        },
        "outputs": {
            "activities": "activities.jsonl",
            "streams": "streams.jsonl",
            "streams_index": "streams_index.jsonl",
            "laps": "laps.jsonl",
            "splits": "splits.jsonl",
            "typed_splits": "typed_splits.jsonl",
            "segment_candidates": "segment_candidates.jsonl",
            "state": "state.json",
        },
        "counts": {
            "activities": len(activities),
            "streams": len(streams),
            "laps": len(laps),
            "splits": len(splits),
            "typed_splits": len(typed_splits),
            "segment_candidates": 0,
            "processed_activities": processed,
            "reused_activities": reused,
        },
    }

    store = SourceNormalizedStore(normalized_root)
    written = [
        store.write_jsonl("activities.jsonl", activities),
        store.write_jsonl("streams.jsonl", streams),
        store.write_jsonl(
            "streams_index.jsonl",
            [_stream_index(stream) for stream in streams],
        ),
        store.write_jsonl("laps.jsonl", laps),
        store.write_jsonl("splits.jsonl", splits),
        store.write_jsonl("typed_splits.jsonl", typed_splits),
        store.write_jsonl("segment_candidates.jsonl", []),
        store.write_json("state.json", state),
    ]
    return GarminNormalizationResult(
        activities=len(activities),
        streams=len(streams),
        laps=len(laps),
        splits=len(splits),
        typed_splits=len(typed_splits),
        processed_activities=processed,
        reused_activities=reused,
        written=tuple(written),
        normalized_root=str(normalized_root),
    )


def _normalize_activities(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    *,
    previous_inputs: dict[str, dict[str, Any]],
    previous_records: "_PreviousGarminRecords",
    force: bool,
    keep_intermediate_files: bool,
    raw_store: GarminRawStore | None,
) -> tuple[
    list[Any],
    list[Any],
    int,
    int,
    dict[str, dict[str, Any]],
]:
    activities: list[Any] = []
    streams: list[Any] = []
    processed = 0
    reused = 0
    activity_inputs: dict[str, dict[str, Any]] = {}
    for activity_path in sorted((raw_root / "activities").glob("*.json")):
        if activity_path.name == "activities_index.json" or "." in activity_path.stem:
            continue
        activity = _read_json(activity_path)
        if not isinstance(activity, dict) or activity.get("activityId") is None:
            continue
        activity_id = str(activity["activityId"])
        fingerprint = _activity_input_fingerprint(raw_root, manifest_index, activity_id)
        activity_inputs[activity_id] = fingerprint
        if (
            not force
            and previous_inputs.get(activity_id) == fingerprint
            and activity_id in previous_records.activities
        ):
            activities.append(
                _sanitize_reused_activity_record(
                    previous_records.activities[activity_id],
                    raw_root,
                )
            )
            if activity_id in previous_records.streams:
                streams.append(
                    _sanitize_reused_stream_record(
                        previous_records.streams[activity_id],
                        raw_root,
                        manifest_index,
                        activity_id,
                    )
                )
            reused += 1
            continue

        references = _references(raw_root, manifest_index, activity_id, activity_path)
        fit_messages_reference, fit_message_payload = _fit_messages(
            raw_root,
            manifest_index,
            activity_id,
            fit_reference=references.get("fit"),
            keep_intermediate_files=keep_intermediate_files,
            raw_store=raw_store,
        )
        splits_reference, splits_payload = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("splits") / f"{activity_id}.json",
            entity_type="splits",
            source_id=activity_id,
        )
        typed_splits_reference, typed_splits_payload = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("typed_splits") / f"{activity_id}.json",
            entity_type="typed_splits",
            source_id=activity_id,
        )
        weather_reference, weather_payload = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("weather") / f"{activity_id}.json",
            entity_type="weather",
            source_id=activity_id,
        )
        activity_record = normalize_garmin_activity(
            activity,
            source_reference=references["activity"],
            details_reference=references.get("details"),
            fit_reference=references.get("fit"),
            decoded_fit_reference=fit_messages_reference,
            gpx_reference=references.get("gpx"),
            tcx_reference=references.get("tcx"),
            splits_reference=splits_reference,
            typed_splits_reference=typed_splits_reference,
            weather_reference=weather_reference,
            fit_messages=fit_message_payload,
            splits_payload=splits_payload,
            typed_splits_payload=typed_splits_payload,
            weather_payload=weather_payload,
        )
        activities.append(activity_record)
        if fit_messages_reference is not None:
            stream = normalize_garmin_stream(
                activity_id,
                fit_message_payload,
                source_reference=fit_messages_reference,
            )
            if stream is not None:
                streams.append(stream)
        else:
            stream = _fallback_track_stream(raw_root, references, activity_id)
            if stream is not None:
                streams.append(stream)
        processed += 1
    return activities, streams, processed, reused, activity_inputs


def _fit_messages(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    activity_id: str,
    *,
    fit_reference: SourceReference | None,
    keep_intermediate_files: bool,
    raw_store: GarminRawStore | None,
) -> tuple[SourceReference | None, dict[str, list[dict[str, Any]]]]:
    decoded_reference, decoded_payload = _optional_payload(
        raw_root,
        manifest_index,
        relative_path=Path("fit_decoded") / f"{activity_id}.fitdecode.json",
        entity_type="fit_decoded",
        source_id=activity_id,
    )
    decoded_messages = _dict(decoded_payload).get("messages")
    if decoded_reference is not None and isinstance(decoded_messages, dict):
        return decoded_reference, decoded_messages

    fit_path = raw_root / "activity_files" / f"{activity_id}.fit"
    if fit_reference is None or not fit_path.is_file():
        return None, {}
    result = decode_fit_with_fitdecode(
        fit_path,
        message_names=(
            None if keep_intermediate_files else FIT_MESSAGES_USED_FOR_NORMALIZATION
        ),
    )
    if keep_intermediate_files and raw_store is not None:
        output_relative = Path("fit_decoded") / f"{activity_id}.fitdecode.json"
        written = raw_store.write_json(
            output_relative,
            {
                "backend": result.backend,
                "errors": list(result.errors),
                "frames": result.frames,
                "messages": result.messages,
            },
            endpoint="fitdecode",
            params={"path": fit_path.relative_to(raw_root).as_posix()},
            kind="derived",
        )
        return (
            SourceReference(
                source=SOURCE,
                entity_type="fit_decoded",
                source_id=activity_id,
                raw_path=written.relative_path,
                raw_sha256=written.sha256,
                endpoint="fitdecode",
            ),
            result.messages,
        )
    return fit_reference, result.messages


def _references(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    activity_id: str,
    activity_path: Path,
) -> dict[str, SourceReference]:
    references = {
        "activity": _source_reference(
            raw_root,
            activity_path,
            manifest_index,
            entity_type="activity",
            source_id=activity_id,
        )
    }
    for key, relative_path, entity_type in (
        (
            "details",
            Path("activities") / f"{activity_id}.details.json",
            "activity_details",
        ),
        ("fit", Path("activity_files") / f"{activity_id}.fit", "fit"),
        ("gpx", Path("activity_files") / f"{activity_id}.gpx", "gpx"),
        ("tcx", Path("activity_files") / f"{activity_id}.tcx", "tcx"),
    ):
        path = raw_root / relative_path
        if path.exists():
            references[key] = _source_reference(
                raw_root,
                path,
                manifest_index,
                entity_type=entity_type,
                source_id=activity_id,
            )
    return references


def _sanitize_reused_activity_record(
    record: dict[str, Any],
    raw_root: Path,
) -> dict[str, Any]:
    sanitized = deepcopy(record)
    source_links = sanitized.get("source_links")
    if isinstance(source_links, list):
        sanitized["source_links"] = [
            link
            for link in source_links
            if not _is_missing_fit_decoded_reference(raw_root, link)
        ]
    return sanitized


def _sanitize_reused_stream_record(
    record: dict[str, Any],
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    activity_id: str,
) -> dict[str, Any]:
    sanitized = deepcopy(record)
    source_reference = sanitized.get("source_reference")
    if _is_missing_fit_decoded_reference(raw_root, source_reference):
        fit_path = raw_root / "activity_files" / f"{activity_id}.fit"
        if fit_path.is_file():
            sanitized["source_reference"] = _source_reference(
                raw_root,
                fit_path,
                manifest_index,
                entity_type="fit",
                source_id=activity_id,
            )
    return sanitized


def _is_missing_fit_decoded_reference(raw_root: Path, reference: Any) -> bool:
    if not isinstance(reference, dict):
        return False
    raw_path = reference.get("raw_path")
    if not isinstance(raw_path, str) or not raw_path.startswith("fit_decoded/"):
        return False
    return not (raw_root / raw_path).is_file()


def _fallback_track_stream(
    raw_root: Path,
    references: dict[str, SourceReference],
    activity_id: str,
) -> Any | None:
    gpx_reference = references.get("gpx")
    if gpx_reference is not None:
        stream = normalize_garmin_track_stream(
            activity_id,
            parse_gpx_track_points(raw_root / gpx_reference.raw_path),
            source_reference=gpx_reference,
        )
        if stream is not None:
            return stream
    tcx_reference = references.get("tcx")
    if tcx_reference is not None:
        return normalize_garmin_track_stream(
            activity_id,
            parse_tcx_track_points(raw_root / tcx_reference.raw_path),
            source_reference=tcx_reference,
        )
    return None


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


def _normalize_json_payloads(
    root: Path,
    pattern: str,
    *,
    exclude_suffixes: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    records = []
    if not root.exists():
        return []
    for path in sorted(root.glob(pattern)):
        if any(path.name.endswith(suffix) for suffix in exclude_suffixes):
            continue
        payload = _read_json(path)
        records.append(
            {
                "schema_version": "nono.garmin_connect.normalized_aux.v1",
                "source": SOURCE,
                "source_activity_id": path.stem.split(".")[0],
                "payload": payload,
            }
        )
    return records


def _activity_input_fingerprint(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    activity_id: str,
) -> dict[str, Any]:
    paths = {
        "activity": Path("activities") / f"{activity_id}.json",
        "details": Path("activities") / f"{activity_id}.details.json",
        "fit": Path("activity_files") / f"{activity_id}.fit",
        "gpx": Path("activity_files") / f"{activity_id}.gpx",
        "tcx": Path("activity_files") / f"{activity_id}.tcx",
        "splits": Path("splits") / f"{activity_id}.json",
        "typed_splits": Path("typed_splits") / f"{activity_id}.json",
        "weather": Path("weather") / f"{activity_id}.json",
    }
    fingerprint: dict[str, Any] = {}
    for key, relative_path in paths.items():
        path = raw_root / relative_path
        if not path.exists():
            continue
        manifest = manifest_index.get(relative_path.as_posix(), {})
        fingerprint[key] = {
            "path": relative_path.as_posix(),
            "sha256": manifest.get("sha256"),
            "size": path.stat().st_size,
        }
    return fingerprint


def _previous_activity_inputs(state: Any) -> dict[str, dict[str, Any]]:
    inputs = _dict(state).get("inputs")
    activities = _dict(inputs).get("activities")
    return activities if isinstance(activities, dict) else {}


def _read_previous_records(normalized_root: Path) -> _PreviousGarminRecords:
    if not normalized_root.exists():
        return _PreviousGarminRecords.empty()
    return _PreviousGarminRecords(
        activities={
            str(record.get("source_activity_id")): record
            for record in _read_jsonl(normalized_root / "activities.jsonl")
            if record.get("source_activity_id") is not None
        },
        streams={
            str(record.get("source_activity_id")): record
            for record in _read_jsonl(normalized_root / "streams.jsonl")
            if record.get("source_activity_id") is not None
        },
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _activity_laps(activity: Any) -> list[Any]:
    if isinstance(activity, dict):
        laps = activity.get("laps")
    else:
        laps = getattr(activity, "laps", None)
    if not isinstance(laps, list):
        return []
    return laps


def _stream_index(stream: Any) -> dict[str, Any]:
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
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
