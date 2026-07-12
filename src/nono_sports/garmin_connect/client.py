"""Read-only Garmin Connect adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from nono_sports.core.errors import AuthenticationError, ConfigurationError


class GarminActivityFileFormat(str, Enum):
    """Downloadable Garmin activity file formats."""

    FIT = "fit"
    TCX = "tcx"
    GPX = "gpx"
    KML = "kml"
    CSV = "csv"


@dataclass(frozen=True)
class GarminConnectCredentials:
    email: str
    password: str


class GarminConnectClient:
    """Small read-only wrapper around ``python-garminconnect``."""

    def __init__(self, api: Any, garmin_module: Any | None = None) -> None:
        self._api = api
        self._garmin_module = garmin_module or load_garminconnect_module()

    @classmethod
    def from_tokenstore(
        cls,
        tokenstore: Path,
        garmin_module: Any | None = None,
    ) -> "GarminConnectClient":
        module = garmin_module or load_garminconnect_module()
        api = module.Garmin()
        try:
            api.login(str(tokenstore.expanduser()))
        except garmin_exceptions(module) as error:
            raise AuthenticationError(
                f"Could not log in to Garmin Connect using tokenstore: {tokenstore}"
            ) from error
        return cls(api, module)

    @classmethod
    def from_credentials(
        cls,
        credentials: GarminConnectCredentials,
        tokenstore: Path,
        prompt_mfa: Any,
        garmin_module: Any | None = None,
    ) -> "GarminConnectClient":
        module = garmin_module or load_garminconnect_module()
        api = module.Garmin(
            email=credentials.email,
            password=credentials.password,
            prompt_mfa=prompt_mfa,
        )
        try:
            api.login(str(tokenstore.expanduser()))
        except garmin_exceptions(module) as error:
            raise AuthenticationError("Could not log in to Garmin Connect") from error
        return cls(api, module)

    def list_activities(
        self,
        start: int = 0,
        limit: int = 20,
        activity_type: str | None = None,
    ) -> Any:
        return self._api.get_activities(
            start=start,
            limit=limit,
            activitytype=activity_type,
        )

    def get_activity(self, activity_id: str | int) -> dict[str, Any]:
        return self._api.get_activity(str(activity_id))

    def get_activity_details(
        self,
        activity_id: str | int,
        maxchart: int = 2000,
        maxpoly: int = 4000,
    ) -> dict[str, Any]:
        return self._api.get_activity_details(
            str(activity_id),
            maxchart=maxchart,
            maxpoly=maxpoly,
        )

    def get_activity_splits(self, activity_id: str | int) -> dict[str, Any]:
        return self._api.get_activity_splits(str(activity_id))

    def get_activity_typed_splits(self, activity_id: str | int) -> dict[str, Any]:
        return self._api.get_activity_typed_splits(str(activity_id))

    def get_activity_split_summaries(self, activity_id: str | int) -> dict[str, Any]:
        return self._api.get_activity_split_summaries(str(activity_id))

    def get_activity_weather(self, activity_id: str | int) -> dict[str, Any]:
        return self._api.get_activity_weather(str(activity_id))

    def get_weigh_ins(self, start_date: str, end_date: str) -> dict[str, Any]:
        return self._api.get_weigh_ins(start_date, end_date)

    def get_body_composition(
        self,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        return self._api.get_body_composition(start_date, end_date)

    def download_activity_file(
        self,
        activity_id: str | int,
        file_format: GarminActivityFileFormat = GarminActivityFileFormat.FIT,
    ) -> bytes:
        download_format = self._download_format(file_format)
        return self._api.download_activity(str(activity_id), download_format)

    def _download_format(self, file_format: GarminActivityFileFormat) -> Any:
        formats = self._garmin_module.Garmin.ActivityDownloadFormat
        mapping = {
            GarminActivityFileFormat.FIT: formats.ORIGINAL,
            GarminActivityFileFormat.TCX: formats.TCX,
            GarminActivityFileFormat.GPX: formats.GPX,
            GarminActivityFileFormat.KML: formats.KML,
            GarminActivityFileFormat.CSV: formats.CSV,
        }
        return mapping[file_format]


def load_garminconnect_module() -> Any:
    try:
        import garminconnect
    except ImportError as error:
        raise ConfigurationError(
            "Missing optional Garmin dependency. Install it with: "
            "./.venv/bin/python -m pip install -e '.[garmin]'"
        ) from error
    return garminconnect


def garmin_exceptions(garmin_module: Any) -> tuple[type[BaseException], ...]:
    return (
        garmin_module.GarminConnectAuthenticationError,
        garmin_module.GarminConnectConnectionError,
        garmin_module.GarminConnectTooManyRequestsError,
    )
