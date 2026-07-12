"""Garmin Connect biometric measurement synchronization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.garmin_connect.client import GarminConnectClient
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.storage.raw_store import RawWriteResult
from nono_sports.storage.state_store import STATE_VERSION

DEFAULT_HISTORY_START = date(2010, 1, 1)


@dataclass(frozen=True)
class GarminMeasurementSyncResult:
    start_date: str
    end_date: str
    written: tuple[RawWriteResult, ...]
    state_path: str


class GarminMeasurementStateStore:
    def __init__(
        self,
        data_root: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = garmin_connect_path(
            data_root,
            "logs",
            "measurement_sync_state.json",
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty_state()
        import json

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return self.empty_state()
        payload.setdefault("version", STATE_VERSION)
        payload.setdefault("runs", [])
        return payload

    def save(self, state: dict[str, Any]) -> None:
        import json

        self.path.parent.mkdir(parents=True, exist_ok=True)
        state["version"] = STATE_VERSION
        state["updated_at"] = self._clock().astimezone(UTC).isoformat()
        encoded = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(f"{encoded}\n", encoding="utf-8")
        temporary_path.replace(self.path)

    def empty_state(self) -> dict[str, Any]:
        return {
            "created_at": self._clock().astimezone(UTC).isoformat(),
            "runs": [],
            "version": STATE_VERSION,
        }


def sync_garmin_measurements_raw(
    client: GarminConnectClient,
    raw_store: GarminRawStore,
    state_store: GarminMeasurementStateStore,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    lookback_days: int = 30,
    full_scan: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> GarminMeasurementSyncResult:
    now = clock or (lambda: datetime.now(UTC))
    today = (end_date or now().astimezone(UTC).date())
    state = state_store.load()
    effective_start = _effective_start_date(
        state,
        start_date=start_date,
        end_date=today,
        lookback_days=lookback_days,
        full_scan=full_scan,
    )
    run = {
        "completed_at": None,
        "end_date": today.isoformat(),
        "full_scan": full_scan,
        "lookback_days": lookback_days,
        "start_date": effective_start.isoformat(),
        "started_at": now().astimezone(UTC).isoformat(),
    }
    state.setdefault("runs", []).append(run)
    state_store.save(state)

    written = [
        raw_store.write_json(
            f"biometrics/weigh_ins_{effective_start.isoformat()}_{today.isoformat()}.json",
            client.get_weigh_ins(effective_start.isoformat(), today.isoformat()),
            endpoint="get_weigh_ins",
            params={
                "end_date": today.isoformat(),
                "start_date": effective_start.isoformat(),
            },
        ),
        raw_store.write_json(
            "biometrics/body_composition_"
            f"{effective_start.isoformat()}_{today.isoformat()}.json",
            client.get_body_composition(effective_start.isoformat(), today.isoformat()),
            endpoint="get_body_composition",
            params={
                "end_date": today.isoformat(),
                "start_date": effective_start.isoformat(),
            },
        ),
    ]
    run["completed_at"] = now().astimezone(UTC).isoformat()
    run["written_files"] = len(written)
    state["last_successful_measurement_sync_at"] = run["completed_at"]
    state["last_successful_measurement_sync_start_date"] = effective_start.isoformat()
    state["last_successful_measurement_sync_end_date"] = today.isoformat()
    state_store.save(state)
    return GarminMeasurementSyncResult(
        start_date=effective_start.isoformat(),
        end_date=today.isoformat(),
        written=tuple(written),
        state_path=str(state_store.path),
    )


def _effective_start_date(
    state: dict[str, Any],
    *,
    start_date: date | None,
    end_date: date,
    lookback_days: int,
    full_scan: bool,
) -> date:
    if start_date is not None:
        return start_date
    if full_scan:
        return DEFAULT_HISTORY_START
    last_end = _parse_date(state.get("last_successful_measurement_sync_end_date"))
    if last_end is None:
        return DEFAULT_HISTORY_START
    return min(last_end, end_date) - timedelta(days=max(lookback_days, 0))


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
