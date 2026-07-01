"""Local diagnostics for Nono Sports environments."""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from nono_sports.core.config import (
    ENV_DATA_ROOT,
    load_environment,
    user_config_env_path,
)
from nono_sports.core.paths import (
    GARMIN_CONNECT_DIRECTORIES,
    STRAVA_V1_DIRECTORIES,
    app_state_dir,
    garmin_connect_tokenstore_path,
    normalize_filesystem_root,
    strava_token_path,
)

DoctorStatus = Literal["ok", "warning", "error"]
DoctorScope = Literal["common", "strava", "garmin"]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: DoctorStatus
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class DoctorReport:
    scope: DoctorScope
    checks: tuple[DoctorCheck, ...]

    @property
    def status(self) -> DoctorStatus:
        statuses = {check.status for check in self.checks}
        if "error" in statuses:
            return "error"
        if "warning" in statuses:
            return "warning"
        return "ok"


def run_common_doctor() -> DoctorReport:
    load_environment()
    checks: list[DoctorCheck] = []
    checks.append(_check_python_version())
    checks.extend(_check_config_env())
    data_root = _configured_data_root()
    checks.extend(_check_data_root(data_root))
    checks.extend(_check_state_dir())
    if data_root is not None:
        checks.extend(_check_obvious_secrets_under_data_root(data_root))
    return DoctorReport(scope="common", checks=tuple(checks))


def run_strava_doctor() -> DoctorReport:
    common = run_common_doctor()
    checks = list(common.checks)
    data_root = _configured_data_root()
    if data_root is not None:
        checks.extend(_check_expected_directories(data_root, STRAVA_V1_DIRECTORIES))
    checks.extend(_check_sensitive_file(strava_token_path(), "Strava token store"))
    return DoctorReport(scope="strava", checks=tuple(checks))


def run_garmin_doctor() -> DoctorReport:
    from nono_sports.garmin_connect.doctor import check_garminconnect_distribution

    common = run_common_doctor()
    checks = list(common.checks)
    data_root = _configured_data_root()
    if data_root is not None:
        checks.extend(
            _check_expected_directories(data_root, GARMIN_CONNECT_DIRECTORIES)
        )
    checks.append(check_garminconnect_distribution())
    checks.extend(
        _check_sensitive_directory(
            garmin_connect_tokenstore_path(),
            "Garmin Connect tokenstore",
        )
    )
    return DoctorReport(scope="garmin", checks=tuple(checks))


def format_doctor_report(report: DoctorReport) -> str:
    lines = [
        f"Nono Sports doctor ({report.scope}): status={report.status}",
    ]
    for check in report.checks:
        path = f" [{check.path}]" if check.path is not None else ""
        lines.append(f"- {check.status.upper()}: {check.name}: {check.message}{path}")
    return "\n".join(lines)


def _check_python_version() -> DoctorCheck:
    version = sys.version_info
    supported = (3, 11) <= (version.major, version.minor) < (3, 15)
    current = f"{version.major}.{version.minor}.{version.micro}"
    if supported:
        return DoctorCheck("python", "ok", f"Python {current} is supported")
    return DoctorCheck(
        "python",
        "error",
        f"Python {current} is outside the supported range >=3.11,<3.15",
    )


def _check_config_env() -> list[DoctorCheck]:
    env_path = user_config_env_path()
    checks = []
    if env_path.exists():
        checks.append(DoctorCheck("config env", "ok", "XDG env file exists", env_path))
        checks.extend(_check_sensitive_file(env_path, "XDG env file"))
    else:
        checks.append(
            DoctorCheck(
                "config env",
                "warning",
                "XDG env file does not exist; environment or local .env may still work",
                env_path,
            )
        )
    return checks


def _configured_data_root() -> Path | None:
    value = os.getenv(ENV_DATA_ROOT)
    if not value:
        return None
    return normalize_filesystem_root(value)


