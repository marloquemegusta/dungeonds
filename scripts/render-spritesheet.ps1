<#
.SYNOPSIS
    Ejecuta el pipeline de renderizado 3D a spritesheet utilizando Blender en contenedor Docker.
.PARAMETER ModelPath
    Ruta al modelo 3D (.glb, .gltf, .fbx).
.PARAMETER OutputPath
    Ruta destino para el archivo .png del spritesheet.
.PARAMETER Animation
    Nombre o patron de la animacion (ej. 'walk', 'run').
.PARAMETER Directions
    Numero de direcciones angulares (8 o 16). Por defecto: 8.
.PARAMETER Frames
    Numero de frames por direccion. Por defecto: 8.
.PARAMETER Resolution
    Resolucion en pixeles por celda (ej. 32, 48, 64). Por defecto: 64.
.EXAMPLE
    .\scripts\render-spritesheet.ps1 -ModelPath assets\thirdparty\RobotExpressive.glb -OutputPath assets\spritesheets\robot_walk_8dir.png -Animation "Walking"
#>
param (
    [Parameter(Mandatory = $true)]
    [string]$ModelPath,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = "assets/spritesheets/spritesheet.png",

    [Parameter(Mandatory = $false)]
    [string]$Animation = "walk",

    [Parameter(Mandatory = $false)]
    [int]$Directions = 8,

    [Parameter(Mandatory = $false)]
    [int]$Frames = 8,

    [Parameter(Mandatory = $false)]
    [int]$Resolution = 64
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Get-Item -Path $PSScriptRoot\..).FullName
$modelFullPath = (Resolve-Path -Path $ModelPath).Path
$outputFullPath = [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $OutputPath))

# Ensure output directory exists
$outDir = [System.IO.Path]::GetDirectoryName($outputFullPath)
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

# Convert paths to relative paths inside the container (/workspace/...)
$relModel = $modelFullPath.Substring($workspaceRoot.Length).TrimStart('\', '/').Replace('\', '/')
$relOutput = $outputFullPath.Substring($workspaceRoot.Length).TrimStart('\', '/').Replace('\', '/')

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  BLENDER SPRITESHEET PIPELINE (DOCKER)         " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Modelo:      $relModel"
Write-Host "  Animacion:   $Animation"
Write-Host "  Direcciones: $Directions"
Write-Host "  Frames/dir:  $Frames"
Write-Host "  Resolucion:  ${Resolution}x${Resolution} px"
Write-Host "  Destino:     $relOutput"
Write-Host "-------------------------------------------------"

# Run container
$containerArgs = @(
    "run", "--rm",
    "-v", "${workspaceRoot}:/workspace",
    "towerds-blender:latest",
    "-b",
    "--python", "/workspace/scripts/render_sprites/render_spritesheet.py",
    "--",
    "--model", "/workspace/$relModel",
    "--anim", "$Animation",
    "--dirs", "$Directions",
    "--frames", "$Frames",
    "--res", "$Resolution",
    "--out", "/workspace/$relOutput"
)

Write-Host "[DOCKER] Ejecutando render..." -ForegroundColor Green
& docker @containerArgs

if (Test-Path $outputFullPath) {
    $fileInfo = Get-Item $outputFullPath
    Write-Host "-------------------------------------------------" -ForegroundColor Cyan
    Write-Host "[EXITO] Spritesheet generado correctamente: $($fileInfo.FullName) ($($fileInfo.Length) bytes)" -ForegroundColor Green
} else {
    Write-Error "[FALLO] El archivo de salida no fue creado."
}
