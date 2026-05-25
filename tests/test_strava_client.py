from urllib.parse import parse_qs

import httpx
import pytest

from nono_sports.auth.strava_oauth import (
    REQUIRED_SCOPES,
    TOKEN_URL,
    StravaTokenResponse,
)
from nono_sports.auth.token_store import StravaTokenStore
from nono_sports.core.config import StravaClientConfig
from nono_sports.core.errors import AuthenticationError
from nono_sports.strava.client import (
    API_BASE_URL,
    StravaApiError,
    StravaClient,
    StravaClientError,
    StravaRateLimitBudget,
    StravaRateLimitBudgetExceeded,
)
from nono_sports.strava.rate_limits import RateLimitPair, RateLimitSnapshot


def test_rate_limit_snapshot_parses_strava_headers() -> None:
    snapshot = RateLimitSnapshot.from_headers(
        {
            "X-RateLimit-Limit": "200,2000",
            "X-RateLimit-Usage": "12,34",
            "X-ReadRateLimit-Limit": "100,1000",
            "X-ReadRateLimit-Usage": "5,21",
        }
    )

    assert snapshot is not None
    assert snapshot.overall_limit == RateLimitPair(fifteen_minutes=200, daily=2000)
    assert snapshot.overall_usage == RateLimitPair(fifteen_minutes=12, daily=34)
    assert snapshot.read_limit == RateLimitPair(fifteen_minutes=100, daily=1000)
    assert snapshot.read_usage == RateLimitPair(fifteen_minutes=5, daily=21)


def test_rate_limit_snapshot_returns_none_without_rate_headers() -> None:
    assert RateLimitSnapshot.from_headers({"Content-Type": "application/json"}) is None


def test_client_refreshes_expired_token_and_persists_new_token(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=100)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and str(request.url) == TOKEN_URL:
            form = parse_qs(request.content.decode())
            assert form["grant_type"] == ["refresh_token"]
            assert form["refresh_token"] == ["old-refresh"]
            return httpx.Response(
                200,
                request=request,
                json={
                    "token_type": "Bearer",
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_at": 2000,
                },
            )
        assert request.method == "GET"
        assert str(request.url) == f"{API_BASE_URL}/athlete"
        assert request.headers["Authorization"] == "Bearer new-access"
        return httpx.Response(
            200,
            request=request,
            headers={
                "X-RateLimit-Limit": "200,2000",
                "X-RateLimit-Usage": "1,10",
            },
            json={"id": 42},
        )

    client = _client(token_store, handler, clock=lambda: 1000)

    assert client.get("/athlete") == {"id": 42}
    assert [request.method for request in requests] == ["POST", "GET"]
    saved = token_store.load()
    assert saved["access_token"] == "new-access"
    assert saved["refresh_token"] == "new-refresh"
    assert client.last_rate_limit is not None
    assert client.last_rate_limit.overall_usage == RateLimitPair(
        fifteen_minutes=1,
        daily=10,
    )


