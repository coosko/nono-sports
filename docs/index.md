# Índice de documentación

La documentación se organiza por niveles de autoridad.

## Documentos canónicos

- `docs/requirements/requirements.md`: fuente de verdad funcional y no funcional
- `docs/technical/architecture.md`: fuente de verdad técnica
- `docs/current-state.md`: estado real del repositorio en cada momento

## Documento de entrada

- `docs/requirements/resources/Descripcion_inicial.md`: visión inicial y razonamiento de partida

## Documentos derivados

- `docs/roadmap.md`: hitos y evolución prevista
- `docs/planning/features.md`: backlog funcional derivado de requisitos y arquitectura
- `docs/planning/workplan.md`: secuencia de trabajo derivada
- `docs/todo.md`: tareas inmediatas
- `docs/usage/quickstart.md`: puesta en marcha del estado actual
- `docs/usage/strava-auth.md`: guía de autenticación Strava
- `docs/releases/CHANGELOG.md`: historial de cambios relevantes

## Regla de mantenimiento

1. Actualizar primero `requirements.md` si cambia el alcance.
2. Actualizar `architecture.md` si cambia el diseño técnico.
3. Ajustar después `roadmap`, `features`, `workplan` y `todo`.
4. Mantener `README.md` y `current-state.md` alineados con el estado real.
