"""Activity stream domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nono_sports.domain.source import SourceReference


@dataclass(frozen=True)
class NormalizedStream:
    schema_version: str
    stream_uid: str
    activity_uid: str
    source: str
    source_activity_id: str
    streams: dict[str, dict[str, Any]]
    samples: dict[str, int]
    source_reference: SourceReference
