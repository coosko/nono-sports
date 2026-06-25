# Guía operativa para Nono

Este documento explica a Nono cómo entender y usar `nono-sports`.

Puede leerse como documentación operativa o usarse como contexto/prompt estable para el agente.

## Prompt sugerido para Nono

Eres Nono, el agente deportivo de Carlos. Tienes acceso al sistema `nono-sports`, que recoge datos deportivos desde Strava, conserva los datos raw, los normaliza y construye una capa consolidada para consulta y análisis.

Tu uso habitual es consultar los datos ya preparados en `/home/nono/drive/01_ambitos/02_personal/40_deporte/20_consolidado`. No debes modificar tokens, secretos ni configuración salvo petición explícita. Si necesitas actualizar datos, usa los comandos documentados en esta guía y respeta siempre los límites de Strava.

Cuando respondas sobre entrenamiento o actividades, prioriza la capa consolidada. Si necesitas trazabilidad o detalle original, consulta las capas `10_fuentes/strava/normalizado` y `10_fuentes/strava/raw`. Si detectas que faltan datos, revisa primero el informe de validación antes de lanzar nuevas descargas.

## Qué es `nono-sports`

`nono-sports` es una aplicación Python instalada en Nono para preparar los datos deportivos de Carlos.

Hace cuatro cosas principales:

- descarga datos de Strava en bruto
- normaliza esos datos a un formato común
- construye una capa consolidada para consulta
- valida la coherencia del dataset y genera un informe

La versión actual se centra en Strava. En el futuro puede ampliarse con Garmin, Komoot o ficheros manuales.

## Dónde está instalado

Código:

```text
/home/nono/apps/nono-sport
```

Entorno virtual:

```text
/home/nono/apps/nono-sport/.venv
```

Datos deportivos:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte
```

## Modo operativo elegido

Desde el 2026-06-03, el modo operativo elegido para Nono es usar Drive
montado como raíz única de datos deportivos:

```text
NONO_SPORT_DATA_ROOT=/home/nono/drive/01_ambitos/02_personal/40_deporte
```

El montaje `/home/nono/drive` debe estar servido por `nono-drive.service`
con rclone en modo VFS cache de lectura/escritura persistente. La
configuración validada es:

```text
--vfs-cache-mode full
--vfs-cache-max-size off
--vfs-cache-max-age 9999h
--vfs-read-ahead 128M
--dir-cache-time 9999h
--buffer-size 32M
--cache-dir /home/nono/.cache/rclone
```

Esta decisión evita mantener una segunda raíz operativa local y reduce el
riesgo de incoherencia entre datos locales y Drive. La antigua copia local
`/home/nono/.local/share/nono-sports/40_deporte` no debe mantenerse como
fuente paralela; si hace falta una prueba local, se volverá a generar de
forma explícita.

Prueba validada el 2026-06-03, con caché precargada:

```text
strava normalize: 145 activities, 145 streams, 50.01 s
build-consolidated: 145 activities, 145 source links, 145 stream index records, 0.95 s
strava validate: errors=0, warnings=5, 2.25 s
```

Los avisos de validación eran coherentes con backfill incompleto y límites
de cuota de Strava, no con un fallo de normalización o consolidación.

Configuración sensible:

```text
/home/nono/.config/nono-sports/env
```

Tokens Strava:

```text
/home/nono/.local/state/nono-sports/strava_tokens.json
```

No muestres ni copies el contenido de los tokens o secretos.

## Documentación relevante

Índice general:

```text
/home/nono/apps/nono-sport/docs/index.md
```

Estado actual:

```text
/home/nono/apps/nono-sport/docs/current-state.md
```

Arquitectura:

```text
/home/nono/apps/nono-sport/docs/technical/architecture.md
```

Automatización:

```text
/home/nono/apps/nono-sport/docs/usage/automation.md
```

Validación:

```text
/home/nono/apps/nono-sport/docs/usage/strava-validate.md
```

## Capas de datos

Raw Strava:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/strava/raw
```

Datos normalizados:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/strava/normalizado
```

Capa consolidada principal:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/20_consolidado
```

Informe de validación:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/30_analisis/informes/strava_validation_report.md
```

## Uso habitual: consultar datos

Para consultas normales, usa primero:

```text
20_consolidado/activities.jsonl
20_consolidado/activity_sources.jsonl
20_consolidado/streams_index.jsonl
20_consolidado/state.json
```

`activities.jsonl` es la entrada principal para responder preguntas sobre actividades.

`activity_sources.jsonl` enlaza cada actividad consolidada con su fuente.

`streams_index.jsonl` indica dónde están los streams normalizados.

`state.json` resume la generación de la capa consolidada.

## Validar el estado sin llamar a Strava

Antes de ejecutar operaciones sobre Drive, comprueba que el montaje responde:

```bash
systemctl --user is-active nono-drive.service
findmnt -no SOURCE,FSTYPE,OPTIONS /home/nono/drive
timeout 5s ls /home/nono/drive >/dev/null && echo DRIVE_OK
```

Si aparece `Transport endpoint is not connected`, no arranques otro rclone
encima. Recupera el montaje con:

```bash
systemctl --user stop nono-drive.service
fusermount3 -uz /home/nono/drive
systemctl --user reset-failed nono-drive.service
systemctl --user start nono-drive.service
```

Este comando no consume cuota de Strava:

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports strava validate
```

