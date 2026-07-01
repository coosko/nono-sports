"""Garmin Connect raw storage."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.storage.manifest import RawManifestEntry
from nono_sports.storage.raw_store import MANIFEST_FILENAME, RawWriteResult


class GarminRawStore:
    def __init__(
        self,
        data_root: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.raw_root = garmin_connect_path(data_root, "raw")
        self._clock = clock or (lambda: datetime.now(UTC))

    def write_json(
        self,
        relative_path: str | Path,
        payload: Any,
        *,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        kind: str = "response",
    ) -> RawWriteResult:
        content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        return self.write_bytes(
            relative_path,
            f"{content}\n".encode("utf-8"),
            endpoint=endpoint,
            params=params,
            kind=kind,
        )

    def write_bytes(
        self,
        relative_path: str | Path,
        payload: bytes,
        *,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        kind: str = "response",
    ) -> RawWriteResult:
        path = self._resolve_relative_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        relative = path.relative_to(self.raw_root).as_posix()
        result = RawWriteResult(
            path=path,
            relative_path=relative,
            sha256=digest,
            bytes_written=len(payload),
        )
        self._append_manifest(
            RawManifestEntry(
                generated_at=self._clock().astimezone(UTC).isoformat(),
                kind=kind,
                endpoint=endpoint,
                params=dict(params or {}),
                path=relative,
                sha256=digest,
                bytes_written=len(payload),
            )
        )
        return result

    def _resolve_relative_path(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ValueError("Raw paths must be relative to the Garmin raw root.")
        root = self.raw_root.resolve()
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Raw paths must stay inside the Garmin raw root.")
        return target

    def _append_manifest(self, entry: RawManifestEntry) -> None:
        manifest_path = self.raw_root / MANIFEST_FILENAME
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("a", encoding="utf-8") as manifest_file:
            manifest_file.write(
                json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True) + "\n"
            )
