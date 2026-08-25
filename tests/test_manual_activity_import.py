import json
from datetime import UTC, datetime
from pathlib import Path

from nono_sports.consolidation.multi_source import build_multi_source_consolidated
from nono_sports.normalization.manual_activities import (
    import_manual_gpx_activity,
    normalize_manual_activities,
)


def test_import_manual_gpx_activity_copies_raw_and_normalizes(
    tmp_path: Path,
) -> None:
    source_gpx = tmp_path / "komoot-route.gpx"
    source_gpx.write_text(_gpx_fixture(), encoding="utf-8")

    imported = import_manual_gpx_activity(
        tmp_path,
        source_gpx,
        sport="hiking",
        source_platform="komoot",
        title="Circular manual",
        generated_at=datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
    )
    result = normalize_manual_activities(
        tmp_path,
        generated_at=datetime(2026, 8, 25, 10, 5, tzinfo=UTC),
    )

    assert imported.activity_id.startswith("komoot_")
    assert imported.raw_path.startswith("activities/komoot_")
    assert (
        tmp_path / "10_fuentes" / "manual" / "raw" / imported.raw_path
    ).is_file()
    assert result.activities == 1
    assert result.streams == 1
    assert result.streams_index == 1
    assert {item.relative_path for item in result.written} == {
        "activities.jsonl",
        "streams.jsonl",
        "streams_index.jsonl",
        "state.json",
    }

    activities = _read_jsonl(
        tmp_path / "10_fuentes" / "manual" / "normalizado" / "activities.jsonl"
    )
    activity = activities[0]
    assert activity["activity_uid"] == f"manual:activity:{imported.activity_id}"
    assert activity["title"] == "Circular manual"
    assert activity["sport"]["family"] == "walking_hiking"
    assert activity["sport"]["discipline"] == "hiking"
    assert activity["start"]["start_at_utc"] == "2026-08-25T06:00:00Z"
    assert activity["duration"]["elapsed_time_s"] == 120
    assert activity["duration"]["moving_time_s"] == 120
    assert 220.0 < activity["distance"]["distance_m"] < 223.0
    assert activity["elevation"]["gain_m"] == 12.0
    assert activity["elevation"]["loss_m"] == 4.0
    assert activity["flags"]["manual_import"] is True
    assert activity["completeness"]["has_gpx"] is True
    assert activity["sport_specific"]["source_platform"] == "komoot"
    assert activity["sport_specific"]["original_file_format"] == "gpx"

    streams = _read_jsonl(
        tmp_path / "10_fuentes" / "manual" / "normalizado" / "streams.jsonl"
    )
    assert streams[0]["stream_uid"] == f"manual:stream:{imported.activity_id}"
    assert streams[0]["samples"]["time"] == 3
    assert streams[0]["streams"]["distance"]["unit"] == "m"
    assert streams[0]["streams"]["latlng"]["values"][0] == [40.0, -3.0]

    manifest_lines = _read_jsonl(
        tmp_path / "10_fuentes" / "manual" / "raw" / "manifest.jsonl"
    )
    assert manifest_lines[0]["kind"] == "manual_import"
    assert manifest_lines[0]["params"]["source_platform"] == "komoot"


def test_multi_source_consolidation_includes_manual_with_lower_priority(
    tmp_path: Path,
) -> None:
    manual = _activity("manual", "komoot_1", start_at_utc="2026-08-25T06:00:00Z")
    garmin = _activity(
        "garmin_connect",
        "234",
        start_at_utc="2026-08-25T06:00:20Z",
    )
    _write_jsonl(
        tmp_path / "10_fuentes" / "manual" / "normalizado" / "activities.jsonl",
        [manual],
    )
    _write_jsonl(
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "normalizado"
        / "activities.jsonl",
        [garmin],
    )

    result = build_multi_source_consolidated(tmp_path)

    assert result.activities == 1
    assert result.activity_sources == 2
    activities = _read_jsonl(tmp_path / "20_consolidado" / "activities.jsonl")
    assert activities[0]["primary_source"] == "garmin_connect"
    assert activities[0]["source_activity_uids"] == [
        "garmin_connect:activity:234",
        "manual:activity:komoot_1",
    ]
    links = _read_jsonl(tmp_path / "20_consolidado" / "activity_sources.jsonl")
    assert [link["source"] for link in links] == ["garmin_connect", "manual"]


def _gpx_fixture() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Circular manual</name>
    <trkseg>
      <trkpt lat="40.0" lon="-3.0">
        <ele>700.0</ele>
        <time>2026-08-25T06:00:00Z</time>
      </trkpt>
      <trkpt lat="40.001" lon="-3.0">
        <ele>712.0</ele>
        <time>2026-08-25T06:01:00Z</time>
      </trkpt>
      <trkpt lat="40.002" lon="-3.0">
        <ele>708.0</ele>
        <time>2026-08-25T06:02:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def _activity(
    source: str,
    source_activity_id: str,
    *,
    start_at_utc: str,
) -> dict:
    activity_uid = f"{source}:activity:{source_activity_id}"
    return {
        "schema_version": "nono.normalized_activity.v1",
        "activity_uid": activity_uid,
        "source": source,
        "source_activity_id": source_activity_id,
        "title": "Circular",
        "sport": {
            "family": "walking_hiking",
            "discipline": "hiking",
            "movement_context": "endurance_distance",
        },
        "start": {"start_at_utc": start_at_utc},
        "duration": {"moving_time_s": 120, "elapsed_time_s": 120},
        "distance": {"distance_m": 222.39},
        "elevation": {"gain_m": 12.0},
        "energy": {},
        "metrics": {},
        "location": {},
        "gear": {},
        "flags": {},
        "completeness": {"has_streams": True},
        "laps": [],
        "segments": [],
        "stream_uid": f"{source}:stream:{source_activity_id}",
        "source_reference": {
            "source": source,
            "entity_type": "activity",
            "source_id": source_activity_id,
            "raw_path": f"activities/{source_activity_id}.json",
        },
        "source_links": [],
        "external_ids": {},
    }


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
