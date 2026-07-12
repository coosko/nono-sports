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
    consolidated_equipment = [
        _consolidated_equipment(group) for group in equipment_groups
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


def _consolidated_equipment(group: list[dict[str, Any]]) -> ConsolidatedEquipment:
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
        distance_m=_first_number("distance_m", ordered),
        weight_kg=_first_number("weight_kg", ordered),
        source_count=len(ordered),
        source_equipment_uids=[
            item.get("equipment_uid")
            for item in ordered
            if item.get("equipment_uid") is not None
        ],
        provenance={"source_links": source_links},
        attributes={"source_attributes": _source_attributes(ordered)},
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
        },
        "manual": {
            "athletes": manual_path(data_root, "normalizado", "athletes.jsonl"),
            "equipment": manual_path(data_root, "normalizado", "equipment.jsonl"),
        },
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


def _normalize_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", value)
