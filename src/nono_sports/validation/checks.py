"""Offline data validation checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from nono_sports.core.paths import STRAVA_V1_DIRECTORIES, strava_path
from nono_sports.storage.raw_store import MANIFEST_FILENAME

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class ValidationFinding:
    severity: Severity
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationSummary:
    generated_at: str
    data_root: str
    status: Literal["pass", "warning", "fail"]
    counts: dict[str, int]
    findings: tuple[ValidationFinding, ...]


def validate_strava_data(
    data_root: Path,
    *,
    generated_at: datetime | None = None,
) -> ValidationSummary:
    checked_at = (generated_at or datetime.now(UTC)).astimezone(UTC)
    findings: list[ValidationFinding] = []
    counts: dict[str, int] = {}

    _check_directories(data_root, findings)

    raw_root = strava_path(data_root, "raw")
    normalized_root = strava_path(data_root, "normalizado")
    consolidated_root = data_root / "20_consolidado"

    activity_listing = _read_json(raw_root / "activities" / "activities.json", findings)
    listed_activities = (
        len(activity_listing) if isinstance(activity_listing, list) else 0
    )
    counts["raw_listed_activities"] = listed_activities

    counts["raw_activity_details"] = _count_json_files(
        raw_root / "activities",
        exclude={"activities.json"},
    )
    counts["raw_activity_streams"] = _count_json_files(raw_root / "streams")
    counts["raw_activity_laps"] = _count_json_files(raw_root / "laps")
    counts["raw_errors"] = _count_json_files(raw_root / "errors")
    counts["raw_manifest_entries"] = _count_jsonl(
        raw_root / MANIFEST_FILENAME,
        findings,
    )

    sync_state = _read_json(
        raw_root.parent / "logs" / "activity_sync_state.json",
        findings,
    )
    _check_sync_state(sync_state, counts, findings)

    counts["normalized_athletes"] = _count_jsonl(
        normalized_root / "athletes.jsonl",
        findings,
    )
    counts["normalized_activities"] = _count_jsonl(
        normalized_root / "activities.jsonl",
        findings,
    )
    counts["normalized_streams"] = _count_jsonl(
        normalized_root / "streams.jsonl",
        findings,
    )
    counts["consolidated_activities"] = _count_jsonl(
        consolidated_root / "activities.jsonl",
        findings,
    )
    counts["consolidated_activity_sources"] = _count_jsonl(
        consolidated_root / "activity_sources.jsonl",
        findings,
    )
    counts["consolidated_streams_index"] = _count_jsonl(
        consolidated_root / "streams_index.jsonl",
        findings,
    )
    consolidated_state = _read_json(consolidated_root / "state.json", findings)

    _check_expected_counts(counts, findings, consolidated_state)

    return ValidationSummary(
        generated_at=checked_at.isoformat(),
        data_root=str(data_root),
        status=_status(findings),
        counts=counts,
        findings=tuple(findings),
    )


def _check_directories(data_root: Path, findings: list[ValidationFinding]) -> None:
    missing = [
        directory
        for directory in STRAVA_V1_DIRECTORIES
        if not (data_root / directory).is_dir()
    ]
    if missing:
        findings.append(
            ValidationFinding(
                severity="error",
                code="directories.missing",
                message="Faltan directorios esperados de la estructura Strava v1.",
                details={"missing": missing},
            )
        )


def _check_sync_state(
    sync_state: Any,
    counts: dict[str, int],
    findings: list[ValidationFinding],
) -> None:
    if not isinstance(sync_state, dict):
        return

    activities = sync_state.get("activities", {})
    if not isinstance(activities, dict):
        findings.append(
            ValidationFinding(
                severity="error",
                code="state.activities_invalid",
                message="El estado de sincronización no contiene actividades válidas.",
            )
        )
        return

    entries = [entry for entry in activities.values() if isinstance(entry, dict)]
    counts["state_tracked_activities"] = len(entries)
    counts["state_completed_activities"] = sum(
        "completed_at" in item for item in entries
    )
    counts["state_detail_activities"] = sum("detail" in item for item in entries)
    counts["state_stream_activities"] = sum("streams" in item for item in entries)
    counts["state_lap_activities"] = sum("laps" in item for item in entries)
    counts["state_segment_checked_activities"] = sum(
        item.get("segments_checked") is True for item in entries
    )
    counts["state_recoverable_errors"] = sum(
        key.endswith("_error") for item in entries for key in item
    )
    runs = sync_state.get("runs", [])
    counts["state_sync_runs"] = len(runs) if isinstance(runs, list) else 0

    stopped_reasons = [
        run.get("stopped_reason")
        for run in runs
        if isinstance(run, dict) and run.get("stopped_reason")
    ]
    if stopped_reasons:
        findings.append(
            ValidationFinding(
                severity="warning",
                code="state.last_run_stopped",
                message=(
                    "Hay ejecuciones pausadas antes de completar la descarga; "
                    "normalmente basta con reanudar cuando haya cuota."
                ),
                details={"last_stopped_reason": stopped_reasons[-1]},
            )
        )


def _check_expected_counts(
    counts: dict[str, int],
    findings: list[ValidationFinding],
    consolidated_state: Any,
) -> None:
    listed = counts.get("raw_listed_activities", 0)
    raw_details = counts.get("raw_activity_details", 0)
    if listed > raw_details:
        findings.append(
            ValidationFinding(
                severity="warning",
                code="raw.activities_incomplete",
                message=(
                    "No todas las actividades listadas tienen detalle raw descargado."
                ),
                details={"listed": listed, "raw_details": raw_details},
            )
        )

    _warn_if_less(
        counts,
        findings,
        left_key="raw_activity_streams",
        right_key="raw_activity_details",
        code="raw.streams_incomplete",
        message="Hay actividades con detalle raw pero sin streams raw.",
    )
    _warn_if_less(
        counts,
        findings,
        left_key="raw_activity_laps",
        right_key="raw_activity_details",
        code="raw.laps_incomplete",
        message="Hay actividades con detalle raw pero sin laps raw.",
    )

    if counts.get("raw_errors", 0) > 0 or counts.get("state_recoverable_errors", 0) > 0:
        findings.append(
            ValidationFinding(
                severity="warning",
                code="raw.recoverable_errors",
                message="Existen errores recuperables registrados durante la descarga.",
                details={
                    "raw_error_files": counts.get("raw_errors", 0),
                    "state_errors": counts.get("state_recoverable_errors", 0),
                },
            )
        )

    completed = counts.get("state_completed_activities", 0)
    tracked = counts.get("state_tracked_activities", 0)
    if tracked > completed:
        findings.append(
            ValidationFinding(
                severity="warning",
                code="state.activities_pending_completion",
                message=(
                    "Hay actividades en estado de sincronización sin marca de "
                    "completado."
                ),
                details={"tracked": tracked, "completed": completed},
            )
        )

    segments_checked = counts.get("state_segment_checked_activities", 0)
    details = counts.get("state_detail_activities", 0)
    if details > segments_checked:
        findings.append(
            ValidationFinding(
                severity="warning",
                code="state.segments_pending",
                message=(
                    "Hay actividades con detalle descargado pendientes de revisar "
                    "segmentos."
                ),
                details={"details": details, "segments_checked": segments_checked},
            )
        )

    _error_if_mismatch(
        counts,
        findings,
        left_key="normalized_activities",
        right_key="raw_activity_details",
        code="normalized.activities_mismatch",
        message=(
            "Las actividades normalizadas no cuadran con los detalles raw disponibles."
        ),
    )
    _error_if_mismatch(
        counts,
        findings,
        left_key="normalized_streams",
        right_key="raw_activity_streams",
        code="normalized.streams_mismatch",
        message="Los streams normalizados no cuadran con los streams raw disponibles.",
    )
    _check_consolidated_counts(counts, findings, consolidated_state)


def _check_consolidated_counts(
    counts: dict[str, int],
    findings: list[ValidationFinding],
    consolidated_state: Any,
) -> None:
    strategy = (
        consolidated_state.get("strategy")
        if isinstance(consolidated_state, dict)
        else None
    )
    if strategy != "multi_source_initial":
        _error_if_mismatch(
            counts,
            findings,
            left_key="consolidated_activities",
            right_key="normalized_activities",
            code="consolidated.activities_mismatch",
            message="Las actividades consolidadas no cuadran con las normalizadas.",
        )
        _error_if_mismatch(
            counts,
            findings,
            left_key="consolidated_activity_sources",
            right_key="consolidated_activities",
            code="consolidated.sources_mismatch",
            message="Los enlaces fuente no cuadran con las actividades consolidadas.",
        )
        _error_if_mismatch(
            counts,
            findings,
            left_key="consolidated_streams_index",
            right_key="normalized_streams",
            code="consolidated.streams_mismatch",
            message=(
                "El índice consolidado de streams no cuadra con los streams "
                "normalizados."
            ),
        )
        return

    if counts.get("consolidated_activities", 0) > counts.get(
        "consolidated_activity_sources",
        0,
    ):
        findings.append(
            ValidationFinding(
                severity="error",
                code="consolidated.sources_missing",
                message=(
                    "Hay actividades consolidadas sin enlace a fuente normalizada."
                ),
                details={
                    "consolidated_activities": counts.get(
                        "consolidated_activities",
                        0,
                    ),
                    "consolidated_activity_sources": counts.get(
                        "consolidated_activity_sources",
                        0,
                    ),
                },
            )
        )


def _warn_if_less(
    counts: dict[str, int],
    findings: list[ValidationFinding],
    *,
    left_key: str,
    right_key: str,
    code: str,
    message: str,
) -> None:
    if counts.get(left_key, 0) < counts.get(right_key, 0):
        findings.append(
            ValidationFinding(
                severity="warning",
                code=code,
                message=message,
                details={
                    left_key: counts.get(left_key, 0),
                    right_key: counts.get(right_key, 0),
                },
            )
        )


def _error_if_mismatch(
    counts: dict[str, int],
    findings: list[ValidationFinding],
    *,
    left_key: str,
    right_key: str,
    code: str,
    message: str,
) -> None:
    if counts.get(left_key, 0) != counts.get(right_key, 0):
        findings.append(
            ValidationFinding(
                severity="error",
                code=code,
                message=message,
                details={
                    left_key: counts.get(left_key, 0),
                    right_key: counts.get(right_key, 0),
                },
            )
        )


def _read_json(path: Path, findings: list[ValidationFinding]) -> Any | None:
    if not path.exists():
        findings.append(
            ValidationFinding(
                severity="error",
                code="file.missing",
                message="Falta un fichero esperado.",
                details={"path": str(path)},
            )
        )
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        findings.append(
            ValidationFinding(
                severity="error",
                code="file.invalid_json",
                message="Un fichero JSON no se puede leer correctamente.",
                details={"path": str(path), "error": str(error)},
            )
        )
        return None


def _count_json_files(path: Path, *, exclude: set[str] | None = None) -> int:
    if not path.exists():
        return 0
    excluded = exclude or set()
    return sum(
        item.is_file() and item.suffix == ".json" and item.name not in excluded
        for item in path.iterdir()
    )


def _count_jsonl(path: Path, findings: list[ValidationFinding]) -> int:
    if not path.exists():
        findings.append(
            ValidationFinding(
                severity="error",
                code="file.missing",
                message="Falta un fichero JSONL esperado.",
                details={"path": str(path)},
            )
        )
        return 0

    count = 0
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as error:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="file.invalid_jsonl",
                    message="Un fichero JSONL contiene una línea inválida.",
                    details={
                        "path": str(path),
                        "line": line_number,
                        "error": str(error),
                    },
                )
            )
            continue
        count += 1
    return count


def _status(findings: list[ValidationFinding]) -> Literal["pass", "warning", "fail"]:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "warning"
    return "pass"
