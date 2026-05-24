# Plan de trabajo

## Fase 1: Base del proyecto

- Establecer la estructura del repositorio.
- Configurar `pyproject.toml`, `pre-commit` y CI.
- Crear documentación inicial en `docs/`.

## Fase 2: Sincronización Strava

- Implementar `StravaSync`.
- Gestionar tokens y refresco.
- Guardar raw data en la estructura de carpetas.

## Fase 3: Normalización

- Implementar `DataNormalizer`.
- Definir esquema normalizado.
- Generar archivos `activities.jsonl` y `activities.csv`.

## Fase 4: Consolidación

- Implementar `DataIntegrator`.
- Añadir deduplicación y merge.
- Generar `20_consolidado/`.

## Fase 5: Producción y despliegue

- Definir el root de datos como parámetro de instalación.
- Documentar instalación y uso en `docs/usage/`.
- Añadir versiones y changelog.

## Cronograma sugerido

- Semana 1: estructura, docs, entorno, primeros scripts.
- Semana 2: sincronización Strava y raw storage.
- Semana 3: normalización y datos consolidados.
- Semana 4: integración, pruebas, documentación final.
