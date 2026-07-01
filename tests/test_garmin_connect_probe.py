from pathlib import Path

from scripts.garmin_connect_probe import build_parser


def test_garmin_connect_probe_parser_defaults() -> None:
    args = build_parser().parse_args([])

    assert args.limit == 1
    assert args.activity_id is None
    assert args.output_dir == Path("/tmp/nono-sports-garmin-probe")  # noqa: S108
    assert args.skip_fit is False


def test_garmin_connect_probe_parser_accepts_activity_id_and_skip_fit() -> None:
    args = build_parser().parse_args(
        [
            "--activity-id",
            "123456",
            "--limit",
            "3",
            "--skip-fit",
            "--output-dir",
            "/tmp/custom-garmin-probe",  # noqa: S108
        ]
    )

    assert args.activity_id == "123456"
    assert args.limit == 3
    assert args.skip_fit is True
    assert args.output_dir == Path("/tmp/custom-garmin-probe")  # noqa: S108