def _check_data_root(data_root: Path | None) -> list[DoctorCheck]:
    if data_root is None:
        return [
            DoctorCheck(
                "data root",
                "error",
                f"Missing required environment variable: {ENV_DATA_ROOT}",
            )
        ]
    if data_root.name == "10_fuentes":
        return [
            DoctorCheck(
                "data root",
                "error",
                f"{ENV_DATA_ROOT} must point to the root that contains 10_fuentes",
                data_root,
            )
        ]
    if not data_root.exists():
        return [
            DoctorCheck("data root", "error", "Data root does not exist", data_root)
        ]
    if not data_root.is_dir():
        return [
            DoctorCheck(
                "data root",
                "error",
                "Data root is not a directory",
                data_root,
            )
        ]
    return [DoctorCheck("data root", "ok", "Data root exists", data_root)]


def _check_state_dir() -> list[DoctorCheck]:
    state_dir = app_state_dir()
    if not state_dir.exists():
        return [
            DoctorCheck(
                "state dir",
                "warning",
                "Application state directory does not exist yet",
                state_dir,
            )
        ]
    if not state_dir.is_dir():
        return [
            DoctorCheck(
                "state dir",
                "error",
                "Application state path exists but is not a directory",
                state_dir,
            )
        ]
    checks = [
        DoctorCheck(
            "state dir",
            "ok",
            "Application state directory exists",
            state_dir,
        )
    ]
    checks.extend(_check_directory_permissions(state_dir, "state dir"))
    return checks


def _check_expected_directories(
    data_root: Path,
    expected_directories: list[str],
) -> list[DoctorCheck]:
    missing = [
        str(data_root / directory)
        for directory in expected_directories
        if not (data_root / directory).is_dir()
    ]
    if not missing:
        return [
            DoctorCheck(
                "source directories",
                "ok",
                f"All {len(expected_directories)} expected directories exist",
            )
        ]
    return [
        DoctorCheck(
            "source directories",
            "warning",
            f"{len(missing)} expected directories are missing",
        )
    ]


def _check_sensitive_file(path: Path, name: str) -> list[DoctorCheck]:
    if not path.exists():
        return [DoctorCheck(name, "warning", "Sensitive file does not exist yet", path)]
    if not path.is_file():
        return [DoctorCheck(name, "error", "Path exists but is not a file", path)]
    checks = [DoctorCheck(name, "ok", "Sensitive file exists", path)]
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        checks.append(
            DoctorCheck(
                f"{name} permissions",
                "warning",
                f"Permissions are {mode:o}; recommended maximum is 600",
                path,
            )
        )
    else:
        checks.append(
            DoctorCheck(
                f"{name} permissions",
                "ok",
                f"Permissions are {mode:o}",
                path,
            )
        )
    return checks


def _check_sensitive_directory(path: Path, name: str) -> list[DoctorCheck]:
    if not path.exists():
        return [
            DoctorCheck(
                name,
                "warning",
                "Sensitive directory does not exist yet",
                path,
            )
        ]
    if not path.is_dir():
        return [DoctorCheck(name, "error", "Path exists but is not a directory", path)]
    checks = [DoctorCheck(name, "ok", "Sensitive directory exists", path)]
    checks.extend(_check_directory_permissions(path, name))
    return checks


def _check_directory_permissions(path: Path, name: str) -> list[DoctorCheck]:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        return [
            DoctorCheck(
                f"{name} permissions",
                "warning",
                f"Permissions are {mode:o}; recommended maximum is 700",
                path,
            )
        ]
    return [
        DoctorCheck(
            f"{name} permissions",
            "ok",
            f"Permissions are {mode:o}",
            path,
        )
    ]


def _check_obvious_secrets_under_data_root(data_root: Path) -> list[DoctorCheck]:
    candidates = [
        data_root / ".env",
        data_root / "env",
        data_root / "00_referencia" / "auth" / "strava_tokens.json",
        data_root / "00_referencia" / "auth" / "garmin_tokens.json",
        data_root / "10_fuentes" / "strava" / "strava_tokens.json",
        data_root / "10_fuentes" / "garmin_connect" / "garmin_tokens.json",
        data_root / "10_fuentes" / "garmin_connect" / "auth_state.json",
    ]
    found = [path for path in candidates if path.exists()]
    if not found:
        return [
            DoctorCheck(
                "secrets in data root",
                "ok",
                "No obvious secret files found under data root",
                data_root,
            )
        ]
    return [
        DoctorCheck(
            "secrets in data root",
            "warning",
            f"Found {len(found)} possible secret file(s) under data root",
            found[0],
        )
    ]
