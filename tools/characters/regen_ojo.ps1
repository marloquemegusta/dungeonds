# Regenera el arte del Ojo del Tribunal de punta a punta (no interactivo).
# Uso (desde la raiz del worktree):
#   powershell -NonInteractive -ExecutionPolicy Bypass -File tools\characters\regen_ojo.ps1
# La cabeza abierta activa vive en assets\models\characters\ojo\source\cabeza\; el generador la prefiere automáticamente.
param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
$blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
# Tamano (celda 56x56), encuadre y boca del haz (hueso OjoMouth): en assets/sprites/characters/characters.json.

& $blender -b -P "$Root/tools/characters/build_ojo.py" -- $Root
if ($LASTEXITCODE -ne 0) { throw 'build_ojo.py fallo' }
# Render con el manifiesto (characters.json): ojo_look y ojo_sentence heredan la escala de ojo (scaleRef).
python "$Root/tools/rebuild_all.py" --only characters --char ojo,ojo_look,ojo_sentence
if ($LASTEXITCODE -ne 0) { throw 'render del ojo fallo' }
python "$Root/tools/generate_player_sprites_c.py"
if ($LASTEXITCODE -ne 0) { throw 'generate_player_sprites_c.py fallo' }
Write-Host 'Ojo regenerado. Compilar con build-project.ps1 y comprobar con los escenarios enemy_ojo_*.'
