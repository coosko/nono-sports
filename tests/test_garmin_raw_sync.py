import io
import json
import zipfile
from datetime import UTC, datetime

from nono_sports.garmin_connect.client import GarminConnectClient
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.garmin_connect.state_store import GarminStateStore
from nono_sports.garmin_connect.sync import sync_garmin_activities_raw


class FakeGarminApi:
    def get_activities(self, start=0, limit=20, activitytype=None):
        activities = [{"activityId": 123, "activityName": "Test activity"}]
        return activities[start : start + limit]

    def get_activity(self, activity_id):
        return {"activityId": activity_id}

    def get_activity_details(self, activity_id, maxchart=2000, maxpoly=4000):
        return {"activityId": activity_id, "detailsAvailable": True}

    def get_activity_splits(self, activity_id):
        return {"activityId": activity_id, "lapDTOs": []}

    def get_activity_typed_splits(self, activity_id):
        return {"activityId": activity_id, "splits": []}

    def get_activity_split_summaries(self, activity_id):
        return {"activityId": activity_id, "splitSummaries": []}

    def get_activity_weather(self, activity_id):
        return {"activityId": activity_id, "weather": "clear"}

    def download_activity(self, activity_id, dl_fmt):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                f"{activity_id}_ACTIVITY.fit",
                b"\x0e\x20\x00\x00\x00\x00\x00\x00.FIT\x00\x00",
            )
        return buffer.getvalue()


class PagedFakeGarminApi(FakeGarminApi):
    def __init__(self):
        self.list_calls = []

    def get_activities(self, start=0, limit=20, activitytype=None):
        self.list_calls.append((start, limit))
        activities = [
            {"activityId": 1, "activityName": "Done 1"},
            {"activityId": 2, "activityName": "Done 2"},
            {"activityId": 3, "activityName": "Pending 3"},
        ]
        return activities[start : start + limit]


class RecentPagedFakeGarminApi(FakeGarminApi):
    def __init__(self):
        self.list_calls = []

    def get_activities(self, start=0, limit=20, activitytype=None):
        self.list_calls.append((start, limit))
        activities = [
            {
                "activityId": 10,
                "activityName": "Recent 10",
                "beginTimestamp": "2026-07-10T08:00:00+00:00",
            },
            {
                "activityId": 9,
                "activityName": "Old 9",
                "beginTimestamp": "2026-07-01T08:00:00+00:00",
            },
            {
                "activityId": 8,
                "activityName": "Older 8",
                "beginTimestamp": "2026-06-30T08:00:00+00:00",
            },
        ]
        return activities[start : start + limit]


class ImportedGpxGarminApi(FakeGarminApi):
    def get_activities(self, start=0, limit=20, activitytype=None):
        activities = [{"activityId": 456, "activityName": "Imported hike"}]
        return activities[start : start + limit]

    def get_activity(self, activity_id):
        return {
            "activityId": activity_id,
            "metadataDTO": {
                "fileFormat": {"formatKey": "gpx"},
                "isOriginal": False,
            },
        }

    def download_activity(self, activity_id, dl_fmt):
        if dl_fmt == "original":
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(
                    f"{activity_id}_ACTIVITY.gpx",
                    b'<?xml version="1.0"?><gpx><trk><trkseg /></trk></gpx>',
                )
            return buffer.getvalue()
        return f"<{dl_fmt}></{dl_fmt}>".encode()


class FakeGarminModule:
    class Garmin:
        class ActivityDownloadFormat:
            ORIGINAL = "original"
            TCX = "tcx"
            GPX = "gpx"
            KML = "kml"
            CSV = "csv"


def test_garmin_raw_store_writes_manifest_entry(tmp_path) -> None:
    store = GarminRawStore(
        tmp_path,
        clock=lambda: datetime(2026, 7, 1, tzinfo=UTC),
    )

    result = store.write_json(
        "activities/123.json",
        {"activityId": 123},
        endpoint="get_activity",
        params={"activity_id": "123"},
    )

    assert result.relative_path == "activities/123.json"
    manifest_path = tmp_path / "10_fuentes/garmin_connect/raw/manifest.jsonl"
    manifest = json.loads(manifest_path.read_text().splitlines()[0])
    assert manifest["endpoint"] == "get_activity"
    assert manifest["path"] == "activities/123.json"


def test_garmin_state_store_round_trips_state(tmp_path) -> None:
    store = GarminStateStore(tmp_path)
    state = store.empty_state()
    state["activities"]["123"] = {"activity": "activities/123.json"}

    store.save(state)

    loaded = store.load()
    assert loaded["activities"]["123"]["activity"] == "activities/123.json"
    assert store.path == (
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "logs"
        / "activity_sync_state.json"
    )


