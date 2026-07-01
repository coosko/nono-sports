# Integración Garmin Connect en nono-sports

Este documento queda como **análisis aprobado y material de entrada**. La
decisión formal derivada vive en `docs/requirements/garmin-connect.md`.

El objetivo es que nono-sports pueda descargarse los datos de Garmin Connect, además de desde otras fuentes como puede ser Strava.

**Parece razonable usar `cyberjunky/python-garminconnect`** descargable desde `https://github.com/cyberjunky/python-garminconnect`, pero no como una dependencia “de confianza absoluta”, sino como **adaptador pragmático para uso personal e interno de Nono**.

La decisión es:

```text
usar cyberjunky/python-garminconnect para leer actividades de Garmin Connect,
pero encapsulado dentro de nono-sports,
solo en modo lectura,
con versión fijada o acotada,
con sincronización prudente,
y con una arquitectura que permita sustituirlo en el futuro.
```

No usar `cyberjunky/python-garminconnect` como si fuera una API oficial estable de Garmin.

---

## 1. Qué es realmente `python-garminconnect`

El proyecto `cyberjunky/python-garminconnect` es una librería Python para acceder a datos de Garmin Connect. Su README indica que ofrece acceso a datos de salud, actividad, dispositivo, objetivos, tendencias históricas, entrenamientos y más; también declara una cobertura amplia, con más de 130 métodos organizados en varias categorías, incluyendo “Activities & Workouts”. ([GitHub][1])

También tiene bastante tracción: en GitHub aparecen miles de estrellas, cientos de forks y cientos de commits, lo que indica que no es un script abandonado. ([GitHub][2])

Pero hay un punto crítico: **no es la API oficial pública de Garmin Connect Developer Program**. En una issue reciente del propio repositorio, un usuario plantea explícitamente que la librería usa endpoints internos de Garmin Connect y pregunta por riesgos de uso en producción, rate limits o posibles restricciones de cuenta. ([GitHub][3])

Además, la versión 0.3.0 introdujo autenticación “native DI OAuth”, dependencias como `curl_cffi` y `ua-generator`, y menciona estrategias para sortear bloqueos de Cloudflare y randomización de fingerprints de navegador. Eso funciona como señal práctica de que la librería está lidiando con mecanismos no pensados para una API pública estable. ([GitHub][4])

Por tanto, la valoración es:

```text
Buena herramienta para uso personal/controlado.
No ideal como dependencia crítica o producto público.
```

---

## 2. Comparación con la API oficial de Garmin

Garmin sí tiene un **Garmin Connect Developer Program** con Activity API oficial. Esa Activity API da acceso a datos detallados de actividades capturadas por dispositivos Garmin y permite obtener ficheros FIT, GPX y TCX; además soporta modelos tipo push/pull tras aprobación. ([Garmin Developers][5])

El problema práctico es que está pensada para integraciones aprobadas, plataformas o soluciones de negocio, no para que un usuario doméstico conecte su propia cuenta de forma sencilla. La propia documentación habla de aprobación, entorno de evaluación y herramientas de onboarding antes de producción. ([Garmin Developers][5])

Para Nono, que es una herramienta personal tuya, la vía oficial sería ideal en teoría, pero probablemente excesiva o difícil de conseguir ahora.

La decisión es:

```text
Fase actual: python-garminconnect.
Futuro: dejar abierta la posibilidad de sustituirlo por Garmin Activity API oficial si algún día merece la pena.
```

---

## 3. Riesgos principales

### 3.1 Riesgo de estabilidad

Al usar endpoints no oficiales, Garmin puede cambiar autenticación, endpoints, payloads o límites. Ya hay issues sobre errores `429 Too Many Requests` durante login OAuth/preauthorized. ([GitHub][6])

Mitigación:

```text
- sincronizaciones poco frecuentes;
- no hacer scraping intensivo;
- cachear tokens;
- reintentos prudentes;
- backoff;
- no reloguear en cada ejecución;
- capturar errores y no romper todo nono-sports.
```

### 3.2 Riesgo de seguridad

