# Sincronización Garmin Connect

`nono-sports garmin sync` encadena descarga raw, decodificación FIT,
normalización Garmin Connect y consolidación multi-fuente. En el flujo normal
también descarga mediciones recientes y datos de usuario/equipación.

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

El flujo normal también intenta descargar:

- perfil y settings del usuario
- equipación declarada y estadísticas de equipación
- dispositivos Garmin conocidos, último dispositivo usado y dispositivo
  principal de entrenamiento
- equipación asociada a cada actividad cuando Garmin la expone

Estas partes son de solo lectura y reutilizan el tokenstore. Si una pieza
secundaria de equipación o dispositivos no está disponible, la sincronización
debe poder continuar con los datos restantes.

Si una actividad no procede de un dispositivo Garmin sino de una importación,
por ejemplo un GPX subido a Garmin Connect, el ZIP `ORIGINAL` puede no contener
FIT. En ese caso `nono-sports`:

- conserva siempre el ZIP original
- intenta extraer GPX/TCX del ZIP
- si hace falta, pide GPX/TCX a Garmin como fallback
- registra un warning de FIT no disponible, no un error recuperable
- considera la actividad completa sin FIT si existen `activity`, `details` y
  al menos un track GPX/TCX utilizable
- marca el origen normalizado como `source_origin`, por ejemplo `imported_gpx`
- conserva en `sport_specific` el formato original (`original_file_format`) y
  si Garmin lo considera original (`is_original`)

La descarga raw es incremental. En operación normal, `nono-sports` guarda en
`logs/activity_sync_state.json` la última sincronización correcta y, en la
siguiente ejecución, aplica una ventana temporal con solape. Así revisa solo
las actividades recientes y deja de paginar cuando el listado llega a
actividades anteriores a la ventana.

Garmin Connect, a través de `garminconnect==0.3.6`, no expone un filtro fiable
de "modificadas desde". Por eso la ventana incremental se basa en la fecha de
inicio de la actividad, no en una fecha real de modificación. El solape reduce
el riesgo de perder actividades recientes editadas o importadas.

Los argumentos temporales están alineados con Strava:

```bash
./.venv/bin/python -m nono_sports garmin sync --after 1714521600 --before 1717200000
```

Si necesitas ignorar la ventana incremental y volver al escaneo histórico:

```bash
./.venv/bin/python -m nono_sports garmin sync --full-scan
```

El solape por defecto es de 7 días y puede ajustarse:

```bash
./.venv/bin/python -m nono_sports garmin sync --incremental-lookback-days 14
```

`--limit` es el tamaño de página del listado de Garmin, no el número de
actividades que se van a descargar. Con `--limit 20`, cada página listada puede
contener hasta 20 resúmenes de actividad.

`--max-activities` limita cuántas actividades pendientes se descargan en esta
ejecución. Con `--max-activities 1`, descarga como máximo una actividad nueva,
aunque tenga que escanear varias páginas para encontrarla.

`--max-pages` limita cuántas páginas del listado se pueden escanear en una
ejecución. En el uso diario normalmente se recorren pocas páginas por la
ventana incremental; `--max-pages` queda como salvaguarda para backfills o
escaneos completos.

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

No uses `--max-activities` en la automatización diaria. El modo incremental ya
corta por fecha al llegar a la ventana de solape; limitar artificialmente las
actividades puede dejar pendientes si se acumulan varios días sin sincronizar.

Para ejecutar solo la parte offline sobre raw ya descargado:

