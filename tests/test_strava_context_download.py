import json
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from nono_sports.storage.raw_store import RawStore
from nono_sports.strava.client import StravaApiError
from nono_sports.strava.endpoints import (
    ProfileContextDownloadResult,
    StravaContextDownloadError,
    StravaEndpoints,
    download_profile_context,
)


def test_download_profile_context_writes_expected_raw_files(tmp_path) -> None:
    client = FakeStravaClient(
        get_payloads={
            "/athlete": {
                "id": 42,
                "bikes": [{"id": "bike-1"}],
                "shoes": [{"id": "shoe-1"}],
            },
            "/athlete/zones": {"heart_rate": {"zones": []}},
            "/athletes/42/stats": {"all_run_totals": {"count": 10}},
            "/clubs/10": {"id": 10, "name": "Club", "sport_type": "cycling"},
            "/routes/100": {
                "id": 100,
                "name": "Morning Route",
                "segments": [{"id": 99, "name": "Hill", "activity_type": "Ride"}],
            },
            "/routes/100/streams": {"latlng": [[40.0, -3.0]]},
            "/segments/88": {"id": 88, "name": "Starred"},
            "/segments/88/streams": {"distance": {"data": [0, 10]}},
            "/segments/99": {"id": 99, "name": "Hill"},
            "/segments/99/streams": {"distance": {"data": [0, 20]}},
            "/gear/bike-1": {"id": "bike-1", "name": "Road bike"},
            "/gear/shoe-1": {"id": "shoe-1", "name": "Fast shoes"},
        },
        bytes_payloads={
            "/routes/100/export_gpx": b"<gpx />\n",
            "/routes/100/export_tcx": b"<TrainingCenterDatabase />\n",
        },
        paginated_payloads={
            "/athlete/clubs": [{"id": 10, "name": "Club"}],
            "/athletes/42/routes": [{"id": 100, "name": "Morning Route"}],
            "/segments/starred": [
                {"id": 88, "name": "Starred", "activity_type": "Run"}
            ],
        },
    )
    store = RawStore(tmp_path)

    result = download_profile_context(StravaEndpoints(client), store)

    assert isinstance(result, ProfileContextDownloadResult)
    assert result.recoverable_errors == ()
    assert _relative_paths(result) == {
        "athlete/profile.json",
        "athlete/stats.json",
        "athlete/zones.json",
        "clubs/10.json",
        "clubs/clubs.json",
        "route_exports/gpx/100.gpx",
        "route_exports/tcx/100.tcx",
        "route_streams/100.json",
        "routes/routes.json",
        "routes/100.json",
        "segments/88.json",
        "segments/99.json",
        "segments/starred.json",
        "segment_streams/88.json",
        "segment_streams/99.json",
        "gear/bike-1.json",
        "gear/shoe-1.json",
    }
    assert _load_raw(tmp_path, "athlete/profile.json")["id"] == 42
    assert _load_raw(tmp_path, "clubs/clubs.json") == [{"id": 10, "name": "Club"}]
    assert len(_manifest_entries(tmp_path)) == 17


def test_download_profile_context_records_recoverable_optional_errors(tmp_path) -> None:
    client = FakeStravaClient(
        get_payloads={
            "/athlete": {"id": 42, "bikes": [], "shoes": []},
            "/athletes/42/stats": {"all_run_totals": {"count": 10}},
        },
        get_errors={
            "/athlete/zones": _api_error(403, "Forbidden"),
        },
        paginated_payloads={
            "/athlete/clubs": [],
            "/athletes/42/routes": [],
            "/segments/starred": [],
        },
    )
    store = RawStore(tmp_path)

    result = download_profile_context(StravaEndpoints(client), store)

    assert len(result.recoverable_errors) == 1
    assert result.recoverable_errors[0].saved_path == "errors/athlete_zones.json"
    assert _load_raw(tmp_path, "errors/athlete_zones.json") == {
        "endpoint": "/athlete/zones",
        "errors": [],
        "message": "Forbidden",
        "name": "athlete_zones",
        "status_code": 403,
    }
    assert "athlete/profile.json" in _relative_paths(result)
    assert "athlete/zones.json" not in _relative_paths(result)


def test_download_profile_context_raises_without_athlete_id(tmp_path) -> None:
    client = FakeStravaClient(
        get_payloads={
            "/athlete": {"username": "nono"},
        },
        paginated_payloads={},
    )

    with pytest.raises(StravaContextDownloadError, match="Missing 'id'"):
        download_profile_context(StravaEndpoints(client), RawStore(tmp_path))


def test_download_profile_context_can_skip_details(tmp_path) -> None:
    client = FakeStravaClient(
        get_payloads={
            "/athlete": {"id": 42, "bikes": [{"id": "bike-1"}]},
            "/athlete/zones": {"heart_rate": {"zones": []}},
            "/athletes/42/stats": {"all_run_totals": {"count": 10}},
        },
        paginated_payloads={
            "/athlete/clubs": [],
            "/athletes/42/routes": [{"id": 100, "name": "Morning Route"}],
            "/segments/starred": [],
        },
    )

    result = download_profile_context(
        StravaEndpoints(client),
        RawStore(tmp_path),
        include_route_details=False,
        include_gear_details=False,
    )

    assert "routes/routes.json" in _relative_paths(result)
    assert "routes/100.json" not in _relative_paths(result)
    assert "gear/bike-1.json" not in _relative_paths(result)


class FakeStravaClient:
    def __init__(
        self,
        *,
        get_payloads: dict[str, Any],
        paginated_payloads: dict[str, list[dict[str, Any]]],
        bytes_payloads: dict[str, bytes] | None = None,
        get_errors: dict[str, Exception] | None = None,
    ) -> None:
        self._get_payloads = get_payloads
        self._bytes_payloads = bytes_payloads or {}
        self._paginated_payloads = paginated_payloads
        self._get_errors = get_errors or {}

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> Any:
        if path in self._get_errors:
            raise self._get_errors[path]
        return self._get_payloads[path]

    def get_bytes(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> bytes:
        if path in self._get_errors:
            raise self._get_errors[path]
        return self._bytes_payloads[path]

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        per_page: int = 200,
        start_page: int = 1,
    ) -> Iterator[dict[str, Any]]:
        yield from self._paginated_payloads[path]


def _api_error(status_code: int, message: str) -> StravaApiError:
    return StravaApiError(
        status_code=status_code,
        reason_phrase=message,
        message=message,
    )


def _relative_paths(result: ProfileContextDownloadResult) -> set[str]:
    return {item.relative_path for item in result.written}


def _load_raw(tmp_path, relative_path: str) -> Any:
    path = tmp_path / "10_fuentes" / "strava" / "raw" / relative_path
    return json.loads(path.read_text())


def _manifest_entries(tmp_path) -> list[dict[str, Any]]:
    path = tmp_path / "10_fuentes" / "strava" / "raw" / "manifest.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]
