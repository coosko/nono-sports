"""Strava OAuth flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from nono_sports.core.config import StravaClientConfig
from nono_sports.core.errors import AuthenticationError, ConfigurationError

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"  # noqa: S105
REQUIRED_SCOPES = ("read", "read_all", "profile:read_all", "activity:read_all")


@dataclass(frozen=True)
class StravaTokenResponse:
    token_type: str
    access_token: str
    refresh_token: str
    expires_at: int
    scope: tuple[str, ...]
    athlete: dict[str, Any]


def build_authorization_url(
    config: StravaClientConfig,
    *,
    state: str | None = None,
    approval_prompt: str = "force",
    scopes: tuple[str, ...] = REQUIRED_SCOPES,
) -> str:
    query = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "approval_prompt": approval_prompt,
        "scope": ",".join(scopes),
    }
    if state:
        query["state"] = state
    return f"{AUTHORIZE_URL}?{urlencode(query)}"


def parse_scopes(
    scope_value: str | list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    if not scope_value:
        return ()
    if isinstance(scope_value, str):
        normalized = scope_value.replace(",", " ")
        return tuple(scope for scope in normalized.split() if scope)
    return tuple(scope_value)


def missing_required_scopes(
    granted_scopes: tuple[str, ...],
    required_scopes: tuple[str, ...] = REQUIRED_SCOPES,
) -> tuple[str, ...]:
    granted = set(granted_scopes)
    return tuple(scope for scope in required_scopes if scope not in granted)


def exchange_code_for_token(
    config: StravaClientConfig,
    code: str,
    *,
    timeout: float = 20.0,
) -> StravaTokenResponse:
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise AuthenticationError(format_token_error(error.response)) from error
    return parse_token_response(response.json())


def format_token_error(response: httpx.Response) -> str:
    detail = _extract_error_detail(response)
    return (
        "Strava token exchange failed "
        f"({response.status_code} {response.reason_phrase}): {detail}"
    )


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "empty response"

    message = str(payload.get("message") or "no message")
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return message

    formatted_errors = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        resource = item.get("resource")
        field = item.get("field")
        code = item.get("code")
        parts = [str(part) for part in (resource, field, code) if part]
        if parts:
            formatted_errors.append(".".join(parts))

    if not formatted_errors:
        return message
    return f"{message}; {', '.join(formatted_errors)}"


def parse_token_response(payload: dict[str, Any]) -> StravaTokenResponse:
    granted_scopes = parse_scopes(payload.get("scope"))
    missing_scopes = missing_required_scopes(granted_scopes)
    if missing_scopes:
        raise ConfigurationError(
            "Strava authorization is missing required scopes: "
            + ", ".join(missing_scopes)
        )

    return StravaTokenResponse(
        token_type=str(payload["token_type"]),
        access_token=str(payload["access_token"]),
        refresh_token=str(payload["refresh_token"]),
        expires_at=int(payload["expires_at"]),
        scope=granted_scopes,
        athlete=dict(payload.get("athlete") or {}),
    )
