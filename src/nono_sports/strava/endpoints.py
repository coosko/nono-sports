"""High-level Strava endpoint access."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from nono_sports.core.errors import NonoSportsError
from nono_sports.storage.raw_store import RawStore, RawWriteResult
from nono_sports.strava.client import StravaApiError

DEFAULT_CONTEXT_PAGE_SIZE = 200
DEFAULT_ACTIVITY_PAGE_SIZE = 200
DEFAULT_ACTIVITY_STREAM_KEYS = (
    "time",
    "distance",
    "latlng",
    "altitude",
    "velocity_smooth",
    "heartrate",
    "cadence",
    "watts",
    "temp",
    "moving",
    "grade_smooth",
)
DEFAULT_SEGMENT_STREAM_KEYS = ("distance", "latlng", "altitude")
RECOVERABLE_CONTEXT_STATUS_CODES = {403, 404}


class StravaReadableClient(Protocol):
    def get(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> Any:
        raise NotImplementedError

    def get_bytes(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> bytes:
        raise NotImplementedError

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        per_page: int = DEFAULT_CONTEXT_PAGE_SIZE,
        start_page: int = 1,
    ) -> Iterator[dict[str, Any]]:
        raise NotImplementedError


class StravaContextDownloadError(NonoSportsError):
    """Raised when the Strava profile/context download cannot continue."""


@dataclass(frozen=True)
class RecoverableContextError:
    name: str
    endpoint: str
    status_code: int
    message: str
    saved_path: str


@dataclass(frozen=True)
class ProfileContextDownloadResult:
    written: tuple[RawWriteResult, ...]
    recoverable_errors: tuple[RecoverableContextError, ...]


class StravaEndpoints:
    def __init__(self, client: StravaReadableClient) -> None:
        self._client = client

    def get_authenticated_athlete(self) -> dict[str, Any]:
        return _expect_object(self._client.get("/athlete"), "/athlete")

    def get_athlete_zones(self) -> Any:
        return self._client.get("/athlete/zones")

    def get_athlete_stats(self, athlete_id: int | str) -> dict[str, Any]:
        endpoint = f"/athletes/{athlete_id}/stats"
        return _expect_object(self._client.get(endpoint), endpoint)

    def list_athlete_clubs(
        self,
        *,
        per_page: int = DEFAULT_CONTEXT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        return list(self._client.paginate("/athlete/clubs", per_page=per_page))

    def list_athlete_routes(
        self,
        athlete_id: int | str,
        *,
        per_page: int = DEFAULT_CONTEXT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        return list(
            self._client.paginate(
                f"/athletes/{athlete_id}/routes",
                per_page=per_page,
            )
        )

    def get_route(self, route_id: int | str) -> dict[str, Any]:
        endpoint = f"/routes/{route_id}"
        return _expect_object(self._client.get(endpoint), endpoint)

    def get_route_streams(self, route_id: int | str) -> Any:
        return self._client.get(f"/routes/{route_id}/streams")

    def get_route_export_gpx(self, route_id: int | str) -> bytes:
        return self._client.get_bytes(f"/routes/{route_id}/export_gpx")

    def get_route_export_tcx(self, route_id: int | str) -> bytes:
        return self._client.get_bytes(f"/routes/{route_id}/export_tcx")

    def get_gear(self, gear_id: str) -> dict[str, Any]:
        endpoint = f"/gear/{gear_id}"
        return _expect_object(self._client.get(endpoint), endpoint)

    def get_club(self, club_id: int | str) -> dict[str, Any]:
        endpoint = f"/clubs/{club_id}"
        return _expect_object(self._client.get(endpoint), endpoint)

    def list_athlete_activities(
        self,
        *,
        before: int | None = None,
        after: int | None = None,
        per_page: int = DEFAULT_ACTIVITY_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        params = _without_none({"before": before, "after": after})
        return list(
            self._client.paginate(
                "/athlete/activities",
                params=params,
                per_page=per_page,
            )
        )

    def get_activity(
        self,
        activity_id: int | str,
        *,
        include_all_efforts: bool = True,
    ) -> dict[str, Any]:
        endpoint = f"/activities/{activity_id}"
        payload = self._client.get(
            endpoint,
            params={
                "include_all_efforts": str(include_all_efforts).lower(),
            },
        )
        return _expect_object(payload, endpoint)

    def get_activity_streams(
        self,
        activity_id: int | str,
        *,
        keys: tuple[str, ...] = DEFAULT_ACTIVITY_STREAM_KEYS,
        key_by_type: bool = True,
    ) -> Any:
        return self._client.get(
            f"/activities/{activity_id}/streams",
            params={
                "key_by_type": str(key_by_type).lower(),
                "keys": ",".join(keys),
            },
        )

    def get_activity_zones(self, activity_id: int | str) -> Any:
        return self._client.get(f"/activities/{activity_id}/zones")

    def get_activity_laps(self, activity_id: int | str) -> list[dict[str, Any]]:
        endpoint = f"/activities/{activity_id}/laps"
        return _expect_list(self._client.get(endpoint), endpoint)

    def list_starred_segments(
        self,
        *,
        per_page: int = DEFAULT_CONTEXT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        return list(self._client.paginate("/segments/starred", per_page=per_page))

    def get_segment(self, segment_id: int | str) -> dict[str, Any]:
        endpoint = f"/segments/{segment_id}"
        return _expect_object(self._client.get(endpoint), endpoint)

    def get_segment_streams(
        self,
        segment_id: int | str,
        *,
        keys: tuple[str, ...] = DEFAULT_SEGMENT_STREAM_KEYS,
        key_by_type: bool = True,
    ) -> Any:
        return self._client.get(
            f"/segments/{segment_id}/streams",
            params={
                "key_by_type": str(key_by_type).lower(),
                "keys": ",".join(keys),
            },
        )


def download_profile_context(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    *,
    include_club_details: bool = True,
    include_route_details: bool = True,
    include_route_exports: bool = True,
    include_route_streams: bool = True,
    include_starred_segments: bool = True,
    include_segment_details: bool = True,
    include_segment_streams: bool = True,
    include_gear_details: bool = True,
    per_page: int = DEFAULT_CONTEXT_PAGE_SIZE,
) -> ProfileContextDownloadResult:
    written: list[RawWriteResult] = []
    recoverable_errors: list[RecoverableContextError] = []
    segment_ids: set[str] = set()

    athlete = endpoints.get_authenticated_athlete()
    written.append(
        raw_store.write_json(
            "athlete/profile.json",
            athlete,
            endpoint="/athlete",
        )
    )
    athlete_id = _required_identifier(athlete, "id", "authenticated athlete")

    stats_endpoint = f"/athletes/{athlete_id}/stats"
    written.append(
        raw_store.write_json(
            "athlete/stats.json",
            endpoints.get_athlete_stats(athlete_id),
            endpoint=stats_endpoint,
        )
    )

    zones = _fetch_optional(
        name="athlete_zones",
        endpoint="/athlete/zones",
        fetch=endpoints.get_athlete_zones,
        raw_store=raw_store,
        error_path="errors/athlete_zones.json",
        recoverable_errors=recoverable_errors,
    )
    if zones is not None:
        written.append(
            raw_store.write_json(
                "athlete/zones.json",
                zones,
                endpoint="/athlete/zones",
            )
        )

    clubs = _fetch_optional(
        name="athlete_clubs",
        endpoint="/athlete/clubs",
        fetch=lambda: endpoints.list_athlete_clubs(per_page=per_page),
        raw_store=raw_store,
        error_path="errors/athlete_clubs.json",
        recoverable_errors=recoverable_errors,
    )
    if clubs is not None:
        written.append(
            raw_store.write_json(
                "clubs/clubs.json",
                clubs,
                endpoint="/athlete/clubs",
                params={"per_page": per_page},
            )
        )
        if include_club_details:
            written.extend(
                _download_club_details(
                    endpoints,
                    raw_store,
                    clubs,
                    recoverable_errors,
                )
            )

    routes_endpoint = f"/athletes/{athlete_id}/routes"
    routes = _fetch_optional(
        name="athlete_routes",
        endpoint=routes_endpoint,
        fetch=lambda: endpoints.list_athlete_routes(athlete_id, per_page=per_page),
        raw_store=raw_store,
        error_path="errors/athlete_routes.json",
        recoverable_errors=recoverable_errors,
    )
    if routes is not None:
        written.append(
            raw_store.write_json(
                "routes/routes.json",
                routes,
                endpoint=routes_endpoint,
                params={"per_page": per_page},
            )
        )
        if include_route_details:
            written.extend(
                _download_route_details(
                    endpoints,
                    raw_store,
                    routes,
                    recoverable_errors,
                    segment_ids,
                    include_route_exports=include_route_exports,
                    include_route_streams=include_route_streams,
                )
            )

    if include_starred_segments:
        starred_segments = _fetch_optional(
            name="starred_segments",
            endpoint="/segments/starred",
            fetch=lambda: endpoints.list_starred_segments(per_page=per_page),
            raw_store=raw_store,
            error_path="errors/starred_segments.json",
            recoverable_errors=recoverable_errors,
        )
        if starred_segments is not None:
            written.append(
                raw_store.write_json(
                    "segments/starred.json",
                    starred_segments,
                    endpoint="/segments/starred",
                    params={"per_page": per_page},
                )
            )
            segment_ids.update(_extract_segment_ids(starred_segments))

    if include_segment_details:
        written.extend(
            _download_segment_details(
                endpoints,
                raw_store,
                segment_ids,
                recoverable_errors,
                include_segment_streams=include_segment_streams,
            )
        )

    if include_gear_details:
        written.extend(
            _download_gear_details(
                endpoints,
                raw_store,
                athlete,
                recoverable_errors,
            )
        )

    return ProfileContextDownloadResult(
        written=tuple(written),
        recoverable_errors=tuple(recoverable_errors),
    )


def _download_route_details(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    routes: list[dict[str, Any]],
    recoverable_errors: list[RecoverableContextError],
    segment_ids: set[str],
    *,
    include_route_exports: bool,
    include_route_streams: bool,
) -> list[RawWriteResult]:
    written = []
    for route in routes:
        route_id = route.get("id") or route.get("id_str")
        if route_id is None:
            continue
        safe_route_id = _safe_identifier(route_id)
        endpoint = f"/routes/{route_id}"
        payload = _fetch_optional(
            name=f"route_{route_id}",
            endpoint=endpoint,
            fetch=lambda route_id=route_id: endpoints.get_route(route_id),
            raw_store=raw_store,
            error_path=f"errors/route_{safe_route_id}.json",
            recoverable_errors=recoverable_errors,
        )
        if payload is None:
            continue
        written.append(
            raw_store.write_json(
                f"routes/{safe_route_id}.json",
                payload,
                endpoint=endpoint,
            )
        )
        segment_ids.update(_extract_segment_ids(payload))
        if include_route_streams:
            stream_payload = _fetch_optional(
                name=f"route_{route_id}_streams",
                endpoint=f"{endpoint}/streams",
                fetch=lambda route_id=route_id: endpoints.get_route_streams(route_id),
                raw_store=raw_store,
                error_path=f"errors/route_{safe_route_id}_streams.json",
                recoverable_errors=recoverable_errors,
            )
            if stream_payload is not None:
                written.append(
                    raw_store.write_json(
                        f"route_streams/{safe_route_id}.json",
                        stream_payload,
                        endpoint=f"{endpoint}/streams",
                    )
                )
        if include_route_exports:
            written.extend(
                _download_route_exports(
                    endpoints,
                    raw_store,
                    route_id,
                    safe_route_id,
                    recoverable_errors,
                )
            )
    return written


def _download_route_exports(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    route_id: object,
    safe_route_id: str,
    recoverable_errors: list[RecoverableContextError],
) -> list[RawWriteResult]:
    written = []
    for extension, fetch in (
        ("gpx", lambda: endpoints.get_route_export_gpx(route_id)),
        ("tcx", lambda: endpoints.get_route_export_tcx(route_id)),
    ):
        endpoint = f"/routes/{route_id}/export_{extension}"
        payload = _fetch_optional(
            name=f"route_{route_id}_export_{extension}",
            endpoint=endpoint,
            fetch=fetch,
            raw_store=raw_store,
            error_path=f"errors/route_{safe_route_id}_export_{extension}.json",
            recoverable_errors=recoverable_errors,
        )
        if payload is None:
            continue
        written.append(
            raw_store.write_bytes(
                f"route_exports/{extension}/{safe_route_id}.{extension}",
                payload,
                endpoint=endpoint,
            )
        )
    return written


def _download_club_details(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    clubs: list[dict[str, Any]],
    recoverable_errors: list[RecoverableContextError],
) -> list[RawWriteResult]:
    written = []
    for club in clubs:
        club_id = club.get("id")
        if club_id is None:
            continue
        safe_club_id = _safe_identifier(club_id)
        endpoint = f"/clubs/{club_id}"
        payload = _fetch_optional(
            name=f"club_{club_id}",
            endpoint=endpoint,
            fetch=lambda club_id=club_id: endpoints.get_club(club_id),
            raw_store=raw_store,
            error_path=f"errors/club_{safe_club_id}.json",
            recoverable_errors=recoverable_errors,
        )
        if payload is None:
            continue
        written.append(
            raw_store.write_json(
                f"clubs/{safe_club_id}.json",
                payload,
                endpoint=endpoint,
            )
        )
    return written


def _download_segment_details(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    segment_ids: set[str],
    recoverable_errors: list[RecoverableContextError],
    *,
    include_segment_streams: bool,
) -> list[RawWriteResult]:
    written = []
    for segment_id in sorted(segment_ids):
        safe_segment_id = _safe_identifier(segment_id)
        endpoint = f"/segments/{segment_id}"
        payload = _fetch_optional(
            name=f"segment_{segment_id}",
            endpoint=endpoint,
            fetch=lambda segment_id=segment_id: endpoints.get_segment(segment_id),
            raw_store=raw_store,
            error_path=f"errors/segment_{safe_segment_id}.json",
            recoverable_errors=recoverable_errors,
        )
        if payload is None:
            continue
        written.append(
            raw_store.write_json(
                f"segments/{safe_segment_id}.json",
                payload,
                endpoint=endpoint,
            )
        )
        if include_segment_streams:
            stream_endpoint = f"/segments/{segment_id}/streams"
            stream_payload = _fetch_optional(
                name=f"segment_{segment_id}_streams",
                endpoint=stream_endpoint,
                fetch=lambda segment_id=segment_id: endpoints.get_segment_streams(
                    segment_id
                ),
                raw_store=raw_store,
                error_path=f"errors/segment_{safe_segment_id}_streams.json",
                recoverable_errors=recoverable_errors,
            )
            if stream_payload is None:
                continue
            written.append(
                raw_store.write_json(
                    f"segment_streams/{safe_segment_id}.json",
                    stream_payload,
                    endpoint=stream_endpoint,
                )
            )
    return written


def _download_gear_details(
    endpoints: StravaEndpoints,
    raw_store: RawStore,
    athlete: dict[str, Any],
    recoverable_errors: list[RecoverableContextError],
) -> list[RawWriteResult]:
    written = []
    for gear_id in _extract_gear_ids(athlete):
        safe_gear_id = _safe_identifier(gear_id)
        endpoint = f"/gear/{gear_id}"
        payload = _fetch_optional(
            name=f"gear_{gear_id}",
            endpoint=endpoint,
            fetch=lambda gear_id=gear_id: endpoints.get_gear(gear_id),
            raw_store=raw_store,
            error_path=f"errors/gear_{safe_gear_id}.json",
            recoverable_errors=recoverable_errors,
        )
        if payload is None:
            continue
        written.append(
            raw_store.write_json(
                f"gear/{safe_gear_id}.json",
                payload,
                endpoint=endpoint,
            )
        )
    return written


def _fetch_optional(
    *,
    name: str,
    endpoint: str,
    fetch,
    raw_store: RawStore,
    error_path: str,
    recoverable_errors: list[RecoverableContextError],
) -> Any | None:
    try:
        return fetch()
    except StravaApiError as error:
        if error.status_code not in RECOVERABLE_CONTEXT_STATUS_CODES:
            raise
        saved = raw_store.write_json(
            error_path,
            {
                "endpoint": endpoint,
                "errors": [detail.label() for detail in error.errors],
                "message": error.message,
                "name": name,
                "status_code": error.status_code,
            },
            endpoint=endpoint,
            kind="error",
        )
        recoverable_errors.append(
            RecoverableContextError(
                name=name,
                endpoint=endpoint,
                status_code=error.status_code,
                message=error.message,
                saved_path=saved.relative_path,
            )
        )
        return None


def _extract_gear_ids(athlete: dict[str, Any]) -> tuple[str, ...]:
    gear_ids = []
    for key in ("bikes", "shoes"):
        values = athlete.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, dict):
                continue
            gear_id = value.get("id")
            if gear_id is not None:
                gear_ids.append(str(gear_id))
    return tuple(dict.fromkeys(gear_ids))


def _extract_segment_ids(payload: Any) -> set[str]:
    segment_ids: set[str] = set()
    if isinstance(payload, list):
        for item in payload:
            segment_ids.update(_extract_segment_ids(item))
        return segment_ids
    if not isinstance(payload, dict):
        return segment_ids

    if _looks_like_segment(payload) and payload.get("id") is not None:
        segment_ids.add(str(payload["id"]))

    for key in ("segments", "starred_segments"):
        segment_ids.update(_extract_segment_ids(payload.get(key)))

    segment_efforts = payload.get("segment_efforts")
    if isinstance(segment_efforts, list):
        for effort in segment_efforts:
            if not isinstance(effort, dict):
                continue
            segment = effort.get("segment")
            if isinstance(segment, dict) and segment.get("id") is not None:
                segment_ids.add(str(segment["id"]))
            elif effort.get("segment_id") is not None:
                segment_ids.add(str(effort["segment_id"]))

    return segment_ids


def _looks_like_segment(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "activity_type",
            "average_grade",
            "climb_category",
            "elevation_high",
            "elevation_low",
            "hazardous",
            "starred",
        )
    )


def _expect_object(payload: Any, endpoint: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StravaContextDownloadError(
            f"Expected a JSON object from Strava endpoint: {endpoint}"
        )
    return payload


def _expect_list(payload: Any, endpoint: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise StravaContextDownloadError(
            f"Expected a JSON list from Strava endpoint: {endpoint}"
        )
    for item in payload:
        if not isinstance(item, dict):
            raise StravaContextDownloadError(
                f"Expected JSON objects in Strava endpoint: {endpoint}"
            )
    return payload


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _required_identifier(
    payload: dict[str, Any],
    field: str,
    label: str,
) -> int | str:
    value = payload.get(field)
    if value is None:
        raise StravaContextDownloadError(f"Missing {field!r} in {label}.")
    if not isinstance(value, int | str):
        raise StravaContextDownloadError(f"Invalid {field!r} in {label}.")
    return value


def _safe_identifier(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    if not normalized:
        raise StravaContextDownloadError("Cannot build a safe filename identifier.")
    return normalized
