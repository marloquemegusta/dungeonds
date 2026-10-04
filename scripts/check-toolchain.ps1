$ErrorActionPreference = 'Stop'
$missing = @()

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $missing += 'Docker CLI (necesario para compilar ROMs)'
} else {
    try {
        $inspect = docker image inspect skylyrac/blocksds:slim-latest 2>&1
        if ($LASTEXITCODE -ne 0) {
            if ($inspect -match 'failed to connect|daemon is running|error during connect') {
                $missing += 'Docker daemon no responde (inicia Docker Desktop)'
            } else {
                $missing += 'imagen BlocksDS (ejecuta scripts/setup.ps1 o scripts/load-blocksds-image.ps1)'
            }
        }
    } catch {
        $missing += 'Docker daemon no responde'
    }
}

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    $missing += 'WSL2 (necesario para DeSmuME y GDB)'
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $missing += 'Python'
}

$runtime = Join-Path $PSScriptRoot '..\runtime\bin\libdesmume.so'
$agent = Join-Path $PSScriptRoot '..\runtime\bin\desmume-agent'
if ((-not (Test-Path -LiteralPath $runtime)) -or (-not (Test-Path -LiteralPath $agent))) {
    $missing += 'DeSmuME runtime (ejecuta scripts/setup.ps1)'
}

if ($missing.Count) {
    Write-Output ('DS_TOOLCHAIN=INCOMPLETE missing=' + ($missing -join '; '))
    exit 1
}
Write-Output 'DS_TOOLCHAIN=PASS'
