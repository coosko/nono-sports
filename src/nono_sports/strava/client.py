"""Read-only Strava HTTP client."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from nono_sports.auth.strava_oauth import TOKEN_URL, StravaTokenResponse
from nono_sports.auth.token_store import StravaTokenStore
from nono_sports.core.config import StravaClientConfig
from nono_sports.core.errors import AuthenticationError, NonoSportsError
from nono_sports.strava.rate_limits import RateLimitSnapshot

API_BASE_URL = "https://www.strava.com/api/v3"
DEFAULT_PAGE_SIZE = 200
DEFAULT_REFRESH_LEEWAY_SECONDS = 3600


class StravaClientError(NonoSportsError):
    """Raised when the Strava client cannot complete a request."""


@dataclass(frozen=True)
class StravaRateLimitBudget:
    """Local read-request budget guard for long Strava syncs."""

    max_read_fifteen_minutes: int | None = None
    max_read_daily: int | None = None
    reserve_requests: int = 5


@dataclass(frozen=True)
class StravaErrorDetail:
    resource: str | None
    field: str | None
    code: str | None

    def label(self) -> str:
        return ".".join(
            value
            for value in (self.resource, self.field, self.code)
            if value is not None
        )


class StravaApiError(StravaClientError):
    """Normalized Strava API error."""

    def __init__(
        self,
        *,
        status_code: int,
        reason_phrase: str,
        message: str,
        errors: tuple[StravaErrorDetail, ...] = (),
        rate_limit: RateLimitSnapshot | None = None,
    ) -> None:
        details = ", ".join(error.label() for error in errors if error.label())
        suffix = f"; {details}" if details else ""
        super().__init__(
            f"Strava API failed ({status_code} {reason_phrase}): {message}{suffix}"
        )
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        self.message = message
        self.errors = errors
        self.rate_limit = rate_limit


class StravaRateLimitBudgetExceeded(StravaClientError):
    """Raised before sending a request that would exceed the local budget."""

    def __init__(
        self,
        message: str,
        *,
        rate_limit: RateLimitSnapshot | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.rate_limit = rate_limit


class StravaClient:
    """Small read-only wrapper around the Strava API."""

    def __init__(
        self,
        config: StravaClientConfig,
        token_store: StravaTokenStore,
        *,
        http_client: httpx.Client | None = None,
        api_base_url: str = API_BASE_URL,
        timeout: float = 20.0,
        clock: Callable[[], float] = time.time,
        refresh_leeway_seconds: int = DEFAULT_REFRESH_LEEWAY_SECONDS,
        rate_limit_budget: StravaRateLimitBudget | None = None,
    ) -> None:
        self._config = config
        self._token_store = token_store
        self._http = http_client or httpx.Client(timeout=timeout)
        self._owns_http_client = http_client is None
        self._api_base_url = api_base_url.rstrip("/")
        self._clock = clock
        self._refresh_leeway_seconds = refresh_leeway_seconds
        self._rate_limit_budget = rate_limit_budget
        self._rate_limit_budget_stop_reason: str | None = None
        self._token: StravaTokenResponse | None = None
        self.rate_limit_history: list[RateLimitSnapshot] = []

    @property
    def last_rate_limit(self) -> RateLimitSnapshot | None:
        if not self.rate_limit_history:
            return None
        return self.rate_limit_history[-1]

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> "StravaClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> Any:
        response = self._get_response(path, params=params)
        return _response_json(response)

    def get_bytes(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> bytes:
        response = self._get_response(path, params=params)
        return response.content

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        per_page: int = DEFAULT_PAGE_SIZE,
        start_page: int = 1,
    ) -> Iterator[dict[str, Any]]:
        page = start_page
        while True:
            page_params = dict(params or {})
            page_params["page"] = page
            page_params["per_page"] = per_page
            payload = self.get(path, params=page_params)
            if not isinstance(payload, list):
                raise StravaClientError(
                    f"Expected a list response while paginating Strava path: {path}"
                )
            if not payload:
                return
            for item in payload:
                if not isinstance(item, dict):
                    raise StravaClientError(
                        "Expected paginated Strava items to be JSON objects."
                    )
                yield item
            if len(payload) < per_page:
                return
            page += 1

    def _get_response(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> httpx.Response:
        token = self._current_token()
        response = self._send_get(path, token.access_token, params=params)
        if response.status_code == 401:
            token = self._refresh_token(token)
            response = self._send_get(path, token.access_token, params=params)
        self._raise_for_api_error(response)
        return response

    def _send_get(
        self,
        path: str,
        access_token: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> httpx.Response:
        self._raise_if_rate_limit_budget_exceeded()
        response = self._http.get(
            self._url(path),
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self._record_rate_limit(response.headers)
        return response

    def _current_token(self) -> StravaTokenResponse:
        token = self._token or self._token_store.load_token()
        if token.expires_at <= int(self._clock()) + self._refresh_leeway_seconds:
            token = self._refresh_token(token)
        self._token = token
        return token

    def _refresh_token(self, token: StravaTokenResponse) -> StravaTokenResponse:
        response = self._http.post(
            TOKEN_URL,
            data={
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise AuthenticationError(_format_token_refresh_error(response)) from error

        payload = _response_json(response)
        refreshed = StravaTokenResponse(
            token_type=str(payload.get("token_type") or token.token_type),
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            expires_at=int(payload["expires_at"]),
            scope=token.scope,
            athlete=token.athlete,
        )
        self._token_store.save(refreshed)
        self._token = refreshed
        return refreshed

    def _record_rate_limit(self, headers: Mapping[str, str]) -> None:
        snapshot = RateLimitSnapshot.from_headers(headers)
        if snapshot is not None:
            self.rate_limit_history.append(snapshot)
            self._rate_limit_budget_stop_reason = _rate_limit_budget_stop_reason(
                snapshot,
                self._rate_limit_budget,
            )

    def _raise_if_rate_limit_budget_exceeded(self) -> None:
        if self._rate_limit_budget_stop_reason is None:
            return
        raise StravaRateLimitBudgetExceeded(
            self._rate_limit_budget_stop_reason,
            rate_limit=self.last_rate_limit,
        )

    def _raise_for_api_error(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        payload = _response_json_or_none(response)
        message = response.reason_phrase
        errors: tuple[StravaErrorDetail, ...] = ()
        if isinstance(payload, dict):
            message = str(payload.get("message") or message)
            errors = _parse_error_details(payload.get("errors"))
        raise StravaApiError(
            status_code=response.status_code,
            reason_phrase=response.reason_phrase,
            message=message,
            errors=errors,
            rate_limit=self.last_rate_limit,
        )

    def _url(self, path: str) -> str:
        return f"{self._api_base_url}/{path.lstrip('/')}"


def _parse_error_details(value: object) -> tuple[StravaErrorDetail, ...]:
    if not isinstance(value, list):
        return ()
    details = []
    for item in value:
        if not isinstance(item, dict):
            continue
        details.append(
            StravaErrorDetail(
                resource=_optional_string(item.get("resource")),
                field=_optional_string(item.get("field")),
                code=_optional_string(item.get("code")),
            )
        )
    return tuple(details)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _rate_limit_budget_stop_reason(
    snapshot: RateLimitSnapshot,
    budget: StravaRateLimitBudget | None,
) -> str | None:
    if budget is None:
        return None
    read_usage = snapshot.read_usage or snapshot.overall_usage
    if read_usage is None:
        return None
    read_limit = snapshot.read_limit or snapshot.overall_limit
    reserve = max(0, budget.reserve_requests)
    daily_reason = _rate_limit_threshold_reason(
        window="daily",
        usage=read_usage.daily,
        reported_limit=read_limit.daily if read_limit else None,
        configured_cap=budget.max_read_daily,
        reserve=reserve,
    )
    if daily_reason is not None:
        return daily_reason
    return _rate_limit_threshold_reason(
        window="15-minute",
        usage=read_usage.fifteen_minutes,
        reported_limit=read_limit.fifteen_minutes if read_limit else None,
        configured_cap=budget.max_read_fifteen_minutes,
        reserve=reserve,
    )


def _rate_limit_threshold_reason(
    *,
    window: str,
    usage: int,
    reported_limit: int | None,
    configured_cap: int | None,
    reserve: int,
) -> str | None:
    threshold = _effective_rate_limit_threshold(
        configured_cap=configured_cap,
        reported_limit=reported_limit,
        reserve=reserve,
    )
    if threshold is None or usage < threshold:
        return None
    limit_label = reported_limit if reported_limit is not None else "unknown"
    cap_label = configured_cap if configured_cap is not None else "none"
    return (
        f"read {window} usage {usage} reached threshold {threshold} "
        f"(reported limit {limit_label}, configured cap {cap_label}, "
        f"reserve {reserve})"
    )


def _effective_rate_limit_threshold(
    *,
    configured_cap: int | None,
    reported_limit: int | None,
    reserve: int,
) -> int | None:
    candidates = [
        value
        for value in (configured_cap, reported_limit)
        if value is not None
    ]
    if not candidates:
        return None
    return max(0, min(candidates) - reserve)


def _response_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as error:
        raise StravaClientError(
            f"Strava returned a non-JSON response ({response.status_code})."
        ) from error


def _response_json_or_none(response: httpx.Response) -> Any | None:
    try:
        return response.json()
    except ValueError:
        return None


def _format_token_refresh_error(response: httpx.Response) -> str:
    payload = _response_json_or_none(response)
    message = response.text or response.reason_phrase
    errors: tuple[StravaErrorDetail, ...] = ()
    if isinstance(payload, dict):
        message = str(payload.get("message") or message)
        errors = _parse_error_details(payload.get("errors"))
    details = ", ".join(error.label() for error in errors if error.label())
    suffix = f"; {details}" if details else ""
    return (
        "Strava token refresh failed "
        f"({response.status_code} {response.reason_phrase}): {message}{suffix}"
    )
