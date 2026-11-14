# Regenera el arte del Abanderado (jefe) de punta a punta (no interactivo).
# Uso (desde la raiz del worktree):
#   powershell -NonInteractive -ExecutionPolicy Bypass -File tools\characters\regen_abanderado.ps1
# Celda 60x60 (DESIGN.md: ~54 px de alto), preset de legibilidad C2. Entradas en assets\models\characters\abanderado\source\.
param([string]$Root = (Get-Location).Path, [double]$Fit = 0.88)
$ErrorActionPreference = 'Stop'
$blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
$RES = 60

& $blender -b -P "$Root/tools/characters/build_abanderado.py" -- $Root
if ($LASTEXITCODE -ne 0) { throw 'build_abanderado.py fallo' }
$clips = @(@('abanderado_walk', 'abanderado'), @('abanderado_point', 'abanderado_point'))
foreach ($c in $clips) {
  node "$Root/tools/lab/export_character_headless.cjs" "$Root/assets/models/characters/abanderado/$($c[0]).fbx" "$Root/assets/sprites/characters/$($c[1])" `
    --template "$Root/tools/characters/abanderado_lab_template.json" --anim $c[0] --resolution $RES --fitZoom $Fit --legibility c2
  if ($LASTEXITCODE -ne 0) { throw "export $($c[0]) fallo" }
}
Write-Host 'Abanderado regenerado (hojas en assets\sprites\characters\abanderado y abanderado_point).'
