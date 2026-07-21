# Arquitectura técnica

Este documento es la fuente de verdad técnica del proyecto.

## Objetivo operativo

El sistema debe permitir que Nono recoja datos deportivos, biométricos, de
atleta y de equipación desde Strava, Garmin Connect y fuentes manuales,
preserve los datos originales y genere una capa normalizada y consolidada
preparada para consulta y análisis.

La arquitectura debe permitir añadir Garmin, Komoot, rutas externas o
importaciones manuales FIT/GPX/TCX/CSV sin rehacer el núcleo.

## Fuentes oficiales consultadas

- Strava Authentication: https://developers.strava.com/docs/authentication/
- Strava OAuth scopes: https://developers.strava.com/docs/oauth-updates/
- Strava API Reference: https://developers.strava.com/docs/reference/
- Strava Rate Limits: https://developers.strava.com/docs/rate-limits/
- Strava Webhooks: https://developers.strava.com/docs/webhooks/
- Garmin Connect Developer Program Activity API: https://developer.garmin.com/gc-developer-program/activity-api/
- python-garminconnect: https://github.com/cyberjunky/python-garminconnect

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
  -> tokenstore Garmin Connect
  -> clientes por fuente
  -> sincronización
  -> almacenamiento raw
  -> normalización
  -> consolidación multi-fuente
  -> validación
```

## Módulos propuestos

```text
src/nono_sports/
├── __main__.py
├── cli.py
├── core/
│   ├── config.py
│   ├── file_lock.py
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
├── garmin_connect/
│   ├── client.py
│   ├── auth.py
│   ├── endpoints.py
│   ├── sync.py
│   └── doctor.py
├── formats/
│   └── fit.py
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
│   ├── equipment.py
│   ├── measurement.py
│   └── stream.py
├── normalization/
│   ├── strava_activity.py
│   ├── strava_athlete.py
│   ├── strava_equipment.py
│   ├── strava_dataset.py
│   ├── strava_stream.py
│   ├── garmin_activity.py
│   ├── garmin_dataset.py
│   ├── garmin_measurements.py
│   ├── garmin_user_data.py
│   ├── garmin_stream.py
│   ├── manual_measurements.py
│   ├── measurement_utils.py
│   └── equipment_utils.py
├── consolidation/
│   ├── multi_source.py
│   ├── measurements.py
│   ├── single_source.py
│   └── user_data.py
├── automation/
│   └── adaptive.py
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
- ofrecer bloqueo de fichero para comandos operativos automatizados
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

### `garmin_connect`

Responsable de hablar con Garmin Connect mediante un adaptador encapsulado sobre `python-garminconnect`.

Reglas:

- solo lectura
- no acoplar el core a la librería externa
- usar inicialmente `garminconnect==0.3.6`
- poder sustituir el adaptador si cambia Garmin Connect o se usa una API oficial futura
- reutilizar tokenstore en ejecuciones automatizadas
- no reloguear en cada ejecución
- exponer diagnóstico mediante `nono-sports garmin doctor`

Datos objetivo:

- perfil/atleta mínimo
- listado de actividades
- detalle JSON por actividad
- FIT original
- GPX/TCX si están disponibles
- splits
- typed splits
- laps
- weather
- equipación usada por actividad cuando Garmin la exponga
- perfil/settings del usuario
- equipación declarada y estadísticas de equipación
- dispositivos Garmin conocidos, último dispositivo usado y dispositivo
  principal de entrenamiento cuando estén disponibles
- mediciones de peso/composición corporal
- candidatos de segmentos si aparecen en payloads o ficheros

Garmin preserva ficheros originales y contenedores. El parseo de FIT no vive en
Garmin, sino en `formats`.

### `formats`

Responsable de leer formatos deportivos reutilizables entre fuentes:

- FIT actual
- GPX futuro
- TCX futuro
- CSV/manual futuro

Regla estándar:

```text
raw original
→ extracción si el proveedor entrega ZIP u otro contenedor
→ lectura/decodificación transitoria del formato original
→ normalización por fuente
→ consolidación común
```

Para FIT, el backend inicial es `fitdecode==0.11.0`.

Razones:

- conserva información cercana al stream original
- expone mensajes/campos desconocidos
- soporta FIT encadenados
- coste razonable
- no acopla el proyecto al SDK oficial ni a Garmin Connect

