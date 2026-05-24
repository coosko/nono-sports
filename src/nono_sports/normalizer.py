from __future__ import annotations

from typing import Any


class DataNormalizer:
    """Normalizador de datos de actividad deportiva."""

    @staticmethod
    def normalize_activity(activity: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": activity.get("id"),
            "name": activity.get("name"),
            "distance_m": activity.get("distance"),
            "elapsed_time_s": activity.get("elapsed_time"),
            "start_date": activity.get("start_date"),
            "type": activity.get("type"),
        }

    @staticmethod
    def normalize_activities(activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [DataNormalizer.normalize_activity(item) for item in activities]
