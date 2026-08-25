from pathlib import Path

import pytest

from nono_sports.storage.consolidated_store import ConsolidatedStore
from nono_sports.storage.source_normalized_store import SourceNormalizedStore


def test_source_normalized_jsonl_does_not_read_existing_file_into_memory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = SourceNormalizedStore(tmp_path / "normalizado")
    records = [{"id": 1, "values": list(range(10))}]

    first = store.write_jsonl("streams.jsonl", records)

    def fail_read_bytes(self):  # noqa: ANN001
        raise AssertionError("read_bytes should not be used for JSONL comparison")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    second = store.write_jsonl("streams.jsonl", records)

    assert second.sha256 == first.sha256
    assert second.bytes_written == first.bytes_written


def test_consolidated_jsonl_does_not_read_existing_file_into_memory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = ConsolidatedStore(tmp_path)
    records = [{"id": 1, "values": list(range(10))}]

    first = store.write_jsonl("activities.jsonl", records)

    def fail_read_bytes(self):  # noqa: ANN001
        raise AssertionError("read_bytes should not be used for JSONL comparison")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    second = store.write_jsonl("activities.jsonl", records)

    assert second.sha256 == first.sha256
    assert second.bytes_written == first.bytes_written


def test_source_normalized_jsonl_removes_temporary_file_on_error(
    tmp_path: Path,
) -> None:
    store = SourceNormalizedStore(tmp_path / "normalizado")

    with pytest.raises(RuntimeError, match="boom"):
        store.write_jsonl("streams.jsonl", _failing_records())

    assert not (tmp_path / "normalizado" / ".streams.jsonl.tmp").exists()
    assert not (tmp_path / "normalizado" / "streams.jsonl").exists()


def test_consolidated_jsonl_removes_temporary_file_on_error(tmp_path: Path) -> None:
    store = ConsolidatedStore(tmp_path)

    with pytest.raises(RuntimeError, match="boom"):
        store.write_jsonl("activities.jsonl", _failing_records())

    assert not (
        tmp_path / "20_consolidado" / ".activities.jsonl.tmp"
    ).exists()
    assert not (tmp_path / "20_consolidado" / "activities.jsonl").exists()


def _failing_records():
    yield {"id": 1}
    raise RuntimeError("boom")
