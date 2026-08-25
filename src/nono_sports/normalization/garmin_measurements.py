"""Normalize Garmin Connect biometric measurements."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.domain.measurement import NormalizedMeasurement
from nono_sports.domain.source import SourceReference
from nono_sports.normalization.measurement_utils import (
    date_from_timestamp_or_date,
    normalize_utc_timestamp,
    stable_measurement_id,
)
from nono_sports.storage.incremental import (
    build_file_fingerprint,
    is_incremental_state_current,
    state_counts,
)
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SOURCE = "garmin_connect"
SCHEMA_VERSION = "nono.normalized_measurement.v1"
REQUIRED_OUTPUTS = ("measurements.jsonl", "measurements_state.json")
FINGERPRINT_PATTERNS = ("biometrics/*.json",)

GARMIN_METRIC_FIELDS = {
    "weight": ("weight", "kg"),
    "bmi": ("bmi", "kg/m2"),
    "bodyFat": ("body_fat", "%"),
    "bodyFatPercent": ("body_fat", "%"),
    "bodyWater": ("body_water", "%"),
    "bodyWaterPercent": ("body_water", "%"),
    "boneMass": ("bone_mass", "kg"),
    "muscleMass": ("muscle_mass", "kg"),
    "skeletalMuscleMass": ("skeletal_muscle_mass", "kg"),
    "visceralFat": ("visceral_fat", "rating"),
    "visceralFatRating": ("visceral_fat", "rating"),
}


@dataclass(frozen=True)
class GarminMeasurementNormalizationResult:
    measurements: int
    written: tuple[SourceNormalizedWriteResult, ...]
    normalized_root: str
    skipped: bool = False


def normalize_garmin_measurements(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> GarminMeasurementNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    raw_root = garmin_connect_path(data_root, "raw")
    normalized_root = garmin_connect_path(data_root, "normalizado")
    store = SourceNormalizedStore(normalized_root)
    previous_state = _read_optional_json(normalized_root / "measurements_state.json")
    input_fingerprint = _garmin_measurements_fingerprint(raw_root)
    if is_incremental_state_current(
        previous_state,
        input_fingerprint,
        output_root=normalized_root,
        required_outputs=REQUIRED_OUTPUTS,
    ):
        counts = state_counts(previous_state)
        return GarminMeasurementNormalizationResult(
            measurements=int(counts.get("measurements") or 0),
            written=(),
            normalized_root=str(normalized_root),
            skipped=True,
        )
    measurements = _normalize_raw_measurements(raw_root)
    measurements.sort(
        key=lambda item: (
            item.measurement_date,
            item.measured_at_utc or "",
            item.metric,
            item.measurement_uid,
        )
    )
    state = {
        "schema_version": "nono.garmin_connect.measurements_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "inputs": {
            "raw_root": str(raw_root),
            "biometrics": str(raw_root / "biometrics"),
            "input_fingerprint": input_fingerprint,
        },
        "outputs": {
            "measurements": "measurements.jsonl",
        },
        "counts": {
            "measurements": len(measurements),
        },
    }
    written = [
        store.write_jsonl("measurements.jsonl", measurements),
        store.write_json("measurements_state.json", state),
    ]
    return GarminMeasurementNormalizationResult(
        measurements=len(measurements),
        written=tuple(written),
        normalized_root=str(normalized_root),
    )


def _garmin_measurements_fingerprint(raw_root: Path) -> dict[str, Any]:
    return build_file_fingerprint(
        raw_root,
        FINGERPRINT_PATTERNS,
        manifest_path=raw_root / "manifest.jsonl",
    )


def _normalize_raw_measurements(raw_root: Path) -> list[NormalizedMeasurement]:
    seen: set[tuple[str, str, str, float]] = set()
    records: list[NormalizedMeasurement] = []
    for path in sorted((raw_root / "biometrics").glob("*.json")):
        payload = _read_json(path)
        for item in _candidate_dicts(payload):
            measured_at = _measurement_timestamp(item)
            measurement_date = date_from_timestamp_or_date(
                measured_at,
                item.get("calendarDate") or item.get("date") or item.get("sampleDate"),
            )
            if not measurement_date:
                continue
            for raw_key, (metric, unit) in GARMIN_METRIC_FIELDS.items():
                if raw_key not in item:
                    continue
                value = _normalize_value(metric, item.get(raw_key))
                if value is None:
                    continue
                identity = (metric, measured_at or measurement_date, unit, value)
                if identity in seen:
                    continue
                seen.add(identity)
                source_id = str(
                    item.get("samplePk")
                    or item.get("id")
                    or stable_measurement_id(path.name, metric, measurement_date, value)
                )
                stable_id = stable_measurement_id(
                    source_id,
                    metric,
                    measurement_date,
                    value,
                )
                measurement_uid = f"{SOURCE}:measurement:{stable_id}"
                records.append(
                    NormalizedMeasurement(
                        schema_version=SCHEMA_VERSION,
                        measurement_uid=measurement_uid,
                        source=SOURCE,
                        source_measurement_id=source_id,
                        metric=metric,
                        value=value,
                        unit=unit,
                        measured_at_utc=measured_at,
                        measurement_date=measurement_date,
                        source_reference=SourceReference(
                            source=SOURCE,
                            entity_type="measurement",
                            source_id=source_id,
                            raw_path=path.relative_to(raw_root).as_posix(),
                        ),
                        attributes={
                            "garmin_raw_key": raw_key,
                        },
                    )
                )
    return records


def _candidate_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if any(key in value for key in GARMIN_METRIC_FIELDS):
            found.append(value)
        for item in value.values():
            found.extend(_candidate_dicts(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_candidate_dicts(item))
    return found


def _measurement_timestamp(item: dict[str, Any]) -> str | None:
    for key in (
        "dateTimestamp",
        "sampleDate",
        "timestamp",
        "weightTimestamp",
        "createdDate",
    ):
        timestamp = normalize_utc_timestamp(item.get(key))
        if timestamp:
            return timestamp
    return None


def _normalize_value(metric: str, value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if metric in {"weight", "bone_mass", "muscle_mass", "skeletal_muscle_mass"}:
        if number > 300:
            number = number / 1000.0
    return round(number, 4)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return _read_json(path)
