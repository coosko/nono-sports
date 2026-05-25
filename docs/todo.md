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

## Pendiente de definición

- [ ] definir el contrato mínimo de `normalized_activity`
- [ ] definir el modelo mínimo de `consolidated_activity`

## Pendiente de implementación

- [ ] persistir `normalizado`

## Pendiente de validación

- [ ] revisar compatibilidad entre Windows, WSL y Linux
- [x] definir tests mínimos por capa inicial
- [x] validar la estructura real de `NONO_SPORT_DATA_ROOT` para desarrollo local
- [x] validar ficheros raw de perfil y contexto generados por Strava
- [ ] validar ficheros raw de actividades generados por Strava
- [ ] validar ruta real de datos en Nono
