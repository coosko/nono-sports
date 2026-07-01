"""Garmin Connect diagnostics."""

from __future__ import annotations

import importlib.metadata

from nono_sports.core.doctor import DoctorCheck


def check_garminconnect_distribution() -> DoctorCheck:
    try:
        version = importlib.metadata.version("garminconnect")
    except importlib.metadata.PackageNotFoundError:
        return DoctorCheck(
            "Garmin Connect library",
            "warning",
            "garminconnect is not installed",
        )
    if version != "0.3.6":
        return DoctorCheck(
            "Garmin Connect library",
            "warning",
            f"garminconnect {version} is installed; expected 0.3.6",
        )
    return DoctorCheck(
        "Garmin Connect library",
        "ok",
        "garminconnect 0.3.6 is installed",
    )
