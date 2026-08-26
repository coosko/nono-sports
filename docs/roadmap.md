# Roadmap

Este roadmap describe la evolución del producto. No es una lista de tareas
ejecutables: el trabajo accionable vive en `docs/todo.md`, el estado real en
`docs/current-state.md` y el histórico en `docs/releases/CHANGELOG.md`.

## Fase 0. Base Strava y arquitectura común

Estado: completada.

Objetivo alcanzado:

- definir la arquitectura documental, funcional y técnica
- crear el proyecto Python y su estructura modular
- resolver configuración, rutas, `.env`, XDG y estructura de datos
- implementar Strava v1 como primera fuente oficial
- persistir `raw`, `normalizado`, `20_consolidado` y validación offline
- instalar el proyecto en Nono y dejar una guía operativa inicial

## Fase 1. Garmin Connect y multifuente

Estado: completada en su alcance v1.

Objetivo alcanzado:

- validar `garminconnect==0.3.6` con tokenstore reutilizable
- implementar adaptador Garmin Connect de solo lectura
- descargar actividades, detalles, FIT/GPX/TCX, splits, typed splits, weather y
  equipación por actividad cuando Garmin lo expone
- extraer y decodificar FIT desde un módulo independiente de la fuente
- normalizar actividades, streams, laps y datos auxiliares Garmin
- descargar y normalizar mediciones de peso/composición Garmin
- normalizar biometría manual desde CSV
- descargar y normalizar perfil, dispositivos y equipación Garmin
- consolidar actividades, mediciones, atleta y equipación entre Strava,
  Garmin Connect y manual
- calcular uso efectivo de equipación sin doble contar actividades presentes en
  varias fuentes

## Fase 2. Robustez operativa en Nono

Estado: fase actual.

Objetivo:

- asegurar que el flujo diario Garmin funciona de forma autónoma en el host
  Nono, con pocos recursos de RAM y Drive montado por rclone
- evitar OOM, bloqueos silenciosos y diagnósticos ambiguos
- mantener Strava como fuente histórica o secundaria mientras no haya acceso API
  operativo

Validación operativa ya realizada:

- el 2026-08-25, `nono-sports-garmin-sync.service` arrancó por timer a las
  19:50:04 UTC y terminó a las 19:51:19 UTC con `status=0/SUCCESS`; duración
  1min 15.028s, CPU 46.775s, pico de memoria 366.8M y pico de swap 2.4M
- los comandos de pipeline ya escriben resumen operativo local por ejecución en
  `~/.local/state/nono-sports/logs/operation_runs.jsonl`
- las fases de normalización y consolidación ya registran huellas ligeras de
  entradas y saltan trabajo completo cuando no hay raw ni normalizados
  modificados, reduciendo I/O sobre Drive en `garmin sync` y
  `strava sync --skip-fetch`

## Fase 3. Gobierno de fuentes conectadas

Estado: siguiente bloque de control.

Objetivo:

- decidir el papel operativo de cada fuente y evitar dependencias frágiles
- adaptar el proyecto a cambios externos antes de que rompan automatizaciones

Líneas de trabajo:

- mantener seguimiento documental de Strava; antes de reactivarla, revisar los
  cambios del Developer Program efectivos desde 2026-09-01, especialmente clubs
  y segmentos
- revisar tier real, capacidad y límites de la app Strava solo si vuelve a
  existir acceso operativo al API
- migrar la base URL de Strava antes del 2027-06-01
- mantener Garmin Connect encapsulado para poder sustituir el adaptador si la
  librería no oficial cambia
- revisar periódicamente compatibilidad Python, Linux/WSL/Windows y rclone

## Fase 4. Enriquecimiento del modelo deportivo

Estado: pendiente de diseño e implementación incremental.

Objetivo:

- hacer que el consolidado no sea solo una unión de fuentes, sino una base
  deportiva semánticamente útil para Nono

Líneas de trabajo:

- decidir fuente primaria por tipo de dato
- mejorar clasificación de deportes y subtipos: senderismo, gimnasio, fuerza,
  esgrima, indoor/outdoor y similares
- investigar laps separados y candidatos de segmentos Garmin
- decidir si Nono necesita segmentos propios o un modelo común de segmentos
- ampliar equipación manual y componentes: peso real, ruedas, cubiertas,
  desarrollos, sensores y cambios de material
- investigar datos Garmin adicionales de salud, recuperación, sueño,
  entrenamiento o carga

## Fase 5. Importadores y fuentes futuras

Estado: pendiente, con importación manual GPX básica ya entregada.

Objetivo:

- permitir que Nono integre datos deportivos que no vienen de Strava ni Garmin
  Connect sin romper el contrato común

Líneas de trabajo:

- ampliar actividades manuales desde GPX inicial a FIT, TCX u otros formatos
- deduplicar actividades importadas frente a Strava/Garmin
- evaluar Komoot/Wikiloc como fuentes normalizadas de rutas o planes, separadas
  de su uso actual como consulta auxiliar
- mantener el patrón común: raw original, normalización por fuente,
  consolidación trazable

## Fase 6. Explotación para Nono

Estado: futuro.

Objetivo:

- convertir la base consolidada en soporte directo para análisis, mantenimiento
  de material y decisiones de entrenamiento

Líneas de trabajo:

- informes y consultas deportivas de alto nivel
- seguimiento de carga, forma, recuperación y tendencias
- mantenimiento de bicicletas, zapatillas, sensores y componentes
- apoyo a planificación de rutas y entrenamientos
- preparación de vistas o salidas específicas para OpenClaw/Nono
