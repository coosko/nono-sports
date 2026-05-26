# Backlog funcional

Este backlog deriva de `requirements.md` y `architecture.md`.

## Prioridad alta

- [x] Definir el contrato mínimo de `normalized_activity`
- [x] Definir el modelo de `consolidated_activity`
- [x] Implementar la ingesta Strava v1
- [x] Persistir datos `raw` de Strava
- [x] Persistir datos `normalizado` de Strava
- [x] Mantener trazabilidad entre dato normalizado y origen

## Prioridad media

- [x] Diseñar la estructura de `20_consolidado`
- [x] Definir reglas simples de consolidación para una única fuente
- [x] Registrar estado de ingestión
- [x] Generar informe de validación de datos
- [ ] Registrar logs operativos por fuente

## Prioridad futura

- [ ] Importador Garmin
- [ ] Importador Komoot
- [ ] Importador manual de FIT, GPX, TCX y CSV
- [ ] Detección de duplicados multifuente
- [ ] Selección de fuente primaria por métrica
- [ ] Informes y análisis para Nono
