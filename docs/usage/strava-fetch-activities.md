# Descarga raw de actividades Strava

Este documento describe la descarga raw de actividades con el máximo detalle previsto para Strava v1 sin consumir endpoints de pago por defecto. No escribe nada en Strava.

## Requisitos previos

- haber completado `docs/usage/strava-auth.md`
- haber ejecutado opcionalmente `docs/usage/strava-fetch-context.md`
- tener `.env` configurado con `NONO_SPORT_DATA_ROOT`, `STRAVA_CLIENT_ID` y `STRAVA_CLIENT_SECRET`
- tener tokens guardados en `~/.local/state/nono-sports/strava_tokens.json`

## Comando completo

```bash
./.venv/bin/python -m nono_sports strava fetch-activities
```

El comando:

- lista todas las actividades disponibles desde `GET /athlete/activities`
- guarda el listado en `10_fuentes/strava/raw/activities/activities.json`
- descarga detalle completo por actividad desde `GET /activities/{id}`
- descarga laps por actividad desde `GET /activities/{id}/laps`
- descarga streams por actividad desde `GET /activities/{id}/streams`
- descarga detalle del gear referenciado por cada actividad
- descarga segmentos referenciados por la actividad y sus streams
- registra errores recuperables en `10_fuentes/strava/raw/errors/`
- mantiene estado reanudable en `10_fuentes/strava/logs/activity_sync_state.json`

No descarga zonas de actividad por defecto. Strava documenta `GET /activities/{id}/zones` como **Summit Feature**, por lo que puede devolver `402 Payment Required` en cuentas sin esa funcionalidad.

## Prueba controlada

Para probar con pocas actividades antes de lanzar la descarga completa:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --max-activities 3
```

`--max-activities` limita el número de actividades pendientes que se procesan en esa ejecución. Si ya hay actividades completadas en el estado, se saltan y el lote continúa con las siguientes pendientes.

## Reanudar

Si una ejecución se interrumpe, vuelve a lanzar el mismo comando. Las actividades ya completadas se saltan si sus ficheros siguen existiendo.

```bash
./.venv/bin/python -m nono_sports strava fetch-activities
```

Si Strava devuelve `429 Too Many Requests`, el proceso guarda el estado y termina de forma controlada. Reanuda más tarde con el mismo comando o con otro lote.

Además, el comando lleva una protección preventiva por defecto para no apurar los límites de lectura:

- máximo configurado de `100` peticiones de lectura cada 15 minutos
- máximo configurado de `1000` peticiones de lectura al día
- reserva de seguridad de `5` peticiones antes del límite efectivo
- si Strava informa límites menores en sus cabeceras, se respeta el menor de ambos valores

Strava documenta dos límites por aplicación: el límite global por defecto (`200` cada 15 minutos y `2000` al día) y un límite separado para endpoints de lectura o "non-upload" (`100` cada 15 minutos y `1000` al día). La descarga de actividades usa endpoints de lectura, por lo que el límite operativo de este proceso es `100/1000`.

Cuando se alcanza el umbral preventivo, el proceso termina con `Stopped early: rate_limit_budget:...` antes de enviar la siguiente petición. El estado queda guardado para reanudar más tarde sin repetir partes ya completadas.

Para el modo prudente de descarga actividad a actividad:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --max-activities 1
```

Después espera al siguiente bloque de 15 minutos antes de repetir. Si una actividad requiere muchas llamadas por sus segmentos, el proceso puede parar a media actividad; al reanudar continuará con lo pendiente gracias a `logs/activity_sync_state.json`.

Para avanzar por lotes:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --max-activities 25
```

Para rehacer todo lo ya descargado:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --force
```

## Filtros temporales

Strava acepta marcas de tiempo Unix:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --after 1714521600 --before 1717200000
```

## Zonas de actividad

Las zonas de actividad son opcionales y requieren funcionalidad Summit/suscripción en Strava. Solo se intentan descargar si lo pides explícitamente:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --include-zones
```

Si Strava responde `402 Payment Required`, el error se registra en `raw/errors/` y la descarga continúa.

## Opciones de contención

Si quieres evitar la descarga de streams:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --skip-streams
```

Para contener llamadas en una ejecución puntual:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities --skip-laps
./.venv/bin/python -m nono_sports strava fetch-activities --skip-gear
./.venv/bin/python -m nono_sports strava fetch-activities --skip-segments
./.venv/bin/python -m nono_sports strava fetch-activities --skip-segment-streams
```

Para ajustar la protección de límites:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities \
  --max-read-requests-15min 100 \
  --max-read-requests-daily 1000 \
  --rate-limit-reserve 5
```

## Validación manual

Después de ejecutar el comando completo, revisa:

- que `activities/activities.json` existe
- que hay un fichero `activities/<id>.json` para cada actividad esperada
- que hay ficheros `laps/<id>.json`
- que hay ficheros `streams/<id>.json`, salvo que se haya usado `--skip-streams`
- que aparecen `gear/<id>.json` y `segments/<id>.json` cuando las actividades los referencian
- que solo hay ficheros `zones/<id>.json` si se ha usado `--include-zones`
- que `logs/activity_sync_state.json` refleja actividades completadas o errores recuperables
- que `raw/errors/`, si contiene ficheros, solo refleja actividades inaccesibles o datos opcionales no disponibles

Referencia oficial: `GET /activities/{id}/zones` aparece como **Summit Feature** en la Strava API Reference.
