# Pone al día el repo del juego y la skill ds-game-dev (ver ONBOARDING.md §3).
# Solo avanza en rápido (fast-forward): si hay cambios locales o ramas divergentes, avisa y no toca nada.
param(
    [string]$GameRepo = 'C:\codexlocal\dungeonds',
    [string]$SkillRepo = 'C:\codexlocal\skills\agentic-ds-dev'
)
$ErrorActionPreference = 'Continue'

function Sync-Repo([string]$Path, [string]$Branch, [switch]$Lfs) {
    Write-Host "== $Path ($Branch)"
    if (-not (Test-Path (Join-Path $Path '.git'))) { Write-Host '   No existe: clónalo primero (ONBOARDING.md §2).'; return }
    $dirty = git -C $Path status --porcelain --untracked-files=no
    if ($dirty) { Write-Host '   Hay cambios sin guardar; no se actualiza.'; return }
    git -C $Path fetch origin --prune
    $current = git -C $Path branch --show-current
    if ($current -eq $Branch) {
        git -C $Path merge --ff-only "origin/$Branch"
    } else {
        git -C $Path fetch origin "${Branch}:${Branch}"
        Write-Host "   Estás en '$current'; '$Branch' actualizada sin cambiarte de rama."
    }
    if ($Lfs) { git -C $Path lfs pull }
}

Sync-Repo $GameRepo 'main' -Lfs
Sync-Repo $SkillRepo 'main'
Write-Host 'Listo.'