La librería permite autenticarse con usuario/contraseña y guardar tokens. El ejemplo oficial del repo muestra variables `EMAIL`, `PASSWORD` y `GARMINTOKENS`, y explica que los tokens se guardan por defecto en `~/.garminconnect/garmin_tokens.json`. ([GitHub][2])

Mitigación:

```text
- no guardar contraseña en config;
- login interactivo inicial;
- guardar solo tokens;
- permisos 700/600;
- tokens fuera de Google Drive;
- no exponer logs con credenciales;
- no ejecutar como root.
```

### 3.3 Riesgo legal/ToS

No puedo afirmar con seguridad qué consecuencias tendría para una cuenta personal, pero el propio debate comunitario reconoce que no es una API oficial y que puede entrar en conflicto con términos de uso. ([GitHub][3])

Mitigación:

```text
- uso personal;
- bajo volumen;
- solo lectura;
- sin redistribuir datos;
- sin uso comercial;
- arquitectura sustituible.
```

---

## 4. Decisión: sí, pero como adaptador

No meter la librería en el núcleo común de `nono-sports`.

La arquitectura debería ser:

```text
nono-sports core
├── modelo común de actividad
├── normalización
├── consolidación
├── informes
└── fuentes
    ├── strava
    └── garmin_connect
        └── adapter usando python-garminconnect
```

Es decir:

```text
python-garminconnect
→ adaptador Garmin
→ raw Garmin
→ normalizado Garmin
→ consolidado común
→ análisis de Nono
```

Nunca:

```text
Nono → llama directamente python-garminconnect
```

Ni:

```text
core de nono-sports depende conceptualmente de Garmin
```

Garmin debe ser una fuente más.

---

## 5. Arquitectura recomendada

### 5.1 Capas

```text
Garmin Connect
   ↓
python-garminconnect
   ↓
nono_sports.garmin_connect
   ↓
raw Garmin
   ↓
normalizado Garmin
   ↓
consolidado común
   ↓
rutinas / informes / Nono
```

### 5.2 Directorios

Ya existe estructura común en `nono-sports`, se añade Garmin siguiendo el patrón existente.

Algo así:

```text
10_fuentes/
└── garmin_connect/
    ├── raw/
    │   ├── manifest.jsonl
    │   ├── athlete/
    │   │   └── profile.json
    │   ├── activities_index.jsonl
    │   ├── activities/
    │   │   └── <garmin_activity_id>.json
    │   ├── activity_files/
    │   │   ├── <garmin_activity_id>.fit
    │   │   ├── <garmin_activity_id>.tcx
    │   │   └── <garmin_activity_id>.gpx
    │   ├── splits/
    │   │   └── <garmin_activity_id>.json
    │   ├── typed_splits/
    │   │   └── <garmin_activity_id>.json
    │   ├── laps/
    │   │   └── <garmin_activity_id>.json
    │   ├── weather/
    │   │   └── <garmin_activity_id>.json
    │   └── segment_candidates/
    │       └── <garmin_activity_id>.json
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
    ├── logs/
    │   └── activity_sync_state.json
    └── README.md
```

Esta es una propuesta de análisis, pero la decisión arquitectónica debería ser clara: **Garmin debe parecerse a Strava todo lo posible**.

El patrón esperado es:

```text
raw/manifest.jsonl              # manifiesto de descargas raw
raw/activities/<id>.json         # detalle JSON original por actividad
raw/activity_files/<id>.<fmt>    # ficheros originales FIT/TCX/GPX
normalizado/*.jsonl             # salida normalizada de la fuente
normalizado/state.json           # resumen de normalización
logs/activity_sync_state.json    # estado incremental de sincronización
```

Por coherencia con Strava, evitaría introducir nombres alternativos como `state.json` en la raíz de la fuente, `activity_sync_state.jsonl` o `raw_activities.jsonl` salvo que haya una razón técnica fuerte. Si una fuente necesita más detalle, se añaden carpetas bajo `raw/`, pero no se cambia el contrato general.

Lo importante no es el número exacto de ficheros, sino mantener esta separación:

```text
raw = lo que viene de Garmin
normalizado = formato propio por fuente, con sintaxis común
consolidado = formato común multi-fuente
```

---

## 6. Qué descargar de Garmin

Empezaría solo con **actividades**.

