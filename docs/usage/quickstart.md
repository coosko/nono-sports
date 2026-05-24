# Guía de uso rápida

Esta guía describe el estado actual del repositorio, no una versión funcional completa del producto.

## Requisitos

- Python 3.11 o 3.12
- `git`
- entorno virtual

## Instalación

```bash
cd /home/carlos/dev/nono-sport
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m pip install -r requirements-dev.txt
```

## Estado actual

Actualmente el paquete solo contiene un scaffold mínimo. No existen todavía comandos funcionales de sincronización.

## Estructura de datos

Si quieres preparar la estructura de datos futura:

```bash
export NONO_SPORT_DATA_ROOT='/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte'
python3 scripts/create_data_directories.py
```

## Verificación básica

Después de instalar las dependencias de desarrollo, puedes ejecutar los tests de cualquiera de estas dos formas:

```bash
python3 -m pytest
```

O de forma explícita contra el entorno virtual del repositorio:

```bash
./.venv/bin/python -m pytest
```

Si aparece `No module named pytest`, significa que faltan las dependencias de desarrollo o que no estás usando el entorno virtual del proyecto.

Para ejecutar lint y tests con un único comando:

```bash
python3 scripts/check.py
```

La autenticación Strava se describe en `docs/usage/strava-auth.md`.
