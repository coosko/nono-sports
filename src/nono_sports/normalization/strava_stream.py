"""Strava stream normalization."""

from __future__ import annotations

from typing import Any

from nono_sports.domain.source import SourceReference
from nono_sports.domain.stream import NormalizedStream

SCHEMA_VERSION = "nono.normalized_stream.v1"
SOURCE = "strava"

STREAM_UNITS = {
    "time": "s",
    "distance": "m",
    "latlng": "deg",
    "altitude": "m",
    "velocity_smooth": "m/s",
    "heartrate": "bpm",
    "cadence": "rpm",
    "watts": "W",
    "temp": "degC",
    "moving": "bool",
    "grade_smooth": "percent",
}


def normalize_strava_stream(
    activity_id: int | str,
    streams: dict[str, Any],
    *,
    source_reference: SourceReference,
) -> NormalizedStream:
    source_activity_id = str(activity_id)
    normalized_streams = {
        stream_type: _normalize_stream_values(stream_type, payload)
        for stream_type, payload in sorted(streams.items())
    }
    return NormalizedStream(
        schema_version=SCHEMA_VERSION,
        stream_uid=f"{SOURCE}:stream:{source_activity_id}",
        activity_uid=f"{SOURCE}:activity:{source_activity_id}",
        source=SOURCE,
        source_activity_id=source_activity_id,
        streams=normalized_streams,
        samples={
            stream_type: _sample_count(stream_data.get("values"))
            for stream_type, stream_data in normalized_streams.items()
        },
        source_reference=source_reference,
    )


def _normalize_stream_values(stream_type: str, payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        values = payload.get("data")
        return {
            "unit": STREAM_UNITS.get(stream_type),
            "series_type": payload.get("series_type"),
            "resolution": payload.get("resolution"),
            "original_size": payload.get("original_size"),
            "values": values,
        }
    return {
        "unit": STREAM_UNITS.get(stream_type),
        "values": payload,
    }


def _sample_count(values: Any) -> int:
    if isinstance(values, list):
        return len(values)
    return 0