```bash
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Con `--skip-fetch` no se llama a Garmin Connect. Solo se reconstruyen
normalizados y consolidados desde raw ya existente, incluyendo
`athletes.jsonl`, `equipment.jsonl` y `measurements.jsonl`.

## Opciones

```bash
./.venv/bin/python -m nono_sports garmin sync --force
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
./.venv/bin/python -m nono_sports garmin sync --skip-fit
./.venv/bin/python -m nono_sports garmin sync --include-gpx
./.venv/bin/python -m nono_sports garmin sync --include-tcx
./.venv/bin/python -m nono_sports garmin sync --skip-measurements
./.venv/bin/python -m nono_sports garmin sync --skip-user-data
./.venv/bin/python -m nono_sports garmin sync --lock-file /ruta/garmin.lock
```

Para depuración excepcional puede conservar los derivados intermedios generados
por actividades que se reprocesen:

```bash
./.venv/bin/python -m nono_sports garmin sync --keep-intermediate-files
./.venv/bin/python -m nono_sports garmin normalize --keep-intermediate-files
```

No debe usarse en la operación diaria: `fit_decoded/*.fitdecode.json` puede
ocupar decenas de MB por actividad.

Los comandos parciales siguen disponibles para diagnóstico:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activities --force
./.venv/bin/python -m nono_sports garmin fetch-activities --skip-fit
./.venv/bin/python -m nono_sports garmin fetch-activities --include-gpx
./.venv/bin/python -m nono_sports garmin fetch-activities --include-tcx
./.venv/bin/python -m nono_sports garmin fetch-user-data
```

## Salida raw

La estructura inicial es:

```text
10_fuentes/garmin_connect/
├── raw/
│   ├── manifest.jsonl
│   ├── athlete/profile.json
│   ├── athlete/settings.json
│   ├── activities_index_<start>.json
│   ├── activities/<id>.json
│   ├── activities/<id>.details.json
│   ├── activity_files/<id>.original.zip
│   ├── activity_files/<id>.fit
│   ├── activity_files/<id>.gpx
│   ├── activity_files/<id>.tcx
│   ├── gear/gear.json
│   ├── gear/activity_<id>.json
│   ├── gear/stats/<gear_id>.json
│   ├── devices/devices.json
│   ├── fit_decoded/<id>.fitdecode.json  # solo diagnóstico explícito
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

El flujo habitual `garmin sync` decodifica cada FIT de forma transitoria durante
la normalización. No conserva `fit_decoded/*.fitdecode.json`, porque estos
derivados son muy voluminosos y siempre pueden reconstruirse desde el FIT raw.
El FIT original es la entrada estable de la huella incremental.

```bash
./.venv/bin/python -m nono_sports garmin decode-fit --activity-id <id>
```

`decode-fit` queda reservado para diagnóstico o investigación de una actividad
concreta. El CLI exige `--activity-id` para evitar generar cientos de archivos
grandes por accidente. Sus archivos pueden eliminarse después de utilizarlos sin
invalidar los datos normalizados.

Si se borra un `fit_decoded` histórico, la siguiente normalización incremental
reutiliza el normalizado existente y elimina referencias rotas al derivado,
apuntando los streams al FIT original cuando procede. No hace falta usar
`--force` para limpiar esos enlaces.

Para limpiar intermedios:

```bash
./.venv/bin/python -m nono_sports garmin clean-intermediates --activity-id <id>
./.venv/bin/python -m nono_sports garmin clean-intermediates
./.venv/bin/python -m nono_sports garmin clean-intermediates --dry-run
```

La limpieza elimina `raw/fit_decoded/*.fitdecode.json`. No elimina raw original
ni normalizados.

## Rehidratar equipación por actividad

El `sync` descarga `activity_gear` para actividades nuevas. Si hay actividades
antiguas que ya estaban descargadas antes de incorporar ese dato, no hace falta
hacer un full scan ni volver a descargar FIT. Usa:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activity-gear --local-only
```

Ese comando solo repara el estado si ya existe
`raw/gear/activity_<id>.json`. No llama a Garmin Connect.

Para descargar `activity_gear` pendiente en lotes pequeños:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activity-gear --max-activities 50
```

Para una actividad concreta:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activity-gear \
  --activity-id <garmin_activity_id>
```

Después reconstruye offline:

```bash
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Este proceso solo descarga `raw/gear/activity_<id>.json`, actualiza
`logs/activity_sync_state.json` y permite que el consolidado de equipación sume
distancias y horas de uso desde actividades sin duplicar Strava/Garmin.

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

La normalización es incremental y de bajo consumo de memoria: guarda
fingerprints por actividad en `normalizado/state.json` y reutiliza los registros
ya normalizados si el raw/FIT no ha cambiado. Cuando reutiliza un stream previo,
lo lee por offset desde `streams.jsonl`, actividad por actividad, en vez de
cargar el fichero completo. En la salida:

- `athletes.jsonl`: perfil/settings Garmin normalizados.
- `equipment.jsonl`: equipación declarada y dispositivos Garmin.
- `processed`: actividades recalculadas desde raw/FIT.
- `reused`: actividades reutilizadas sin volver a leer FIT decodificado.
- `streams_index.jsonl` y `state.json` forman parte del contrato mínimo común
  de normalizados por fuente, igual que en Strava.

Usa `--force` solo si quieres recalcular todo:

```bash
./.venv/bin/python -m nono_sports garmin normalize --force
./.venv/bin/python -m nono_sports garmin sync --skip-fetch --force
```

Cuando no hay FIT pero sí GPX/TCX, la normalización extrae el track XML con
`defusedxml` y genera `streams.jsonl` desde esos puntos. El registro de actividad
queda con `has_fit=false`, `has_gpx`/`has_tcx` según proceda,
`complete_without_fit=true` y `stream_uid` si el track contiene puntos.

También conserva pistas de procedencia en `sport_specific`:

- `original_file_format`: formato declarado por Garmin, por ejemplo `gpx`
- `is_original`: valor bruto `metadataDTO.isOriginal`
- `source_origin`: clasificación derivada, por ejemplo `imported_gpx`

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

Los ficheros `laps.jsonl`, `splits.jsonl`, `typed_splits.jsonl` y
`segment_candidates.jsonl` son extensiones específicas de Garmin Connect. No
implican que Strava o futuras fuentes tengan que crear ficheros vacíos: el
contrato común está en `activities.jsonl`, `streams.jsonl`,
`streams_index.jsonl`, `state.json` y `logs/activity_sync_state.json`.

## Mediciones Garmin Connect

Garmin Connect también aporta mediciones puntuales, empezando por peso y
composición corporal. La descarga raw usa endpoints de rango de fechas:

```bash
./.venv/bin/python -m nono_sports garmin fetch-measurements \
  --start-date 2023-01-01 \
  --end-date 2026-07-12
```

Para un backfill completo:

```bash
./.venv/bin/python -m nono_sports garmin fetch-measurements \
  --full-measurement-scan
```

`garmin sync` incluye esta descarga por defecto con una ventana incremental y
solape de 30 días. Si alguna operación excepcional no debe tocar mediciones,
puede usarse `--skip-measurements`.

Si el tokenstore Garmin ha caducado o Garmin exige reautenticación:

```bash
./.venv/bin/python -m nono_sports garmin auth
```

Salidas:

```text
10_fuentes/garmin_connect/raw/biometrics/*.json
10_fuentes/garmin_connect/logs/measurement_sync_state.json
10_fuentes/garmin_connect/normalizado/measurements.jsonl
10_fuentes/garmin_connect/normalizado/measurements_state.json
20_consolidado/measurements.jsonl
20_consolidado/measurement_sources.jsonl
20_consolidado/measurements_state.json
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
- normalización/consolidación optimizadas para no cargar `streams.jsonl`
  completo en memoria durante la operación diaria.
- actividad importada Garmin `18858207006`: el ZIP `ORIGINAL` contenía
  `18858207006_ACTIVITY.gpx`, sin FIT; el sistema descargó GPX/TCX fallback y
  dejó la descarga raw con `0 recoverable errors`.
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
- para backfill manual, usar límites acotados solo de forma explícita, por
  ejemplo `garmin sync --limit 20 --max-activities 1 --max-pages 100`, y
  esperar entre ejecuciones
