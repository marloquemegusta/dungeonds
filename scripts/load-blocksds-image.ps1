$ErrorActionPreference = 'Stop'
$image = 'skylyrac/blocksds:slim-latest'
$tar = Join-Path (Split-Path -Parent $PSScriptRoot) 'images\blocksds-slim-latest.tar'

if (Test-Path -LiteralPath $tar) {
    Write-Host "Cargando imagen offline desde $tar ..."
    docker load --input $tar
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo cargar la imagen BlocksDS offline.' }
} else {
    Write-Host "Tar offline no encontrado; descargando imagen directamente ($image)..."
    docker pull $image
    if ($LASTEXITCODE -ne 0) { throw "No se pudo descargar la imagen BlocksDS: $image" }
}

docker image inspect $image *> $null
if ($LASTEXITCODE -ne 0) { throw "La imagen cargada no tiene el nombre esperado: $image" }
Write-Output "BLOCKSDS_IMAGE=PASS image=$image"
