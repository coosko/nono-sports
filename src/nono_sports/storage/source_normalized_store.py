"""Normalized dataset storage for one source."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from types import TracebackType
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
        records: Iterable[Any],
    ) -> SourceNormalizedWriteResult:
        with self.open_jsonl(relative_path) as writer:
            for record in records:
                writer.write_record(record)
            return writer.finish()

    def open_jsonl(
        self,
        relative_path: str | Path,
    ) -> "SourceNormalizedJsonlWriter":
        path = self._resolve_relative_path(relative_path)
        return SourceNormalizedJsonlWriter(path, self.normalized_root)

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


class SourceNormalizedJsonlWriter:
    def __init__(self, path: Path, normalized_root: Path) -> None:
        self._path = path
        self._normalized_root = normalized_root
        self._temporary_path = _temporary_path(path)
        self._digest = hashlib.sha256()
        self._bytes_written = 0
        self._records_written = 0
        self._output: Any | None = None
        self._finished = False

    def __enter__(self) -> "SourceNormalizedJsonlWriter":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._output = self._temporary_path.open("wb")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._output is not None and not self._output.closed:
            self._output.close()
        if exc_type is not None and self._temporary_path.exists():
            self._temporary_path.unlink()

    def write_record(self, record: Any) -> None:
        line = (
            json.dumps(
                _to_jsonable(record),
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        self.write_encoded_line(line)

    def write_encoded_line(self, line: bytes | str) -> None:
        if self._output is None:
            raise RuntimeError("JSONL writer must be opened before writing.")
        payload = line.encode("utf-8") if isinstance(line, str) else line
        if not payload.endswith(b"\n"):
            payload += b"\n"
        self._output.write(payload)
        self._digest.update(payload)
        self._bytes_written += len(payload)
        self._records_written += 1

    def finish(self) -> SourceNormalizedWriteResult:
        if self._finished:
            raise RuntimeError("JSONL writer has already been finished.")
        if self._output is None:
            raise RuntimeError("JSONL writer must be opened before finishing.")
        self._output.close()
        digest = self._digest.hexdigest()
        _replace_if_changed(self._path, self._temporary_path, digest)
        self._finished = True
        return SourceNormalizedWriteResult(
            path=self._path,
            relative_path=self._path.relative_to(self._normalized_root).as_posix(),
            sha256=digest,
            records_written=self._records_written,
            bytes_written=self._bytes_written,
        )


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
