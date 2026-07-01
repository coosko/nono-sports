"""Garmin Connect raw dataset normalization orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.domain.activity import NormalizedActivity
from nono_sports.domain.source import SourceReference
from nono_sports.domain.stream import NormalizedStream
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
    written: tuple[SourceNormalizedWriteResult, ...]
    normalized_root: str


def normalize_garmin_dataset(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> GarminNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    raw_root = garmin_connect_path(data_root, "raw")
    normalized_root = garmin_connect_path(data_root, "normalizado")
    manifest_index = _read_manifest_index(raw_root / "manifest.jsonl")
    activities, streams = _normalize_activities(raw_root, manifest_index)
    laps = [
        lap
        for activity in activities
        for lap in activity.laps
        if isinstance(lap, dict) or hasattr(lap, "lap_uid")
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
        "inputs": {
            "raw_root": str(raw_root),
            "manifest": str(raw_root / "manifest.jsonl"),
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
        written=tuple(written),
        normalized_root=str(normalized_root),
    )


def _normalize_activities(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> tuple[list[NormalizedActivity], list[NormalizedStream]]:
    activities: list[NormalizedActivity] = []
    streams: list[NormalizedStream] = []
    for activity_path in sorted((raw_root / "activities").glob("*.json")):
        if activity_path.name == "activities_index.json" or "." in activity_path.stem:
            continue
        activity = _read_json(activity_path)
        if not isinstance(activity, dict) or activity.get("activityId") is None:
            continue
        activity_id = str(activity["activityId"])
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
    return activities, streams


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
