# Instalación en Nono

Esta guía instala `nono-sports` en el host de Nono como aplicación de usuario. La ruta de datos ya está sincronizada por Google Drive, por lo que no hay que copiar los datos deportivos descargados.

## Decisión de instalación

Para la v1 se recomienda:

- instalar el proyecto en `/home/nono/apps/nono-sport`
- usar un entorno virtual local en `/home/nono/apps/nono-sport/.venv`
- ejecutar los comandos como usuario `nono`
- configurar datos en `/home/nono/drive/01_ambitos/02_personal/40_deporte`
- guardar configuración sensible en `/home/nono/.config/nono-sports/env`
- guardar tokens OAuth en `/home/nono/.local/state/nono-sports/strava_tokens.json`

No se recomienda instalar el paquete globalmente con `sudo pip` ni guardar secretos en Google Drive o dentro del repositorio.

## Permisos y webhooks futuros

La v1 no expone ningún servicio de escucha. Por tanto, lo más simple y seguro es ejecutar sincronización, normalización, consolidación y validación como `nono`.

Si más adelante se añaden webhooks:

- el listener público debería tener el mínimo privilegio posible
- idealmente el listener no debería tener acceso a tokens Strava
- el listener puede registrar eventos y delegar la descarga real en un worker ejecutado como `nono`
- si un servicio separado necesita escribir en datos, se deberá crear un grupo compartido y revisar permisos/ACLs del mount de Drive

Con Google Drive montado bajo `/home/nono/drive`, ejecutar el proceso operativo como `nono` evita problemas típicos de acceso entre usuarios a mounts FUSE o sincronizados.

## 1. Comprobación inicial del host

Desde tu equipo:

```bash
ssh nono@nono.carlos.prades.name
```

La primera vez, revisa y acepta la huella del host solo si es la esperada.

En Nono:

```bash
whoami
echo "$HOME"
python3 --version
git --version
test -d "$HOME/drive/01_ambitos/02_personal/40_deporte" && echo "data root OK"
ls -ld "$HOME/drive/01_ambitos/02_personal/40_deporte"
ls -l "$HOME/drive/01_ambitos/02_personal/40_deporte/20_consolidado"
```

Valores esperados:

- `whoami` debe devolver `nono`
- el data root debe existir
- `20_consolidado` debe contener los ficheros ya generados en desarrollo
- Python debe ser 3.11 o 3.12 para esta versión del proyecto

Si `python3 --version` devuelve una versión no soportada, por ejemplo `3.14`, no uses ese intérprete para crear el entorno virtual. Comprueba primero si existe una versión compatible:

```bash
command -v python3.12 || true
command -v python3.11 || true
```

Si no existe, instala una versión compatible antes de continuar. En Ubuntu/Debian, si está disponible en tus repositorios:

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

Si el paquete no está disponible, usa `uv` como gestor de Python de usuario. Esta opción no modifica el Python del sistema y no requiere `sudo`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
uv python install 3.12
uv python find 3.12
```

## 2. Instalar proyecto

En Nono:

```bash
mkdir -p "$HOME/apps"
cd "$HOME/apps"
git clone git@github.com:coosko/nono-sports.git nono-sport
cd "$HOME/apps/nono-sport"
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e .
```

Si el repositorio ya existe:

```bash
cd "$HOME/apps/nono-sport"
git pull
uv pip install --python .venv/bin/python -e .
```

Para poder ejecutar tests en Nono, instala dependencias de desarrollo de forma opcional:

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

## 3. Configurar entorno

En Nono:

```bash
mkdir -p "$HOME/.config/nono-sports"
chmod 700 "$HOME/.config/nono-sports"
```

Crea `/home/nono/.config/nono-sports/env` con:

```bash
NONO_SPORT_DATA_ROOT=/home/nono/drive/01_ambitos/02_personal/40_deporte
STRAVA_CLIENT_ID=<client_id>
STRAVA_CLIENT_SECRET=<client_secret>
STRAVA_REDIRECT_URI=http://localhost/exchange_token
LOG_LEVEL=INFO
```

Después:

```bash
chmod 600 "$HOME/.config/nono-sports/env"
```

`nono-sports` carga este fichero automáticamente. El `.env` del repositorio queda como opción de desarrollo local.

## 4. Copiar tokens Strava

Copiar el token ya autorizado evita repetir OAuth en Nono. Desde tu equipo de desarrollo:

```bash
ssh nono@nono.carlos.prades.name 'mkdir -p "$HOME/.local/state/nono-sports" && chmod 700 "$HOME/.local/state" "$HOME/.local/state/nono-sports"'
scp "$HOME/.local/state/nono-sports/strava_tokens.json" \
  nono@nono.carlos.prades.name:/home/nono/.local/state/nono-sports/strava_tokens.json
ssh nono@nono.carlos.prades.name 'chmod 600 "$HOME/.local/state/nono-sports/strava_tokens.json"'
```

No copies este fichero al repositorio ni a Google Drive.

Importante: Strava puede rotar el `refresh_token` cuando se renueva el acceso. Después de copiar el token, conviene que Nono sea el dueño de la sincronización. Evita ejecutar descargas Strava desde desarrollo y desde Nono indistintamente, porque cada máquina tendría una copia distinta del token. Si vuelves a ejecutar sincronización desde desarrollo, copia de nuevo el token vigente al host que vaya a continuar el proceso.

## 5. Validar instalación

En Nono:

```bash
cd "$HOME/apps/nono-sport"
./.venv/bin/python -m nono_sports strava prepare-dirs
./.venv/bin/python -m nono_sports strava validate
```

La validación no llama a Strava y no consume cuota. Si el estado es `warning` por descarga incompleta, es aceptable mientras los avisos coincidan con el estado conocido.

Para verificar que Nono puede reconstruir las capas derivadas:

```bash
./.venv/bin/python -m nono_sports strava normalize
./.venv/bin/python -m nono_sports build-consolidated
./.venv/bin/python -m nono_sports strava validate
```

## 6. Validación del usuario

El Paso 11 queda validado cuando:

- `nono-sports` se ejecuta en Nono como usuario `nono`
- `NONO_SPORT_DATA_ROOT` resuelve a `/home/nono/drive/01_ambitos/02_personal/40_deporte`
- el comando `strava validate` genera informe en `30_analisis/informes`
- Nono ve `20_consolidado/activities.jsonl`
- los tokens quedan en `/home/nono/.local/state/nono-sports/strava_tokens.json` con permisos `600`
