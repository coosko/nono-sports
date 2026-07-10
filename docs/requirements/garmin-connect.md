# Decisión aprobada: Garmin Connect

Este documento recoge la decisión aprobada para integrar Garmin Connect en
`nono-sports`. Deriva del análisis conservado en
`docs/requirements/resources/descripcion_integracion_garmin_connect.md`.

## Decisión

`nono-sports` incorporará Garmin Connect como fuente de datos deportiva en una
fase posterior a Strava v1.

La integración se hará con `cyberjunky/python-garminconnect` como adaptador
pragmático de solo lectura, encapsulado y sustituible. No se tratará como API
oficial ni como dependencia conceptual del núcleo.

Dependencia inicial prevista:

```text
garminconnect==0.3.6
```

Cuando haya pruebas suficientes, se podrá valorar:

```text
garminconnect>=0.3.6,<0.4
```

## Alcance Garmin Connect v1

La primera versión Garmin se centrará en actividades deportivas.

Debe descargar y preservar, cuando estén disponibles:

- perfil/atleta Garmin mínimo necesario
- listado de actividades
- detalle JSON de cada actividad
- fichero FIT original
- ficheros GPX y TCX si están disponibles
- splits
- typed splits
- laps
- weather
- bloques que puedan representar segmentos o esfuerzos de segmento

La fase inicial debe investigar la estructura real de Garmin antes de cerrar el
modelo final de segmentos. No se aprueba todavía un consolidado específico de
segmentos hasta validar datos reales.

## Uso de datos por Nono

Nono debe poder usar:

- `segments`: comparativas históricas en tramos equivalentes.
- `splits`: evolución global dentro de la actividad.
- `laps`: fases de entrenamiento, series, calentamientos y recuperaciones.
- `typed splits`: agrupaciones semánticas de Garmin que ayuden a interpretar la actividad.

Si Garmin no ofrece segmentos nativos útiles, se evaluará crear segmentos
propios de Nono en una fase posterior.

## FIT

El FIT original debe guardarse siempre como raw.

Para normalizar y consolidar será necesario parsearlo. La estrategia aprobada es
usar un módulo independiente de Garmin en `nono_sports.formats`, de modo que el
mismo procedimiento sirva para FIT descargados de Garmin, FIT importados a mano
o FIT procedentes de futuras fuentes.

Backend inicial:

```text
fitdecode==0.11.0
```

Motivo:

- release reciente frente a `fitparse`
- sin dependencias pesadas
- conserva cabecera/CRC y permite representación más cercana al stream FIT
- soporta FIT encadenados
- expone mensajes y campos desconocidos
- buen equilibrio entre información recuperada y coste

`garmin-fit-sdk` queda como alternativa oficial/fallback si necesitamos
contrastar interpretación de campos. `fit-tool` y `fitparse` no quedan como
primera opción.

El derivado FIT debe evitar pérdida de información:

- conservar campos directos por nombre para facilitar normalización
- conservar metadatos por campo con `def_num`, `raw_value`, `value`, unidades y
  tipos
- permitir comparar el resultado con `garmin-fit-sdk` sobre cualquier FIT,
  aunque no proceda de Garmin Connect

Criterio de decisión:

- conservar el máximo de información
- no descartar campos desconocidos
- mantener trazabilidad al FIT original
- validar con actividades reales antes de fijar dependencia

Resultado validado con una actividad real Garmin:

- Garmin entregó un ZIP como descarga `ORIGINAL`, no un FIT directo.
- Se conserva `activity_files/<id>.original.zip`.
- Se extrae y conserva `activity_files/<id>.fit`.
- El flujo normal decodifica el FIT de forma transitoria y no conserva
  `fit_decoded/<id>.fitdecode.json`.
- El derivado trazable `fit_decoded/<id>.fitdecode.json` solo se genera bajo
  demanda para diagnóstico de una actividad concreta.
- `fitdecode` recuperó 6844 frames, 20 tipos de mensajes, 2480 records y 4254
  mensajes HRV sin errores.
- La comparación con `garmin-fit-sdk` no mostró tipos de mensaje ni series
  adicionales. Las diferencias detectadas fueron alias o metadatos de campo
  que deben conservarse mediante `raw_value` y `def_num`.

