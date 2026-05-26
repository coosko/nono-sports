"""Configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from nono_sports.core.errors import ConfigurationError
from nono_sports.core.paths import normalize_filesystem_root

ENV_DATA_ROOT = "NONO_SPORT_DATA_ROOT"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_STRAVA_CLIENT_ID = "STRAVA_CLIENT_ID"
ENV_STRAVA_CLIENT_SECRET = "STRAVA_CLIENT_SECRET"  # noqa: S105
ENV_STRAVA_REDIRECT_URI = "STRAVA_REDIRECT_URI"
ENV_XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
APP_CONFIG_DIR = "nono-sports"
APP_CONFIG_ENV = "env"
DEFAULT_STRAVA_REDIRECT_URI = "http://localhost/exchange_token"


@dataclass(frozen=True)
class ProjectConfig:
    data_root: Path
    log_level: str = "INFO"


@dataclass(frozen=True)
class StravaClientConfig:
    client_id: str
    client_secret: str
    redirect_uri: str = DEFAULT_STRAVA_REDIRECT_URI


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_environment(env_file: Path | None = None) -> None:
    if env_file is not None:
        if env_file.exists():
            load_dotenv(env_file, override=False)
        return

    for env_path in (user_config_env_path(), get_project_root() / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


def user_config_env_path() -> Path:
    config_home = os.getenv(ENV_XDG_CONFIG_HOME)
    if config_home:
        return Path(config_home).expanduser() / APP_CONFIG_DIR / APP_CONFIG_ENV
    return Path.home() / ".config" / APP_CONFIG_DIR / APP_CONFIG_ENV


def load_config(env_file: Path | None = None) -> ProjectConfig:
    load_environment(env_file)
    data_root_value = os.getenv(ENV_DATA_ROOT)
    if not data_root_value:
        raise ConfigurationError(
            f"Missing required environment variable: {ENV_DATA_ROOT}"
        )

    data_root = normalize_filesystem_root(data_root_value)
    if data_root.name == "10_fuentes":
        raise ConfigurationError(
            f"{ENV_DATA_ROOT} must point to the data root that contains "
            "10_fuentes, not to 10_fuentes itself."
        )

    return ProjectConfig(
        data_root=data_root,
        log_level=os.getenv(ENV_LOG_LEVEL, "INFO"),
    )


def load_strava_client_config(env_file: Path | None = None) -> StravaClientConfig:
    load_environment(env_file)
    client_id = os.getenv(ENV_STRAVA_CLIENT_ID)
    client_secret = os.getenv(ENV_STRAVA_CLIENT_SECRET)
    missing_variables = [
        name
        for name, value in (
            (ENV_STRAVA_CLIENT_ID, client_id),
            (ENV_STRAVA_CLIENT_SECRET, client_secret),
        )
        if not value
    ]
    if missing_variables:
        raise ConfigurationError(
            "Missing required Strava environment variables: "
            + ", ".join(missing_variables)
        )
    placeholder_variables = [
        name
        for name, value in (
            (ENV_STRAVA_CLIENT_ID, client_id),
            (ENV_STRAVA_CLIENT_SECRET, client_secret),
        )
        if _is_placeholder(str(value))
    ]
    if placeholder_variables:
        raise ConfigurationError(
            "Replace placeholder Strava environment variables: "
            + ", ".join(placeholder_variables)
        )

    return StravaClientConfig(
        client_id=str(client_id),
        client_secret=str(client_secret),
        redirect_uri=os.getenv(
            ENV_STRAVA_REDIRECT_URI,
            DEFAULT_STRAVA_REDIRECT_URI,
        ),
    )


def _is_placeholder(value: str) -> bool:
    return value.startswith("your_") or value.startswith("<") or value.endswith(">")
