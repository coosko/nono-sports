from nono_sports.cli import build_parser


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
    args = build_parser().parse_args(["garmin", "normalize"])

    assert args.command == "garmin"
    assert args.garmin_command == "normalize"


def test_parser_accepts_garmin_fetch_activities_options() -> None:
    args = build_parser().parse_args(
        [
            "garmin",
            "fetch-activities",
            "--start",
            "5",
            "--limit",
            "10",
            "--max-activities",
            "2",
            "--force",
            "--skip-fit",
            "--include-tcx",
            "--include-gpx",
        ]
    )

    assert args.command == "garmin"
    assert args.garmin_command == "fetch-activities"
    assert args.start == 5
    assert args.limit == 10
    assert args.max_activities == 2
    assert args.force is True
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
