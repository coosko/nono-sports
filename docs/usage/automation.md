# Automatización controlada

Esta guía define la ejecución repetible de Strava v1 y Garmin Connect v1 en
Nono.

## Comando recomendado Strava

Para el día a día:

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports strava sync \
  --max-read-requests-15min 100 \
  --max-read-requests-daily 1000 \
  --rate-limit-reserve 10 \
  --schedule-next-if-pending \
  --schedule-delay-minutes 20 \
  --lock-file /home/nono/.local/state/nono-sports/strava-sync.lock
```

El comando ejecuta:

- descarga incremental raw de actividades
- normalización Strava
- consolidación inicial
- validación offline e informe
- reprogramación adaptativa si quedan actividades pendientes y queda cuota diaria

Si quieres ejecutar solo la parte offline, sin llamar a Strava:

```bash
./.venv/bin/python -m nono_sports strava sync --skip-fetch
```

## Salvaguardas de rate limit

La descarga usa límites preventivos:

- límite de lectura cada 15 minutos
- límite de lectura diario
- reserva de seguridad antes del límite efectivo
- respeto del menor valor entre la configuración local y las cabeceras reportadas por Strava

Importante: en un proceso nuevo no se conoce el uso real de Strava hasta recibir la primera respuesta con cabeceras de rate limit. Si la cuota diaria ya está agotada o casi agotada, el comando puede consumir una única llamada para conocer el estado y detenerse antes de continuar. Esto es aceptable y evita descargas largas fuera de presupuesto.

## Reprogramación adaptativa

El modo recomendado usa `--schedule-next-if-pending`.

Al final de cada ejecución:

- si no quedan descargas pendientes de actividad, termina
- si la validación falla, termina
- si no hay cabecera de rate limit, termina
- si la cuota diaria está cerca del límite, termina
- si quedan pendientes y hay cuota diaria suficiente, programa una única ejecución adicional para dentro de 20 minutos con `systemd-run --user`

Esto evita tener un timer cada 15 minutos funcionando siempre. En régimen normal, el timer diario ejecuta una vez y termina. En una puesta al día histórica, el propio comando va encadenando tandas hasta que no haya pendientes o hasta acercarse al límite diario.

Desde el ajuste realizado por Nono el 2026-06-25, la reprogramación adaptativa
solo considera trabajo descargable estos hallazgos de validación:

- `raw.activities_incomplete`: Strava ha listado actividades que aún no tienen
  detalle raw local.
- `state.activities_pending_completion`: hay actividades en el estado sin marca
  de completado.
- `state.segments_pending`: hay actividades con detalle pendiente de revisar
  segmentos.

No se reprograma otra ejecución solo por `raw.streams_incomplete`,
`raw.laps_incomplete` o `raw.recoverable_errors`. En particular, streams que
Strava responde como `404 Resource Not Found` y zonas que responde como
`402 Payment Required` deben tratarse como datos no disponibles, no como trabajo
pendiente que se vaya a arreglar consumiendo más cuota.

Cada ejecución adaptativa se crea con un sufijo único en la unidad transient de
`systemd-run`. Esto evita colisiones con unidades previas ya ejecutadas o
pendientes.

`--lock-file` evita solapes entre la ejecución diaria y una ejecución adaptativa pendiente.

## Comando recomendado Garmin Connect

Para una actualización controlada de Garmin Connect:

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports garmin sync \
  --lock-file /home/nono/.local/state/nono-sports/garmin-sync.lock
```

El comando ejecuta:

- listado incremental de actividades recientes
- descarga raw de actividades pendientes
- descarga incremental de mediciones Garmin Connect de peso/composición
- normalización Garmin Connect
- normalización de actividades GPX manuales y mediciones manuales si existen
- consolidación multi-fuente

La normalización y la validación procesan los JSONL grandes en streaming. En
particular, el flujo diario no debe cargar `normalizado/streams.jsonl` completo
en memoria; Garmin reutiliza streams previos por offsets y Strava escribe los
streams línea a línea cuando se reconstruye offline.

Cada ejecución de pipeline escribe además un resumen operativo local en:

```text
~/.local/state/nono-sports/logs/operation_runs.jsonl
```

Este fichero no está en Drive. Sirve para auditar cómo se ejecutó el comando en
ese host: fases, duración, conteos, estado final y errores si los hay. Los
ficheros `10_fuentes/<fuente>/logs/*_sync_state.json` siguen siendo estados de
sincronización del dataset y deben permanecer en Drive.

