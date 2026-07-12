"""Shared equipment normalization helpers."""

from __future__ import annotations

from typing import Any


def number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def canonical_equipment_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"bike", "bikes", "bicycle", "cycling"}:
        return "bike"
    if text in {"shoe", "shoes", "running_shoes"}:
        return "shoes"
    if text in {"device", "watch", "sensor"}:
        return "device"
    return text.replace(" ", "_") or "unknown"
