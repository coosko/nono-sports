# Doctor

`doctor` diagnostica el entorno local de `nono-sports` antes de sincronizar o
investigar una fuente.

Por defecto no descarga datos, no llama a APIs externas y no escribe en servicios
remotos.

## Comandos

Diagnóstico común:

```bash
./.venv/bin/python -m nono_sports doctor
```

Diagnóstico Strava:

```bash
./.venv/bin/python -m nono_sports strava doctor
```

Diagnóstico Garmin Connect:

```bash
./.venv/bin/python -m nono_sports garmin doctor
```

## Estados

La salida general puede ser:

```text
status=ok
status=warning
status=error
```

Interpretación:

- `ok`: el diagnóstico no ha encontrado problemas.
- `warning`: hay algo revisable, pero no necesariamente bloqueante.
- `error`: hay un problema que debe resolverse antes de operar con seguridad.

El comando devuelve código `1` solo si el estado final es `error`.

## Qué comprueba

El diagnóstico común comprueba:

- versión de Python compatible
- fichero XDG `~/.config/nono-sports/env` si existe
- `NONO_SPORT_DATA_ROOT`
- existencia de la raíz de datos
- estado y permisos de `~/.local/state/nono-sports`
- ausencia de secretos obvios en ubicaciones de datos

`strava doctor` añade:

- estructura esperada de `10_fuentes/strava`
- existencia y permisos de `~/.local/state/nono-sports/strava_tokens.json`

`garmin doctor` añade:

- estructura esperada de `10_fuentes/garmin_connect`
- presencia opcional de la dependencia `garminconnect`
- existencia y permisos de `~/.local/state/nono-sports/garmin_connect/tokenstore`

En este momento `garminconnect` puede aparecer como `warning` si aún no está
instalado. Eso es esperable antes del Paso 14.

## Buenas prácticas

- Ejecutar `doctor` antes de activar una sincronización nueva.
- Ejecutar `strava doctor` después de mover tokens o cambiar permisos.
- Ejecutar `garmin doctor` antes de iniciar la prueba aislada de Garmin Connect.
- No usar `doctor` como sustituto de `validate`: `doctor` revisa entorno; `validate`
  revisa calidad del dataset.
