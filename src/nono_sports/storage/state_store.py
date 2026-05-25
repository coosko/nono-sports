"""Synchronization state storage."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import strava_path

STATE_VERSION = 1
DEFAULT_ACTIVITY_SYNC_STATE = Path("logs") / "activity_sync_state.json"


class StateStore:
    def __init__(
        self,
        data_root: Path,
        *,
        relative_path: Path = DEFAULT_ACTIVITY_SYNC_STATE,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = strava_path(data_root, *relative_path.parts)
        self._clock = clock or (lambda: datetime.now(UTC))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty_state()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return self.empty_state()
        payload.setdefault("version", STATE_VERSION)
        payload.setdefault("activities", {})
        payload.setdefault("runs", [])
        return payload

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state["version"] = STATE_VERSION
        state["updated_at"] = self._clock().astimezone(UTC).isoformat()
        encoded = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(f"{encoded}\n", encoding="utf-8")
        temporary_path.replace(self.path)

    def empty_state(self) -> dict[str, Any]:
        return {
            "activities": {},
            "created_at": self._clock().astimezone(UTC).isoformat(),
            "runs": [],
            "version": STATE_VERSION,
        }
