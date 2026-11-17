# Regenera el arte del Abanderado (jefe) de punta a punta (no interactivo).
# Uso (desde la raiz del worktree):
#   powershell -NonInteractive -ExecutionPolicy Bypass -File tools\characters\regen_abanderado.ps1
# Celda 60x60 (DESIGN.md: ~54 px de alto), preset de legibilidad C2. Entradas en assets\models\characters\abanderado\source\.
param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
$blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'

& $blender -b -P "$Root/tools/characters/build_abanderado.py" -- $Root
if ($LASTEXITCODE -ne 0) { throw 'build_abanderado.py fallo' }
# Render con el manifiesto (characters.json): abanderado_point hereda la escala de abanderado (scaleRef).
python "$Root/tools/rebuild_all.py" --only characters --char abanderado,abanderado_point
if ($LASTEXITCODE -ne 0) { throw 'render de abanderado fallo' }
Write-Host 'Abanderado regenerado (hojas en assets\sprites\characters\abanderado y abanderado_point).'
