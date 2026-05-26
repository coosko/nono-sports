import subprocess

from nono_sports.automation.adaptive import (
    build_adaptive_schedule_decision,
    build_systemd_run_command,
    has_daily_budget_room,
    schedule_with_systemd,
)
from nono_sports.strava.rate_limits import RateLimitPair, RateLimitSnapshot
from nono_sports.validation.checks import ValidationFinding, ValidationSummary


def test_adaptive_schedule_decision_schedules_when_pending_and_budget_has_room(
) -> None:
    decision = build_adaptive_schedule_decision(
        summary=_summary("raw.activities_incomplete"),
        rate_limit=_rate_limit(daily_usage=500),
        configured_daily_cap=1000,
        reserve_requests=10,
        skip_fetch=False,
    )

    assert decision.should_schedule is True


def test_adaptive_schedule_decision_stops_when_daily_budget_is_near_limit() -> None:
    decision = build_adaptive_schedule_decision(
        summary=_summary("raw.activities_incomplete"),
        rate_limit=_rate_limit(daily_usage=995),
        configured_daily_cap=1000,
        reserve_requests=10,
        skip_fetch=False,
    )

    assert decision.should_schedule is False
    assert "daily" in decision.reason


def test_adaptive_schedule_decision_stops_without_pending_work() -> None:
    decision = build_adaptive_schedule_decision(
        summary=_summary(),
        rate_limit=_rate_limit(daily_usage=500),
        configured_daily_cap=1000,
        reserve_requests=10,
        skip_fetch=False,
    )

    assert decision.should_schedule is False
    assert "no pending" in decision.reason


def test_has_daily_budget_room_uses_minimum_between_cap_and_reported_limit() -> None:
    snapshot = _rate_limit(daily_usage=895, daily_limit=900)

    assert (
        has_daily_budget_room(
            snapshot,
            configured_daily_cap=1000,
            reserve_requests=10,
        )
        is False
    )


def test_build_systemd_run_command_uses_single_transient_unit() -> None:
    command = build_systemd_run_command(
        command=("python", "-m", "nono_sports", "strava", "sync"),
        delay_minutes=20,
        unit_name="nono-sports-strava-sync-adaptive",
    )

    assert command == [
        "systemd-run",
        "--user",
        "--unit=nono-sports-strava-sync-adaptive",
        "--on-active=20m",
        "--collect",
        "python",
        "-m",
        "nono_sports",
        "strava",
        "sync",
    ]


def test_schedule_with_systemd_uses_runner() -> None:
    calls = []

    def runner(command, *, capture_output, text):
        calls.append((command, capture_output, text))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    schedule_with_systemd(
        command=("python", "-m", "nono_sports"),
        delay_minutes=20,
        unit_name="unit",
        runner=runner,
    )

    assert calls == [
        (
            [
                "systemd-run",
                "--user",
                "--unit=unit",
                "--on-active=20m",
                "--collect",
                "python",
                "-m",
                "nono_sports",
            ],
            True,
            True,
        )
    ]


def _summary(*finding_codes: str) -> ValidationSummary:
    return ValidationSummary(
        generated_at="2026-05-26T00:00:00+00:00",
        data_root="/data-root",
        status="warning" if finding_codes else "pass",
        counts={},
        findings=tuple(
            ValidationFinding(
                severity="warning",
                code=code,
                message=code,
            )
            for code in finding_codes
        ),
    )


def _rate_limit(
    *,
    daily_usage: int,
    daily_limit: int = 1000,
) -> RateLimitSnapshot:
    return RateLimitSnapshot(
        overall_limit=None,
        overall_usage=None,
        read_limit=RateLimitPair(fifteen_minutes=100, daily=daily_limit),
        read_usage=RateLimitPair(fifteen_minutes=50, daily=daily_usage),
    )
