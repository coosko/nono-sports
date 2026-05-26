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

## Pendiente de validación

- [ ] revisar compatibilidad entre Windows, WSL y Linux
- [x] definir tests mínimos por capa inicial
- [x] validar la estructura real de `NONO_SPORT_DATA_ROOT` para desarrollo local
- [x] validar ficheros raw de perfil y contexto generados por Strava
- [ ] validar ficheros raw de actividades generados por Strava
- [ ] revisar el informe `30_analisis/informes/strava_validation_report.md`
- [ ] validar ruta real de datos en Nono
- [ ] validar instalación del proyecto en Nono
- [ ] confirmar que Nono ve `20_consolidado`
