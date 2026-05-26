"""Strava athlete normalization."""

from __future__ import annotations

from typing import Any

from nono_sports.domain.athlete import NormalizedAthlete
from nono_sports.domain.source import SourceReference

SCHEMA_VERSION = "nono.normalized_athlete.v1"
SOURCE = "strava"


def normalize_strava_athlete(
    profile: dict[str, Any],
    *,
    source_reference: SourceReference,
) -> NormalizedAthlete:
    athlete_id = _required_id(profile, "athlete")
    bikes = profile.get("bikes")
    shoes = profile.get("shoes")
    return NormalizedAthlete(
        schema_version=SCHEMA_VERSION,
        athlete_uid=f"{SOURCE}:athlete:{athlete_id}",
        source=SOURCE,
        source_athlete_id=athlete_id,
        display={
            "username": profile.get("username"),
            "firstname": profile.get("firstname"),
            "lastname": profile.get("lastname"),
        },
        profile={
            "sex": profile.get("sex"),
            "city": profile.get("city"),
            "state": profile.get("state"),
            "country": profile.get("country"),
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
        },
        physiology={
            "weight_kg": _number(profile.get("weight")),
            "ftp_watts": _number(profile.get("ftp")),
        },
        preferences={
            "measurement_preference": profile.get("measurement_preference"),
            "date_preference": profile.get("date_preference"),
        },
        gear={
            "bikes": bikes if isinstance(bikes, list) else [],
            "shoes": shoes if isinstance(shoes, list) else [],
        },
        source_reference=source_reference,
        source_specific={
            "athlete_type": profile.get("athlete_type"),
            "premium": profile.get("premium"),
            "summit": profile.get("summit"),
        },
    )


def _required_id(payload: dict[str, Any], label: str) -> str:
    value = payload.get("id")
    if value is None:
        raise ValueError(f"Missing Strava {label} id.")
    return str(value)


def _number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None
