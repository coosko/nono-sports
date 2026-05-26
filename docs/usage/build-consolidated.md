# Consolidación inicial

Este documento describe la construcción de la capa `20_consolidado` para consumo posterior por Nono.

## Objetivo

La consolidación inicial crea una vista única de actividades a partir de la capa normalizada.

En la v1 solo se usa Strava como fuente, por lo que no hay deduplicación multi-fuente ni selección avanzada de fuente primaria. Aun así, el resultado ya conserva enlaces fuente para poder añadir Garmin, Komoot o importaciones manuales sin rehacer el contrato.

## Comando

```bash
./.venv/bin/python -m nono_sports build-consolidated
```

El comando no llama a Strava. Lee:

```text
10_fuentes/strava/normalizado/activities.jsonl
10_fuentes/strava/normalizado/streams.jsonl
```

Y escribe:

```text
20_consolidado/activities.jsonl
20_consolidado/activity_sources.jsonl
20_consolidado/streams_index.jsonl
20_consolidado/state.json
```

Cada ejecución reescribe la salida consolidada desde los normalizados disponibles.

Después de consolidar, ejecuta la validación offline:

```bash
./.venv/bin/python -m nono_sports strava validate
```

## Ficheros generados

`activities.jsonl` contiene la actividad consolidada que debe usar Nono como entrada principal.

`activity_sources.jsonl` conserva la relación entre cada actividad consolidada y su actividad fuente normalizada.

`streams_index.jsonl` enlaza cada actividad consolidada con su stream normalizado disponible.

`state.json` resume la estrategia, entradas, salidas y conteos de la ejecución.

## Estrategia v1

- `strategy`: `single_source`
- `primary_source`: `strava`
- `source_count`: `1`
- `match_strategy`: `single_source`
- `match_confidence`: `1.0`

La deduplicación entre fuentes queda fuera de este paso y se abordará cuando entren fuentes adicionales.

## Validación manual

Después de ejecutar el comando, revisa:

- que existen los cuatro ficheros esperados en `20_consolidado`
- que `state.json` muestra los conteos esperados
- que cada actividad tiene `consolidated_activity_uid`
- que cada actividad tiene un enlace correspondiente en `activity_sources.jsonl`
- que una actividad con stream tiene entrada en `streams_index.jsonl`
