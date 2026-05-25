import json
from datetime import UTC, datetime

from nono_sports.storage.state_store import STATE_VERSION, StateStore


def test_state_store_returns_empty_state_when_missing(tmp_path) -> None:
    store = StateStore(
        tmp_path,
        clock=lambda: datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )

    state = store.load()

    assert state["version"] == STATE_VERSION
    assert state["activities"] == {}
    assert state["runs"] == []
    assert state["created_at"] == "2026-05-24T12:00:00+00:00"


def test_state_store_saves_json_atomically(tmp_path) -> None:
    store = StateStore(
        tmp_path,
        clock=lambda: datetime(2026, 5, 24, 12, 30, tzinfo=UTC),
    )

    store.save({"activities": {"1": {"detail": "activities/1.json"}}})

    saved = json.loads(store.path.read_text())
    assert saved["version"] == STATE_VERSION
    assert saved["updated_at"] == "2026-05-24T12:30:00+00:00"
    assert saved["activities"]["1"]["detail"] == "activities/1.json"
    assert not store.path.with_suffix(".json.tmp").exists()
