import json
from pathlib import Path

from nono_sports.consolidation.user_data import build_consolidated_user_data
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.garmin_connect.user_data import (
    GarminUserDataStateStore,
    sync_garmin_user_data_raw,
)
from nono_sports.normalization.garmin_user_data import normalize_garmin_user_data
from nono_sports.storage.raw_store import RawStore


class FakeGarminUserClient:
    def get_user_profile(self):
        return {
            "userProfileId": 7,
            "firstName": "Carlos",
            "displayName": "Carlos P",
            "weight": 73.5,
        }

    def get_userprofile_settings(self):
        return {"measurementSystem": "metric"}

    def get_gear(self, user_profile_number):
        return {
            "gear": [
                {
                    "gearUuid": "bike-1",
                    "displayName": "REACTO 5000",
                    "gearTypeName": "bike",
                    "brandName": "Merida",
                }
            ]
        }

    def get_gear_defaults(self, user_profile_number):
        return {"defaultBike": "bike-1"}

    def get_gear_stats(self, gear_uuid):
        return {"totalDistance": 12345.6}

    def get_devices(self):
        return [
            {
                "deviceId": "edge-1",
                "deviceName": "Edge 1040",
                "manufacturer": "Garmin",
            }
        ]

    def get_device_last_used(self):
        return {"deviceId": "edge-1"}

    def get_primary_training_device(self):
        return {"deviceId": "edge-1"}


def test_garmin_user_data_normalizes_and_consolidates_equipment(
    tmp_path: Path,
) -> None:
    raw_result = sync_garmin_user_data_raw(
        FakeGarminUserClient(),
        GarminRawStore(tmp_path),
        GarminUserDataStateStore(tmp_path),
    )
    assert len(raw_result.written) == 8

    normalized = normalize_garmin_user_data(tmp_path)
    assert normalized.athletes == 1
    assert normalized.equipment == 2

    strava_raw = RawStore(tmp_path)
    strava_raw.write_json(
        "athlete/profile.json",
        {
            "id": 42,
            "firstname": "Carlos",
            "bikes": [{"id": "strava-bike-1", "name": "REACTO 5000"}],
        },
        endpoint="/athlete",
    )
    strava_raw.write_json(
        "gear/strava-bike-1.json",
        {
            "id": "strava-bike-1",
            "name": "REACTO 5000",
            "brand_name": "Merida",
        },
        endpoint="/gear/strava-bike-1",
    )
    from nono_sports.normalization.strava_dataset import normalize_strava_dataset

    normalize_strava_dataset(tmp_path)

    consolidated = build_consolidated_user_data(tmp_path)
    assert consolidated.athletes == 1
    assert consolidated.equipment == 2
    assert consolidated.equipment_sources == 3

    equipment = _read_jsonl(tmp_path / "20_consolidado" / "equipment.jsonl")
    reacto = [
        item
        for item in equipment
        if item["name"] == "REACTO 5000"
    ][0]
    assert reacto["source_count"] == 2
    assert reacto["primary_source"] == "garmin_connect"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
