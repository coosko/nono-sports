# Roadmap del proyecto nono-sports

## Objetivo general
Crear una plataforma backend para sincronizar datos deportivos desde Strava y otras fuentes, normalizar esa información y mantener un conjunto consolidado listo para análisis.

## Fases principales

1. **Infraestructura y base del proyecto**
   - Estructura Python y packaging
   - Configuración de CI/CD
   - Documentación inicial

2. **Sincronización con Strava**
   - Obtención de token de acceso
   - Descarga de actividades y streams
   - Almacenamiento raw y logs

3. **Normalización de datos**
   - Transformación de actividades a un esquema común
   - Normalización de métricas, tiempos y tipos

4. **Integración multiplataforma**
   - Consolidación de fuentes (Strava, Garmin, Komoot, manual)
   - Dedupe y merge de registros

5. **Salida y análisis**
   - Generación de CSV/JSONL consolidados
   - Preparación de data para análisis y visualización

## Próximos hitos

- [ ] Definir el contrato de datos normalizados.
- [ ] Añadir soporte para Garmin Connect.
- [ ] Implementar validación de integridad de datos.
- [ ] Crear procesos automáticos de ingestión y estado.
