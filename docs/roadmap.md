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

## Fase 4. Extensibilidad

- preparar la entrada de Garmin, Komoot y fuentes manuales
- definir reglas de deduplicación multifuente

## Fase 5. Explotación

- habilitar salidas útiles para Nono
- preparar análisis e informes posteriores
