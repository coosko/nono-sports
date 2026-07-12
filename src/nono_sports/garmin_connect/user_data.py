"""Garmin Connect user profile, gear and device synchronization."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nono_sports.core.paths import garmin_connect_path
from nono_sports.garmin_connect.client import GarminConnectClient
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.storage.raw_store import RawWriteResult
from nono_sports.storage.state_store import STATE_VERSION


@dataclass(frozen=True)
class GarminUserDataSyncResult:
    written: tuple[RawWriteResult, ...]
    state_path: str


class GarminUserDataStateStore:
    def __init__(
        self,
        data_root: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = garmin_connect_path(data_root, "logs", "user_sync_state.json")
        self._clock = clock or (lambda: datetime.now(UTC))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty_state()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return self.empty_state()
        payload.setdefault("version", STATE_VERSION)
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
            "created_at": self._clock().astimezone(UTC).isoformat(),
            "runs": [],
            "version": STATE_VERSION,
        }


def sync_garmin_user_data_raw(
    client: GarminConnectClient,
    raw_store: GarminRawStore,
    state_store: GarminUserDataStateStore,
    *,
    clock: Callable[[], datetime] | None = None,
) -> GarminUserDataSyncResult:
    now = clock or (lambda: datetime.now(UTC))
    state = state_store.load()
    run = {
        "completed_at": None,
        "started_at": now().astimezone(UTC).isoformat(),
    }
    state.setdefault("runs", []).append(run)
    state_store.save(state)

    written: list[RawWriteResult] = []
    profile = client.get_user_profile()
    settings = client.get_userprofile_settings()
    written.append(
        raw_store.write_json(
            "athlete/profile.json",
            profile,
            endpoint="get_user_profile",
        )
    )
    written.append(
        raw_store.write_json(
            "athlete/settings.json",
            settings,
            endpoint="get_userprofile_settings",
        )
    )
    user_profile_number = _user_profile_number(profile, settings)
    if user_profile_number is not None:
        gear = _optional_call(client.get_gear, user_profile_number)
        if gear is not None:
            written.append(
                raw_store.write_json(
                    "gear/gear.json",
                    gear,
                    endpoint="get_gear",
                    params={"user_profile_number": user_profile_number},
                )
            )
        defaults = _optional_call(client.get_gear_defaults, user_profile_number)
        if defaults is not None:
            written.append(
                raw_store.write_json(
                    "gear/defaults.json",
                    defaults,
                    endpoint="get_gear_defaults",
                    params={"user_profile_number": user_profile_number},
                )
            )
        for gear_id in _gear_ids(gear):
            stats = _optional_call(client.get_gear_stats, gear_id)
            if stats is None:
                continue
            written.append(
                raw_store.write_json(
                    f"gear/stats/{_safe_id(gear_id)}.json",
                    stats,
                    endpoint="get_gear_stats",
                    params={"gear_uuid": gear_id},
                )
            )
    for relative_path, endpoint, fetch in (
        (
            "devices/devices.json",
            "get_devices",
            client.get_devices,
        ),
        (
            "devices/last_used.json",
            "get_device_last_used",
            client.get_device_last_used,
        ),
        (
            "devices/primary_training_device.json",
            "get_primary_training_device",
            client.get_primary_training_device,
        ),
    ):
        payload = _optional_call(fetch)
        if payload is None:
            continue
        written.append(
            raw_store.write_json(
                relative_path,
                payload,
                endpoint=endpoint,
            )
        )
    run["completed_at"] = now().astimezone(UTC).isoformat()
    run["written_files"] = len(written)
    state["last_successful_user_sync_at"] = run["completed_at"]
    state_store.save(state)
    return GarminUserDataSyncResult(
        written=tuple(written),
        state_path=str(state_store.path),
    )


def _user_profile_number(*payloads: dict[str, Any]) -> str | None:
    for payload in payloads:
        for key in ("userProfileId", "userProfilePk", "profileId", "id"):
            value = payload.get(key)
            if value is not None:
                return str(value)
    return None


def _gear_ids(payload: Any) -> list[str]:
    ids: set[str] = set()
    for item in _dicts(payload):
        for key in ("gearUuid", "uuid", "gearPk", "id"):
            value = item.get(key)
            if value is not None:
                ids.add(str(value))
                break
    return sorted(ids)


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        found = [value]
        for item in value.values():
            found.extend(_dicts(item))
        return found
    if isinstance(value, list):
        found: list[dict[str, Any]] = []
        for item in value:
            found.extend(_dicts(item))
        return found
    return []


def _optional_call(method: Callable[..., Any], *args: Any) -> Any | None:
    try:
        return method(*args)
    except Exception:  # noqa: BLE001
        return None


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in value)