`garmin-fit-sdk` queda como fallback o herramienta de contraste oficial.

El flujo normal no persiste derivados pesados de decodificación. Cuando se
necesite diagnóstico explícito de una actividad concreta, el derivado
`fit_decoded/<id>.fitdecode.json` debe conservar tanto valores normalizados
como metadatos de bajo nivel:

- valor decodificado directo por nombre de campo
- `_fit_message` con identificadores del mensaje FIT
- `_fit_fields` con `def_num`, `raw_value`, `value`, `units`, `type` y
  `base_type`

La comparación entre decodificadores es una capacidad común de `formats`, no de
Garmin. Debe poder ejecutarse sobre cualquier FIT futuro para detectar si
`garmin-fit-sdk` interpreta campos que el backend principal no esté exponiendo.

La normalización diaria de FIT debe limitarse a los mensajes necesarios para el
contrato común (`record`, `hrv`, `lap`, `time_in_zone`) y debe reutilizar la
salida normalizada si la huella de entrada no cambia, aunque no exista ningún
derivado `fit_decoded`.

### Incrementalidad Garmin

Garmin Connect usa el mismo patrón de control que Strava:

- `10_fuentes/garmin_connect/logs/activity_sync_state.json`
- lista de `runs`
- mapa `activities`
- marca `last_successful_activity_sync_at`

La sintaxis de ventana temporal se mantiene alineada con Strava mediante
`--after` y `--before` en Unix timestamp. A diferencia de Strava, la librería
Garmin Connect disponible no ofrece un filtro estable de "modified since"; por
eso el fetch incremental Garmin calcula `effective_after` a partir de la última
sincronización correcta menos un solape configurable
(`--incremental-lookback-days`, 7 días por defecto) y corta la paginación cuando
el listado ordenado por actividad llega a entradas anteriores a esa ventana.

Para backfills, auditorías o reparaciones se puede desactivar ese corte con
`--full-scan`. `--force` tampoco aplica la ventana incremental, porque su
objetivo es reconstruir raw de forma explícita.

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
- `NormalizedEquipment`
- `NormalizedMeasurement`
- `NormalizedStream`
- `ConsolidatedActivity`
- `ConsolidatedEquipment`
- `ActivitySourceLink`

Estos modelos no deben depender de Strava ni de Garmin Connect.

### `normalization`

Convierte raw de cada fuente a modelos comunes:

- atleta
- actividad
- streams
- zonas
- equipo
- mediciones
- rutas

La normalización nunca debe borrar la trazabilidad hacia el fichero raw original.

La salida normalizada por fuente se escribe como JSONL en:

- `normalizado/athletes.jsonl`
- `normalizado/equipment.jsonl`
- `normalizado/activities.jsonl`
- `normalizado/streams.jsonl`
- `normalizado/streams_index.jsonl`
- `normalizado/measurements.jsonl`
- `normalizado/state.json`

Los modelos usan identificadores estables `<fuente>:<tipo>:<id>`, unidades SI
y campos opcionales para deportes sin distancia clara o para datos
complementarios de futuras fuentes.

`equipment.jsonl` es el contrato común para bicicletas, zapatillas,
dispositivos, sensores o material equivalente. Las fuentes pueden aportar
información complementaria sobre la misma pieza: Strava puede aportar cambios o
uso histórico, Garmin Connect puede aportar uso del dispositivo o equipación por
actividad, y una fuente manual futura puede aportar peso, ruedas, cubiertas o
configuración real.

En `20_consolidado/equipment.jsonl`, `distance_m` representa la mejor distancia
consolidada disponible. Cuando existen actividades consolidadas con enlaces de
equipación, se calcula sumando cada actividad una sola vez y usando la primera
fuente prioritaria que declara ese equipo. Si una fuente prioritaria no declara
equipo y otra fuente de la misma actividad sí lo hace, se usa esa otra fuente.
La distancia declarada por las fuentes de equipación no se pierde: queda en
`attributes.usage.base_distance`, junto con `partial_distance_m`, tiempos de
uso, conteo de actividades y actividades no asignables por falta de enlace de
equipo. Los identificadores de equipo fuente evitan mezclar bicicletas,
zapatillas, dispositivos o sensores por similitud de nombre.

### `consolidation`

La estrategia activa es `multi_source_initial`.

Responsabilidad:

