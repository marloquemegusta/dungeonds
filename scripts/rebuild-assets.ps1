[CmdletBinding()]
param(
    [switch]$NoRebuild
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot

$pythonScript = Join-Path $scriptRoot 'build_assets.py'

if ($NoRebuild) {
    & python $pythonScript
} else {
    & python $pythonScript --rebuild
}
