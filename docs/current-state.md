# Estado actual del proyecto

Fecha de referencia: 2026-08-26

## Situación actual

El repositorio tiene Strava v1 operativo como fuente histórica local y Garmin
Connect v1 operativo como fuente diaria principal. Mientras no haya acceso API
operativo a Strava, no se planifican auditorías live ni sincronización periódica
de Strava.

Existe actualmente:

- un scaffold de módulos para Strava v1 en `src/nono_sports/`
- un punto de entrada CLI con preparación de directorios Strava v1 y autenticación Strava
- almacenamiento de token Strava en `~/.local/state/nono-sports/strava_tokens.json`
- un cliente Strava base de solo lectura con refresh de token, paginación, rate limits y errores normalizados
- descarga raw de perfil y contexto Strava con rutas, clubs, segmentos favoritos, exports y manifiesto de trazabilidad
- descarga raw de actividades Strava con detalle, laps, streams, gear, segmentos, estado reanudable, zonas opcionales bajo demanda y parada preventiva por presupuesto de rate limit
- normalización Strava a JSONL de atleta, actividades, streams, índice de
  streams y estado de normalización con trazabilidad a raw
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
- FIT Garmin decodificado transitoriamente durante la normalización, sin
  persistir el voluminoso `raw/fit_decoded/<id>.fitdecode.json`
- decodificación FIT enriquecida con metadatos de campo para conservar
  `def_num`, `raw_value`, unidades y tipos
- comparación reutilizable `fitdecode` vs `garmin-fit-sdk` disponible para FITs
  de cualquier origen
- normalización Garmin Connect implementada para activities, streams, laps,
  splits, typed splits, segment candidates y state
- contrato mínimo común por fuente normalizada: `activities.jsonl`,
  `streams.jsonl`, `streams_index.jsonl`, `state.json` y
  `logs/activity_sync_state.json`
- mediciones biométricas implementadas con descarga Garmin Connect de
  peso/composición, normalización del CSV manual de biometría y consolidación
  en `20_consolidado/measurements.jsonl`
- importación manual GPX implementada con copia raw, manifiesto, normalización
  a `activities.jsonl`, `streams.jsonl`, `streams_index.jsonl` y reconstrucción
  del consolidado
- datos de usuario/equipación implementados: Garmin Connect descarga
  perfil/settings, equipación declarada, estadísticas de equipación,
  dispositivos y equipación por actividad cuando está disponible; Strava
  normaliza atleta y equipación desde perfil/detalles de gear
- consolidación multi-fuente de atleta y equipación en
  `20_consolidado/athletes.jsonl`, `athlete_sources.jsonl`,
  `equipment.jsonl` y `equipment_sources.jsonl`
- normalización Garmin incremental: usa el FIT original como entrada estable y
  permite borrar sin riesgo cualquier JSON decodificado de diagnóstico
- comandos operativos Garmin para diagnóstico y limpieza de intermedios:
  `garmin decode-fit --activity-id <id>` y `garmin clean-intermediates`
- opción excepcional `--keep-intermediate-files` en `garmin normalize` y
  `garmin sync`; no forma parte de la operación diaria
- comando `garmin sync` implementado para encadenar descarga raw, decodificación
  FIT transitoria, normalización y consolidación
- backfill Garmin incremental: pagina el listado, salta actividades ya completas
  y sigue buscando pendientes sin pedir todo el histórico en una sola llamada
- sincronización diaria Garmin optimizada: usa `last_successful_activity_sync_at`
  con solape configurable para cortar el listado al llegar a actividades
  anteriores a la ventana incremental
- fallback Garmin para actividades importadas sin FIT: conserva el ZIP original,
  extrae o descarga GPX/TCX, normaliza el track XML y marca la actividad como
  completa sin FIT cuando hay datos suficientes
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
- optimización de memoria en normalización, consolidación y validación:
  `streams.jsonl` se procesa línea a línea, Garmin reutiliza streams previos
  mediante offsets y el consolidado de equipación usa actividades fuente
  reducidas para calcular uso efectivo
