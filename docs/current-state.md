# Estado actual del proyecto

Fecha de referencia: 2026-06-25

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
- reprogramación adaptativa de `strava sync` con `systemd-run --user`, limitada
  a trabajo descargable real
- guía operativa para que Nono entienda y use su sistema deportivo
- scripts para crear la estructura base de directorios de datos
- documentación de visión, requisitos, arquitectura y planificación
- integración básica de calidad con `ruff`, `pytest` y GitHub Actions

No existe todavía:

- importadores para Garmin, Komoot o ficheros manuales
- consolidación multi-fuente con deduplicación

## Estado del código activo

El código activo contiene el scaffold de paquetes de Strava v1, configuración inicial, resolución de rutas, creación de directorios de datos, autenticación OAuth, cliente HTTP base para Strava, descarga raw de perfil/contexto, descarga raw de actividades con control preventivo de límites de lectura, normalización local de raw Strava, consolidación inicial desde una sola fuente, validación offline de conteos/coherencia, carga de configuración desde entorno/XDG/`.env` local, comando operativo `strava sync` y reprogramación adaptativa para backfill.

Cambios operativos realizados por Nono hasta el 2026-06-25:

- Uso operativo de Drive como raíz única de datos:
  `/home/nono/drive/01_ambitos/02_personal/40_deporte`.
- Documentada la recuperación prudente de `nono-drive.service` cuando el mount
  FUSE falla.
- Ajustada la reprogramación adaptativa para que no se encadene por streams o
  errores recuperables no descargables.
- Añadido sufijo único a las unidades transient de `systemd-run` para evitar
  colisiones entre ejecuciones adaptativas.
- Añadida tolerancia a líneas JSON corruptas en el índice de manifiesto raw
  durante normalización.

Estado observado el 2026-06-25:

- `20_consolidado` contiene 1.148 actividades.
- Todas las actividades listadas por Strava tienen detalle raw y laps.
- Hay 1.141 streams de actividad; 7 workouts/estiramientos devuelven
  `404 Resource Not Found` en el endpoint de streams.
- Hay 6 errores antiguos de zones con `402 Payment Required`; zones no se
  descargan en la sincronización normal.
- Esos avisos no deben considerarse motivo suficiente para reprogramar otra
  ejecución adaptativa.

El código previo se conserva en `deprecated/initial-bootstrap/` solo como referencia histórica y no forma parte de la implementación vigente.

## Próximo objetivo

Mantener el timer diario activo para detectar actividades nuevas y comprobar que,
tras descargar una actividad nueva, solo se encadenan ejecuciones adaptativas si
queda trabajo descargable real.
