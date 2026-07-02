"""Garmin Connect raw dataset normalization orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.domain.source import SourceReference
from nono_sports.normalization.garmin_activity import normalize_garmin_activity
from nono_sports.normalization.garmin_stream import normalize_garmin_stream
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SOURCE = "garmin_connect"


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
            activities.append(previous_records.activities[activity_id])
            if activity_id in previous_records.streams:
                streams.append(previous_records.streams[activity_id])
            reused += 1
            continue

        fit_messages_reference, fit_messages = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("fit_decoded") / f"{activity_id}.fitdecode.json",
            entity_type="fit_decoded",
            source_id=activity_id,
        )
        messages = _dict(fit_messages).get("messages")
        fit_message_payload = messages if isinstance(messages, dict) else {}
        references = _references(raw_root, manifest_index, activity_id, activity_path)
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
        processed += 1
    return activities, streams, processed, reused, activity_inputs


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
        "fit_decoded": Path("fit_decoded") / f"{activity_id}.fitdecode.json",
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
