"""Initial multi-source consolidation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path, manual_path, strava_path
from nono_sports.domain.activity import ActivitySourceLink, ConsolidatedActivity
from nono_sports.storage.consolidated_store import (
    ConsolidatedStore,
    ConsolidatedWriteResult,
)

SCHEMA_VERSION_ACTIVITY = "nono.consolidated_activity.v1"
SCHEMA_VERSION_SOURCE_LINK = "nono.activity_source_link.v1"
SCHEMA_VERSION_DUPLICATE_CANDIDATE = "nono.duplicate_candidate.v1"

SOURCE_PRIORITY = {
    "strava": 1,
    "garmin_connect": 2,
    "manual": 3,
}


@dataclass(frozen=True)
class MultiSourceConsolidationResult:
    activities: int
    activity_sources: int
    streams_index: int
    duplicate_candidates: int
    written: tuple[ConsolidatedWriteResult, ...]
    consolidated_root: str


def build_multi_source_consolidated(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> MultiSourceConsolidationResult:
    generated_at = generated_at or datetime.now(UTC)
    inputs = _load_normalized_inputs(data_root)
    groups, duplicate_candidates = _group_activities(inputs)
    consolidated_activities = [_consolidated_activity(group) for group in groups]
    consolidated_activities.sort(
        key=lambda activity: (
            str(activity.start.get("start_at_utc") or ""),
            activity.consolidated_activity_uid,
        )
    )

    store = ConsolidatedStore(data_root)
    activities_result = store.write_jsonl("activities.jsonl", consolidated_activities)
    source_links_result = store.write_jsonl(
        "activity_sources.jsonl",
        _iter_activity_source_links(consolidated_activities),
    )
    streams_index_result = store.write_jsonl(
        "streams_index.jsonl",
        _iter_stream_index(consolidated_activities),
    )
    duplicate_candidates_result = store.write_jsonl(
        "duplicate_candidates.jsonl",
        duplicate_candidates,
    )
    state = {
        "schema_version": "nono.consolidation_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "strategy": "multi_source_initial",
        "primary_source_policy": "prefer_strava_for_backward_compatibility",
        "inputs": {
            source: str(path)
            for source, path in _normalized_activity_paths(data_root).items()
        },
        "outputs": {
            "activities": "activities.jsonl",
            "activity_sources": "activity_sources.jsonl",
            "streams_index": "streams_index.jsonl",
            "duplicate_candidates": "duplicate_candidates.jsonl",
        },
        "counts": {
            "activities": len(consolidated_activities),
            "activity_sources": source_links_result.records_written,
            "streams_index": streams_index_result.records_written,
            "duplicate_candidates": len(duplicate_candidates),
            "input_activities": len(inputs),
        },
    }

    written = [
        activities_result,
        source_links_result,
        streams_index_result,
        duplicate_candidates_result,
        store.write_json("state.json", state),
    ]
    return MultiSourceConsolidationResult(
        activities=len(consolidated_activities),
        activity_sources=source_links_result.records_written,
        streams_index=streams_index_result.records_written,
        duplicate_candidates=len(duplicate_candidates),
        written=tuple(written),
        consolidated_root=str(store.consolidated_root),
    )


def _load_normalized_inputs(data_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _normalized_activity_paths(data_root).values():
        records.extend(_read_jsonl(path))
    return records


def _normalized_activity_paths(data_root: Path) -> dict[str, Path]:
    return {
        "strava": strava_path(data_root, "normalizado", "activities.jsonl"),
        "garmin_connect": garmin_connect_path(
            data_root,
            "normalizado",
            "activities.jsonl",
        ),
        "manual": manual_path(data_root, "normalizado", "activities.jsonl"),
    }


def _group_activities(
    activities: list[dict[str, Any]],
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    duplicate_candidates: list[dict[str, Any]] = []
    for activity in sorted(activities, key=_activity_sort_key):
        best_index: int | None = None
        best_candidate: dict[str, Any] | None = None
        for index, group in enumerate(groups):
            candidate = _duplicate_candidate(activity, group)
            if candidate is None:
                continue
            if best_candidate is None or candidate["confidence"] > best_candidate[
                "confidence"
            ]:
                best_index = index
                best_candidate = candidate
        if best_index is None or best_candidate is None:
            groups.append([activity])
            continue
        groups[best_index].append(activity)
        duplicate_candidates.append(best_candidate)
    return groups, duplicate_candidates


def _duplicate_candidate(
    activity: dict[str, Any],
    group: list[dict[str, Any]],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for existing in group:
        if existing.get("source") == activity.get("source"):
            continue
        score = _match_score(existing, activity)
        if score is None:
            continue
        candidate = {
            "schema_version": SCHEMA_VERSION_DUPLICATE_CANDIDATE,
            "activity_uid": activity.get("activity_uid"),
            "matched_activity_uid": existing.get("activity_uid"),
            "sources": [existing.get("source"), activity.get("source")],
            "confidence": score["confidence"],
            "match_strategy": score["match_strategy"],
            "signals": score["signals"],
            "action": "auto_grouped_initial_rule",
        }
        if best is None or candidate["confidence"] > best["confidence"]:
            best = candidate
    return best


def _match_score(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any] | None:
    start_delta_s = _start_delta_seconds(left, right)
    duration_delta_s = _numeric_delta(
        left.get("duration"),
        right.get("duration"),
        "moving_time_s",
        "elapsed_time_s",
    )
    distance_delta_m = _numeric_delta(
        left.get("distance"),
        right.get("distance"),
        "distance_m",
    )
    if start_delta_s is None or duration_delta_s is None or distance_delta_m is None:
        return None

    left_duration = _first_number(
        left.get("duration"),
        "moving_time_s",
        "elapsed_time_s",
    )
    left_distance = _first_number(left.get("distance"), "distance_m")
    sport_match = _sport_key(left) == _sport_key(right)
    sport_compatible = _sports_compatible(left, right)
    duration_ok = duration_delta_s <= max(30.0, (left_duration or 0.0) * 0.05)
    distance_ok = distance_delta_m <= max(200.0, (left_distance or 0.0) * 0.05)
    start_ok = start_delta_s <= 120.0
    strict_match = start_ok and duration_ok and distance_ok and sport_match
    synchronized_start = (
        start_delta_s <= 5.0
        and distance_delta_m <= 50.0
        and (
            sport_compatible
            or _has_garmin_import_signal(left, right)
        )
    )
    delayed_cycling_start = (
        start_delta_s <= 1800.0
        and duration_ok
        and distance_delta_m <= max(100.0, (left_distance or 0.0) * 0.01)
        and _canonical_sport(left) == "cycling"
        and _canonical_sport(right) == "cycling"
    )
    if not (strict_match or synchronized_start or delayed_cycling_start):
        return None

    if strict_match:
        match_strategy = "time_duration_distance_sport"
        confidence = 0.90
    elif synchronized_start:
        match_strategy = (
            "garmin_import_start_distance"
            if _has_garmin_import_signal(left, right)
            else "synchronized_start_distance_sport"
        )
        confidence = 0.96
    elif delayed_cycling_start:
        match_strategy = "cycling_duration_distance_delayed_start"
        confidence = 0.92
    if start_delta_s <= 30.0:
        confidence += 0.03
    if duration_delta_s <= 10.0:
        confidence += 0.02
    if distance_delta_m <= 50.0:
        confidence += 0.02
    return {
        "confidence": round(min(confidence, 0.99), 4),
        "match_strategy": match_strategy,
        "signals": {
            "start_delta_s": start_delta_s,
            "duration_delta_s": duration_delta_s,
            "distance_delta_m": distance_delta_m,
            "sport_match": sport_match,
            "sport_compatible": sport_compatible,
            "garmin_import_signal": _has_garmin_import_signal(left, right),
            "device_overlap": _device_overlap(left, right),
        },
    }


def _consolidated_activity(group: list[dict[str, Any]]) -> ConsolidatedActivity:
    ordered = sorted(group, key=_source_priority)
    primary = ordered[0]
    activity_uid = _required_str(primary, "activity_uid")
    consolidated_uid = f"consolidated:activity:{activity_uid}"
    source_links = [
        _source_link_payload(activity, index + 1)
        for index, activity in enumerate(ordered)
    ]
    return ConsolidatedActivity(
        schema_version=SCHEMA_VERSION_ACTIVITY,
        consolidated_activity_uid=consolidated_uid,
        primary_source=str(primary.get("source") or "unknown"),
        primary_activity_uid=activity_uid,
        title=primary.get("title"),
        description=primary.get("description"),
        sport=_preferred_sport(ordered),
        start=_dict(primary.get("start")),
        duration=_dict(primary.get("duration")),
        distance=_dict(primary.get("distance")),
        elevation=_dict(primary.get("elevation")),
        energy=_dict(primary.get("energy")),
        metrics=_dict(primary.get("metrics")),
        location=_dict(primary.get("location")),
        gear=_dict(primary.get("gear")),
        flags=_dict(primary.get("flags")),
        completeness=_merged_completeness(ordered),
        laps=_list_of_dicts(primary.get("laps")),
        segments=_list_of_dicts(primary.get("segments")),
        stream_uid=primary.get("stream_uid"),
        source_count=len(ordered),
        source_activity_uids=[
            _required_str(activity, "activity_uid") for activity in ordered
        ],
        provenance={
            "strategy": "multi_source_initial",
            "primary_source": primary.get("source"),
            "source_reference": primary.get("source_reference"),
            "source_links": source_links,
        },
        external_ids=_merge_dicts(activity.get("external_ids") for activity in ordered),
        sport_specific=_dict(primary.get("sport_specific")),
    )


def _source_link_payload(activity: dict[str, Any], priority: int) -> dict[str, Any]:
    return {
        "source": activity.get("source") or "unknown",
        "activity_uid": _required_str(activity, "activity_uid"),
        "source_activity_id": activity.get("source_activity_id"),
        "source_priority": priority,
        "source_reference": activity.get("source_reference") or {},
        "stream_uid": activity.get("stream_uid"),
    }


def _activity_source_links(activity: ConsolidatedActivity) -> list[ActivitySourceLink]:
    links = []
    source_links = activity.provenance.get("source_links", [])
    for source_link in source_links if isinstance(source_links, list) else []:
        source_reference = source_link.get("source_reference")
        links.append(
            ActivitySourceLink(
                schema_version=SCHEMA_VERSION_SOURCE_LINK,
                consolidated_activity_uid=activity.consolidated_activity_uid,
                source=str(source_link.get("source") or "unknown"),
                source_activity_uid=str(source_link.get("activity_uid")),
                normalized_activity_uid=str(source_link.get("activity_uid")),
                source_priority=int(source_link.get("source_priority") or 99),
                match_strategy=activity.provenance.get("strategy", "unknown"),
                match_confidence=1.0 if activity.source_count == 1 else 0.97,
                source_reference=(
                    source_reference if isinstance(source_reference, dict) else {}
                ),
            )
        )
    return links


def _iter_activity_source_links(
    activities: list[ConsolidatedActivity],
):
    for activity in activities:
        yield from _activity_source_links(activity)


def _iter_stream_index(
    activities: list[ConsolidatedActivity],
):
    for activity in activities:
        source_links = activity.provenance.get("source_links", [])
        for source_link in source_links if isinstance(source_links, list) else []:
            if source_link.get("stream_uid") is not None:
                yield _stream_index(activity, source_link)


def _stream_index(
    activity: ConsolidatedActivity,
    source_link: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "nono.streams_index.v1",
        "consolidated_activity_uid": activity.consolidated_activity_uid,
        "stream_uid": source_link.get("stream_uid"),
        "source": source_link.get("source"),
        "source_activity_uid": source_link.get("activity_uid"),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _activity_sort_key(activity: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(_dict(activity.get("start")).get("start_at_utc") or ""),
        _source_priority(activity),
        str(activity.get("activity_uid") or ""),
    )


def _source_priority(activity: dict[str, Any]) -> int:
    return SOURCE_PRIORITY.get(str(activity.get("source") or ""), 99)


def _start_delta_seconds(
    left: dict[str, Any],
    right: dict[str, Any],
) -> float | None:
    left_start = _parse_datetime(_dict(left.get("start")).get("start_at_utc"))
    right_start = _parse_datetime(_dict(right.get("start")).get("start_at_utc"))
    if left_start is None or right_start is None:
        return None
    return abs((left_start - right_start).total_seconds())


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _numeric_delta(
    left: Any,
    right: Any,
    *keys: str,
) -> float | None:
    left_value = _first_number(left, *keys)
    right_value = _first_number(right, *keys)
    if left_value is None or right_value is None:
        return None
    return abs(left_value - right_value)


def _first_number(payload: Any, *keys: str) -> float | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int | float):
            return float(value)
    return None


def _sport_key(activity: dict[str, Any]) -> tuple[str, str]:
    sport = _dict(activity.get("sport"))
    return (
        str(sport.get("family") or "").lower(),
        str(sport.get("discipline") or "").lower(),
    )


def _canonical_sport(activity: dict[str, Any]) -> str:
    family, discipline = _sport_key(activity)
    if family == "cycling" or discipline in {
        "cycling",
        "indoor_cycling",
        "road_cycling",
        "virtual_ride",
    }:
        return "cycling"
    if family == "walking_hiking" or discipline in {"hiking", "walking"}:
        return "walking_hiking"
    if family == "fitness" or discipline == "general_workout":
        return "fitness"
    return f"{family}:{discipline}"


def _sports_compatible(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _canonical_sport(left) == _canonical_sport(right)


def _has_garmin_import_signal(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    for activity in (left, right):
        if activity.get("source") != "strava":
            continue
        external_id = _dict(activity.get("external_ids")).get("external_id")
        normalized = str(external_id or "").lower()
        if normalized.startswith(("garmin_ping_", "garmin_push_")):
            return True
    return False


def _preferred_sport(activities: list[dict[str, Any]]) -> dict[str, Any]:
    for activity in activities:
        if activity.get("source") == "garmin_connect":
            return _dict(activity.get("sport"))
    return _dict(activities[0].get("sport")) if activities else {}


def _device_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool | None:
    left_devices = _device_tokens(left)
    right_devices = _device_tokens(right)
    if not left_devices or not right_devices:
        return None
    return bool(left_devices & right_devices)


def _device_tokens(activity: dict[str, Any]) -> set[str]:
    gear = _dict(activity.get("gear"))
    metrics = _dict(activity.get("metrics"))
    return {
        str(value).strip().lower()
        for value in (
            gear.get("name"),
            gear.get("source_gear_id"),
            metrics.get("device_name"),
            metrics.get("manufacturer"),
        )
        if value
    }


def _merged_completeness(activities: list[dict[str, Any]]) -> dict[str, bool]:
    merged: dict[str, bool] = {}
    for activity in activities:
        completeness = activity.get("completeness")
        if not isinstance(completeness, dict):
            continue
        for key, value in completeness.items():
            merged[key] = bool(merged.get(key) or value)
    return merged


def _merge_dicts(values: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for value in values:
        if isinstance(value, dict):
            merged.update(value)
    return merged


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
