from pathlib import Path

from nono_sports.core.paths import (
    GARMIN_CONNECT_DIRECTORIES,
    STRAVA_V1_DIRECTORIES,
    app_state_dir,
    ensure_garmin_connect_directories,
    ensure_strava_v1_directories,
    garmin_connect_path,
    garmin_connect_state_dir,
    garmin_connect_tokenstore_path,
    normalize_filesystem_root,
    strava_path,
    strava_token_path,
)


def test_normalize_filesystem_root_expands_user_home() -> None:
    assert normalize_filesystem_root("~").is_absolute()


def test_normalize_filesystem_root_keeps_unmounted_windows_path() -> None:
    assert normalize_filesystem_root("H:\\Data") == Path("H:\\Data")


def test_strava_path_builds_path_under_source_root(tmp_path) -> None:
    assert strava_path(tmp_path, "raw", "activities") == (
        tmp_path / "10_fuentes" / "strava" / "raw" / "activities"
    )


def test_garmin_connect_path_builds_path_under_source_root(tmp_path) -> None:
    assert garmin_connect_path(tmp_path, "raw", "activities") == (
        tmp_path / "10_fuentes" / "garmin_connect" / "raw" / "activities"
    )


def test_ensure_strava_v1_directories_creates_expected_structure(tmp_path) -> None:
    created_paths = ensure_strava_v1_directories(tmp_path)

    assert len(created_paths) == len(STRAVA_V1_DIRECTORIES)
    for directory in STRAVA_V1_DIRECTORIES:
        assert (tmp_path / directory).is_dir()


def test_ensure_garmin_connect_directories_creates_expected_structure(
    tmp_path,
) -> None:
    created_paths = ensure_garmin_connect_directories(tmp_path)

    assert len(created_paths) == len(GARMIN_CONNECT_DIRECTORIES)
    for directory in GARMIN_CONNECT_DIRECTORIES:
        assert (tmp_path / directory).is_dir()


def test_strava_v1_directories_do_not_include_auth_secrets() -> None:
    assert "00_referencia/auth" not in STRAVA_V1_DIRECTORIES


def test_garmin_connect_directories_do_not_include_auth_secrets() -> None:
    assert all(
        ".local/state" not in directory for directory in GARMIN_CONNECT_DIRECTORIES
    )
    assert all(".config" not in directory for directory in GARMIN_CONNECT_DIRECTORIES)


def test_app_state_dir_uses_xdg_state_home(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert app_state_dir() == tmp_path / "nono-sports"


def test_strava_token_path_uses_app_state_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert strava_token_path() == tmp_path / "nono-sports" / "strava_tokens.json"


def test_garmin_connect_state_paths_use_app_state_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert garmin_connect_state_dir() == tmp_path / "nono-sports" / "garmin_connect"
    assert garmin_connect_tokenstore_path() == (
        tmp_path / "nono-sports" / "garmin_connect" / "tokenstore"
    )
