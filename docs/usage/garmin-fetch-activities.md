# Sincronización Garmin Connect

`nono-sports garmin sync` encadena descarga raw, decodificación FIT,
normalización Garmin Connect y consolidación multi-fuente.

Usa el tokenstore validado en:

```text
~/.local/state/nono-sports/garmin_connect/tokenstore/
```

No hace login interactivo. Si el tokenstore no sirve, hay que repetir la prueba
aislada o reautenticar manualmente antes de automatizar.

## Preparar estructura

```bash
./.venv/bin/python -m nono_sports garmin prepare-dirs
```

## Sincronizar una actividad

```bash
./.venv/bin/python -m nono_sports garmin sync \
  --limit 20 \
  --max-activities 1 \
  --max-pages 100
```

Por defecto descarga FIT original y no descarga GPX/TCX para reducir llamadas.
Garmin entrega el formato `ORIGINAL` como ZIP; `nono-sports` conserva ese ZIP y
extrae el FIT interno.

La descarga raw es incremental. Si las primeras actividades ya están completas,
el comando escanea páginas sucesivas de Garmin Connect y las salta hasta
encontrar la siguiente actividad pendiente. Por tanto, no hace falta pedir
siempre las 1153 actividades ni mover `--start` a mano.

`--limit` es el tamaño de página del listado de Garmin, no el número de
actividades que se van a descargar. Con `--limit 20`, cada página listada puede
contener hasta 20 resúmenes de actividad.

`--max-activities` limita cuántas actividades pendientes se descargan en esta
ejecución. Con `--max-activities 1`, descarga como máximo una actividad nueva,
aunque tenga que escanear varias páginas para encontrarla.

`--max-pages` limita cuántas páginas del listado se pueden escanear en una
ejecución. Con `--limit 20 --max-pages 100`, el comando puede revisar hasta
2000 resúmenes, suficiente para localizar pendientes dentro de un histórico de
1153 actividades.

Para descargar varias actividades nuevas en una ejecución conservadora:

```bash
./.venv/bin/python -m nono_sports garmin sync \
  --limit 20 \
  --max-activities 3 \
  --max-pages 100
```

Para escanear menos páginas con el mismo histórico se puede subir el tamaño de
página:

```bash
./.venv/bin/python -m nono_sports garmin sync \
  --limit 50 \
  --max-activities 1 \
  --max-pages 30
```

Ese ejemplo puede revisar hasta 1500 resúmenes y descargar como máximo una
actividad pendiente.

Para ejecutar solo la parte offline sobre raw ya descargado:

```bash
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

## Opciones

```bash
./.venv/bin/python -m nono_sports garmin sync --force
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
./.venv/bin/python -m nono_sports garmin sync --skip-fit
./.venv/bin/python -m nono_sports garmin sync --include-gpx
./.venv/bin/python -m nono_sports garmin sync --include-tcx
./.venv/bin/python -m nono_sports garmin sync --lock-file /ruta/garmin.lock
```

Los comandos parciales siguen disponibles para diagnóstico:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activities --force
./.venv/bin/python -m nono_sports garmin fetch-activities --skip-fit
./.venv/bin/python -m nono_sports garmin fetch-activities --include-gpx
./.venv/bin/python -m nono_sports garmin fetch-activities --include-tcx
```

## Salida raw

La estructura inicial es:

```text
10_fuentes/garmin_connect/
├── raw/
│   ├── manifest.jsonl
│   ├── activities_index_<start>.json
│   ├── activities/<id>.json
│   ├── activities/<id>.details.json
│   ├── activity_files/<id>.original.zip
│   ├── activity_files/<id>.fit
│   ├── fit_decoded/<id>.fitdecode.json
│   ├── splits/<id>.json
│   ├── splits/<id>.summaries.json
│   ├── typed_splits/<id>.json
│   └── weather/<id>.json
└── logs/
    └── activity_sync_state.json
```

