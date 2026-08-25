# TODO

Este documento contiene solo trabajo accionable o validaciones operativas
pendientes. El histórico de lo ya entregado vive en `docs/releases/CHANGELOG.md`
y el estado real del proyecto en `docs/current-state.md`.

## Prioridad alta

- [ ] Validar en Nono la siguiente ejecución real de
  `nono-sports-garmin-sync.service` con la optimización streaming de agosto de
  2026. Revisar `journalctl`, duración, pico de memoria si está disponible y
  confirmar que no vuelve a morir por OOM.
- [ ] Añadir logging operativo por fase para Garmin/Strava/manual:
  fetch, normalización, consolidación, validación, duración, conteos y motivo
  de parada. Debe ayudar a distinguir OOM, bloqueo de Drive/rclone y errores de
  API.
- [ ] Auditar Strava antes del 2026-09-01 por los cambios oficiales del
  Developer Program: confirmar que `fetch-context` y `fetch-activities` no
  dependen de endpoints retirados de clubs ni de `segments/explore`, y ajustar
  documentación/código si procede.
- [ ] Revisar en el API Settings Dashboard de Strava el tier real de la app,
  capacidad de atleta y límites actuales. Documentar si Strava queda solo como
  fuente histórica o si conviene reactivar sincronización operativa.

## Prioridad media

- [ ] Optimizar `garmin sync` cuando no hay raw nuevo o modificado: evitar
  reconstruir splits, typed splits, normalizados y consolidados completos si el
  resultado no puede cambiar. La prioridad de memoria ya está resuelta; esta
  tarea busca reducir tiempo e I/O sobre Drive.
- [ ] Optimizar `strava sync --skip-fetch` sobre Drive: evitar lecturas masivas
  de segmentos y actividades cuando no hay raw nuevo. La escritura de streams ya
  es streaming, pero falta una estrategia incremental equivalente a Garmin.
- [ ] Estudiar particionado de streams/normalizados por actividad y escritura
  local atómica antes de sincronizar a Drive si el volumen sigue creciendo o el
  I/O de rclone se convierte en cuello de botella.
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
- [x] Retirado del backlog el preflight de memoria/swap tras resolver la causa
  estructural del OOM con procesamiento streaming; se mantiene la validación
  operativa real en Nono.
- [x] Eliminado `docs/planning/` por duplicar `roadmap`, `todo`,
  `current-state` y `CHANGELOG`.
