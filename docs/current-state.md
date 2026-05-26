# Estado actual del proyecto

Fecha de referencia: 2026-05-26

## Situación actual

El repositorio está en fase de implementación incremental de Strava v1.

Existe actualmente:

- un scaffold de módulos para Strava v1 en `src/nono_sports/`
- un punto de entrada CLI con preparación de directorios Strava v1 y autenticación Strava
- almacenamiento de token Strava en `~/.local/state/nono-sports/strava_tokens.json`
- un cliente Strava base de solo lectura con refresh de token, paginación, rate limits y errores normalizados
- descarga raw de perfil y contexto Strava con rutas, clubs, segmentos favoritos, exports y manifiesto de trazabilidad
- descarga raw de actividades Strava con detalle, laps, streams, gear, segmentos, estado reanudable, zonas opcionales bajo demanda y parada preventiva por presupuesto de rate limit
- normalización Strava a JSONL de atleta, actividades y streams con trazabilidad a raw
- consolidación inicial single-source en `20_consolidado` para consumo de Nono
- validación offline del dataset local con informe Markdown en `30_analisis/informes`
- soporte de configuración persistente en `~/.config/nono-sports/env`
- guía de instalación en el host Nono
- compatibilidad validada con Python 3.14.4 en Nono
- instalación persistente validada en `/home/nono/apps/nono-sport`
- tokens OAuth copiados en Nono con permisos restrictivos
- comando `strava sync` para sincronización controlada manual o programada
- reprogramación adaptativa de `strava sync` con `systemd-run --user`
- guía operativa para que Nono entienda y use su sistema deportivo
- scripts para crear la estructura base de directorios de datos
- documentación de visión, requisitos, arquitectura y planificación
- integración básica de calidad con `ruff`, `pytest` y GitHub Actions

No existe todavía:

- importadores para Garmin, Komoot o ficheros manuales
- consolidación multi-fuente con deduplicación

## Estado del código activo

El código activo contiene el scaffold de paquetes de Strava v1, configuración inicial, resolución de rutas, creación de directorios de datos, autenticación OAuth, cliente HTTP base para Strava, descarga raw de perfil/contexto, descarga raw de actividades con control preventivo de límites de lectura, normalización local de raw Strava, consolidación inicial desde una sola fuente, validación offline de conteos/coherencia, carga de configuración desde entorno/XDG/`.env` local, comando operativo `strava sync` y reprogramación adaptativa para backfill.

El código previo se conserva en `deprecated/initial-bootstrap/` solo como referencia histórica y no forma parte de la implementación vigente.

## Próximo objetivo

Ejecutar `strava sync` con descarga cuando se libere cuota diaria de Strava y decidir si se activa el `systemd timer` en Nono.
