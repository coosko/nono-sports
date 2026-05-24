from __future__ import annotations

from typing import Any

import httpx


class StravaSync:
    """Sincronizador de datos con la API de Strava."""

    BASE_URL = "https://www.strava.com/api/v3"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def refresh_access_token(self) -> dict[str, Any]:
        response = httpx.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()

    def fetch_activities(
        self,
        access_token: str,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = httpx.get(
            f"{self.BASE_URL}/athlete/activities",
            headers=headers,
            params={"per_page": per_page},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
