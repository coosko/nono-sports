"""Strava raw synchronization workflows."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from nono_sports.storage.raw_store import RawStore, RawWriteResult
from nono_sports.storage.state_store import StateStore
from nono_sports.strava.client import StravaApiError, StravaRateLimitBudgetExceeded
from nono_sports.strava.endpoints import (
    DEFAULT_ACTIVITY_PAGE_SIZE,
    StravaContextDownloadError,
    StravaEndpoints,
)

RECOVERABLE_ACTIVITY_STATUS_CODES = {402, 403, 404}


@dataclass(frozen=True)
class RecoverableActivityError:
    activity_id: str
    part: str
    endpoint: str
    status_code: int
    message: str
    saved_path: str


@dataclass(frozen=True)
class ActivitySyncResult:
    listed_activities: int
    processed_activities: int
    skipped_activities: int
    written: tuple[RawWriteResult, ...]
    recoverable_errors: tuple[RecoverableActivityError, ...]
    state_path: str
    stopped_reason: str | None = None


def sync_activities_raw(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    state_store: StateStore,
    *,
    before: int | None = None,
    after: int | None = None,
    per_page: int = DEFAULT_ACTIVITY_PAGE_SIZE,
    max_activities: int | None = None,
    force: bool = False,
    include_streams: bool = True,
    include_laps: bool = True,
    include_gear: bool = True,
    include_segments: bool = True,
    include_segment_streams: bool = True,
    include_zones: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> ActivitySyncResult:
    now = clock or (lambda: datetime.now(UTC))
    state = state_store.load()
    written: list[RawWriteResult] = []
    recoverable_errors: list[RecoverableActivityError] = []

    list_params = _without_none(
        {
            "after": after,
            "before": before,
            "max_activities": max_activities,
            "per_page": per_page,
        }
    )
    run = {
        "after": after,
        "before": before,
        "completed_at": None,
        "force": force,
        "include_gear": include_gear,
        "include_laps": include_laps,
        "include_segment_streams": include_segment_streams,
        "include_segments": include_segments,
        "include_streams": include_streams,
        "include_zones": include_zones,
        "listed_activities": None,
        "max_activities": max_activities,
        "started_at": now().astimezone(UTC).isoformat(),
    }
    state.setdefault("runs", []).append(run)
    state_store.save(state)

    try:
        activities = endpoints.list_athlete_activities(
            before=before,
            after=after,
            per_page=per_page,
        )
    except (StravaApiError, StravaRateLimitBudgetExceeded) as error:
        if not _is_rate_limit_stop(error):
            raise
        return _stop_for_rate_limit(
            error,
            activity_key=None,
            activities=[],
            processed=0,
            recoverable_errors=recoverable_errors,
            run=run,
            skipped=0,
            state=state,
            state_store=state_store,
            written=written,
            now=now,
        )

    written.append(
        raw_store.write_json(
            "activities/activities.json",
            activities,
            endpoint="/athlete/activities",
            params=list_params,
        )
    )
    run["listed_activities"] = len(activities)
    state["last_activity_listing_path"] = "activities/activities.json"
    state["last_listed_activities"] = len(activities)
    state["last_activity_batch_limit"] = max_activities
    state_store.save(state)

    processed = 0
    skipped = 0
    for activity in activities:
        activity_id = _activity_id(activity)
        activity_key = str(activity_id)
        existing_state = state.setdefault("activities", {}).get(activity_key)

        if (
            isinstance(existing_state, dict)
            and not force
            and _activity_complete(
                existing_state,
                raw_store,
                include_gear=include_gear,
                include_laps=include_laps,
                include_segments=include_segments,
                include_streams=include_streams,
                include_zones=include_zones,
            )
        ):
            skipped += 1
            existing_state["skipped_at"] = now().astimezone(UTC).isoformat()
            state_store.save(state)
            continue

        if max_activities is not None and processed >= max_activities:
            break

        state_entry = _activity_state(state, activity_key)
        state_entry["summary_seen_at"] = now().astimezone(UTC).isoformat()
        state_entry["summary"] = _summarize_activity(activity)

        if not force and _activity_complete(
            state_entry,
            raw_store,
            include_gear=include_gear,
            include_laps=include_laps,
            include_segments=include_segments,
            include_streams=include_streams,
            include_zones=include_zones,
        ):
            skipped += 1
            state_entry["skipped_at"] = now().astimezone(UTC).isoformat()
            state_store.save(state)
            continue

        processed += 1
        safe_activity_id = _safe_identifier(activity_key)
        try:
            detail_payload = _download_activity_part(
                part="detail",
                endpoint=f"/activities/{activity_key}",
                fetch=lambda activity_id=activity_id: endpoints.get_activity(
                    activity_id
                ),
                raw_store=raw_store,
                raw_path=f"activities/{safe_activity_id}.json",
                error_path=f"errors/activity_{safe_activity_id}_detail.json",
                state_entry=state_entry,
                written=written,
                recoverable_errors=recoverable_errors,
                activity_id=activity_key,
            )
            if include_laps:
                _download_activity_part(
                    part="laps",
                    endpoint=f"/activities/{activity_key}/laps",
                    fetch=lambda activity_id=activity_id: endpoints.get_activity_laps(
                        activity_id
                    ),
                    raw_store=raw_store,
                    raw_path=f"laps/{safe_activity_id}.json",
                    error_path=f"errors/activity_{safe_activity_id}_laps.json",
                    state_entry=state_entry,
                    written=written,
                    recoverable_errors=recoverable_errors,
                    activity_id=activity_key,
                )
            if include_streams:
                _download_activity_part(
                    part="streams",
                    endpoint=f"/activities/{activity_key}/streams",
                    fetch=lambda activity_id=activity_id: (
                        endpoints.get_activity_streams(activity_id)
                    ),
                    raw_store=raw_store,
                    raw_path=f"streams/{safe_activity_id}.json",
                    error_path=f"errors/activity_{safe_activity_id}_streams.json",
                    state_entry=state_entry,
                    written=written,
                    recoverable_errors=recoverable_errors,
                    activity_id=activity_key,
                )
            if include_gear:
                gear_payload = (
                    detail_payload if isinstance(detail_payload, dict) else activity
                )
                _download_activity_gear(
                    endpoints,
                    raw_store,
                    activity_id=activity_key,
                    activity_payload=gear_payload,
                    force=force,
                    state_entry=state_entry,
                    written=written,
                    recoverable_errors=recoverable_errors,
                )
            if include_segments:
                segment_payload = (
                    detail_payload if isinstance(detail_payload, dict) else {}
                )
                _download_activity_segments(
                    endpoints,
                    raw_store,
                    activity_id=activity_key,
                    activity_payload=segment_payload,
                    force=force,
                    include_segment_streams=include_segment_streams,
                    state_entry=state_entry,
                    written=written,
                    recoverable_errors=recoverable_errors,
                )
            if include_zones:
                _download_activity_part(
                    part="zones",
                    endpoint=f"/activities/{activity_key}/zones",
                    fetch=lambda activity_id=activity_id: (
                        endpoints.get_activity_zones(activity_id)
                    ),
                    raw_store=raw_store,
                    raw_path=f"zones/{safe_activity_id}.json",
                    error_path=f"errors/activity_{safe_activity_id}_zones.json",
                    state_entry=state_entry,
                    written=written,
                    recoverable_errors=recoverable_errors,
                    activity_id=activity_key,
                )
        except (StravaApiError, StravaRateLimitBudgetExceeded) as error:
            if not _is_rate_limit_stop(error):
                raise
            return _stop_for_rate_limit(
                error,
                activity_key=activity_key,
                activities=activities,
                processed=processed,
                recoverable_errors=recoverable_errors,
                run=run,
                skipped=skipped,
                state=state,
                state_store=state_store,
                written=written,
                now=now,
            )

        state_entry["completed_at"] = now().astimezone(UTC).isoformat()
        state_store.save(state)

    run["completed_at"] = now().astimezone(UTC).isoformat()
    run["processed_activities"] = processed
    run["skipped_activities"] = skipped
    run["recoverable_errors"] = len(recoverable_errors)
    run["written_files"] = len(written)
    state_store.save(state)

    return ActivitySyncResult(
        listed_activities=len(activities),
        processed_activities=processed,
        skipped_activities=skipped,
        written=tuple(written),
        recoverable_errors=tuple(recoverable_errors),
        state_path=str(state_store.path),
        stopped_reason=None,
    )


def _stop_for_rate_limit(
    error: StravaApiError | StravaRateLimitBudgetExceeded,
    *,
    activity_key: str | None,
    activities: list[dict[str, Any]],
    processed: int,
    recoverable_errors: list[RecoverableActivityError],
    run: dict[str, Any],
    skipped: int,
    state: dict[str, Any],
    state_store: StateStore,
    written: list[RawWriteResult],
    now: Callable[[], datetime],
) -> ActivitySyncResult:
    reason = _rate_limit_reason(error)
    run["completed_at"] = now().astimezone(UTC).isoformat()
    run["processed_activities"] = processed
    run["recoverable_errors"] = len(recoverable_errors)
    run["skipped_activities"] = skipped
    if activity_key is not None:
        run["stopped_at_activity_id"] = activity_key
    run["stopped_reason"] = reason
    run["written_files"] = len(written)
    state_store.save(state)
    return ActivitySyncResult(
        listed_activities=len(activities),
        processed_activities=processed,
        skipped_activities=skipped,
        written=tuple(written),
        recoverable_errors=tuple(recoverable_errors),
        state_path=str(state_store.path),
        stopped_reason=reason,
    )


def _is_rate_limit_stop(
    error: StravaApiError | StravaRateLimitBudgetExceeded,
) -> bool:
    if isinstance(error, StravaRateLimitBudgetExceeded):
        return True
    return error.status_code == 429


def _rate_limit_reason(
    error: StravaApiError | StravaRateLimitBudgetExceeded,
) -> str:
    if isinstance(error, StravaRateLimitBudgetExceeded):
        return f"rate_limit_budget:{error.message}"
    return f"rate_limit:{error.message}"


def _download_activity_part(
    *,
    part: str,
    endpoint: str,
    fetch,
    raw_store: RawStore,
    raw_path: str,
    error_path: str,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[RecoverableActivityError],
    activity_id: str,
) -> Any | None:
    try:
        payload = fetch()
    except StravaApiError as error:
        if error.status_code not in RECOVERABLE_ACTIVITY_STATUS_CODES:
            raise
        saved = raw_store.write_json(
            error_path,
            {
                "activity_id": activity_id,
                "endpoint": endpoint,
                "errors": [detail.label() for detail in error.errors],
                "message": error.message,
                "part": part,
                "status_code": error.status_code,
            },
            endpoint=endpoint,
            kind="error",
        )
        state_entry[f"{part}_error"] = saved.relative_path
        recoverable_errors.append(
            RecoverableActivityError(
                activity_id=activity_id,
                part=part,
                endpoint=endpoint,
                status_code=error.status_code,
                message=error.message,
                saved_path=saved.relative_path,
            )
        )
        return None

    saved = raw_store.write_json(raw_path, payload, endpoint=endpoint)
    state_entry[part] = saved.relative_path
    state_entry.pop(f"{part}_error", None)
    written.append(saved)
    return payload


def _download_activity_gear(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    *,
    activity_id: str,
    activity_payload: dict[str, Any],
    force: bool,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[RecoverableActivityError],
) -> None:
    gear_id = activity_payload.get("gear_id")
    if gear_id is None:
        state_entry["gear_checked"] = True
        return
    safe_gear_id = _safe_identifier(gear_id)
    raw_path = f"gear/{safe_gear_id}.json"
    if not force and (raw_store.raw_root / raw_path).exists():
        state_entry["gear"] = raw_path
        state_entry["gear_checked"] = True
        return

    payload = _download_activity_part(
        part="gear",
        endpoint=f"/gear/{gear_id}",
        fetch=lambda gear_id=gear_id: endpoints.get_gear(str(gear_id)),
        raw_store=raw_store,
        raw_path=raw_path,
        error_path=f"errors/activity_{activity_id}_gear_{safe_gear_id}.json",
        state_entry=state_entry,
        written=written,
        recoverable_errors=recoverable_errors,
        activity_id=activity_id,
    )
    state_entry["gear_checked"] = payload is not None


def _download_activity_segments(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    *,
    activity_id: str,
    activity_payload: dict[str, Any],
    force: bool,
    include_segment_streams: bool,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[RecoverableActivityError],
) -> None:
    segment_ids = sorted(_extract_segment_ids(activity_payload))
    state_entry["segments"] = segment_ids
    if not segment_ids:
        state_entry["segments_checked"] = True
        return

    for segment_id in segment_ids:
        safe_segment_id = _safe_identifier(segment_id)
        segment_path = f"segments/{safe_segment_id}.json"
        if force or not (raw_store.raw_root / segment_path).exists():
            _download_activity_part(
                part=f"segment_{safe_segment_id}",
                endpoint=f"/segments/{segment_id}",
                fetch=lambda segment_id=segment_id: endpoints.get_segment(segment_id),
                raw_store=raw_store,
                raw_path=segment_path,
                error_path=f"errors/activity_{activity_id}_segment_{safe_segment_id}.json",
                state_entry=state_entry,
                written=written,
                recoverable_errors=recoverable_errors,
                activity_id=activity_id,
            )
        if include_segment_streams:
            stream_path = f"segment_streams/{safe_segment_id}.json"
            if not force and (raw_store.raw_root / stream_path).exists():
                continue
            _download_activity_part(
                part=f"segment_{safe_segment_id}_streams",
                endpoint=f"/segments/{segment_id}/streams",
                fetch=lambda segment_id=segment_id: endpoints.get_segment_streams(
                    segment_id
                ),
                raw_store=raw_store,
                raw_path=stream_path,
                error_path=(
                    f"errors/activity_{activity_id}_segment_{safe_segment_id}"
                    "_streams.json"
                ),
                state_entry=state_entry,
                written=written,
                recoverable_errors=recoverable_errors,
                activity_id=activity_id,
            )
    state_entry["segments_checked"] = True


def _activity_complete(
    state_entry: dict[str, Any],
    raw_store: RawStore,
    *,
    include_gear: bool,
    include_laps: bool,
    include_segments: bool,
    include_streams: bool,
    include_zones: bool,
) -> bool:
    required_parts = ["detail"]
    if include_laps:
        required_parts.append("laps")
    if include_streams:
        required_parts.append("streams")
    if include_zones:
        required_parts.append("zones")
    for part in required_parts:
        value = state_entry.get(part) or state_entry.get(f"{part}_error")
        if not isinstance(value, str):
            return False
        if not (raw_store.raw_root / value).exists():
            return False
    if include_gear and state_entry.get("gear_checked") is not True:
        return False
    if include_segments and state_entry.get("segments_checked") is not True:
        return False
    return True


def _activity_state(state: dict[str, Any], activity_id: str) -> dict[str, Any]:
    activities = state.setdefault("activities", {})
    activity_state = activities.setdefault(activity_id, {"id": activity_id})
    if not isinstance(activity_state, dict):
        activity_state = {"id": activity_id}
        activities[activity_id] = activity_state
    return activity_state


def _activity_id(activity: dict[str, Any]) -> int | str:
    value = activity.get("id")
    if value is None:
        raise StravaContextDownloadError("Missing 'id' in listed activity.")
    if not isinstance(value, int | str):
        raise StravaContextDownloadError("Invalid 'id' in listed activity.")
    return value


def _summarize_activity(activity: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ("id", "name", "start_date", "start_date_local", "type", "sport_type"):
        if key in activity:
            summary[key] = activity[key]
    return summary


def _extract_segment_ids(payload: dict[str, Any]) -> set[str]:
    segment_ids: set[str] = set()
    segment_efforts = payload.get("segment_efforts")
    if not isinstance(segment_efforts, list):
        return segment_ids
    for effort in segment_efforts:
        if not isinstance(effort, dict):
            continue
        segment = effort.get("segment")
        if isinstance(segment, dict) and segment.get("id") is not None:
            segment_ids.add(str(segment["id"]))
        elif effort.get("segment_id") is not None:
            segment_ids.add(str(effort["segment_id"]))
    return segment_ids


def _safe_identifier(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    if not normalized:
        raise StravaContextDownloadError("Cannot build a safe filename identifier.")
    return normalized


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
