import json
from datetime import UTC, datetime
from pathlib import Path

from nono_sports.core.paths import ensure_strava_v1_directories
from nono_sports.storage.consolidated_store import ConsolidatedStore
from nono_sports.storage.normalized_store import NormalizedStore
from nono_sports.storage.raw_store import RawStore
from nono_sports.validation.checks import validate_strava_data
from nono_sports.validation.reports import write_validation_report


def test_validate_strava_data_passes_for_coherent_dataset(tmp_path: Path) -> None:
    _write_minimal_dataset(tmp_path)

    summary = validate_strava_data(
        tmp_path,
        generated_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    assert summary.status == "pass"
    assert summary.counts["raw_listed_activities"] == 1
    assert summary.counts["raw_activity_details"] == 1
    assert summary.counts["normalized_activities"] == 1
    assert summary.findings == ()


def test_validate_strava_data_warns_when_raw_download_is_incomplete(
    tmp_path: Path,
) -> None:
    _write_minimal_dataset(
        tmp_path,
        listed_activities=[
            {"id": 100, "name": "Morning Ride"},
            {"id": 101, "name": "Evening Ride"},
        ],
    )

    summary = validate_strava_data(tmp_path)

    assert summary.status == "warning"
    assert {finding.code for finding in summary.findings} == {
        "raw.activities_incomplete"
    }


def test_write_validation_report_writes_markdown(tmp_path: Path) -> None:
    _write_minimal_dataset(
        tmp_path,
        listed_activities=[
            {"id": 100, "name": "Morning Ride"},
            {"id": 101, "name": "Evening Ride"},
        ],
    )
    summary = validate_strava_data(tmp_path)

    report_path = write_validation_report(tmp_path, summary)

    assert report_path == tmp_path / "30_analisis" / "informes" / (
        "strava_validation_report.md"
    )
    content = report_path.read_text(encoding="utf-8")
    assert "# Informe de validación Strava" in content
    assert "`raw.activities_incomplete`" in content


def _write_minimal_dataset(
    tmp_path: Path,
    *,
    listed_activities: list[dict] | None = None,
) -> None:
    ensure_strava_v1_directories(tmp_path)
    raw_store = RawStore(tmp_path)
    activities = listed_activities or [{"id": 100, "name": "Morning Ride"}]
    raw_store.write_json(
        "activities/activities.json",
        activities,
        endpoint="/athlete/activities",
    )
    raw_store.write_json(
        "activities/100.json",
        {"id": 100, "name": "Morning Ride", "sport_type": "Ride"},
        endpoint="/activities/100",
    )
    raw_store.write_json(
        "streams/100.json",
        {"distance": {"data": [0.0], "original_size": 1}},
        endpoint="/activities/100/streams",
    )
    raw_store.write_json(
        "laps/100.json",
        [{"id": 1, "lap_index": 1}],
        endpoint="/activities/100/laps",
    )
    _write_state(tmp_path)
    NormalizedStore(tmp_path).write_jsonl(
        "athletes.jsonl",
        [{"athlete_uid": "strava:athlete:42"}],
    )
    NormalizedStore(tmp_path).write_jsonl(
        "activities.jsonl",
        [{"activity_uid": "strava:activity:100"}],
    )
    NormalizedStore(tmp_path).write_jsonl(
        "streams.jsonl",
        [{"stream_uid": "strava:stream:100"}],
    )
    ConsolidatedStore(tmp_path).write_jsonl(
        "activities.jsonl",
        [{"consolidated_activity_uid": "consolidated:activity:strava:activity:100"}],
    )
    ConsolidatedStore(tmp_path).write_jsonl(
        "activity_sources.jsonl",
        [{"consolidated_activity_uid": "consolidated:activity:strava:activity:100"}],
    )
    ConsolidatedStore(tmp_path).write_jsonl(
        "streams_index.jsonl",
        [{"stream_uid": "strava:stream:100"}],
    )
    ConsolidatedStore(tmp_path).write_json(
        "state.json",
        {"counts": {"activities": 1}},
    )


def _write_state(tmp_path: Path) -> None:
    state_path = (
        tmp_path
        / "10_fuentes"
        / "strava"
        / "logs"
        / "activity_sync_state.json"
    )
    state_path.write_text(
        json.dumps(
            {
                "activities": {
                    "100": {
                        "completed_at": "2026-05-26T00:00:00+00:00",
                        "detail": "activities/100.json",
                        "id": "100",
                        "laps": "laps/100.json",
                        "segments_checked": True,
                        "streams": "streams/100.json",
                    }
                },
                "runs": [],
                "version": 1,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
