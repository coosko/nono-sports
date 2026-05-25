# Autenticación Strava

Este documento describe el proceso manual asistido para autorizar a Nono a leer datos de Strava.

## Ruta de datos local

En desarrollo, `NONO_SPORT_DATA_ROOT` debe apuntar al directorio que contiene `10_fuentes`.

Valor local recomendado:

```bash
export NONO_SPORT_DATA_ROOT='/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte'
```

No debe apuntar a `.../10_fuentes`, porque el proyecto crea esa carpeta por debajo de la raíz.

## Configuración previa en Strava

En la aplicación de Strava, configura el dominio de callback como:

```text
localhost
```

La URI de redirect usada por defecto es:

```text
http://localhost/exchange_token
```

## Variables de entorno

Configura `.env` con:

```bash
NONO_SPORT_DATA_ROOT="/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte"
STRAVA_CLIENT_ID="<client_id>"
STRAVA_CLIENT_SECRET="<client_secret>"
STRAVA_REDIRECT_URI="http://localhost/exchange_token"
```

## Paso 1. Preparar carpetas

```bash
./.venv/bin/python -m nono_sports strava prepare-dirs
```

## Paso 2. Generar URL de autorización

```bash
./.venv/bin/python -m nono_sports strava auth
```

Abre la URL generada en el navegador y concede los permisos solicitados.

## Paso 3. Copiar el código

Tras aceptar, Strava redirigirá a una URL parecida a:

```text
http://localhost/exchange_token?state=&code=<CODE>&scope=read,read_all,profile:read_all,activity:read_all
```

Puede que el navegador muestre un error porque no hay servidor escuchando en `localhost`; eso es normal. Copia el valor del parámetro `code`.

## Paso 4. Intercambiar el código por tokens

```bash
./.venv/bin/python -m nono_sports strava auth --code "<CODE>"
```

Los tokens se guardan fuera del repositorio en:

```text
~/.local/state/nono-sports/strava_tokens.json
```

Este fichero es estado sensible de autenticación. No forma parte del árbol de datos deportivos y no debe sincronizarse con Google Drive ni compartirse.

No compartas el `code`, el `client_secret`, el `access_token` ni el `refresh_token`.

## Caducidad y renovación de tokens

Strava emite `access_token` de corta duración. Caducan a las 6 horas y se renuevan con el `refresh_token`.

El cliente de Nono Sports:

- comprueba `expires_at` antes de llamar a Strava
- refresca automáticamente si el token caduca en 1 hora o menos
- guarda el nuevo `access_token`, `expires_at` y `refresh_token` en `~/.local/state/nono-sports/strava_tokens.json`
- usa siempre el último `refresh_token` guardado, porque Strava puede rotarlo en cada renovación

Acción normal del usuario:

- ninguna; la renovación es automática durante `fetch-context` y `fetch-activities`

Acción si falla la renovación:

- repetir `./.venv/bin/python -m nono_sports strava auth`
- abrir la URL generada
- autorizar con los scopes esperados
- ejecutar `./.venv/bin/python -m nono_sports strava auth --code "<CODE>"`

Referencia oficial: Strava Authentication documenta que los access tokens caducan a las 6 horas, que el refresh endpoint devuelve un nuevo refresh token y que debe persistirse siempre el último.
