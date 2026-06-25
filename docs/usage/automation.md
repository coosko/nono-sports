# Automatización controlada

Esta guía define la ejecución repetible de Strava v1 en Nono.

## Comando recomendado

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

## Servicio systemd de usuario

Crear el servicio:

```bash
mkdir -p /home/nono/.config/systemd/user
nano /home/nono/.config/systemd/user/nono-sports-strava-sync.service
```

Contenido:

```ini
[Unit]
Description=Nono Sports Strava controlled sync
ConditionPathIsDirectory=/home/nono/drive/01_ambitos/02_personal/40_deporte

[Service]
Type=oneshot
WorkingDirectory=/home/nono/apps/nono-sport
ExecStart=/home/nono/apps/nono-sport/.venv/bin/python -m nono_sports strava sync --max-read-requests-15min 100 --max-read-requests-daily 1000 --rate-limit-reserve 10 --schedule-next-if-pending --schedule-delay-minutes 20 --lock-file /home/nono/.local/state/nono-sports/strava-sync.lock
```

Crear el timer:

```bash
nano /home/nono/.config/systemd/user/nono-sports-strava-sync.timer
```

Contenido:

```ini
[Unit]
Description=Run Nono Sports Strava sync daily

[Timer]
OnCalendar=*-*-* 03:20:00
Persistent=true
RandomizedDelaySec=30m

[Install]
WantedBy=timers.target
```

Activar:

```bash
systemctl --user daemon-reload
systemctl --user enable --now nono-sports-strava-sync.timer
systemctl --user list-timers nono-sports-strava-sync.timer
```

Si el timer debe ejecutarse aunque el usuario `nono` no tenga sesión abierta, ejecutar una vez con privilegios:

```bash
sudo loginctl enable-linger nono
```

## Logs

Ver últimas ejecuciones:

```bash
journalctl --user -u nono-sports-strava-sync.service -n 100 --no-pager
```

Seguir logs en vivo:

```bash
journalctl --user -u nono-sports-strava-sync.service -f
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
