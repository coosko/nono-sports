import json
from pathlib import Path

from nono_sports.normalization.garmin_dataset import normalize_garmin_dataset


def test_normalize_garmin_dataset_writes_common_outputs(tmp_path: Path) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    _write_json(raw_root / "activities" / "234.details.json", {"activityId": 234})
    _write_json(raw_root / "fit_decoded" / "234.fitdecode.json", _fitdecode_payload())
    _write_json(raw_root / "splits" / "234.json", {"activityId": 234, "lapDTOs": []})
    _write_json(raw_root / "typed_splits" / "234.json", {"activityId": 234})
    _write_json(raw_root / "weather" / "234.json", {"condition": "sunny"})
    _write_manifest(raw_root / "manifest.jsonl")

    result = normalize_garmin_dataset(tmp_path)

    assert result.activities == 1
    assert result.streams == 1
    assert result.laps == 1
    assert result.splits == 1
    assert result.typed_splits == 1
    assert {item.relative_path for item in result.written} == {
        "activities.jsonl",
        "streams.jsonl",
        "streams_index.jsonl",
        "laps.jsonl",
        "splits.jsonl",
        "typed_splits.jsonl",
        "segment_candidates.jsonl",
        "state.json",
    }

    activities = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "activities.jsonl"
    )
    activity = activities[0]
    assert activity["activity_uid"] == "garmin_connect:activity:234"
    assert activity["sport"]["discipline"] == "road_cycling"
    assert activity["start"]["start_at_utc"] == "2026-06-29T18:42:22Z"
    assert activity["distance"]["distance_m"] == 30289.77
    assert activity["duration"]["moving_time_s"] == 3986
    assert activity["duration"]["elapsed_time_s"] == 4208
    assert activity["stream_uid"] == "garmin_connect:stream:234"
    assert activity["completeness"]["has_decoded_fit"] is True

    streams = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "streams.jsonl"
    )
    assert streams[0]["samples"]["time"] == 2
    assert streams[0]["samples"]["hrv"] == 2
    assert streams[0]["streams"]["heartrate"]["values"] == [88, 90]


def _activity_payload() -> dict:
    return {
        "activityId": 234,
        "activityName": "Madrid Ciclismo en ruta",
        "activityTypeDTO": {"typeKey": "road_biking"},
        "activityUUID": {"uuid": "activity-uuid"},
        "accessControlRuleDTO": {"typeKey": "subscribers"},
        "locationName": "Madrid",
        "metadataDTO": {
            "deviceMetaDataDTO": {"deviceId": "3976792982"},
            "fileFormat": {"formatKey": "fit"},
            "lapCount": 1,
            "manualActivity": False,
            "manufacturer": "GARMIN",
            "sensors": [],
            "userInfoDto": {"userProfilePk": 42},
        },
        "summaryDTO": {
            "averageBikeCadence": 78.0,
            "averageHR": 143.0,
            "averageSpeed": 7.599,
            "calories": 665.0,
            "distance": 30289.77,
            "duration": 3986.15,
            "elapsedDuration": 4208.147,
            "elevationGain": 181.0,
            "maxHR": 177.0,
            "startTimeGMT": "2026-06-29T18:42:22.0",
            "startTimeLocal": "2026-06-29T20:42:22.0",
        },
    }


def _fitdecode_payload() -> dict:
    return {
        "backend": "fitdecode",
        "errors": [],
        "frames": 3,
        "messages": {
            "record": [
                {
                    "timestamp": "2026-06-29T18:42:22+00:00",
                    "distance": 7.03,
                    "enhanced_altitude": 549.0,
                    "enhanced_speed": 7.026,
                    "heart_rate": 88,
                    "temperature": 24,
                },
                {
                    "timestamp": "2026-06-29T18:42:23+00:00",
                    "distance": 14.0,
                    "enhanced_altitude": 550.0,
                    "enhanced_speed": 7.1,
                    "heart_rate": 90,
                    "temperature": 24,
                },
            ],
            "hrv": [{"time": [0.688, 0.695]}],
            "lap": [
                {
                    "message_index": 0,
                    "start_time": "2026-06-29T18:42:22+00:00",
                    "total_distance": 30289.77,
                    "total_elapsed_time": 4208.147,
                    "total_timer_time": 3986.15,
                    "total_ascent": 181,
                    "avg_heart_rate": 143,
                    "max_heart_rate": 177,
                }
            ],
        },
    }


def _write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {"path": "activities/234.json", "sha256": "activity"},
        {"path": "activities/234.details.json", "sha256": "details"},
        {"path": "fit_decoded/234.fitdecode.json", "sha256": "fitdecode"},
    ]
    path.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]
