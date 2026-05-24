# Backlog funcional

Este backlog deriva de `requirements.md` y `architecture.md`.

## Prioridad alta

- [ ] Definir el contrato mínimo de `normalized_activity`
- [ ] Definir el modelo de `consolidated_activity`
- [ ] Implementar la ingesta Strava v1
- [ ] Persistir datos `raw` de Strava
- [ ] Persistir datos `normalizado` de Strava
- [ ] Mantener trazabilidad entre dato normalizado y origen

## Prioridad media

- [ ] Diseñar la estructura de `20_consolidado`
- [ ] Definir reglas simples de consolidación para una única fuente
- [ ] Registrar estado de ingestión
- [ ] Registrar logs operativos por fuente

## Prioridad futura

- [ ] Importador Garmin
- [ ] Importador Komoot
- [ ] Importador manual de FIT, GPX, TCX y CSV
- [ ] Detección de duplicados multifuente
- [ ] Selección de fuente primaria por métrica
- [ ] Informes y análisis para Nono
