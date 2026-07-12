"""Equipment domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nono_sports.domain.source import SourceReference


@dataclass(frozen=True)
class NormalizedEquipment:
    schema_version: str
    equipment_uid: str
    source: str
    source_equipment_id: str
    equipment_type: str
    name: str | None
    brand: str | None
    model: str | None
    description: str | None
    status: str | None
    distance_m: float | None
    weight_kg: float | None
    source_reference: SourceReference
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConsolidatedEquipment:
    schema_version: str
    consolidated_equipment_uid: str
    primary_source: str
    primary_equipment_uid: str
    equipment_type: str
    name: str | None
    brand: str | None
    model: str | None
    description: str | None
    status: str | None
    distance_m: float | None
    weight_kg: float | None
    source_count: int
    source_equipment_uids: list[str]
    provenance: dict[str, Any]
    attributes: dict[str, Any] = field(default_factory=dict)
