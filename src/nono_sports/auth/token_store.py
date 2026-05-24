"""Token persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from nono_sports.auth.strava_oauth import StravaTokenResponse


class StravaTokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, token: StravaTokenResponse) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(token), ensure_ascii=False, indent=2) + "\n",
        )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def load(self) -> dict[str, object]:
        return json.loads(self.path.read_text())
