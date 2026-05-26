"""Markdown validation report generation."""

from __future__ import annotations

from pathlib import Path

from nono_sports.validation.checks import ValidationFinding, ValidationSummary

REPORT_FILENAME = "strava_validation_report.md"


def write_validation_report(
    data_root: Path,
    summary: ValidationSummary,
    *,
    filename: str = REPORT_FILENAME,
) -> Path:
    report_dir = data_root / "30_analisis" / "informes"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / filename
    report_path.write_text(render_markdown_report(summary), encoding="utf-8")
    return report_path


def render_markdown_report(summary: ValidationSummary) -> str:
    lines = [
        "# Informe de validación Strava",
        "",
        f"- Generado: `{summary.generated_at}`",
        f"- Data root: `{summary.data_root}`",
        f"- Estado: **{_status_label(summary.status)}**",
        "",
        "## Conteos",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| `{key}` | {value} |"
        for key, value in sorted(summary.counts.items())
    )
    lines.extend(["", "## Hallazgos", ""])
    if summary.findings:
        lines.extend(
            [
                "| Severidad | Código | Mensaje | Detalles |",
                "| --- | --- | --- | --- |",
            ]
        )
        lines.extend(_finding_row(finding) for finding in summary.findings)
    else:
        lines.append("No se han encontrado errores ni avisos.")

    lines.extend(["", "## Siguiente acción recomendada", ""])
    lines.append(_next_action(summary))
    lines.append("")
    return "\n".join(lines)


def _finding_row(finding: ValidationFinding) -> str:
    details = ", ".join(
        f"`{key}`=`{value}`"
        for key, value in sorted(finding.details.items())
    )
    return (
        f"| {_severity_label(finding.severity)} "
        f"| `{finding.code}` "
        f"| {finding.message} "
        f"| {details or '-'} |"
    )


def _status_label(status: str) -> str:
    labels = {
        "pass": "OK",
        "warning": "OK con avisos",
        "fail": "Fallo",
    }
    return labels.get(status, status)


def _severity_label(severity: str) -> str:
    labels = {
        "error": "Error",
        "warning": "Aviso",
        "info": "Info",
    }
    return labels.get(severity, severity)


def _next_action(summary: ValidationSummary) -> str:
    if summary.status == "fail":
        return (
            "Corregir primero los errores marcados como `Error` y volver a ejecutar "
            "`nono-sports strava validate`."
        )
    if summary.status == "warning":
        return (
            "Revisar los avisos. Si se deben a una descarga incompleta o a rate limit, "
            "reanudar la descarga y repetir normalización, consolidación y validación."
        )
    return (
        "El dataset actual es coherente para el alcance descargado. Puede pasar a "
        "revisión manual o consumo por Nono."
    )
