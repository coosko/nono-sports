# Changelog

Todas las versiones y entregables se documentan aquí.

## [Unreleased]
- Reorganizada la arquitectura documental del proyecto.
- Definido `Descripcion_inicial.md` como documento de entrada no normativo.
- Añadidos documentos canónicos para estado actual, requisitos y arquitectura.
- Añadido cliente Strava base de solo lectura con refresh de token, paginación, rate limits y errores normalizados.
- Añadida descarga raw de perfil y contexto Strava con manifiesto de trazabilidad.
- Añadida descarga raw de actividades Strava con detalle, streams, zonas opcionales, errores recuperables y estado reanudable.
- Cambiada la descarga de zonas de actividad a opt-in por ser una Strava Summit Feature.
- Ampliado el raw gratuito con laps, gear desde actividades, segmentos favoritos/referenciados, club detail, route streams y exports GPX/TCX.

## 0.1.0 - 2026-05-24
- Creación del repositorio inicial.
- Añadidos módulos de sincronización, normalización e integración.
- Añadida primera versión de la documentación y estructura de datos.
