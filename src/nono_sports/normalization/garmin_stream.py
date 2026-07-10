"""Garmin FIT stream normalization."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nono_sports.domain.source import SourceReference
from nono_sports.domain.stream import NormalizedStream
from nono_sports.formats.track_xml import TrackPoint

SCHEMA_VERSION = "nono.normalized_stream.v1"
SOURCE = "garmin_connect"

STREAM_FIELDS = {
    "time": ("timestamp", "s"),
    "distance": ("distance", "m"),
    "altitude": ("enhanced_altitude", "m"),
    "velocity_smooth": ("enhanced_speed", "m/s"),
    "heartrate": ("heart_rate", "bpm"),
    "cadence": ("cadence", "rpm"),
    "temperature": ("temperature", "degC"),
}


def normalize_garmin_stream(
    activity_id: int | str,
    fit_messages: dict[str, list[dict[str, Any]]],
    *,
    source_reference: SourceReference,
) -> NormalizedStream | None:
    records = fit_messages.get("record")
    if not records:
        return None
    streams = {
        stream_name: _stream_from_records(records, field_name, unit)
        for stream_name, (field_name, unit) in STREAM_FIELDS.items()
    }
    hrv_values = _hrv_values(fit_messages.get("hrv", []))
    if hrv_values:
        streams["hrv"] = {"unit": "s", "values": hrv_values}

    source_activity_id = str(activity_id)
    return NormalizedStream(
        schema_version=SCHEMA_VERSION,
        stream_uid=f"{SOURCE}:stream:{source_activity_id}",
        activity_uid=f"{SOURCE}:activity:{source_activity_id}",
        source=SOURCE,
        source_activity_id=source_activity_id,
        streams=streams,
        samples={
            stream_type: _sample_count(stream_data.get("values"))
            for stream_type, stream_data in streams.items()
        },
        source_reference=source_reference,
    )


def normalize_garmin_track_stream(
    activity_id: int | str,
    points: list[TrackPoint],
    *,
    source_reference: SourceReference,
) -> NormalizedStream | None:
    if not points:
        return None
    streams = {
        "time": {"unit": "s", "values": _elapsed_seconds_from_track(points)},
        "latlng": {
            "unit": "deg",
            "values": [
                [point.lat, point.lng]
                if point.lat is not None and point.lng is not None
                else None
                for point in points
            ],
        },
        "distance": {
            "unit": "m",
            "values": [point.distance_m for point in points],
        },
        "altitude": {
            "unit": "m",
            "values": [point.altitude_m for point in points],
        },
        "heartrate": {
            "unit": "bpm",
            "values": [point.heartrate_bpm for point in points],
        },
        "cadence": {
            "unit": "rpm",
            "values": [point.cadence for point in points],
        },
    }
    source_activity_id = str(activity_id)
    return NormalizedStream(
        schema_version=SCHEMA_VERSION,
        stream_uid=f"{SOURCE}:stream:{source_activity_id}",
        activity_uid=f"{SOURCE}:activity:{source_activity_id}",
        source=SOURCE,
        source_activity_id=source_activity_id,
        streams=streams,
        samples={
            stream_type: _sample_count(stream_data.get("values"))
            for stream_type, stream_data in streams.items()
        },
        source_reference=source_reference,
    )


def _stream_from_records(
    records: list[dict[str, Any]],
    field_name: str,
    unit: str,
) -> dict[str, Any]:
    if field_name == "timestamp":
        values = _elapsed_seconds(records)
    else:
        values = [record.get(field_name) for record in records]
    return {"unit": unit, "values": values}


def _elapsed_seconds_from_track(points: list[TrackPoint]) -> list[float | None]:
    records = [{"timestamp": point.timestamp} for point in points]
    return _elapsed_seconds(records)


def _elapsed_seconds(records: list[dict[str, Any]]) -> list[float | None]:
    timestamps = [_parse_datetime(record.get("timestamp")) for record in records]
    first = next((timestamp for timestamp in timestamps if timestamp is not None), None)
    if first is None:
        return [None for _ in records]
    return [
        round((timestamp - first).total_seconds(), 3) if timestamp is not None else None
        for timestamp in timestamps
    ]


def _hrv_values(messages: list[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    for message in messages:
        times = message.get("time")
        if not isinstance(times, list):
            continue
        values.extend(value for value in times if isinstance(value, int | float))
    return values


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sample_count(values: Any) -> int:
    if isinstance(values, list):
        return len(values)
    return 0
