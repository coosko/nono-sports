
import io
import zipfile

import pytest

from nono_sports.core.errors import AuthenticationError
from nono_sports.garmin_connect.auth import ensure_garmin_tokenstore
from nono_sports.garmin_connect.client import (
    GarminActivityFileFormat,
    GarminConnectClient,
    GarminConnectCredentials,
)
from nono_sports.garmin_connect.sync import collect_activity_snapshot


class FakeGarminModule:
    class GarminConnectAuthenticationError(Exception):
        pass

    class GarminConnectConnectionError(Exception):
        pass

    class GarminConnectTooManyRequestsError(Exception):
        pass

    class Garmin:
        instances = []
        fail_login = False

        class ActivityDownloadFormat:
            ORIGINAL = "original"
            TCX = "tcx"
            GPX = "gpx"
            KML = "kml"
            CSV = "csv"

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.login_tokenstore = None
            self.download_calls = []
            FakeGarminModule.Garmin.instances.append(self)

        def login(self, tokenstore):
            self.login_tokenstore = tokenstore
            if self.fail_login:
                raise FakeGarminModule.GarminConnectAuthenticationError()

        def get_activities(self, start=0, limit=20, activitytype=None):
            return [
                {
                    "activityId": 123,
                    "start": start,
                    "limit": limit,
                    "activitytype": activitytype,
                }
            ]

        def get_activity(self, activity_id):
            return {"activityId": activity_id}

        def get_activity_details(self, activity_id, maxchart=2000, maxpoly=4000):
            return {
                "activityId": activity_id,
                "maxchart": maxchart,
                "maxpoly": maxpoly,
            }

        def get_activity_splits(self, activity_id):
            return {"activityId": activity_id, "lapDTOs": []}

        def get_activity_typed_splits(self, activity_id):
            return {"activityId": activity_id, "splits": []}

        def get_activity_split_summaries(self, activity_id):
            return {"activityId": activity_id, "splitSummaries": []}

        def get_activity_weather(self, activity_id):
            return {"activityId": activity_id, "weather": "clear"}

        def download_activity(self, activity_id, dl_fmt):
            self.download_calls.append((activity_id, dl_fmt))
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(
                    f"{activity_id}_ACTIVITY.fit",
                    b"\x0e\x20\x00\x00\x00\x00\x00\x00.FIT\x00\x00",
                )
            return buffer.getvalue()


def setup_function() -> None:
    FakeGarminModule.Garmin.instances = []
    FakeGarminModule.Garmin.fail_login = False


def test_client_logs_in_from_tokenstore(tmp_path) -> None:
    client = GarminConnectClient.from_tokenstore(
        tmp_path / "tokenstore",
        garmin_module=FakeGarminModule,
    )

    assert client.list_activities(limit=1)[0]["activityId"] == 123
    assert FakeGarminModule.Garmin.instances[0].login_tokenstore == str(
        tmp_path / "tokenstore"
    )


def test_client_translates_tokenstore_login_failure(tmp_path) -> None:
    FakeGarminModule.Garmin.fail_login = True

    with pytest.raises(AuthenticationError):
        GarminConnectClient.from_tokenstore(
            tmp_path / "tokenstore",
            garmin_module=FakeGarminModule,
        )


def test_client_logs_in_from_credentials(tmp_path) -> None:
    client = GarminConnectClient.from_credentials(
        credentials=GarminConnectCredentials("user@example.test", "secret"),
        tokenstore=tmp_path / "tokenstore",
        prompt_mfa=lambda: "123456",
        garmin_module=FakeGarminModule,
    )

    assert client.get_activity("123") == {"activityId": "123"}
    assert FakeGarminModule.Garmin.instances[0].kwargs["email"] == "user@example.test"


def test_client_downloads_fit_as_original_format() -> None:
    api = FakeGarminModule.Garmin()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)

    payload = client.download_activity_file("123", GarminActivityFileFormat.FIT)

    assert zipfile.is_zipfile(io.BytesIO(payload))
    assert api.download_calls == [("123", "original")]


def test_collect_activity_snapshot_reads_expected_blocks() -> None:
    api = FakeGarminModule.Garmin()
    client = GarminConnectClient(api, garmin_module=FakeGarminModule)

    snapshot = collect_activity_snapshot(client, "123")

    assert snapshot.activity_id == "123"
    assert snapshot.activity == {"activityId": "123"}
    assert snapshot.details["maxchart"] == 2000
    assert snapshot.splits == {"activityId": "123", "lapDTOs": []}
    assert snapshot.typed_splits == {"activityId": "123", "splits": []}
    assert snapshot.split_summaries == {"activityId": "123", "splitSummaries": []}
    assert snapshot.weather == {"activityId": "123", "weather": "clear"}
    assert zipfile.is_zipfile(io.BytesIO(snapshot.fit))


def test_ensure_garmin_tokenstore_creates_private_directory(tmp_path) -> None:
    path = ensure_garmin_tokenstore(tmp_path / "tokenstore")

    assert path == tmp_path / "tokenstore"
    assert path.is_dir()
    assert path.stat().st_mode & 0o777 == 0o700
