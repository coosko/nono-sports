import logging
import os
from pathlib import Path

from dotenv import load_dotenv


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def load_environment() -> None:
    env_path = get_project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def get_data_root() -> Path | None:
    load_environment()
    root = os.getenv("NONO_SPORT_DATA_ROOT")
    return Path(root) if root else None


def get_strava_credentials() -> dict[str, str]:
    load_environment()
    return {
        "client_id": os.getenv("STRAVA_CLIENT_ID", ""),
        "client_secret": os.getenv("STRAVA_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("STRAVA_REFRESH_TOKEN", ""),
    }
