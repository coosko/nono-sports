# Plan de trabajo Strava v1

Este documento define los pasos de implementación de la primera versión. Cada paso debe completarse y validarse antes de pasar al siguiente.

## Paso 1. Cierre de arquitectura Strava v1

Objetivo:

- revisar y aprobar la arquitectura de `docs/technical/architecture.md`
- confirmar endpoints, scopes y estructura de datos

Entregables:

- arquitectura aprobada
- lista de módulos confirmada
- alcance v1 cerrado

Validación de usuario:

- completado: el usuario confirma que el alcance de Strava v1 es correcto

## Paso 2. Scaffold de módulos

Objetivo:

- crear la estructura de paquetes propuesta
- añadir módulos vacíos con responsabilidades claras
- mantener el código sin lógica de negocio todavía

Entregables:

- paquetes `core`, `auth`, `strava`, `storage`, `domain`, `normalization`, `consolidation` y `validation`
- tests mínimos de importación

Validación:

- completado: `python3 scripts/check.py`

## Paso 3. Configuración y rutas

Objetivo:

- cargar `.env`
- validar `NONO_SPORT_DATA_ROOT`
- resolver rutas de datos
- preparar estructura de directorios Strava v1

Entregables:

- módulo `core.config`
- módulo `core.paths`
- tests de configuración y rutas
- comando `nono-sports strava prepare-dirs`

Validación de usuario:

- local confirmado: `/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte`
- pendiente: confirmar ruta real de datos en Nono

## Paso 4. Autenticación Strava con intervención del usuario

Objetivo:

- implementar OAuth de Strava
- generar URL de autorización
- capturar o aceptar el `code`
- intercambiar `code` por tokens
- validar scopes concedidos
- guardar refresh token vigente fuera del repositorio y del root de datos

Scopes esperados:

- `read`
- `read_all`
- `profile:read_all`
- `activity:read_all`

Entregables:

- comando `nono-sports strava auth`
- `auth.strava_oauth`
- `auth.token_store`
- tests unitarios con mocks
- guía `docs/usage/strava-auth.md`

Validación de usuario:

- el usuario entra en Strava
- acepta permisos
- confirma que el comando guarda tokens correctamente
- confirma que el token queda en `~/.local/state/nono-sports/strava_tokens.json`
- confirma que los scopes concedidos son suficientes
- completado: validado por el usuario

## Paso 5. Cliente Strava base

Objetivo:

- implementar cliente HTTP de solo lectura
- refrescar access token cuando caduque
- paginar endpoints
- registrar cabeceras de rate limit
- normalizar errores de API

Entregables:

- `strava.client`
- `strava.rate_limits`
- tests con respuestas mock

Validación:

- tests unitarios de token refresh, errores, paginación y rate limits
- completado: `python3 scripts/check.py`

## Paso 6. Descarga raw de perfil y contexto

Objetivo:

- descargar atleta autenticado
- descargar zonas del atleta si el scope lo permite
- descargar estadísticas agregadas
- descargar clubes y rutas disponibles
- descargar detalle de clubes
- descargar streams y export GPX/TCX de rutas
- descargar segmentos favoritos y segmentos referenciados por rutas
- descargar equipo referenciado cuando aparezca

Entregables:

- `strava.endpoints`
- `storage.raw_store`
- ficheros raw en `10_fuentes/strava/raw/`
- comando `nono-sports strava fetch-context`
- guía `docs/usage/strava-fetch-context.md`

Validación de usuario:

- el usuario revisa que los ficheros raw esperados existen
- el usuario confirma que no se ha escrito nada en Strava
- completado: el usuario confirma que el Paso 6 está completo

## Paso 7. Descarga raw de actividades con máximo detalle

Objetivo:

- listar todas las actividades disponibles
- descargar detalle completo de cada actividad
- descargar laps de cada actividad
- descargar streams de cada actividad
- descargar equipo referenciado por actividades
- descargar segmentos referenciados por actividades y sus streams
- no descargar zonas de actividad por defecto porque Strava las documenta como Summit Feature
- permitir zonas de actividad solo bajo demanda
- guardar errores recuperables sin abortar toda la sincronización
- parar de forma preventiva antes de superar el presupuesto de rate limit de lectura

