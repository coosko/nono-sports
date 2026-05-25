"""Strava rate-limit handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RateLimitPair:
    fifteen_minutes: int
    daily: int

    @classmethod
    def parse(cls, value: str | None) -> "RateLimitPair | None":
        if not value:
            return None
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 2:
            return None
        try:
            return cls(fifteen_minutes=int(parts[0]), daily=int(parts[1]))
        except ValueError:
            return None


@dataclass(frozen=True)
class RateLimitSnapshot:
    overall_limit: RateLimitPair | None
    overall_usage: RateLimitPair | None
    read_limit: RateLimitPair | None
    read_usage: RateLimitPair | None

    @classmethod
    def from_headers(
        cls,
        headers: Mapping[str, str],
    ) -> "RateLimitSnapshot | None":
        snapshot = cls(
            overall_limit=RateLimitPair.parse(headers.get("X-RateLimit-Limit")),
            overall_usage=RateLimitPair.parse(headers.get("X-RateLimit-Usage")),
            read_limit=RateLimitPair.parse(headers.get("X-ReadRateLimit-Limit")),
            read_usage=RateLimitPair.parse(headers.get("X-ReadRateLimit-Usage")),
        )
        if not any(
            (
                snapshot.overall_limit,
                snapshot.overall_usage,
                snapshot.read_limit,
                snapshot.read_usage,
            )
        ):
            return None
        return snapshot
