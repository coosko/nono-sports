# Changelog

Todas las versiones y entregables se documentan aquí.

## [Unreleased]

## [0.2.0] - 2026-07-10

### Added

- Añadida guía operativa actualizada para Nono con Strava y Garmin Connect como
  fuentes activas.
- Añadidas instrucciones de instalación en Nono para el extra Garmin y el
  tokenstore Garmin Connect.
- Añadida documentación de automatización controlada Garmin Connect junto a
  Strava.

### Changed

- Actualizado README para reflejar que Garmin Connect v1 ya está operativo.
- Actualizado quickstart para incluir `garmin prepare-dirs` y la guía Garmin.
- Aclarado en la guía de Nono cuándo usar consolidado, raw/normalizado Strava,
  raw/normalizado Garmin, `garmin sync`, `garmin sync --skip-fetch`,
  `garmin decode-fit --activity-id` y `garmin clean-intermediates`.
- Aclarado que Garmin queda operativo por comando controlado y que cualquier
  timer futuro debe usar usuario `nono`, lock, ventana incremental y evitar
  `--force`.

### Verified

- Verificación local: `./.venv/bin/python scripts/check.py` con 131 tests
  pasados.

## [0.1.0] - 2026-07-01

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
- Añadida reprogramación adaptativa de `strava sync` con `systemd-run --user` cuando quedan actividades pendientes y hay cuota diaria.
- Añadido bloqueo opcional `--lock-file` para evitar solapes en automatización.
- Añadidas guías de uso para autenticación, descarga de contexto, descarga de actividades, normalización, consolidación y validación.
- Añadida guía de instalación en Nono con estrategia de usuario, permisos, tokens y preparación para webhooks futuros.
- Añadida guía de automatización controlada con propuesta de `systemd timer` de usuario.
- Añadida guía operativa y prompt sugerido para que Nono entienda, consulte y opere `nono-sports`.
- Añadida decisión aprobada de integración Garmin Connect en `docs/requirements/garmin-connect.md`.
- Añadida funcionalidad `doctor` para diagnóstico seguro de configuración, rutas, permisos, tokens, locks y estado local.
- Añadidos comandos `nono-sports doctor`, `nono-sports strava doctor` y `nono-sports garmin doctor`.
- Añadida guía `docs/usage/doctor.md`.
- Añadido extra opcional `garmin` con `garminconnect==0.3.6` para la prueba aislada Garmin Connect.
- Añadido script `scripts/garmin_connect_probe.py` y guía `docs/usage/garmin-connect-probe.md`.
- Añadido adaptador Garmin Connect base de solo lectura con autenticación por tokenstore, login interactivo, lectura de actividad y descarga FIT.
- Añadida descarga raw Garmin Connect inicial con manifiesto, estado reanudable y comando `nono-sports garmin fetch-activities`.
- Añadido módulo independiente `nono_sports.formats.fit` con extracción de FIT directo o dentro de ZIP.
- Añadido comando offline `nono-sports garmin decode-fit`.
- Añadido extra opcional `fit` con `fitdecode==0.11.0`.
- Añadido extra opcional `fit-compare` con `fitdecode` y `garmin-fit-sdk` para
  comparación de decodificadores.
- Añadido comando fuente-independiente `nono-sports fit compare-decoders`.
- Añadida consolidación multi-fuente inicial en `consolidation.multi_source`.
- Añadido informe consolidado `duplicate_candidates.jsonl`.
- Añadida normalización Garmin Connect inicial para actividades, streams FIT,
  laps, splits, typed splits, candidatos de segmento y estado.
- Añadido comando `nono-sports garmin normalize`.
- Añadido comando `nono-sports garmin sync` para encadenar descarga raw,
  decodificación FIT, normalización y consolidación.
- Añadido parser seguro GPX/TCX con `defusedxml` para normalizar tracks de
  actividades Garmin importadas sin FIT.
- Nono documentó el 2026-06-25 el uso de Wikiloc como fuente auxiliar externa
  para planificación de rutas, cruzada con Open-Meteo, Google Maps, datos
  deportivos consolidados y fuentes oficiales cuando proceda.

### Changed

- `garmin sync` deja de persistir JSON FIT decodificados y normaliza
  directamente desde el FIT raw para evitar agotar la capacidad de Drive.
- La huella incremental Garmin depende del FIT original, no del derivado
  `fitdecode.json`, que puede borrarse de forma segura.
- La normalización FIT diaria limita la decodificación a los mensajes necesarios
  para el contrato común y reutiliza normalizados aunque no existan derivados
  `fit_decoded`.
- `garmin decode-fit` requiere `--activity-id` para evitar generar derivados
  masivos por accidente.
- Añadido `garmin clean-intermediates` para eliminar derivados de diagnóstico
  y `--keep-intermediate-files` en `garmin normalize`/`garmin sync` para debug
  excepcional.
- La reutilización incremental Garmin sanea referencias históricas a
  `fit_decoded` ausentes sin forzar la decodificación completa de todos los FIT.
- Garmin Connect incorpora ventana incremental diaria alineada con Strava:
  `--after`, `--before`, `--full-scan`, `--incremental-lookback-days` y marca
  `last_successful_activity_sync_at` en `activity_sync_state.json`.
- Auditado y reparado el raw Garmin tras agotarse el espacio de Drive: nueve
  actividades redescargadas, payloads mal ubicados corregidos y derivados FIT
  voluminosos eliminados.
- Ampliado el matching Garmin-Strava para reconocer importaciones indoor con
  taxonomías distintas y salidas ciclistas cuyo inicio fue activado antes de
  comenzar el movimiento.
- La clasificación deportiva Garmin prevalece en actividades consolidadas con
  ambas fuentes.
