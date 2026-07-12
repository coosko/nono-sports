"""Shared helpers for normalized measurements."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any


def stable_measurement_id(*parts: Any) -> str:
    raw = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def normalize_utc_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def date_from_timestamp_or_date(timestamp: str | None, fallback_date: Any) -> str:
    if timestamp:
        return timestamp[:10]
    return str(fallback_date or "")[:10]


def canonical_metric(value: Any) -> str:
    text = str(value or "").strip().lower()
    return {
        "peso": "weight",
        "weight_kg": "weight",
        "resting_hr": "resting_heart_rate",
        "rhr": "resting_heart_rate",
        "fc_reposo": "resting_heart_rate",
        "frecuencia cardiaca en reposo": "resting_heart_rate",
    }.get(text, text.replace(" ", "_"))


def canonical_unit(metric: str, unit: Any) -> str:
    text = str(unit or "").strip()
    if text:
        return text
    return {
        "weight": "kg",
        "resting_heart_rate": "bpm",
        "body_fat": "%",
        "bmi": "kg/m2",
    }.get(metric, "")
