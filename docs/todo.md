# TODO inmediato

## Completado

- [x] aprobar documento de análisis de Garmin Connect
- [x] separar decisión aprobada Garmin Connect en documentación canónica
- [x] implementar `doctor` común sin llamadas de descarga por defecto
- [x] implementar `nono-sports strava doctor`
- [x] implementar `nono-sports garmin doctor`
- [x] preparar prueba aislada Garmin Connect con `garminconnect==0.3.6`
- [x] cerrar la arquitectura de software de la v1
- [x] crear los módulos vacíos alineados con la arquitectura aprobada
- [x] implementar carga de `.env`, rutas y preparación de directorios
- [x] implementar autenticación OAuth Strava con almacenamiento XDG de tokens
- [x] implementar cliente Strava base con refresh, paginación, rate limits y errores normalizados
- [x] implementar descarga raw de perfil y contexto Strava
- [x] implementar descarga raw de actividades Strava con estado reanudable
- [x] ampliar raw gratuito con laps, segmentos, gear, clubs y rutas completas
- [x] proteger la descarga raw de actividades con presupuesto preventivo de rate limit
- [x] persistir `raw`
- [x] definir el contrato mínimo de `normalized_activity`
- [x] persistir `normalizado`
- [x] definir el modelo mínimo de `consolidated_activity`
- [x] persistir `20_consolidado`
- [x] definir el informe mínimo de validación de datos
- [x] implementar validación de datos offline
- [x] definir instalación recomendada en Nono
- [x] validar ruta real de datos en Nono
- [x] validar instalación del proyecto en Nono
- [x] confirmar que Nono ve `20_consolidado`
- [x] definir comando repetible de sincronización controlada
- [x] documentar propuesta de `systemd timer`
- [x] implementar reprogramación adaptativa para backfill histórico
- [x] añadir bloqueo de solapes para sincronización automatizada
- [x] activar timer diario de Strava en Nono
- [x] ajustar reprogramación adaptativa para ignorar streams/errores no descargables
- [x] validar instalación aislada local de `garminconnect==0.3.6`
- [x] ejecutar prueba aislada Garmin Connect con intervención del usuario
- [x] probar login inicial Garmin Connect y reutilización de tokenstore
- [x] descargar actividad Garmin de prueba con detalle, splits, typed splits, split summaries, weather y FIT
- [x] implementar adaptador Garmin Connect de solo lectura
- [x] refactorizar la prueba aislada para usar el adaptador Garmin Connect
- [x] implementar descarga raw Garmin Connect inicial
- [x] descargar raw real de 1 actividad Garmin Connect con manifiesto y estado
- [x] validar idempotencia de `garmin fetch-activities` en segunda ejecución
- [x] detectar que Garmin `ORIGINAL` entrega ZIP y extraer FIT interno
- [x] comparar alternativas FIT incluyendo `fitdecode`
- [x] implementar módulo independiente `nono_sports.formats.fit`
- [x] decodificar FIT real con `fitdecode`
- [x] conservar metadatos FIT de bajo nivel para evitar pérdida de datos
- [x] añadir comparación reutilizable `fitdecode` vs `garmin-fit-sdk`
- [x] implementar consolidación multi-fuente inicial
- [x] generar informe `duplicate_candidates.jsonl`
- [x] adaptar validación a actividades consolidadas con varias fuentes
- [x] normalizar Garmin Connect manteniendo trazabilidad a raw
- [x] comprobar que Garmin `23422332225` y Strava `19114956119` consolidan como
  la misma actividad
- [x] automatizar `garmin sync` con fetch, decode FIT, normalize y consolidación
- [x] hacer incremental la normalización Garmin para no releer FIT decodificados
  sin cambios
- [x] hacer incremental el backfill Garmin: paginar listados y saltar
  actividades ya completas hasta encontrar pendientes

## Pendiente de validación

- [ ] validar autonomía Garmin Connect en Nono cuando se despliegue allí
- [x] decidir estrategia de parseo FIT tras comparar alternativas con actividades reales
- [ ] revisar manualmente actividad Garmin descargada frente a Garmin Connect
- [ ] ampliar raw Garmin Connect con GPX/TCX si están disponibles
- [ ] investigar si hay laps separados fuera de `splits/lapDTOs`
- [ ] investigar candidatos de segmentos Garmin antes de aprobar un modelo consolidado de segmentos
- [x] revisar candidatos duplicados Strava/Garmin cuando exista normalizado Garmin suficiente
- [ ] decidir fuente primaria por tipo de métrica en consolidación multi-fuente
- [ ] confirmar en la ejecución diaria del 2026-06-26 que no se programa una ejecución adaptativa si solo quedan `raw.streams_incomplete` y `raw.recoverable_errors`
- [ ] mejorar escalabilidad avanzada: particionar streams/normalizados por
  actividad y estudiar escritura local atómica antes de sincronizar a Drive si
  el volumen crece mucho más.
- [ ] revisar tier/suscripción de la app Strava antes del 2026-06-30 por cambios del Developer Program
- [ ] migrar `API_BASE_URL` de Strava a `https://www.api-v3.strava.com` antes del 2027-06-01
- [ ] revisar si las deprecaciones de clubs/segments del 2026-09-01 afectan a endpoints usados por `fetch-context` y `fetch-activities`
- [ ] revisar compatibilidad entre Windows, WSL y Linux
- [x] definir tests mínimos por capa inicial
- [x] validar la estructura real de `NONO_SPORT_DATA_ROOT` para desarrollo local
- [x] validar ficheros raw de perfil y contexto generados por Strava
- [x] validar ficheros raw de actividades generados por Strava
- [x] revisar el informe `30_analisis/informes/strava_validation_report.md`
- [x] ejecutar `strava sync` con descarga cuando se libere cuota diaria
- [x] decidir si activar `systemd timer` en Nono

## Backlog funcional próximo

- [ ] Alinear ergonomía CLI entre fuentes: mantener nombres comunes para
  `sync`, `--skip-fetch`, `--force`, `--max-activities`, `--lock-file` y
  separar solo las opciones específicas de cada API.
- [ ] Ampliar Garmin Connect para bajar todos los datos útiles del usuario, no
  solo actividades deportivas.
- [ ] Incorporar datos de peso reportados por Garmin Connect y definir un
  registro histórico de peso que pueda consolidar varias fuentes, incluyendo
  entradas manuales.
- [ ] Asegurar que las actividades normalizadas identifican y clasifican bien el
  tipo de actividad, deporte e indicadores específicos, por ejemplo senderismo
  o peso levantado en gimnasio.
- [ ] Recoger la equipación usada por actividad y guardar el detalle de cada
  elemento de equipación, incluyendo bicicletas, para mejorar análisis como la
  estimación de potencia.
- [ ] Verificar y completar, si hace falta, la recogida de equipación en Strava.
- [ ] Permitir que el consolidado integre actividades subidas a mano desde FIT,
  GPX, TCX u otros formatos, deduplicándolas frente a Strava/Garmin si
  representan la misma actividad.
