#!/usr/bin/env bash
# Regenera el remate de la Super Monja arana (walkthroughs/remate-smonja): Blender -> lab rapido -> bins + tablas -> build.
# Uso (desde la raiz del worktree): bash tools/characters/regen_remate_smonja.sh   (SM_VAR=A para la variante descartada)
# Los modelos fuente se leen de SM_MODEL_ROOT (por defecto la carpeta principal: en un worktree son punteros LFS).
set -e
W=$(pwd -W 2>/dev/null || pwd)
export SM_MODEL_ROOT=${SM_MODEL_ROOT:-C:/codexlocal/dungeonds}
GLB=scratch_lab/glb_smonja
rm -rf "$GLB"
REMATE_GLB_DIR="$W/$GLB" PYTHONUTF8=1 "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/ds_remate_smonja.py -- . x all
rm -rf walkthroughs/remate-smonja/assets/lab_out
node tools/lab/fast/export_scene_fast.cjs "$GLB" walkthroughs/remate-smonja/assets/lab_out --ppm 38 --resolution 160 --shadow-skip-materials cera_o1,cera_o2
SMONJA_GLB="$GLB" python tools/pack_remate_smonja.py
powershell -NonInteractive -ExecutionPolicy Bypass -File 'C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1' -ProjectPath "$W" -Variant arpg-lab
