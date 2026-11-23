"""Ronda de animacion de la Super Monja (solo andar), fuera de la ROM. Color vigente (A negro puro).
Genera assets/staging/super_monja_anim/<A|B|C>/exvoto_super_monja/spritesheet.png (56 px, 8x8) con el constructor
Blender (SM_WALK_ONLY=1, SM_STYLE) y el horneado del lab rapido. Las hojas vigentes no se tocan.
  A al extremo: cabeza ~40 grados, encorvada, brazos mas largos, zancada larga y lenta
  B andar roto: tirones de tiempo, pierna que arrastra, sacudidas de tronco, tiron de cabeza
  C acecho: inclinada como depredadora, cuello adelantado, brazos adelantados y abiertos, pasos largos
Uso: python tools/characters/super_monja_anim.py [A B C]
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
STAGE = ROOT / "assets/staging/super_monja_anim"
BASE = {"SM_WALK_ONLY": "1", "SM_RES": "56", "SM_FIXED_NORM": "1.8464e-4"}
STYLES = {
    "A": {"SM_HEAD_ROLL": "45", "SM_STOOP": "32", "SM_HIPS_PITCH": "16", "SM_ARM_LEN": "1.45", "SM_WALK_STRIDE": "1.15", "SM_WALK_FRAMES": "60"},
    "B": {"SM_STYLE": "B", "SM_HEAD_ROLL": "25", "SM_STOOP": "16", "SM_HIPS_PITCH": "8", "SM_WALK_STRIDE": "0.8", "SM_WALK_FRAMES": "44",
          "SM_B_STUTTER": "0.9", "SM_B_DRAG": "26", "SM_B_JERK": "28", "SM_B_YANK": "60", "SM_B_SWAY": "14"},
    "C": {"SM_STYLE": "C", "SM_HEAD_ROLL": "8", "SM_STOOP": "8", "SM_HIPS_PITCH": "18", "SM_NECK_LEN": "1.6", "SM_WALK_STRIDE": "1.15",
          "SM_WALK_FRAMES": "60", "SM_C_SPINE": "6", "SM_C_NECK": "12", "SM_C_HEAD": "-34", "SM_C_ARM_FWD": "70", "SM_C_ARM_OPEN": "30", "SM_C_ELBOW": "15"},
}

for v in (sys.argv[1:] or list(STYLES)):
    env = dict(os.environ, **BASE, **STYLES[v])
    env["SM_OUT_DIR"] = str(STAGE / "fbx" / v)
    env["SM_FBX_DIR"] = env["SM_OUT_DIR"]
    env["SM_ONLY_WALK"] = "1"
    env["SM_OUTBASE"] = str(STAGE / v)
    subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools/characters/build_exvoto_super_monja.py"), "--", str(ROOT), "exvoto_super_monja"],
                   env=env, check=True)
    if not (STAGE / "fbx" / v / "exvoto_super_monja_walk.fbx").exists():
        sys.exit("Blender fallo en el estilo " + v)
    subprocess.run([sys.executable, str(ROOT / "tools/characters/bake_exvoto_super_monja.py")], env=env, check=True)
