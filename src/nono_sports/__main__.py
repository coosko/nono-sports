"""CLI entrypoint for the nono-sports project."""

import sys

from nono_sports.cli import main
from nono_sports.core.errors import NonoSportsError

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NonoSportsError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