## Estructura de datos

Garmin debe seguir el patrón ya implementado para Strava.

La sincronización diaria debe evitar recorrer todo el histórico. Como
`garminconnect==0.3.6` no expone un filtro fiable de actividades modificadas
desde una fecha, el sistema debe:

- aceptar `--after` y `--before`, igual que Strava
- guardar `last_successful_activity_sync_at` en `logs/activity_sync_state.json`
- calcular una ventana incremental con solape configurable
- cortar la paginación cuando el listado llega a actividades anteriores a esa
  ventana
- permitir `--full-scan` para backfills, auditorías o reparaciones

```text
10_fuentes/
└── garmin_connect/
    ├── raw/
    │   ├── manifest.jsonl
    │   ├── athlete/
    │   │   └── profile.json
    │   ├── activities/
    │   │   └── <garmin_activity_id>.json
    │   ├── activity_files/
    │   │   ├── <garmin_activity_id>.fit
    │   │   ├── <garmin_activity_id>.tcx
    │   │   └── <garmin_activity_id>.gpx
    │   ├── splits/
    │   ├── typed_splits/
    │   ├── laps/
    │   ├── weather/
    │   └── segment_candidates/
    ├── normalizado/
    │   ├── athletes.jsonl
    │   ├── activities.jsonl
    │   ├── streams.jsonl
    │   ├── streams_index.jsonl
    │   ├── laps.jsonl
    │   ├── splits.jsonl
    │   ├── typed_splits.jsonl
    │   ├── segment_candidates.jsonl
    │   └── state.json
    └── logs/
        └── activity_sync_state.json
```

## Configuración y secretos

La configuración y el estado sensible deben seguir el estándar XDG ya usado en
Strava.

```text
~/.config/nono-sports/env
~/.config/nono-sports/garmin_connect/config.toml
~/.local/state/nono-sports/garmin_connect/tokenstore/
~/.local/state/nono-sports/garmin_connect/auth_state.json
~/.local/state/nono-sports/nono-sports-garmin-sync.lock
```

Reglas:

- no guardar tokens ni credenciales en el repositorio
- no guardar tokens ni credenciales en Google Drive
- no poner usuario/contraseña en argumentos de línea de comandos
- no mostrar secretos en logs
- probar primero autonomía basada en tokenstore
- usar usuario/contraseña solo si se aprueba como fallback explícito

## Autenticación y autonomía

El objetivo operativo es:

1. autenticación manual inicial
2. persistencia de tokens en `~/.local/state/nono-sports/garmin_connect/tokenstore/`
3. sincronizaciones autónomas usando tokens
4. error claro y acción humana si Garmin exige reautenticación

El timer no debe reloguear en cada ejecución. Si los tokens no bastan para
autonomía diaria o semanal, se abrirá una decisión específica sobre fallback con
credenciales.

## Comandos previstos

```bash
nono-sports garmin auth
nono-sports garmin doctor
nono-sports garmin sync --window-days 60
nono-sports garmin sync --activity-id <garmin_activity_id>
nono-sports sync --source garmin_connect
nono-sports sync --all
```

## Doctor

Debe existir una funcionalidad `doctor` para diagnóstico seguro antes de
sincronizar.

El `doctor` debe comprobar, como mínimo:

- versión de Python compatible
- paquete instalado y versión de `garminconnect`
- carga de configuración XDG
- existencia y permisos de rutas sensibles
- existencia de `NONO_SPORT_DATA_ROOT`
- estructura `10_fuentes/garmin_connect`
- presencia de tokenstore
- estado de ficheros de logs y locks
- que no hay secretos en rutas de datos
- lectura básica de estado local sin descargar datos

Por defecto, `doctor` no debe descargar actividades ni hacer operaciones de
escritura remota.

## Fuera de alcance inicial

- escribir o modificar datos en Garmin Connect
- programar entrenamientos en Garmin
- depender de Garmin como única fuente
- backfill completo repetido
- segmentos propios de Nono
- salud/recuperación avanzada
- servicio web o webhooks Garmin
