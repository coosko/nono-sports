# TODO

Este documento contiene solo trabajo accionable o validaciones operativas
pendientes. El histórico de lo ya entregado vive en `docs/releases/CHANGELOG.md`
y el estado real del proyecto en `docs/current-state.md`.

## Prioridad alta

No hay tareas de prioridad alta abiertas.

## Prioridad media

- [ ] Decidir fuente primaria por tipo de dato en la consolidación multi-fuente:
  por ejemplo Garmin/FIT para sensores y clasificación deportiva, Strava para
  segmentos/rutas sociales si siguen disponibles, manual para especificaciones
  declaradas por Carlos.
- [ ] Mejorar clasificación de actividades e indicadores específicos:
  senderismo, gimnasio, esgrima, fuerza, peso levantado, indoor/outdoor y otros
  campos que Nono necesite para análisis.
- [ ] Investigar candidatos de segmentos Garmin y decidir si se crea un modelo
  de segmentos propios de Nono o una normalización común de segmentos.
- [ ] Investigar si Garmin expone laps separados fuera de `splits/lapDTOs` y
  normalizarlos si aportan información adicional.
- [ ] Ampliar el modelo manual de equipación y componentes: peso real en orden
  de marcha, ruedas, cubiertas, desarrollos, sensores, cambios de componentes y
  relación componente-equipo.
- [ ] Ampliar el importador manual de actividades, ya operativo para GPX, a
  FIT, TCX u otros formatos cuando aporten datos que no estén en Garmin/Strava.
- [ ] Investigar datos Garmin adicionales de salud, recuperación, sueño,
  entrenamiento o carga si aportan valor deportivo y pueden sincronizarse de
  forma autónoma.

## Prioridad baja o seguimiento

- [ ] Mantener seguimiento documental de Strava mientras no haya acceso API
  operativo. Si se decide reactivar Strava, revisar antes el Developer Program,
  el API Settings Dashboard, endpoints de clubs/segmentos, límites vigentes y
  ejecutar una prueba controlada antes de activar sincronización periódica.
- [ ] Migrar `API_BASE_URL` de Strava a `https://api-v3.strava.com` antes del
  2027-06-01, manteniendo compatibilidad y tests.
- [ ] Actualizar la toolchain de calidad: subir `ruff-pre-commit` desde
  `v0.0.266` y migrar configuración a `tool.ruff.lint` cuando el hook lo
  soporte, eliminando el aviso actual de `scripts/check.py`.
- [ ] Revisar compatibilidad periódica entre Windows, WSL, Linux y Python
  `>=3.11,<3.15`, especialmente en rutas con espacios, Drive/rclone y timers.
- [ ] Evaluar ingesta futura de Komoot/Wikiloc como fuente normalizada de rutas
  o planes, separándola del uso actual como fuente auxiliar de consulta.

## Completado reciente

- [x] Validada autonomía Garmin Connect basada en tokenstore: las ejecuciones
  reales en Nono llegaron a ejecutar el flujo diario sin relogueo; los fallos
  recientes fueron de memoria, no de autenticación.
- [x] Implementada descarga y normalización de mediciones Garmin/manual con
  consolidado común en `20_consolidado/measurements.jsonl`.
- [x] Implementada descarga, normalización y consolidación de atleta/equipación
  entre Strava y Garmin Connect.
- [x] Implementado cálculo de uso efectivo de equipación sin doble conteo entre
  actividades Strava/Garmin.
- [x] Implementado fallback Garmin GPX/TCX para actividades importadas sin FIT.
- [x] Implementado importador manual GPX con raw, normalizado, streams y
  deduplicación multi-fuente.
- [x] Implementada normalización/consolidación de bajo consumo de memoria:
  `streams.jsonl` ya no se carga completo en normalización Garmin/Strava,
  consolidación de equipación ni validación offline.
- [x] Validada en Nono la ejecución real de
  `nono-sports-garmin-sync.service` con la optimización streaming: el
  2026-08-25 arrancó por timer a las 19:50:04 UTC y terminó correctamente a las
  19:51:19 UTC, con 1min 15.028s de duración, pico de memoria de 366.8M y pico
  de swap de 2.4M.
- [x] Añadido resumen operativo local por ejecución en
  `~/.local/state/nono-sports/logs/operation_runs.jsonl`, con fases, duración,
  conteos, salidas y errores para comandos de pipeline, manteniendo en Drive
  solo estados/checkpoints reproducibles del dataset.
- [x] Optimizado `garmin sync` cuando no hay raw nuevo o modificado: las
  normalizaciones de Garmin/manual y los consolidados saltan fases completas si
  `inputs.input_fingerprint` no cambia y las salidas esperadas existen.
- [x] Optimizado `strava sync --skip-fetch` sobre Drive: la normalización
  Strava y la consolidación reutilizan salidas previas cuando el raw local no
  cambia, evitando lecturas masivas innecesarias de actividades, streams,
  segmentos y equipación.
- [x] Validada en Nono la optimización incremental real: primera ejecución
  `garmin sync --skip-fetch` sembrando huellas en 1:32.31, 325180 KB RSS y 0
  swaps; segunda ejecución sin cambios con fases derivadas `skipped=true`, 0
  ficheros escritos, 4.00 s, 60264 KB RSS y 0 swaps.
- [x] Retirado del backlog el preflight de memoria/swap tras resolver la causa
  estructural del OOM con procesamiento streaming.
- [x] Eliminado `docs/planning/` por duplicar `roadmap`, `todo`,
  `current-state` y `CHANGELOG`.
