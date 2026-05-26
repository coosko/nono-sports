"""Strava activity normalization."""

from __future__ import annotations

from typing import Any

from nono_sports.domain.activity import (
    NormalizedActivity,
    NormalizedLap,
    NormalizedSegmentReference,
)
from nono_sports.domain.source import SourceReference

SCHEMA_VERSION = "nono.normalized_activity.v1"
SOURCE = "strava"

SPORT_MAP = {
    "Ride": ("cycling", "road_cycling", "endurance_distance"),
    "MountainBikeRide": ("cycling", "mountain_biking", "endurance_distance"),
    "GravelRide": ("cycling", "gravel_cycling", "endurance_distance"),
    "VirtualRide": ("cycling", "indoor_cycling", "endurance_distance"),
    "EBikeRide": ("cycling", "e_bike", "endurance_distance"),
    "Run": ("running", "road_running", "endurance_distance"),
    "TrailRun": ("running", "trail_running", "endurance_distance"),
    "Walk": ("walking_hiking", "walking", "endurance_distance"),
    "Hike": ("walking_hiking", "hiking", "endurance_distance"),
    "Workout": ("fitness", "general_workout", "strength_skill_or_mixed"),
    "WeightTraining": ("fitness", "strength_training", "strength_skill_or_mixed"),
    "Crossfit": ("fitness", "crossfit", "strength_skill_or_mixed"),
    "Yoga": ("fitness", "yoga", "mobility"),
}


def normalize_strava_activity(
    activity: dict[str, Any],
    *,
    source_reference: SourceReference,
    stream_reference: SourceReference | None = None,
    laps_reference: SourceReference | None = None,
    gear_payload: dict[str, Any] | None = None,
    gear_reference: SourceReference | None = None,
    segment_payloads: list[tuple[dict[str, Any], SourceReference]] | None = None,
) -> NormalizedActivity:
    activity_id = _required_id(activity, "activity")
    sport_type = str(activity.get("sport_type") or activity.get("type") or "Unknown")
    source_links = [source_reference]
    if stream_reference is not None:
        source_links.append(stream_reference)
    if laps_reference is not None:
        source_links.append(laps_reference)
    if gear_reference is not None:
        source_links.append(gear_reference)
    segments = _segments(segment_payloads or [], source_links)
    return NormalizedActivity(
        schema_version=SCHEMA_VERSION,
        activity_uid=f"{SOURCE}:activity:{activity_id}",
        source=SOURCE,
        source_activity_id=activity_id,
        athlete_uid=_athlete_uid(activity),
        title=_optional_str(activity.get("name")),
        description=_optional_str(activity.get("description")),
        sport=_sport(sport_type, activity.get("type")),
        start={
            "start_at_utc": activity.get("start_date"),
            "start_at_local": activity.get("start_date_local"),
            "timezone": activity.get("timezone"),
            "utc_offset_s": _number(activity.get("utc_offset")),
        },
        duration={
            "moving_time_s": _int(activity.get("moving_time")),
            "elapsed_time_s": _int(activity.get("elapsed_time")),
        },
        distance={
            "distance_m": _number(activity.get("distance")),
        },
        elevation={
            "gain_m": _number(activity.get("total_elevation_gain")),
            "high_m": _number(activity.get("elev_high")),
            "low_m": _number(activity.get("elev_low")),
        },
        energy={
            "calories_kcal": _number(activity.get("calories")),
            "kilojoules": _number(activity.get("kilojoules")),
        },
        metrics=_metrics(activity),
        location=_location(activity),
        gear=_gear(activity, gear_payload, gear_reference),
        flags=_flags(activity),
        completeness={
            "has_detail": True,
            "has_streams": stream_reference is not None,
            "has_laps": laps_reference is not None,
            "has_gear": gear_reference is not None,
            "has_segments": bool(segments),
            "has_zones": False,
        },
        laps=[
            _lap(activity_id, lap)
            for lap in activity.get("laps", [])
            if isinstance(lap, dict)
        ],
        segments=segments,
        stream_uid=f"{SOURCE}:stream:{activity_id}" if stream_reference else None,
        source_reference=source_reference,
        source_links=source_links,
        external_ids={
            "strava_upload_id": activity.get("upload_id_str")
            or _optional_str(activity.get("upload_id")),
            "external_id": activity.get("external_id"),
        },
        sport_specific={
            "workout_type": activity.get("workout_type"),
            "perceived_exertion": activity.get("perceived_exertion"),
            "prefer_perceived_exertion": activity.get("prefer_perceived_exertion"),
            "available_zones": activity.get("available_zones"),
            "device_name": activity.get("device_name"),
            "map": activity.get("map") if isinstance(activity.get("map"), dict) else {},
        },
    )