- Aclarado que `duplicate_candidates.jsonl` registra agrupaciones ya aplicadas,
  no duplicados pendientes adicionales.
- Reorganizada la arquitectura documental del proyecto.
- Definido `Descripcion_inicial.md` como documento de entrada no normativo.
- Archivado el bootstrap inicial en `deprecated/initial-bootstrap/` y mantenido fuera del código activo.
- Cambiada la descarga de zonas de actividad a opt-in porque Strava la documenta como Summit Feature.
- Ampliado el raw gratuito con laps, gear desde actividades, segmentos favoritos/referenciados, club detail, route streams y exports GPX/TCX.
- Actualizada la arquitectura técnica para reflejar capas raw, normalizado, consolidado y validación.
- Nono ajustó el 2026-06-25 la reprogramación adaptativa para que `raw.streams_incomplete`,
  `raw.laps_incomplete` y `raw.recoverable_errors` no provoquen por sí solos
  nuevas ejecuciones si no hay actividades realmente pendientes.
- Nono cambió las unidades transient de `systemd-run` para usar sufijos únicos y
  evitar colisiones entre ejecuciones adaptativas.
- Nono hizo la lectura del índice de manifiesto raw más tolerante a líneas JSON
  corruptas durante la normalización.
- Nono documentó el uso de Drive como raíz operativa única y la recuperación
  segura de `nono-drive.service` si el mount FUSE queda inconsistente.
- Separado el análisis Garmin Connect del documento de decisión aprobada y alineados requisitos, arquitectura, roadmap, backlog, plan de trabajo y TODO.
- Enriquecida la salida FIT decodificada para conservar metadatos por campo:
  `def_num`, `raw_value`, unidades y tipos.
- `build-consolidated` usa ahora la estrategia `multi_source_initial`, manteniendo
  Strava como fuente primaria inicial por compatibilidad.
- La validación acepta actividades consolidadas con más de un enlace fuente.
- La normalización Garmin es incremental y reutiliza actividades cuyo raw/FIT no
  ha cambiado.
- La descarga raw Garmin pagina automáticamente el listado y salta actividades
  ya completas hasta encontrar pendientes, evitando quedar bloqueada en las
  primeras actividades del histórico.
- La descarga raw Garmin conserva siempre el ZIP `ORIGINAL`; si no contiene FIT,
  intenta GPX/TCX como fallback y registra warning en vez de error recuperable.
- Las actividades Garmin importadas desde GPX/TCX pueden quedar como completas
  sin FIT y se marcan con `source_origin`, por ejemplo `imported_gpx`.
- La normalización Garmin conserva explícitamente `original_file_format` e
  `is_original` para que Nono pueda decidir cuándo recurrir al fichero original.
- El store normalizado evita reescribir ficheros cuando el contenido no cambia.

### Verified

- Validada instalación local de `garminconnect==0.3.6` mediante `nono-sports garmin doctor`.
- Validada prueba aislada Garmin Connect con login inicial, tokenstore, segunda ejecución sin credenciales, listado de actividades, detalle, splits, typed splits, split summaries, weather y FIT.
- Validados tests unitarios del adaptador Garmin Connect con mocks, sin llamadas reales a Garmin.
- Validada descarga real local de 1 actividad Garmin Connect y segunda ejecución idempotente.
- Validado que Garmin `ORIGINAL` entrega ZIP; ahora se conserva `.original.zip` y se extrae `.fit`.
- Validado caso real Garmin `18858207006`: el ZIP `ORIGINAL` contenía
  `18858207006_ACTIVITY.gpx`, no FIT; GPX y TCX se pudieron recuperar y la
  descarga acotada terminó con `0 recoverable errors`.
- Validado FIT real con `fitdecode`: 6844 frames, 20 tipos de mensajes, 2480 records, 4254 HRV y 0 errores.
- Comparado FIT real con `fitdecode` y `garmin-fit-sdk`: mismos tipos de
  mensaje y volúmenes principales; las diferencias fueron alias/metadatos, no
  datos deportivos adicionales exclusivos del SDK oficial.
- Validada normalización Garmin real de la actividad `23422332225`.
- Validado que Garmin `23422332225` y Strava `19114956119` se consolidan como
  una única actividad con confianza `0.97`.
- Ejecutada autenticación real de Strava por el usuario.
- Ejecutada descarga real de perfil/contexto y descarga incremental real de actividades.
- Confirmado límite operativo de Strava de `100/1000` peticiones de lectura.
- Ejecutada normalización real de 34 actividades descargadas.
- Ejecutada consolidación real de 34 actividades normalizadas.
- Ejecutada validación real con estado `warning` por descarga incompleta esperada debido a rate limit.
- Ejecutada validación de compatibilidad en Nono con Python 3.14.4: `scripts/check.py` con 67 tests pasados y `strava validate` correcto.
- Ejecutada instalación persistente en Nono con configuración XDG, tokens copiados con permisos `600` y prueba real de autenticación Strava detenida correctamente por cuota diaria `996/1000`.
- Ejecutada prueba local de `strava sync --skip-fetch --schedule-next-if-pending` sin llamar a Strava.
- Verificación local actual: `python3 scripts/check.py` con 120 tests pasados.
- Nono verificó el 2026-06-25 que, con el estado real actual (`state.last_run_stopped`,
  `raw.streams_incomplete`, `raw.recoverable_errors`), la nueva decisión
  adaptativa es no programar otra ejecución.
- Nono verificó el 2026-06-25 que `raw.activities_incomplete` y
  `state.activities_pending_completion` sí siguen programando otra ejecución si
  hay cuota diaria.

## 0.1.0 - 2026-05-24
- Creación del repositorio inicial.
- Añadidos módulos de sincronización, normalización e integración.
- Añadida primera versión de la documentación y estructura de datos.
