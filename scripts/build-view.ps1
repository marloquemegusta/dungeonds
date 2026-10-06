[CmdletBinding()]
param(
    [ValidateSet('e30', 'e60')]
    [string]$Preset = 'e30',
    [switch]$SkipBake
)

# Rebuilds one complete view preset end to end:
#   1. bake environment sprites (Blender)
#   2. bake the player spritesheet (Blender)
#   3. convert sprites + map to C
#   4. compile the ROM
# Usage:  scripts\build-view.ps1 -Preset e30
#         scripts\build-view.ps1 -Preset e60 -SkipBake

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not $SkipBake) {
    & python (Join-Path $root 'tools\bake_dungeon_iso.py') --preset $Preset
    if ($LASTEXITCODE -ne 0) { throw "environment bake failed ($Preset)" }
    & python (Join-Path $root 'tools\bake_player.py') --preset $Preset
    if ($LASTEXITCODE -ne 0) { throw "player bake failed ($Preset)" }
}

& python (Join-Path $root 'tools\convert_iso_to_c.py') --preset $Preset
if ($LASTEXITCODE -ne 0) { throw "conversion failed ($Preset)" }

& (Join-Path $PSScriptRoot 'build-project.ps1') -ProjectPath $root
if ($LASTEXITCODE -ne 0) { throw "build failed ($Preset)" }

$rom = Join-Path $root "dungeonds.nds"
$viewRom = Join-Path $root "dungeonds_$Preset.nds"
Copy-Item -LiteralPath $rom -Destination $viewRom -Force
Write-Output "VIEW_PRESET=$Preset rom=$viewRom"