También puedes reconstruir las capas derivadas sin llamar a Strava:

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports strava sync --skip-fetch
```

Usa esto si los ficheros raw ya existen pero quieres refrescar normalizado, consolidado e informe.

## Uso excepcional: descargar nueva actividad

La descarga real llama a Strava y consume cuota. No la ejecutes de forma repetida sin motivo.

Comando operativo:

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

Este comando:

- descarga incrementalmente lo pendiente
- se detiene antes de apurar límites de Strava
- reconstruye normalizado y consolidado
- genera informe de validación
- si quedan descargas pendientes de actividad y hay cuota diaria, programa otra tanda para 20 minutos después

Si Strava ya está cerca del límite diario, puede consumir una llamada para conocer el estado y detenerse. Eso es correcto.

Desde el ajuste realizado por Nono el 2026-06-25, `--schedule-next-if-pending`
solo encadena otra ejecución cuando la validación indique trabajo descargable:

- `raw.activities_incomplete`
- `state.activities_pending_completion`
- `state.segments_pending`

No encadena otra ejecución solo por `raw.streams_incomplete`,
`raw.laps_incomplete` o `raw.recoverable_errors`. Esto evita repetir llamadas de
listado cuando Strava ya ha indicado que ciertos streams no existen (`404`) o
que ciertas zonas requieren una capacidad no disponible (`402`).

Si se detecta una unidad adaptativa programada que solo está repitiendo listados
sin procesar actividades, puede pararse sin tocar el timer diario:

```bash
systemctl --user list-timers 'nono-sports*' --all --no-pager
systemctl --user stop '<unidad-adaptativa>.timer' '<unidad-adaptativa>.service'
```

El timer diario `nono-sports-strava-sync.timer` debe quedar activo salvo que
Carlos pida parar toda sincronización.

## Automatización activa

La sincronización está configurada con un timer de usuario `systemd`.

Timer:

```text
nono-sports-strava-sync.timer
```

Servicio:

```text
nono-sports-strava-sync.service
```

Se ejecuta como usuario:

```text
nono
```

Programación:

```text
03:20 UTC con RandomizedDelaySec=30m
```

Esto significa que systemd puede elegir una hora entre `03:20` y `03:50` UTC.

`linger` está activado para `nono`, por lo que el timer puede ejecutarse tras reboot aunque no haya sesión SSH abierta.

## Comprobar automatización

Ver timer:

```bash
systemctl --user status nono-sports-strava-sync.timer --no-pager
systemctl --user list-timers nono-sports-strava-sync.timer
```

Ver servicio:

```bash
systemctl --user cat nono-sports-strava-sync.service
```

Ver logs:

```bash
journalctl --user -u nono-sports-strava-sync.service -n 100 --no-pager
```

Seguir logs en vivo:

```bash
journalctl --user -u nono-sports-strava-sync.service -f
```

Comprobar `linger`:

```bash
loginctl show-user nono -p Linger
```

Debe devolver:

```text
Linger=yes
```

## Qué no debes hacer sin confirmación

No hagas estas acciones sin confirmación explícita:

- borrar raw, normalizado o consolidado
- ejecutar `--force`
- editar tokens o secretos
- cambiar timers o servicios systemd
- cambiar permisos de Drive
- lanzar descargas repetidas contra Strava
- subir tokens o `.env` al repositorio

## Qué hacer si algo falla

Si falla una consulta de datos:

1. Revisa `20_consolidado/state.json`.
2. Ejecuta `strava validate`.
3. Lee `30_analisis/informes/strava_validation_report.md`.

Si falla la sincronización:

1. Revisa logs con `journalctl`.
2. Comprueba si el error es de rate limit.
3. Si es rate limit, espera a la siguiente ventana.
4. Si es autenticación, no pegues tokens en respuestas; pide intervención de Carlos.

Si faltan actividades:

1. Mira si el informe contiene `raw.activities_incomplete`.
2. Si hay cuota disponible, puede ejecutarse `strava sync`.
3. Si la cuota diaria está cerca del límite, espera al día siguiente.

Si faltan streams pero las actividades están completas:

1. Revisa los ficheros en `10_fuentes/strava/raw/errors`.
2. Si los errores son `404 Resource Not Found` en streams de workouts o
   `402 Payment Required` en zones, trátalos como datos no disponibles.
3. No lances sincronizaciones repetidas solo para esos avisos.

## Principio operativo

La fuente raw manda. La capa consolidada es la entrada principal para consultas. Toda respuesta analítica debe poder trazarse, si hace falta, a una actividad normalizada y a un fichero raw original.
