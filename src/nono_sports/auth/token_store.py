"""Token persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from nono_sports.auth.strava_oauth import StravaTokenResponse
from nono_sports.core.errors import AuthenticationError


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
        if not self.path.exists():
            raise AuthenticationError(
                "Strava tokens were not found. Run `nono-sports strava auth` first."
            )
        return json.loads(self.path.read_text())

    def load_token(self) -> StravaTokenResponse:
        payload = self.load()
        return StravaTokenResponse(
            token_type=str(payload["token_type"]),
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            expires_at=int(payload["expires_at"]),
            scope=tuple(str(scope) for scope in payload.get("scope", ())),
            athlete=dict(payload.get("athlete") or {}),
        )