`splits/<id>.json` puede incluir `lapDTOs`; si Garmin ofrece laps por otro
endpoint o estructura independiente, se añadirá en una fase posterior.

## Decodificar FIT

La decodificación FIT es offline y usa el módulo independiente
`nono_sports.formats.fit`.

```bash
./.venv/bin/python -m nono_sports garmin decode-fit --activity-id <id>
```

El backend inicial es `fitdecode==0.11.0`.

El JSON derivado conserva dos niveles:

- campos directos por nombre, pensados para uso sencillo en normalización
- `_fit_fields` y `_fit_message`, con `def_num`, `raw_value`, unidades y tipos
  FIT para no perder información de bajo nivel

Para contrastar un FIT con el SDK oficial de Garmin, sin depender de que el
origen sea Garmin Connect:

```bash
./.venv/bin/python -m nono_sports fit compare-decoders \
  --path /ruta/a/activity.fit \
  --output /tmp/fit-decoder-comparison.json
```

Requiere instalar el extra opcional:

```bash
./.venv/bin/python -m pip install -e '.[fit-compare]'
```

## Normalizar Garmin Connect

Una vez descargado el raw y decodificado el FIT, genera la capa común:

```bash
./.venv/bin/python -m nono_sports garmin normalize
```

La normalización es incremental: guarda fingerprints por actividad en
`normalizado/state.json` y reutiliza los registros ya normalizados si el raw/FIT
no ha cambiado. En la salida:

- `processed`: actividades recalculadas desde raw/FIT.
- `reused`: actividades reutilizadas sin volver a leer FIT decodificado.

Usa `--force` solo si quieres recalcular todo:

```bash
./.venv/bin/python -m nono_sports garmin normalize --force
./.venv/bin/python -m nono_sports garmin sync --skip-fetch --force
```

Escribe:

```text
10_fuentes/garmin_connect/normalizado/activities.jsonl
10_fuentes/garmin_connect/normalizado/streams.jsonl
10_fuentes/garmin_connect/normalizado/streams_index.jsonl
10_fuentes/garmin_connect/normalizado/laps.jsonl
10_fuentes/garmin_connect/normalizado/splits.jsonl
10_fuentes/garmin_connect/normalizado/typed_splits.jsonl
10_fuentes/garmin_connect/normalizado/segment_candidates.jsonl
10_fuentes/garmin_connect/normalizado/state.json
```

## Validación local inicial

Resultado validado:

- 1 actividad listada.
- 1 actividad procesada.
- 8 ficheros raw escritos.
- tras corregir el contenedor `ORIGINAL`, 9 ficheros raw escritos: ZIP original
  y FIT extraído por separado.
- FIT decodificado con `fitdecode`: 6844 frames, 20 tipos de mensajes, 2480
  records, 4254 mensajes HRV y 0 errores.
- comparación `fitdecode` frente a `garmin-fit-sdk`: mismos tipos de mensaje y
  mismos volúmenes principales. Las diferencias observadas son alias o
  metadatos de campo, por ejemplo `product` frente al `raw_value` de
  `garmin_product`.
- normalización real Garmin: 1 actividad, 1 stream, 3 laps, 1 splits y 1 typed
  splits.
- normalización incremental real: segunda ejecución offline con 12 actividades,
  `0 processed` y `12 reused`.
- consolidación real detectó Garmin `23422332225` y Strava `19114956119` como
  la misma actividad con confianza `0.97`.
- 0 errores recuperables.
- segunda ejecución idempotente: 0 procesadas, 1 saltada.

## Prudencia operativa

Garmin ya devolvió `429` durante pruebas de login. Por tanto:

- no reloguear en cada ejecución
- reutilizar tokenstore
- empezar con lotes pequeños
- evitar backfills agresivos hasta entender límites reales
- para backfill manual, usar `garmin sync --limit 20 --max-activities 1
  --max-pages 100` y esperar entre ejecuciones