def test_sync_garmin_activities_raw_writes_expected_files(tmp_path) -> None:
    api = FakeGarminApi()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)
    raw_store = GarminRawStore(tmp_path)
    state_store = GarminStateStore(tmp_path)

    result = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        limit=1,
        max_activities=1,
    )

    assert result.listed_activities == 1
    assert result.processed_activities == 1
    assert result.skipped_activities == 0
    assert len(result.written) == 9
    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    assert (raw_root / "activities_index_0.json").is_file()
    assert (raw_root / "activities/123.json").is_file()
    assert (raw_root / "activities/123.details.json").is_file()
    assert (raw_root / "splits/123.json").is_file()
    assert (raw_root / "typed_splits/123.json").is_file()
    assert (raw_root / "splits/123.summaries.json").is_file()
    assert (raw_root / "weather/123.json").is_file()
    assert (raw_root / "activity_files/123.original.zip").is_file()
    assert (raw_root / "activity_files/123.fit").is_file()


def test_sync_garmin_activities_raw_skips_completed_activity(tmp_path) -> None:
    api = FakeGarminApi()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)
    raw_store = GarminRawStore(tmp_path)
    state_store = GarminStateStore(tmp_path)

    sync_garmin_activities_raw(client, raw_store, state_store, limit=1)
    result = sync_garmin_activities_raw(client, raw_store, state_store, limit=1)

    assert result.processed_activities == 0
    assert result.skipped_activities == 1


def test_sync_garmin_activities_raw_paginates_until_pending_activity(tmp_path) -> None:
    api = PagedFakeGarminApi()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)
    raw_store = GarminRawStore(tmp_path)
    state_store = GarminStateStore(tmp_path)
    state = state_store.load()
    state["activities"]["1"] = {
        "activity": "activities/1.json",
        "details": "activities/1.details.json",
        "fit": "activity_files/1.fit",
    }
    state["activities"]["2"] = {
        "activity": "activities/2.json",
        "details": "activities/2.details.json",
        "fit": "activity_files/2.fit",
    }
    state_store.save(state)

    result = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        limit=1,
        max_activities=1,
        max_pages=5,
    )

    assert api.list_calls == [(0, 1), (1, 1), (2, 1)]
    assert result.listed_activities == 3
    assert result.scanned_pages == 3
    assert result.skipped_activities == 2
    assert result.processed_activities == 1
    assert (
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "raw"
        / "activities"
        / "3.json"
    ).is_file()


def test_sync_garmin_activities_raw_uses_incremental_watermark(tmp_path) -> None:
    api = RecentPagedFakeGarminApi()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)
    raw_store = GarminRawStore(tmp_path)
    state_store = GarminStateStore(tmp_path)
    state = state_store.load()
    state["last_successful_activity_sync_at"] = "2026-07-10T10:00:00+00:00"
    state_store.save(state)

    result = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        limit=2,
        max_activities=None,
        max_pages=5,
        incremental_lookback_days=2,
        clock=lambda: datetime(2026, 7, 11, 10, tzinfo=UTC),
    )

    assert api.list_calls == [(0, 2)]
    assert result.listed_activities == 2
    assert result.scanned_pages == 1
    assert result.processed_activities == 1
    assert result.stopped_reason == "incremental_after_reached"

    saved_state = state_store.load()
    last_run = saved_state["runs"][-1]
    assert last_run["effective_after"] == int(
        datetime(2026, 7, 8, 10, tzinfo=UTC).timestamp()
    )
    assert saved_state["last_successful_activity_sync_at"] == (
        "2026-07-11T10:00:00+00:00"
    )


def test_sync_garmin_activities_raw_can_full_scan_without_watermark(tmp_path) -> None:
    api = RecentPagedFakeGarminApi()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)
    raw_store = GarminRawStore(tmp_path)
    state_store = GarminStateStore(tmp_path)
    state = state_store.load()
    state["last_successful_activity_sync_at"] = "2026-07-10T10:00:00+00:00"
    state_store.save(state)

    result = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        limit=2,
        max_activities=None,
        max_pages=5,
        incremental=False,
    )

    assert api.list_calls == [(0, 2), (2, 2), (4, 2)]
    assert result.processed_activities == 3
    assert result.stopped_reason is None


def test_sync_garmin_activities_raw_warns_and_falls_back_when_original_has_no_fit(
    tmp_path,
) -> None:
    api = ImportedGpxGarminApi()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)
    raw_store = GarminRawStore(tmp_path)
    state_store = GarminStateStore(tmp_path)

    result = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        limit=1,
        max_activities=1,
    )

    raw_root = tmp_path / "10_fuentes" / "garmin_connect" / "raw"
    state = state_store.load()
    activity_state = state["activities"]["456"]
    assert result.recoverable_errors == ()
    assert len(result.warnings) == 1
    assert result.warnings[0].part == "fit"
    assert activity_state["fit_unavailable"] is True
    assert "fit_error" not in activity_state
    assert activity_state["gpx"] == "activity_files/456.gpx"
    assert (raw_root / "activity_files/456.original.zip").is_file()
    assert (raw_root / "activity_files/456.gpx").is_file()

    second = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        limit=1,
        max_activities=1,
    )
    assert second.processed_activities == 0
    assert second.skipped_activities == 1
