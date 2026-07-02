# Estado actual del proyecto

Fecha de referencia: 2026-07-02

## Situación actual

El repositorio tiene Strava v1 operativo y Garmin Connect v1 en fase de
backfill controlado.

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
- comandos `doctor`, `strava doctor` y `garmin doctor` para diagnóstico local seguro
- extra opcional `garmin` con `garminconnect==0.3.6`
- script aislado `scripts/garmin_connect_probe.py` para validar login, tokenstore, actividad y FIT de Garmin Connect
- instalación local de `garminconnect==0.3.6` validada por `garmin doctor`
- prueba aislada Garmin Connect completada con login inicial, tokenstore, segunda ejecución sin credenciales y descarga de una actividad
- adaptador Garmin Connect base de solo lectura implementado con login por tokenstore, login interactivo, listado, detalle, splits, typed splits, split summaries, weather y descarga FIT
- descarga raw Garmin Connect inicial implementada con `garmin fetch-activities`
- una actividad Garmin real descargada en `10_fuentes/garmin_connect/raw` con manifiesto y estado reanudable
- idempotencia Garmin inicial validada: la segunda ejecución salta la actividad ya completa
- módulo independiente `nono_sports.formats.fit` implementado para extracción y decodificación FIT
- backend FIT inicial decidido: `fitdecode==0.11.0`
- FIT Garmin real decodificado en `raw/fit_decoded/<id>.fitdecode.json`
- decodificación FIT enriquecida con metadatos de campo para conservar
  `def_num`, `raw_value`, unidades y tipos
- comparación reutilizable `fitdecode` vs `garmin-fit-sdk` disponible para FITs
  de cualquier origen
- normalización Garmin Connect implementada para activities, streams, laps,
  splits, typed splits, segment candidates y state
- normalización Garmin incremental: reutiliza actividades sin cambios y evita
  releer FIT decodificados grandes
- comando `garmin sync` implementado para encadenar descarga raw, decodificación
  FIT, normalización y consolidación
- backfill Garmin incremental: pagina el listado, salta actividades ya completas
  y sigue buscando pendientes sin pedir todo el histórico en una sola llamada
- consolidación multi-fuente inicial implementada con `activity_sources.jsonl`
  multi-enlace y `duplicate_candidates.jsonl`
- Garmin `23422332225` y Strava `19114956119` validados como una única
  actividad consolidada
- reprogramación adaptativa de `strava sync` con `systemd-run --user`, limitada
  a trabajo descargable real
- guía operativa para que Nono entienda y use su sistema deportivo
- Wikiloc validado como fuente auxiliar externa para descubrir rutas reales,
  tracks, desnivel, waypoints y fotos antes de cruzar con meteo, logística y
  estado deportivo de Carlos
- scripts para crear la estructura base de directorios de datos
- documentación de visión, requisitos, arquitectura y planificación
- decisión aprobada para Garmin Connect en `docs/requirements/garmin-connect.md`
- análisis de entrada Garmin Connect conservado en `docs/requirements/resources/descripcion_integracion_garmin_connect.md`
- integración básica de calidad con `ruff`, `pytest` y GitHub Actions

No existe todavía:

- validación real de autonomía Garmin Connect en Nono
- importadores para Komoot o ficheros manuales
- ingesta normalizada de rutas Wikiloc dentro de `10_fuentes` o
  `20_consolidado`
- selección avanzada de fuente primaria por métrica en consolidación multi-fuente

## Estado del código activo

El código activo contiene el scaffold de paquetes de Strava v1, configuración inicial, resolución de rutas, creación de directorios de datos, autenticación OAuth, cliente HTTP base para Strava, descarga raw de perfil/contexto, descarga raw de actividades con control preventivo de límites de lectura, normalización local de raw Strava, consolidación inicial multi-fuente, validación offline de conteos/coherencia, carga de configuración desde entorno/XDG/`.env` local, comando operativo `strava sync`, comando operativo `garmin sync` y reprogramación adaptativa para backfill Strava.

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
- Validado Wikiloc como herramienta auxiliar dinámica para planificación de
  rutas. No forma parte todavía de la ingesta ni de la capa consolidada.

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

Completar el backfill histórico Garmin Connect de forma conservadora y validar
manualmente varias actividades representativas frente a Garmin Connect.
