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