Garmin Connect no expone, mediante `garminconnect==0.3.6`, un filtro fiable de
"modificadas desde". El comando usa `last_successful_activity_sync_at` y un
solape por defecto de 7 días para cortar el listado cuando llega a actividades
anteriores a la ventana incremental.

El modo diario no debe limitar `--max-activities` ni `--max-pages`: el propio
incremental corta al llegar a actividades anteriores a la ventana de solape.
Esos límites quedan para pruebas, backfills manuales o auditorías controladas.

Opciones operativas:

```bash
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
./.venv/bin/python -m nono_sports garmin sync --full-scan
./.venv/bin/python -m nono_sports garmin sync --incremental-lookback-days 14
./.venv/bin/python -m nono_sports garmin fetch-measurements --full-measurement-scan
```

`--skip-fetch` solo reconstruye normalizado y consolidado desde raw local.
`--full-scan` se reserva para backfills o auditorías. `--force` requiere
confirmación explícita porque puede reprocesar mucho histórico, aunque ya no
debe crear derivados FIT masivos ni cargar todos los streams a la vez.

Las mediciones usan opciones propias porque Garmin trabaja por fechas y no por
timestamp Unix de actividad:

```bash
./.venv/bin/python -m nono_sports garmin fetch-measurements \
  --start-date 2023-01-01 \
  --end-date 2026-07-12
```

En el modo diario, `garmin sync` incluye mediciones salvo que se indique
`--skip-measurements`.

Las actividades GPX importadas manualmente no requieren una llamada diaria
propia. Si existen en `10_fuentes/manual/raw/activities/`, `garmin sync` las
normaliza de nuevo antes de reconstruir el consolidado. Para importar un GPX
nuevo se usa el comando explícito documentado en
`docs/usage/manual-activity-imports.md`.

El flujo normal no conserva `raw/fit_decoded/*.fitdecode.json`. Si se genera un
derivado de diagnóstico para una actividad concreta, límpialo después:

```bash
./.venv/bin/python -m nono_sports garmin clean-intermediates --activity-id <id>
```

## Servicio systemd de usuario

Desde el 2026-07-10, la automatización activa en Nono debe ser Garmin Connect.
Strava queda como histórico y su timer no debe activarse mientras la API siga
sin ser fuente operativa fiable.

Crear el servicio Garmin:

```bash
mkdir -p /home/nono/.config/systemd/user
nano /home/nono/.config/systemd/user/nono-sports-garmin-sync.service
```

Contenido:

```ini
[Unit]
Description=Nono Sports Garmin Connect controlled sync
ConditionPathIsDirectory=/home/nono/drive/01_ambitos/02_personal/40_deporte

[Service]
Type=oneshot
WorkingDirectory=/home/nono/apps/nono-sport
ExecStart=/home/nono/apps/nono-sport/.venv/bin/python -m nono_sports garmin sync --lock-file /home/nono/.local/state/nono-sports/garmin-sync.lock
```

Crear el timer:

```bash
nano /home/nono/.config/systemd/user/nono-sports-garmin-sync.timer
```

Contenido:

```ini
[Unit]
Description=Run Nono Sports Garmin Connect sync daily

[Timer]
OnCalendar=*-*-* 19:50:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Activar:

```bash
systemctl --user daemon-reload
systemctl --user enable --now nono-sports-garmin-sync.timer
systemctl --user list-timers nono-sports-garmin-sync.timer
```

Si el timer debe ejecutarse aunque el usuario `nono` no tenga sesión abierta, ejecutar una vez con privilegios:

```bash
sudo loginctl enable-linger nono
```

## Logs

Ver últimas ejecuciones:

```bash
journalctl --user -u nono-sports-garmin-sync.service -n 100 --no-pager
```

Ver el último resumen operativo estructurado:

```bash
tail -n 1 /home/nono/.local/state/nono-sports/logs/operation_runs.jsonl
```

Seguir logs en vivo:

```bash
journalctl --user -u nono-sports-garmin-sync.service -f
```

El informe de validación se escribe siempre en:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/30_analisis/informes/strava_validation_report.md
```

## Webhooks futuros

La v1 no instala listener público.

Si se añaden webhooks más adelante:

- el listener debe tener el mínimo privilegio posible
- el listener no debería tener tokens Strava si solo recibe eventos
- la descarga real debería delegarse en el mismo pipeline controlado
- si otro usuario escribe en Drive, habrá que introducir grupo compartido o ACLs explícitas