- crear una vista consolidada desde fuentes normalizadas disponibles
- mantener Strava como fuente primaria inicial por compatibilidad
- permitir varios enlaces fuente por actividad consolidada
- detectar duplicados candidatos entre Strava y Garmin Connect
- consolidar atleta/equipación entre fuentes
- consolidar mediciones biométricas y métricas puntuales
- conservar trazabilidad completa antes de elegir fuente por métrica

La salida consolidada inicial se escribe en:

- `20_consolidado/activities.jsonl`
- `20_consolidado/activity_sources.jsonl`
- `20_consolidado/streams_index.jsonl`
- `20_consolidado/athletes.jsonl`
- `20_consolidado/athlete_sources.jsonl`
- `20_consolidado/equipment.jsonl`
- `20_consolidado/equipment_sources.jsonl`
- `20_consolidado/measurements.jsonl`
- `20_consolidado/measurement_sources.jsonl`
- `20_consolidado/duplicate_candidates.jsonl`
- `20_consolidado/state.json`

La deduplicación usa señales conservadoras de fecha/hora, duración, distancia,
deporte y origen Garmin de la importación Strava. Contempla el inicio tardío de
Strava cuando tiempo en movimiento y distancia confirman que es la misma salida.
`duplicate_candidates.jsonl` audita agrupaciones ya aplicadas; no es una cola de
duplicados pendientes. En actividades emparejadas, Garmin prevalece para la
clasificación deportiva.

### `validation`

Responsable de comprobar la calidad del resultado:

- estructura de carpetas correcta
- número de actividades esperadas frente a descargadas
- presencia de detalles y streams por actividad cuando proceda
- errores de API y rate limits registrados
- coherencia entre raw, normalizado y consolidado
- informe legible para revisión del usuario

La validación de datos es offline: no llama a Strava ni consume rate limit. La validación de tokens/scopes se realiza durante autenticación y cliente HTTP.

### `doctor`

Los comandos `doctor` son diagnósticos seguros y previos a la sincronización.

Responsabilidades:

- comprobar versión de Python
- comprobar instalación de dependencias
- comprobar configuración XDG
- comprobar permisos de tokens, logs y locks
- comprobar `NONO_SPORT_DATA_ROOT`
- comprobar estructura de carpetas por fuente
- detectar placeholders o secretos mal ubicados
- leer estado local sin descargar datos por defecto
- emitir una salida accionable para usuario y Nono

### `automation`

Responsable de automatización operativa:

