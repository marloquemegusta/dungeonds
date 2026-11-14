# Regenera el arte del Ojo del Tribunal de punta a punta (no interactivo).
# Uso (desde la raiz del worktree):
#   powershell -NonInteractive -ExecutionPolicy Bypass -File tools\characters\regen_ojo.ps1
# La cabeza abierta activa vive en assets\models\characters\ojo\source\cabeza\; el generador la prefiere automáticamente.
param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
$blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
# Tamano y encuadre: celda 56x56 nativa (140 % del heroe 40x40), fitZoom 0.78
$RES = 56; $FIT = 0.78
# Boca del haz: hueso auxiliar OjoMouth (hijo de la mano, creado en build_ojo.py en la boca de la cabeza; MOUTH_FRAC alli); MUZZLE_FORWARD = alturas de modelo hacia delante
$MUZZLE_BONE = 'mixamorig:OjoMouth'; $MUZZLE_FORWARD = 0

& $blender -b -P "$Root/tools/characters/build_ojo.py" -- $Root
if ($LASTEXITCODE -ne 0) { throw 'build_ojo.py fallo' }
$clips = @(@('ojo_walk', 'ojo'), @('ojo_look', 'ojo_look'), @('ojo_sentence', 'ojo_sentence'))
foreach ($c in $clips) {
  node "$Root/tools/lab/export_character_headless.cjs" "$Root/assets/models/characters/ojo/$($c[0]).fbx" "$Root/assets/sprites/characters/$($c[1])" `
    --template "$Root/tools/characters/ojo_lab_template.json" --resolution $RES --fitZoom $FIT --muzzleBone $MUZZLE_BONE --muzzleForward $MUZZLE_FORWARD
  if ($LASTEXITCODE -ne 0) { throw "export $($c[0]) fallo" }
}
python "$Root/tools/generate_player_sprites_c.py"
if ($LASTEXITCODE -ne 0) { throw 'generate_player_sprites_c.py fallo' }
Write-Host 'Ojo regenerado. Compilar con build-project.ps1 y comprobar con los escenarios enemy_ojo_*.'
