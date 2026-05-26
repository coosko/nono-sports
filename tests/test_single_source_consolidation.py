import json
from datetime import UTC, datetime
from pathlib import Path

from nono_sports.consolidation.single_source import build_single_source_consolidated
from nono_sports.storage.normalized_store import NormalizedStore


def test_build_single_source_consolidated_writes_nono_dataset(
    tmp_path: Path,
) -> None:
    NormalizedStore(tmp_path).write_jsonl(
        "activities.jsonl",
        [
            {
                "activity_uid": "strava:activity:100",
                "source": "strava",
                "source_activity_id": "100",
                "title": "Morning Ride",
                "sport": {
                    "family": "cycling",
                    "discipline": "road_cycling",
                    "movement_context": "endurance_distance",
                },
                "start": {"start_at_utc": "2026-05-26T05:00:00Z"},
                "duration": {"moving_time_s": 1800},
                "distance": {"distance_m": 12000.0},
                "elevation": {"gain_m": 220.0},
                "energy": {"calories_kcal": 500.0},
                "metrics": {"average_heartrate_bpm": 140.0},
                "location": {"country": "Spain"},
                "gear": {"name": "Road Bike"},
                "flags": {"trainer": False},
                "completeness": {"has_streams": True},
                "laps": [{"lap_uid": "strava:activity:100:lap:1"}],
                "segments": [{"segment_uid": "strava:segment:200"}],
                "stream_uid": "strava:stream:100",
                "source_reference": {
                    "source": "strava",
                    "entity_type": "activity",
                    "source_id": "100",
                    "raw_path": "activities/100.json",
                },
                "source_links": [],
                "external_ids": {"external_id": "fit-file.fit"},
            }
        ],
    )

    result = build_single_source_consolidated(
        tmp_path,
        generated_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    assert result.activities == 1
    assert result.activity_sources == 1
    assert result.streams_index == 1
    assert {item.relative_path for item in result.written} == {
        "activities.jsonl",
        "activity_sources.jsonl",
        "streams_index.jsonl",
        "state.json",
    }
    activities = _read_jsonl(tmp_path, "activities.jsonl")
    assert activities[0]["consolidated_activity_uid"] == (
        "consolidated:activity:strava:activity:100"
    )
    assert activities[0]["primary_source"] == "strava"
    assert activities[0]["source_count"] == 1
    assert activities[0]["sport"]["family"] == "cycling"
    assert activities[0]["provenance"]["strategy"] == "single_source"
    links = _read_jsonl(tmp_path, "activity_sources.jsonl")
    assert links[0]["match_confidence"] == 1.0
    assert links[0]["match_strategy"] == "single_source"
    streams = _read_jsonl(tmp_path, "streams_index.jsonl")
    assert streams[0]["stream_uid"] == "strava:stream:100"
    state = json.loads(
        (tmp_path / "20_consolidado" / "state.json").read_text(encoding="utf-8")
    )
    assert state["counts"]["activities"] == 1


def _read_jsonl(tmp_path: Path, relative_path: str) -> list[dict]:
    path = tmp_path / "20_consolidado" / relative_path
    return [json.loads(line) for line in path.read_text().splitlines()]
