param([switch]$Quiet)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root 'runtime\bin'
$required = @('desmume-agent', 'libdesmume.so')
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $runtime $_)) })
if ($missing.Count -gt 0) { throw "Faltan archivos del runtime: $($missing -join ', ')" }
if (-not $Quiet) { Write-Output "DS_DESMUME_AGENT_INSTALL=PASS root=$root" }
