# Roadmap

Este roadmap deriva de `docs/requirements/requirements.md` y `docs/technical/architecture.md`.

## Fase 0. Definición

- cerrar arquitectura documental
- definir alcance exacto de la v1
- fijar contrato mínimo de datos normalizados

## Fase 1. Base técnica

- consolidar el scaffold del proyecto
- definir módulos y responsabilidades
- estabilizar configuración, calidad y estructura de datos

## Fase 2. Strava v1

- implementar ingesta desde Strava
- almacenar `raw`
- generar `normalizado`

## Fase 3. Consolidación inicial

- definir el modelo de actividad consolidada
- preparar `20_consolidado`
- resolver la consolidación simple para una única fuente
- validar conteos y coherencia del dataset local
- estado: implementado para Strava y Garmin Connect con enlaces multi-fuente

## Fase 4. Extensibilidad

- estado: Garmin Connect operativo como fuente conectada
- implementar `doctor` común y `garmin doctor`
- validar Garmin Connect con `garminconnect==0.3.6`
- preparar la entrada de Komoot y actividades manuales
- definir reglas de deduplicación multifuente

## Fase 5. Garmin Connect v1

- probar autenticación inicial y autonomía por tokenstore
- implementar adaptador Garmin Connect de solo lectura
- descargar raw de actividades, detalles, FIT, GPX/TCX, splits, typed splits, laps, weather y candidatos de segmentos
- decidir estrategia de parseo FIT conservando máxima información
- normalizar actividades Garmin Connect
- descargar y normalizar mediciones de peso/composición Garmin Connect
- normalizar biometría manual desde CSV
- investigar segmentos Garmin sin cerrar todavía modelo consolidado

## Fase 6. Consolidación multifuente

- detectar actividades equivalentes entre Strava y Garmin Connect: implementado
- permitir varias fuentes por actividad consolidada: implementado
- consolidar mediciones biométricas multi-fuente: implementado
- generar informe auditable de candidatos duplicados: implementado
- elegir fuente primaria por tipo de métrica
- preparar segmentos propios de Nono si Garmin/Strava no cubren el análisis necesario

## Fase 7. Explotación

- habilitar salidas útiles para Nono
- preparar análisis e informes posteriores
