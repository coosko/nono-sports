from pathlib import Path

import pytest

from nono_sports.core.config import (
    ENV_DATA_ROOT,
    ENV_LOG_LEVEL,
    ENV_STRAVA_CLIENT_ID,
    ENV_STRAVA_CLIENT_SECRET,
    ENV_STRAVA_REDIRECT_URI,
    ENV_XDG_CONFIG_HOME,
    ProjectConfig,
    StravaClientConfig,
    load_config,
    load_strava_client_config,
    user_config_env_path,
)
from nono_sports.core.errors import ConfigurationError


def test_load_config_reads_data_root_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(ENV_DATA_ROOT, str(tmp_path))

    config = load_config()

    assert config == ProjectConfig(data_root=tmp_path, log_level="INFO")


def test_load_config_raises_when_data_root_is_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(ENV_DATA_ROOT, raising=False)

    with pytest.raises(ConfigurationError, match=ENV_DATA_ROOT):
        load_config(tmp_path / ".env")


def test_load_config_rejects_source_directory_as_data_root(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(ENV_DATA_ROOT, str(tmp_path / "10_fuentes"))

    with pytest.raises(ConfigurationError, match="not to 10_fuentes itself"):
        load_config()


def test_load_config_reads_env_file(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(ENV_DATA_ROOT, raising=False)
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"{ENV_DATA_ROOT}={tmp_path}\nLOG_LEVEL=DEBUG\n")

    config = load_config(env_file)

    assert config == ProjectConfig(data_root=Path(tmp_path), log_level="DEBUG")


def test_load_config_reads_xdg_user_config_env(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(ENV_DATA_ROOT, raising=False)
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
    monkeypatch.setenv(ENV_XDG_CONFIG_HOME, str(tmp_path / "config"))
    env_path = user_config_env_path()
    env_path.parent.mkdir(parents=True)
    env_path.write_text(f"{ENV_DATA_ROOT}={tmp_path}\nLOG_LEVEL=DEBUG\n")

    config = load_config()

    assert config == ProjectConfig(data_root=Path(tmp_path), log_level="DEBUG")


def test_load_strava_client_config_reads_required_values(monkeypatch) -> None:
    monkeypatch.setenv(ENV_STRAVA_CLIENT_ID, "123")
    monkeypatch.setenv(ENV_STRAVA_CLIENT_SECRET, "secret")
    monkeypatch.setenv(ENV_STRAVA_REDIRECT_URI, "http://localhost/callback")

    config = load_strava_client_config()

    assert config == StravaClientConfig(
        client_id="123",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
    )


def test_load_strava_client_config_raises_when_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(ENV_STRAVA_CLIENT_ID, raising=False)
    monkeypatch.delenv(ENV_STRAVA_CLIENT_SECRET, raising=False)

    with pytest.raises(ConfigurationError, match=ENV_STRAVA_CLIENT_ID):
        load_strava_client_config(tmp_path / ".env")


def test_load_strava_client_config_rejects_placeholders(monkeypatch) -> None:
    monkeypatch.setenv(ENV_STRAVA_CLIENT_ID, "your_strava_client_id")
    monkeypatch.setenv(ENV_STRAVA_CLIENT_SECRET, "your_strava_client_secret")

    with pytest.raises(ConfigurationError, match="Replace placeholder"):
        load_strava_client_config()
