[CmdletBinding()]
param(
    [switch]$NoRebuild,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardArgs
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot
$pythonScript = Join-Path $scriptRoot 'rebuild_all.py'

$allArgs = @()
if ($NoRebuild) {
    $allArgs += '--skip-render'
}
if ($ForwardArgs) {
    $allArgs += $ForwardArgs
}

& python $pythonScript @allArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
