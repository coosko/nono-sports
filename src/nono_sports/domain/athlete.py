"""Athlete domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nono_sports.domain.source import SourceReference


@dataclass(frozen=True)
class NormalizedAthlete:
    schema_version: str
    athlete_uid: str
    source: str
    source_athlete_id: str
    display: dict[str, Any]
    profile: dict[str, Any]
    physiology: dict[str, Any]
    preferences: dict[str, Any]
    gear: dict[str, Any]
    source_reference: SourceReference
    source_specific: dict[str, Any] = field(default_factory=dict)
