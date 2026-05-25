import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nono_sports.storage.raw_store import RawStore


def test_raw_store_writes_json_under_strava_raw_root(tmp_path) -> None:
    store = RawStore(
        tmp_path,
        clock=lambda: datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )

    result = store.write_json(
        "athlete/profile.json",
        {"id": 42, "name": "Nono"},
        endpoint="/athlete",
    )

    assert result.relative_path == "athlete/profile.json"
    assert result.path == (
        tmp_path / "10_fuentes" / "strava" / "raw" / "athlete" / "profile.json"
    )
    assert json.loads(result.path.read_text()) == {"id": 42, "name": "Nono"}

    manifest_path = tmp_path / "10_fuentes" / "strava" / "raw" / "manifest.jsonl"
    entries = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    assert entries == [
        {
            "bytes_written": result.bytes_written,
            "endpoint": "/athlete",
            "generated_at": "2026-05-24T12:00:00+00:00",
            "kind": "response",
            "params": {},
            "path": "athlete/profile.json",
            "sha256": result.sha256,
        }
    ]


def test_raw_store_rejects_absolute_paths(tmp_path) -> None:
    store = RawStore(tmp_path)

    with pytest.raises(ValueError, match="relative"):
        store.write_json(Path("/") / "outside.json", {}, endpoint="/athlete")


def test_raw_store_writes_non_json_payloads(tmp_path) -> None:
    store = RawStore(tmp_path)

    result = store.write_bytes(
        "route_exports/gpx/100.gpx",
        b"<gpx />\n",
        endpoint="/routes/100/export_gpx",
    )

    assert result.relative_path == "route_exports/gpx/100.gpx"
    assert result.path.read_bytes() == b"<gpx />\n"


def test_raw_store_rejects_path_traversal(tmp_path) -> None:
    store = RawStore(tmp_path)

    with pytest.raises(ValueError, match="inside"):
        store.write_json("../outside.json", {}, endpoint="/athlete")
