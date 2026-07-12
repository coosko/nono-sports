# Índice de documentación

La documentación se organiza por niveles de autoridad.

## Documentos canónicos

- `docs/requirements/requirements.md`: fuente de verdad funcional y no funcional
- `docs/requirements/garmin-connect.md`: decisión aprobada de integración Garmin Connect
- `docs/technical/architecture.md`: fuente de verdad técnica
- `docs/current-state.md`: estado real del repositorio en cada momento

## Documento de entrada

- `docs/requirements/resources/Descripcion_inicial.md`: visión inicial y razonamiento de partida
- `docs/requirements/resources/descripcion_integracion_garmin_connect.md`: análisis aprobado que sustenta la decisión Garmin Connect

## Documentos derivados

- `docs/roadmap.md`: hitos y evolución prevista
- `docs/planning/features.md`: backlog funcional derivado de requisitos y arquitectura
- `docs/planning/workplan.md`: secuencia de trabajo derivada
- `docs/todo.md`: tareas inmediatas
- `docs/usage/quickstart.md`: puesta en marcha del estado actual
- `docs/usage/doctor.md`: diagnóstico local seguro de entorno y fuentes
- `docs/usage/garmin-connect-probe.md`: prueba aislada Garmin Connect
- `docs/usage/garmin-fetch-activities.md`: descarga raw Garmin Connect
- `docs/usage/measurements.md`: mediciones biométricas Garmin/manual y consolidado
- `docs/usage/strava-auth.md`: guía de autenticación Strava
- `docs/usage/strava-fetch-context.md`: guía de descarga raw de perfil y contexto Strava
- `docs/usage/strava-fetch-activities.md`: guía de descarga raw de actividades Strava
- `docs/usage/strava-normalize.md`: guía de normalización Strava
- `docs/usage/build-consolidated.md`: guía de consolidación inicial
- `docs/usage/strava-validate.md`: guía de validación de datos Strava
- `docs/usage/install-nono.md`: guía de instalación en el host Nono
- `docs/usage/automation.md`: guía de automatización controlada en Nono
- `docs/usage/nono-operator-guide.md`: guía operativa y prompt sugerido para Nono
- `docs/releases/CHANGELOG.md`: historial de cambios relevantes

## Regla de mantenimiento

1. Actualizar primero `requirements.md` si cambia el alcance.
2. Actualizar `architecture.md` si cambia el diseño técnico.
3. Ajustar después `roadmap`, `features`, `workplan` y `todo`.
4. Mantener `README.md` y `current-state.md` alineados con el estado real.
