"""Local structured operational run summaries.

Dataset checkpoints live under NONO_SPORT_DATA_ROOT so they travel with the
data. Operational logs describe how a local host executed a command, so they
belong in the XDG state directory next to locks and token state.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from nono_sports.core.paths import operation_runs_log_path

SCHEMA_VERSION = "nono.operational_run.v1"
SENSITIVE_OPTIONS = {
    "--access-token",
    "--client-secret",
    "--code",
    "--password",
    "--refresh-token",
    "--secret",
    "--token",
}


@dataclass
class _PhaseRecord:
    name: str
    status: str
    started_at: str
    completed_at: str
    duration_seconds: float
    counts: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    message: str | None = None
    error: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "name": self.name,
            "started_at": self.started_at,
            "status": self.status,
        }
        if self.counts:
            record["counts"] = _json_safe(self.counts)
        if self.outputs:
            record["outputs"] = _json_safe(self.outputs)
        if self.details:
            record["details"] = _json_safe(self.details)
        if self.message:
            record["message"] = self.message
        if self.error:
            record["error"] = self.error
        return record


class OperationalPhase:
    """Context manager used to time and annotate one command phase."""

    def __init__(self, recorder: OperationalRunRecorder, name: str) -> None:
        self._recorder = recorder
        self._name = name
        self._started_at: datetime | None = None
        self._started_monotonic: float | None = None
        self._counts: dict[str, Any] = {}
        self._outputs: dict[str, Any] = {}
        self._details: dict[str, Any] = {}
        self._message: str | None = None

    def __enter__(self) -> OperationalPhase:
        self._started_at = self._recorder.now()
        self._started_monotonic = self._recorder.monotonic()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del traceback
        started_at = self._started_at or self._recorder.now()
        started_monotonic = self._started_monotonic or self._recorder.monotonic()
        completed_at = self._recorder.now()
        status = "failed" if exc is not None else "success"
        error = _error_payload(exc) if exc is not None else None
        self._recorder.add_phase_record(
            _PhaseRecord(
                name=self._name,
                status=status,
                started_at=_isoformat(started_at),
                completed_at=_isoformat(completed_at),
                duration_seconds=_duration(
                    self._recorder.monotonic() - started_monotonic
                ),
                counts=self._counts,
                outputs=self._outputs,
                details=self._details,
                message=self._message,
                error=error,
            )
        )
        return False

    def set(
        self,
        *,
        counts: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        if counts:
            self._counts.update(counts)
        if outputs:
            self._outputs.update(outputs)
        if details:
            self._details.update(details)
        if message is not None:
            self._message = message


class OperationalRunRecorder:
    """Collect and append one local command execution summary."""

    def __init__(
        self,
        *,
        command: str,
        source: str,
        argv: Iterable[str],
        data_root: Path | None = None,
        log_path: Path | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self.run_id = str(uuid.uuid4())
        self.command = command
        self.source = source
        self.argv = _redact_argv(tuple(argv))
        self.data_root = data_root
        self.log_path = log_path or operation_runs_log_path()
        self.now = clock or (lambda: datetime.now(UTC))
        self.monotonic = monotonic or time.perf_counter
        self._started_at = self.now()
        self._started_monotonic = self.monotonic()
        self._completed_at: datetime | None = None
        self._duration_seconds: float | None = None
        self._status: str | None = None
        self._exit_code: int | None = None
        self._error: dict[str, str] | None = None
        self._phases: list[_PhaseRecord] = []

    def phase(self, name: str) -> OperationalPhase:
        return OperationalPhase(self, name)

    def skip_phase(self, name: str, reason: str) -> None:
        now = self.now()
        self.add_phase_record(
            _PhaseRecord(
                name=name,
                status="skipped",
                started_at=_isoformat(now),
                completed_at=_isoformat(now),
                duration_seconds=0.0,
                message=reason,
            )
        )

    def add_phase_record(self, phase: _PhaseRecord) -> None:
        self._phases.append(phase)

    def finish(
        self,
        *,
        status: str,
        exit_code: int | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._completed_at = self.now()
        self._duration_seconds = _duration(self.monotonic() - self._started_monotonic)
        self._status = status
        self._exit_code = exit_code
        self._error = _error_payload(error) if error is not None else None

    def as_dict(self) -> dict[str, Any]:
        completed_at = self._completed_at or self.now()
        duration_seconds = self._duration_seconds
        if duration_seconds is None:
            duration_seconds = _duration(self.monotonic() - self._started_monotonic)
        payload: dict[str, Any] = {
            "argv": list(self.argv),
            "command": self.command,
            "completed_at": _isoformat(completed_at),
            "duration_seconds": duration_seconds,
            "phases": [phase.as_dict() for phase in self._phases],
            "run_id": self.run_id,
            "schema_version": SCHEMA_VERSION,
            "source": self.source,
            "started_at": _isoformat(self._started_at),
            "status": self._status or "running",
        }
        if self.data_root is not None:
            payload["data_root"] = str(self.data_root)
        if self._exit_code is not None:
            payload["exit_code"] = self._exit_code
        if self._error:
            payload["error"] = self._error
        return payload

    def append(self) -> Path:
        payload = self.as_dict()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.chmod(0o700)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        fd = os.open(
            self.log_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        with os.fdopen(fd, "a", encoding="utf-8") as log_file:
            log_file.write(f"{encoded}\n")
        self.log_path.chmod(0o600)
        return self.log_path

    def append_best_effort(self) -> tuple[Path | None, str | None]:
        try:
            return self.append(), None
        except OSError as error:
            return None, str(error)


def _duration(seconds: float) -> float:
    return round(max(0.0, seconds), 6)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _error_payload(error: BaseException | None) -> dict[str, str] | None:
    if error is None:
        return None
    return {
        "type": error.__class__.__name__,
        "message": str(error),
    }


def _redact_argv(argv: tuple[str, ...]) -> tuple[str, ...]:
    redacted: list[str] = []
    redact_next = False
    for item in argv:
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
            continue
        option, has_inline_value, _value = item.partition("=")
        if option in SENSITIVE_OPTIONS:
            if has_inline_value:
                redacted.append(f"{option}=<redacted>")
            else:
                redacted.append(option)
                redact_next = True
            continue
        redacted.append(item)
    return tuple(redacted)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
