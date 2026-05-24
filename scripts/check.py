#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

COMMANDS = [
    [sys.executable, "-m", "ruff", "check", "src", "tests"],
    [sys.executable, "-m", "pytest"],
]


def main() -> int:
    for command in COMMANDS:
        # The command list is static project tooling, not user-provided input.
        completed = subprocess.run(command, check=False)  # noqa: S603
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
