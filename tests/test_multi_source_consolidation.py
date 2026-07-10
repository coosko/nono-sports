import json
from datetime import UTC, datetime
from pathlib import Path

from nono_sports.consolidation.multi_source import build_multi_source_consolidated


def test_build_multi_source_consolidated_keeps_single_source_contract(
    tmp_path: Path,
) -> None:
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl",
        [_activity("strava", "100")],
    )

    result = build_multi_source_consolidated(
        tmp_path,
        generated_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    assert result.activities == 1
    assert result.activity_sources == 1
    assert result.streams_index == 1
    assert result.duplicate_candidates == 0
    assert {item.relative_path for item in result.written} == {
        "activities.jsonl",
        "activity_sources.jsonl",
        "streams_index.jsonl",
        "duplicate_candidates.jsonl",
        "state.json",
    }
    activities = _read_consolidated_jsonl(tmp_path, "activities.jsonl")
    assert activities[0]["primary_source"] == "strava"
    assert activities[0]["source_count"] == 1
    assert activities[0]["provenance"]["strategy"] == "multi_source_initial"


def test_build_multi_source_consolidated_groups_matching_sources(
    tmp_path: Path,
) -> None:
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl",
        [_activity("strava", "100")],
    )
    _write_jsonl(
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "normalizado"
        / "activities.jsonl",
        [
            _activity(
                "garmin_connect",
                "abc",
                start_at_utc="2026-05-26T05:00:20Z",
                moving_time_s=1810,
                distance_m=12025.0,
                stream_uid="garmin_connect:stream:abc",
            )
        ],
    )

    result = build_multi_source_consolidated(
        tmp_path,
        generated_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    assert result.activities == 1
    assert result.activity_sources == 2
    assert result.streams_index == 2
    assert result.duplicate_candidates == 1
    activities = _read_consolidated_jsonl(tmp_path, "activities.jsonl")
    assert activities[0]["primary_source"] == "strava"
    assert activities[0]["source_count"] == 2
    assert activities[0]["source_activity_uids"] == [
        "strava:activity:100",
        "garmin_connect:activity:abc",
    ]
    links = _read_consolidated_jsonl(tmp_path, "activity_sources.jsonl")
    assert [link["source"] for link in links] == ["strava", "garmin_connect"]
    candidates = _read_consolidated_jsonl(tmp_path, "duplicate_candidates.jsonl")
    assert candidates[0]["match_strategy"] == "time_duration_distance_sport"
    assert candidates[0]["confidence"] >= 0.95


def test_build_multi_source_consolidated_groups_when_garmin_existed_first(
    tmp_path: Path,
) -> None:
    _write_jsonl(
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "normalizado"
        / "activities.jsonl",
        [_activity("garmin_connect", "abc", stream_uid="garmin_connect:stream:abc")],
    )
    result_before_strava = build_multi_source_consolidated(tmp_path)

    assert result_before_strava.activities == 1
    assert result_before_strava.activity_sources == 1

    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl",
        [
            _activity(
                "strava",
                "100",
                start_at_utc="2026-05-26T05:00:20Z",
                moving_time_s=1810,
                distance_m=12025.0,
            )
        ],
    )

    result_after_strava = build_multi_source_consolidated(tmp_path)

    assert result_after_strava.activities == 1
    assert result_after_strava.activity_sources == 2
    assert result_after_strava.duplicate_candidates == 1
    activities = _read_consolidated_jsonl(tmp_path, "activities.jsonl")
    assert activities[0]["primary_source"] == "strava"
    assert activities[0]["source_activity_uids"] == [
        "strava:activity:100",
        "garmin_connect:activity:abc",
    ]


def test_groups_garmin_indoor_import_and_prefers_garmin_sport(
    tmp_path: Path,
) -> None:
    strava = _activity("strava", "100", distance_m=0.0)
    strava["external_ids"]["external_id"] = "garmin_ping_123"
    garmin = _activity("garmin_connect", "abc", distance_m=0.0)
    garmin["sport"] = {
        "family": "other",
        "discipline": "indoor_cycling",
        "movement_context": "unknown",
    }
    garmin["duration"]["moving_time_s"] = 2400
    _write_source_activities(tmp_path, strava=[strava], garmin=[garmin])

    result = build_multi_source_consolidated(tmp_path)

    assert result.activities == 1
    activity = _read_consolidated_jsonl(tmp_path, "activities.jsonl")[0]
    assert activity["sport"]["discipline"] == "indoor_cycling"
    candidate = _read_consolidated_jsonl(
        tmp_path,
        "duplicate_candidates.jsonl",
    )[0]
    assert candidate["match_strategy"] == "garmin_import_start_distance"


