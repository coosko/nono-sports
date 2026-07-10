"""Command-line interface for nono-sports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nono_sports.auth.strava_oauth import (
    build_authorization_url,
    exchange_code_for_token,
)
from nono_sports.auth.token_store import StravaTokenStore
from nono_sports.automation.adaptive import (
    build_adaptive_schedule_decision,
    schedule_with_systemd,
)
from nono_sports.consolidation.multi_source import build_multi_source_consolidated
from nono_sports.core.config import (
    ProjectConfig,
    load_config,
    load_strava_client_config,
)
from nono_sports.core.doctor import (
    format_doctor_report,
    run_common_doctor,
    run_garmin_doctor,
    run_strava_doctor,
)
from nono_sports.core.file_lock import acquire_file_lock
from nono_sports.core.paths import (
    ensure_garmin_connect_directories,
    ensure_strava_v1_directories,
    garmin_connect_path,
    strava_token_path,
)
from nono_sports.formats.fit import (
    compare_fit_decoders,
    decode_fit_with_fitdecode,
    fit_decoder_comparison_to_dict,
)
from nono_sports.garmin_connect.auth import login_from_tokenstore
from nono_sports.garmin_connect.raw_store import GarminRawStore
from nono_sports.garmin_connect.state_store import GarminStateStore
from nono_sports.garmin_connect.sync import (
    GarminRawSyncResult,
    sync_garmin_activities_raw,
)
from nono_sports.normalization.garmin_dataset import (
    GarminNormalizationResult,
    normalize_garmin_dataset,
)
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
    subparsers.add_parser("doctor")
    subparsers.add_parser("build-consolidated")
    fit_parser = subparsers.add_parser("fit")
    fit_subparsers = fit_parser.add_subparsers(dest="fit_command")
    fit_compare_parser = fit_subparsers.add_parser("compare-decoders")
    fit_compare_parser.add_argument("--path", required=True)
    fit_compare_parser.add_argument("--output", default=None)

    strava_parser = subparsers.add_parser("strava")
    strava_subparsers = strava_parser.add_subparsers(dest="strava_command")
    strava_subparsers.add_parser("doctor")
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
    sync_parser.add_argument("--schedule-next-if-pending", action="store_true")
    sync_parser.add_argument("--schedule-delay-minutes", type=int, default=20)
    sync_parser.add_argument(
        "--schedule-unit",
        default="nono-sports-strava-sync-adaptive",
    )
    sync_parser.add_argument("--lock-file", default=None)
    _add_activity_fetch_options(sync_parser)

    garmin_parser = subparsers.add_parser("garmin")
    garmin_subparsers = garmin_parser.add_subparsers(dest="garmin_command")
    garmin_subparsers.add_parser("doctor")
    garmin_subparsers.add_parser("prepare-dirs")
    garmin_normalize_parser = garmin_subparsers.add_parser("normalize")
    garmin_normalize_parser.add_argument("--force", action="store_true")
    garmin_normalize_parser.add_argument(
        "--keep-intermediate-files",
        action="store_true",
        help=(
            "Keep diagnostic intermediate files generated during normalization. "
            "Use only for debugging specific issues."
        ),
    )
    garmin_fetch_parser = garmin_subparsers.add_parser("fetch-activities")
    garmin_fetch_parser.add_argument("--start", type=int, default=0)
    garmin_fetch_parser.add_argument("--limit", type=int, default=20)
    garmin_fetch_parser.add_argument("--max-activities", type=int, default=1)
    garmin_fetch_parser.add_argument("--max-pages", type=int, default=100)
    garmin_fetch_parser.add_argument("--force", action="store_true")
    garmin_fetch_parser.add_argument("--skip-fit", action="store_true")
    garmin_fetch_parser.add_argument("--include-tcx", action="store_true")
    garmin_fetch_parser.add_argument("--include-gpx", action="store_true")
    garmin_decode_parser = garmin_subparsers.add_parser("decode-fit")
    garmin_decode_parser.add_argument("--activity-id", default=None)
    garmin_decode_parser.add_argument("--force", action="store_true")
    garmin_clean_parser = garmin_subparsers.add_parser("clean-intermediates")
    garmin_clean_parser.add_argument("--activity-id", default=None)
    garmin_clean_parser.add_argument("--dry-run", action="store_true")
    garmin_sync_parser = garmin_subparsers.add_parser("sync")
    garmin_sync_parser.add_argument("--skip-fetch", action="store_true")
    garmin_sync_parser.add_argument("--start", type=int, default=0)
    garmin_sync_parser.add_argument("--limit", type=int, default=20)
    garmin_sync_parser.add_argument("--max-activities", type=int, default=1)
    garmin_sync_parser.add_argument("--max-pages", type=int, default=100)
    garmin_sync_parser.add_argument("--force", action="store_true")
    garmin_sync_parser.add_argument("--skip-fit", action="store_true")
    garmin_sync_parser.add_argument("--include-tcx", action="store_true")
    garmin_sync_parser.add_argument("--include-gpx", action="store_true")
    garmin_sync_parser.add_argument("--lock-file", default=None)
    garmin_sync_parser.add_argument(
        "--keep-intermediate-files",
        action="store_true",
        help=(
            "Keep diagnostic intermediate files generated during synchronization. "
            "Use only for debugging specific issues."
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        report = run_common_doctor()
        print(format_doctor_report(report))
        return 1 if report.status == "error" else 0

    if args.command == "strava" and args.strava_command == "doctor":
        report = run_strava_doctor()
        print(format_doctor_report(report))
        return 1 if report.status == "error" else 0

    if args.command == "garmin" and args.garmin_command == "doctor":
        report = run_garmin_doctor()
        print(format_doctor_report(report))
        return 1 if report.status == "error" else 0

    if args.command == "garmin" and args.garmin_command == "prepare-dirs":
        config = load_config()
        created_paths = ensure_garmin_connect_directories(config.data_root)
        print(
            f"Prepared {len(created_paths)} Garmin Connect directories "
            f"in {config.data_root}"
        )
        return 0

    if args.command == "fit" and args.fit_command == "compare-decoders":
        comparison = compare_fit_decoders(Path(args.path))
        comparison_payload = fit_decoder_comparison_to_dict(comparison)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                _json_dump(comparison_payload),
                encoding="utf-8",
            )
            print(f"Wrote FIT decoder comparison: {output_path}")
        else:
            print(
                "Compared FIT decoders: "
                f"message_types_equal={comparison.message_types_equal}, "
                f"fitdecode_messages={len(comparison.fitdecode['message_counts'])}, "
                "garmin_fit_sdk_messages="
                f"{len(comparison.garmin_fit_sdk['message_counts'])}."
            )
        return 0

    if args.command == "garmin" and args.garmin_command == "fetch-activities":
        project_config = load_config()
        ensure_garmin_connect_directories(project_config.data_root)
        result, raw_store = _run_garmin_fetch_activities(args, project_config)
        _print_garmin_fetch_activities_result(result, raw_store)
        return 0

    if args.command == "garmin" and args.garmin_command == "sync":
        project_config = load_config()
        ensure_garmin_connect_directories(project_config.data_root)
        if args.lock_file:
            with acquire_file_lock(Path(args.lock_file)):
                return _run_garmin_sync(args, project_config)
        return _run_garmin_sync(args, project_config)

    if args.command == "garmin" and args.garmin_command == "normalize":
        project_config = load_config()
        ensure_garmin_connect_directories(project_config.data_root)
        result = normalize_garmin_dataset(
            project_config.data_root,
            force=args.force,
            keep_intermediate_files=args.keep_intermediate_files,
        )
        _print_garmin_normalization_result(result)
        return 0

    if args.command == "garmin" and args.garmin_command == "decode-fit":
        if args.activity_id is None:
            print(
                "ERROR: garmin decode-fit requires --activity-id to avoid "
                "generating hundreds of large diagnostic files."
            )
            return 2
        project_config = load_config()
        ensure_garmin_connect_directories(project_config.data_root)
        raw_store = GarminRawStore(project_config.data_root)
        decoded = _decode_garmin_fit_files(
            project_config.data_root,
            raw_store,
            activity_id=args.activity_id,
            force=args.force,
        )
        print(f"Decoded {decoded} Garmin FIT file(s).")
        decoded_root = garmin_connect_path(
            project_config.data_root,
            "raw",
            "fit_decoded",
        )
        print(f"Decoded root: {decoded_root}")
        return 0

    if args.command == "garmin" and args.garmin_command == "clean-intermediates":
        project_config = load_config()
        ensure_garmin_connect_directories(project_config.data_root)
        count, bytes_cleaned = _clean_garmin_intermediate_files(
            project_config.data_root,
            activity_id=args.activity_id,
            dry_run=args.dry_run,
        )
        verb = "Would remove" if args.dry_run else "Removed"
        print(
            f"{verb} {count} Garmin intermediate file(s), "
            f"{bytes_cleaned} bytes."
        )
        return 0

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
        result = build_multi_source_consolidated(project_config.data_root)
        print(
            "Built consolidated dataset: "
            f"{result.activities} activities, "
            f"{result.activity_sources} activity source links, "
            f"{result.streams_index} stream index records, "
            f"{result.duplicate_candidates} duplicate candidates, "
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
        if args.lock_file:
            with acquire_file_lock(Path(args.lock_file)):
                return _run_strava_sync(args, project_config)
        return _run_strava_sync(args, project_config)

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


def _decode_garmin_fit_files(
    data_root: Path,
    raw_store: GarminRawStore,
    *,
    activity_id: str | None,
    force: bool,
) -> int:
    fit_root = garmin_connect_path(data_root, "raw", "activity_files")
    decoded = 0
    fit_paths = (
        [fit_root / f"{activity_id}.fit"]
        if activity_id is not None
        else sorted(fit_root.glob("*.fit"))
    )
    for fit_path in fit_paths:
        if not fit_path.exists():
            continue
        output_relative = f"fit_decoded/{fit_path.stem}.fitdecode.json"
        output_path = raw_store.raw_root / output_relative
        if output_path.exists() and not force:
            continue
        result = decode_fit_with_fitdecode(fit_path)
        raw_store.write_json(
            output_relative,
            {
                "backend": result.backend,
                "errors": list(result.errors),
                "frames": result.frames,
                "messages": result.messages,
            },
            endpoint="fitdecode",
            params={"path": fit_path.relative_to(raw_store.raw_root).as_posix()},
            kind="derived",
        )
        decoded += 1
    return decoded


def _clean_garmin_intermediate_files(
    data_root: Path,
    *,
    activity_id: str | None,
    dry_run: bool,
) -> tuple[int, int]:
    fit_decoded_root = garmin_connect_path(data_root, "raw", "fit_decoded")
    if activity_id is None:
        paths = sorted(fit_decoded_root.glob("*.fitdecode.json"))
    else:
        paths = [fit_decoded_root / f"{activity_id}.fitdecode.json"]

    count = 0
    bytes_cleaned = 0
    for path in paths:
        if not path.is_file():
            continue
        count += 1
        bytes_cleaned += path.stat().st_size
        if not dry_run:
            path.unlink()
    return count, bytes_cleaned


def _json_dump(payload: object) -> str:
    return f"{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}\n"


def _run_strava_sync(args: argparse.Namespace, project_config: ProjectConfig) -> int:
    last_rate_limit = None
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
    consolidated_result = build_multi_source_consolidated(project_config.data_root)
    print(
        "Built consolidated dataset: "
        f"{consolidated_result.activities} activities, "
        f"{consolidated_result.activity_sources} activity source links, "
        f"{consolidated_result.streams_index} stream index records, "
        f"{consolidated_result.duplicate_candidates} duplicate candidates, "
        f"{len(consolidated_result.written)} files written."
    )
    summary = _run_validation(project_config)
    if args.schedule_next_if_pending:
        _schedule_next_sync_if_needed(args, summary, last_rate_limit)
    return 1 if summary.status == "fail" else 0


def _run_garmin_sync(args: argparse.Namespace, project_config: ProjectConfig) -> int:
    raw_store = GarminRawStore(project_config.data_root)
    if args.skip_fetch:
        print("Skipped Garmin Connect fetch. Running offline pipeline only.")
    else:
        result, raw_store = _run_garmin_fetch_activities(args, project_config)
        _print_garmin_fetch_activities_result(result, raw_store)

    if args.keep_intermediate_files:
        print(
            "Garmin diagnostic intermediate files will be kept. "
            "Use garmin clean-intermediates after debugging."
        )
    else:
        print(
            "Garmin FIT files will be decoded transiently during normalization; "
            "no fit_decoded files will be persisted."
        )

    normalize_result = normalize_garmin_dataset(
        project_config.data_root,
        force=args.force,
        keep_intermediate_files=args.keep_intermediate_files,
    )
    _print_garmin_normalization_result(normalize_result)

    consolidated_result = build_multi_source_consolidated(project_config.data_root)
    print(
        "Built consolidated dataset: "
        f"{consolidated_result.activities} activities, "
        f"{consolidated_result.activity_sources} activity source links, "
        f"{consolidated_result.streams_index} stream index records, "
        f"{consolidated_result.duplicate_candidates} duplicate candidates, "
        f"{len(consolidated_result.written)} files written."
    )
    print(f"Consolidated root: {consolidated_result.consolidated_root}")
    return 0


def _schedule_next_sync_if_needed(
    args: argparse.Namespace,
    summary: ValidationSummary,
    last_rate_limit: RateLimitSnapshot | None,
) -> None:
    decision = build_adaptive_schedule_decision(
        summary=summary,
        rate_limit=last_rate_limit,
        configured_daily_cap=args.max_read_requests_daily,
        reserve_requests=args.rate_limit_reserve,
        skip_fetch=args.skip_fetch,
    )
    print(f"Adaptive schedule: {decision.reason}")
    if not decision.should_schedule:
        return

    schedule_with_systemd(
        command=tuple(_build_adaptive_sync_command(args)),
        delay_minutes=args.schedule_delay_minutes,
        unit_name=args.schedule_unit,
    )
    print(
        "Adaptive schedule: next sync scheduled "
        f"in {args.schedule_delay_minutes} minutes as {args.schedule_unit}."
    )


def _build_adaptive_sync_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "nono_sports",
        "strava",
        "sync",
        "--schedule-next-if-pending",
        "--schedule-delay-minutes",
        str(args.schedule_delay_minutes),
        "--schedule-unit",
        args.schedule_unit,
        "--max-read-requests-15min",
        str(args.max_read_requests_15min),
        "--max-read-requests-daily",
        str(args.max_read_requests_daily),
        "--rate-limit-reserve",
        str(args.rate_limit_reserve),
    ]
    if args.lock_file:
        command.extend(["--lock-file", args.lock_file])
    _append_optional_activity_fetch_options(command, args)
    return command


def _append_optional_activity_fetch_options(
    command: list[str],
    args: argparse.Namespace,
) -> None:
    for flag_name, value in (
        ("--after", args.after),
        ("--before", args.before),
        ("--max-activities", args.max_activities),
    ):
        if value is not None:
            command.extend([flag_name, str(value)])
    for flag_name, enabled in (
        ("--force", args.force),
        ("--skip-gear", args.skip_gear),
        ("--skip-laps", args.skip_laps),
        ("--skip-segments", args.skip_segments),
        ("--skip-segment-streams", args.skip_segment_streams),
        ("--skip-streams", args.skip_streams),
        ("--include-zones", args.include_zones),
    ):
        if enabled:
            command.append(flag_name)


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


def _run_garmin_fetch_activities(
    args: argparse.Namespace,
    project_config: ProjectConfig,
) -> tuple[GarminRawSyncResult, GarminRawStore]:
    client = login_from_tokenstore()
    raw_store = GarminRawStore(project_config.data_root)
    state_store = GarminStateStore(project_config.data_root)
    result = sync_garmin_activities_raw(
        client,
        raw_store,
        state_store,
        start=args.start,
        limit=args.limit,
        max_activities=args.max_activities,
        max_pages=args.max_pages,
        force=args.force,
        include_fit=not args.skip_fit,
        include_tcx=args.include_tcx,
        include_gpx=args.include_gpx,
    )
    return result, raw_store


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


def _print_garmin_fetch_activities_result(
    result: GarminRawSyncResult,
    raw_store: GarminRawStore,
) -> None:
    print(
        "Downloaded Garmin Connect raw files: "
        f"{result.listed_activities} listed, "
        f"{result.scanned_pages} pages scanned, "
        f"{result.processed_activities} processed, "
        f"{result.skipped_activities} skipped, "
        f"{len(result.written)} written, "
        f"{len(result.recoverable_errors)} recoverable errors, "
        f"{len(result.warnings)} warnings."
    )
    print(f"Raw root: {raw_store.raw_root}")
    print(f"State: {result.state_path}")


def _print_garmin_normalization_result(result: GarminNormalizationResult) -> None:
    print(
        "Normalized Garmin Connect raw data: "
        f"{result.activities} activities, "
        f"{result.streams} streams, "
        f"{result.laps} laps, "
        f"{result.splits} splits, "
        f"{result.typed_splits} typed splits, "
        f"{result.processed_activities} processed, "
        f"{result.reused_activities} reused, "
        f"{len(result.written)} files written."
    )
    print(f"Normalized root: {result.normalized_root}")


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