Entregables:

- `strava.sync`
- `storage.state_store`
- raw por actividad
- estado de sincronización reanudable
- comando `nono-sports strava fetch-activities`
- flags de protección `--max-read-requests-15min`, `--max-read-requests-daily` y `--rate-limit-reserve`
- guía `docs/usage/strava-fetch-activities.md`

Validación de usuario:

- el usuario compara el número de actividades descargadas con Strava
- el usuario revisa una actividad concreta en Strava y en raw
- validación técnica: prueba real por lotes ejecutada contra Strava
- pendiente: completar lotes restantes y revisión manual del usuario

## Paso 8. Normalización Strava

Objetivo:

- definir modelos comunes en `domain`
- convertir atleta, actividades y streams a formato normalizado
- conservar referencias a ficheros raw

Entregables:

- `domain.activity`
- `domain.athlete`
- `domain.stream`
- `normalization.strava_activity`
- `normalization.strava_athlete`
- `normalization.strava_stream`
- `normalization.strava_dataset`
- `storage.normalized_store`
- comando `nono-sports strava normalize`
- JSONL normalizados

Validación:

- tests de normalización con fixtures raw
- completado: `python3 scripts/check.py`
- completado: normalización real local de raw disponibles a JSONL
- pendiente: revisión manual de una actividad representativa por el usuario

## Paso 9. Consolidación inicial

Objetivo:

- crear una vista consolidada desde Strava como única fuente
- generar `activity_source_link`
- dejar preparado el modelo para futuras fuentes

Entregables:

- `consolidation.single_source`
- `storage.consolidated_store`
- comando `nono-sports build-consolidated`
- `20_consolidado/activities.jsonl`
- `20_consolidado/activity_sources.jsonl`
- `20_consolidado/streams_index.jsonl`
- `20_consolidado/state.json`

Validación:

- completado: `python3 scripts/check.py`
- completado: consolidación real local desde normalizados disponibles
- pendiente: el usuario confirma que Nono debe consumir `20_consolidado/` como entrada principal

Validación de usuario:

- el usuario confirma que Nono debe consumir `20_consolidado/` como entrada principal

## Paso 10. Validación de datos

Objetivo:

- comprobar estructura de carpetas
- comprobar conteos
- comprobar actividades sin detalle, sin stream o con errores
- generar informe de validación

Entregables:

- `validation.checks`
- `validation.reports`
- comando `nono-sports strava validate`

Validación técnica:

- completado: `python3 scripts/check.py`
- completado: informe real generado en `30_analisis/informes/strava_validation_report.md`

Validación de usuario:

- el usuario revisa el informe
- el usuario decide si se repite sincronización, se acepta el resultado o se ajusta alcance

## Paso 11. Instalación en Nono

Objetivo:

- preparar instalación en el entorno Linux de Nono
- configurar `~/.config/nono-sports/env`
- configurar `NONO_SPORT_DATA_ROOT`
- copiar tokens OAuth si se reutiliza autorización existente
- ejecutar validación y prueba de autenticación contenida

Entregables:

- instrucciones de despliegue
- verificación en entorno Nono
- primer dataset real accesible por Nono

Validación de usuario:

- completado: validación temporal en Nono con Python 3.14.4, 67 tests pasados y `strava validate` correcto
- completado: instalación persistente en `/home/nono/apps/nono-sport`
- completado: `NONO_SPORT_DATA_ROOT` resuelve a `/home/nono/drive/01_ambitos/02_personal/40_deporte`
- completado: `20_consolidado` es visible para Nono desde Google Drive
- completado: configuración XDG en `/home/nono/.config/nono-sports/env`
- completado: tokens copiados a `/home/nono/.local/state/nono-sports/strava_tokens.json` con permisos `600`
- completado: prueba real de autenticación Strava ejecutada; parada preventiva por cuota diaria `996/1000`

