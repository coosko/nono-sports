# Changelog

Todas las versiones y entregables se documentan aquí.

## [Unreleased]

### Added

- Añadida carga de `.env`, validación de configuración y resolución de `NONO_SPORT_DATA_ROOT`.
- Añadido comando `nono-sports strava prepare-dirs` para crear la estructura de datos Strava v1.
- Añadido soporte de configuración persistente en `~/.config/nono-sports/env`.
- Ampliado soporte Python declarado a `>=3.11,<3.15` tras validación en Python 3.14.4.
- Añadida autenticación OAuth Strava con almacenamiento XDG de tokens en `~/.local/state/nono-sports/strava_tokens.json`.
- Añadido cliente Strava base de solo lectura con refresh de token, paginación, rate limits y errores normalizados.
- Añadida descarga raw de perfil y contexto Strava con manifiesto de trazabilidad.
- Añadida descarga raw de actividades Strava con detalle, laps, streams, gear, segmentos, errores recuperables y estado reanudable.
- Añadido control preventivo de rate limit con límites por defecto `100` peticiones de lectura cada 15 minutos y `1000` diarias.
- Añadidos modelos de dominio para atleta, actividad, stream, referencias de fuente y actividad consolidada.
- Añadida normalización Strava a JSONL de atleta, actividades y streams con trazabilidad a raw.
- Añadida consolidación inicial single-source en `20_consolidado` con enlaces a actividades fuente.
- Añadida validación offline del dataset Strava con informe Markdown en `30_analisis/informes`.
- Añadido comando `nono-sports strava sync` para encadenar descarga, normalización, consolidación y validación.
- Añadidas guías de uso para autenticación, descarga de contexto, descarga de actividades, normalización, consolidación y validación.
- Añadida guía de instalación en Nono con estrategia de usuario, permisos, tokens y preparación para webhooks futuros.
- Añadida guía de automatización controlada con propuesta de `systemd timer` de usuario.

### Changed

- Reorganizada la arquitectura documental del proyecto.
- Definido `Descripcion_inicial.md` como documento de entrada no normativo.
- Archivado el bootstrap inicial en `deprecated/initial-bootstrap/` y mantenido fuera del código activo.
- Cambiada la descarga de zonas de actividad a opt-in porque Strava la documenta como Summit Feature.
- Ampliado el raw gratuito con laps, gear desde actividades, segmentos favoritos/referenciados, club detail, route streams y exports GPX/TCX.
- Actualizada la arquitectura técnica para reflejar capas raw, normalizado, consolidado y validación.

### Verified

- Ejecutada autenticación real de Strava por el usuario.
- Ejecutada descarga real de perfil/contexto y descarga incremental real de actividades.
- Confirmado límite operativo de Strava de `100/1000` peticiones de lectura.
- Ejecutada normalización real de 34 actividades descargadas.
- Ejecutada consolidación real de 34 actividades normalizadas.
- Ejecutada validación real con estado `warning` por descarga incompleta esperada debido a rate limit.
- Ejecutada validación de compatibilidad en Nono con Python 3.14.4: `scripts/check.py` con 67 tests pasados y `strava validate` correcto.
- Ejecutada instalación persistente en Nono con configuración XDG, tokens copiados con permisos `600` y prueba real de autenticación Strava detenida correctamente por cuota diaria `996/1000`.
- Ejecutada prueba local de `strava sync --skip-fetch` sin llamar a Strava.
- Verificación local actual: `python3 scripts/check.py` con 68 tests pasados y `pre-commit run --all-files` correcto.

## 0.1.0 - 2026-05-24
- Creación del repositorio inicial.
- Añadidos módulos de sincronización, normalización e integración.
- Añadida primera versión de la documentación y estructura de datos.
