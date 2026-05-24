from pathlib import Path

from nono_sports.core.paths import (
    STRAVA_V1_DIRECTORIES,
    app_state_dir,
    ensure_strava_v1_directories,
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


def test_ensure_strava_v1_directories_creates_expected_structure(tmp_path) -> None:
    created_paths = ensure_strava_v1_directories(tmp_path)

    assert len(created_paths) == len(STRAVA_V1_DIRECTORIES)
    for directory in STRAVA_V1_DIRECTORIES:
        assert (tmp_path / directory).is_dir()


def test_strava_v1_directories_do_not_include_auth_secrets() -> None:
    assert "00_referencia/auth" not in STRAVA_V1_DIRECTORIES


def test_app_state_dir_uses_xdg_state_home(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert app_state_dir() == tmp_path / "nono-sports"


def test_strava_token_path_uses_app_state_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert strava_token_path() == tmp_path / "nono-sports" / "strava_tokens.json"
