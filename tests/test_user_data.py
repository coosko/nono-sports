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


def test_consolidated_equipment_usage_sums_activity_distance_without_duplicates(
    tmp_path: Path,
) -> None:
    _write_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "equipment.jsonl",
        [
            _equipment(
                "garmin_connect",
                "garmin_connect:equipment:bike-1",
                "bike-1",
                "bike",
                "REACTO 5000",
            ),
            _equipment(
                "garmin_connect",
                "garmin_connect:equipment:device:edge-1",
                "edge-1",
                "device",
                "Edge 1040",
            ),
        ],
    )
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "equipment.jsonl",
        [
            _equipment(
                "strava",
                "strava:equipment:strava-bike-1",
                "strava-bike-1",
                "bike",
                "REACTO 5000",
            )
        ],
    )
    _write_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "activities.jsonl",
        [
            _activity(
                "garmin_connect",
                "g-dup",
                1100,
                110,
                {"activity_gear": {"gear": [{"uuid": "bike-1"}]}},
            ),
            _activity(
                "garmin_connect",
                "g-bike-only",
                2000,
                200,
                {"activity_gear": {"gear": [{"gearUuid": "bike-1"}]}},
            ),
            _activity("garmin_connect", "g-no-bike", 3000, 300, {}),
            _activity("garmin_connect", "g-duplicate-without-bike", 5100, 510, {}),
            _activity(
                "garmin_connect",
                "g-device-only",
                6000,
                600,
                {"device_id": "edge-1"},
            ),
        ],
    )
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl",
        [
            _activity(
                "strava",
                "s-dup",
                1000,
                100,
                {"source_gear_id": "strava-bike-1"},
            ),
            _activity(
                "strava",
                "s-bike-only",
                4000,
                400,
                {"source_gear_id": "strava-bike-1"},
            ),
            _activity(
                "strava",
                "s-duplicate-with-bike",
                5000,
                500,
                {"source_gear_id": "strava-bike-1"},
            ),
            _activity("strava", "s-no-bike", 7000, 700, {}),
        ],
    )
    _write_jsonl(
        tmp_path / "20_consolidado" / "activities.jsonl",
        [
            _consolidated_activity(
                "dup",
                [
                    ("strava", "strava:activity:s-dup", 1),
                    ("garmin_connect", "garmin_connect:activity:g-dup", 2),
                ],
            ),
            _consolidated_activity(
                "garmin-bike-only",
                [("garmin_connect", "garmin_connect:activity:g-bike-only", 1)],
            ),
            _consolidated_activity(
                "garmin-no-bike",
                [("garmin_connect", "garmin_connect:activity:g-no-bike", 1)],
            ),
            _consolidated_activity(
                "strava-bike-only",
                [("strava", "strava:activity:s-bike-only", 1)],
            ),
            _consolidated_activity(
                "duplicate-with-strava-bike",
                [
                    (
                        "garmin_connect",
                        "garmin_connect:activity:g-duplicate-without-bike",
                        1,
                    ),
                    ("strava", "strava:activity:s-duplicate-with-bike", 2),
                ],
            ),
            _consolidated_activity(
                "strava-no-bike",
                [("strava", "strava:activity:s-no-bike", 1)],
            ),
            _consolidated_activity(
                "garmin-device-only",
                [("garmin_connect", "garmin_connect:activity:g-device-only", 1)],
            ),
        ],
    )

    build_consolidated_user_data(tmp_path)

    equipment = _read_jsonl(tmp_path / "20_consolidado" / "equipment.jsonl")
    bike = next(item for item in equipment if item["equipment_type"] == "bike")
    device = next(item for item in equipment if item["equipment_type"] == "device")
    assert bike["distance_m"] == 12000.0
    assert bike["attributes"]["usage"]["moving_time_s"] == 1200.0
    assert bike["attributes"]["usage"]["activity_count"] == 4
    assert bike["attributes"]["usage"]["unassignable_activity_count"] == 3
    assert sorted(
        (item["source"], item["distance_m"])
        for item in bike["attributes"]["usage"]["partial_distance_m"]
    ) == [("garmin_connect", 2000.0), ("strava", 10000.0)]
    assert device["distance_m"] == 6000.0
    assert device["attributes"]["usage"]["activity_count"] == 1


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _equipment(
    source: str,
    equipment_uid: str,
    source_equipment_id: str,
    equipment_type: str,
    name: str,
) -> dict:
    return {
        "schema_version": "nono.normalized_equipment.v1",
        "equipment_uid": equipment_uid,
        "source": source,
        "source_equipment_id": source_equipment_id,
        "equipment_type": equipment_type,
        "name": name,
        "source_reference": {"raw_path": f"{source}/{source_equipment_id}.json"},
    }


def _activity(
    source: str,
    source_activity_id: str,
    distance_m: float,
    moving_time_s: int,
    gear: dict,
) -> dict:
    return {
        "schema_version": "nono.normalized_activity.v1",
        "activity_uid": f"{source}:activity:{source_activity_id}",
        "source": source,
        "source_activity_id": source_activity_id,
        "duration": {
            "moving_time_s": moving_time_s,
            "elapsed_time_s": moving_time_s + 10,
        },
        "distance": {"distance_m": distance_m},
        "gear": gear,
    }


def _consolidated_activity(
    source_activity_id: str,
    source_links: list[tuple[str, str, int]],
) -> dict:
    return {
        "schema_version": "nono.consolidated_activity.v1",
        "consolidated_activity_uid": f"consolidated:activity:{source_activity_id}",
        "source_activity_uids": [activity_uid for _, activity_uid, _ in source_links],
        "provenance": {
            "source_links": [
                {
                    "source": source,
                    "activity_uid": activity_uid,
                    "source_priority": source_priority,
                }
                for source, activity_uid, source_priority in source_links
            ]
        },
    }
