"""Non-blocking file locks for operational commands."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from nono_sports.core.errors import NonoSportsError


class FileLockUnavailableError(NonoSportsError):
    """Raised when another process already holds a lock."""


@contextmanager
def acquire_file_lock(path: Path) -> Iterator[None]:
    try:
        import fcntl
    except ImportError as error:  # pragma: no cover - Windows fallback.
        raise NonoSportsError("File locks require a Unix-like system.") from error

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise FileLockUnavailableError(
                f"Another nono-sports process holds lock: {path}"
            ) from error
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
