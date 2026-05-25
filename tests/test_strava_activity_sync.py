import json
from collections.abc import Iterator, Mapping
from typing import Any

from nono_sports.storage.raw_store import RawStore
from nono_sports.storage.state_store import StateStore
from nono_sports.strava.client import StravaApiError, StravaRateLimitBudgetExceeded
from nono_sports.strava.endpoints import StravaEndpoints
from nono_sports.strava.rate_limits import RateLimitPair, RateLimitSnapshot
from nono_sports.strava.sync import sync_activities_raw


def test_sync_activities_raw_writes_default_free_activity_data(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
            {"id": 2, "name": "Ride", "sport_type": "Ride"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/1/laps": [{"id": 11, "lap_index": 1}],
            "/activities/1/streams": {"distance": {"data": [0, 10]}},
            "/activities/2": {"id": 2, "name": "Ride", "full": True},
            "/activities/2/laps": [{"id": 21, "lap_index": 1}],
            "/activities/2/streams": {"distance": {"data": [0, 20]}},
        },
    )
    raw_store = RawStore(tmp_path)
    state_store = StateStore(tmp_path)

    result = sync_activities_raw(
        StravaEndpoints(client),
        raw_store,
        state_store,
    )

    assert result.listed_activities == 2
    assert result.processed_activities == 2
    assert result.skipped_activities == 0
    assert result.recoverable_errors == ()
    assert _relative_paths(result.written) == {
        "activities/activities.json",
        "activities/1.json",
        "laps/1.json",
        "streams/1.json",
        "activities/2.json",
        "laps/2.json",
        "streams/2.json",
    }
    state = json.loads(state_store.path.read_text())
    assert state["activities"]["1"]["detail"] == "activities/1.json"
    assert state["activities"]["1"]["laps"] == "laps/1.json"
    assert state["activities"]["1"]["streams"] == "streams/1.json"
    assert state["activities"]["1"]["gear_checked"] is True
    assert state["activities"]["1"]["segments_checked"] is True
    assert "zones" not in state["activities"]["1"]
    assert _load_raw(tmp_path, "activities/2.json")["full"] is True


def test_sync_activities_raw_records_recoverable_optional_errors(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/1/laps": [],
        },
        get_errors={
            "/activities/1/streams": StravaApiError(
                status_code=404,
                reason_phrase="Not Found",
                message="Record Not Found",
            ),
        },
    )
    raw_store = RawStore(tmp_path)
    state_store = StateStore(tmp_path)

    result = sync_activities_raw(
        StravaEndpoints(client),
        raw_store,
        state_store,
    )

    assert len(result.recoverable_errors) == 1
    assert result.recoverable_errors[0].saved_path == "errors/activity_1_streams.json"
    state = json.loads(state_store.path.read_text())
    assert state["activities"]["1"]["streams_error"] == (
        "errors/activity_1_streams.json"
    )
    assert _load_raw(tmp_path, "errors/activity_1_streams.json")["status_code"] == 404


def test_sync_activities_raw_fetches_zones_only_when_enabled(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/1/laps": [],
            "/activities/1/streams": {"distance": {"data": [0, 10]}},
            "/activities/1/zones": [{"score": 1}],
        },
    )

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        StateStore(tmp_path),
        include_zones=True,
    )

    assert "zones/1.json" in _relative_paths(result.written)


def test_sync_activities_raw_records_recoverable_zone_errors_when_enabled(
    tmp_path,
) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/1/laps": [],
            "/activities/1/streams": {"distance": {"data": [0, 10]}},
        },
        get_errors={
            "/activities/1/zones": StravaApiError(
                status_code=402,
                reason_phrase="Payment Required",
                message="Payment Required",
            ),
        },
    )

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        StateStore(tmp_path),
        include_zones=True,
    )

    assert len(result.recoverable_errors) == 1
    assert result.recoverable_errors[0].saved_path == "errors/activity_1_zones.json"
    assert _load_raw(tmp_path, "errors/activity_1_zones.json")["status_code"] == 402


def test_sync_activities_raw_fetches_activity_gear_and_segments(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {
                "id": 1,
                "gear_id": "g1",
                "segment_efforts": [
                    {"segment": {"id": 99, "name": "Hill"}},
                ],
            },
            "/activities/1/laps": [],
            "/activities/1/streams": {"distance": {"data": [0, 10]}},
            "/gear/g1": {"id": "g1", "name": "Shoes"},
            "/segments/99": {"id": 99, "name": "Hill"},
            "/segments/99/streams": {"distance": {"data": [0, 10]}},
        },
    )

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        StateStore(tmp_path),
    )

    assert {
        "gear/g1.json",
        "segments/99.json",
        "segment_streams/99.json",
    }.issubset(_relative_paths(result.written))


def test_sync_activities_raw_stops_gracefully_on_rate_limit(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {
                "id": 1,
                "segment_efforts": [
                    {"segment": {"id": 99, "name": "Hill"}},
                ],
            },
            "/activities/1/laps": [],
            "/activities/1/streams": {"distance": {"data": [0, 10]}},
            "/segments/99": {"id": 99, "name": "Hill"},
        },
        get_errors={
            "/segments/99/streams": StravaApiError(
                status_code=429,
                reason_phrase="Too Many Requests",
                message="Rate Limit Exceeded",
            )
        },
    )

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        StateStore(tmp_path),
    )

    assert result.stopped_reason == "rate_limit:Rate Limit Exceeded"
    assert "segments/99.json" in _relative_paths(result.written)


