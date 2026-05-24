import stat

import httpx
import pytest

from nono_sports.auth.strava_oauth import (
    REQUIRED_SCOPES,
    TOKEN_URL,
    StravaTokenResponse,
    build_authorization_url,
    exchange_code_for_token,
    format_token_error,
    missing_required_scopes,
    parse_scopes,
)
from nono_sports.auth.token_store import StravaTokenStore
from nono_sports.core.config import StravaClientConfig
from nono_sports.core.errors import ConfigurationError


def test_build_authorization_url_includes_required_scopes() -> None:
    config = StravaClientConfig(
        client_id="123",
        client_secret="secret",
        redirect_uri="http://localhost/exchange_token",
    )

    url = build_authorization_url(config, state="abc")

    assert "https://www.strava.com/oauth/authorize" in url
    assert "client_id=123" in url
    assert "response_type=code" in url
    assert "state=abc" in url
    for scope in REQUIRED_SCOPES:
        assert scope.replace(":", "%3A") in url or scope in url


def test_parse_scopes_accepts_space_and_comma_delimiters() -> None:
    assert parse_scopes("read activity:read_all") == ("read", "activity:read_all")
    assert parse_scopes("read,activity:read_all") == ("read", "activity:read_all")


def test_missing_required_scopes_returns_missing_values() -> None:
    assert missing_required_scopes(("read",)) == (
        "read_all",
        "profile:read_all",
        "activity:read_all",
    )


def test_exchange_code_for_token_validates_scopes(monkeypatch) -> None:
    config = StravaClientConfig(client_id="123", client_secret="secret")

    def fake_post(url, data, timeout):
        assert url == TOKEN_URL
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == "auth-code"
        return httpx.Response(
            200,
            request=httpx.Request("POST", TOKEN_URL),
            json={
                "token_type": "Bearer",
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_at": 1234567890,
                "scope": "read read_all profile:read_all activity:read_all",
                "athlete": {"id": 42},
            },
        )

    monkeypatch.setattr("nono_sports.auth.strava_oauth.httpx.post", fake_post)

    token = exchange_code_for_token(config, "auth-code")

    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert token.scope == REQUIRED_SCOPES
    assert token.athlete == {"id": 42}


def test_exchange_code_for_token_rejects_missing_scopes(monkeypatch) -> None:
    config = StravaClientConfig(client_id="123", client_secret="secret")

    def fake_post(url, data, timeout):
        return httpx.Response(
            200,
            request=httpx.Request("POST", TOKEN_URL),
            json={
                "token_type": "Bearer",
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_at": 1234567890,
                "scope": "read",
                "athlete": {"id": 42},
            },
        )

    monkeypatch.setattr("nono_sports.auth.strava_oauth.httpx.post", fake_post)

    with pytest.raises(ConfigurationError, match="read_all"):
        exchange_code_for_token(config, "auth-code")


def test_format_token_error_includes_strava_error_detail() -> None:
    response = httpx.Response(
        400,
        request=httpx.Request("POST", TOKEN_URL),
        json={
            "message": "Bad Request",
            "errors": [
                {
                    "resource": "AuthorizationCode",
                    "field": "code",
                    "code": "invalid",
                }
            ],
        },
    )

    assert format_token_error(response) == (
        "Strava token exchange failed "
        "(400 Bad Request): Bad Request; AuthorizationCode.code.invalid"
    )


def test_token_store_saves_token_without_repo_assumptions(tmp_path) -> None:
    token_path = tmp_path / "auth" / "strava_tokens.json"
    store = StravaTokenStore(token_path)
    store.save(
        StravaTokenResponse(
            token_type="Bearer",
            access_token="access",
            refresh_token="refresh",
            expires_at=1234567890,
            scope=REQUIRED_SCOPES,
            athlete={"id": 42},
        )
    )

    saved = store.load()

    assert saved["refresh_token"] == "refresh"
    assert saved["athlete"] == {"id": 42}
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600
