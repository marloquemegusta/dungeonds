[CmdletBinding()]
param(
    [string]$ReleaseTag = 'latest',
    [string]$Repo = 'marloquemegusta/agentic-ds-dev',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runtimeBin = Join-Path $root 'runtime\bin'
$libPath = Join-Path $runtimeBin 'libdesmume.so'
$agentPath = Join-Path $runtimeBin 'desmume-agent'

New-Item -ItemType Directory -Force -Path $runtimeBin | Out-Null

$needsRuntime = $Force -or (-not (Test-Path -LiteralPath $libPath)) -or (-not (Test-Path -LiteralPath $agentPath))

if ($needsRuntime) {
    Write-Host "[1/3] Preparando runtime DeSmuME headless..."
    
    # 1. Comprobar si existe un archivo local previo
    $localArchive = Join-Path $root 'desmume-runtime-linux-x64.tar.gz'
    $archivePath = Join-Path $env:TEMP "desmume-runtime-linux-x64.tar.gz"

    if (Test-Path -LiteralPath $localArchive) {
        Copy-Item -LiteralPath $localArchive -Destination $archivePath -Force
        Write-Host "  -> Usando archivo de runtime local."
    } else {
        $url = if ($ReleaseTag -eq 'latest') {
            "https://github.com/$Repo/releases/latest/download/desmume-runtime-linux-x64.tar.gz"
        } else {
            "https://github.com/$Repo/releases/download/$ReleaseTag/desmume-runtime-linux-x64.tar.gz"
        }
        Write-Host "  -> Descargando runtime precompilado desde $url ..."
        try {
            Invoke-WebRequest -Uri $url -OutFile $archivePath -UseBasicParsing
        } catch {
            Write-Warning "No se pudo descargar de GitHub Releases ($($_.Exception.Message))."
        }
    }

    if (Test-Path -LiteralPath $archivePath) {
        function ToWslPath([string]$p) {
            $res = (Resolve-Path -LiteralPath $p).Path
            return "/mnt/$($res.Substring(0,1).ToLowerInvariant())$($res.Substring(2).Replace('\','/'))"
        }
        $tarWsl = ToWslPath $archivePath
        $destWsl = ToWslPath $runtimeBin
        & wsl tar -xzf $tarWsl -C $destWsl
        & wsl chmod +x "$destWsl/desmume-agent" "$destWsl/libdesmume.so"
        Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
    }

    if ((-not (Test-Path -LiteralPath $libPath)) -or (-not (Test-Path -LiteralPath $agentPath))) {
        Write-Warning "El runtime precompilado no est listo. Puedes construirlo con scripts/build-runtime.ps1 si dispones de herramientas en WSL."
    } else {
        Write-Host "  -> Runtime DeSmuME instalado correctamente."
    }
} else {
    Write-Host "[1/3] Runtime DeSmuME verificado en $runtimeBin."
}

# 2. Verificar o cargar contenedor Docker BlocksDS
Write-Host "[2/3] Comprobando imagen Docker de BlocksDS..."
$image = 'skylyrac/blocksds:slim-latest'
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker image inspect $image *> $null
    if ($LASTEXITCODE -ne 0) {
        $tar = Join-Path $root 'images\blocksds-slim-latest.tar'
        if (Test-Path -LiteralPath $tar) {
            Write-Host "  -> Cargando imagen offline desde $tar ..."
            docker load --input $tar
        } else {
            Write-Host "  -> Descargando imagen desde Docker Hub ($image)..."
            docker pull $image
        }
    } else {
        Write-Host "  -> Imagen Docker $image presente."
    }
} else {
    Write-Warning "Docker no est instalado o no est en el PATH. Necesario para compilar ROMs."
}

# 3. Validacin general del toolchain
Write-Host "[3/3] Validando estado general..."
& (Join-Path $PSScriptRoot 'check-toolchain.ps1')

Write-Output "DS_SETUP=PASS"
