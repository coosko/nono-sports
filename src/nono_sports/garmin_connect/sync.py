"""Read-only Garmin Connect sync primitives."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from nono_sports.formats.fit import (
    extract_fit_payloads,
    extract_zip_payloads_by_suffix,
)
from nono_sports.garmin_connect.client import (
    GarminActivityFileFormat,
    GarminConnectClient,
)
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.garmin_connect.state_store import GarminStateStore
from nono_sports.storage.raw_store import RawWriteResult


@dataclass(frozen=True)
class GarminActivitySnapshot:
    activity_id: str
    activity: dict[str, Any]
    details: dict[str, Any]
    splits: dict[str, Any] | None = None
    typed_splits: dict[str, Any] | None = None
    split_summaries: dict[str, Any] | None = None
    weather: dict[str, Any] | None = None
    activity_gear: dict[str, Any] | None = None
    fit: bytes | None = None


@dataclass(frozen=True)
class GarminRecoverableError:
    activity_id: str
    part: str
    message: str


@dataclass(frozen=True)
class GarminSyncWarning:
    activity_id: str
    part: str
    message: str


@dataclass(frozen=True)
class GarminRawSyncResult:
    listed_activities: int
    scanned_pages: int
    processed_activities: int
    skipped_activities: int
    written: tuple[RawWriteResult, ...]
    recoverable_errors: tuple[GarminRecoverableError, ...]
    warnings: tuple[GarminSyncWarning, ...]
    state_path: str
    stopped_reason: str | None = None


def sync_garmin_activities_raw(
    client: GarminConnectClient,
    raw_store: GarminRawStore,
    state_store: GarminStateStore,
    *,
    start: int = 0,
    before: int | None = None,
    after: int | None = None,
    limit: int = 20,
    max_activities: int | None = None,
    max_pages: int | None = None,
    force: bool = False,
    incremental: bool = True,
    incremental_lookback_days: int = 7,
    include_fit: bool = True,
    include_tcx: bool = False,
    include_gpx: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> GarminRawSyncResult:
    now = clock or (lambda: datetime.now(UTC))
    state = state_store.load()
    started_at = now().astimezone(UTC)
    effective_after = _effective_after(
        after=after,
        force=force,
        incremental=incremental,
        incremental_lookback_days=incremental_lookback_days,
        start=start,
        state=state,
    )
    written: list[RawWriteResult] = []
    recoverable_errors: list[GarminRecoverableError] = []
    warnings: list[GarminSyncWarning] = []
    run = {
        "after": after,
        "before": before,
        "completed_at": None,
        "effective_after": effective_after,
        "force": force,
        "include_fit": include_fit,
        "include_gpx": include_gpx,
        "include_tcx": include_tcx,
        "incremental": incremental,
        "incremental_lookback_days": incremental_lookback_days,
        "limit": limit,
        "listed_activities": None,
        "max_activities": max_activities,
        "max_pages": max_pages,
        "processed_activities": None,
        "scanned_pages": None,
        "skipped_activities": None,
        "started_at": started_at.isoformat(),
        "start": start,
        "stopped_reason": None,
    }
    state.setdefault("runs", []).append(run)
    state_store.save(state)

    listed = 0
    processed = 0
    skipped = 0
    scanned_pages = 0
    current_start = start
    while max_pages is None or scanned_pages < max_pages:
        if max_activities is not None and processed >= max_activities:
            break
        activities = client.list_activities(start=current_start, limit=limit)
        activities_list = activities if isinstance(activities, list) else []
        scanned_pages += 1
        listed += len(activities_list)
        listing_path = f"activities_index_{current_start}.json"
        written.append(
            raw_store.write_json(
                listing_path,
                activities,
                endpoint="get_activities",
                params={"limit": limit, "start": current_start},
            )
        )
        state["last_activity_listing_path"] = listing_path
        state["last_listed_activities"] = len(activities_list)
        state["last_listing_start"] = current_start
        state_store.save(state)
        if not activities_list:
            break

        for activity in activities_list:
            activity_timestamp = _activity_timestamp(activity)
            if before is not None and activity_timestamp is not None:
                if activity_timestamp >= before:
                    continue
            if effective_after is not None and activity_timestamp is not None:
                if activity_timestamp <= effective_after:
                    run["stopped_reason"] = "incremental_after_reached"
                    break
            activity_id = _activity_id(activity)
            if activity_id is None:
                continue
            activity_key = str(activity_id)
            state_entry = state.setdefault("activities", {}).setdefault(
                activity_key,
                {},
            )
            if _activity_complete(state_entry) and not force:
                skipped += 1
                state_entry["skipped_at"] = now().astimezone(UTC).isoformat()
                state_store.save(state)
                continue
            if max_activities is not None and processed >= max_activities:
                break
            processed += 1
            _download_activity_parts(
                client,
                raw_store,
                state_entry,
                written,
                recoverable_errors,
                warnings,
                activity=activity,
                activity_key=activity_key,
                include_fit=include_fit,
                include_tcx=include_tcx,
                include_gpx=include_gpx,
                now=now,
            )
            state_store.save(state)
        if run["stopped_reason"] == "incremental_after_reached":
            break
        current_start += limit

    run["completed_at"] = now().astimezone(UTC).isoformat()
    run["listed_activities"] = listed
    run["processed_activities"] = processed
    run["scanned_pages"] = scanned_pages
    run["skipped_activities"] = skipped
    run["recoverable_errors"] = len(recoverable_errors)
    run["warnings"] = len(warnings)
    run["written_files"] = len(written)
    if not force:
        state["last_successful_activity_sync_at"] = started_at.isoformat()
        state["last_successful_activity_sync_after"] = effective_after
    state_store.save(state)

    return GarminRawSyncResult(
        listed_activities=listed,
        scanned_pages=scanned_pages,
        processed_activities=processed,
        skipped_activities=skipped,
        written=tuple(written),
        recoverable_errors=tuple(recoverable_errors),
        warnings=tuple(warnings),
        state_path=str(state_store.path),
        stopped_reason=run["stopped_reason"],
    )


def _download_activity_parts(
    client: GarminConnectClient,
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[GarminRecoverableError],
    warnings: list[GarminSyncWarning],
    *,
    activity: dict[str, Any],
    activity_key: str,
    include_fit: bool,
    include_tcx: bool,
    include_gpx: bool,
    now: Callable[[], datetime],
) -> None:
    state_entry["summary_seen_at"] = now().astimezone(UTC).isoformat()
    state_entry["summary"] = _summarize_activity(activity)
    safe_activity_id = _safe_identifier(activity_key)

    _write_required_json_part(
        client.get_activity(activity_key),
        raw_store,
        state_entry,
        written,
        part="activity",
        endpoint="get_activity",
        raw_path=f"activities/{safe_activity_id}.json",
        activity_id=activity_key,
    )
    _write_required_json_part(
        client.get_activity_details(activity_key),
        raw_store,
        state_entry,
        written,
        part="details",
        endpoint="get_activity_details",
        raw_path=f"activities/{safe_activity_id}.details.json",
        activity_id=activity_key,
    )
    _download_optional_json_part(
        lambda: client.get_activity_splits(activity_key),
        raw_store,
        state_entry,
        written,
        recoverable_errors,
        part="splits",
        endpoint="get_activity_splits",
        raw_path=f"splits/{safe_activity_id}.json",
        activity_id=activity_key,
    )
    _download_optional_json_part(
        lambda: client.get_activity_typed_splits(activity_key),
        raw_store,
        state_entry,
        written,
        recoverable_errors,
        part="typed_splits",
        endpoint="get_activity_typed_splits",
        raw_path=f"typed_splits/{safe_activity_id}.json",
        activity_id=activity_key,
    )
    _download_optional_json_part(
        lambda: client.get_activity_split_summaries(activity_key),
        raw_store,
        state_entry,
        written,
        recoverable_errors,
        part="split_summaries",
        endpoint="get_activity_split_summaries",
        raw_path=f"splits/{safe_activity_id}.summaries.json",
        activity_id=activity_key,
    )
    _download_optional_json_part(
        lambda: client.get_activity_weather(activity_key),
        raw_store,
        state_entry,
        written,
        recoverable_errors,
        part="weather",
        endpoint="get_activity_weather",
        raw_path=f"weather/{safe_activity_id}.json",
        activity_id=activity_key,
    )
    _download_optional_json_part(
        lambda: client.get_activity_gear(activity_key),
        raw_store,
        state_entry,
        written,
        recoverable_errors,
        part="activity_gear",
        endpoint="get_activity_gear",
        raw_path=f"gear/activity_{safe_activity_id}.json",
        activity_id=activity_key,
    )
    if include_fit:
        has_fit = _download_original_activity_file_part(
            lambda: client.download_activity_file(
                activity_key,
                GarminActivityFileFormat.FIT,
            ),
            raw_store,
            state_entry,
            written,
            recoverable_errors,
            raw_archive_path=f"activity_files/{safe_activity_id}.original.zip",
            raw_fit_path=f"activity_files/{safe_activity_id}.fit",
            activity_id=activity_key,
            warnings=warnings,
        )
        if not has_fit:
            _download_missing_fallback_activity_files(
                client,
                raw_store,
                state_entry,
                written,
                warnings,
                activity_key=activity_key,
                safe_activity_id=safe_activity_id,
            )
    if include_tcx:
        _download_optional_file_part(
            lambda: client.download_activity_file(
                activity_key,
                GarminActivityFileFormat.TCX,
            ),
            raw_store,
            state_entry,
            written,
            recoverable_errors,
            part="tcx",
            endpoint="download_activity:tcx",
            raw_path=f"activity_files/{safe_activity_id}.tcx",
            activity_id=activity_key,
        )
    if include_gpx:
        _download_optional_file_part(
            lambda: client.download_activity_file(
                activity_key,
                GarminActivityFileFormat.GPX,
            ),
            raw_store,
            state_entry,
            written,
            recoverable_errors,
            part="gpx",
            endpoint="download_activity:gpx",
            raw_path=f"activity_files/{safe_activity_id}.gpx",
            activity_id=activity_key,
        )
    state_entry["completed_at"] = now().astimezone(UTC).isoformat()


def collect_activity_snapshot(
    client: GarminConnectClient,
    activity_id: str | int,
    include_fit: bool = True,
) -> GarminActivitySnapshot:
    source_id = str(activity_id)
    return GarminActivitySnapshot(
        activity_id=source_id,
        activity=client.get_activity(source_id),
        details=client.get_activity_details(source_id),
        splits=_optional_read(client.get_activity_splits, source_id),
        typed_splits=_optional_read(client.get_activity_typed_splits, source_id),
        split_summaries=_optional_read(
            client.get_activity_split_summaries,
            source_id,
        ),
        weather=_optional_read(client.get_activity_weather, source_id),
        activity_gear=_optional_read(client.get_activity_gear, source_id),
        fit=(
            client.download_activity_file(source_id, GarminActivityFileFormat.FIT)
            if include_fit
            else None
        ),
    )


def _optional_read(method: Any, activity_id: str) -> dict[str, Any] | None:
    try:
        return method(activity_id)
    except Exception:  # noqa: BLE001
        return None


def _write_required_json_part(
    payload: dict[str, Any],
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    *,
    part: str,
    endpoint: str,
    raw_path: str,
    activity_id: str,
) -> None:
    result = raw_store.write_json(
        raw_path,
        payload,
        endpoint=endpoint,
        params={"activity_id": activity_id},
    )
    written.append(result)
    state_entry[part] = result.relative_path


def _download_optional_json_part(
    fetch: Callable[[], dict[str, Any]],
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[GarminRecoverableError],
    *,
    part: str,
    endpoint: str,
    raw_path: str,
    activity_id: str,
) -> None:
    try:
        payload = fetch()
    except Exception as error:  # noqa: BLE001
        _record_recoverable_error(recoverable_errors, activity_id, part, error)
        state_entry[f"{part}_error"] = str(error)
        return
    result = raw_store.write_json(
        raw_path,
        payload,
        endpoint=endpoint,
        params={"activity_id": activity_id},
    )
    written.append(result)
    state_entry[part] = result.relative_path


def _download_optional_file_part(
    fetch: Callable[[], bytes],
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[GarminRecoverableError],
    *,
    part: str,
    endpoint: str,
    raw_path: str,
    activity_id: str,
) -> None:
    try:
        payload = fetch()
    except Exception as error:  # noqa: BLE001
        _record_recoverable_error(recoverable_errors, activity_id, part, error)
        state_entry[f"{part}_error"] = str(error)
        return
    result = raw_store.write_bytes(
        raw_path,
        payload,
        endpoint=endpoint,
        params={"activity_id": activity_id},
        kind="file",
    )
    written.append(result)
    state_entry[part] = result.relative_path


def _download_original_activity_file_part(
    fetch: Callable[[], bytes],
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    recoverable_errors: list[GarminRecoverableError],
    *,
    raw_archive_path: str,
    raw_fit_path: str,
    activity_id: str,
    warnings: list[GarminSyncWarning],
) -> bool:
    try:
        payload = fetch()
    except Exception as error:  # noqa: BLE001
        _record_recoverable_error(recoverable_errors, activity_id, "fit", error)
        state_entry["fit_error"] = str(error)
        return False

    archive_result = raw_store.write_bytes(
        raw_archive_path,
        payload,
        endpoint="download_activity:original",
        params={"activity_id": activity_id},
        kind="file",
    )
    written.append(archive_result)
    state_entry["fit_archive"] = archive_result.relative_path

    try:
        fit_payloads = extract_fit_payloads(payload, default_name=raw_fit_path)
    except ValueError as error:
        _record_warning(warnings, activity_id, "fit", error)
        state_entry.pop("fit_error", None)
        state_entry["fit_warning"] = str(error)
        state_entry["fit_unavailable"] = True
        _write_fallback_files_from_original_archive(
            payload,
            raw_store,
            state_entry,
            written,
            activity_id=activity_id,
            raw_gpx_path=raw_fit_path.replace(".fit", ".gpx"),
            raw_tcx_path=raw_fit_path.replace(".fit", ".tcx"),
        )
        return False

    fit_payload = fit_payloads[0]
    fit_result = raw_store.write_bytes(
        raw_fit_path,
        fit_payload.payload,
        endpoint="download_activity:fit_extracted",
        params={"activity_id": activity_id, "source_name": fit_payload.name},
        kind="file",
    )
    written.append(fit_result)
    state_entry["fit"] = fit_result.relative_path
    state_entry.pop("fit_error", None)
    state_entry.pop("fit_warning", None)
    state_entry.pop("fit_unavailable", None)
    return True


def _write_fallback_files_from_original_archive(
    payload: bytes,
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    *,
    activity_id: str,
    raw_gpx_path: str,
    raw_tcx_path: str,
) -> None:
    for part, suffix, raw_path in (
        ("gpx", ".gpx", raw_gpx_path),
        ("tcx", ".tcx", raw_tcx_path),
    ):
        if state_entry.get(part):
            continue
        extracted = extract_zip_payloads_by_suffix(payload, (suffix,))
        if not extracted:
            continue
        fallback = extracted[0]
        result = raw_store.write_bytes(
            raw_path,
            fallback.payload,
            endpoint=f"download_activity:original_{part}_extracted",
            params={"activity_id": activity_id, "source_name": fallback.name},
            kind="file",
        )
        written.append(result)
        state_entry[part] = result.relative_path


def _download_missing_fallback_activity_files(
    client: GarminConnectClient,
    raw_store: GarminRawStore,
    state_entry: dict[str, Any],
    written: list[RawWriteResult],
    warnings: list[GarminSyncWarning],
    *,
    activity_key: str,
    safe_activity_id: str,
) -> None:
    for part, file_format in (
        ("gpx", GarminActivityFileFormat.GPX),
        ("tcx", GarminActivityFileFormat.TCX),
    ):
        if state_entry.get(part):
            continue
        try:
            payload = client.download_activity_file(activity_key, file_format)
        except Exception as error:  # noqa: BLE001
            _record_warning(warnings, activity_key, part, error)
            state_entry[f"{part}_warning"] = str(error)
            continue
        result = raw_store.write_bytes(
            f"activity_files/{safe_activity_id}.{part}",
            payload,
            endpoint=f"download_activity:{part}",
            params={"activity_id": activity_key},
            kind="file",
        )
        written.append(result)
        state_entry[part] = result.relative_path


def _record_recoverable_error(
    recoverable_errors: list[GarminRecoverableError],
    activity_id: str,
    part: str,
    error: Exception,
) -> None:
    recoverable_errors.append(
        GarminRecoverableError(
            activity_id=activity_id,
            part=part,
            message=str(error),
        )
    )


def _record_warning(
    warnings: list[GarminSyncWarning],
    activity_id: str,
    part: str,
    error: Exception,
) -> None:
    warnings.append(
        GarminSyncWarning(
            activity_id=activity_id,
            part=part,
            message=str(error),
        )
    )


def _activity_complete(state_entry: dict[str, Any]) -> bool:
    if not state_entry.get("activity") or not state_entry.get("details"):
        return False
    if not state_entry.get("activity_gear") and not state_entry.get(
        "activity_gear_error"
    ):
        return False
    if state_entry.get("fit"):
        return True
    return bool(state_entry.get("fit_unavailable") and _has_fallback_track(state_entry))


def _has_fallback_track(state_entry: dict[str, Any]) -> bool:
    return bool(state_entry.get("gpx") or state_entry.get("tcx"))


def _activity_id(activity: dict[str, Any]) -> str | None:
    value = activity.get("activityId")
    return str(value) if value is not None else None


def _effective_after(
    *,
    after: int | None,
    force: bool,
    incremental: bool,
    incremental_lookback_days: int,
    start: int,
    state: dict[str, Any],
) -> int | None:
    if after is not None:
        return after
    if force or not incremental or start != 0:
        return None
    last_sync_at = _parse_datetime(state.get("last_successful_activity_sync_at"))
    if last_sync_at is None:
        return None
    lookback = max(incremental_lookback_days, 0)
    return int((last_sync_at - timedelta(days=lookback)).timestamp())


def _activity_timestamp(activity: dict[str, Any]) -> int | None:
    for key in (
        "beginTimestamp",
        "startTimeGMT",
        "startTimeLocal",
        "startTime",
    ):
        parsed = _parse_datetime(activity.get(key))
        if parsed is not None:
            return int(parsed.timestamp())
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _summarize_activity(activity: dict[str, Any]) -> dict[str, Any]:
    return {
        key: activity.get(key)
        for key in (
            "activityId",
            "activityName",
            "activityType",
            "beginTimestamp",
            "distance",
            "duration",
            "startTimeLocal",
        )
        if key in activity
    }


def _safe_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)
