from pathlib import Path

from nono_sports.cli import _clean_garmin_intermediate_files, build_parser


def test_parser_accepts_build_consolidated_command() -> None:
    args = build_parser().parse_args(["build-consolidated"])

    assert args.command == "build-consolidated"


def test_parser_accepts_common_doctor_command() -> None:
    args = build_parser().parse_args(["doctor"])

    assert args.command == "doctor"


def test_parser_accepts_fit_compare_decoders_command() -> None:
    args = build_parser().parse_args(
        [
            "fit",
            "compare-decoders",
            "--path",
            "activity.fit",
            "--output",
            "comparison.json",
        ]
    )

    assert args.command == "fit"
    assert args.fit_command == "compare-decoders"
    assert args.path == "activity.fit"
    assert args.output == "comparison.json"


def test_parser_accepts_strava_doctor_command() -> None:
    args = build_parser().parse_args(["strava", "doctor"])

    assert args.command == "strava"
    assert args.strava_command == "doctor"


def test_parser_accepts_garmin_doctor_command() -> None:
    args = build_parser().parse_args(["garmin", "doctor"])

    assert args.command == "garmin"
    assert args.garmin_command == "doctor"


def test_parser_accepts_garmin_prepare_dirs_command() -> None:
    args = build_parser().parse_args(["garmin", "prepare-dirs"])

    assert args.command == "garmin"
    assert args.garmin_command == "prepare-dirs"


def test_parser_accepts_garmin_normalize_command() -> None:
    args = build_parser().parse_args(
        ["garmin", "normalize", "--force", "--keep-intermediate-files"]
    )

    assert args.command == "garmin"
    assert args.garmin_command == "normalize"
    assert args.force is True
    assert args.keep_intermediate_files is True


def test_parser_accepts_garmin_fetch_activities_options() -> None:
    args = build_parser().parse_args(
        [
            "garmin",
            "fetch-activities",
            "--start",
            "5",
            "--after",
            "1714521600",
            "--before",
            "1717200000",
            "--limit",
            "10",
            "--max-activities",
            "2",
            "--max-pages",
            "3",
            "--force",
            "--full-scan",
            "--incremental-lookback-days",
            "3",
            "--skip-fit",
            "--include-tcx",
            "--include-gpx",
        ]
    )

    assert args.command == "garmin"
    assert args.garmin_command == "fetch-activities"
    assert args.start == 5
    assert args.after == 1714521600
    assert args.before == 1717200000
    assert args.limit == 10
    assert args.max_activities == 2
    assert args.max_pages == 3
    assert args.force is True
    assert args.full_scan is True
    assert args.incremental_lookback_days == 3
    assert args.skip_fit is True
    assert args.include_tcx is True
    assert args.include_gpx is True


def test_parser_accepts_garmin_decode_fit_options() -> None:
    args = build_parser().parse_args(
        [
            "garmin",
            "decode-fit",
            "--activity-id",
            "123",
            "--force",
        ]
    )

    assert args.command == "garmin"
    assert args.garmin_command == "decode-fit"
    assert args.activity_id == "123"
    assert args.force is True


def test_parser_accepts_garmin_clean_intermediates_options() -> None:
    args = build_parser().parse_args(
        [
            "garmin",
            "clean-intermediates",
            "--activity-id",
            "123",
            "--dry-run",
        ]
    )

    assert args.command == "garmin"
    assert args.garmin_command == "clean-intermediates"
    assert args.activity_id == "123"
    assert args.dry_run is True


def test_parser_accepts_garmin_sync_options() -> None:
    args = build_parser().parse_args(
        [
            "garmin",
            "sync",
            "--skip-fetch",
            "--start",
            "5",
            "--after",
            "1714521600",
            "--before",
            "1717200000",
            "--limit",
            "10",
            "--max-activities",
            "2",
            "--max-pages",
            "3",
            "--force",
            "--full-scan",
            "--incremental-lookback-days",
            "3",
            "--skip-fit",
            "--include-tcx",
            "--include-gpx",
            "--lock-file",
            "garmin.lock",
            "--keep-intermediate-files",
        ]
    )

    assert args.command == "garmin"
    assert args.garmin_command == "sync"
    assert args.skip_fetch is True
    assert args.start == 5
    assert args.after == 1714521600
    assert args.before == 1717200000
    assert args.limit == 10
    assert args.max_activities == 2
    assert args.max_pages == 3
    assert args.force is True
    assert args.full_scan is True
    assert args.incremental_lookback_days == 3
    assert args.skip_fit is True
    assert args.include_tcx is True
    assert args.include_gpx is True
    assert args.lock_file == "garmin.lock"
    assert args.keep_intermediate_files is True


