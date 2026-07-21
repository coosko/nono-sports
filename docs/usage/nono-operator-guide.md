# Guía operativa para Nono

Este documento explica a Nono cómo entender y usar `nono-sports`.

Puede leerse como documentación operativa o usarse como contexto/prompt estable para el agente.

## Prompt sugerido para Nono

Eres Nono, el agente deportivo de Carlos. Tienes acceso al sistema `nono-sports`, que recoge datos deportivos desde Strava y Garmin Connect, conserva los datos raw, los normaliza y construye una capa consolidada para consulta y análisis.

Tu uso habitual es consultar los datos ya preparados en `/home/nono/drive/01_ambitos/02_personal/40_deporte/20_consolidado`. No debes modificar tokens, secretos ni configuración salvo petición explícita. Si necesitas actualizar datos, usa los comandos documentados en esta guía y respeta siempre los límites de Strava y las llamadas a Garmin Connect.

Cuando respondas sobre entrenamiento o actividades, prioriza la capa consolidada. Si necesitas trazabilidad o detalle original, consulta las capas `10_fuentes/<fuente>/normalizado` y `10_fuentes/<fuente>/raw`. Garmin Connect suele ser la fuente original del dispositivo y puede aportar FIT, sensores, laps, splits, typed splits, weather, perfil, dispositivos y equipación usada por actividad; Strava puede aportar segmentos, rutas, gear y compatibilidad histórica. Si detectas que faltan datos, revisa primero el estado local antes de lanzar nuevas descargas.

## Qué es `nono-sports`

`nono-sports` es una aplicación Python instalada en Nono para preparar los datos deportivos de Carlos.

Hace cuatro cosas principales:

- descarga datos de Strava en bruto
- descarga datos de Garmin Connect en bruto
- normaliza esos datos a un formato común
- construye una capa consolidada para consulta
- valida la coherencia del dataset y genera un informe

La versión actual tiene Strava v1 y Garmin Connect v1 operativos. En el futuro puede ampliarse con Komoot o ficheros manuales.

## Fuentes auxiliares para planificar rutas

`nono-sports` no ingiere todavía rutas externas como fuente normalizada, pero
Nono puede usar herramientas externas para preparar propuestas de salida.

Desde el 2026-06-25, Wikiloc queda validado como fuente secundaria para
descubrir rutas reales de senderismo, paseos, ciclismo, gravel, MTB y otras
actividades al aire libre. Su uso operativo recomendado es:

- Wikiloc: descubrir candidatos, tracks, desnivel, waypoints y fotos.
- Open-Meteo: validar lluvia, calor, viento, horas razonables y riesgos
  meteorológicos.
- Google Maps: validar accesos, tiempo de desplazamiento, aparcamiento y
  logística real.
- Datos deportivos consolidados de Carlos: ajustar distancia, desnivel y
  exigencia a la forma física reciente, carga acumulada, descanso y objetivo.
- Fuentes oficiales: contrastar cierres, permisos, riesgo de incendio,
  normativa de parques o cualquier decisión con implicaciones de seguridad.

Wikiloc es contenido comunitario. No debe tratarse como fuente única ni como
verdad operativa: una ruta puede estar desactualizada, mal clasificada, pasar
por terrenos privados, tener tramos cortados o incluir pasos más difíciles de
lo que aparenta. Para planes con familia, calor, montaña, poca luz o zonas
aisladas, ser conservador.

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

Tokenstore Garmin Connect:

```text
/home/nono/.local/state/nono-sports/garmin_connect/tokenstore/
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

Sincronización Garmin Connect:

```text
/home/nono/apps/nono-sport/docs/usage/garmin-fetch-activities.md
```

## Capas de datos

Raw Strava:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/strava/raw
```

Raw Garmin Connect:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/garmin_connect/raw
```

Fuentes manuales:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/manual/biometria/mediciones_carlos.csv
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/manual/sensaciones
```

La biometria manual conserva mediciones comparables como peso y frecuencia
cardiaca en reposo. Las sensaciones conservan notas declaradas por Carlos
sobre salidas, recuperacion, fatiga, alimentacion, hidratacion, molestias,
disfrute o intencion de entrenamiento. Los documentos de `30_analisis`
pueden resumir o interpretar estas fuentes, pero no deben ser la fuente
primaria.