## Paso 12. Automatización controlada

Objetivo:

- definir ejecución manual o programada
- preparar logs
- dejar pendiente webhook para una versión posterior
- mantener salvaguardas de rate limit en ejecución diaria

Entregables:

- comando de sincronización repetible
- propuesta de `systemd timer` o tarea equivalente
- reprogramación adaptativa con `systemd-run --user`
- bloqueo de solapes con `--lock-file`
- guía `docs/usage/automation.md`

Validación:

- una ejecución incremental no duplica datos
- el informe muestra cambios esperados
- pendiente: ejecutar `strava sync` con descarga cuando se libere cuota diaria
- completado: comando `strava sync --skip-fetch` permite probar la parte offline sin llamar a Strava

## Paso 13. Doctor común

Objetivo:

- crear una capacidad de diagnóstico segura antes de sincronizar
- comprobar configuración, permisos, rutas, tokens, locks y estructura de datos
- evitar llamadas de descarga por defecto
- producir salida accionable para usuario y Nono

Entregables:

- completado: diseño común de `doctor`
- completado: comprobaciones de Python, configuración XDG y `NONO_SPORT_DATA_ROOT`
- completado: comprobaciones de secretos fuera de repositorio y fuera de Drive
- completado: comando `nono-sports doctor`
- completado: comandos `nono-sports strava doctor` y `nono-sports garmin doctor`
- completado: base reutilizable por fuente

Validación:

- completado: tests unitarios con rutas temporales
- completado: salida clara con estado `ok`, `warning` o `error`
- pendiente: ejecución en Nono cuando se despliegue la nueva versión

## Paso 14. Decisión y prueba aislada Garmin Connect

Objetivo:

- validar `garminconnect==0.3.6` en entorno aislado
- probar login inicial y tokenstore
- confirmar si una segunda ejecución funciona sin introducir credenciales
- descargar una actividad de prueba sin incorporarla todavía al flujo principal

Entregables:

- completado: dependencia Garmin Connect fijada para prueba como extra opcional `garmin`
- completado: script aislado `scripts/garmin_connect_probe.py`
- completado: guía `docs/usage/garmin-connect-probe.md`
- completado: instalación local de `garminconnect==0.3.6` validada con `garmin doctor`
- completado: prueba aislada de autenticación con usuario Garmin
- completado: prueba aislada de listado de actividades
- completado: prueba aislada de descarga de detalle y FIT
- completado: registro inicial de conclusiones sobre tokenstore/autonomía

Validación de usuario:

- completado: el usuario participa en la autenticación inicial
- completado: no consta MFA/captcha en la prueba pegada por el usuario
- completado: la segunda ejecución reutiliza tokenstore sin pedir credenciales
- completado: Garmin devolvió `429` en intentos mobile previos, pero el login terminó correctamente
- decisión: tokenstore es viable para la siguiente fase; evitar relogueos repetidos
- pendiente: validar autonomía en Nono cuando se instale allí

## Paso 15. Adaptador Garmin Connect base

Objetivo:

- encapsular `python-garminconnect` como adaptador sustituible
- exponer operaciones de solo lectura
- no acoplar el core a Garmin

Entregables:

- completado: `nono_sports/garmin_connect/client.py`
- completado: `nono_sports/garmin_connect/auth.py`
- completado: `nono_sports/garmin_connect/sync.py`
- completado: `nono_sports/garmin_connect/doctor.py`
- completado: script aislado refactorizado para usar el adaptador
- completado: tests con mocks controlados

Validación:

- completado: `nono-sports garmin doctor`
- completado: listado controlado de actividades en tests
- completado: lectura de snapshot Garmin en tests sin escritura remota
- pendiente: usar el adaptador para persistencia raw en Paso 16

## Paso 16. Descarga raw Garmin Connect

Objetivo:

