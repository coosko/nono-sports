"""Strava raw dataset normalization orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nono_sports.core.paths import strava_path
from nono_sports.domain.activity import NormalizedActivity
from nono_sports.domain.athlete import NormalizedAthlete
from nono_sports.domain.source import SourceReference
from nono_sports.domain.stream import NormalizedStream
from nono_sports.normalization.strava_activity import normalize_strava_activity
from nono_sports.normalization.strava_athlete import normalize_strava_athlete
from nono_sports.normalization.strava_stream import normalize_strava_stream
from nono_sports.storage.normalized_store import NormalizedStore, NormalizedWriteResult

SOURCE = "strava"


@dataclass(frozen=True)
class StravaNormalizationResult:
    athletes: int
    activities: int
    streams: int
    written: tuple[NormalizedWriteResult, ...]
    normalized_root: str


def normalize_strava_dataset(data_root: Path) -> StravaNormalizationResult:
    raw_root = strava_path(data_root, "raw")
    manifest_index = _read_manifest_index(raw_root / "manifest.jsonl")
    store = NormalizedStore(data_root)

    athletes = _normalize_athletes(raw_root, manifest_index)
    activities, streams = _normalize_activities(raw_root, manifest_index)

    written = [
        store.write_jsonl("athletes.jsonl", athletes),
        store.write_jsonl("activities.jsonl", activities),
        store.write_jsonl("streams.jsonl", streams),
    ]
    return StravaNormalizationResult(
        athletes=len(athletes),
        activities=len(activities),
        streams=len(streams),
        written=tuple(written),
        normalized_root=str(store.normalized_root),
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


def _normalize_activities(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> tuple[list[NormalizedActivity], list[NormalizedStream]]:
    activities: list[NormalizedActivity] = []
    streams: list[NormalizedStream] = []
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
        stream_reference, stream_payload = _optional_payload(
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
        segment_payloads = _segment_payloads(raw_root, manifest_index, payload)
        activity_for_normalization = dict(payload)
        if isinstance(laps_payload, list):
            activity_for_normalization["laps"] = laps_payload
        activities.append(
            normalize_strava_activity(
                activity_for_normalization,
                source_reference=activity_reference,
                stream_reference=stream_reference,
                laps_reference=laps_reference,
                gear_payload=gear_payload if isinstance(gear_payload, dict) else None,
                gear_reference=gear_reference,
                segment_payloads=segment_payloads,
            )
        )
        if isinstance(stream_payload, dict) and stream_reference is not None:
            streams.append(
                normalize_strava_stream(
                    activity_id,
                    stream_payload,
                    source_reference=stream_reference,
                )
            )
    return activities, streams


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
) -> list[tuple[dict[str, Any], SourceReference]]:
    payloads = []
    for segment_id in _extract_segment_ids(activity):
        reference, payload = _optional_payload(
            raw_root,
            manifest_index,
            relative_path=Path("segments") / f"{_safe_filename(segment_id)}.json",
            entity_type="segment",
            source_id=segment_id,
        )
        if reference is not None and isinstance(payload, dict):
            payloads.append((payload, reference))
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


def _safe_filename(value: object) -> str:
    return str(value).replace("/", "_")
