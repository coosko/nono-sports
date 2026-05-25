# Estado actual del proyecto

Fecha de referencia: 2026-05-25

## Situación actual

El repositorio está en fase de implementación incremental de Strava v1.

Existe actualmente:

- un scaffold de módulos para Strava v1 en `src/nono_sports/`
- un punto de entrada CLI con preparación de directorios Strava v1 y autenticación Strava
- almacenamiento de token Strava en `~/.local/state/nono-sports/strava_tokens.json`
- un cliente Strava base de solo lectura con refresh de token, paginación, rate limits y errores normalizados
- descarga raw de perfil y contexto Strava con rutas, clubs, segmentos favoritos, exports y manifiesto de trazabilidad
- descarga raw de actividades Strava con detalle, laps, streams, gear, segmentos, estado reanudable, zonas opcionales bajo demanda y parada preventiva por presupuesto de rate limit
- scripts para crear la estructura base de directorios de datos
- documentación de visión, requisitos, arquitectura y planificación
- integración básica de calidad con `ruff`, `pytest` y GitHub Actions

No existe todavía:

- normalización de los raw descargados desde Strava
- importadores para Garmin, Komoot o ficheros manuales
- modelo común implementado
- proceso de consolidación
- escritura de datasets `normalizado` o `20_consolidado`

## Estado del código activo

El código activo contiene el scaffold de paquetes de Strava v1, configuración inicial, resolución de rutas, creación de directorios de datos, autenticación OAuth, cliente HTTP base para Strava, descarga raw de perfil/contexto y descarga raw de actividades con control preventivo de límites de lectura.

El código previo se conserva en `deprecated/initial-bootstrap/` solo como referencia histórica y no forma parte de la implementación vigente.

## Próximo objetivo

Validar con el usuario los ficheros generados por el Paso 7 y pasar después a la normalización Strava.