No empezaría con sueño, HRV, Body Battery, pasos, estrés, peso, etc., aunque la librería pueda obtenerlo. El README de la librería muestra mucha cobertura de salud, métricas avanzadas y datos diarios, pero eso puede abrir demasiado el alcance. ([GitHub][1])

### Fase 1: actividades + ficheros originales + detalles + investigación de estructura

Descargar:

```text
- lista de actividades;
- detalle de cada actividad nueva;
- fichero FIT si está disponible;
- GPX/TCX si están disponibles;
- splits;
- typed splits;
- laps si aparecen en el detalle o en el FIT;
- weather si está disponible;
- cualquier bloque nativo que parezca representar segmentos o esfuerzos de segmento;
- resumen: fecha, tipo, distancia, duración, desnivel, FC, calorías, dispositivo.
```

Preferencia:

```text
FIT = fuente rica/canónica.
JSON detalle = metadatos rápidos.
GPX = útil para ruta.
TCX = útil como respaldo intermedio con trackpoints y algunas métricas.
```

La API oficial de Garmin también trata FIT/GPX/TCX como formatos relevantes para detalles completos de actividad, lo que confirma que es una separación razonable. ([Garmin Developers][5])

La fase 1 no debe prometer todavía segmentos nativos Garmin como salida estable. Debe **investigar y preservar todo lo que Garmin devuelva** para poder decidir después con evidencia.

### Fase 2: segmentos, splits, laps y typed splits

**Los segmentos deben entrar en Garmin desde la primera fase**, al menos como capacidad de lectura/diagnóstico. Para pruebas de esfuerzo son más útiles que muchas métricas globales, porque permiten comparar siempre el mismo tramo.

#### Por qué sí incluir segmentos

Garmin define los segmentos como tramos virtuales de carrera o ciclismo contra los que puedes competir, comparar tu resultado con actividades pasadas, con otros usuarios o con tus contactos. También permite enviar segmentos de Garmin Connect al dispositivo y competir contra ellos. ([Garmin][11])

Para tu caso, esto encaja muy bien con:

```text
- pruebas de rendimiento en subidas concretas;
- comparar tiempos en el mismo tramo;
- ver evolución sin potenciómetro;
- analizar FC media, FC máxima, velocidad, cadencia y desnivel;
- detectar si mejoras por forma, peso, viento o intensidad;
- controlar segmentos como La Marañosa.
```

#### Lo que he visto en `python-garminconnect`

En el código actual de `python-garminconnect` veo métodos de actividad como `get_activity`, `get_activity_details`, `get_activity_splits`, `get_activity_typed_splits`, `get_activity_split_summaries`, `get_activity_weather`, zonas de FC/potencia y descarga de actividad en FIT/TCX/GPX/KML/CSV. ([GitHub][12])

Pero no veo un método explícito tipo `get_segments`, `get_activity_segments` o similar; una búsqueda en el código del repositorio no encontró coincidencias para `segment`. ([GitHub][13])

Eso no significa que no podamos obtenerlos. Significa que hay que tratarlos como una capacidad a investigar en el adaptador Garmin, no como algo garantizado por la librería.

#### Diferencia práctica entre segments, splits, laps y typed splits

Para Nono conviene separar estos conceptos porque sirven a preguntas distintas:

```text
segments:
  Tramos geográficos concretos y comparables entre actividades.
  Sirven para analizar rendimiento en el mismo sitio: una subida, una recta,
  una vuelta de control o un tramo de referencia creado por Garmin, Strava
  o por Nono en el futuro.

splits:
  Divisiones regulares o resumidas de una actividad, normalmente por distancia
  o por bloques de tiempo. Sirven para ver ritmo medio, deriva de frecuencia
  cardíaca, fatiga progresiva o consistencia.

laps:
  Vueltas registradas por el dispositivo o por autolap. Pueden ser manuales,
  automáticas o asociadas a fases del entrenamiento. Son esenciales para
  analizar series, calentamiento, recuperación, bloques de trabajo y gimnasio
  si el dispositivo los representa así.

typed splits:
  Splits clasificados por Garmin con una semántica concreta. Pueden separar
  tipos de tramo o agregaciones diferentes de los splits simples. Hay que
  descargarlos y estudiarlos antes de decidir cómo normalizarlos.
```