Datos normalizados:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/strava/normalizado
/home/nono/drive/01_ambitos/02_personal/40_deporte/10_fuentes/garmin_connect/normalizado
```

Cada fuente normalizada debe exponer, como mínimo:

```text
normalizado/athletes.jsonl
normalizado/equipment.jsonl
normalizado/activities.jsonl
normalizado/streams.jsonl
normalizado/streams_index.jsonl
normalizado/state.json
logs/activity_sync_state.json
```

No todas las fuentes tienen que tener datos en todos los ficheros, pero los
nombres comunes se mantienen para facilitar consulta y automatización. Garmin
Connect puede tener además `laps.jsonl`, `splits.jsonl`,
`typed_splits.jsonl` y `segment_candidates.jsonl`. Para responder a consultas
normales, prioriza siempre `20_consolidado`.

Capa consolidada principal:

```text
/home/nono/drive/01_ambitos/02_personal/40_deporte/20_consolidado
```

Para actividades, consulta:

```text
20_consolidado/activities.jsonl
20_consolidado/activity_sources.jsonl
20_consolidado/streams_index.jsonl
```

Para perfil de atleta y equipación, consulta:

```text
20_consolidado/athletes.jsonl
20_consolidado/athlete_sources.jsonl
20_consolidado/equipment.jsonl
20_consolidado/equipment_sources.jsonl
```

`equipment.jsonl` agrupa material equivalente entre fuentes cuando coinciden
tipo y nombre. Usa `equipment_sources.jsonl` para ver qué información procede
de Strava, Garmin Connect o una fuente manual futura.

En `equipment.jsonl`, `distance_m` es la distancia efectiva consolidada cuando
hay actividades con enlace de equipación. Para auditoría, revisa
`attributes.usage`: ahí están la estrategia, parciales por fuente, horas de uso,
distancia base declarada por la fuente y actividades que no se pudieron asignar
por falta de enlace de equipación.

Si una bici o dispositivo parece tener menos uso del esperado y hay actividades
Garmin antiguas sin `activity_gear`, se puede rehidratar solo ese dato:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activity-gear --local-only
./.venv/bin/python -m nono_sports garmin fetch-activity-gear --max-activities 50
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Para una actividad concreta:

```bash
./.venv/bin/python -m nono_sports garmin fetch-activity-gear \
  --activity-id <garmin_activity_id>
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Para peso, frecuencia cardiaca en reposo, composición corporal u otras
mediciones puntuales, consulta:

