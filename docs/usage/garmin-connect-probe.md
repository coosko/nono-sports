# Prueba aislada Garmin Connect

Esta guía corresponde al Paso 14 del plan de trabajo.

La prueba valida `garminconnect==0.3.6`, login inicial, tokenstore, reutilización
de tokens y descarga de una actividad de muestra sin integrar Garmin Connect en
el pipeline principal.

El script usa el adaptador interno `nono_sports.garmin_connect`, por lo que sirve
también como prueba manual del encapsulado aprobado.

## Instalar dependencia opcional

```bash
./.venv/bin/python -m pip install -e '.[garmin]'
```

## Ejecutar doctor

```bash
./.venv/bin/python -m nono_sports garmin doctor
```

Antes de la prueba es normal ver avisos si no existe todavía el tokenstore o si
`garminconnect` aún no está instalado.

## Ejecutar prueba

```bash
./.venv/bin/python scripts/garmin_connect_probe.py
```

El script intentará primero usar tokens existentes en:

```text
~/.local/state/nono-sports/garmin_connect/tokenstore/
```

Si no hay tokens válidos, pedirá:

- email Garmin
- contraseña Garmin
- código MFA si Garmin lo requiere

La contraseña no se guarda en el repositorio ni en `NONO_SPORT_DATA_ROOT`.

## Salida

Por defecto escribe muestras en:

```text
/tmp/nono-sports-garmin-probe/
```

Puede generar:

- `activities_index.json`
- `<activity_id>.activity.json`
- `<activity_id>.details.json`
- `<activity_id>.splits.json`
- `<activity_id>.typed_splits.json`
- `<activity_id>.split_summaries.json`
- `<activity_id>.weather.json`
- `<activity_id>.fit`

Estos ficheros son solo para validar la integración. No forman parte todavía de
`10_fuentes/garmin_connect`.

## Segunda ejecución

Para validar autonomía por tokenstore, ejecutar de nuevo:

```bash
./.venv/bin/python scripts/garmin_connect_probe.py --skip-fit
```

Si no pide email/contraseña, la reutilización de tokens queda validada.

## Actividad concreta

Si queremos repetir sobre una actividad específica:

```bash
./.venv/bin/python scripts/garmin_connect_probe.py --activity-id <garmin_activity_id>
```

## Criterio de éxito

La prueba queda validada si:

- se instala `garminconnect==0.3.6`
- el login inicial funciona
- se guarda tokenstore en la ruta XDG aprobada
- una segunda ejecución funciona sin introducir credenciales
- se lista al menos una actividad
- se descarga detalle y FIT de una actividad

## Resultado local validado

Resultado observado en desarrollo local:

- `garminconnect==0.3.6` instalado correctamente.
- `garmin doctor` detecta la librería y el tokenstore.
- Login inicial completado.
- Garmin devolvió `429` en intentos mobile previos al login correcto, por lo que
  hay que evitar relogueos repetidos.
- Tokenstore guardado en `~/.local/state/nono-sports/garmin_connect/tokenstore/`.
- Segunda ejecución completada sin pedir credenciales.
- Descargada una actividad de prueba con:
  `activity`, `details`, `splits`, `typed_splits`, `split_summaries`, `weather`
  y FIT original.

Conclusión:

```text
El tokenstore es viable para la siguiente fase local.
El adaptador Garmin Connect debe reutilizar tokens y no reloguear en cada ejecución.
```
