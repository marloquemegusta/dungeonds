[CmdletBinding()]
param([Parameter(Mandatory)][string]$ProjectPath)
if (-not (Test-Path -LiteralPath $ProjectPath)) { New-Item -ItemType Directory -Force -Path $ProjectPath | Out-Null }
$root = (Resolve-Path -LiteralPath $ProjectPath).Path
foreach ($dir in @('source','include','tests','scenarios','tools','artifacts','.ds-game-dev','docs')) { New-Item -ItemType Directory -Force -Path (Join-Path $root $dir) | Out-Null }
if (-not (Test-Path (Join-Path $root '.ds-game-dev\project.json'))) {
    @{
        rom = 'game.nds'; outputRom = 'game-blocksds.nds'; buildTemplate = 'skill-default'
        blocksdsImage = 'skylyrac/blocksds:slim-latest'; copy = @(); hostTests = @()
        scenarioDirectory = 'scenarios'; romUploadName = 'game.nds'
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $root '.ds-game-dev\project.json')
}
Write-Output "DS_SCAFFOLD=READY project=$root"
Write-Output 'NEXT=Ask product questions; draft project documents and wait for approval before writing them.'
