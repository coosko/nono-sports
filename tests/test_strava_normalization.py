import json
from pathlib import Path

from nono_sports.domain.source import SourceReference
from nono_sports.normalization.strava_activity import normalize_strava_activity
from nono_sports.normalization.strava_dataset import normalize_strava_dataset
from nono_sports.storage.raw_store import RawStore
from nono_sports.storage.source_normalized_store import SourceNormalizedStore


def test_normalize_strava_dataset_writes_jsonl_outputs(tmp_path: Path) -> None:
    raw_store = RawStore(tmp_path)
    raw_store.write_json(
        "athlete/profile.json",
        {
            "id": 42,
            "firstname": "Ada",
            "measurement_preference": "meters",
            "weight": 60.5,
            "bikes": [{"id": "g1", "name": "Road Bike"}],
        },
        endpoint="/athlete",
    )
    raw_store.write_json(
        "activities/100.json",
        {
            "id": 100,
            "athlete": {"id": 42},
            "name": "Morning Ride",
            "sport_type": "Ride",
            "type": "Ride",
            "start_date": "2026-05-26T05:00:00Z",
            "start_date_local": "2026-05-26T07:00:00Z",
            "timezone": "(GMT+01:00) Europe/Madrid",
            "utc_offset": 7200,
            "moving_time": 1800,
            "elapsed_time": 1900,
            "distance": 12000.0,
            "total_elevation_gain": 220.0,
            "average_speed": 6.6,
            "max_speed": 12.3,
            "average_heartrate": 140.0,
            "gear_id": "g1",
            "segment_efforts": [{"segment": {"id": 200}}],
        },
        endpoint="/activities/100",
    )
    raw_store.write_json(
        "streams/100.json",
        {
            "distance": {
                "data": [0.0, 10.0],
                "series_type": "distance",
                "original_size": 2,
            },
            "heartrate": {"data": [130, 140], "original_size": 2},
        },
        endpoint="/activities/100/streams",
    )
    raw_store.write_json(
        "laps/100.json",
        [
            {
                "id": 1,
                "lap_index": 1,
                "name": "Lap 1",
                "distance": 1000.0,
                "moving_time": 180,
                "elapsed_time": 190,
            }
        ],
        endpoint="/activities/100/laps",
    )
    raw_store.write_json(
        "gear/g1.json",
        {"id": "g1", "name": "Road Bike", "brand_name": "Nono"},
        endpoint="/gear/g1",
    )
    raw_store.write_json(
        "segments/200.json",
        {
            "id": 200,
            "name": "Hill",
            "distance": 400.0,
            "total_elevation_gain": 30.0,
        },
        endpoint="/segments/200",
    )

    result = normalize_strava_dataset(tmp_path)

    assert result.athletes == 1
    assert result.equipment == 1
    assert result.activities == 1
    assert result.streams == 1
    assert result.streams_index == 1
    assert {item.relative_path for item in result.written} == {
        "athletes.jsonl",
        "equipment.jsonl",
        "activities.jsonl",
        "streams.jsonl",
        "streams_index.jsonl",
        "state.json",
    }
    equipment = _read_jsonl(tmp_path, "equipment.jsonl")
    assert equipment[0]["equipment_uid"] == "strava:equipment:g1"
    assert equipment[0]["equipment_type"] == "bike"
    assert equipment[0]["brand"] == "Nono"
    activities = _read_jsonl(tmp_path, "activities.jsonl")
    assert activities[0]["activity_uid"] == "strava:activity:100"
    assert activities[0]["sport"]["family"] == "cycling"
    assert activities[0]["distance"]["distance_m"] == 12000.0
    assert activities[0]["gear"]["name"] == "Road Bike"
    assert activities[0]["laps"][0]["lap_uid"] == "strava:activity:100:lap:1"
    assert activities[0]["segments"][0]["segment_uid"] == "strava:segment:200"
    assert activities[0]["completeness"]["has_streams"] is True
    assert activities[0]["source_reference"]["raw_path"] == "activities/100.json"
    streams = _read_jsonl(tmp_path, "streams.jsonl")
    assert streams[0]["samples"] == {"distance": 2, "heartrate": 2}
    assert streams[0]["streams"]["distance"]["unit"] == "m"
    streams_index = _read_jsonl(tmp_path, "streams_index.jsonl")
    assert streams_index[0]["schema_version"] == "nono.streams_index.v1"
    assert streams_index[0]["activity_uid"] == "strava:activity:100"
    assert streams_index[0]["stream_uid"] == "strava:stream:100"
    state = json.loads(
        (
            tmp_path
            / "10_fuentes"
            / "strava"
            / "normalizado"
            / "state.json"
        ).read_text(encoding="utf-8")
    )
    assert state["schema_version"] == "nono.strava.normalization_state.v1"
    assert state["outputs"]["streams_index"] == "streams_index.jsonl"
    assert state["counts"]["streams_index"] == 1


def test_normalize_strava_dataset_streams_large_outputs_without_lists(
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
            "sport_type": "Ride",
            "type": "Ride",
            "moving_time": 1800,
        },
        endpoint="/activities/100",
    )
    raw_store.write_json(
        "streams/100.json",
        {"heartrate": {"data": [130, 140], "original_size": 2}},
        endpoint="/activities/100/streams",
    )
    original_write_jsonl = SourceNormalizedStore.write_jsonl

    def spy_write_jsonl(self, relative_path, records):  # noqa: ANN001
        if str(relative_path) in {
            "activities.jsonl",
            "streams.jsonl",
            "streams_index.jsonl",
        }:
            assert not isinstance(records, list)
        return original_write_jsonl(self, relative_path, records)

    monkeypatch.setattr(SourceNormalizedStore, "write_jsonl", spy_write_jsonl)

    result = normalize_strava_dataset(tmp_path)

    assert result.activities == 1
    assert result.streams == 1
    assert result.streams_index == 1


def test_normalize_strava_activity_supports_non_distance_sports() -> None:
    activity = normalize_strava_activity(
        {
            "id": 101,
            "athlete": {"id": 42},
            "name": "Gym",
            "sport_type": "Workout",
            "type": "Workout",
            "moving_time": 2400,
        },
        source_reference=SourceReference(
            source="strava",
            entity_type="activity",
            source_id="101",
            raw_path="activities/101.json",
        ),
    )

    assert activity.sport["family"] == "fitness"
    assert activity.sport["movement_context"] == "strength_skill_or_mixed"
    assert activity.distance["distance_m"] is None
    assert activity.duration["moving_time_s"] == 2400


def _read_jsonl(tmp_path: Path, relative_path: str) -> list[dict]:
    path = tmp_path / "10_fuentes" / "strava" / "normalizado" / relative_path
    return [json.loads(line) for line in path.read_text().splitlines()]