- crear estructura `10_fuentes/garmin_connect`
- descargar raw con manifiesto y estado reanudable
- preservar FIT original y ficheros GPX/TCX disponibles
- descargar splits, typed splits, laps, weather y candidatos de segmentos

Entregables:

- completado: `raw/manifest.jsonl`
- completado: `raw/activities/<id>.json`
- completado: `raw/activities/<id>.details.json`
- completado: `raw/activity_files/<id>.fit`
- completado: `raw/splits/<id>.json`
- completado: `raw/splits/<id>.summaries.json`
- completado: `raw/typed_splits/<id>.json`
- completado: `raw/weather/<id>.json`
- completado: `logs/activity_sync_state.json`
- pendiente: `raw/laps/<id>.json` separado si Garmin lo ofrece fuera de `splits/lapDTOs`
- pendiente: `raw/segment_candidates/<id>.json` cuando se identifiquen bloques de segmentos

Validación de usuario:

- completado: descarga real local de 1 actividad Garmin Connect
- completado: segunda ejecución idempotente saltó la actividad ya completa
- completado: `garmin doctor` no detecta secretos en `NONO_SPORT_DATA_ROOT`
- pendiente: revisión manual del usuario de una actividad concreta en Garmin Connect y en raw

## Paso 17. FIT y normalización Garmin Connect

Objetivo:

- completado: decidir estrategia de parseo FIT
- completado: conservar máxima información posible en raw y derivado decodificado
- completado: normalizar actividades Garmin Connect con trazabilidad a raw

Entregables:

- completado: decisión documentada sobre `fitdecode==0.11.0`
- completado: módulo independiente `nono_sports.formats.fit`
- completado: extracción de FIT desde ZIP `ORIGINAL` de Garmin
- completado: comando offline `nono-sports garmin decode-fit`
- completado: `raw/fit_decoded/<id>.fitdecode.json`
- completado: conservación de metadatos FIT por campo (`def_num`, `raw_value`,
  unidades y tipos)
- completado: comando fuente-independiente `nono-sports fit compare-decoders`
  para comparar `fitdecode` y `garmin-fit-sdk`
- completado: `normalizado/activities.jsonl`
- completado: `normalizado/streams.jsonl`
- completado: `normalizado/streams_index.jsonl`
- completado: `normalizado/laps.jsonl`
- completado: `normalizado/splits.jsonl`
- completado: `normalizado/typed_splits.jsonl`
- completado: `normalizado/segment_candidates.jsonl`
- completado: `normalizado/state.json`

Validación:

- completado: comparación técnica de `fitdecode`, `garmin-fit-sdk`, `fitparse` y `fit-tool`
- completado: FIT real decodificado con 6844 frames, 2480 records, 4254 HRV y 0 errores
- completado: comparación práctica `fitdecode` vs `garmin-fit-sdk` sobre FIT
  real, sin datos adicionales exclusivos del SDK oficial
- completado: tests de extracción FIT sin datos sensibles
- completado: comparación de Garmin `23422332225` frente a Strava
  `19114956119` en consolidación multi-fuente
- pendiente: comparación manual visual de una actividad Garmin frente a Garmin
  Connect

## Paso 18. Consolidación multi-fuente inicial

Objetivo:

- completado: permitir que una actividad consolidada tenga fuentes Strava y
  Garmin Connect
- completado: deduplicar inicialmente por fecha, duración, distancia y deporte
- completado: mantener trazabilidad completa mediante `activity_sources.jsonl`
- pendiente: selección avanzada de fuente primaria por métrica

Entregables:

- completado: `consolidation.multi_source`
- completado: `build-consolidated` usa `multi_source_initial`
- completado: `activity_sources.jsonl` con varios enlaces por actividad cuando
  proceda
- completado: `duplicate_candidates.jsonl`
- completado: validación adaptada a consolidación multi-fuente
- completado: test de orden inverso, si Garmin existía antes y Strava llega
  después

Validación de usuario:

- pendiente: revisar un conjunto pequeño de actividades duplicadas Strava/Garmin
- pendiente: aprobar reglas antes de aplicarlas masivamente
