"""Consolidate multi-source athlete profile and equipment data."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path, manual_path, strava_path
from nono_sports.domain.equipment import ConsolidatedEquipment
from nono_sports.storage.consolidated_store import (
    ConsolidatedStore,
    ConsolidatedWriteResult,
)

SCHEMA_VERSION_ATHLETE = "nono.consolidated_athlete.v1"
SCHEMA_VERSION_ATHLETE_SOURCE = "nono.athlete_source_link.v1"
SCHEMA_VERSION_EQUIPMENT_SOURCE = "nono.equipment_source_link.v1"
EQUIPMENT_USAGE_STRATEGY = "activity_source_links_deduplicated_v1"

SOURCE_PRIORITY = {
    "manual": 1,
    "garmin_connect": 2,
    "strava": 3,
}


@dataclass(frozen=True)
class UserDataConsolidationResult:
    athletes: int
    athlete_sources: int
    equipment: int
    equipment_sources: int
    written: tuple[ConsolidatedWriteResult, ...]
    consolidated_root: str


def build_consolidated_user_data(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> UserDataConsolidationResult:
    generated_at = generated_at or datetime.now(UTC)
    athletes = _load_records(_normalized_path(data_root, "athletes.jsonl"))
    equipment = _load_records(_normalized_path(data_root, "equipment.jsonl"))
    consolidated_athletes = _consolidated_athletes(athletes)
    athlete_sources = _athlete_source_links(consolidated_athletes)
    equipment_groups = _group_equipment(equipment)
    activity_usage_context = _load_activity_usage_context(data_root)
    consolidated_equipment = [
        _consolidated_equipment(group, activity_usage_context)
        for group in equipment_groups
    ]
    consolidated_equipment.sort(
        key=lambda item: (
            item.equipment_type,
            _normalize_name(item.name),
            item.consolidated_equipment_uid,
        )
    )
    equipment_sources = [
        link
        for item in consolidated_equipment
        for link in item.provenance.get("source_links", [])
    ]
    state = {
        "schema_version": "nono.user_data_consolidation_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "strategy": "athlete_single_identity_and_equipment_type_name",
        "inputs": {
            source: {
                "athletes": str(paths["athletes"]),
                "equipment": str(paths["equipment"]),
                "activities": str(paths["activities"]),
            }
            for source, paths in _normalized_paths(data_root).items()
        },
        "outputs": {
            "athletes": "athletes.jsonl",
            "athlete_sources": "athlete_sources.jsonl",
            "equipment": "equipment.jsonl",
            "equipment_sources": "equipment_sources.jsonl",
            "state": "user_data_state.json",
        },
        "counts": {
            "athletes": len(consolidated_athletes),
            "athlete_sources": len(athlete_sources),
            "equipment": len(consolidated_equipment),
            "equipment_sources": len(equipment_sources),
            "input_athletes": len(athletes),
            "input_equipment": len(equipment),
            "input_consolidated_activities": len(
                activity_usage_context["consolidated_activities"]
            ),
            "input_source_activities": len(activity_usage_context["source_activities"]),
        },
    }
    store = ConsolidatedStore(data_root)
    written = (
        store.write_jsonl("athletes.jsonl", consolidated_athletes),
        store.write_jsonl("athlete_sources.jsonl", athlete_sources),
        store.write_jsonl("equipment.jsonl", consolidated_equipment),
        store.write_jsonl("equipment_sources.jsonl", equipment_sources),
        store.write_json("user_data_state.json", state),
    )
    return UserDataConsolidationResult(
        athletes=len(consolidated_athletes),
        athlete_sources=len(athlete_sources),
        equipment=len(consolidated_equipment),
        equipment_sources=len(equipment_sources),
        written=written,
        consolidated_root=str(store.consolidated_root),
    )


def _consolidated_athletes(athletes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not athletes:
        return []
    ordered = sorted(athletes, key=_source_priority)
    primary = ordered[0]
    source_links = [
        {
            "schema_version": SCHEMA_VERSION_ATHLETE_SOURCE,
            "consolidated_athlete_uid": "consolidated:athlete:primary",
            "source": source.get("source"),
            "source_athlete_id": source.get("source_athlete_id"),
            "athlete_uid": source.get("athlete_uid"),
            "source_reference": source.get("source_reference"),
        }
        for source in ordered
    ]
    return [
        {
            "schema_version": SCHEMA_VERSION_ATHLETE,
            "consolidated_athlete_uid": "consolidated:athlete:primary",
            "primary_source": primary.get("source"),
            "primary_athlete_uid": primary.get("athlete_uid"),
            "display": _merge_dicts("display", ordered),
            "profile": _merge_dicts("profile", ordered),
            "physiology": _merge_dicts("physiology", ordered),
            "preferences": _merge_dicts("preferences", ordered),
            "source_count": len(ordered),
            "source_athlete_uids": [
                item.get("athlete_uid")
                for item in ordered
                if item.get("athlete_uid") is not None
            ],
            "provenance": {"source_links": source_links},
        }
    ]


def _athlete_source_links(athletes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        link
        for athlete in athletes
        for link in athlete.get("provenance", {}).get("source_links", [])
    ]


def _group_equipment(equipment: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in equipment:
        equipment_type = str(item.get("equipment_type") or "unknown")
        name_key = _normalize_name(item.get("name")) or str(
            item.get("source_equipment_id") or item.get("equipment_uid")
        )
        groups.setdefault((equipment_type, name_key), []).append(item)
    return list(groups.values())


def _consolidated_equipment(
    group: list[dict[str, Any]],
    activity_usage_context: dict[str, Any],
) -> ConsolidatedEquipment:
    ordered = sorted(group, key=_source_priority)
    primary = ordered[0]
    primary_uid = str(primary.get("equipment_uid") or "unknown")
    consolidated_uid = f"consolidated:equipment:{_safe_key(primary_uid)}"
    source_links = [
        {
            "schema_version": SCHEMA_VERSION_EQUIPMENT_SOURCE,
            "consolidated_equipment_uid": consolidated_uid,
            "source": item.get("source"),
            "source_equipment_id": item.get("source_equipment_id"),
            "equipment_uid": item.get("equipment_uid"),
            "source_reference": item.get("source_reference"),
        }
        for item in ordered
    ]
    base_distance = _base_distance(ordered)
    usage = _effective_equipment_usage(ordered, activity_usage_context)
    distance_m = (
        usage["distance_m"]
        if usage["activity_count"] > 0 and usage["distance_m"] is not None
        else base_distance.get("distance_m")
    )
    return ConsolidatedEquipment(
        schema_version="nono.consolidated_equipment.v1",
        consolidated_equipment_uid=consolidated_uid,
        primary_source=str(primary.get("source") or "unknown"),
        primary_equipment_uid=primary_uid,
        equipment_type=str(primary.get("equipment_type") or "unknown"),
        name=_first_text("name", ordered),
        brand=_first_text("brand", ordered),
        model=_first_text("model", ordered),
        description=_first_text("description", ordered),
        status=_first_text("status", ordered),
        distance_m=distance_m,
        weight_kg=_first_number("weight_kg", ordered),
        source_count=len(ordered),
        source_equipment_uids=[
            item.get("equipment_uid")
            for item in ordered
            if item.get("equipment_uid") is not None
        ],
        provenance={"source_links": source_links},
        attributes={
            "source_attributes": _source_attributes(ordered),
            "usage": usage | {"base_distance": base_distance},
        },
    )


def _merge_dicts(key: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for record in reversed(records):
        payload = record.get(key)
        if isinstance(payload, dict):
            merged.update({item_key: item for item_key, item in payload.items()})
    return {item_key: item for item_key, item in merged.items() if item is not None}


def _first_text(key: str, records: list[dict[str, Any]]) -> str | None:
    for record in records:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_number(key: str, records: list[dict[str, Any]]) -> float | None:
    for record in records:
        value = record.get(key)
        if isinstance(value, int | float):
            return float(value)
    return None


def _source_attributes(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(record.get("equipment_uid")): record.get("attributes", {})
        for record in records
        if record.get("equipment_uid") is not None
    }


def _base_distance(records: list[dict[str, Any]]) -> dict[str, Any]:
    for record in records:
        value = record.get("distance_m")
        if isinstance(value, int | float):
            return {
                "source": record.get("source"),
                "equipment_uid": record.get("equipment_uid"),
                "distance_m": float(value),
            }
    return {}


def _load_activity_usage_context(data_root: Path) -> dict[str, Any]:
    consolidated_activities = [
        _slim_consolidated_activity(activity)
        for activity in _iter_jsonl(data_root / "20_consolidado" / "activities.jsonl")
    ]
    source_activities: dict[str, dict[str, Any]] = {}
    for path in _normalized_path(data_root, "activities.jsonl").values():
        for activity in _iter_jsonl(path):
            activity_uid = activity.get("activity_uid")
            if activity_uid is not None:
                source_activities[str(activity_uid)] = _slim_source_activity(activity)
    return {
        "consolidated_activities": consolidated_activities,
        "source_activities": source_activities,
    }


def _slim_consolidated_activity(activity: dict[str, Any]) -> dict[str, Any]:
    source_links = activity.get("provenance", {}).get("source_links", [])
    return {
        "consolidated_activity_uid": activity.get("consolidated_activity_uid"),
        "source_activity_uids": activity.get("source_activity_uids", []),
        "provenance": {
            "source_links": source_links if isinstance(source_links, list) else []
        },
    }


def _slim_source_activity(activity: dict[str, Any]) -> dict[str, Any]:
    return {
        "activity_uid": activity.get("activity_uid"),
        "source": activity.get("source"),
        "distance": _dict(activity.get("distance")),
        "duration": _dict(activity.get("duration")),
        "gear": _dict(activity.get("gear")),
    }


def _effective_equipment_usage(
    equipment_group: list[dict[str, Any]],
    activity_usage_context: dict[str, Any],
) -> dict[str, Any]:
    source_equipment_uids = {
        str(item.get("equipment_uid"))
        for item in equipment_group
        if item.get("equipment_uid") is not None
    }
    missing_keys = {
        key
        for uid in source_equipment_uids
        for key in _equipment_missing_keys(uid)
    }
    source_activities = activity_usage_context["source_activities"]
    partials: dict[str, dict[str, Any]] = {}
    totals = {
        "distance_m": 0.0,
        "moving_time_s": 0.0,
        "elapsed_time_s": 0.0,
    }
    has_distance = False
    has_moving_time = False
    has_elapsed_time = False
    activity_count = 0
    unassignable_activity_count = 0
    unassignable_examples: list[dict[str, Any]] = []

    for consolidated_activity in activity_usage_context["consolidated_activities"]:
        source_links = _ordered_source_links(consolidated_activity)
        matched = False
        missing_for_equipment = False
        for source_link in source_links:
            activity_uid = source_link.get("activity_uid")
            if activity_uid is None:
                continue
            source_activity = source_activities.get(str(activity_uid))
            if source_activity is None:
                continue
            activity_equipment = _activity_equipment_usage(source_activity)
            if activity_equipment["equipment_uids"] & source_equipment_uids:
                _add_activity_usage(
                    partials,
                    totals,
                    source_activity,
                    source_link,
                    activity_equipment["equipment_uids"] & source_equipment_uids,
                )
                has_distance = has_distance or _number_from_mapping(
                    source_activity.get("distance"),
                    "distance_m",
                ) is not None
                has_moving_time = has_moving_time or _number_from_mapping(
                    source_activity.get("duration"),
                    "moving_time_s",
                ) is not None
                has_elapsed_time = has_elapsed_time or _number_from_mapping(
                    source_activity.get("duration"),
                    "elapsed_time_s",
                ) is not None
                activity_count += 1
                matched = True
                break
            if activity_equipment["missing_keys"] & missing_keys:
                missing_for_equipment = True
        if not matched and missing_for_equipment:
            unassignable_activity_count += 1
            if len(unassignable_examples) < 10:
                unassignable_examples.append(
                    {
                        "consolidated_activity_uid": consolidated_activity.get(
                            "consolidated_activity_uid"
                        ),
                        "source_activity_uids": consolidated_activity.get(
                            "source_activity_uids",
                            [],
                        ),
                    }
                )

    partial_distance_m = [
        {
            "source": source,
            "distance_m": partial.get("distance_m"),
            "moving_time_s": partial.get("moving_time_s"),
            "elapsed_time_s": partial.get("elapsed_time_s"),
            "activity_count": partial["activity_count"],
        }
        for source, partial in sorted(partials.items())
    ]
    return {
        "strategy": EQUIPMENT_USAGE_STRATEGY,
        "distance_strategy": (
            "sum_source_activity_distance_once_per_consolidated_activity"
        ),
        "distance_m": totals["distance_m"] if has_distance else None,
        "moving_time_s": totals["moving_time_s"] if has_moving_time else None,
        "moving_time_h": _hours(totals["moving_time_s"]) if has_moving_time else None,
        "elapsed_time_s": totals["elapsed_time_s"] if has_elapsed_time else None,
        "elapsed_time_h": (
            _hours(totals["elapsed_time_s"]) if has_elapsed_time else None
        ),
        "activity_count": activity_count,
        "partial_distance_m": partial_distance_m,
        "unassignable_activity_count": unassignable_activity_count,
        "unassignable_activity_examples": unassignable_examples,
    }


def _ordered_source_links(
    consolidated_activity: dict[str, Any],
) -> list[dict[str, Any]]:
    source_links = consolidated_activity.get("provenance", {}).get("source_links", [])
    if not isinstance(source_links, list):
        return []
    return sorted(
        [link for link in source_links if isinstance(link, dict)],
        key=lambda link: int(link.get("source_priority") or 99),
    )


def _activity_equipment_usage(activity: dict[str, Any]) -> dict[str, set[str]]:
    source = str(activity.get("source") or "")
    gear = _dict(activity.get("gear"))
    equipment_uids: set[str] = set()
    missing_keys: set[str] = set()
    if source == "strava":
        source_gear_id = _text(
            gear.get("source_gear_id") or gear.get("gear_id") or gear.get("id")
        )
        if source_gear_id:
            equipment_uids.add(f"strava:equipment:{source_gear_id}")
        else:
            missing_keys.add("strava:equipment")
    elif source == "garmin_connect":
        gear_ids = _garmin_activity_gear_ids(gear.get("activity_gear"))
        equipment_uids.update(
            f"garmin_connect:equipment:{gear_id}" for gear_id in gear_ids
        )
        if not gear_ids:
            missing_keys.add("garmin_connect:equipment")
        device_id = _text(gear.get("device_id"))
        if device_id:
            equipment_uids.add(f"garmin_connect:equipment:device:{device_id}")
        else:
            missing_keys.add("garmin_connect:equipment:device")
    return {"equipment_uids": equipment_uids, "missing_keys": missing_keys}


def _garmin_activity_gear_ids(payload: Any) -> set[str]:
    ids: set[str] = set()
    for item in _iter_payload_dicts(payload):
        for key in ("gearUuid", "uuid", "gearPk"):
            value = _text(item.get(key))
            if value:
                ids.add(value)
        if any(key in item for key in ("gearName", "gearTypeName", "displayName")):
            value = _text(item.get("id"))
            if value:
                ids.add(value)
    return ids


def _iter_payload_dicts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = [payload]
        for value in payload.values():
            items.extend(_iter_payload_dicts(value))
        return items
    if isinstance(payload, list):
        items: list[dict[str, Any]] = []
        for value in payload:
            items.extend(_iter_payload_dicts(value))
        return items
    return []


def _equipment_missing_keys(equipment_uid: str) -> set[str]:
    if equipment_uid.startswith("garmin_connect:equipment:device:"):
        return {"garmin_connect:equipment:device"}
    if equipment_uid.startswith("garmin_connect:equipment:"):
        return {"garmin_connect:equipment"}
    if equipment_uid.startswith("strava:equipment:"):
        return {"strava:equipment"}
    return set()


def _add_activity_usage(
    partials: dict[str, dict[str, Any]],
    totals: dict[str, float],
    source_activity: dict[str, Any],
    source_link: dict[str, Any],
    matched_equipment_uids: set[str],
) -> None:
    source = str(
        source_activity.get("source") or source_link.get("source") or "unknown"
    )
    partial = partials.setdefault(
        source,
        {
            "distance_m": 0.0,
            "moving_time_s": 0.0,
            "elapsed_time_s": 0.0,
            "activity_count": 0,
            "matched_equipment_uids": set(),
        },
    )
    distance_m = _number_from_mapping(source_activity.get("distance"), "distance_m")
    moving_time_s = _number_from_mapping(
        source_activity.get("duration"),
        "moving_time_s",
    )
    elapsed_time_s = _number_from_mapping(
        source_activity.get("duration"),
        "elapsed_time_s",
    )
    if distance_m is not None:
        totals["distance_m"] += distance_m
        partial["distance_m"] += distance_m
    if moving_time_s is not None:
        totals["moving_time_s"] += moving_time_s
        partial["moving_time_s"] += moving_time_s
    if elapsed_time_s is not None:
        totals["elapsed_time_s"] += elapsed_time_s
        partial["elapsed_time_s"] += elapsed_time_s
    partial["activity_count"] += 1
    partial["matched_equipment_uids"].update(matched_equipment_uids)


def _number_from_mapping(payload: Any, key: str) -> float | None:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, int | float):
            return float(value)
    return None


def _hours(seconds: float) -> float:
    return round(seconds / 3600, 4)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int | float):
        return str(value)
    return None


def _source_priority(record: dict[str, Any]) -> tuple[int, str]:
    source = str(record.get("source") or "")
    uid = str(
        record.get("equipment_uid")
        or record.get("athlete_uid")
        or record.get("source_equipment_id")
        or ""
    )
    return (SOURCE_PRIORITY.get(source, 100), uid)


def _load_records(paths_by_source: dict[str, Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths_by_source.values():
        records.extend(_read_jsonl(path))
    return records


def _normalized_path(data_root: Path, filename: str) -> dict[str, Path]:
    return {
        source: paths[filename.removesuffix(".jsonl")]
        for source, paths in _normalized_paths(data_root).items()
    }


def _normalized_paths(data_root: Path) -> dict[str, dict[str, Path]]:
    return {
        "strava": {
            "athletes": strava_path(data_root, "normalizado", "athletes.jsonl"),
            "equipment": strava_path(data_root, "normalizado", "equipment.jsonl"),
            "activities": strava_path(data_root, "normalizado", "activities.jsonl"),
        },
        "garmin_connect": {
            "athletes": garmin_connect_path(
                data_root,
                "normalizado",
                "athletes.jsonl",
            ),
            "equipment": garmin_connect_path(
                data_root,
                "normalizado",
                "equipment.jsonl",
            ),
            "activities": garmin_connect_path(
                data_root,
                "normalizado",
                "activities.jsonl",
            ),
        },
        "manual": {
            "athletes": manual_path(data_root, "normalizado", "athletes.jsonl"),
            "equipment": manual_path(data_root, "normalizado", "equipment.jsonl"),
            "activities": manual_path(data_root, "normalizado", "activities.jsonl"),
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return list(_iter_jsonl(path))


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                yield payload


def _normalize_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", value)