- decidir si una sincronización debe reprogramar otra tanda
- usar `systemd-run --user` para una única ejecución diferida
- evitar loops permanentes cuando no quedan pendientes o no hay cuota diaria suficiente

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
│   ├── strava/
│   │   ├── raw/
│   │   │   ├── athlete/
│   │   │   ├── activities/
│   │   │   ├── clubs/
│   │   │   ├── errors/
│   │   │   ├── streams/
│   │   │   ├── zones/
│   │   │   ├── gear/
│   │   │   ├── laps/
│   │   │   ├── routes/
│   │   │   ├── route_exports/
│   │   │   ├── route_streams/
│   │   │   ├── segments/
│   │   │   ├── segment_streams/
│   │   │   └── manifest.jsonl
│   │   ├── normalizado/
│   │   │   ├── athletes.jsonl
│   │   │   ├── equipment.jsonl
│   │   │   ├── activities.jsonl
│   │   │   ├── streams.jsonl
│   │   │   ├── streams_index.jsonl
│   │   │   └── state.json
│   │   └── logs/
│   │       └── activity_sync_state.json
│   ├── garmin_connect/
│   │   ├── raw/
│   │   │   ├── athlete/
│   │   │   ├── activities/
│   │   │   ├── activity_files/
│   │   │   ├── biometrics/
│   │   │   ├── devices/
│   │   │   ├── fit_decoded/          # diagnóstico explícito, no flujo normal
│   │   │   ├── gear/
│   │   │   ├── splits/
│   │   │   ├── typed_splits/
│   │   │   ├── laps/
│   │   │   ├── weather/
│   │   │   ├── segment_candidates/
│   │   │   └── manifest.jsonl
│   │   ├── normalizado/
│   │   │   ├── athletes.jsonl
│   │   │   ├── equipment.jsonl
│   │   │   ├── activities.jsonl
│   │   │   ├── streams.jsonl
│   │   │   ├── streams_index.jsonl
│   │   │   ├── laps.jsonl
│   │   │   ├── splits.jsonl
│   │   │   ├── typed_splits.jsonl
│   │   │   ├── segment_candidates.jsonl
│   │   │   ├── measurements.jsonl
│   │   │   ├── measurements_state.json
│   │   │   └── state.json
│   │   └── logs/
│   │       └── activity_sync_state.json
│   └── manual/
│       ├── biometria/
│       │   └── mediciones_carlos.csv
│       ├── normalizado/
│       │   ├── measurements.jsonl
│       │   └── measurements_state.json
│       ├── logs/
│       └── sensaciones/
├── 20_consolidado/
│   ├── activities.jsonl
│   ├── activity_sources.jsonl
│   ├── streams_index.jsonl
│   ├── athletes.jsonl
│   ├── athlete_sources.jsonl
│   ├── equipment.jsonl
│   ├── equipment_sources.jsonl
│   ├── measurements.jsonl
│   ├── measurement_sources.jsonl
│   ├── measurements_state.json
│   └── state.json
├── 30_analisis/
│   ├── informes/
│   │   └── strava_validation_report.md
│   ├── planes/
│   ├── seguimiento/
│   └── graficas/
└── 90_archivo/
```

Contrato mínimo por fuente normalizada:

- `normalizado/activities.jsonl`: actividades en el esquema común.
- `normalizado/athletes.jsonl`: perfil/atleta normalizado cuando la fuente lo
  aporta.
- `normalizado/equipment.jsonl`: equipación/dispositivos normalizados cuando
  la fuente los aporta.
- `normalizado/streams.jsonl`: streams normalizados cuando existan.
- `normalizado/streams_index.jsonl`: índice ligero para localizar streams sin
  leer todo el fichero de streams.
- `normalizado/state.json`: estado, entradas, salidas y conteos de la última
  normalización.
- `logs/activity_sync_state.json`: estado incremental de descarga/sincronización.

Cada fuente puede añadir ficheros específicos si aportan valor real. Garmin
Connect añade `laps.jsonl`, `splits.jsonl`, `typed_splits.jsonl` y
`segment_candidates.jsonl`; Strava y Garmin Connect escriben `athletes.jsonl`
y `equipment.jsonl` como contrato común.

Contrato de mediciones:

- Cada fuente que aporte biometría o métricas puntuales escribe
  `normalizado/measurements.jsonl`.
- Cada medición normalizada incluye `metric`, `value`, `unit`,
  `measurement_date`, `measured_at_utc`, `source_reference` y `attributes`.
- El consolidado escribe `20_consolidado/measurements.jsonl` y
  `20_consolidado/measurement_sources.jsonl`.
- La deduplicación inicial agrupa mediciones de la misma métrica, fecha, unidad
  y valor equivalente. Garmin Connect tiene prioridad frente a entradas
  manuales cuando ambas representan la misma medición importada desde Garmin.

Los secretos de autenticación no viven en `<data_root>`. Los tokens OAuth de Strava se guardan como estado local de aplicación:

```text
~/.local/state/nono-sports/strava_tokens.json
```

Garmin Connect debe usar el mismo criterio:

```text
~/.local/state/nono-sports/garmin_connect/tokenstore/
```

No hay, por ahora, configuración específica Garmin en
`~/.config/nono-sports/garmin_connect/config.toml` ni estado adicional en
`~/.local/state/nono-sports/garmin_connect/auth_state.json`. Si se necesitan en
el futuro, deberán incorporarse como una decisión explícita de arquitectura.

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
- La puesta al día histórica debe usar reprogramación adaptativa, no un timer cada 15 minutos permanente.
- Las fuentes no oficiales, como Garmin Connect mediante `python-garminconnect`, deben estar encapsuladas como adaptadores sustituibles.
- Los comandos `doctor` deben diagnosticar configuración, permisos y estado local sin descargar datos por defecto.
- Garmin Connect debe probar primero autonomía por tokens; user/password solo puede aprobarse como fallback explícito si los tokens no bastan.
- El FIT original debe conservarse como raw aunque se genere una representación parseada para normalización.

## Fuera de alcance de la v1

- escritura o modificación de datos en Strava
- webhooks productivos
- implementación Garmin, Komoot o ficheros manuales
- deduplicación compleja entre fuentes
- análisis deportivo avanzado