```text
20_consolidado/measurements.jsonl
20_consolidado/measurement_sources.jsonl
20_consolidado/measurements_state.json
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

## Validar el estado sin llamar a APIs externas

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

Para Garmin Connect, la reconstrucción offline equivalente es:

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Este comando no llama a Garmin Connect. Lee raw Garmin ya descargado, normaliza,
consolida y no conserva `raw/fit_decoded/*.fitdecode.json`.

## Uso excepcional: descargar nueva actividad Strava

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

El timer diario `nono-sports-strava-sync.timer` quedó desactivado el
2026-07-10 porque Strava no debe ser fuente operativa reciente mientras su API
siga vetada/no operativa.

## Uso excepcional: sincronizar Garmin Connect

Garmin Connect usa tokenstore local y no debe reloguear en cada ejecución.
El comando recomendado para una actualización normal es:

```bash
cd /home/nono/apps/nono-sport
./.venv/bin/python -m nono_sports garmin sync \
  --lock-file /home/nono/.local/state/nono-sports/garmin-sync.lock
```

Este comando:

- lista actividades recientes de Garmin Connect
- usa `last_successful_activity_sync_at` y un solape por defecto de 7 días
- deja de paginar al llegar a actividades anteriores a la ventana incremental
- descarga solo actividades pendientes o incompletas
- descarga mediciones recientes de peso/composición desde Garmin Connect
- descarga perfil, settings, equipación declarada, dispositivos y equipación
  usada por actividad cuando Garmin lo expone
- conserva el ZIP/FIT/GPX/TCX original que corresponda
- normaliza Garmin Connect
- normaliza el CSV manual de biometría si existe
- reconstruye el consolidado multi-fuente
- no genera `fit_decoded/*.fitdecode.json` en el flujo normal

No añadir `--max-activities` ni `--max-pages` en la automatización diaria: si
una ejecución queda limitada artificialmente, una actividad reciente podria
quedar sin descargar aunque el marcador incremental avance. Usar esos limites
solo en pruebas, backfills o auditorias controladas.

Si Carlos pide una auditoría o backfill histórico, puede usarse:

```bash
./.venv/bin/python -m nono_sports garmin sync --full-scan
```

Si Garmin Connect rechaza el tokenstore, no reloguear en automatización. Pedir
intervención humana y ejecutar:

```bash
./.venv/bin/python -m nono_sports garmin auth
```

Para forzar solo una descarga histórica de mediciones Garmin:

```bash
./.venv/bin/python -m nono_sports garmin fetch-measurements \
  --full-measurement-scan
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Para refrescar solo datos de usuario/equipación Garmin:

```bash
./.venv/bin/python -m nono_sports garmin fetch-user-data
./.venv/bin/python -m nono_sports garmin sync --skip-fetch
```

Para normalizar solo el CSV manual de biometría:

```bash
./.venv/bin/python -m nono_sports manual normalize
```

No uses `--force` sin confirmación explícita: puede reprocesar mucho histórico.

Si necesitas investigar una actividad concreta con todo el detalle FIT:

```bash
./.venv/bin/python -m nono_sports garmin decode-fit --activity-id <garmin_activity_id>
```

Después de la investigación, limpia intermedios:

```bash
./.venv/bin/python -m nono_sports garmin clean-intermediates --activity-id <garmin_activity_id>
```

No uses `--keep-intermediate-files` salvo depuración explícita; esos JSON pueden
ocupar decenas de MB por actividad.

## Automatización activa

La sincronización Garmin Connect está configurada con un timer de usuario
`systemd`. Usa el patrón operativo aprobado: usuario `nono`, `--lock-file`,
ventana incremental y sin `--force`.

Timer:

```text
nono-sports-garmin-sync.timer
```

Servicio:

```text
nono-sports-garmin-sync.service
```

Se ejecuta como usuario:

```text
nono
```

Programación:

```text
19:50 UTC, sin retraso aleatorio
```

`linger` está activado para `nono`, por lo que el timer puede ejecutarse tras reboot aunque no haya sesión SSH abierta.

## Comprobar automatización

Ver timer:

```bash
systemctl --user status nono-sports-garmin-sync.timer --no-pager
systemctl --user list-timers nono-sports-garmin-sync.timer
```

Ver servicio:

```bash
systemctl --user cat nono-sports-garmin-sync.service
```

Ver logs:

```bash
journalctl --user -u nono-sports-garmin-sync.service -n 100 --no-pager
```

Seguir logs en vivo:

```bash
journalctl --user -u nono-sports-garmin-sync.service -f
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
- lanzar backfills Garmin con `--full-scan` o `--force`
- conservar intermedios Garmin con `--keep-intermediate-files`
- subir tokens o `.env` al repositorio

## Qué hacer si algo falla

Si falla una consulta de datos:

1. Revisa `20_consolidado/state.json`.
2. Ejecuta `strava validate`.
3. Lee `30_analisis/informes/strava_validation_report.md`.
4. Si la duda afecta a Garmin, revisa `10_fuentes/garmin_connect/logs/activity_sync_state.json`.

Si falla la sincronización:

1. Revisa logs con `journalctl`.
2. Comprueba si el error es de rate limit.
3. Si es rate limit, espera a la siguiente ventana.
4. Si es autenticación, no pegues tokens en respuestas; pide intervención de Carlos.
5. Si falla Garmin por tokenstore, ejecuta `garmin doctor` y pide intervención si requiere login.

Si faltan actividades:

1. Mira si el informe contiene `raw.activities_incomplete`.
2. Si hay cuota disponible, puede ejecutarse `strava sync`.
3. Si la cuota diaria está cerca del límite, espera al día siguiente.
4. Para Garmin, ejecuta `garmin sync` normal antes de plantear `--full-scan`.

Si faltan streams pero las actividades están completas:

1. Revisa los ficheros en `10_fuentes/strava/raw/errors`.
2. Si los errores son `404 Resource Not Found` en streams de workouts o
   `402 Payment Required` en zones, trátalos como datos no disponibles.
3. No lances sincronizaciones repetidas solo para esos avisos.

## Principio operativo

La fuente raw manda. La capa consolidada es la entrada principal para consultas. Toda respuesta analítica debe poder trazarse, si hace falta, a una actividad normalizada y a un fichero raw original.
