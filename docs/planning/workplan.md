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
- configurar `.env`
- configurar `NONO_SPORT_DATA_ROOT`
- ejecutar autenticación si es necesaria
- ejecutar primera sincronización completa

Entregables:

- instrucciones de despliegue
- verificación en entorno Nono
- primer dataset real accesible por Nono

Validación de usuario:

- el usuario confirma que Nono ve los datos consolidados
- pendiente: ejecutar comprobación en `nono.carlos.prades.name`
- pendiente: confirmar que `NONO_SPORT_DATA_ROOT` resuelve a `/home/nono/drive/01_ambitos/02_personal/40_deporte`
- pendiente: confirmar permisos de configuración y tokens

## Paso 12. Automatización controlada

Objetivo:

- definir ejecución manual o programada
- preparar logs
- dejar pendiente webhook para una versión posterior

Entregables:

- comando de sincronización repetible
- propuesta de `systemd timer` o tarea equivalente

Validación:

- una ejecución incremental no duplica datos
- el informe muestra cambios esperados