def test_sync_activities_raw_stops_gracefully_on_rate_limit_budget(
    tmp_path,
) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/1/laps": [],
        },
        get_errors={
            "/activities/1/streams": StravaRateLimitBudgetExceeded(
                "read 15-minute usage 195 reached threshold 195",
                rate_limit=_rate_limit_snapshot(),
            )
        },
    )

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        StateStore(tmp_path),
    )

    assert result.stopped_reason == (
        "rate_limit_budget:read 15-minute usage 195 reached threshold 195"
    )
    assert {"activities/1.json", "laps/1.json"}.issubset(
        _relative_paths(result.written)
    )


def test_sync_activities_raw_stops_gracefully_when_listing_hits_rate_limit_budget(
    tmp_path,
) -> None:
    client = FakeActivityClient(
        activities=[],
        get_payloads={},
        paginate_error=StravaRateLimitBudgetExceeded(
            "read daily usage 1995 reached threshold 1995",
            rate_limit=_rate_limit_snapshot(),
        ),
    )
    state_store = StateStore(tmp_path)

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        state_store,
    )

    assert result.listed_activities == 0
    assert result.processed_activities == 0
    assert result.stopped_reason == (
        "rate_limit_budget:read daily usage 1995 reached threshold 1995"
    )
    state = json.loads(state_store.path.read_text())
    assert state["runs"][-1]["stopped_reason"] == result.stopped_reason


def test_sync_activities_raw_skips_completed_activity_on_resume(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/1/laps": [],
            "/activities/1/streams": {"distance": {"data": [0, 10]}},
            "/activities/1/zones": [{"score": 1}],
        },
    )
    raw_store = RawStore(tmp_path)
    state_store = StateStore(tmp_path)

    first = sync_activities_raw(StravaEndpoints(client), raw_store, state_store)
    second = sync_activities_raw(StravaEndpoints(client), raw_store, state_store)

    assert first.processed_activities == 1
    assert second.processed_activities == 0
    assert second.skipped_activities == 1


def test_sync_activities_raw_limits_selected_activities(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
            {"id": 2, "name": "Ride", "sport_type": "Ride"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
        },
    )

    result = sync_activities_raw(
        StravaEndpoints(client),
        RawStore(tmp_path),
        StateStore(tmp_path),
        max_activities=1,
        include_gear=False,
        include_laps=False,
        include_segments=False,
        include_streams=False,
        include_zones=False,
    )

    assert result.listed_activities == 2
    assert result.processed_activities == 1
    assert "activities/2.json" not in _relative_paths(result.written)


def test_sync_activities_raw_limit_applies_to_pending_activities(tmp_path) -> None:
    client = FakeActivityClient(
        activities=[
            {"id": 1, "name": "Run", "sport_type": "Run"},
            {"id": 2, "name": "Ride", "sport_type": "Ride"},
        ],
        get_payloads={
            "/activities/1": {"id": 1, "name": "Run", "full": True},
            "/activities/2": {"id": 2, "name": "Ride", "full": True},
        },
    )
    raw_store = RawStore(tmp_path)
    state_store = StateStore(tmp_path)

    first = sync_activities_raw(
        StravaEndpoints(client),
        raw_store,
        state_store,
        max_activities=1,
        include_gear=False,
        include_laps=False,
        include_segments=False,
        include_streams=False,
        include_zones=False,
    )
    second = sync_activities_raw(
        StravaEndpoints(client),
        raw_store,
        state_store,
        max_activities=1,
        include_gear=False,
        include_laps=False,
        include_segments=False,
        include_streams=False,
        include_zones=False,
    )

    assert first.processed_activities == 1
    assert second.skipped_activities == 1
    assert second.processed_activities == 1
    assert "activities/2.json" in _relative_paths(second.written)


class FakeActivityClient:
    def __init__(
        self,
        *,
        activities: list[dict[str, Any]],
        get_payloads: dict[str, Any],
        get_errors: dict[str, Exception] | None = None,
        paginate_error: Exception | None = None,
    ) -> None:
        self._activities = activities
        self._get_payloads = get_payloads
        self._get_errors = get_errors or {}
        self._paginate_error = paginate_error

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> Any:
        if path in self._get_errors:
            raise self._get_errors[path]
        return self._get_payloads[path]

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        per_page: int = 200,
        start_page: int = 1,
    ) -> Iterator[dict[str, Any]]:
        assert path == "/athlete/activities"
        if self._paginate_error is not None:
            raise self._paginate_error
        yield from self._activities


def _rate_limit_snapshot() -> RateLimitSnapshot:
    return RateLimitSnapshot(
        overall_limit=RateLimitPair(fifteen_minutes=200, daily=2000),
        overall_usage=RateLimitPair(fifteen_minutes=195, daily=1995),
        read_limit=RateLimitPair(fifteen_minutes=200, daily=2000),
        read_usage=RateLimitPair(fifteen_minutes=195, daily=1995),
    )


def _relative_paths(written) -> set[str]:
    return {item.relative_path for item in written}


def _load_raw(tmp_path, relative_path: str) -> Any:
    path = tmp_path / "10_fuentes" / "strava" / "raw" / relative_path
    return json.loads(path.read_text())