Uso esperado por Nono:

```text
- segments: comparativas históricas en tramos equivalentes.
- splits: evolución global dentro de la actividad.
- laps: fases de entrenamiento y lectura de sesiones estructuradas.
- typed splits: señal complementaria para entender cómo Garmin agrupa la actividad.
```

En principio debe descargarse toda la información disponible sobre estos cuatro bloques, siempre en modo lectura y conservando el raw aunque todavía no se normalice todo.

#### Dónde lo pondría

Sin complicar demasiado:

```text
10_fuentes/garmin_connect/
├── raw/
│   ├── manifest.jsonl
│   ├── activities/
│   ├── activity_files/
│   ├── splits/
│   ├── typed_splits/
│   ├── laps/
│   └── segment_candidates/
├── normalizado/
│   ├── activities.jsonl
│   ├── splits.jsonl
│   ├── typed_splits.jsonl
│   ├── laps.jsonl
│   └── segment_candidates.jsonl
└── logs/
    └── activity_sync_state.json

20_consolidado/
├── activities.jsonl
├── activity_sources.jsonl
└── streams_index.jsonl
```

Los ficheros consolidados `segments.jsonl` y `segment_efforts.jsonl` pueden ser necesarios más adelante, pero no los daría por aprobados hasta decidir cómo tratar segmentos nativos de Garmin, segmentos de Strava y segmentos propios de Nono.

#### Estrategia recomendada

##### 1. Descargar actividad completa y FIT

La API oficial de Garmin Activity API habla de acceso a detalles completos de actividad y ficheros FIT, GPX y TCX. ([Garmin Developers][14]) Aunque en nuestro caso usemos `python-garminconnect`, el principio es el mismo: **para análisis serio, el FIT o los detalles de actividad son la fuente fuerte**.

Por tanto, para Garmin:

```text
- actividad resumen;
- activity details;
- FIT original;
- GPX/TCX si están disponibles;
- splits/laps;
- typed splits;
- weather si está disponible;
- datos de segmentos si aparecen;
- si no aparecen, derivarlos localmente.
```

##### 2. Intentar leer segmentos nativos Garmin

En la fase de prueba, pediría a Codex que inspeccione qué devuelven:

```text
get_activity(activity_id)
get_activity_details(activity_id)
get_activity_splits(activity_id)
get_activity_typed_splits(activity_id)
get_activity_split_summaries(activity_id)
FIT original
GPX/TCX original si existe
```

Y buscar claves como:

```text
segment
segments
segmentEfforts
activitySegments
leaderboard
lap
laps
splits
typedSplits
splitSummaries
course
```

Si aparecen segmentos, se guardan en `raw/segment_candidates/` y se normalizan solo cuando entendamos su semántica. Mientras tanto, deben conservarse como candidatos para análisis posterior.

##### 3. Si Garmin no da segmentos claros, calcularlos nosotros

Esta es la parte importante para pruebas de esfuerzo.

Pero queda por definir una vez tengamos integrado el resto.

#### Segmentos Garmin vs Strava

Garmin permite usar segmentos Garmin y también Strava segments en dispositivos compatibles; la documentación de Garmin indica que la información se aplica tanto a Garmin Connect segments como a Strava segments. ([Garmin][11])

Prioridad para análisis deberá ser definida según la necesidad

Y añadiría:

```text
Fase 1b: segmentos para pruebas de esfuerzo

- crear catálogo local de segmentos de test;
- calcular esfuerzos por actividad;
- generar histórico de esfuerzos;
- comparar tiempo, FC, velocidad, cadencia, desnivel y potencia si existe;
- permitir informe específico de segmento.
```

#### Veredicto

Sí, incluiría segmentos, pero con esta jerarquía:

```text
1. Descargar de Garmin lo que exista sobre segmentos.
2. Guardarlo como raw, sin asumir que será estable.
3. Normalizar si aparece información útil.
4. Investigar si hay esfuerzos de segmentos nativos.
5. Si no hay segmentos útiles, definir segmentos propios de Nono más adelante.
```

#### Parseo de FIT

