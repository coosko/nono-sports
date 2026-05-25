# Descarga raw de perfil y contexto Strava

Este documento describe el primer comando de lectura real contra Strava. No escribe nada en Strava.

## Requisitos previos

- haber completado `docs/usage/strava-auth.md`
- tener `.env` configurado con `NONO_SPORT_DATA_ROOT`, `STRAVA_CLIENT_ID` y `STRAVA_CLIENT_SECRET`
- tener tokens guardados en `~/.local/state/nono-sports/strava_tokens.json`

## Comando

```bash
./.venv/bin/python -m nono_sports strava fetch-context
```

El comando descarga y guarda:

- atleta autenticado en `10_fuentes/strava/raw/athlete/profile.json`
- estadísticas agregadas en `10_fuentes/strava/raw/athlete/stats.json`
- zonas del atleta, si Strava lo permite, en `10_fuentes/strava/raw/athlete/zones.json`
- clubes en `10_fuentes/strava/raw/clubs/clubs.json`
- detalle de cada club en `10_fuentes/strava/raw/clubs/<id>.json`
- rutas en `10_fuentes/strava/raw/routes/routes.json`
- detalle de cada ruta en `10_fuentes/strava/raw/routes/<id>.json`
- streams de cada ruta en `10_fuentes/strava/raw/route_streams/<id>.json`
- export GPX/TCX de cada ruta en `10_fuentes/strava/raw/route_exports/`
- segmentos favoritos en `10_fuentes/strava/raw/segments/starred.json`
- detalle y streams de segmentos referenciados en rutas o favoritos
- equipo referenciado por el perfil en `10_fuentes/strava/raw/gear/<id>.json`
- manifiesto de trazabilidad en `10_fuentes/strava/raw/manifest.jsonl`

Si Strava deniega un dato opcional, por ejemplo zonas o una ruta privada, el comando registra el error recuperable en `10_fuentes/strava/raw/errors/` y continúa.

## Opciones

Para evitar llamadas de detalle de rutas:

```bash
./.venv/bin/python -m nono_sports strava fetch-context --skip-route-details
```

Para evitar exports GPX/TCX de rutas:

```bash
./.venv/bin/python -m nono_sports strava fetch-context --skip-route-exports
```

Para evitar streams de rutas:

```bash
./.venv/bin/python -m nono_sports strava fetch-context --skip-route-streams
```

Para evitar llamadas de detalle de equipo:

```bash
./.venv/bin/python -m nono_sports strava fetch-context --skip-gear-details
```

Para evitar segmentos favoritos o streams de segmentos:

```bash
./.venv/bin/python -m nono_sports strava fetch-context --skip-starred-segments
./.venv/bin/python -m nono_sports strava fetch-context --skip-segment-streams
```

## Validación manual

Después de ejecutar el comando, revisa:

- que existen los ficheros raw esperados bajo `10_fuentes/strava/raw/`
- que `manifest.jsonl` contiene una línea por fichero generado
- que no aparece ningún fichero de token dentro de `NONO_SPORT_DATA_ROOT`
- que los errores en `raw/errors/`, si existen, corresponden a datos opcionales
