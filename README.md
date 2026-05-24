# nono-sports

Proyecto Python para construir la base de datos deportiva de Nono a partir de Strava y futuras fuentes como Garmin, Komoot o importaciones manuales.

El proyecto está en fase de definición de arquitectura y diseño documental. El código activo contiene solo un scaffold mínimo.

## Estado actual

- paquete Python mínimo en `src/nono_sports/`
- scripts para crear la estructura base de datos
- documentación canónica de requisitos y arquitectura
- código bootstrap anterior archivado en `deprecated/initial-bootstrap/`

Documento de referencia del estado real:

- `docs/current-state.md`

## Documentación principal

- `docs/requirements/requirements.md`: requisitos funcionales y no funcionales
- `docs/technical/architecture.md`: arquitectura técnica objetivo
- `docs/current-state.md`: estado real del repositorio
- `docs/index.md`: índice y jerarquía documental
- `docs/requirements/resources/Descripcion_inicial.md`: documento de entrada y descubrimiento

## Requisitos

- Python 3.11 o 3.12
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
│   │   │   ├── athlete.json
│   │   │   └── activities/
│   │   ├── normalizado/
│   │   │   ├── activities.jsonl
│   │   │   ├── activities.csv
│   │   │   ├── streams_index.jsonl
│   │   │   └── state.json
│   │   └── logs/
│   ├── garmin_connect/
│   ├── komoot/
│   └── manual/
├── 20_consolidado/
│   ├── activities.jsonl
│   ├── activities.csv
│   ├── activity_sources.jsonl
│   ├── streams_index.jsonl
│   └── state.json
├── 30_analisis/
│   ├── informes/
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
- Mantener alineados `requirements.md`, `architecture.md` y `current-state.md`.
- Aplicar `pre-commit` antes de cada commit.
- Mantener el código activo separado del código archivado en `deprecated/`.
