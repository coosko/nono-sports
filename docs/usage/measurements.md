# Mediciones biométricas

Esta guía describe el flujo de peso, frecuencia cardiaca en reposo,
composición corporal y futuras métricas puntuales.

## Modelo

Cada fuente escribe mediciones normalizadas en:

```text
10_fuentes/<fuente>/normalizado/measurements.jsonl
```

Cada registro incluye:

- `metric`: nombre canónico, por ejemplo `weight`, `resting_heart_rate`,
  `body_fat`, `bmi`.
- `value` y `unit`: valor numérico y unidad.
- `measurement_date` y `measured_at_utc`: fecha de medición y hora UTC cuando
  se conoce.
- `source_reference`: trazabilidad al raw original.
- `attributes`: datos específicos de la fuente.

El consolidado escribe:

```text
20_consolidado/measurements.jsonl
20_consolidado/measurement_sources.jsonl
20_consolidado/measurements_state.json
```

## Garmin Connect

Descarga mediciones por rango de fechas:

```bash
./.venv/bin/python -m nono_sports garmin fetch-measurements \
  --start-date 2023-01-01 \
  --end-date 2026-07-12
```

Backfill completo:

```bash
./.venv/bin/python -m nono_sports garmin fetch-measurements \
  --full-measurement-scan
```

El comando diario recomendado incluye mediciones:

```bash
./.venv/bin/python -m nono_sports garmin sync \
  --lock-file /home/nono/.local/state/nono-sports/garmin-sync.lock
```

Para una operación excepcional sin tocar mediciones:

```bash
./.venv/bin/python -m nono_sports garmin sync --skip-measurements
```

Si Garmin rechaza el tokenstore, renovar sesión de forma interactiva:

```bash
./.venv/bin/python -m nono_sports garmin auth
```

## Manual

El CSV manual vive en:

```text
10_fuentes/manual/biometria/mediciones_carlos.csv
```

Normalización:

```bash
./.venv/bin/python -m nono_sports manual normalize
```

`garmin sync --skip-fetch` y `build-consolidated` también reconstruyen el
consolidado de mediciones desde los normalizados disponibles.
