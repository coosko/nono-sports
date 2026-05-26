"""Source provenance domain models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceReference:
    """Traceability link from a normalized record back to a raw source file."""

    source: str
    entity_type: str
    source_id: str
    raw_path: str
    raw_sha256: str | None = None
    endpoint: str | None = None
    collected_at: str | None = None
