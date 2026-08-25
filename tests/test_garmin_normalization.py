import json
from pathlib import Path
from unittest.mock import patch

import nono_sports.normalization.garmin_dataset as garmin_dataset_module
from nono_sports.formats.fit import FitDecodeResult
from nono_sports.normalization.garmin_dataset import normalize_garmin_dataset


def test_normalize_garmin_dataset_writes_common_outputs(tmp_path: Path) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    _write_json(raw_root / "activities" / "234.details.json", {"activityId": 234})
    _write_json(raw_root / "fit_decoded" / "234.fitdecode.json", _fitdecode_payload())
    _write_json(raw_root / "splits" / "234.json", {"activityId": 234, "lapDTOs": []})
    _write_json(raw_root / "typed_splits" / "234.json", {"activityId": 234})
    _write_json(raw_root / "weather" / "234.json", {"condition": "sunny"})
    _write_json(
        raw_root / "gear" / "activity_234.json",
        {"gear": [{"gearUuid": "bike-1", "gearName": "Reacto"}]},
    )
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
    assert activity["completeness"]["has_activity_gear"] is True
    assert activity["gear"]["activity_gear"]["gear"][0]["gearName"] == "Reacto"

    streams = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "streams.jsonl"
    )
    assert streams[0]["samples"]["time"] == 2
    assert streams[0]["samples"]["hrv"] == 2
    assert streams[0]["streams"]["heartrate"]["values"] == [88, 90]


