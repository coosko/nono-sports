# Descripción inicial

Este documento recoge la visión inicial del proyecto y sirve como entrada para los documentos formales de requisitos, arquitectura y planificación.

No es un documento normativo. La fuente de verdad funcional es `docs/requirements/requirements.md` y la fuente de verdad técnica es `docs/technical/architecture.md`.

## Propósito

Construir una base backend para que Nono pueda recoger, conservar, normalizar y explotar datos deportivos del usuario sin depender de una única plataforma.

## Principios de partida

- empezar por una integración viable y segura
- priorizar fuentes oficiales o exportaciones controladas
- preservar los datos originales sin transformarlos
- normalizar cada fuente a un esquema común
- consolidar actividades equivalentes en una vista operativa única
- dejar preparada la arquitectura para ampliar fuentes en el futuro

## Decisión de inicio

La primera fuente será Strava mediante API oficial.

Motivos:

- es la vía más simple y documentada para una primera versión
- evita compartir credenciales de cuenta
- ofrece una automatización razonable para uso personal
- permite validar el flujo completo antes de abordar integraciones más complejas

## Fuentes previstas

- Strava API oficial
- exportaciones de Garmin Connect
- exportaciones o ficheros GPX de Komoot
- ficheros manuales como FIT, GPX, TCX o CSV

## Idea arquitectónica inicial

El proyecto se organiza en cuatro capas:

1. `raw`
   Conserva los datos tal como llegan desde cada fuente.

2. `normalizado`
   Convierte cada fuente a un modelo común sin perder trazabilidad.

3. `consolidado`
   Fusiona actividades equivalentes y define una vista operativa única.

4. `analisis`
   Genera informes, seguimiento y apoyo a la toma de decisiones para Nono.

## Alcance de la v1

- definir la arquitectura técnica
- definir el contrato mínimo de datos
- preparar la estructura de directorios
- implementar el flujo base para Strava
- almacenar `raw` y `normalizado`
- dejar la consolidación preparada aunque inicialmente sea simple

## Fuera de alcance de la v1

- automatizaciones avanzadas de Garmin
- acceso web autenticado por navegador
- consolidación compleja entre múltiples fuentes
- análisis avanzados, planes e informes sofisticados

## Uso de este documento

Este documento debe servir como semilla para:

- `docs/requirements/requirements.md`
- `docs/technical/architecture.md`
- `docs/roadmap.md`
- `docs/todo.md`
- guías operativas en `docs/usage/`