Descargar FIT es imprescindible, pero **no es suficiente** para normalizar y consolidar. El fichero FIT conserva mucha información que puede no aparecer completa en JSON, GPX o TCX: muestras temporales, eventos, vueltas, sensores, potencia, cadencia, temperatura, altitud, estados del dispositivo y metadatos.

Para aprovecharlo hay que parsearlo. Las estrategias candidatas son:

```text
fitparse:
  Ventajas:
  - muy usada históricamente;
  - sencilla para leer mensajes FIT;
  - suficiente para prototipos.
  Inconvenientes:
  - mantenimiento irregular;
  - puede quedarse corta con campos nuevos;
  - puede requerir trabajo adicional para conservar mensajes poco comunes.

garmin-fit-sdk:
  Ventajas:
  - SDK oficial de Garmin para FIT;
  - mejor alineación con el formato;
  - opción más sólida si queremos conservar máxima información.
  Inconvenientes:
  - integración potencialmente más pesada;
  - hay que revisar licencia, empaquetado y ergonomía en Python;
  - puede ser menos cómoda para desarrollo rápido.

python-fit-tool:
  Ventajas:
  - orientada a leer/escribir FIT;
  - puede ser más moderna en ciertos usos;
  - útil si necesitamos inspección detallada.
  Inconvenientes:
  - hay que validar cobertura real;
  - comunidad y estabilidad pueden ser menores que alternativas más conocidas.

fitdecode:
  Ventajas:
  - release reciente 0.11.0 publicada en 2025;
  - sin dependencias pesadas;
  - orientada a leer frame a frame;
  - conserva cabecera y CRC en el flujo de lectura;
  - permite una representación muy cercana al stream original;
  - soporta FIT encadenados;
  - expone campos y mensajes desconocidos.
  Inconvenientes:
  - no es SDK oficial;
  - API diferente a fitparse;
  - estado beta en PyPI aunque el proyecto tiene evolución reciente.

Conversión externa a CSV/JSON:
  Ventajas:
  - facilita depuración manual;
  - puede servir como herramienta auxiliar de diagnóstico.
  Inconvenientes:
  - añade dependencia operacional externa;
  - puede perder estructura;
  - no debería ser el camino principal si queremos máxima fidelidad.
```

Criterio propuesto para decidir:

```text
1. Priorizar la estrategia que conserve más mensajes y campos FIT.
2. Guardar siempre el FIT original en raw aunque se parseen derivados.
3. Parsear hacia una representación intermedia raw/derivada antes de normalizar.
4. No descartar campos desconocidos; guardarlos como extras o payload raw referenciado.
5. Conservar metadatos por campo: número FIT, valor crudo, valor decodificado,
   unidades y tipos.
6. Poder comparar decodificadores sobre cualquier FIT, no solo sobre FITs de
   Garmin Connect.
7. Comparar al menos dos actividades reales antes de cerrar dependencia.
```

Conclusión tras prueba real:

```text
Usar fitdecode como backend inicial.
Mantener garmin-fit-sdk como contraste oficial/fallback.
No usar fitparse como primera opción por antigüedad.
No usar fit-tool como primera opción por coste y ruido de warnings en la prueba.
```

Comparación práctica sobre FIT real:

```text
fitdecode y garmin-fit-sdk vieron los mismos tipos de mensaje y los mismos
volúmenes principales. Las diferencias observadas fueron alias o metadatos de
campo, por ejemplo product/device_type/total_cycles frente a raw_value,
antplus_device_type/local_device_type/total_strokes.
```

La implementación debe vivir fuera de Garmin, por ejemplo en `nono_sports.formats`,
para que el mismo mecanismo sirva a Garmin, Komoot, importaciones manuales u
otras fuentes futuras.


### Fase 3: métricas corporales/salud

Solo después:

```text
- frecuencia cardíaca en reposo;
- peso;
- sueño;
- HRV;
- Body Battery;
- estrés.
```

Esto puede ser muy útil para tus rutinas semanales, pero lo metería cuando la parte de actividades sea estable.

---

## 7. Sincronización incremental

Garmin Connect vía esta librería no debe asumirse como una API con `deltaLink` formal como Microsoft Graph. Haría incremental por **estado local**:

```text
10_fuentes/garmin_connect/logs/activity_sync_state.json
├── last_successful_sync
├── last_activity_start_time
├── known_activity_ids
├── latest_downloaded_files
├── pending_activity_ids
├── recoverable_errors
└── sync_window_days
```

Estrategia:

```text
1. Primera carga: backfill controlado, por ejemplo últimos 2 años o todo si lo decides.
2. Sync normal: consultar últimos 30/60/90 días.
3. Si aparece activity_id nuevo: descargar detalle y FIT.
4. Si una actividad existente cambió: actualizar detalle.
5. Si una actividad desaparece: marcar como missing, no borrar inmediatamente.
```

Esto evita descargar todo en cada ejecución.

Comandos sugeridos:

```bash
nono-sports garmin auth
nono-sports garmin doctor
nono-sports garmin sync --since 2024-01-01
nono-sports garmin sync --window-days 60
nono-sports garmin sync --activity-id 123456789
```

Y para la sincronización general:

```bash
nono-sports sync --source garmin_connect
nono-sports sync --all
```

---

## 8. Relación con Strava

Garmin y Strava no deben competir. Deben complementarse.

Yo definiría prioridades por tipo de dato:

```text
Resumen de actividad:
- Garmin si la actividad nace en Garmin.
- Strava si no existe en Garmin.

Datos detallados:
- FIT de Garmin como fuente preferente.
- Strava streams si no hay FIT.

Social:
- Strava.

Segmento:
- Según necesidad.

Rutas planificadas:
- Komoot o fuente específica.

Salud/recuperación:
- Garmin.
```

Para deduplicar Garmin/Strava:

```text
match por:
- fecha/hora de inicio;
- duración;
- distancia;
- tipo de actividad;
- dispositivo;
- coordenadas inicio/fin;
- external_id si existe;
- tolerancia temporal.
```

En el consolidado común, cada actividad debería poder tener varias fuentes:

```json
{
  "activity_id": "consolidated-...",
  "sources": [
    {
      "source": "garmin_connect",
      "source_activity_id": "123456789",
      "confidence": 1.0
    },
    {
      "source": "strava",
      "source_activity_id": "987654321",
      "confidence": 0.95
    }
  ]
}
```

---

## 9. Instalación y dependencias

No instalaría la librería globalmente. La metería en el venv de `nono-sports`.

En `pyproject.toml` o requirements:

```text
garminconnect==0.3.6
curl_cffi
ua-generator
```

O, mejor, acotar una versión mínima ya validada tras probarla. La release 0.3.0 cambió autenticación y formato de tokens, y versiones posteriores han ido corrigiendo detalles del tokenstore, por lo que conviene no dejarlo sin fijar ni excesivamente abierto. ([GitHub][4])

Yo usaría algo así:

```text
garminconnect>=0.3.6,<0.4
```

o incluso:

```text
garminconnect==0.3.6
```

hasta que tengamos pruebas suficientes. Para la primera implantación me parece más prudente `garminconnect==0.3.6`; cuando haya tests y experiencia de operación, se puede relajar a `>=0.3.6,<0.4`.

---

## 10. Seguridad de credenciales

Ubicación recomendada:

```text
~/.config/nono-sports/
└── env

~/.config/nono-sports/garmin_connect/
└── config.toml              # si hace falta configuración específica no secreta

~/.local/state/nono-sports/garmin_connect/
├── tokenstore/
└── auth_state.json           # si hace falta registrar metadata no sensible de autenticación

~/.local/state/nono-sports/
└── nono-sports-garmin-sync.lock
```

Permisos:

```bash
chmod 700 ~/.config/nono-sports
chmod 700 ~/.config/nono-sports/garmin_connect
chmod 700 ~/.local/state/nono-sports
chmod 700 ~/.local/state/nono-sports/garmin_connect
chmod 700 ~/.local/state/nono-sports/garmin_connect/tokenstore
chmod 600 ~/.config/nono-sports/env
```

Reglas:

```text
- no guardar contraseña Garmin;
- probar primero login interactivo inicial y persistencia por tokens;
- guardar tokens fuera del repositorio y fuera de Drive;
- no guardar tokens en Drive;
- no subir tokens a Git;
- no mostrar tokens en logs;
- no poner EMAIL/PASSWORD en systemd.
```