def test_normalize_garmin_dataset_reuses_unchanged_activity(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    _write_json(raw_root / "fit_decoded" / "234.fitdecode.json", _fitdecode_payload())
    _write_manifest(raw_root / "manifest.jsonl")

    first = normalize_garmin_dataset(tmp_path)
    second = normalize_garmin_dataset(tmp_path)

    assert first.processed_activities == 1
    assert first.reused_activities == 0
    assert second.processed_activities == 0
    assert second.reused_activities == 1


def test_normalize_garmin_dataset_decodes_fit_without_persisted_json(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    fit_path = raw_root / "activity_files" / "234.fit"
    _write_text(fit_path, "temporary FIT fixture")
    _write_manifest(
        raw_root / "manifest.jsonl",
        [
            {"path": "activities/234.json", "sha256": "activity"},
            {"path": "activity_files/234.fit", "sha256": "fit"},
        ],
    )

    decoded = FitDecodeResult(
        backend="fitdecode",
        messages=_fitdecode_payload()["messages"],
        frames=2,
    )
    with patch(
        "nono_sports.normalization.garmin_dataset.decode_fit_with_fitdecode",
        return_value=decoded,
    ) as decode:
        first = normalize_garmin_dataset(tmp_path)
        second = normalize_garmin_dataset(tmp_path)

    assert first.streams == 1
    assert second.reused_activities == 1
    decode.assert_called_once_with(
        fit_path,
        message_names=frozenset({"record", "hrv", "lap", "time_in_zone"}),
    )
    assert not (raw_root / "fit_decoded" / "234.fitdecode.json").exists()


def test_normalize_garmin_dataset_can_keep_diagnostic_fit_json(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    fit_path = raw_root / "activity_files" / "234.fit"
    _write_text(fit_path, "temporary FIT fixture")
    _write_manifest(
        raw_root / "manifest.jsonl",
        [
            {"path": "activities/234.json", "sha256": "activity"},
            {"path": "activity_files/234.fit", "sha256": "fit"},
        ],
    )

    decoded = FitDecodeResult(
        backend="fitdecode",
        messages=_fitdecode_payload()["messages"],
        frames=2,
    )
    with patch(
        "nono_sports.normalization.garmin_dataset.decode_fit_with_fitdecode",
        return_value=decoded,
    ) as decode:
        result = normalize_garmin_dataset(
            tmp_path,
            keep_intermediate_files=True,
        )

    assert result.processed_activities == 1
    decode.assert_called_once_with(fit_path, message_names=None)
    decoded_path = raw_root / "fit_decoded" / "234.fitdecode.json"
    assert decoded_path.is_file()
    payload = json.loads(decoded_path.read_text(encoding="utf-8"))
    assert payload["messages"]["record"][0]["heart_rate"] == 88

    activity = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "activities.jsonl"
    )[0]
    source_paths = {link["raw_path"] for link in activity["source_links"]}
    assert "activity_files/234.fit" in source_paths
    assert "fit_decoded/234.fitdecode.json" in source_paths


def test_normalize_garmin_dataset_reuses_existing_output_without_fitdecode_json(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    fit_path = raw_root / "activity_files" / "234.fit"
    _write_text(fit_path, "temporary FIT fixture")
    _write_manifest(
        raw_root / "manifest.jsonl",
        [
            {"path": "activities/234.json", "sha256": "activity"},
            {"path": "activity_files/234.fit", "sha256": "fit"},
        ],
    )

    decoded = FitDecodeResult(
        backend="fitdecode",
        messages=_fitdecode_payload()["messages"],
        frames=2,
    )
    with patch(
        "nono_sports.normalization.garmin_dataset.decode_fit_with_fitdecode",
        return_value=decoded,
    ) as decode:
        first = normalize_garmin_dataset(tmp_path)
        second = normalize_garmin_dataset(tmp_path)

    assert first.processed_activities == 1
    assert second.processed_activities == 0
    assert second.reused_activities == 1
    decode.assert_called_once()
    assert not (raw_root / "fit_decoded" / "234.fitdecode.json").exists()


def test_normalize_garmin_dataset_does_not_load_previous_streams_jsonl(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    _write_json(raw_root / "fit_decoded" / "234.fitdecode.json", _fitdecode_payload())
    _write_manifest(raw_root / "manifest.jsonl")

    normalize_garmin_dataset(tmp_path)
    original_read_jsonl = garmin_dataset_module._read_jsonl

    def guarded_read_jsonl(path: Path):
        if path.name == "streams.jsonl":
            raise AssertionError("streams.jsonl must be reused with the offset reader")
        return original_read_jsonl(path)

    monkeypatch.setattr(garmin_dataset_module, "_read_jsonl", guarded_read_jsonl)

    result = normalize_garmin_dataset(tmp_path)

    assert result.processed_activities == 0
    assert result.reused_activities == 1
    assert result.streams == 1


def test_normalize_garmin_dataset_sanitizes_reused_missing_fitdecode_reference(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    _write_json(raw_root / "activities" / "234.json", _activity_payload())
    _write_text(raw_root / "activity_files" / "234.fit", "temporary FIT fixture")
    fitdecoded_path = raw_root / "fit_decoded" / "234.fitdecode.json"
    _write_json(fitdecoded_path, _fitdecode_payload())
    _write_manifest(
        raw_root / "manifest.jsonl",
        [
            {"path": "activities/234.json", "sha256": "activity"},
            {"path": "activity_files/234.fit", "sha256": "fit"},
            {"path": "fit_decoded/234.fitdecode.json", "sha256": "fitdecode"},
        ],
    )

    first = normalize_garmin_dataset(tmp_path)
    fitdecoded_path.unlink()
    second = normalize_garmin_dataset(tmp_path)

    assert first.processed_activities == 1
    assert second.reused_activities == 1
    activity = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "activities.jsonl"
    )[0]
    source_paths = {link["raw_path"] for link in activity["source_links"]}
    assert "activity_files/234.fit" in source_paths
    assert "fit_decoded/234.fitdecode.json" not in source_paths

    stream = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "streams.jsonl"
    )[0]
    assert stream["source_reference"]["raw_path"] == "activity_files/234.fit"


def test_normalize_garmin_dataset_uses_gpx_stream_when_fit_is_missing(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    activity = _activity_payload()
    activity["activityId"] = 456
    activity["activityName"] = "Imported hike"
    activity["activityTypeDTO"] = {"typeKey": "hiking"}
    activity["metadataDTO"]["fileFormat"] = {"formatKey": "gpx"}
    activity["metadataDTO"]["isOriginal"] = False
    _write_json(raw_root / "activities" / "456.json", activity)
    _write_json(raw_root / "activities" / "456.details.json", {"activityId": 456})
    _write_text(
        raw_root / "activity_files" / "456.gpx",
        """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk><trkseg>
    <trkpt lat="40.0" lon="-3.0">
      <ele>700.0</ele><time>2026-06-29T18:42:22Z</time>
    </trkpt>
    <trkpt lat="40.1" lon="-3.1">
      <ele>701.0</ele><time>2026-06-29T18:42:32Z</time>
    </trkpt>
  </trkseg></trk>
</gpx>
""",
    )
    _write_manifest(
        raw_root / "manifest.jsonl",
        [
            {"path": "activities/456.json", "sha256": "activity"},
            {"path": "activities/456.details.json", "sha256": "details"},
            {"path": "activity_files/456.gpx", "sha256": "gpx"},
        ],
    )

    result = normalize_garmin_dataset(tmp_path)

    assert result.activities == 1
    assert result.streams == 1
    activity_record = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "activities.jsonl"
    )[0]
    assert activity_record["sport"]["discipline"] == "hiking"
    assert activity_record["completeness"]["has_fit"] is False
    assert activity_record["completeness"]["has_gpx"] is True
    assert activity_record["completeness"]["has_streams"] is True
    assert activity_record["completeness"]["complete_without_fit"] is True
    assert activity_record["stream_uid"] == "garmin_connect:stream:456"
    assert activity_record["sport_specific"]["original_file_format"] == "gpx"
    assert activity_record["sport_specific"]["is_original"] is False
    assert activity_record["sport_specific"]["source_origin"] == "imported_gpx"

    stream = _read_jsonl(
        tmp_path / "10_fuentes" / "garmin_connect" / "normalizado" / "streams.jsonl"
    )[0]
    assert stream["source_reference"]["raw_path"] == "activity_files/456.gpx"
    assert stream["samples"]["latlng"] == 2
    assert stream["streams"]["time"]["values"] == [0.0, 10.0]
    assert stream["streams"]["altitude"]["values"] == [700.0, 701.0]


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


def _write_manifest(path: Path, entries: list[dict] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = entries or [
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


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]
