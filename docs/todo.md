# TODO inmediato

## Completado

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

## Pendiente de validación

- [ ] confirmar en la ejecución diaria del 2026-06-26 que no se programa una ejecución adaptativa si solo quedan `raw.streams_incomplete` y `raw.recoverable_errors`
- [ ] corregir escalabilidad de normalización/consolidación: el 2026-06-02, con 104 actividades raw, `strava normalize` no terminó en 180s sobre `/home/nono/drive` montado con `rclone FUSE`; el cuello está en lectura/normalización de actividades+streams raw antes de escribir normalizado. Priorizar normalización incremental, streams particionados/por actividad y escritura local atómica antes de sincronizar a Drive.
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
