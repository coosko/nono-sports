"""Activity domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nono_sports.domain.source import SourceReference


@dataclass(frozen=True)
class NormalizedLap:
    lap_uid: str
    source_lap_id: str | None
    index: int | None
    name: str | None
    start_at_utc: str | None
    start_at_local: str | None
    distance_m: float | None
    moving_time_s: int | None
    elapsed_time_s: int | None
    elevation_gain_m: float | None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedSegmentReference:
    segment_uid: str
    source_segment_id: str
    name: str | None
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    source_reference: SourceReference | None = None


@dataclass(frozen=True)
class NormalizedActivity:
    """Source-agnostic activity record prepared for later consolidation."""

    schema_version: str
    activity_uid: str
    source: str
    source_activity_id: str
    athlete_uid: str | None
    title: str | None
    description: str | None
    sport: dict[str, Any]
    start: dict[str, Any]
    duration: dict[str, Any]
    distance: dict[str, Any]
    elevation: dict[str, Any]
    energy: dict[str, Any]
    metrics: dict[str, Any]
    location: dict[str, Any]
    gear: dict[str, Any]
    flags: dict[str, Any]
    completeness: dict[str, bool]
    laps: list[NormalizedLap]
    segments: list[NormalizedSegmentReference]
    stream_uid: str | None
    source_reference: SourceReference
    source_links: list[SourceReference] = field(default_factory=list)
    external_ids: dict[str, Any] = field(default_factory=dict)
    sport_specific: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActivitySourceLink:
    """Link between one consolidated activity and one source activity."""

    schema_version: str
    consolidated_activity_uid: str
    source: str
    source_activity_uid: str
    normalized_activity_uid: str
    source_priority: int
    match_strategy: str
    match_confidence: float
    source_reference: dict[str, Any]


@dataclass(frozen=True)
class ConsolidatedActivity:
    """Single activity view intended as the primary input for Nono."""

    schema_version: str
    consolidated_activity_uid: str
    primary_source: str
    primary_activity_uid: str
    title: str | None
    description: str | None
    sport: dict[str, Any]
    start: dict[str, Any]
    duration: dict[str, Any]
    distance: dict[str, Any]
    elevation: dict[str, Any]
    energy: dict[str, Any]
    metrics: dict[str, Any]
    location: dict[str, Any]
    gear: dict[str, Any]
    flags: dict[str, Any]
    completeness: dict[str, bool]
    laps: list[dict[str, Any]]
    segments: list[dict[str, Any]]
    stream_uid: str | None
    source_count: int
    source_activity_uids: list[str]
    provenance: dict[str, Any]
    external_ids: dict[str, Any] = field(default_factory=dict)
    sport_specific: dict[str, Any] = field(default_factory=dict)
