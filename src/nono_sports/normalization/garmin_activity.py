"""Garmin Connect activity normalization."""

from __future__ import annotations

from typing import Any

from nono_sports.domain.activity import NormalizedActivity, NormalizedLap
from nono_sports.domain.source import SourceReference

SCHEMA_VERSION = "nono.normalized_activity.v1"
SOURCE = "garmin_connect"

SPORT_MAP = {
    "road_biking": ("cycling", "road_cycling", "endurance_distance"),
    "cycling": ("cycling", "cycling", "endurance_distance"),
    "mountain_biking": ("cycling", "mountain_biking", "endurance_distance"),
    "gravel_cycling": ("cycling", "gravel_cycling", "endurance_distance"),
    "running": ("running", "road_running", "endurance_distance"),
    "trail_running": ("running", "trail_running", "endurance_distance"),
    "walking": ("walking_hiking", "walking", "endurance_distance"),
    "hiking": ("walking_hiking", "hiking", "endurance_distance"),
    "strength_training": ("fitness", "strength_training", "strength_skill_or_mixed"),
}


def normalize_garmin_activity(
    activity: dict[str, Any],
    *,
    source_reference: SourceReference,
    details_reference: SourceReference | None = None,
    fit_reference: SourceReference | None = None,
    decoded_fit_reference: SourceReference | None = None,
    splits_reference: SourceReference | None = None,
    typed_splits_reference: SourceReference | None = None,
    weather_reference: SourceReference | None = None,
    fit_messages: dict[str, list[dict[str, Any]]] | None = None,
    splits_payload: Any | None = None,
    typed_splits_payload: Any | None = None,
    weather_payload: Any | None = None,
) -> NormalizedActivity:
    activity_id = _required_activity_id(activity)
    summary = _dict(activity.get("summaryDTO"))
    metadata = _dict(activity.get("metadataDTO"))
    activity_type = _dict(activity.get("activityTypeDTO"))
    source_links = [
        reference
        for reference in (
            source_reference,
            details_reference,
            fit_reference,
            decoded_fit_reference,
            splits_reference,
            typed_splits_reference,
            weather_reference,
        )
        if reference is not None
    ]
    laps = _laps_from_fit(activity_id, fit_messages or {})
    return NormalizedActivity(
        schema_version=SCHEMA_VERSION,
        activity_uid=f"{SOURCE}:activity:{activity_id}",
        source=SOURCE,
        source_activity_id=activity_id,
        athlete_uid=_athlete_uid(metadata),
        title=_optional_str(activity.get("activityName")),
        description=None,
        sport=_sport(_optional_str(activity_type.get("typeKey"))),
        start={
            "start_at_utc": _garmin_time(summary.get("startTimeGMT"), utc=True),
            "start_at_local": _garmin_time(summary.get("startTimeLocal"), utc=False),
            "timezone": _dict(activity.get("timeZoneUnitDTO")).get("timeZone"),
            "utc_offset_s": None,
        },
        duration={
            "moving_time_s": _int(summary.get("duration")),
            "elapsed_time_s": _int(summary.get("elapsedDuration")),
        },
        distance={"distance_m": _number(summary.get("distance"))},
        elevation={
            "gain_m": _number(summary.get("elevationGain")),
            "loss_m": _number(summary.get("elevationLoss")),
            "high_m": _number(summary.get("maxElevation")),
            "low_m": _number(summary.get("minElevation")),
            "average_m": _number(summary.get("avgElevation")),
        },
        energy={"calories_kcal": _number(summary.get("calories"))},
        metrics=_metrics(summary),
        location=_location(activity, summary),
        gear=_gear(metadata),
        flags=_flags(activity, metadata),
        completeness={
            "has_detail": details_reference is not None,
            "has_streams": decoded_fit_reference is not None
            and bool((fit_messages or {}).get("record")),
            "has_laps": bool(laps),
            "has_splits": splits_reference is not None,
            "has_typed_splits": typed_splits_reference is not None,
            "has_weather": weather_reference is not None,
            "has_fit": fit_reference is not None,
            "has_decoded_fit": decoded_fit_reference is not None,
            "has_segments": False,
            "has_zones": bool((fit_messages or {}).get("time_in_zone")),
        },
        laps=laps,
        segments=[],
        stream_uid=(
            f"{SOURCE}:stream:{activity_id}"
            if decoded_fit_reference is not None and (fit_messages or {}).get("record")
            else None
        ),
        source_reference=source_reference,
        source_links=source_links,
        external_ids={
            "garmin_activity_id": activity_id,
            "garmin_activity_uuid": _dict(activity.get("activityUUID")).get("uuid"),
        },
        sport_specific={
            "location_name": activity.get("locationName"),
            "event_type": _dict(activity.get("eventTypeDTO")).get("typeKey"),
            "file_format": _dict(metadata.get("fileFormat")).get("formatKey"),
            "lap_count": metadata.get("lapCount"),
            "manufacturer": metadata.get("manufacturer"),
            "weather": weather_payload if isinstance(weather_payload, dict) else {},
            "splits_summary": _summarize_payload(splits_payload),
            "typed_splits_summary": _summarize_payload(typed_splits_payload),
        },
    )


