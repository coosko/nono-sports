#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

DATA_ROOT_ENV = "NONO_SPORT_DATA_ROOT"

DIRECTORIES = [
    "00_referencia",
    "10_fuentes/strava/raw/activities",
    "10_fuentes/strava/normalizado",
    "10_fuentes/strava/logs",
    "10_fuentes/garmin_connect",
    "10_fuentes/komoot",
    "10_fuentes/manual",
    "20_consolidado",
    "30_analisis/informes",
    "30_analisis/planes",
    "30_analisis/seguimiento",
    "30_analisis/graficas",
    "90_archivo",
]

FILES = [
    "10_fuentes/strava/raw/athlete.json",
    "10_fuentes/strava/normalizado/activities.jsonl",
    "10_fuentes/strava/normalizado/activities.csv",
    "10_fuentes/strava/normalizado/streams_index.jsonl",
    "10_fuentes/strava/normalizado/state.json",
    "20_consolidado/activities.jsonl",
    "20_consolidado/activities.csv",
    "20_consolidado/activity_sources.jsonl",
    "20_consolidado/streams_index.jsonl",
    "20_consolidado/state.json",
]


def normalize_root(root: str) -> Path:
    if len(root) >= 2 and root[1] == ":":
        drive = root[0].lower()
        rest = root[2:].replace("\\", "/").lstrip("/")
        wsl_mount = Path("/mnt") / drive / Path(rest)
        if wsl_mount.exists():
            return wsl_mount
    return Path(root)


def create_directories(root: Path) -> None:
    for directory in DIRECTORIES:
        path = root / directory
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {path}")


def create_files(root: Path) -> None:
    for file_path in FILES:
        path = root / file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        print(f"Created file: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea la estructura de directorios de datos para nono-sports."
    )
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "Ruta raíz donde se debe crear la estructura de datos. "
            f"Si no se indica, se usa la variable de entorno {DATA_ROOT_ENV}."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root_value = args.root or os.getenv(DATA_ROOT_ENV)
    if not root_value:
        print(
            "ERROR: Debes proporcionar la ruta raíz con --root "
            f"o establecer la variable de entorno {DATA_ROOT_ENV}."
        )
        return 1

    root = normalize_root(root_value)

    if not root.exists() and root.drive and root.drive.endswith(":"):
        print(
            f"Advertencia: no se encontró la ruta montada {root}.\n"
            "Ejecuta este script desde Windows o asegura que el volumen "
            "esté montado en WSL.\n"
        )

    print(f"Uso de raíz: {root}")
    create_directories(root)
    create_files(root)
    print("Estructura creada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
