# Requisitos del proyecto

Este documento es la fuente de verdad funcional y no funcional del proyecto.

## Objetivo

Permitir que Nono disponga de una base de datos deportiva propia, trazable y ampliable a múltiples fuentes.

## Requisitos funcionales de la v1

- RF1: El sistema debe poder obtener actividades de Strava mediante API oficial.
- RF2: El sistema debe almacenar los datos originales de Strava en una capa `raw`.
- RF3: El sistema debe transformar los datos de Strava a un esquema común en una capa `normalizado`.
- RF4: El sistema debe mantener trazabilidad entre cada registro normalizado y su origen.
- RF5: El sistema debe crear y usar una estructura de directorios de datos fuera del repositorio.
- RF6: El sistema debe permitir configurar la raíz de datos mediante `NONO_SPORT_DATA_ROOT`.
- RF7: El sistema debe dejar preparada una capa `20_consolidado` para consumo posterior por Nono.

## Requisitos funcionales previstos para versiones posteriores

- RF8: El sistema debe poder importar datos desde Garmin Connect.
- RF9: El sistema debe poder importar datos desde Komoot.
- RF10: El sistema debe poder importar ficheros manuales como FIT, GPX, TCX o CSV.
- RF11: El sistema debe detectar actividades equivalentes entre varias fuentes.
- RF12: El sistema debe elegir una fuente primaria por tipo de dato cuando existan duplicados.
- RF13: El sistema debe producir una vista consolidada única por actividad real.

## Requisitos de datos

- RDAT1: Los datos `raw` deben conservarse sin transformación funcional.
- RDAT2: Los datos `normalizado` deben seguir un esquema común entre fuentes.
- RDAT3: La capa consolidada debe conservar la relación entre actividad consolidada y actividades fuente.
- RDAT4: El sistema debe priorizar trazabilidad sobre compactación prematura.

## Requisitos no funcionales

- RNF1: El proyecto debe ser portable entre Windows, WSL y Linux.
- RNF2: El proyecto debe usar Python 3.11 o 3.12 mientras no se revise oficialmente la compatibilidad con versiones posteriores, y empaquetado PEP 621.
- RNF3: El código debe poder evolucionar por capas, sin quedar acoplado a una única fuente.
- RNF4: El proyecto debe incluir validación automática mínima mediante lint y tests.
- RNF5: La documentación debe diferenciar con claridad estado actual, arquitectura objetivo y backlog.
- RNF6: El sistema debe evitar el uso de credenciales de alto riesgo cuando exista una alternativa oficial o de exportación controlada.

## Fuera de alcance de la v1

- sincronización completa de múltiples fuentes
- consolidación heurística avanzada entre actividades
- análisis, recomendación o planificación deportiva avanzada
- automatización basada en navegador autenticado

## Requisitos de documentación

- RDOC1: `README.md` debe describir el proyecto y su estado real.
- RDOC2: `docs/technical/architecture.md` debe ser la fuente de verdad técnica.
- RDOC3: `docs/current-state.md` debe reflejar el estado actual del repositorio.
- RDOC4: `docs/planning/` y `docs/todo.md` deben derivarse de este documento y de la arquitectura técnica.
