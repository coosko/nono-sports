# Consolidación inicial

Este documento describe la construcción de la capa `20_consolidado` para consumo posterior por Nono.

## Objetivo

La consolidación inicial crea una vista única de actividades a partir de las
capas normalizadas disponibles.

La estrategia actual es `multi_source_initial`: mantiene compatibilidad con
Strava como fuente primaria cuando solo existe Strava, pero ya permite agrupar
actividades equivalentes de varias fuentes y conservar todos sus enlaces.

## Comando

```bash
./.venv/bin/python -m nono_sports build-consolidated
```

El comando no llama a Strava. Lee:

```text
10_fuentes/strava/normalizado/activities.jsonl
10_fuentes/strava/normalizado/streams.jsonl
10_fuentes/garmin_connect/normalizado/activities.jsonl
```

Los ficheros que no existan se ignoran.

Y escribe:

```text
20_consolidado/activities.jsonl
20_consolidado/activity_sources.jsonl
20_consolidado/streams_index.jsonl
20_consolidado/duplicate_candidates.jsonl
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

`duplicate_candidates.jsonl` registra coincidencias detectadas entre fuentes
para revisión humana y ajuste futuro de reglas.

`state.json` resume la estrategia, entradas, salidas y conteos de la ejecución.

## Estrategia v1

- `strategy`: `multi_source_initial`
- política primaria inicial: preferir Strava para mantener compatibilidad
- deduplicación: fecha/hora, duración, distancia y deporte
- `source_count`: `1` si no hay equivalencia, `>1` si se agrupan fuentes
- `activity_sources.jsonl`: un enlace por fuente normalizada
- `duplicate_candidates.jsonl`: informe auditable de agrupaciones candidatas

La selección avanzada por tipo de métrica todavía no está aprobada. Por ejemplo,
Garmin puede ser mejor para sensores/FIT y Strava para segmentos sociales, pero
esa decisión queda para la siguiente iteración de consolidación.

## Validación manual

Después de ejecutar el comando, revisa:

- que existen los cinco ficheros esperados en `20_consolidado`
- que `state.json` muestra los conteos esperados
- que cada actividad tiene `consolidated_activity_uid`
- que cada actividad tiene un enlace correspondiente en `activity_sources.jsonl`
- que una actividad con stream tiene entrada en `streams_index.jsonl`
- que los candidatos de `duplicate_candidates.jsonl` son agrupaciones correctas
  antes de endurecer reglas
