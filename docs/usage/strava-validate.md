# Validación de datos Strava

Este comando valida el dataset local ya descargado, normalizado y consolidado. No llama a la API de Strava y no consume cuota.

## Ejecutar validación

```bash
export NONO_SPORT_DATA_ROOT='/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte'
./.venv/bin/python -m nono_sports strava validate
```

El comando comprueba:

- estructura de directorios Strava v1
- conteos de raw, normalizado y consolidado
- actividades listadas sin detalle descargado
- detalles sin streams o laps
- errores recuperables registrados
- coherencia entre `10_fuentes/strava/normalizado` y `20_consolidado`

## Informe generado

El informe se escribe en:

```text
<NONO_SPORT_DATA_ROOT>/30_analisis/informes/strava_validation_report.md
```

Estados posibles:

- `pass`: no hay errores ni avisos
- `warning`: el dataset es coherente, pero hay trabajo pendiente o incidencias revisables
- `fail`: hay errores estructurales o incoherencias que deben corregirse antes de consumir los datos

El comando devuelve código de salida `0` para `pass` y `warning`, y `1` para `fail`.

Con la descarga incremental actual es normal ver `warning` si faltan actividades por descargar debido a rate limit.

## Flujo recomendado

Cuando se reanude una descarga pendiente:

```bash
./.venv/bin/python -m nono_sports strava fetch-activities
./.venv/bin/python -m nono_sports strava normalize
./.venv/bin/python -m nono_sports build-consolidated
./.venv/bin/python -m nono_sports strava validate
```
