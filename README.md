# nono-sports

Proyecto Python para sincronizar datos deportivos desde Strava, normalizarlos y combinarlos con otras fuentes. No incluye interfaz gráfica; el foco está en integración de datos y procesamiento backend.

## Estructura inicial

- `src/nono_sports/`
  - `strava_sync.py`: sincronizador con Strava
  - `normalizer.py`: normalización de datos
  - `integrator.py`: integración entre orígenes
  - `config.py`: carga de variables de entorno
- `tests/`: pruebas unitarias básicas
- `.github/workflows/`: configuración de CI para GitHub Actions
- `.gitignore`: exclusiones de Git
- `pyproject.toml`: configuración de empaquetado y dependencias
- `requirements-dev.txt`: dependencias de desarrollo
- `.pre-commit-config.yaml`: hooks de calidad
- `.env.example`: ejemplo de variables sensibles

## Requisitos

- Python 3.11 o superior
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

3. Copiar el archivo de ejemplo y configurar credenciales seguras:

```bash
cp .env.example .env
```

4. Ejecutar los tests iniciales:

```bash
python -m pytest
```

## Estructura de datos

Para los datos usaremos una carpeta raíz configurada en el entorno. En desarrollo podemos usar un ejemplo como:

`H:\Mi unidad\01_ambitos\02_personal\40_deporte`

Dentro de ese directorio la estructura esperada es:

```text
H:\Mi unidad\01_ambitos\02_personal\40_deporte
├── 00_referencia/
├── 10_fuentes/
│   ├── strava/
│   │   ├── raw/
│   │   │   ├── athlete.json
│   │   │   ├── activities/
│   │   │   └── streams/
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

### Crear la estructura

Se ha añadido un script en `scripts/create_data_directories.py` y otro en `scripts/create_data_directories.ps1`.

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

Si la ruta no está montada, ejecuta el script desde el sistema Windows donde la unidad `H:` exista.

## GitHub

1. Inicializa el repositorio si aún no está creado:

```bash
git init
```

2. Crea el primer commit:

```bash
git add .
git commit -m "chore: inicializar proyecto nono-sports"
```

3. Crea el repositorio remoto en GitHub y conéctalo:

```bash
git remote add origin git@github.com:<usuario>/nono-sports.git
git branch -M main
git push -u origin main
```

> Si necesitas crear el repositorio desde la CLI, usa `gh repo create <usuario>/nono-sports --public --source=. --remote=origin`.

## Buenas prácticas

- No subir el archivo `.env` ni variables secretas al repositorio.
- Usar CI en GitHub Actions para tests automatizados.
- Aplicar `pre-commit` antes de cada commit.
- Mantener dependencias actualizadas con revisiones de seguridad.
