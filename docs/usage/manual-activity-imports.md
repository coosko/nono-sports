# Importaciones manuales de actividades

Esta guía describe la importación manual inicial de actividades GPX.

## Alcance actual

`manual` es una fuente controlada por Nono/Carlos. Sirve para incorporar
ficheros deportivos sueltos cuando no existe un conector directo o cuando una
actividad procede de otra aplicación.

En esta versión está operativo:

- importación de GPX
- copia del GPX original a `10_fuentes/manual/raw/activities/`
- manifiesto raw en `10_fuentes/manual/raw/manifest.jsonl`
- normalización a `activities.jsonl`, `streams.jsonl`, `streams_index.jsonl`
  y `state.json`
- reconstrucción del consolidado tras `manual import-gpx`
- deduplicación frente a Strava/Garmin si la actividad representa la misma
  salida

No está operativo todavía como importador manual:

- FIT manual
- TCX manual
- un conector propio de Komoot, Wikiloc u otra plataforma

Si el GPX viene de Komoot, se debe indicar como `--source-platform komoot`.
Eso no convierte Komoot en fuente conectada; queda como atributo trazable del
import manual.

## Importar un GPX

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports manual import-gpx \
  --path /ruta/a/actividad.gpx \
  --sport hiking \
  --source-platform komoot
```

Opcionalmente se puede fijar el título:

```bash
./.venv/bin/python -m nono_sports manual import-gpx \
  --path /ruta/a/actividad.gpx \
  --sport hiking \
  --source-platform komoot \
  --title "Circular por la sierra"
```

El comando no llama a APIs externas. Ejecuta:

- copia raw del GPX
- normalización de actividades manuales
- normalización de mediciones manuales si existe el CSV
- reconstrucción de `20_consolidado`

## Deportes admitidos

El argumento `--sport` se normaliza al contrato común. Valores útiles:

- `hiking`
- `walking`
- `running`
- `trail_running`
- `ride`
- `cycling`
- `road_cycling`
- `gravel_cycling`
- `mountain_biking`
- `workout`

Si se usa otro valor, se conserva como `source_type` y queda clasificado como
`other`.

## Ficheros generados

Raw:

```text
10_fuentes/manual/raw/activities/<source_platform>_<sha>.gpx
10_fuentes/manual/raw/manifest.jsonl
```

Normalizado:

```text
10_fuentes/manual/normalizado/activities.jsonl
10_fuentes/manual/normalizado/streams.jsonl
10_fuentes/manual/normalizado/streams_index.jsonl
10_fuentes/manual/normalizado/state.json
```

El normalizado conserva:

- `source=manual`
- `flags.manual_import=true`
- `sport_specific.source_platform`
- `sport_specific.original_file_format=gpx`
- distancia estimada desde puntos GPS
- desnivel positivo/negativo desde altitud GPX
- duración y velocidad cuando hay timestamps
- stream de tiempo, lat/lon, distancia acumulada y altitud

## Reprocesar sin importar de nuevo

Si ya existen GPX en `10_fuentes/manual/raw/activities/`:

```bash
./.venv/bin/python -m nono_sports manual normalize
./.venv/bin/python -m nono_sports build-consolidated
```

`manual normalize` no llama a APIs externas y no modifica el raw original.

## Buenas prácticas

- No editar los GPX ya importados salvo reparación explícita.
- Si una actividad procede de una app concreta, usar siempre
  `--source-platform`.
- Si el GPX ya existe en Garmin/Strava, la consolidación intentará agruparlo
  para no duplicar actividades.
- Si se necesita preservar información FIT o TCX, queda pendiente ampliar el
  importador manual a esos formatos.
