# Documentación técnica

## Arquitectura general

El proyecto se articula en tres capas principales:

1. **Sincronización**
   - `src/nono_sports/strava_sync.py`
   - Obtiene tokens y descarga datos raw desde Strava.

2. **Normalización**
   - `src/nono_sports/normalizer.py`
   - Transforma los datos raw a un esquema común.

3. **Integración**
   - `src/nono_sports/integrator.py`
   - Combina datos de diversas fuentes y elimina duplicados.

## Almacenamiento de datos

- `10_fuentes/strava/raw/`: datos originales descargados de Strava.
- `10_fuentes/strava/normalizado/`: datos normalizados y listos para consumo.
- `20_consolidado/`: datos consolidados que unifican todas las fuentes.

## Flujo de datos

1. Cargar variables de entorno desde `.env`.
2. Refrescar token con Strava.
3. Descargar actividades y streams.
4. Normalizar cada actividad.
5. Integrar los registros en un dataset unificado.
6. Guardar resultados en JSONL/CSV y mantener estado.

## Configuración

- `src/nono_sports/config.py` carga variables desde `.env`.
- `NONO_SPORT_DATA_ROOT` define la ruta base de datos.

## Buenas prácticas de desarrollo

- Usar `pre-commit` para formateo y lint.
- Mantener la carpeta `docs/` actualizada.
- Evitar hardcode de rutas; usar variables de entorno.
