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
- si quedan pendientes y hay cuota diaria, programa otra tanda para 20 minutos después

Si Strava ya está cerca del límite diario, puede consumir una llamada para conocer el estado y detenerse. Eso es correcto.

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

## Principio operativo

La fuente raw manda. La capa consolidada es la entrada principal para consultas. Toda respuesta analítica debe poder trazarse, si hace falta, a una actividad normalizada y a un fichero raw original.
