from __future__ import annotations

from typing import Any


class DataIntegrator:
    """Integra datos de distintos orígenes en un único modelo."""

    @staticmethod
    def merge_sources(*sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        for source in sources:
            merged.extend(source)
        return merged

    @staticmethod
    def deduplicate_by_id(dataset: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for record in dataset:
            record_id = str(record.get("id"))
            if record_id and record_id not in seen:
                seen.add(record_id)
                unique.append(record)
        return unique
