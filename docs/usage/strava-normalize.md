# Normalización Strava

Este documento describe cómo convertir los raw descargados desde Strava a JSONL normalizados y trazables.

## Objetivo

La normalización crea una salida estable para análisis y consolidación posterior. El contrato no depende de Strava: otros orígenes como Garmin, Komoot o importaciones manuales podrán aportar datos complementarios sobre la misma actividad más adelante.

## Comando

```bash
./.venv/bin/python -m nono_sports strava normalize
```

El comando no llama a la API de Strava. Solo lee ficheros locales en:

```text
10_fuentes/strava/raw/
```

Y escribe:

```text
10_fuentes/strava/normalizado/athletes.jsonl
10_fuentes/strava/normalizado/equipment.jsonl
10_fuentes/strava/normalizado/activities.jsonl
10_fuentes/strava/normalizado/streams.jsonl
10_fuentes/strava/normalizado/streams_index.jsonl
10_fuentes/strava/normalizado/state.json
```

Cada ejecución reescribe los JSONL desde los raw disponibles, por lo que es idempotente.

`athletes.jsonl`, `equipment.jsonl`, `streams_index.jsonl` y `state.json`
forman parte del contrato mínimo común de normalizados por fuente.
`streams_index.jsonl` no sustituye a `streams.jsonl`: permite localizar streams
y revisar conteos/entradas sin leer todos los datos de detalle.

## Contrato de actividad

Cada registro de `activities.jsonl` incluye:

- identificadores estables: `activity_uid`, `source`, `source_activity_id`
- deporte normalizado: `sport.family`, `sport.discipline`, `sport.movement_context`
- tiempos: `start`, `duration`
- distancia y desnivel en unidades SI
- energía y métricas principales: velocidad, pulso, cadencia, potencia, temperatura
- localización resumida
- equipo referenciado cuando existe
- vueltas o fases en `laps`
- segmentos referenciados en `segments`
- enlace a stream normalizado mediante `stream_uid`
- completitud por partes: detalle, streams, laps, gear, segmentos, zonas
- trazabilidad raw en `source_reference` y `source_links`
- datos específicos de Strava en `sport_specific`

## Diseño multi-fuente

El modelo deja hueco para datos complementarios:

- Garmin puede aportar sensores, dinámica de ciclismo/carrera, carga fisiológica o mejor granularidad.
- Komoot puede aportar planificación, rutas previstas y contexto de navegación.
- Importaciones manuales pueden aportar notas, RPE, objetivos o entrenamiento de gimnasio.
- Deportes sin distancia clara, como gimnasio o esgrima, usan métricas opcionales y `sport.movement_context` para no forzar campos de ciclismo/carrera.

La consolidación posterior decidirá qué fuente manda para cada campo.

## Validación manual

Después de normalizar, revisa:

- que existen los ficheros esperados de la fuente, incluyendo
  `streams_index.jsonl` y `state.json`
- que el número de actividades coincide con los raw de `activities/<id>.json` disponibles
- que `activities.jsonl` conserva `source_reference.raw_path`
- que una actividad con stream tiene `stream_uid` y registro correspondiente en `streams.jsonl`
