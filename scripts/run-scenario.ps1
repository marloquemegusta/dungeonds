param(
    [Parameter(Mandatory)] [string]$RomPath,
    [Parameter(Mandatory)] [string]$ScenarioPath,
    [Parameter(Mandatory)] [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $root 'runtime\run_scenario.py'
$library = Join-Path $root 'runtime\bin\libdesmume.so'
foreach ($path in @($RomPath, $ScenarioPath, $runner, $library)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Ruta no encontrada: $path" }
}
New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
function WslPath([string]$path) {
    $resolved = (Resolve-Path -LiteralPath $path).Path
    return "/mnt/$($resolved.Substring(0,1).ToLowerInvariant())$($resolved.Substring(2).Replace('\','/'))"
}
$log = Join-Path $OutputPath 'emulator.log'
& wsl python3 -u (WslPath $runner) (WslPath $RomPath) (WslPath $ScenarioPath) (WslPath $OutputPath) (WslPath $library) 2>&1 | Tee-Object -FilePath $log
if ($LASTEXITCODE -ne 0) { throw 'El escenario DeSmuME falló.' }
Write-Output "DS_SCENARIO_RESULT=PASS output=$OutputPath"