def _required_id(payload: dict[str, Any], label: str) -> str:
    value = payload.get("id")
    if value is None:
        raise ValueError(f"Missing Strava {label} id.")
    return str(value)


def _athlete_uid(activity: dict[str, Any]) -> str | None:
    athlete = activity.get("athlete")
    if isinstance(athlete, dict) and athlete.get("id") is not None:
        return f"{SOURCE}:athlete:{athlete['id']}"
    return None


def _sport(sport_type: str, legacy_type: object) -> dict[str, Any]:
    family, discipline, movement_context = SPORT_MAP.get(
        sport_type,
        ("other", _snake_case(sport_type), "unknown"),
    )
    return {
        "family": family,
        "discipline": discipline,
        "movement_context": movement_context,
        "source_type": sport_type,
        "source_legacy_type": legacy_type,
    }


def _metrics(activity: dict[str, Any]) -> dict[str, Any]:
    return {
        "average_speed_mps": _number(activity.get("average_speed")),
        "max_speed_mps": _number(activity.get("max_speed")),
        "average_heartrate_bpm": _number(activity.get("average_heartrate")),
        "max_heartrate_bpm": _number(activity.get("max_heartrate")),
        "average_cadence": _number(activity.get("average_cadence")),
        "average_watts": _number(activity.get("average_watts")),
        "average_temp_c": _number(activity.get("average_temp")),
    }


def _location(activity: dict[str, Any]) -> dict[str, Any]:
    return {
        "start_latlng": activity.get("start_latlng"),
        "end_latlng": activity.get("end_latlng"),
        "city": activity.get("location_city"),
        "state": activity.get("location_state"),
        "country": activity.get("location_country"),
    }


def _gear(
    activity: dict[str, Any],
    gear_payload: dict[str, Any] | None,
    gear_reference: SourceReference | None,
) -> dict[str, Any]:
    return {
        "source_gear_id": activity.get("gear_id"),
        "name": gear_payload.get("name") if gear_payload else None,
        "brand_name": gear_payload.get("brand_name") if gear_payload else None,
        "model_name": gear_payload.get("model_name") if gear_payload else None,
        "raw_path": gear_reference.raw_path if gear_reference else None,
    }


def _flags(activity: dict[str, Any]) -> dict[str, Any]:
    return {
        "commute": _bool(activity.get("commute")),
        "trainer": _bool(activity.get("trainer")),
        "manual": _bool(activity.get("manual")),
        "private": _bool(activity.get("private")),
        "flagged": _bool(activity.get("flagged")),
        "device_watts": _bool(activity.get("device_watts")),
        "has_heartrate": _bool(activity.get("has_heartrate")),
        "visibility": activity.get("visibility"),
    }


def _lap(activity_id: str, payload: dict[str, Any]) -> NormalizedLap:
    source_lap_id = _optional_str(payload.get("id"))
    index = _int(payload.get("lap_index") or payload.get("split"))
    return NormalizedLap(
        lap_uid=f"{SOURCE}:activity:{activity_id}:lap:{index or source_lap_id}",
        source_lap_id=source_lap_id,
        index=index,
        name=_optional_str(payload.get("name")),
        start_at_utc=_optional_str(payload.get("start_date")),
        start_at_local=_optional_str(payload.get("start_date_local")),
        distance_m=_number(payload.get("distance")),
        moving_time_s=_int(payload.get("moving_time")),
        elapsed_time_s=_int(payload.get("elapsed_time")),
        elevation_gain_m=_number(payload.get("total_elevation_gain")),
        metrics={
            "average_speed_mps": _number(payload.get("average_speed")),
            "max_speed_mps": _number(payload.get("max_speed")),
            "average_heartrate_bpm": _number(payload.get("average_heartrate")),
            "max_heartrate_bpm": _number(payload.get("max_heartrate")),
            "average_cadence": _number(payload.get("average_cadence")),
            "average_watts": _number(payload.get("average_watts")),
        },
    )


def _segments(
    segment_payloads: list[tuple[dict[str, Any], SourceReference]],
    source_links: list[SourceReference],
) -> list[NormalizedSegmentReference]:
    segments = []
    for payload, reference in segment_payloads:
        segment_id = _required_id(payload, "segment")
        source_links.append(reference)
        segments.append(
            NormalizedSegmentReference(
                segment_uid=f"{SOURCE}:segment:{segment_id}",
                source_segment_id=segment_id,
                name=_optional_str(payload.get("name")),
                distance_m=_number(payload.get("distance")),
                elevation_gain_m=_number(payload.get("total_elevation_gain")),
                source_reference=reference,
            )
        )
    return segments


def _number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _snake_case(value: str) -> str:
    normalized = []
    for char in value:
        if char.isupper() and normalized:
            normalized.append("_")
        normalized.append(char.lower())
    return "".join(normalized) or "unknown"
