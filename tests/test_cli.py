from nono_sports.cli import build_parser


def test_parser_accepts_build_consolidated_command() -> None:
    args = build_parser().parse_args(["build-consolidated"])

    assert args.command == "build-consolidated"


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
