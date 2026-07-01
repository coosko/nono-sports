# Descarga raw Garmin Connect

`nono-sports garmin fetch-activities` descarga actividades Garmin Connect en la
capa raw sin normalizar ni consolidar todavía.

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

## Descargar una actividad

```bash
./.venv/bin/python -m nono_sports garmin fetch-activities \
  --limit 1 \
  --max-activities 1
```

Por defecto descarga FIT original y no descarga GPX/TCX para reducir llamadas.
Garmin entrega el formato `ORIGINAL` como ZIP; `nono-sports` conserva ese ZIP y
extrae el FIT interno.

## Opciones

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
│   ├── activities_index.json
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
