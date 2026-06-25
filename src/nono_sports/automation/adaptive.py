"""Adaptive systemd scheduling for controlled sync backfill."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from typing import Protocol

from nono_sports.core.errors import NonoSportsError
from nono_sports.strava.rate_limits import RateLimitSnapshot
from nono_sports.validation.checks import ValidationSummary

PENDING_DOWNLOAD_FINDING_CODES = {
    "raw.activities_incomplete",
    "state.activities_pending_completion",
    "state.segments_pending",
}


class AdaptiveScheduleError(NonoSportsError):
    """Raised when an adaptive sync cannot be scheduled."""


class SystemdRunner(Protocol):
    def __call__(
        self,
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and return its completed process."""


@dataclass(frozen=True)
class AdaptiveScheduleDecision:
    should_schedule: bool
    reason: str


def build_adaptive_schedule_decision(
    *,
    summary: ValidationSummary,
    rate_limit: RateLimitSnapshot | None,
    configured_daily_cap: int | None,
    reserve_requests: int,
    skip_fetch: bool,
) -> AdaptiveScheduleDecision:
    if skip_fetch:
        return AdaptiveScheduleDecision(
            should_schedule=False,
            reason="skip-fetch active; no adaptive reschedule needed.",
        )
    if summary.status == "fail":
        return AdaptiveScheduleDecision(
            should_schedule=False,
            reason="validation failed; not scheduling another sync.",
        )
    if not has_pending_download_work(summary):
        return AdaptiveScheduleDecision(
            should_schedule=False,
            reason="no pending Strava download work detected.",
        )
    if rate_limit is None:
        return AdaptiveScheduleDecision(
            should_schedule=False,
            reason="no Strava rate-limit snapshot available.",
        )
    if not has_daily_budget_room(
        rate_limit,
        configured_daily_cap=configured_daily_cap,
        reserve_requests=reserve_requests,
    ):
        return AdaptiveScheduleDecision(
            should_schedule=False,
            reason="daily Strava read budget is too close to the limit.",
        )
    return AdaptiveScheduleDecision(
        should_schedule=True,
        reason="pending work remains and daily Strava read budget has room.",
    )


def has_pending_download_work(summary: ValidationSummary) -> bool:
    return any(
        finding.code in PENDING_DOWNLOAD_FINDING_CODES
        for finding in summary.findings
    )


def has_daily_budget_room(
    snapshot: RateLimitSnapshot,
    *,
    configured_daily_cap: int | None,
    reserve_requests: int,
) -> bool:
    usage = snapshot.read_usage or snapshot.overall_usage
    if usage is None:
        return False
    limit = snapshot.read_limit or snapshot.overall_limit
    reported_daily_limit = limit.daily if limit is not None else None
    candidates = [
        value
        for value in (configured_daily_cap, reported_daily_limit)
        if value is not None
    ]
    if not candidates:
        return False
    threshold = max(0, min(candidates) - max(0, reserve_requests))
    return usage.daily < threshold


def build_systemd_run_command(
    *,
    command: tuple[str, ...],
    delay_minutes: int,
    unit_name: str,
    unit_suffix: str | None = None,
) -> list[str]:
    scheduled_unit_name = unit_name
    if unit_suffix is not None:
        scheduled_unit_name = f"{unit_name}-{unit_suffix}"
    return [
        "systemd-run",
        "--user",
        f"--unit={scheduled_unit_name}",
        f"--on-active={delay_minutes}m",
        "--collect",
        *command,
    ]


def schedule_with_systemd(
    *,
    command: tuple[str, ...],
    delay_minutes: int,
    unit_name: str,
    runner: SystemdRunner = subprocess.run,
) -> None:
    result = runner(
        build_systemd_run_command(
            command=command,
            delay_minutes=delay_minutes,
            unit_name=unit_name,
            unit_suffix=uuid.uuid4().hex,
        ),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise AdaptiveScheduleError(
            f"Could not schedule next sync with systemd-run: {detail}"
        )
