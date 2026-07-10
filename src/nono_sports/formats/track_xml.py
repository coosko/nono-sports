"""Minimal GPX/TCX track parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET


@dataclass(frozen=True)
class TrackPoint:
    timestamp: str | None = None
    distance_m: float | None = None
    altitude_m: float | None = None
    lat: float | None = None
    lng: float | None = None
    heartrate_bpm: int | None = None
    cadence: int | None = None


def parse_gpx_track_points(path: Path) -> list[TrackPoint]:
    root = ET.parse(path).getroot()
    points: list[TrackPoint] = []
    for point in root.iter():
        if _local_name(point.tag) != "trkpt":
            continue
        points.append(
            TrackPoint(
                timestamp=_child_text(point, "time"),
                altitude_m=_float(_child_text(point, "ele")),
                lat=_float(point.attrib.get("lat")),
                lng=_float(point.attrib.get("lon")),
                heartrate_bpm=_int(_descendant_text(point, "hr")),
                cadence=_int(_descendant_text(point, "cad")),
            )
        )
    return points


def parse_tcx_track_points(path: Path) -> list[TrackPoint]:
    root = ET.parse(path).getroot()
    points: list[TrackPoint] = []
    for point in root.iter():
        if _local_name(point.tag) != "Trackpoint":
            continue
        position = _child(point, "Position")
        points.append(
            TrackPoint(
                timestamp=_child_text(point, "Time"),
                distance_m=_float(_child_text(point, "DistanceMeters")),
                altitude_m=_float(_child_text(point, "AltitudeMeters")),
                lat=(
                    _float(_child_text(position, "LatitudeDegrees"))
                    if position is not None
                    else None
                ),
                lng=(
                    _float(_child_text(position, "LongitudeDegrees"))
                    if position is not None
                    else None
                ),
                heartrate_bpm=_int(_descendant_text(point, "Value")),
                cadence=_int(_child_text(point, "Cadence")),
            )
        )
    return points


def _child(element: ET.Element | None, local_name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _child_text(element: ET.Element | None, local_name: str) -> str | None:
    child = _child(element, local_name)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _descendant_text(element: ET.Element, local_name: str) -> str | None:
    for descendant in element.iter():
        if _local_name(descendant.tag) == local_name and descendant.text is not None:
            return descendant.text.strip()
    return None


def _local_name(tag: Any) -> str:
    text = str(tag)
    return text.rsplit("}", maxsplit=1)[-1]


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None