El ejemplo del repositorio permite usar variables `EMAIL` y `PASSWORD`, pero para Nono no las usaría como diseño inicial de servicios automáticos. ([GitHub][2])

El objetivo operativo debe ser:

```text
1. Autenticación manual inicial.
2. Persistencia de tokens en ~/.local/state/nono-sports/garmin_connect/tokenstore/.
3. Ejecuciones diarias autónomas usando tokens.
4. Si el token caduca o Garmin exige reautenticación, registrar error claro y pedir intervención.
5. Solo si la prueba demuestra que los tokens no sirven para autonomía real, valorar user/password como fallback controlado.
```

Si hubiera que usar usuario/contraseña como fallback, debería tratarse como una excepción explícita:

```text
- credenciales fuera del repositorio;
- permisos 600;
- nunca en argumentos de línea de comandos;
- nunca en logs;
- nunca en Google Drive;
- preferiblemente en un almacén de secretos o fichero XDG protegido;
- documentar claramente el riesgo antes de aprobarlo.
```

---

## 11. Timer

No haría un timer agresivo.

Garmin se puede sincronizar:

```text
1 vez al día
```

o, como mucho:

```text
cada 6-12 horas
```

Para actividades deportivas, no necesitas consultar cada 10 minutos.

Servicio:

```text
nono-sports-garmin-sync.service
nono-sports-garmin-sync.timer
```

O mejor, si ya tienes timer general:

```text
nono-sports-sync.timer
```

con fuentes configuradas:

```toml
[sources]
enabled = ["strava", "garmin_connect"]
```

El timer no debería hacer login completo en cada ejecución. Debería ejecutar una sincronización normal que reutilice tokens ya persistidos. Si Garmin exige reautenticación, el servicio debe fallar de forma controlada, dejar log claro y no entrar en bucles de login.

Esto no significa renunciar a la autonomía diaria. Significa que la autonomía deseada se intentará primero así:

```text
timer diario
→ nono-sports garmin sync
→ carga tokenstore
→ refresca/renueva sesión si la librería lo permite sin intervención
→ descarga novedades
→ actualiza raw/normalizado/consolidado
```

Solo si las pruebas demuestran que Garmin no permite mantener sesiones/tokens de forma suficiente, se abrirá una decisión explícita sobre autenticación automática con credenciales.

---

## 12. Qué no hacer

No hacer todavía:

```text
- subir actividades a Garmin;
- modificar entrenamientos;
- programar workouts en Garmin;
- usar la librería desde Nono directamente;
- depender de Garmin como única fuente;
- reloguear cada vez;
- guardar contraseña;
- ejecutar muchas llamadas en paralelo;
- hacer backfill completo repetidamente.
```

---

## 13. Plan de implantación

### Fase 0: prueba aislada

En una rama:

```text
feature/garmin-connect-source
```

Probar:

```text
- instalación;
- login inicial;
- tokenstore;
- listar últimas actividades;
- descargar una actividad;
- descargar FIT de una actividad.
- ejecutar una segunda vez sin introducir credenciales.
```

Criterio de éxito:

```text
sin reloguear,
sin 429,
sin guardar contraseña,
sin errores con MFA.
```

### Fase 1: adaptador Garmin mínimo

Crear:

```text
nono_sports/garmin_connect/client.py
nono_sports/garmin_connect/sync.py
nono_sports/normalization/garmin_connect_activity.py
```

Funciones:

```text
list_activities(start, limit)
get_activity(activity_id)
download_activity_file(activity_id, format="fit")
sync_recent(window_days)
```

La fase 1 también debe inspeccionar qué devuelven `get_activity_splits`, `get_activity_typed_splits`, `get_activity_split_summaries`, `get_activity_weather` y el FIT original, pero sin prometer todavía un modelo final de segmentos.

### Fase 2: raw + normalizado

Generar:

```text
10_fuentes/garmin_connect/raw/manifest.jsonl
10_fuentes/garmin_connect/raw/activities/<id>.json
10_fuentes/garmin_connect/raw/activity_files/<id>.fit
10_fuentes/garmin_connect/raw/splits/<id>.json
10_fuentes/garmin_connect/raw/typed_splits/<id>.json
10_fuentes/garmin_connect/raw/laps/<id>.json
10_fuentes/garmin_connect/raw/weather/<id>.json
10_fuentes/garmin_connect/raw/segment_candidates/<id>.json
10_fuentes/garmin_connect/normalizado/activities.jsonl
10_fuentes/garmin_connect/normalizado/streams.jsonl
10_fuentes/garmin_connect/normalizado/streams_index.jsonl
10_fuentes/garmin_connect/normalizado/laps.jsonl
10_fuentes/garmin_connect/normalizado/splits.jsonl
10_fuentes/garmin_connect/normalizado/typed_splits.jsonl
10_fuentes/garmin_connect/normalizado/segment_candidates.jsonl
10_fuentes/garmin_connect/normalizado/state.json
10_fuentes/garmin_connect/logs/activity_sync_state.json
```

### Fase 3: consolidación Garmin + Strava

Actualizar el consolidador para fusionar actividades coincidentes.

Regla:

```text
Garmin no sustituye a Strava; ambos son fuentes.
```

### Fase 4: rutinas deportivas

Actualizar `revision_deportiva_semanal.md` para que pueda usar:

```text
Garmin = actividades y recuperación
Strava = actividades y contexto social/segmentos
```

### Fase 5: salud/recuperación

Añadir solo si aporta:

```text
frecuencia cardíaca en reposo
peso
sueño
HRV
```

---

## 14. Veredicto

Sí, usaría `python-garminconnect`, con estas condiciones:

```text
- solo para uso personal de Nono;
- solo lectura;
- versión fijada;
- encapsulado como fuente Garmin dentro de nono-sports;
- tokens fuera de Drive;
- sincronización diaria o poco frecuente;
- sin login repetido;
- sin endpoints de escritura;
- con logs y fallback;
- manteniendo Strava y Garmin como fuentes separadas.
```

La arquitectura adecuada sería:

```text
Garmin Connect
→ python-garminconnect
→ source adapter garmin_connect
→ raw Garmin
→ normalizado Garmin
→ consolidado común nono-sports
→ rutinas deportivas / Nono
```

Es una buena idea **si no dejas que esa librería condicione todo el diseño**. Debe ser una pieza reemplazable.

## Referencias

[1]: https://github.com/cyberjunky/python-garminconnect "GitHub - cyberjunky/python-garminconnect: Python 3 API wrapper for Garmin Connect to get statistics and set activities · GitHub"
[2]: https://github.com/cyberjunky/python-garminconnect/blob/master/example.py "python-garminconnect/example.py at master · cyberjunky/python-garminconnect · GitHub"
[3]: https://github.com/cyberjunky/python-garminconnect/issues/362 "Community experience using the library in production · Issue #362 · cyberjunky/python-garminconnect · GitHub"
[4]: https://github.com/cyberjunky/python-garminconnect/releases "Releases · cyberjunky/python-garminconnect · GitHub"
[5]: https://developer.garmin.com/gc-developer-program/activity-api/ "Activity API | Garmin Connect Developer Program | Garmin Developers"
[6]: https://github.com/cyberjunky/python-garminconnect/issues/337 "429 Too Many Requests - during login (OAuth Preauthorized) · Issue #337 · cyberjunky/python-garminconnect · GitHub"
[11]: https://www8.garmin.com/manuals/webhelp/GUID-0221611A-992D-495E-8DED-1DD448F7A066/EN-US/GUID-A31B940D-7C93-4202-94D9-8D3A2C018514.html "Forerunner 965 Watch Owner's Manual - Segments"
[12]: https://raw.githubusercontent.com/cyberjunky/python-garminconnect/master/garminconnect/__init__.py "raw.githubusercontent.com"
[13]: https://github.com/cyberjunky/python-garminconnect/blob/master/garminconnect/__init__.py "python-garminconnect/garminconnect/__init__.py at master · cyberjunky/python-garminconnect · GitHub"
[14]: https://developer.garmin.com/gc-developer-program/activity-api/ "Activity API | Garmin Connect Developer Program | Garmin Developers"