def test_client_reuses_valid_token_without_refresh(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer old-access"
        return httpx.Response(200, request=request, json={"id": 42})

    client = _client(token_store, handler, clock=lambda: 1000)

    assert client.get("athlete") == {"id": 42}


def test_client_refreshes_once_after_unauthorized_response(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(
                200,
                request=request,
                json={
                    "token_type": "Bearer",
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_at": 3000,
                },
            )
        if calls.count("GET") == 1:
            return httpx.Response(
                401,
                request=request,
                json={"message": "Unauthorized"},
            )
        assert request.headers["Authorization"] == "Bearer new-access"
        return httpx.Response(200, request=request, json={"id": 42})

    client = _client(token_store, handler, clock=lambda: 1000)

    assert client.get("/athlete") == {"id": 42}
    assert calls == ["GET", "POST", "GET"]


def test_client_paginates_until_short_page(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        per_page = int(request.url.params["per_page"])
        assert per_page == 2
        payload = {
            1: [{"id": 1}, {"id": 2}],
            2: [{"id": 3}],
        }[page]
        return httpx.Response(200, request=request, json=payload)

    client = _client(token_store, handler, clock=lambda: 1000)

    assert list(client.paginate("/athlete/activities", per_page=2)) == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]


def test_client_raises_normalized_api_error(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            request=request,
            headers={
                "X-RateLimit-Limit": "200,2000",
                "X-RateLimit-Usage": "3,20",
            },
            json={
                "message": "Record Not Found",
                "errors": [
                    {
                        "resource": "Activity",
                        "field": "id",
                        "code": "invalid",
                    }
                ],
            },
        )

    client = _client(token_store, handler, clock=lambda: 1000)

    with pytest.raises(StravaApiError) as exc_info:
        client.get("/activities/999")

    error = exc_info.value
    assert error.status_code == 404
    assert error.message == "Record Not Found"
    assert error.errors[0].label() == "Activity.id.invalid"
    assert error.rate_limit is not None
    assert "Activity.id.invalid" in str(error)


def test_client_blocks_next_get_when_read_budget_is_reached(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            200,
            request=request,
            headers={
                "X-ReadRateLimit-Limit": "100,1000",
                "X-ReadRateLimit-Usage": "95,42",
            },
            json={"id": 42},
        )

    client = _client(
        token_store,
        handler,
        clock=lambda: 1000,
        rate_limit_budget=StravaRateLimitBudget(
            max_read_fifteen_minutes=200,
            max_read_daily=2000,
            reserve_requests=5,
        ),
    )

    assert client.get("/athlete") == {"id": 42}
    with pytest.raises(StravaRateLimitBudgetExceeded, match="15-minute"):
        client.get("/athlete")
    assert len(calls) == 1


def test_client_prioritizes_daily_budget_in_stop_reason(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            headers={
                "X-ReadRateLimit-Limit": "100,1000",
                "X-ReadRateLimit-Usage": "95,995",
            },
            json={"id": 42},
        )

    client = _client(
        token_store,
        handler,
        clock=lambda: 1000,
        rate_limit_budget=StravaRateLimitBudget(
            max_read_fifteen_minutes=200,
            max_read_daily=2000,
            reserve_requests=5,
        ),
    )

    assert client.get("/athlete") == {"id": 42}
    with pytest.raises(StravaRateLimitBudgetExceeded, match="daily usage"):
        client.get("/athlete")


def test_client_raises_error_when_paginated_payload_is_not_list(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=10000)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, json={"id": 42})

    client = _client(token_store, handler, clock=lambda: 1000)

    with pytest.raises(StravaClientError, match="Expected a list"):
        list(client.paginate("/athlete/activities"))


def test_client_raises_authentication_error_when_refresh_fails(tmp_path) -> None:
    token_store = _token_store(tmp_path, expires_at=100)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            request=request,
            json={
                "message": "Bad Request",
                "errors": [
                    {
                        "resource": "RefreshToken",
                        "field": "refresh_token",
                        "code": "invalid",
                    }
                ],
            },
        )

    client = _client(token_store, handler, clock=lambda: 1000)

    with pytest.raises(AuthenticationError, match="RefreshToken.refresh_token.invalid"):
        client.get("/athlete")


def _token_store(
    tmp_path,
    *,
    expires_at: int,
) -> StravaTokenStore:
    store = StravaTokenStore(tmp_path / "strava_tokens.json")
    store.save(
        StravaTokenResponse(
            token_type="Bearer",
            access_token="old-access",
            refresh_token="old-refresh",
            expires_at=expires_at,
            scope=REQUIRED_SCOPES,
            athlete={"id": 42},
        )
    )
    return store


def _client(
    token_store: StravaTokenStore,
    handler,
    *,
    clock,
    rate_limit_budget: StravaRateLimitBudget | None = None,
) -> StravaClient:
    return StravaClient(
        StravaClientConfig(client_id="123", client_secret="secret"),
        token_store,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=clock,
        rate_limit_budget=rate_limit_budget,
    )
