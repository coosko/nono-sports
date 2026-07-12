# nono-sports

Proyecto Python para construir la base de datos deportiva de Nono a partir de Strava, Garmin Connect y futuras fuentes como Komoot o importaciones manuales.

El proyecto tiene Strava v1 y Garmin Connect v1 operativos. El código activo permite autenticación OAuth Strava, tokenstore Garmin Connect, descarga raw, normalización por fuente, consolidación multi-fuente en `20_consolidado` y validación offline del dataset local.

## Estado actual

- paquete Python en `src/nono_sports/`
- comandos para diagnosticar entorno, preparar directorios, autenticar Strava, sincronizar Strava y Garmin Connect, normalizar raw por fuente, construir `20_consolidado` y validar datos
- documentación canónica de requisitos y arquitectura
- Garmin Connect integrado con descarga raw, FIT/GPX/TCX, normalización incremental, consolidación multi-fuente y limpieza de intermedios pesados
- código bootstrap anterior archivado en `deprecated/initial-bootstrap/`

Documento de referencia del estado real:

- `docs/current-state.md`

## Documentación principal

- `docs/requirements/requirements.md`: requisitos funcionales y no funcionales
- `docs/requirements/garmin-connect.md`: decisión aprobada para Garmin Connect
- `docs/technical/architecture.md`: arquitectura técnica objetivo
- `docs/current-state.md`: estado real del repositorio
- `docs/index.md`: índice y jerarquía documental
- `docs/usage/install-nono.md`: instalación en el host Nono
- `docs/usage/doctor.md`: diagnóstico local seguro del entorno
- `docs/usage/garmin-connect-probe.md`: prueba aislada Garmin Connect
- `docs/usage/garmin-fetch-activities.md`: sincronización, normalización y diagnóstico Garmin Connect
- `docs/usage/measurements.md`: mediciones biométricas Garmin/manual y consolidado
- `docs/usage/automation.md`: automatización controlada en Nono
- `docs/usage/nono-operator-guide.md`: guía operativa y prompt sugerido para Nono
- `docs/requirements/resources/Descripcion_inicial.md`: documento de entrada y descubrimiento
- `docs/requirements/resources/descripcion_integracion_garmin_connect.md`: análisis de Garmin Connect

## Requisitos

- Python 3.11, 3.12, 3.13 o 3.14
- `git`
- `python3 -m venv .venv`

## Configuración local

1. Si `python3 -m venv .venv` falla en Debian/Ubuntu, instala el paquete requerido:

```bash
sudo apt update
sudo apt install python3-venv
```

2. Crear el entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instalar el paquete en modo editable y dependencias de desarrollo:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m pip install -r requirements-dev.txt
```

4. Copiar el archivo de ejemplo si necesitas preparar variables de entorno para futuras integraciones:

```bash
cp .env.example .env
```

5. Ejecutar la verificación básica:

```bash
python3 -m pytest
```

También puedes ejecutar los tests directamente contra el entorno virtual del repositorio:

```bash
./.venv/bin/python -m pytest
```

Si aparece `No module named pytest`, faltan las dependencias de desarrollo o no estás usando el entorno virtual del proyecto.

Para ejecutar toda la validación local con un único comando:

```bash
python3 scripts/check.py
```

## Estructura de datos

El proyecto usará una carpeta raíz de datos configurada fuera del repositorio. En desarrollo puede usarse una ruta como:

`H:\Mi unidad\01_ambitos\02_personal\40_deporte`

La estructura objetivo es:

```text
H:\Mi unidad\01_ambitos\02_personal\40_deporte
├── 00_referencia/
├── 10_fuentes/
│   ├── strava/
│   │   ├── raw/
│   │   │   ├── athlete/
│   │   │   ├── activities/
│   │   │   ├── clubs/
│   │   │   ├── errors/
│   │   │   ├── gear/
│   │   │   ├── laps/
│   │   │   ├── routes/
│   │   │   ├── route_exports/
│   │   │   ├── route_streams/
│   │   │   ├── segments/
│   │   │   ├── segment_streams/
│   │   │   ├── streams/
│   │   │   ├── zones/
│   │   │   └── manifest.jsonl
│   │   ├── normalizado/
│   │   │   ├── athletes.jsonl
│   │   │   ├── activities.jsonl
│   │   │   ├── streams.jsonl
│   │   │   ├── streams_index.jsonl
│   │   │   └── state.json
│   │   └── logs/
│   │       └── activity_sync_state.json
│   ├── garmin_connect/
│   │   ├── raw/
│   │   │   ├── activities/
│   │   │   ├── activity_files/
│   │   │   ├── biometrics/
│   │   │   ├── fit_decoded/
│   │   │   ├── splits/
│   │   │   ├── typed_splits/
│   │   │   ├── weather/
│   │   │   └── manifest.jsonl
│   │   ├── normalizado/
│   │   │   ├── activities.jsonl
│   │   │   ├── streams.jsonl
│   │   │   ├── streams_index.jsonl
│   │   │   ├── laps.jsonl
│   │   │   ├── splits.jsonl
│   │   │   ├── typed_splits.jsonl
│   │   │   ├── segment_candidates.jsonl
│   │   │   ├── measurements.jsonl
│   │   │   ├── measurements_state.json
│   │   │   └── state.json
│   │   └── logs/
│   │       └── activity_sync_state.json
│   ├── komoot/
│   └── manual/
│       ├── biometria/
│       │   └── mediciones_carlos.csv
│       ├── normalizado/
│       │   ├── measurements.jsonl
│       │   └── measurements_state.json
│       └── logs/
├── 20_consolidado/
│   ├── activities.jsonl
│   ├── activity_sources.jsonl
│   ├── streams_index.jsonl
│   ├── measurements.jsonl
│   ├── measurement_sources.jsonl
│   ├── measurements_state.json
│   └── state.json
├── 30_analisis/
│   ├── informes/
│   │   └── strava_validation_report.md
│   ├── planes/
│   ├── seguimiento/
│   └── graficas/
└── 90_archivo/
```

### Crear la estructura base

Se incluyen `scripts/create_data_directories.py` y `scripts/create_data_directories.ps1`.

Estos scripts usan la variable de entorno `NONO_SPORT_DATA_ROOT` si no se indica una ruta explícita.

- En Windows PowerShell:

```powershell
$env:NONO_SPORT_DATA_ROOT = 'H:\Mi unidad\01_ambitos\02_personal\40_deporte'
cd \path\al\repositorio\nono-sport
powershell.exe -ExecutionPolicy Bypass -File scripts\create_data_directories.ps1
```

- En WSL o Linux si la unidad está montada en `/mnt/h`:

```bash
export NONO_SPORT_DATA_ROOT='H:\Mi unidad\01_ambitos\02_personal\40_deporte'
cd /home/carlos/dev/nono-sport
python3 scripts/create_data_directories.py
```

También puedes pasar la ruta directamente:

```bash
python3 scripts/create_data_directories.py --root '/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte'
```

Si la ruta no está montada, ejecuta el script desde Windows o usa una ruta local válida.

## Buenas prácticas

- No subir el archivo `.env` ni variables secretas al repositorio.
- En Nono, usar `~/.config/nono-sports/env` para configuración sensible y `~/.local/state/nono-sports/` para tokens.
- Mantener alineados `requirements.md`, `architecture.md` y `current-state.md`.
- Aplicar `pre-commit` antes de cada commit.
- Mantener el código activo separado del código archivado en `deprecated/`.