def test_groups_cycling_with_delayed_start_when_distance_and_moving_time_match(
    tmp_path: Path,
) -> None:
    strava = _activity(
        "strava",
        "100",
        start_at_utc="2022-12-04T08:36:57Z",
        moving_time_s=5594,
        distance_m=43958.4,
    )
    garmin = _activity(
        "garmin_connect",
        "abc",
        start_at_utc="2022-12-04T08:29:02Z",
        moving_time_s=5554,
        distance_m=43958.4,
    )
    _write_source_activities(tmp_path, strava=[strava], garmin=[garmin])

    result = build_multi_source_consolidated(tmp_path)

    assert result.activities == 1
    candidate = _read_consolidated_jsonl(
        tmp_path,
        "duplicate_candidates.jsonl",
    )[0]
    assert candidate["match_strategy"] == (
        "cycling_duration_distance_delayed_start"
    )
    assert candidate["signals"]["start_delta_s"] == 475.0


def test_groups_compatible_sport_with_same_start_and_distance(
    tmp_path: Path,
) -> None:
    strava = _activity("strava", "100", moving_time_s=1200, distance_m=8500.0)
    strava["sport"] = {
        "family": "walking_hiking",
        "discipline": "hiking",
    }
    garmin = _activity(
        "garmin_connect",
        "abc",
        start_at_utc="2026-05-26T05:00:01Z",
        moving_time_s=1800,
        distance_m=8501.0,
    )
    garmin["sport"] = {
        "family": "walking_hiking",
        "discipline": "hiking",
    }
    _write_source_activities(tmp_path, strava=[strava], garmin=[garmin])

    result = build_multi_source_consolidated(tmp_path)

    assert result.activities == 1
    candidate = _read_consolidated_jsonl(
        tmp_path,
        "duplicate_candidates.jsonl",
    )[0]
    assert candidate["match_strategy"] == "synchronized_start_distance_sport"


def _write_source_activities(
    tmp_path: Path,
    *,
    strava: list[dict],
    garmin: list[dict],
) -> None:
    _write_jsonl(
        tmp_path / "10_fuentes" / "strava" / "normalizado" / "activities.jsonl",
        strava,
    )
    _write_jsonl(
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "normalizado"
        / "activities.jsonl",
        garmin,
    )


def _activity(
    source: str,
    source_id: str,
    *,
    start_at_utc: str = "2026-05-26T05:00:00Z",
    moving_time_s: int = 1800,
    distance_m: float = 12000.0,
    stream_uid: str | None = "strava:stream:100",
) -> dict:
    activity_uid = f"{source}:activity:{source_id}"
    return {
        "activity_uid": activity_uid,
        "source": source,
        "source_activity_id": source_id,
        "title": "Morning Ride",
        "sport": {
            "family": "cycling",
            "discipline": "road_cycling",
            "movement_context": "endurance_distance",
        },
        "start": {"start_at_utc": start_at_utc},
        "duration": {"moving_time_s": moving_time_s},
        "distance": {"distance_m": distance_m},
        "elevation": {"gain_m": 220.0},
        "energy": {"calories_kcal": 500.0},
        "metrics": {"average_heartrate_bpm": 140.0},
        "location": {"country": "Spain"},
        "gear": {"name": "Road Bike"},
        "flags": {"trainer": False},
        "completeness": {"has_streams": stream_uid is not None},
        "laps": [{"lap_uid": f"{activity_uid}:lap:1"}],
        "segments": [],
        "stream_uid": stream_uid,
        "source_reference": {
            "source": source,
            "entity_type": "activity",
            "source_id": source_id,
            "raw_path": f"activities/{source_id}.json",
        },
        "source_links": [],
        "external_ids": {"external_id": f"{source_id}.fit"},
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _read_consolidated_jsonl(tmp_path: Path, relative_path: str) -> list[dict]:
    path = tmp_path / "20_consolidado" / relative_path
    return [json.loads(line) for line in path.read_text().splitlines()]