def _required_activity_id(activity: dict[str, Any]) -> str:
    value = activity.get("activityId")
    if value is None:
        raise ValueError("Missing Garmin activityId.")
    return str(value)


def _athlete_uid(metadata: dict[str, Any]) -> str | None:
    user_info = _dict(metadata.get("userInfoDto"))
    profile_id = user_info.get("userProfilePk")
    if profile_id is None:
        return None
    return f"{SOURCE}:athlete:{profile_id}"


def _sport(source_type: str | None) -> dict[str, Any]:
    source = source_type or "unknown"
    family, discipline, movement_context = SPORT_MAP.get(
        source,
        ("other", source.replace("-", "_"), "unknown"),
    )
    return {
        "family": family,
        "discipline": discipline,
        "movement_context": movement_context,
        "source_type": source,
    }


def _metrics(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "average_speed_mps": _number(summary.get("averageSpeed")),
        "average_moving_speed_mps": _number(summary.get("averageMovingSpeed")),
        "max_speed_mps": _number(summary.get("maxSpeed")),
        "average_heartrate_bpm": _number(summary.get("averageHR")),
        "max_heartrate_bpm": _number(summary.get("maxHR")),
        "average_cadence": _number(summary.get("averageBikeCadence")),
        "max_cadence": _number(summary.get("maxBikeCadence")),
        "average_temp_c": _number(summary.get("averageTemperature")),
    }


def _location(activity: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "location_name": activity.get("locationName"),
        "start_latlng": _latlng(
            summary.get("startLatitude"),
            summary.get("startLongitude"),
        ),
        "end_latlng": _latlng(
            summary.get("endLatitude"),
            summary.get("endLongitude"),
        ),
    }


def _gear(metadata: dict[str, Any]) -> dict[str, Any]:
    device = _dict(metadata.get("deviceMetaDataDTO"))
    sensors = (
        metadata.get("sensors")
        if isinstance(metadata.get("sensors"), list)
        else []
    )
    return {
        "manufacturer": metadata.get("manufacturer"),
        "device_id": device.get("deviceId"),
        "device_type_pk": device.get("deviceTypePk"),
        "device_version_pk": device.get("deviceVersionPk"),
        "sensors": sensors,
    }


def _flags(activity: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    access = _dict(activity.get("accessControlRuleDTO"))
    return {
        "manual": _bool(metadata.get("manualActivity")),
        "private": access.get("typeKey") == "private",
        "visibility": access.get("typeKey"),
        "favorite": _bool(metadata.get("favorite")),
        "trimmed": _bool(metadata.get("trimmed")),
        "elevation_corrected": _bool(metadata.get("elevationCorrected")),
        "has_heartrate": _bool(metadata.get("hasHrTimeInZones")),
    }


def _laps_from_fit(
    activity_id: str,
    fit_messages: dict[str, list[dict[str, Any]]],
) -> list[NormalizedLap]:
    laps = []
    for index, payload in enumerate(fit_messages.get("lap", []), start=1):
        message_index = _int(payload.get("message_index")) or index - 1
        laps.append(
            NormalizedLap(
                lap_uid=f"{SOURCE}:activity:{activity_id}:lap:{message_index}",
                source_lap_id=str(message_index),
                index=message_index,
                name=None,
                start_at_utc=_optional_str(payload.get("start_time")),
                start_at_local=None,
                distance_m=_number(payload.get("total_distance")),
                moving_time_s=_int(payload.get("total_timer_time")),
                elapsed_time_s=_int(payload.get("total_elapsed_time")),
                elevation_gain_m=_number(payload.get("total_ascent")),
                metrics={
                    "average_speed_mps": _number(payload.get("avg_speed")),
                    "max_speed_mps": _number(payload.get("max_speed")),
                    "average_heartrate_bpm": _number(payload.get("avg_heart_rate")),
                    "max_heartrate_bpm": _number(payload.get("max_heart_rate")),
                    "average_cadence": _number(payload.get("avg_cadence")),
                    "max_cadence": _number(payload.get("max_cadence")),
                    "trigger": payload.get("lap_trigger"),
                },
            )
        )
    return laps


def _garmin_time(value: Any, *, utc: bool) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    cleaned = value[:-2] if value.endswith(".0") else value
    return f"{cleaned}Z" if utc and not cleaned.endswith("Z") else cleaned


def _latlng(lat: Any, lng: Any) -> list[float] | None:
    lat_number = _number(lat)
    lng_number = _number(lng)
    if lat_number is None or lng_number is None:
        return None
    return [lat_number, lng_number]


def _summarize_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"type": "list", "items": len(payload)}
    if isinstance(payload, dict):
        return {"type": "dict", "keys": sorted(payload.keys())}
    return {}


def _number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
