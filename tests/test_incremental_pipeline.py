import json
from pathlib import Path

import nono_sports.consolidation.measurements as measurements_consolidation
import nono_sports.consolidation.multi_source as activity_consolidation
import nono_sports.consolidation.user_data as user_data_consolidation
import nono_sports.normalization.garmin_dataset as garmin_dataset
import nono_sports.normalization.garmin_measurements as garmin_measurements
import nono_sports.normalization.manual_activities as manual_activities
import nono_sports.normalization.manual_measurements as manual_measurements
import nono_sports.normalization.strava_dataset as strava_dataset
from nono_sports.consolidation.measurements import build_consolidated_measurements
from nono_sports.consolidation.multi_source import build_multi_source_consolidated
from nono_sports.consolidation.user_data import build_consolidated_user_data
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.normalization.garmin_dataset import normalize_garmin_dataset
from nono_sports.normalization.garmin_measurements import (
    normalize_garmin_measurements,
)
from nono_sports.normalization.manual_activities import normalize_manual_activities
from nono_sports.normalization.manual_measurements import normalize_manual_measurements
from nono_sports.normalization.strava_dataset import normalize_strava_dataset
from nono_sports.storage.incremental import build_file_fingerprint
from nono_sports.storage.raw_store import RawStore


def test_manifest_sha_keeps_raw_fingerprint_stable_after_same_content_rewrite(
    tmp_path: Path,
) -> None:
    raw_store = RawStore(tmp_path)
    raw_store.write_json("activities/100.json", {"id": 100}, endpoint="/activity")
    first = build_file_fingerprint(
        raw_store.raw_root,
        ("activities/*.json",),
        manifest_path=raw_store.raw_root / "manifest.jsonl",
    )

    raw_store.write_json("activities/100.json", {"id": 100}, endpoint="/activity")
    second = build_file_fingerprint(
        raw_store.raw_root,
        ("activities/*.json",),
        manifest_path=raw_store.raw_root / "manifest.jsonl",
    )

    assert second == first


def test_strava_normalization_skips_when_raw_inputs_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_store = RawStore(tmp_path)
    raw_store.write_json(
        "activities/100.json",
        {
            "id": 100,
            "athlete": {"id": 42},
            "name": "Morning Ride",
            "type": "Ride",
        },
        endpoint="/activities/100",
    )

    first = normalize_strava_dataset(tmp_path)
    monkeypatch.setattr(
        strava_dataset,
        "_iter_normalized_activities",
        _raise_if_called,
    )
    second = normalize_strava_dataset(tmp_path)

    assert first.skipped is False
    assert second.skipped is True
    assert second.activities == first.activities
    assert second.written == ()


def test_strava_normalization_rebuilds_when_raw_inputs_change(
    tmp_path: Path,
) -> None:
    raw_store = RawStore(tmp_path)
    raw_store.write_json(
        "activities/100.json",
        {"id": 100, "athlete": {"id": 42}, "name": "Ride", "type": "Ride"},
        endpoint="/activities/100",
    )
    normalize_strava_dataset(tmp_path)

    raw_store.write_json(
        "activities/101.json",
        {"id": 101, "athlete": {"id": 42}, "name": "Run", "type": "Run"},
        endpoint="/activities/101",
    )
    second = normalize_strava_dataset(tmp_path)

    assert second.skipped is False
    assert second.activities == 2
    assert len(second.written) == 6


def test_garmin_normalization_skips_when_raw_inputs_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_store = GarminRawStore(tmp_path)
    raw_store.write_json(
        "activities/234.json",
        {
            "activityId": 234,
            "activityName": "Ride",
            "activityTypeDTO": {"typeKey": "road_biking"},
            "summaryDTO": {"startTimeGMT": "2026-08-26T07:00:00.0"},
        },
        endpoint="activity",
    )

    first = normalize_garmin_dataset(tmp_path)
    monkeypatch.setattr(garmin_dataset, "_normalize_activities", _raise_if_called)
    second = normalize_garmin_dataset(tmp_path)

    assert first.skipped is False
    assert second.skipped is True
    assert second.activities == first.activities
    assert second.written == ()


def test_measurement_normalizers_skip_when_inputs_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_store = GarminRawStore(tmp_path)
    raw_store.write_json(
        "biometrics/weigh_ins_2026-08-01_2026-08-26.json",
        {"dateWeightList": [{"calendarDate": "2026-08-26", "weight": 74500}]},
        endpoint="weigh_ins",
    )
    manual_csv = (
        tmp_path
        / "10_fuentes"
        / "manual"
        / "biometria"
        / "mediciones_carlos.csv"
    )
    manual_csv.parent.mkdir(parents=True)
    manual_csv.write_text(
        "measurement_date,metric,value,unit\n2026-08-26,weight,74.5,kg\n",
        encoding="utf-8",
    )

    garmin_first = normalize_garmin_measurements(tmp_path)
    manual_first = normalize_manual_measurements(tmp_path)
    monkeypatch.setattr(
        garmin_measurements,
        "_normalize_raw_measurements",
        _raise_if_called,
    )
    monkeypatch.setattr(manual_measurements, "_iter_manual_csv", _raise_if_called)

    garmin_second = normalize_garmin_measurements(tmp_path)
    manual_second = normalize_manual_measurements(tmp_path)

    assert garmin_second.skipped is True
    assert garmin_second.measurements == garmin_first.measurements
    assert garmin_second.written == ()
    assert manual_second.skipped is True
    assert manual_second.measurements == manual_first.measurements
    assert manual_second.written == ()


