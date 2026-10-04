param([string]$ProjectPath = '.')
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$skill = Split-Path -Parent $PSScriptRoot
& (Join-Path $skill 'scripts\build-project.ps1') -ProjectPath $project
