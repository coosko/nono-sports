"""Data-root and project path resolution."""

from __future__ import annotations

from pathlib import Path

XDG_STATE_HOME_ENV = "XDG_STATE_HOME"
APP_STATE_DIR = "nono-sports"

STRAVA_V1_DIRECTORIES = [
    "10_fuentes/strava/raw/athlete",
    "10_fuentes/strava/raw/activities",
    "10_fuentes/strava/raw/clubs",
    "10_fuentes/strava/raw/errors",
    "10_fuentes/strava/raw/streams",
    "10_fuentes/strava/raw/zones",
    "10_fuentes/strava/raw/gear",
    "10_fuentes/strava/raw/laps",
    "10_fuentes/strava/raw/routes",
    "10_fuentes/strava/raw/route_exports/gpx",
    "10_fuentes/strava/raw/route_exports/tcx",
    "10_fuentes/strava/raw/route_streams",
    "10_fuentes/strava/raw/segments",
    "10_fuentes/strava/raw/segment_streams",
    "10_fuentes/strava/normalizado",
    "10_fuentes/strava/logs",
    "20_consolidado",
    "30_analisis/informes",
    "30_analisis/planes",
    "30_analisis/seguimiento",
    "30_analisis/graficas",
    "90_archivo",
]

GARMIN_CONNECT_DIRECTORIES = [
    "10_fuentes/garmin_connect/raw/athlete",
    "10_fuentes/garmin_connect/raw/activities",
    "10_fuentes/garmin_connect/raw/activity_files",
    "10_fuentes/garmin_connect/raw/biometrics",
    "10_fuentes/garmin_connect/raw/fit_decoded",
    "10_fuentes/garmin_connect/raw/splits",
    "10_fuentes/garmin_connect/raw/typed_splits",
    "10_fuentes/garmin_connect/raw/laps",
    "10_fuentes/garmin_connect/raw/weather",
    "10_fuentes/garmin_connect/raw/segment_candidates",
    "10_fuentes/garmin_connect/normalizado",
    "10_fuentes/garmin_connect/logs",
]

MANUAL_DIRECTORIES = [
    "10_fuentes/manual/biometria",
    "10_fuentes/manual/normalizado",
    "10_fuentes/manual/logs",
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


def garmin_connect_path(data_root: Path, *parts: str) -> Path:
    return data_root.joinpath("10_fuentes", "garmin_connect", *parts)


def manual_path(data_root: Path, *parts: str) -> Path:
    return data_root.joinpath("10_fuentes", "manual", *parts)


def app_state_dir() -> Path:
    import os

    state_home = os.getenv(XDG_STATE_HOME_ENV)
    if state_home:
        return Path(state_home).expanduser() / APP_STATE_DIR
    return Path.home() / ".local" / "state" / APP_STATE_DIR


def strava_token_path() -> Path:
    return app_state_dir() / "strava_tokens.json"


def garmin_connect_state_dir() -> Path:
    return app_state_dir() / "garmin_connect"


def garmin_connect_tokenstore_path() -> Path:
    return garmin_connect_state_dir() / "tokenstore"


def ensure_garmin_connect_directories(data_root: Path) -> list[Path]:
    created_paths: list[Path] = []
    for directory in GARMIN_CONNECT_DIRECTORIES:
        path = data_root / directory
        path.mkdir(parents=True, exist_ok=True)
        created_paths.append(path)
    return created_paths


def ensure_manual_directories(data_root: Path) -> list[Path]:
    created_paths: list[Path] = []
    for directory in MANUAL_DIRECTORIES:
        path = data_root / directory
        path.mkdir(parents=True, exist_ok=True)
        created_paths.append(path)
    return created_paths


def ensure_strava_v1_directories(data_root: Path) -> list[Path]:
    created_paths: list[Path] = []
    for directory in STRAVA_V1_DIRECTORIES:
        path = data_root / directory
        path.mkdir(parents=True, exist_ok=True)
        created_paths.append(path)
    return created_paths
