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
- [x] Ejecutar prueba aislada de Garmin Connect con cuenta real
- [x] Validar autonomía Garmin Connect basada en tokenstore

## Prioridad media

- [x] Diseñar la estructura de `20_consolidado`
- [x] Definir reglas simples de consolidación para una única fuente
- [x] Implementar consolidación multi-fuente inicial
- [x] Generar informe de duplicados candidatos multi-fuente
- [x] Registrar estado de ingestión
- [x] Generar informe de validación de datos
- [ ] Registrar logs operativos por fuente
- [x] Implementar adaptador Garmin Connect de solo lectura
- [x] Descargar raw Garmin Connect con actividades, detalles, FIT, GPX/TCX, splits, typed splits, laps y weather
- [x] Parsear FIT conservando máxima información y trazabilidad
- [x] Separar decodificación FIT en módulo independiente de la fuente
- [x] Normalizar actividades Garmin Connect
- [ ] Investigar candidatos de segmentos Garmin
- [x] Alinear contrato mínimo de salidas normalizadas entre fuentes
- [x] Alinear ergonomía de comandos comunes entre Strava y Garmin Connect
- [x] Incorporar mediciones biométricas Garmin/manual y consolidado común
- [x] Incorporar perfil/equipación Garmin y Strava con consolidado común

## Prioridad futura

- [ ] Importador Komoot
- [ ] Importador manual de FIT, GPX, TCX y CSV
- [x] Detección de duplicados multifuente inicial
- [ ] Selección de fuente primaria por métrica
- [ ] Informes y análisis para Nono
- [ ] Segmentos propios de Nono
- [ ] Salud/recuperación Garmin
- [x] Descarga inicial de datos útiles de usuario Garmin más allá de actividades
- [ ] Clasificación avanzada por tipo de actividad e indicadores específicos
- [x] Equipación por actividad y catálogo de equipación por fuente
- [ ] Modelo manual de equipación y componentes para specs no presentes en APIs
- [ ] Consolidación de actividades importadas manualmente con deduplicación
  frente a actividades de fuentes conectadas
