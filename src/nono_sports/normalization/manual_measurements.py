"""Normalize manually maintained biometric measurements."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from nono_sports.core.paths import manual_path
from nono_sports.domain.measurement import NormalizedMeasurement
from nono_sports.domain.source import SourceReference
from nono_sports.normalization.measurement_utils import (
    canonical_metric,
    canonical_unit,
    date_from_timestamp_or_date,
    normalize_utc_timestamp,
    parse_float,
    stable_measurement_id,
)
from nono_sports.storage.source_normalized_store import (
    SourceNormalizedStore,
    SourceNormalizedWriteResult,
)

SOURCE = "manual"
SCHEMA_VERSION = "nono.normalized_measurement.v1"
DEFAULT_CSV = Path("biometria") / "mediciones_carlos.csv"


@dataclass(frozen=True)
class ManualMeasurementNormalizationResult:
    measurements: int
    written: tuple[SourceNormalizedWriteResult, ...]
    normalized_root: str


def normalize_manual_measurements(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> ManualMeasurementNormalizationResult:
    generated_at = generated_at or datetime.now(UTC)
    source_path = manual_path(data_root, DEFAULT_CSV.as_posix())
    normalized_root = manual_path(data_root, "normalizado")
    measurements = _read_manual_csv(source_path)
    state = {
        "schema_version": "nono.manual.measurements_state.v1",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "inputs": {
            "measurements_csv": str(source_path),
        },
        "outputs": {
            "measurements": "measurements.jsonl",
        },
        "counts": {
            "measurements": len(measurements),
        },
    }
    store = SourceNormalizedStore(normalized_root)
    written = [
        store.write_jsonl("measurements.jsonl", measurements),
        store.write_json("measurements_state.json", state),
    ]
    return ManualMeasurementNormalizationResult(
        measurements=len(measurements),
        written=tuple(written),
        normalized_root=str(normalized_root),
    )


def _read_manual_csv(path: Path) -> list[NormalizedMeasurement]:
    if not path.exists():
        return []
    records: list[NormalizedMeasurement] = []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for line_number, row in enumerate(reader, start=2):
            metric = canonical_metric(row.get("metric"))
            value = parse_float(row.get("value"))
            if not metric or value is None:
                continue
            unit = canonical_unit(metric, row.get("unit"))
            measured_at = normalize_utc_timestamp(row.get("reported_at_utc"))
            measurement_date = date_from_timestamp_or_date(
                measured_at,
                row.get("measurement_date"),
            )
            source_id = f"mediciones_carlos.csv:{line_number}"
            measurement_uid = (
                f"{SOURCE}:measurement:"
                f"{stable_measurement_id(source_id, metric, measurement_date, value)}"
            )
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
                    conditions=_blank_to_none(row.get("conditions")),
                    notes=_blank_to_none(row.get("notes")),
                    source_reference=SourceReference(
                        source=SOURCE,
                        entity_type="measurement",
                        source_id=source_id,
                        raw_path=DEFAULT_CSV.as_posix(),
                    ),
                    attributes={
                        "declared_source": _blank_to_none(row.get("source")),
                    },
                )
            )
    return records


def _blank_to_none(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()
