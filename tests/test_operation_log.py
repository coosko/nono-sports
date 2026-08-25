import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from nono_sports.core.operation_log import OperationalRunRecorder


def test_operational_run_recorder_appends_local_jsonl(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    clock = _Clock()
    recorder = OperationalRunRecorder(
        command="garmin sync",
        source="garmin_connect",
        argv=["garmin", "sync", "--code", "secret-code", "--limit", "20"],
        data_root=tmp_path / "data",
        clock=clock.now,
        monotonic=clock.monotonic,
    )

    with recorder.phase("fetch.activities") as phase:
        clock.tick(seconds=2.5)
        phase.set(
            counts={"listed_activities": 20, "written_files": 1},
            outputs={"state": tmp_path / "data" / "state.json"},
        )
    recorder.skip_phase("fetch.measurements", "--skip-fetch")
    recorder.finish(status="success", exit_code=0)

    path = recorder.append()

    assert path == tmp_path / "state" / "nono-sports" / "logs" / "operation_runs.jsonl"
    payloads = _read_jsonl(path)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["schema_version"] == "nono.operational_run.v1"
    assert payload["command"] == "garmin sync"
    assert payload["source"] == "garmin_connect"
    assert payload["status"] == "success"
    assert payload["exit_code"] == 0
    assert payload["argv"] == [
        "garmin",
        "sync",
        "--code",
        "<redacted>",
        "--limit",
        "20",
    ]
    assert payload["phases"][0]["name"] == "fetch.activities"
    assert payload["phases"][0]["duration_seconds"] == 2.5
    assert payload["phases"][0]["counts"]["listed_activities"] == 20
    assert payload["phases"][0]["outputs"]["state"].endswith("state.json")
    assert payload["phases"][1]["status"] == "skipped"


def test_operational_run_recorder_records_failed_phase(tmp_path: Path) -> None:
    clock = _Clock()
    recorder = OperationalRunRecorder(
        command="manual import-gpx",
        source="manual",
        argv=["manual", "import-gpx"],
        log_path=tmp_path / "runs.jsonl",
        clock=clock.now,
        monotonic=clock.monotonic,
    )

    try:
        with recorder.phase("import.gpx"):
            clock.tick(seconds=1)
            raise ValueError("bad GPX")
    except ValueError as error:
        recorder.finish(status="error", exit_code=1, error=error)

    recorder.append()

    payload = _read_jsonl(tmp_path / "runs.jsonl")[0]
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "ValueError"
    assert payload["phases"][0]["status"] == "failed"
    assert payload["phases"][0]["error"]["message"] == "bad GPX"


class _Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
        self._monotonic = 100.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def tick(self, *, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
        self._monotonic += seconds


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
