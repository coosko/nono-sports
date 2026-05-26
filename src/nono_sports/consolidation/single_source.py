"""Single-source consolidation for Strava v1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import strava_path
from nono_sports.domain.activity import ActivitySourceLink, ConsolidatedActivity
from nono_sports.storage.consolidated_store import (
    ConsolidatedStore,
    ConsolidatedWriteResult,
)

SCHEMA_VERSION_ACTIVITY = "nono.consolidated_activity.v1"
SCHEMA_VERSION_SOURCE_LINK = "nono.activity_source_link.v1"


@dataclass(frozen=True)
class SingleSourceConsolidationResult:
    activities: int
    activity_sources: int
    streams_index: int
    written: tuple[ConsolidatedWriteResult, ...]
    consolidated_root: str


def build_single_source_consolidated(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> SingleSourceConsolidationResult:
    generated_at = generated_at or datetime.now(UTC)
    normalized_root = strava_path(data_root, "normalizado")
    normalized_activities = _read_jsonl(normalized_root / "activities.jsonl")
    consolidated_activities = [
        _consolidated_activity(activity) for activity in normalized_activities
    ]
    consolidated_activities.sort(
        key=lambda activity: (
            str(activity.start.get("start_at_utc") or ""),
            activity.consolidated_activity_uid,
        )
    )
    source_links = [
        _activity_source_link(activity) for activity in consolidated_activities
    ]
    streams_index = [
        _stream_index(activity)
        for activity in consolidated_activities
        if activity.stream_uid is not None
    ]
    state = {
        "schema_version": "nono.consolidation_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "strategy": "single_source",
        "primary_source": "strava",
        "inputs": {
            "strava_activities": str(normalized_root / "activities.jsonl"),
            "strava_streams": str(normalized_root / "streams.jsonl"),
        },
        "outputs": {
            "activities": "activities.jsonl",
            "activity_sources": "activity_sources.jsonl",
            "streams_index": "streams_index.jsonl",
        },
        "counts": {
            "activities": len(consolidated_activities),
            "activity_sources": len(source_links),
            "streams_index": len(streams_index),
        },
    }

    store = ConsolidatedStore(data_root)
    written = [
        store.write_jsonl("activities.jsonl", consolidated_activities),
        store.write_jsonl("activity_sources.jsonl", source_links),
        store.write_jsonl("streams_index.jsonl", streams_index),
        store.write_json("state.json", state),
    ]
    return SingleSourceConsolidationResult(
        activities=len(consolidated_activities),
        activity_sources=len(source_links),
        streams_index=len(streams_index),
        written=tuple(written),
        consolidated_root=str(store.consolidated_root),
    )


def _consolidated_activity(activity: dict[str, Any]) -> ConsolidatedActivity:
    activity_uid = _required_str(activity, "activity_uid")
    consolidated_uid = f"consolidated:activity:{activity_uid}"
    return ConsolidatedActivity(
        schema_version=SCHEMA_VERSION_ACTIVITY,
        consolidated_activity_uid=consolidated_uid,
        primary_source=str(activity.get("source") or "unknown"),
        primary_activity_uid=activity_uid,
        title=activity.get("title"),
        description=activity.get("description"),
        sport=_dict(activity.get("sport")),
        start=_dict(activity.get("start")),
        duration=_dict(activity.get("duration")),
        distance=_dict(activity.get("distance")),
        elevation=_dict(activity.get("elevation")),
        energy=_dict(activity.get("energy")),
        metrics=_dict(activity.get("metrics")),
        location=_dict(activity.get("location")),
        gear=_dict(activity.get("gear")),
        flags=_dict(activity.get("flags")),
        completeness=_dict(activity.get("completeness")),
        laps=_list_of_dicts(activity.get("laps")),
        segments=_list_of_dicts(activity.get("segments")),
        stream_uid=activity.get("stream_uid"),
        source_count=1,
        source_activity_uids=[activity_uid],
        provenance={
            "strategy": "single_source",
            "primary_source": activity.get("source"),
            "source_reference": activity.get("source_reference"),
            "source_links": activity.get("source_links", []),
        },
        external_ids=_dict(activity.get("external_ids")),
        sport_specific=_dict(activity.get("sport_specific")),
    )


def _activity_source_link(activity: ConsolidatedActivity) -> ActivitySourceLink:
    source_reference = activity.provenance.get("source_reference")
    return ActivitySourceLink(
        schema_version=SCHEMA_VERSION_SOURCE_LINK,
        consolidated_activity_uid=activity.consolidated_activity_uid,
        source=activity.primary_source,
        source_activity_uid=activity.primary_activity_uid,
        normalized_activity_uid=activity.primary_activity_uid,
        source_priority=1,
        match_strategy="single_source",
        match_confidence=1.0,
        source_reference=source_reference if isinstance(source_reference, dict) else {},
    )


def _stream_index(activity: ConsolidatedActivity) -> dict[str, Any]:
    return {
        "schema_version": "nono.streams_index.v1",
        "consolidated_activity_uid": activity.consolidated_activity_uid,
        "stream_uid": activity.stream_uid,
        "source": activity.primary_source,
        "source_activity_uid": activity.primary_activity_uid,
    }


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


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"Missing required normalized activity field: {key}")
    return str(value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
