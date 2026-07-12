"""Biometric and point-in-time measurement domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nono_sports.domain.source import SourceReference


@dataclass(frozen=True)
class NormalizedMeasurement:
    schema_version: str
    measurement_uid: str
    source: str
    source_measurement_id: str
    metric: str
    value: float
    unit: str
    measured_at_utc: str | None
    measurement_date: str
    source_reference: SourceReference
    conditions: str | None = None
    notes: str | None = None
    quality: str = "observed"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConsolidatedMeasurement:
    schema_version: str
    consolidated_measurement_uid: str
    metric: str
    value: float
    unit: str
    measured_at_utc: str | None
    measurement_date: str
    primary_source: str
    primary_measurement_uid: str
    source_count: int
    source_measurement_uids: list[str]
    conditions: str | None = None
    notes: str | None = None
    quality: str = "observed"
    provenance: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)