def test_parser_defaults_garmin_sync_to_unbounded_incremental_scan() -> None:
    args = build_parser().parse_args(["garmin", "sync"])

    assert args.command == "garmin"
    assert args.garmin_command == "sync"
    assert args.limit == 20
    assert args.max_activities is None
    assert args.max_pages is None


def test_clean_garmin_intermediate_files_supports_dry_run_and_delete(
    tmp_path: Path,
) -> None:
    fit_decoded_root = (
        tmp_path
        / "10_fuentes"
        / "garmin_connect"
        / "raw"
        / "fit_decoded"
    )
    fit_decoded_root.mkdir(parents=True)
    first = fit_decoded_root / "123.fitdecode.json"
    second = fit_decoded_root / "456.fitdecode.json"
    first.write_text("abc", encoding="utf-8")
    second.write_text("defg", encoding="utf-8")

    count, bytes_cleaned = _clean_garmin_intermediate_files(
        tmp_path,
        activity_id="123",
        dry_run=True,
    )

    assert count == 1
    assert bytes_cleaned == 3
    assert first.exists()

    count, bytes_cleaned = _clean_garmin_intermediate_files(
        tmp_path,
        activity_id=None,
        dry_run=False,
    )

    assert count == 2
    assert bytes_cleaned == 7
    assert not first.exists()
    assert not second.exists()


def test_parser_accepts_strava_fetch_context_options() -> None:
    args = build_parser().parse_args(
        [
            "strava",
            "fetch-context",
            "--skip-route-details",
            "--skip-gear-details",
        ]
    )

    assert args.command == "strava"
    assert args.strava_command == "fetch-context"
    assert args.skip_route_details is True
    assert args.skip_gear_details is True


def test_parser_accepts_strava_fetch_activities_options() -> None:
    args = build_parser().parse_args(
        [
            "strava",
            "fetch-activities",
            "--after",
            "1714521600",
            "--before",
            "1717200000",
            "--max-activities",
            "3",
            "--force",
            "--skip-gear",
            "--skip-laps",
            "--skip-segments",
            "--skip-segment-streams",
            "--skip-streams",
            "--include-zones",
            "--max-read-requests-15min",
            "180",
            "--max-read-requests-daily",
            "1500",
            "--rate-limit-reserve",
            "10",
        ]
    )

    assert args.command == "strava"
    assert args.strava_command == "fetch-activities"
    assert args.after == 1714521600
    assert args.before == 1717200000
    assert args.max_activities == 3
    assert args.force is True
    assert args.skip_gear is True
    assert args.skip_laps is True
    assert args.skip_segments is True
    assert args.skip_segment_streams is True
    assert args.skip_streams is True
    assert args.include_zones is True
    assert args.max_read_requests_15min == 180
    assert args.max_read_requests_daily == 1500
    assert args.rate_limit_reserve == 10


def test_parser_accepts_strava_normalize_command() -> None:
    args = build_parser().parse_args(["strava", "normalize"])

    assert args.command == "strava"
    assert args.strava_command == "normalize"


def test_parser_accepts_strava_validate_command() -> None:
    args = build_parser().parse_args(["strava", "validate"])

    assert args.command == "strava"
    assert args.strava_command == "validate"


def test_parser_accepts_strava_sync_options() -> None:
    args = build_parser().parse_args(
        [
            "strava",
            "sync",
            "--skip-fetch",
            "--schedule-next-if-pending",
            "--schedule-delay-minutes",
            "20",
            "--schedule-unit",
            "nono-sports-strava-sync-adaptive",
            "--lock-file",
            "/home/nono/.local/state/nono-sports/strava-sync.lock",
            "--max-activities",
            "10",
            "--max-read-requests-15min",
            "80",
            "--max-read-requests-daily",
            "900",
            "--rate-limit-reserve",
            "10",
        ]
    )

    assert args.command == "strava"
    assert args.strava_command == "sync"
    assert args.skip_fetch is True
    assert args.schedule_next_if_pending is True
    assert args.schedule_delay_minutes == 20
    assert args.schedule_unit == "nono-sports-strava-sync-adaptive"
    assert args.lock_file == "/home/nono/.local/state/nono-sports/strava-sync.lock"
    assert args.max_activities == 10
    assert args.max_read_requests_15min == 80
    assert args.max_read_requests_daily == 900
    assert args.rate_limit_reserve == 10