def test_manual_activity_normalization_skips_when_inputs_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "manual" / "raw"
    _write_text(raw_root / "activities" / "komoot_1.gpx", _gpx_fixture())

    first = normalize_manual_activities(tmp_path)
    monkeypatch.setattr(manual_activities, "_normalize_gpx_file", _raise_if_called)
    second = normalize_manual_activities(tmp_path)

    assert second.skipped is True
    assert second.activities == first.activities
    assert second.written == ()


def test_consolidation_steps_skip_when_inputs_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl",
        [_normalized_activity("strava", "100")],
    )
    _write_jsonl(
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "normalizado"
        / "measurements.jsonl",
        [_normalized_measurement("garmin_connect", "1")],
    )
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "athletes.jsonl",
        [_normalized_athlete("strava")],
    )

    activities_first = build_multi_source_consolidated(tmp_path)
    measurements_first = build_consolidated_measurements(tmp_path)
    user_data_first = build_consolidated_user_data(tmp_path)
    monkeypatch.setattr(
        activity_consolidation,
        "_load_normalized_inputs",
        _raise_if_called,
    )
    monkeypatch.setattr(
        measurements_consolidation,
        "_load_normalized_measurements",
        _raise_if_called,
    )
    monkeypatch.setattr(user_data_consolidation, "_load_records", _raise_if_called)
    monkeypatch.setattr(
        user_data_consolidation,
        "_load_activity_usage_context",
        _raise_if_called,
    )

    activities_second = build_multi_source_consolidated(tmp_path)
    measurements_second = build_consolidated_measurements(tmp_path)
    user_data_second = build_consolidated_user_data(tmp_path)

    assert activities_second.skipped is True
    assert activities_second.activities == activities_first.activities
    assert activities_second.written == ()
    assert measurements_second.skipped is True
    assert measurements_second.measurements == measurements_first.measurements
    assert measurements_second.written == ()
    assert user_data_second.skipped is True
    assert user_data_second.athletes == user_data_first.athletes
    assert user_data_second.written == ()


def test_activity_consolidation_rebuilds_when_normalized_inputs_change(
    tmp_path: Path,
) -> None:
    strava_path = (
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl"
    )
    _write_jsonl(strava_path, [_normalized_activity("strava", "100")])
    build_multi_source_consolidated(tmp_path)

    _write_jsonl(
        strava_path,
        [
            _normalized_activity("strava", "100"),
            _normalized_activity(
                "strava",
                "101",
                start_at_utc="2026-08-27T07:00:00Z",
            ),
        ],
    )
    second = build_multi_source_consolidated(tmp_path)

    assert second.skipped is False
    assert second.activities == 2


def _raise_if_called(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    raise AssertionError("Incremental skip should avoid this expensive function")


def _normalized_activity(
    source: str,
    source_id: str,
    *,
    start_at_utc: str = "2026-08-26T07:00:00Z",
) -> dict:
    activity_uid = f"{source}:activity:{source_id}"
    return {
        "activity_uid": activity_uid,
        "source": source,
        "source_activity_id": source_id,
        "title": "Ride",
        "sport": {"family": "cycling", "discipline": "road_cycling"},
        "start": {"start_at_utc": start_at_utc},
        "duration": {"moving_time_s": 1800},
        "distance": {"distance_m": 12000.0},
        "elevation": {},
        "energy": {},
        "metrics": {},
        "location": {},
        "gear": {},
        "flags": {},
        "completeness": {},
        "laps": [],
        "segments": [],
        "stream_uid": f"{source}:stream:{source_id}",
        "source_reference": {"raw_path": f"activities/{source_id}.json"},
        "external_ids": {},
    }


def _normalized_measurement(source: str, source_id: str) -> dict:
    return {
        "measurement_uid": f"{source}:measurement:{source_id}",
        "source": source,
        "source_measurement_id": source_id,
        "metric": "weight",
        "value": 74.5,
        "unit": "kg",
        "measured_at_utc": "2026-08-26T07:00:00Z",
        "measurement_date": "2026-08-26",
        "source_reference": {"raw_path": "biometrics/a.json"},
    }


def _normalized_athlete(source: str) -> dict:
    return {
        "athlete_uid": f"{source}:athlete:42",
        "source": source,
        "source_athlete_id": "42",
        "display": {"firstname": "Carlos"},
        "profile": {},
        "physiology": {},
        "preferences": {},
        "source_reference": {"raw_path": "athlete/profile.json"},
    }


def _gpx_fixture() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk><trkseg>
    <trkpt lat="40.0" lon="-3.0">
      <ele>700.0</ele><time>2026-08-26T07:00:00Z</time>
    </trkpt>
    <trkpt lat="40.001" lon="-3.0">
      <ele>701.0</ele><time>2026-08-26T07:01:00Z</time>
    </trkpt>
  </trkseg></trk>
</gpx>
"""


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
