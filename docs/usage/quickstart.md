# Guía de uso rápida

Esta guía describe el estado actual del repositorio, no una versión funcional completa del producto.

## Requisitos

- Python 3.11, 3.12, 3.13 o 3.14
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

Actualmente el paquete permite preparar directorios, autenticar Strava, descargar raw de perfil/contexto, descargar raw de actividades con detalle, normalizar esos raw a JSONL, construir una primera capa `20_consolidado` y validar la coherencia del dataset local.

## Estructura de datos

Si quieres preparar la estructura de datos futura:

```bash
export NONO_SPORT_DATA_ROOT='/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte'
./.venv/bin/python -m nono_sports strava prepare-dirs
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

La primera descarga raw de perfil y contexto se describe en `docs/usage/strava-fetch-context.md`.

La descarga raw de actividades se describe en `docs/usage/strava-fetch-activities.md`.

La normalización Strava se describe en `docs/usage/strava-normalize.md`.

La consolidación inicial se describe en `docs/usage/build-consolidated.md`.

La validación de datos se describe en `docs/usage/strava-validate.md`.

La instalación en Nono se describe en `docs/usage/install-nono.md`.

La automatización controlada se describe en `docs/usage/automation.md`.

La guía operativa para el agente Nono se describe en `docs/usage/nono-operator-guide.md`.
