"""Lightweight input fingerprints for incremental pipelines."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

FINGERPRINT_SCHEMA_VERSION = "nono.input_fingerprint.v1"


def build_file_fingerprint(
    root: Path,
    patterns: Iterable[str],
    *,
    manifest_path: Path | None = None,
    exclude: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    """Return a stable, lightweight fingerprint of files under ``root``.

    Manifest SHA256 values are preferred because some raw files can be rewritten
    with the same content. When a file has no manifest entry, size and mtime keep
    the fingerprint cheap without reading potentially large files from Drive.
    """

    root = root.resolve()
    manifest = _read_manifest_sha_index(manifest_path) if manifest_path else {}
    files: dict[str, dict[str, Any]] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if exclude is not None and exclude(path):
                continue
            relative_path = path.resolve().relative_to(root).as_posix()
            stat = path.stat()
            entry: dict[str, Any] = {
                "path": relative_path,
                "size": stat.st_size,
            }
            sha256 = manifest.get(relative_path)
            if sha256:
                entry["sha256"] = sha256
            else:
                entry["mtime_ns"] = stat.st_mtime_ns
            files[relative_path] = entry
    return {
        "schema_version": FINGERPRINT_SCHEMA_VERSION,
        "files": {path: files[path] for path in sorted(files)},
    }


def required_outputs_exist(root: Path, relative_paths: Iterable[str]) -> bool:
    return all((root / relative_path).is_file() for relative_path in relative_paths)


def state_fingerprint(state: Any) -> dict[str, Any]:
    inputs = state.get("inputs") if isinstance(state, dict) else None
    fingerprint = inputs.get("input_fingerprint") if isinstance(inputs, dict) else None
    return fingerprint if isinstance(fingerprint, dict) else {}


def state_counts(state: Any) -> dict[str, Any]:
    counts = state.get("counts") if isinstance(state, dict) else None
    return counts if isinstance(counts, dict) else {}


def is_incremental_state_current(
    state: Any,
    fingerprint: dict[str, Any],
    *,
    output_root: Path,
    required_outputs: Iterable[str],
) -> bool:
    return (
        bool(state_fingerprint(state))
        and state_fingerprint(state) == fingerprint
        and required_outputs_exist(output_root, required_outputs)
    )


def _read_manifest_sha_index(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    index: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as manifest_file:
        for line in manifest_file:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            path_value = payload.get("path")
            sha256 = payload.get("sha256")
            if isinstance(path_value, str) and isinstance(sha256, str):
                index[path_value] = sha256
    return index
