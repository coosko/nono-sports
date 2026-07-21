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

- RF8: El sistema debe poder importar datos desde Garmin Connect siguiendo la decisión aprobada en `docs/requirements/garmin-connect.md`.
- RF9: El sistema debe poder importar datos desde Komoot.
- RF10: El sistema debe poder importar ficheros manuales como FIT, GPX, TCX o CSV.
- RF11: El sistema debe detectar actividades equivalentes entre varias fuentes.
- RF12: El sistema debe elegir una fuente primaria por tipo de dato cuando existan duplicados.
- RF13: El sistema debe producir una vista consolidada única por actividad real.
- RF14: El sistema debe ofrecer comandos `doctor` por fuente para diagnosticar configuración, permisos, estado local y riesgos antes de sincronizar.
- RF15: La integración Garmin Connect debe descargar actividades, detalles, FIT, GPX/TCX disponibles, splits, typed splits, laps, weather y candidatos de segmentos cuando existan.
- RF16: La integración Garmin Connect debe investigar la estructura real de segmentos antes de aprobar un modelo consolidado de segmentos.
- RF17: El sistema debe decodificar FIT mediante un módulo independiente de la fuente para reutilizarlo con Garmin, importaciones manuales u otras fuentes futuras.
- RF18: La decodificación de formatos deportivos debe seguir un patrón replicable para FIT, GPX, TCX u otros formatos: raw original, derivado parseado trazable, normalización y consolidación.
- RF19: La consolidación debe permitir que una actividad consolidada tenga varias actividades fuente enlazadas.
- RF20: La consolidación debe generar un informe auditable de candidatos duplicados antes de endurecer reglas de fusión o selección por métrica.
- RF21: El sistema debe importar mediciones biométricas y métricas puntuales
  desde fuentes automáticas o manuales.
- RF22: El sistema debe normalizar y consolidar mediciones como peso,
  frecuencia cardiaca en reposo, composición corporal u otras métricas futuras
  mediante un contrato común.
- RF23: El sistema debe importar datos útiles del usuario/atleta desde las
  fuentes disponibles, normalizarlos por fuente y consolidarlos en una vista
  común auditable.
- RF24: El sistema debe importar equipación usada o declarada por las fuentes,
  incluyendo bicicletas, zapatillas, dispositivos y sensores cuando existan,
  con detalle por fuente y relación con actividades cuando la API lo exponga.

## Requisitos de datos

- RDAT1: Los datos `raw` deben conservarse sin transformación funcional.
- RDAT2: Los datos `normalizado` deben seguir un esquema común entre fuentes.
  El contrato mínimo por fuente es `activities.jsonl`, `streams.jsonl`,
  `streams_index.jsonl`, `state.json` y `logs/activity_sync_state.json`; cada
  fuente puede añadir extensiones específicas si aportan información real.
- RDAT3: La capa consolidada debe conservar la relación entre actividad consolidada y actividades fuente.
- RDAT4: El sistema debe priorizar trazabilidad sobre compactación prematura.
- RDAT5: Los ficheros FIT originales deben conservarse siempre como raw antes de cualquier parseo.
- RDAT6: El parseo de FIT debe priorizar conservación de información y trazabilidad frente a simplicidad.
- RDAT7: Si una fuente entrega un contenedor, como ZIP con FIT interno, se debe conservar el contenedor original y extraer el fichero parseable como derivado raw trazable.
- RDAT8: Una actividad consolidada debe conservar todos los enlaces fuente que participaron en su agrupación.
- RDAT9: Las mediciones normalizadas deben escribirse en
  `normalizado/measurements.jsonl` por fuente, con `metric`, `value`, `unit`,
  fecha/hora, trazabilidad raw y atributos extensibles.
- RDAT10: Las mediciones consolidadas deben escribirse en
  `20_consolidado/measurements.jsonl` y conservar enlaces fuente en
  `20_consolidado/measurement_sources.jsonl`.
- RDAT11: Los perfiles de atleta normalizados deben escribirse por fuente en
  `normalizado/athletes.jsonl`; la vista multi-fuente se escribe en
  `20_consolidado/athletes.jsonl` y sus enlaces en
  `20_consolidado/athlete_sources.jsonl`.
- RDAT12: La equipación normalizada debe escribirse por fuente en
  `normalizado/equipment.jsonl`; la vista multi-fuente se escribe en
  `20_consolidado/equipment.jsonl` y sus enlaces en
  `20_consolidado/equipment_sources.jsonl`.
- RDAT13: La equipación debe usar un contrato extensible con `equipment_type`,
  `name`, `brand`, `model`, `distance_m`, `weight_kg`, `attributes` y
  `source_reference`, para permitir fusionar datos complementarios de Strava,
  Garmin Connect, fuentes manuales u otras fuentes futuras.
- RDAT14: La equipación consolidada debe calcular métricas efectivas de uso,
  como `distance_m` y horas, a partir de actividades consolidadas y enlaces de
  fuente, evitando doble conteo cuando una actividad existe en varias
  plataformas. La trazabilidad de la estrategia y de las distancias fuente debe
  conservarse en `attributes.usage`.

## Requisitos no funcionales

- RNF1: El proyecto debe ser portable entre Windows, WSL y Linux.
- RNF2: El proyecto debe usar Python `>=3.11,<3.15` y empaquetado PEP 621. La instalación en Nono se ha validado con Python 3.14.4.
- RNF3: El código debe poder evolucionar por capas, sin quedar acoplado a una única fuente.
- RNF4: El proyecto debe incluir validación automática mínima mediante lint y tests.
- RNF5: La documentación debe diferenciar con claridad estado actual, arquitectura objetivo y backlog.
- RNF6: El sistema debe evitar el uso de credenciales de alto riesgo cuando exista una alternativa oficial o de exportación controlada.
- RNF7: Las integraciones no oficiales deben estar encapsuladas como adaptadores sustituibles y no condicionar el núcleo.
- RNF8: Tokens, secretos, locks y estado sensible deben vivir fuera del repositorio y fuera de `NONO_SPORT_DATA_ROOT`, siguiendo XDG siempre que sea posible.
- RNF9: La automatización no debe reloguear en cada ejecución; debe reutilizar tokens y fallar con diagnóstico claro si requiere intervención humana.

## Fuera de alcance de la v1

- sincronización completa de múltiples fuentes
- consolidación heurística avanzada entre actividades
- análisis, recomendación o planificación deportiva avanzada
- automatización basada en navegador autenticado
- escritura o modificación de datos en Garmin Connect
- segmentos propios de Nono

## Requisitos de documentación

- RDOC1: `README.md` debe describir el proyecto y su estado real.
- RDOC2: `docs/technical/architecture.md` debe ser la fuente de verdad técnica.
- RDOC3: `docs/current-state.md` debe reflejar el estado actual del repositorio.
- RDOC4: `docs/planning/` y `docs/todo.md` deben derivarse de este documento y de la arquitectura técnica.
