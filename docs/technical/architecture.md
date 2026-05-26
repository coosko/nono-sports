# Arquitectura técnica

Este documento es la fuente de verdad técnica del proyecto.

## Objetivo de la v1

La primera versión debe permitir que Nono recoja de Strava la información más completa posible del atleta autenticado, preserve los datos originales y genere una base normalizada preparada para consolidación posterior.

La v1 se centra solo en Strava, pero la arquitectura debe permitir añadir Garmin, Komoot o importaciones manuales sin rehacer el núcleo.

## Fuentes oficiales consultadas

- Strava Authentication: https://developers.strava.com/docs/authentication/
- Strava OAuth scopes: https://developers.strava.com/docs/oauth-updates/
- Strava API Reference: https://developers.strava.com/docs/reference/
- Strava Rate Limits: https://developers.strava.com/docs/rate-limits/
- Strava Webhooks: https://developers.strava.com/docs/webhooks/

## Alcance Strava v1

Datos a recoger:

- atleta autenticado
- zonas del atleta si el scope concedido lo permite
- estadísticas agregadas del atleta
- listado paginado de actividades
- detalle completo de cada actividad
- streams de actividad
- zonas de actividad cuando estén disponibles
- equipo referenciado por actividades
- rutas del atleta cuando estén disponibles y el scope lo permita
- clubes del atleta como contexto secundario

Scopes previstos:

- `read`
- `read_all`
- `profile:read_all`
- `activity:read_all`

No se pedirá `activity:write` ni `profile:write` en la v1.

## Capas del sistema

```text
CLI
  -> configuración
  -> autenticación Strava
  -> cliente Strava
  -> sincronización
  -> almacenamiento raw
  -> normalización
  -> consolidación inicial
  -> validación
```

## Módulos propuestos

```text
src/nono_sports/
├── __main__.py
├── cli.py
├── core/
│   ├── config.py
│   ├── paths.py
│   ├── logging.py
│   └── errors.py
├── auth/
│   ├── strava_oauth.py
│   └── token_store.py
├── strava/
│   ├── client.py
│   ├── endpoints.py
│   ├── sync.py
│   └── rate_limits.py
├── storage/
│   ├── raw_store.py
│   ├── consolidated_store.py
│   ├── normalized_store.py
│   ├── state_store.py
│   └── manifest.py
├── domain/
│   ├── source.py
│   ├── activity.py
│   ├── athlete.py
│   └── stream.py
├── normalization/
│   ├── strava_activity.py
│   ├── strava_athlete.py
│   ├── strava_dataset.py
│   └── strava_stream.py
├── consolidation/
│   └── single_source.py
└── validation/
    ├── checks.py
    └── reports.py
```

## Responsabilidades por módulo

### `cli.py`

Expone comandos de usuario:

- `nono-sports strava auth`
- `nono-sports strava fetch-context`
- `nono-sports strava fetch-activities`
- `nono-sports strava sync`
- `nono-sports strava validate`
- `nono-sports build-consolidated`

### `core`

Responsable de configuración común:

- leer `.env`
- validar variables obligatorias
- resolver `NONO_SPORT_DATA_ROOT`
- cargar configuración desde entorno, `~/.config/nono-sports/env` o `.env` de desarrollo
- configurar logging
- definir errores comunes

### `auth`

Responsable del ciclo OAuth:

- construir la URL de autorización
- guiar al usuario hasta Strava
- recibir o aceptar el `code` de autorización
- intercambiar `code` por tokens
- refrescar access tokens caducados
- validar scopes concedidos
- persistir tokens fuera del repositorio y fuera del root de datos deportivos
- usar por defecto `~/.local/state/nono-sports/strava_tokens.json`

### `strava`

Responsable de hablar con la API:

- envolver `httpx`
- añadir autenticación
- paginar respuestas
- leer cabeceras de rate limit
- exponer endpoints de alto nivel
- no conocer el formato final de almacenamiento

Endpoints v1:

- `GET /athlete`
- `GET /athlete/zones`
- `GET /athletes/{id}/stats`
- `GET /clubs/{id}`
- `GET /athlete/activities`
- `GET /activities/{id}`
- `GET /activities/{id}/laps`
- `GET /activities/{id}/streams`
- `GET /activities/{id}/zones` solo bajo demanda; Strava Summit Feature
- `GET /gear/{id}`
- `GET /athletes/{id}/routes`
- `GET /routes/{id}`
- `GET /routes/{id}/streams`
- `GET /routes/{id}/export_gpx`
- `GET /routes/{id}/export_tcx`
- `GET /athlete/clubs`
- `GET /segments/starred`
- `GET /segments/{id}`
- `GET /segments/{id}/streams`

No se usan en v1:

- `GET /segment_efforts` ni `GET /segment_efforts/{id}` porque requieren suscripción
- `GET /activities/{id}/comments` ni `GET /activities/{id}/kudos` porque son datos sociales/de terceros

### `storage`

Responsable de escritura y estado:

