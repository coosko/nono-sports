"""Normalized dataset storage for one source."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceNormalizedWriteResult:
    path: Path
    relative_path: str
    sha256: str
    records_written: int
    bytes_written: int


class SourceNormalizedStore:
    def __init__(self, normalized_root: Path) -> None:
        self.normalized_root = normalized_root

    def write_jsonl(
        self,
        relative_path: str | Path,
        records: list[Any],
    ) -> SourceNormalizedWriteResult:
        payload = "".join(
            json.dumps(_to_jsonable(record), ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ).encode("utf-8")
        return self._write_bytes(relative_path, payload, len(records))

    def write_json(
        self,
        relative_path: str | Path,
        payload: Any,
    ) -> SourceNormalizedWriteResult:
        content = (
            json.dumps(
                _to_jsonable(payload),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        records_written = len(payload) if isinstance(payload, list) else 1
        return self._write_bytes(relative_path, content, records_written)

    def _write_bytes(
        self,
        relative_path: str | Path,
        payload: bytes,
        records_written: int,
    ) -> SourceNormalizedWriteResult:
        path = self._resolve_relative_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        return SourceNormalizedWriteResult(
            path=path,
            relative_path=path.relative_to(self.normalized_root).as_posix(),
            sha256=digest,
            records_written=records_written,
            bytes_written=len(payload),
        )

    def _resolve_relative_path(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ValueError("Normalized paths must be relative to the source root.")
        root = self.normalized_root.resolve()
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Normalized paths must stay inside the source root.")
        return target


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _drop_none(asdict(value))
    if isinstance(value, dict):
        return _drop_none({key: _to_jsonable(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: item for key, item in value.items() if item is not None}
    return value
