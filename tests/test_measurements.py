import csv
import json
from datetime import UTC, date, datetime
from pathlib import Path

from nono_sports.consolidation.measurements import build_consolidated_measurements
from nono_sports.garmin_connect.client import GarminConnectClient
from nono_sports.garmin_connect.measurements import (
    GarminMeasurementStateStore,
    sync_garmin_measurements_raw,
)
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.normalization.garmin_measurements import (
    normalize_garmin_measurements,
)
from nono_sports.normalization.manual_measurements import normalize_manual_measurements


class FakeGarminMeasurementApi:
    def get_weigh_ins(self, start_date, end_date):
        return {
            "dateWeightList": [
                {
                    "samplePk": 123,
                    "calendarDate": "2026-07-12",
                    "dateTimestamp": "2026-07-12T06:30:00Z",
                    "weight": 74500,
                    "bmi": 26.1,
                }
            ],
            "range": {"start": start_date, "end": end_date},
        }

    def get_body_composition(self, start_date, end_date):
        return {
            "dateWeightList": [
                {
                    "samplePk": 123,
                    "calendarDate": "2026-07-12",
                    "dateTimestamp": "2026-07-12T06:30:00Z",
                    "bodyFat": 18.2,
                }
            ],
            "range": {"start": start_date, "end": end_date},
        }


def test_sync_garmin_measurements_raw_writes_range_and_state(tmp_path: Path) -> None:
    client = GarminConnectClient(FakeGarminMeasurementApi())
    result = sync_garmin_measurements_raw(
        client,
        GarminRawStore(tmp_path),
        GarminMeasurementStateStore(tmp_path),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 12),
        clock=lambda: datetime(2026, 7, 12, 8, 0, tzinfo=UTC),
    )

    assert result.start_date == "2026-07-01"
    assert result.end_date == "2026-07-12"
    assert {item.relative_path for item in result.written} == {
        "biometrics/body_composition_2026-07-01_2026-07-12.json",
        "biometrics/weigh_ins_2026-07-01_2026-07-12.json",
    }
    state = json.loads(Path(result.state_path).read_text(encoding="utf-8"))
    assert state["last_successful_measurement_sync_end_date"] == "2026-07-12"


def test_normalize_garmin_measurements_extracts_weight_and_body_composition(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw" / "biometrics"
    _write_json(
        raw_root / "weigh_ins_2026-07-01_2026-07-12.json",
        {
            "dateWeightList": [
                {
                    "samplePk": 123,
                    "calendarDate": "2026-07-12",
                    "dateTimestamp": "2026-07-12T06:30:00Z",
                    "weight": 74500,
                    "bmi": 26.1,
                }
            ]
        },
    )
    _write_json(
        raw_root / "body_composition_2026-07-01_2026-07-12.json",
        {
            "dateWeightList": [
                {
                    "samplePk": 123,
                    "calendarDate": "2026-07-12",
                    "dateTimestamp": "2026-07-12T06:30:00Z",
                    "bodyFat": 18.2,
                }
            ]
        },
    )

    result = normalize_garmin_measurements(tmp_path)

    assert result.measurements == 3
    measurements = _read_jsonl(
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "normalizado"
        / "measurements.jsonl"
    )
    weight = next(item for item in measurements if item["metric"] == "weight")
    assert weight["value"] == 74.5
    assert weight["unit"] == "kg"
    assert weight["measurement_date"] == "2026-07-12"


def test_normalize_manual_measurements_reads_existing_csv_shape(tmp_path: Path) -> None:
    csv_path = (
        tmp_path
        / "10_fuentes"
        / "manual"
        / "biometria"
        / "mediciones_carlos.csv"
    )
    csv_path.parent.mkdir(parents=True)
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "measurement_date",
                "reported_at_utc",
                "metric",
                "value",
                "unit",
                "conditions",
                "source",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "measurement_date": "2026-07-12",
                "reported_at_utc": "2026-07-12T06:30:00Z",
                "metric": "weight",
                "value": "74.5",
                "unit": "kg",
                "conditions": "manana",
                "source": "manual",
                "notes": "ok",
            }
        )

    result = normalize_manual_measurements(tmp_path)

    assert result.measurements == 1
    measurements = _read_jsonl(
        tmp_path / "10_fuentes" / "manual" / "normalizado" / "measurements.jsonl"
    )
    assert measurements[0]["metric"] == "weight"
    assert measurements[0]["value"] == 74.5
    assert measurements[0]["conditions"] == "manana"


def test_build_consolidated_measurements_deduplicates_sources(tmp_path: Path) -> None:
    garmin_root = tmp_path / "10_fuentes" / "garmin_connect" / "normalizado"
    manual_root = tmp_path / "10_fuentes" / "manual" / "normalizado"
    _write_jsonl(
        garmin_root / "measurements.jsonl",
        [
            {
                "schema_version": "nono.normalized_measurement.v1",
                "measurement_uid": "garmin_connect:measurement:1",
                "source": "garmin_connect",
                "source_measurement_id": "1",
                "metric": "weight",
                "value": 74.5,
                "unit": "kg",
                "measured_at_utc": "2026-07-12T06:30:00Z",
                "measurement_date": "2026-07-12",
                "source_reference": {"raw_path": "biometrics/a.json"},
            }
        ],
    )
    _write_jsonl(
        manual_root / "measurements.jsonl",
        [
            {
                "schema_version": "nono.normalized_measurement.v1",
                "measurement_uid": "manual:measurement:1",
                "source": "manual",
                "source_measurement_id": "mediciones_carlos.csv:2",
                "metric": "weight",
                "value": 74.5,
                "unit": "kg",
                "measured_at_utc": "2026-07-12T06:30:00Z",
                "measurement_date": "2026-07-12",
                "source_reference": {"raw_path": "biometria/mediciones_carlos.csv"},
            }
        ],
    )

    result = build_consolidated_measurements(tmp_path)

    assert result.measurements == 1
    assert result.measurement_sources == 2
    consolidated = _read_jsonl(tmp_path / "20_consolidado" / "measurements.jsonl")
    assert consolidated[0]["metric"] == "weight"
    assert consolidated[0]["primary_source"] == "garmin_connect"
    assert consolidated[0]["source_count"] == 2


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
