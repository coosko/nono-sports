#!/usr/bin/env python3
"""Isolated Garmin Connect probe for Step 14.

This script validates garminconnect login, token reuse and one activity download
without integrating Garmin data into the main Nono Sports pipeline.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nono_sports.core.errors import AuthenticationError
from nono_sports.core.paths import garmin_connect_tokenstore_path
from nono_sports.garmin_connect.auth import (
    login_from_tokenstore,
    login_interactive,
)
from nono_sports.garmin_connect.sync import collect_activity_snapshot


@dataclass(frozen=True)
class ProbePaths:
    tokenstore: Path
    output_dir: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe Garmin Connect access.")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--activity-id", default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/nono-sports-garmin-probe"),  # noqa: S108
    )
    parser.add_argument(
        "--tokenstore",
        type=Path,
        default=garmin_connect_tokenstore_path(),
    )
    parser.add_argument("--skip-fit", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = ProbePaths(
        tokenstore=args.tokenstore.expanduser(),
        output_dir=args.output_dir.expanduser(),
    )
    _prepare_paths(paths)

    garmin = _login(paths.tokenstore)
    login_from_tokenstore(paths.tokenstore)
    print("Token reuse validated in a fresh Garmin client.")

    print("Calling Garmin: list activities...")
    activities = garmin.list_activities(0, args.limit)
    _write_json(paths.output_dir / "activities_index.json", activities)
    print(f"Listed {len(activities)} Garmin activities.")

    activity_id = args.activity_id or _first_activity_id(activities)
    if activity_id is None:
        print("No activities found; probe finished after login/tokenstore validation.")
        return 0

    print(f"Using activity_id={activity_id}")
    print("Calling Garmin: activity snapshot...")
    snapshot = collect_activity_snapshot(
        garmin,
        activity_id,
        include_fit=not args.skip_fit,
    )
    _write_json(paths.output_dir / f"{activity_id}.activity.json", snapshot.activity)
    _write_json(paths.output_dir / f"{activity_id}.details.json", snapshot.details)
    _write_optional_json(
        paths.output_dir / f"{activity_id}.splits.json",
        snapshot.splits,
    )
    _write_optional_json(
        paths.output_dir / f"{activity_id}.typed_splits.json",
        snapshot.typed_splits,
    )
    _write_optional_json(
        paths.output_dir / f"{activity_id}.split_summaries.json",
        snapshot.split_summaries,
    )
    _write_optional_json(
        paths.output_dir / f"{activity_id}.weather.json",
        snapshot.weather,
    )

    if snapshot.fit is not None:
        fit_path = paths.output_dir / f"{activity_id}.fit"
        fit_path.write_bytes(snapshot.fit)
        print(f"Wrote FIT: {fit_path} ({len(snapshot.fit)} bytes)")

    print(f"Probe output: {paths.output_dir}")
    print(f"Tokenstore: {paths.tokenstore}")
    return 0


def _prepare_paths(paths: ProbePaths) -> None:
    paths.tokenstore.mkdir(parents=True, exist_ok=True)
    paths.tokenstore.chmod(0o700)
    paths.output_dir.mkdir(parents=True, exist_ok=True)


def _login(tokenstore: Path) -> Any:
    try:
        garmin = login_from_tokenstore(tokenstore)
        print("Logged in using saved Garmin tokens.")
        return garmin
    except AuthenticationError:
        print("No valid Garmin tokens found; interactive login required.")
    garmin = login_interactive(tokenstore)
    print("Garmin login successful; tokens saved.")
    return garmin


def _write_optional_json(path: Path, payload: Any | None) -> None:
    if payload is None:
        print(f"WARNING: no payload for {path.name}")
        return
    _write_json(path, payload)


def _first_activity_id(activities: list[dict[str, Any]]) -> str | None:
    if not activities:
        return None
    activity_id = activities[0].get("activityId")
    return str(activity_id) if activity_id is not None else None


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote JSON: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
