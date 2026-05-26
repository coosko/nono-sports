"""Command-line interface for nono-sports."""

from __future__ import annotations

import argparse

from nono_sports.auth.strava_oauth import (
    build_authorization_url,
    exchange_code_for_token,
)
from nono_sports.auth.token_store import StravaTokenStore
from nono_sports.consolidation.single_source import build_single_source_consolidated
from nono_sports.core.config import (
    ProjectConfig,
    load_config,
    load_strava_client_config,
)
from nono_sports.core.paths import ensure_strava_v1_directories, strava_token_path
from nono_sports.normalization.strava_dataset import normalize_strava_dataset
from nono_sports.storage.raw_store import RawStore
from nono_sports.storage.state_store import StateStore
from nono_sports.strava.client import StravaClient, StravaRateLimitBudget
from nono_sports.strava.endpoints import StravaEndpoints, download_profile_context
from nono_sports.strava.rate_limits import RateLimitSnapshot
from nono_sports.strava.sync import ActivitySyncResult, sync_activities_raw
from nono_sports.validation.checks import ValidationSummary, validate_strava_data
from nono_sports.validation.reports import write_validation_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nono-sports")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("build-consolidated")

    strava_parser = subparsers.add_parser("strava")
    strava_subparsers = strava_parser.add_subparsers(dest="strava_command")
    strava_subparsers.add_parser("prepare-dirs")
    auth_parser = strava_subparsers.add_parser("auth")
    auth_parser.add_argument("--code", default=None)
    auth_parser.add_argument("--state", default=None)
    context_parser = strava_subparsers.add_parser("fetch-context")
    context_parser.add_argument("--skip-club-details", action="store_true")
    context_parser.add_argument("--skip-route-exports", action="store_true")
    context_parser.add_argument("--skip-route-details", action="store_true")
    context_parser.add_argument("--skip-route-streams", action="store_true")
    context_parser.add_argument("--skip-segment-details", action="store_true")
    context_parser.add_argument("--skip-segment-streams", action="store_true")
    context_parser.add_argument("--skip-starred-segments", action="store_true")
    context_parser.add_argument("--skip-gear-details", action="store_true")
    strava_subparsers.add_parser("normalize")
    strava_subparsers.add_parser("validate")
    activities_parser = strava_subparsers.add_parser("fetch-activities")
    _add_activity_fetch_options(activities_parser)
    sync_parser = strava_subparsers.add_parser("sync")
    sync_parser.add_argument("--skip-fetch", action="store_true")
    _add_activity_fetch_options(sync_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "strava" and args.strava_command == "prepare-dirs":
        config = load_config()
        created_paths = ensure_strava_v1_directories(config.data_root)
        print(
            f"Prepared {len(created_paths)} Strava v1 directories "
            f"in {config.data_root}"
        )
        return 0

    if args.command == "build-consolidated":
        project_config = load_config()
        ensure_strava_v1_directories(project_config.data_root)
        result = build_single_source_consolidated(project_config.data_root)
        print(
            "Built consolidated dataset: "
            f"{result.activities} activities, "
            f"{result.activity_sources} activity source links, "
            f"{result.streams_index} stream index records, "
            f"{len(result.written)} files written."
        )
        print(f"Consolidated root: {result.consolidated_root}")
        return 0

    if args.command == "strava" and args.strava_command == "auth":
        strava_config = load_strava_client_config()
        token_path = strava_token_path()

        if not args.code:
            print(build_authorization_url(strava_config, state=args.state))
            print("After approving access in Strava, rerun with --code <CODE>.")
            return 0

        token = exchange_code_for_token(strava_config, args.code)
        StravaTokenStore(token_path).save(token)
        print(f"Strava tokens saved in {token_path}")
        print(f"Granted scopes: {', '.join(token.scope)}")
        return 0

    if args.command == "strava" and args.strava_command == "fetch-context":
        project_config = load_config()
        ensure_strava_v1_directories(project_config.data_root)
        strava_config = load_strava_client_config()
        token_store = StravaTokenStore(strava_token_path())
        raw_store = RawStore(project_config.data_root)
        with StravaClient(strava_config, token_store) as client:
            result = download_profile_context(
                StravaEndpoints(client),
                raw_store,
                include_club_details=not args.skip_club_details,
                include_route_details=not args.skip_route_details,
                include_route_exports=not args.skip_route_exports,
                include_route_streams=not args.skip_route_streams,
                include_starred_segments=not args.skip_starred_segments,
                include_segment_details=not args.skip_segment_details,
                include_segment_streams=not args.skip_segment_streams,
                include_gear_details=not args.skip_gear_details,
            )
        print(
            "Downloaded Strava profile/context raw files: "
            f"{len(result.written)} written, "
            f"{len(result.recoverable_errors)} recoverable errors."
        )
        print(f"Raw root: {raw_store.raw_root}")
        return 0

    if args.command == "strava" and args.strava_command == "fetch-activities":
        project_config = load_config()
        ensure_strava_v1_directories(project_config.data_root)
        result, raw_store, last_rate_limit = _run_strava_fetch_activities(
            args,
            project_config,
        )
        _print_fetch_activities_result(result, raw_store, last_rate_limit)
        return 0

    if args.command == "strava" and args.strava_command == "normalize":
        project_config = load_config()
        ensure_strava_v1_directories(project_config.data_root)
        result = normalize_strava_dataset(project_config.data_root)
        print(
            "Normalized Strava raw data: "
            f"{result.athletes} athletes, "
            f"{result.activities} activities, "
            f"{result.streams} streams, "
            f"{len(result.written)} files written."
        )
        print(f"Normalized root: {result.normalized_root}")
        return 0

    if args.command == "strava" and args.strava_command == "validate":
        project_config = load_config()
        ensure_strava_v1_directories(project_config.data_root)
        summary = _run_validation(project_config)
        return 1 if summary.status == "fail" else 0

    if args.command == "strava" and args.strava_command == "sync":
        project_config = load_config()
        ensure_strava_v1_directories(project_config.data_root)
        if args.skip_fetch:
            print("Skipped Strava fetch. Running offline pipeline only.")
        else:
            result, raw_store, last_rate_limit = _run_strava_fetch_activities(
                args,
                project_config,
            )
            _print_fetch_activities_result(result, raw_store, last_rate_limit)
        normalize_result = normalize_strava_dataset(project_config.data_root)
        print(
            "Normalized Strava raw data: "
            f"{normalize_result.athletes} athletes, "
            f"{normalize_result.activities} activities, "
            f"{normalize_result.streams} streams, "
            f"{len(normalize_result.written)} files written."
        )
        consolidated_result = build_single_source_consolidated(
            project_config.data_root,
        )
        print(
            "Built consolidated dataset: "
            f"{consolidated_result.activities} activities, "
            f"{consolidated_result.activity_sources} activity source links, "
            f"{consolidated_result.streams_index} stream index records, "
            f"{len(consolidated_result.written)} files written."
        )
        summary = _run_validation(project_config)
        return 1 if summary.status == "fail" else 0

    parser.print_help()
    return 0


def _add_activity_fetch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--after", type=int, default=None)
    parser.add_argument("--before", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-activities", type=int, default=None)
    parser.add_argument("--skip-gear", action="store_true")
    parser.add_argument("--skip-laps", action="store_true")
    parser.add_argument("--skip-segments", action="store_true")
    parser.add_argument("--skip-segment-streams", action="store_true")
    parser.add_argument("--skip-streams", action="store_true")
    parser.add_argument("--include-zones", action="store_true")
    parser.add_argument(
        "--max-read-requests-15min",
        "--max-read-requests-15-min",
        dest="max_read_requests_15min",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--max-read-requests-daily",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--rate-limit-reserve",
        type=int,
        default=5,
    )


def _run_strava_fetch_activities(
    args: argparse.Namespace,
    project_config: ProjectConfig,
) -> tuple[ActivitySyncResult, RawStore, RateLimitSnapshot | None]:
    strava_config = load_strava_client_config()
    token_store = StravaTokenStore(strava_token_path())
    raw_store = RawStore(project_config.data_root)
    state_store = StateStore(project_config.data_root)
    rate_limit_budget = StravaRateLimitBudget(
        max_read_fifteen_minutes=args.max_read_requests_15min,
        max_read_daily=args.max_read_requests_daily,
        reserve_requests=args.rate_limit_reserve,
    )
    with StravaClient(
        strava_config,
        token_store,
        rate_limit_budget=rate_limit_budget,
    ) as client:
        result = sync_activities_raw(
            StravaEndpoints(client),
            raw_store,
            state_store,
            after=args.after,
            before=args.before,
            force=args.force,
            max_activities=args.max_activities,
            include_gear=not args.skip_gear,
            include_laps=not args.skip_laps,
            include_segments=not args.skip_segments,
            include_segment_streams=not args.skip_segment_streams,
            include_streams=not args.skip_streams,
            include_zones=args.include_zones,
        )
        return result, raw_store, client.last_rate_limit


def _print_fetch_activities_result(
    result: ActivitySyncResult,
    raw_store: RawStore,
    last_rate_limit: RateLimitSnapshot | None,
) -> None:
    print(
        "Downloaded Strava activities raw files: "
        f"{result.listed_activities} listed, "
        f"{result.processed_activities} processed, "
        f"{result.skipped_activities} skipped, "
        f"{len(result.written)} written, "
        f"{len(result.recoverable_errors)} recoverable errors."
    )
    print(f"Raw root: {raw_store.raw_root}")
    print(f"State: {result.state_path}")
    if result.stopped_reason:
        print(f"Stopped early: {result.stopped_reason}")
    rate_limit_line = _format_rate_limit(last_rate_limit)
    if rate_limit_line is not None:
        print(rate_limit_line)


def _run_validation(project_config: ProjectConfig) -> ValidationSummary:
    summary = validate_strava_data(project_config.data_root)
    report_path = write_validation_report(project_config.data_root, summary)
    severities = _count_findings_by_severity(summary)
    print(
        "Validated Strava dataset: "
        f"status={summary.status}, "
        f"errors={severities['error']}, "
        f"warnings={severities['warning']}, "
        f"info={severities['info']}."
    )
    print(f"Report: {report_path}")
    return summary


def _format_rate_limit(snapshot: RateLimitSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    usage = snapshot.read_usage or snapshot.overall_usage
    limit = snapshot.read_limit or snapshot.overall_limit
    if usage is None or limit is None:
        return None
    return (
        "Rate limit read usage: "
        f"{usage.fifteen_minutes}/{limit.fifteen_minutes} 15min, "
        f"{usage.daily}/{limit.daily} daily"
    )


def _count_findings_by_severity(summary: ValidationSummary) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in summary.findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts
