"""Command-line interface for nono-sports."""

from __future__ import annotations

import argparse

from nono_sports.auth.strava_oauth import (
    build_authorization_url,
    exchange_code_for_token,
)
from nono_sports.auth.token_store import StravaTokenStore
from nono_sports.core.config import load_config, load_strava_client_config
from nono_sports.core.paths import ensure_strava_v1_directories, strava_token_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nono-sports")
    subparsers = parser.add_subparsers(dest="command")

    strava_parser = subparsers.add_parser("strava")
    strava_subparsers = strava_parser.add_subparsers(dest="strava_command")
    strava_subparsers.add_parser("prepare-dirs")
    auth_parser = strava_subparsers.add_parser("auth")
    auth_parser.add_argument("--code", default=None)
    auth_parser.add_argument("--state", default=None)

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

    parser.print_help()
    return 0
