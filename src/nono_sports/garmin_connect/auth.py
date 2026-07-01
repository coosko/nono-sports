"""Garmin Connect authentication helpers."""

from __future__ import annotations

import os
from getpass import getpass
from pathlib import Path

from nono_sports.core.paths import garmin_connect_tokenstore_path
from nono_sports.garmin_connect.client import (
    GarminConnectClient,
    GarminConnectCredentials,
)

ENV_GARMIN_EMAIL = "GARMIN_EMAIL"
ENV_GARMIN_PASSWORD = "GARMIN_PASSWORD"  # noqa: S105


def ensure_garmin_tokenstore(tokenstore: Path | None = None) -> Path:
    path = (tokenstore or garmin_connect_tokenstore_path()).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def login_from_tokenstore(tokenstore: Path | None = None) -> GarminConnectClient:
    path = ensure_garmin_tokenstore(tokenstore)
    return GarminConnectClient.from_tokenstore(path)


def login_interactive(tokenstore: Path | None = None) -> GarminConnectClient:
    path = ensure_garmin_tokenstore(tokenstore)
    credentials = GarminConnectCredentials(
        email=os.getenv(ENV_GARMIN_EMAIL) or input("Garmin email: ").strip(),
        password=os.getenv(ENV_GARMIN_PASSWORD) or getpass("Garmin password: "),
    )
    return GarminConnectClient.from_credentials(
        credentials=credentials,
        tokenstore=path,
        prompt_mfa=lambda: input("Garmin MFA code: ").strip(),
    )
