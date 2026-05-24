param(
    [string]$Root = $env:NONO_SPORT_DATA_ROOT
)

if (-not $Root) {
    Write-Host "ERROR: Debes proporcionar la ruta raíz con -Root o establecer la variable de entorno NONO_SPORT_DATA_ROOT."
    exit 1
}

$directories = @(
    "00_referencia",
    "10_fuentes\strava\raw\activities",
    "10_fuentes\strava\normalizado",
    "10_fuentes\strava\logs",
    "10_fuentes\garmin_connect",
    "10_fuentes\komoot",
    "10_fuentes\manual",
    "20_consolidado",
    "30_analisis\informes",
    "30_analisis\planes",
    "30_analisis\seguimiento",
    "30_analisis\graficas",
    "90_archivo"
)

$files = @(
    "10_fuentes\strava\raw\athlete.json",
    "10_fuentes\strava\normalizado\activities.jsonl",
    "10_fuentes\strava\normalizado\activities.csv",
    "10_fuentes\strava\normalizado\streams_index.jsonl",
    "10_fuentes\strava\normalizado\state.json",
    "20_consolidado\activities.jsonl",
    "20_consolidado\activities.csv",
    "20_consolidado\activity_sources.jsonl",
    "20_consolidado\streams_index.jsonl",
    "20_consolidado\state.json"
)

foreach ($directory in $directories) {
    $path = Join-Path -Path $Root -ChildPath $directory
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    Write-Host "Created directory: $path"
}

foreach ($file in $files) {
    $path = Join-Path -Path $Root -ChildPath $file
    $parent = Split-Path -Path $path -Parent
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    if (-Not (Test-Path -Path $path)) {
        New-Item -ItemType File -Path $path | Out-Null
    }
    Write-Host "Created file: $path"
}

Write-Host "Estructura creada correctamente en: $Root"
