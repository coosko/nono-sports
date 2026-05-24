# Requisitos del proyecto

## Requisitos funcionales

- RF1: El sistema debe sincronizar actividades desde la API de Strava.
- RF2: El sistema debe almacenar datos raw y normalizados en una estructura de carpetas.
- RF3: El sistema debe poder integrar datos de múltiples fuentes.
- RF4: El sistema debe producir salidas en `JSONL` y `CSV`.
- RF5: El sistema debe permitir configurar la ruta base de datos mediante una variable de entorno.

## Requisitos no funcionales

- RNF1: El proyecto debe ser portable entre Windows y WSL.
- RNF2: El proyecto debe usar Python 3.11+ y empaquetado PEP 621.
- RNF3: El proyecto debe incluir CI con pruebas automáticas.
- RNF4: El proyecto debe mantener documentación clara y actualizada.

## Requisitos de documentación

- RD1: Mantener un historial de versiones (`CHANGELOG`).
- RD2: Documentar la estructura y uso del proyecto (`usage/`).
- RD3: Documentar la arquitectura y decisiones técnicas.
- RD4: Documentar la planificación y roadmap.
