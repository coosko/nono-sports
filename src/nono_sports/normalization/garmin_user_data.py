"""Garmin Connect user profile and equipment normalization."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.domain.athlete import NormalizedAthlete
from nono_sports.domain.equipment import NormalizedEquipment
from nono_sports.domain.source import SourceReference
from nono_sports.normalization.equipment_utils import (
    canonical_equipment_type,
    number,
    optional_str,
)
from nono_sports.storage.incremental import (
    build_file_fingerprint,
    is_incremental_state_current,
    state_counts,
)
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SCHEMA_VERSION_ATHLETE = "nono.normalized_athlete.v1"
SCHEMA_VERSION_EQUIPMENT = "nono.normalized_equipment.v1"
SOURCE = "garmin_connect"
REQUIRED_OUTPUTS = ("athletes.jsonl", "equipment.jsonl", "user_state.json")
FINGERPRINT_PATTERNS = (
    "athlete/*.json",
    "devices/*.json",
    "gear/gear.json",
    "gear/stats/*.json",
)


class GarminUserDataNormalizationResult:
    def __init__(
        self,
        *,
        athletes: int,
        equipment: int,
        written: tuple[SourceNormalizedWriteResult, ...],
        normalized_root: str,
        skipped: bool = False,
    ) -> None:
        self.athletes = athletes
        self.equipment = equipment
        self.written = written
        self.normalized_root = normalized_root
        self.skipped = skipped


def normalize_garmin_user_data(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> GarminUserDataNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    raw_root = garmin_connect_path(data_root, "raw")
    normalized_root = garmin_connect_path(data_root, "normalizado")
    manifest_index = _read_manifest_index(raw_root / "manifest.jsonl")
    store = SourceNormalizedStore(normalized_root)
    previous_state = _read_json(normalized_root / "user_state.json")
    input_fingerprint = _garmin_user_data_fingerprint(raw_root)
    if is_incremental_state_current(
        previous_state,
        input_fingerprint,
        output_root=normalized_root,
        required_outputs=REQUIRED_OUTPUTS,
    ):
        counts = state_counts(previous_state)
        return GarminUserDataNormalizationResult(
            athletes=int(counts.get("athletes") or 0),
            equipment=int(counts.get("equipment") or 0),
            written=(),
            normalized_root=str(normalized_root),
            skipped=True,
        )
    athletes = _normalize_athletes(raw_root, manifest_index)
    equipment = _normalize_equipment(raw_root, manifest_index)
    state = {
        "schema_version": "nono.garmin_connect.user_normalization_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "inputs": {
            "profile": "raw/athlete/profile.json",
            "settings": "raw/athlete/settings.json",
            "gear": "raw/gear/gear.json",
            "devices": "raw/devices/devices.json",
            "input_fingerprint": input_fingerprint,
        },
        "outputs": {
            "athletes": "athletes.jsonl",
            "equipment": "equipment.jsonl",
            "state": "user_state.json",
        },
        "counts": {
            "athletes": len(athletes),
            "equipment": len(equipment),
        },
    }
    written = (
        store.write_jsonl("athletes.jsonl", athletes),
        store.write_jsonl("equipment.jsonl", equipment),
        store.write_json("user_state.json", state),
    )
    return GarminUserDataNormalizationResult(
        athletes=len(athletes),
        equipment=len(equipment),
        written=written,
        normalized_root=str(normalized_root),
    )


def _garmin_user_data_fingerprint(raw_root: Path) -> dict[str, Any]:
    return build_file_fingerprint(
        raw_root,
        FINGERPRINT_PATTERNS,
        manifest_path=raw_root / "manifest.jsonl",
    )


def _normalize_athletes(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> list[NormalizedAthlete]:
    profile_path = raw_root / "athlete" / "profile.json"
    if not profile_path.exists():
        return []
    profile = _dict(_read_json(profile_path))
    settings = _dict(_read_json(raw_root / "athlete" / "settings.json"))
    athlete_id = _first_present(
        profile,
        settings,
        keys=("userProfileId", "userProfilePk", "profileId", "id"),
    )
    if athlete_id is None:
        return []
    reference = _source_reference(
        raw_root,
        profile_path,
        manifest_index,
        entity_type="athlete",
        source_id=str(athlete_id),
    )
    return [
        NormalizedAthlete(
            schema_version=SCHEMA_VERSION_ATHLETE,
            athlete_uid=f"{SOURCE}:athlete:{athlete_id}",
            source=SOURCE,
            source_athlete_id=str(athlete_id),
            display={
                "username": profile.get("userName") or profile.get("username"),
                "firstname": profile.get("firstName"),
                "lastname": profile.get("lastName"),
                "display_name": profile.get("displayName") or profile.get("fullName"),
            },
            profile={
                "sex": profile.get("gender") or profile.get("sex"),
                "country": profile.get("country"),
                "created_at": profile.get("createdDate"),
                "updated_at": profile.get("updatedDate"),
                "birth_date": profile.get("birthDate"),
            },
            physiology={
                "height_cm": number(profile.get("height")),
                "weight_kg": number(profile.get("weight")),
            },
            preferences={
                "measurement_system": settings.get("measurementSystem"),
                "time_format": settings.get("timeFormat"),
                "first_day_of_week": settings.get("firstDayOfWeek"),
            },
            gear={},
            source_reference=reference,
            source_specific={
                "profile_keys": sorted(profile),
                "settings_keys": sorted(settings),
            },
        )
    ]


def _normalize_equipment(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
) -> list[NormalizedEquipment]:
    records: list[NormalizedEquipment] = []
    gear_path = raw_root / "gear" / "gear.json"
    if gear_path.exists():
        gear_reference = _source_reference(
            raw_root,
            gear_path,
            manifest_index,
            entity_type="gear",
            source_id="gear",
        )
        for item in _iter_dicts(_read_json(gear_path)):
            equipment_id = _garmin_equipment_id(item)
            if equipment_id is None:
                continue
            records.append(
                _garmin_equipment_record(
                    item,
                    equipment_id=equipment_id,
                    source_reference=gear_reference,
                    stats=_gear_stats(raw_root, manifest_index, equipment_id),
                )
            )
    devices_path = raw_root / "devices" / "devices.json"
    if devices_path.exists():
        devices_reference = _source_reference(
            raw_root,
            devices_path,
            manifest_index,
            entity_type="devices",
            source_id="devices",
        )
        for item in _iter_dicts(_read_json(devices_path)):
            equipment_id = _garmin_device_id(item)
            if equipment_id is None:
                continue
            records.append(
                _garmin_device_record(
                    item,
                    equipment_id=equipment_id,
                    source_reference=devices_reference,
                )
            )
    return _deduplicate(records)


def _garmin_equipment_record(
    payload: dict[str, Any],
    *,
    equipment_id: str,
    source_reference: SourceReference,
    stats: dict[str, Any],
) -> NormalizedEquipment:
    return NormalizedEquipment(
        schema_version=SCHEMA_VERSION_EQUIPMENT,
        equipment_uid=f"{SOURCE}:equipment:{equipment_id}",
        source=SOURCE,
        source_equipment_id=equipment_id,
        equipment_type=canonical_equipment_type(
            payload.get("gearTypeName")
            or payload.get("gearType")
            or payload.get("type")
            or payload.get("category")
        ),
        name=optional_str(
            payload.get("displayName")
            or payload.get("gearName")
            or payload.get("name")
        ),
        brand=optional_str(payload.get("brandName") or payload.get("manufacturer")),
        model=optional_str(payload.get("modelName") or payload.get("model")),
        description=optional_str(payload.get("description")),
        status=optional_str(payload.get("status")),
        distance_m=number(
            payload.get("totalDistance")
            or payload.get("distance")
            or stats.get("totalDistance")
        ),
        weight_kg=number(payload.get("weight")),
        source_reference=source_reference,
        attributes={
            "stats": stats,
            "source_payload_keys": sorted(payload),
        },
    )


def _garmin_device_record(
    payload: dict[str, Any],
    *,
    equipment_id: str,
    source_reference: SourceReference,
) -> NormalizedEquipment:
    return NormalizedEquipment(
        schema_version=SCHEMA_VERSION_EQUIPMENT,
        equipment_uid=f"{SOURCE}:equipment:device:{equipment_id}",
        source=SOURCE,
        source_equipment_id=str(equipment_id),
        equipment_type="device",
        name=optional_str(
            payload.get("deviceName")
            or payload.get("displayName")
            or payload.get("name")
        ),
        brand=optional_str(payload.get("manufacturer")),
        model=optional_str(payload.get("modelName") or payload.get("deviceModel")),
        description=optional_str(payload.get("description")),
        status=optional_str(payload.get("status")),
        distance_m=None,
        weight_kg=None,
        source_reference=source_reference,
        attributes={
            "device_type": payload.get("deviceType"),
            "device_type_pk": payload.get("deviceTypePk"),
            "serial_number": payload.get("serialNumber"),
            "last_used": payload.get("lastUsedDate"),
            "source_payload_keys": sorted(payload),
        },
    )


def _gear_stats(
    raw_root: Path,
    manifest_index: dict[str, dict[str, Any]],
    equipment_id: str,
) -> dict[str, Any]:
    path = raw_root / "gear" / "stats" / f"{_safe_id(equipment_id)}.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    reference = _source_reference(
        raw_root,
        path,
        manifest_index,
        entity_type="gear_stats",
        source_id=equipment_id,
    )
    return {
        "payload": payload,
        "source_reference": reference,
    }


def _garmin_equipment_id(payload: dict[str, Any]) -> str | None:
    for key in ("gearUuid", "uuid", "gearPk", "id"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    return None


def _garmin_device_id(payload: dict[str, Any]) -> str | None:
    for key in ("deviceId", "unitId", "serialNumber", "id"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    return None


def _deduplicate(records: list[NormalizedEquipment]) -> list[NormalizedEquipment]:
    by_uid = {record.equipment_uid: record for record in records}
    return [by_uid[uid] for uid in sorted(by_uid)]


def _first_present(
    *payloads: dict[str, Any],
    keys: tuple[str, ...],
) -> Any | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value
    return None


def _iter_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        nested = [
            item
            for item in value.values()
            if isinstance(item, list | dict)
        ]
        if _looks_like_item(value):
            return [value]
        found: list[dict[str, Any]] = []
        for item in nested:
            found.extend(_iter_dicts(item))
        return found
    if isinstance(value, list):
        found: list[dict[str, Any]] = []
        for item in value:
            found.extend(_iter_dicts(item))
        return found
    return []


def _looks_like_item(payload: dict[str, Any]) -> bool:
    return bool(
        _garmin_equipment_id(payload)
        or _garmin_device_id(payload)
        or payload.get("displayName")
        or payload.get("deviceName")
    )


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


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in value)
