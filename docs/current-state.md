# Estado actual del proyecto

Fecha de referencia: 2026-05-24

## Situación actual

El repositorio está en fase de definición documental y de arquitectura.

Existe actualmente:

- un scaffold de módulos para Strava v1 en `src/nono_sports/`
- un punto de entrada CLI con preparación de directorios Strava v1 y autenticación Strava
- almacenamiento de token Strava en `~/.local/state/nono-sports/strava_tokens.json`
- scripts para crear la estructura base de directorios de datos
- documentación de visión, requisitos, arquitectura y planificación
- integración básica de calidad con `ruff`, `pytest` y GitHub Actions

No existe todavía:

- sincronización real con Strava
- importadores para Garmin, Komoot o ficheros manuales
- modelo común implementado
- proceso de consolidación
- escritura de datasets `raw`, `normalizado` o `20_consolidado`

## Estado del código activo

El código activo contiene el scaffold de paquetes de Strava v1, configuración inicial, resolución de rutas y creación de directorios de datos.

El código previo se conserva en `deprecated/initial-bootstrap/` solo como referencia histórica y no forma parte de la implementación vigente.

## Próximo objetivo

Completar la autenticación OAuth real con intervención del usuario.
