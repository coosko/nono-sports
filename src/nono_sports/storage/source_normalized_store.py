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
        path = self._resolve_relative_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        bytes_written = 0
        temporary_path = _temporary_path(path)
        with temporary_path.open("wb") as output:
            for record in records:
                line = (
                    json.dumps(
                        _to_jsonable(record),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                ).encode("utf-8")
                output.write(line)
                digest.update(line)
                bytes_written += len(line)
        hexdigest = digest.hexdigest()
        _replace_if_changed(path, temporary_path, hexdigest)
        return SourceNormalizedWriteResult(
            path=path,
            relative_path=path.relative_to(self.normalized_root).as_posix(),
            sha256=hexdigest,
            records_written=len(records),
            bytes_written=bytes_written,
        )

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
        digest = hashlib.sha256(payload).hexdigest()
        temporary_path = _temporary_path(path)
        temporary_path.write_bytes(payload)
        _replace_if_changed(path, temporary_path, digest)
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


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp")


def _replace_if_changed(path: Path, temporary_path: Path, digest: str) -> None:
    if path.exists() and _file_sha256(path) == digest:
        temporary_path.unlink()
        return
    temporary_path.replace(path)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
