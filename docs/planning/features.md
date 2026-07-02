# Backlog funcional

Este backlog deriva de `requirements.md` y `architecture.md`.

## Prioridad alta

- [x] Definir el contrato mínimo de `normalized_activity`
- [x] Definir el modelo de `consolidated_activity`
- [x] Implementar la ingesta Strava v1
- [x] Persistir datos `raw` de Strava
- [x] Persistir datos `normalizado` de Strava
- [x] Mantener trazabilidad entre dato normalizado y origen
- [x] Implementar `doctor` común para diagnóstico de entorno, rutas, permisos y secretos
- [x] Implementar `nono-sports strava doctor`
- [x] Implementar `nono-sports garmin doctor`
- [x] Preparar prueba aislada de Garmin Connect con `garminconnect==0.3.6`
- [ ] Ejecutar prueba aislada de Garmin Connect con cuenta real
- [ ] Validar autonomía Garmin Connect basada en tokenstore

## Prioridad media

- [x] Diseñar la estructura de `20_consolidado`
- [x] Definir reglas simples de consolidación para una única fuente
- [x] Implementar consolidación multi-fuente inicial
- [x] Generar informe de duplicados candidatos multi-fuente
- [x] Registrar estado de ingestión
- [x] Generar informe de validación de datos
- [ ] Registrar logs operativos por fuente
- [x] Implementar adaptador Garmin Connect de solo lectura
- [ ] Descargar raw Garmin Connect con actividades, detalles, FIT, GPX/TCX, splits, typed splits, laps y weather
- [x] Parsear FIT conservando máxima información y trazabilidad
- [x] Separar decodificación FIT en módulo independiente de la fuente
- [x] Normalizar actividades Garmin Connect
- [ ] Investigar candidatos de segmentos Garmin
- [ ] Alinear ergonomía de comandos comunes entre Strava, Garmin y futuras fuentes

## Prioridad futura

- [ ] Importador Komoot
- [ ] Importador manual de FIT, GPX, TCX y CSV
- [x] Detección de duplicados multifuente inicial
- [ ] Selección de fuente primaria por métrica
- [ ] Informes y análisis para Nono
- [ ] Segmentos propios de Nono
- [ ] Salud/recuperación Garmin
- [ ] Descarga de datos completos de usuario Garmin más allá de actividades
- [ ] Histórico de peso multifuente con datos Garmin y registros manuales
- [ ] Clasificación avanzada por tipo de actividad e indicadores específicos
- [ ] Equipación por actividad y catálogo de equipación por fuente
- [ ] Consolidación de actividades importadas manualmente con deduplicación
  frente a actividades de fuentes conectadas
