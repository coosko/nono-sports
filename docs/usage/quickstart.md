# Guía de uso rápida

## Requisitos

- Python 3.11 o superior
- `git`
- Entorno virtual

## Instalación

```bash
cd /home/carlos/dev/nono-sport
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m pip install -r requirements-dev.txt
```

## Configuración

1. Copia el ejemplo de variables de entorno:

```bash
cp .env.example .env
```

2. Rellena las variables `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` y `STRAVA_REFRESH_TOKEN`.
3. Define el root de datos:

```bash
export NONO_SPORT_DATA_ROOT='/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte'
```

## Crear estructura de datos

```bash
python3 scripts/create_data_directories.py
```

## Ejecutar tests

```bash
python3 -m pytest
```
