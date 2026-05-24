"""Data-root and project path resolution."""

from __future__ import annotations

from pathlib import Path

XDG_STATE_HOME_ENV = "XDG_STATE_HOME"
APP_STATE_DIR = "nono-sports"

STRAVA_V1_DIRECTORIES = [
    "10_fuentes/strava/raw/athlete",
    "10_fuentes/strava/raw/activities",
    "10_fuentes/strava/raw/streams",
    "10_fuentes/strava/raw/zones",
    "10_fuentes/strava/raw/gear",
    "10_fuentes/strava/raw/routes",
    "10_fuentes/strava/normalizado",
    "10_fuentes/strava/logs",
    "20_consolidado",
    "30_analisis/informes",
    "30_analisis/planes",
    "30_analisis/seguimiento",
    "30_analisis/graficas",
    "90_archivo",
]


def normalize_filesystem_root(root: str) -> Path:
    if len(root) >= 2 and root[1] == ":":
        drive = root[0].lower()
        rest = root[2:].replace("\\", "/").lstrip("/")
        wsl_mount = Path("/mnt") / drive / Path(rest)
        if wsl_mount.exists():
            return wsl_mount
    return Path(root).expanduser()


def strava_path(data_root: Path, *parts: str) -> Path:
    return data_root.joinpath("10_fuentes", "strava", *parts)


def app_state_dir() -> Path:
    import os

    state_home = os.getenv(XDG_STATE_HOME_ENV)
    if state_home:
        return Path(state_home).expanduser() / APP_STATE_DIR
    return Path.home() / ".local" / "state" / APP_STATE_DIR


def strava_token_path() -> Path:
    return app_state_dir() / "strava_tokens.json"


def ensure_strava_v1_directories(data_root: Path) -> list[Path]:
    created_paths: list[Path] = []
    for directory in STRAVA_V1_DIRECTORIES:
        path = data_root / directory
        path.mkdir(parents=True, exist_ok=True)
        created_paths.append(path)
    return created_paths
