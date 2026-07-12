"""Strava equipment normalization."""

from __future__ import annotations

from typing import Any

from nono_sports.domain.equipment import NormalizedEquipment
from nono_sports.domain.source import SourceReference
from nono_sports.normalization.equipment_utils import (
    canonical_equipment_type,
    number,
    optional_str,
)

SCHEMA_VERSION = "nono.normalized_equipment.v1"
SOURCE = "strava"


def normalize_strava_equipment(
    payload: dict[str, Any],
    *,
    source_reference: SourceReference,
    fallback_type: str | None = None,
) -> NormalizedEquipment:
    equipment_id = _equipment_id(payload)
    equipment_type = canonical_equipment_type(
        payload.get("resource_state_type")
        or payload.get("type")
        or payload.get("frame_type")
        or fallback_type
    )
    return NormalizedEquipment(
        schema_version=SCHEMA_VERSION,
        equipment_uid=f"{SOURCE}:equipment:{equipment_id}",
        source=SOURCE,
        source_equipment_id=equipment_id,
        equipment_type=equipment_type,
        name=optional_str(payload.get("name")),
        brand=optional_str(payload.get("brand_name")),
        model=optional_str(payload.get("model_name")),
        description=optional_str(payload.get("description")),
        status=_status(payload),
        distance_m=number(payload.get("distance")),
        weight_kg=number(payload.get("weight")),
        source_reference=source_reference,
        attributes={
            "primary": payload.get("primary"),
            "retired": payload.get("retired"),
            "frame_type": payload.get("frame_type"),
            "source_payload_keys": sorted(payload),
        },
    )


def _equipment_id(payload: dict[str, Any]) -> str:
    for key in ("id", "gear_id"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    raise ValueError("Missing Strava equipment id.")


def _status(payload: dict[str, Any]) -> str | None:
    if payload.get("retired") is True:
        return "retired"
    if payload.get("primary") is True:
        return "primary"
    return None