- validación real en Nono de `nono-sports-garmin-sync.service` tras la
  optimización streaming: el 2026-08-25 arrancó por timer a las 19:50:04 UTC,
  terminó a las 19:51:19 UTC con `status=0/SUCCESS`, pico de memoria 366.8M y
  pico de swap 2.4M
- resumen operativo local por ejecución en
  `~/.local/state/nono-sports/logs/operation_runs.jsonl` para comandos de
  pipeline, separado de los checkpoints reproducibles que viven en Drive bajo
  `10_fuentes/<fuente>/logs/`
- optimización incremental por huella de entradas en normalización y
  consolidación: `garmin sync` y `strava sync --skip-fetch` reutilizan salidas
  previas cuando no hay raw/normalizado nuevo o modificado y las salidas
  esperadas existen

No existe todavía:

- importadores manuales desde FIT o TCX
- conectores normalizados para Komoot, Wikiloc u otras plataformas de rutas
- ingesta normalizada de rutas Wikiloc dentro de `10_fuentes` o
  `20_consolidado`
- selección avanzada de fuente primaria por métrica en consolidación multi-fuente
- separación opcional de fases en procesos distintos para liberar memoria entre
  fetch, normalización, consolidación y validación

## Estado del código activo

El código activo contiene el scaffold de paquetes de Strava v1, configuración
inicial, resolución de rutas, creación de directorios de datos, autenticación
OAuth, cliente HTTP base para Strava, descarga raw de perfil/contexto, descarga
raw de actividades con control preventivo de límites de lectura, normalización
local de raw Strava, Garmin Connect operativo con actividades, mediciones,
perfil, equipación y dispositivos, normalización de biometría manual,
importación manual de actividades GPX, consolidación multi-fuente de
actividades, mediciones, atleta y equipación,
validación offline de conteos/coherencia, carga de configuración
desde entorno/XDG/`.env` local, comando operativo `strava sync`, comando
operativo `garmin sync` y reprogramación adaptativa para backfill Strava.

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

Estado observado tras la auditoría Garmin del 2026-07-10:

- El raw local Garmin contiene 908 actividades alineadas con el estado de
  sincronización; Strava contiene 1.152 actividades.
- Se repararon desde Garmin nueve actividades con ZIP o splits ausentes, o con
  un payload ubicado en un directorio incorrecto.
- El raw Garmin queda con 908 ZIP originales, 902 FIT y 6 actividades con
  fallback GPX/TCX; no quedan referencias ausentes, nombres de conflicto de
  Drive ni archivos en un directorio incorrecto.
- `raw/fit_decoded` queda vacío. Una normalización posterior reutilizó las 908
  actividades sin regenerar derivados ni perder datos normalizados.
- Tras mejorar el matching Garmin-Strava y sincronizar Garmin, el consolidado
  contiene 1.158 actividades y 2.060 enlaces de fuente.

Estado observado tras los fallos OOM de agosto de 2026:

- El timer diario Garmin había ejecutado cerca del límite de memoria del host
  Nono, con picos aproximados de 1.1-1.2 GB en una máquina de 1.8 GiB de RAM.
- La causa estructural principal era cargar JSONL grandes, especialmente
  `normalizado/streams.jsonl`, como objetos completos de Python.
- Se implementó la prioridad 1: lectura/escritura streaming para JSONL grandes,
  reutilización incremental de streams Garmin por offset y validación sin
  `read_text().splitlines()` sobre `streams.jsonl`.
- Validación real local offline tras el cambio:
  `strava normalize` procesó 1.152 actividades y 1.145 streams con pico de
  148.556 KB RSS; `garmin sync --skip-fetch` reconstruyó Garmin/manual y
  consolidado con 925 actividades Garmin, 1.175 actividades consolidadas y pico
  de 321.004 KB RSS, sin swaps.

El código previo se conserva en `deprecated/initial-bootstrap/` solo como referencia histórica y no forma parte de la implementación vigente.

## Próximo objetivo

Vigilar el comportamiento real de I/O en Drive tras la optimización
incremental. Si vuelve a aparecer presión operativa, revisar primero
`journalctl` y
`~/.local/state/nono-sports/logs/operation_runs.jsonl`, y luego priorizar
diagnóstico de Drive/rclone antes de plantear cambios de arquitectura o
salvaguardas preventivas de memoria.
