param(
    [switch]$SkipUpload
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== 1/3 Exportando mapas a C ===" -ForegroundColor Cyan
& python "$root\tools\export_maps_to_c.py"

Write-Host "=== 2/3 Compilando ROM (Docker BlocksDS) ===" -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File "$root\scripts\build-project.ps1" -ProjectPath "$root"
Copy-Item -Force "$root\game.nds" "$root\towerdefense.nds"

if (-not $SkipUpload) {
    Write-Host "=== 3/3 Subiendo ROM a Nintendo DS por FTP ===" -ForegroundColor Cyan
    & powershell -ExecutionPolicy Bypass -File "$root\scripts\upload-rom.ps1" -ConfirmUpload -ProjectPath "$root" -RomPath "$root\towerdefense.nds" -RemoteName "towerdefense.nds"
}
Write-Host "Pipeline completado con exito!" -ForegroundColor Green