- guardar cada respuesta raw como JSON
- escribir normalizados en JSONL
- mantener índices auxiliares
- registrar `state.json`
- guardar manifiestos con fecha, endpoint, parámetros, hash y fichero generado

### `domain`

Define contratos internos estables:

- `SourceRecord`
- `NormalizedAthlete`
- `NormalizedActivity`
- `NormalizedStream`
- `ConsolidatedActivity`
- `ActivitySourceLink`

Estos modelos no deben depender de Strava.

### `normalization`

Convierte raw de Strava a modelos comunes:

- atleta
- actividad
- streams
- zonas
- equipo
- rutas

La normalización nunca debe borrar la trazabilidad hacia el fichero raw original.

La salida normalizada Strava v1 se escribe como JSONL en:

- `10_fuentes/strava/normalizado/athletes.jsonl`
- `10_fuentes/strava/normalizado/activities.jsonl`
- `10_fuentes/strava/normalizado/streams.jsonl`

Los modelos usan identificadores estables `strava:<tipo>:<id>`, unidades SI y campos opcionales para deportes sin distancia clara o para datos complementarios de futuras fuentes.

### `consolidation`

En la v1 solo trabaja con una fuente.

Responsabilidad:

- crear una primera vista consolidada desde Strava
- conservar `source = strava`
- dejar preparado el modelo para futuras fuentes

La salida consolidada inicial se escribe en:

- `20_consolidado/activities.jsonl`
- `20_consolidado/activity_sources.jsonl`
- `20_consolidado/streams_index.jsonl`
- `20_consolidado/state.json`

En la v1 la estrategia es `single_source`: cada actividad consolidada procede de una única actividad normalizada Strava con `match_confidence = 1.0`.

### `validation`

Responsable de comprobar la calidad del resultado:

- estructura de carpetas correcta
- número de actividades esperadas frente a descargadas
- presencia de detalles y streams por actividad cuando proceda
- errores de API y rate limits registrados
- coherencia entre raw, normalizado y consolidado
- informe legible para revisión del usuario

La validación de datos es offline: no llama a Strava ni consume rate limit. La validación de tokens/scopes se realiza durante autenticación y cliente HTTP.

## Flujo de datos Strava v1

```text
auth usuario
  -> token_store
  -> strava client
  -> raw_store
  -> normalization
  -> normalized_store
  -> consolidation inicial
  -> validation report
```

El comando operativo `nono-sports strava sync` encadena descarga incremental, normalización, consolidación y validación. Con `--skip-fetch` ejecuta solo la parte offline.

## Estructura de datos objetivo

```text
<data_root>/
├── 00_referencia/
├── 10_fuentes/
│   └── strava/
│       ├── raw/
│       │   ├── athlete/
│       │   ├── activities/
│       │   ├── clubs/
│       │   ├── errors/
│       │   ├── streams/
│       │   ├── zones/
│       │   ├── gear/
│       │   ├── laps/
│       │   ├── routes/
│       │   ├── route_exports/
│       │   ├── route_streams/
│       │   ├── segments/
│       │   ├── segment_streams/
│       │   └── manifest.jsonl
│       ├── normalizado/
│       │   ├── athletes.jsonl
│       │   ├── activities.jsonl
│       │   └── streams.jsonl
│       └── logs/
│           └── activity_sync_state.json
├── 20_consolidado/
│   ├── activities.jsonl
│   ├── activity_sources.jsonl
│   ├── streams_index.jsonl
│   └── state.json
├── 30_analisis/
│   ├── informes/
│   │   └── strava_validation_report.md
│   ├── planes/
│   ├── seguimiento/
│   └── graficas/
└── 90_archivo/
```

Los secretos de autenticación no viven en `<data_root>`. Los tokens OAuth de Strava se guardan como estado local de aplicación:

```text
~/.local/state/nono-sports/strava_tokens.json
```

## Decisiones técnicas

- La fuente raw manda: cualquier dato derivado debe poder trazarse al JSON original.
- La sincronización debe ser reanudable e idempotente.
- El cliente debe respetar rate limits usando cabeceras de respuesta.
- El usuario debe participar explícitamente en la autorización OAuth inicial.
- La v1 debe ser de solo lectura.
- La instalación en Nono debe usar variables de entorno y datos fuera del repositorio.
- La configuración persistente en Nono debe vivir en `~/.config/nono-sports/env` con permisos restrictivos.
- Los tokens OAuth deben tratarse como estado sensible local, no como datos deportivos.
- La v1 debe ejecutarse como usuario `nono`; un webhook futuro expuesto a Internet debe separar listener sin secretos y worker con permisos de sincronización.
- La automatización debe usar presupuestos preventivos de rate limit y generar siempre informe de validación.

## Fuera de alcance de la v1

- escritura o modificación de datos en Strava
- webhooks productivos
- soporte Garmin, Komoot o ficheros manuales
- deduplicación compleja entre fuentes
- análisis deportivo avanzado
