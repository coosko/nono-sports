"""Consolidate normalized measurements across sources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path, manual_path
from nono_sports.domain.measurement import ConsolidatedMeasurement
from nono_sports.storage.consolidated_store import (
    ConsolidatedStore,
    ConsolidatedWriteResult,
)
from nono_sports.storage.incremental import (
    build_file_fingerprint,
    is_incremental_state_current,
    state_counts,
)

SCHEMA_VERSION = "nono.consolidated_measurement.v1"
SOURCE_LINK_SCHEMA_VERSION = "nono.measurement_source_link.v1"
REQUIRED_OUTPUTS = (
    "measurements.jsonl",
    "measurement_sources.jsonl",
    "measurements_state.json",
)
SOURCE_PRIORITY = {
    "garmin_connect": 1,
    "manual": 2,
}
VALUE_TOLERANCE = {
    "weight": 0.05,
    "resting_heart_rate": 0.5,
    "bmi": 0.05,
    "body_fat": 0.1,
}


@dataclass(frozen=True)
class MeasurementConsolidationResult:
    measurements: int
    measurement_sources: int
    written: tuple[ConsolidatedWriteResult, ...]
    consolidated_root: str
    skipped: bool = False


def build_consolidated_measurements(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> MeasurementConsolidationResult:
    generated_at = generated_at or datetime.now(UTC)
    store = ConsolidatedStore(data_root)
    input_fingerprint = _measurement_consolidation_fingerprint(data_root)
    previous_state = _read_json(store.consolidated_root / "measurements_state.json")
    if is_incremental_state_current(
        previous_state,
        input_fingerprint,
        output_root=store.consolidated_root,
        required_outputs=REQUIRED_OUTPUTS,
    ):
        counts = state_counts(previous_state)
        return MeasurementConsolidationResult(
            measurements=int(counts.get("measurements") or 0),
            measurement_sources=int(counts.get("measurement_sources") or 0),
            written=(),
            consolidated_root=str(store.consolidated_root),
            skipped=True,
        )
    inputs = _load_normalized_measurements(data_root)
    groups = _group_measurements(inputs)
    consolidated = [_consolidated_measurement(group) for group in groups]
    consolidated.sort(
        key=lambda item: (
            item.measurement_date,
            item.measured_at_utc or "",
            item.metric,
            item.consolidated_measurement_uid,
        )
    )
    source_links = [
        link
        for measurement in consolidated
        for link in measurement.provenance.get("source_links", [])
    ]
    state = {
        "schema_version": "nono.measurement_consolidation_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "strategy": "multi_source_measurements_initial",
        "inputs": {
            source: str(path)
            for source, path in _normalized_measurement_paths(data_root).items()
        }
        | {"input_fingerprint": input_fingerprint},
        "outputs": {
            "measurements": "measurements.jsonl",
            "measurement_sources": "measurement_sources.jsonl",
        },
        "counts": {
            "input_measurements": len(inputs),
            "measurements": len(consolidated),
            "measurement_sources": len(source_links),
        },
    }
    written = [
        store.write_jsonl("measurements.jsonl", consolidated),
        store.write_jsonl("measurement_sources.jsonl", source_links),
        store.write_json("measurements_state.json", state),
    ]
    return MeasurementConsolidationResult(
        measurements=len(consolidated),
        measurement_sources=len(source_links),
        written=tuple(written),
        consolidated_root=str(store.consolidated_root),
    )


def _measurement_consolidation_fingerprint(data_root: Path) -> dict[str, Any]:
    paths = _normalized_measurement_paths(data_root).values()
    return build_file_fingerprint(
        data_root,
        (path.relative_to(data_root).as_posix() for path in paths),
    )


def _load_normalized_measurements(data_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _normalized_measurement_paths(data_root).values():
        records.extend(_read_jsonl(path))
    return records


def _normalized_measurement_paths(data_root: Path) -> dict[str, Path]:
    return {
        "garmin_connect": garmin_connect_path(
            data_root,
            "normalizado",
            "measurements.jsonl",
        ),
        "manual": manual_path(data_root, "normalizado", "measurements.jsonl"),
    }


def _group_measurements(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    for record in sorted(records, key=_sort_key):
        for group in groups:
            if _same_measurement(record, group[0]):
                group.append(record)
                break
        else:
            groups.append([record])
    return groups


def _same_measurement(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("metric") != right.get("metric"):
        return False
    if left.get("unit") != right.get("unit"):
        return False
    if left.get("measurement_date") != right.get("measurement_date"):
        return False
    left_value = _float(left.get("value"))
    right_value = _float(right.get("value"))
    if left_value is None or right_value is None:
        return False
    tolerance = VALUE_TOLERANCE.get(str(left.get("metric")), 0.0001)
    return abs(left_value - right_value) <= tolerance


def _consolidated_measurement(group: list[dict[str, Any]]) -> ConsolidatedMeasurement:
    ordered = sorted(group, key=_source_priority)
    primary = ordered[0]
    source_links = [
        _source_link(record, index + 1)
        for index, record in enumerate(ordered)
    ]
    primary_uid = str(primary.get("measurement_uid"))
    consolidated_uid = f"consolidated:measurement:{primary_uid}"
    return ConsolidatedMeasurement(
        schema_version=SCHEMA_VERSION,
        consolidated_measurement_uid=consolidated_uid,
        metric=str(primary.get("metric")),
        value=float(primary.get("value")),
        unit=str(primary.get("unit")),
        measured_at_utc=primary.get("measured_at_utc"),
        measurement_date=str(primary.get("measurement_date")),
        primary_source=str(primary.get("source")),
        primary_measurement_uid=primary_uid,
        source_count=len(ordered),
        source_measurement_uids=[
            str(record.get("measurement_uid")) for record in ordered
        ],
        conditions=primary.get("conditions"),
        notes=primary.get("notes"),
        quality=str(primary.get("quality") or "observed"),
        provenance={
            "strategy": "multi_source_measurements_initial",
            "source_links": source_links,
        },
        attributes=(
            primary.get("attributes")
            if isinstance(primary.get("attributes"), dict)
            else {}
        ),
    )


def _source_link(record: dict[str, Any], priority: int) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_LINK_SCHEMA_VERSION,
        "source": record.get("source"),
        "measurement_uid": record.get("measurement_uid"),
        "source_measurement_id": record.get("source_measurement_id"),
        "source_priority": priority,
        "source_reference": record.get("source_reference") or {},
    }


def _source_priority(record: dict[str, Any]) -> tuple[int, str]:
    return (
        SOURCE_PRIORITY.get(str(record.get("source") or ""), 99),
        str(record.get("measurement_uid") or ""),
    )


def _sort_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(record.get("measurement_date") or ""),
        str(record.get("measured_at_utc") or ""),
        str(record.get("metric") or ""),
        str(record.get("measurement_uid") or ""),
    )


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
