"""Data manifest models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RawManifestEntry:
    generated_at: str
    kind: str
    endpoint: str
    params: dict[str, Any]
    path: str
    sha256: str
    bytes_written: int
