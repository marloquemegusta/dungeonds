"""Forma ARANA de la Monja de cera (exvoto) y del Monaguillo: andar arana + transicion de pie -> arana (la vuelta = al reves).
Reutiliza tools/characters/super_monja_arana.py (modo walk / trans) y bake_exvoto_super_monja.py (variables SM_*). Fuera de la ROM.
Uso: python tools/characters/arana_exvotos.py [exvoto|monaguillo ...]   Salida: assets/staging/arana_exvotos/<pers>/{fbx,walk,trans}/
Escala = la de la hoja de juego del personaje (normScale/100 porque el FBX del Tripo esta en cm; fitExtent y fitZoom de su settings.json; el monaguillo se midio con su walk).
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ.get("SM_MODEL_ROOT", "C:/codexlocal/dungeonds"))   # originales LFS y walks derivados
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
CFG = {  # pers: (normScale, fitExtent a 40 px, fitZoom)
    "exvoto": ("1.862710668667068e-4", "2.0391720414700383", "0.86"),
    "monaguillo": ("1.885375751417045e-4", "2.049601262247646", "1"),
}
RES = os.environ.get("SM_RES", "40")
NT = os.environ.get("SM_AR_NT", "8")
for pers in (sys.argv[1:] or list(CFG)):
    norm, ext, zoom = CFG[pers]
    st = ROOT / "assets/staging/arana_exvotos" / pers
    for clip, mode, frames in (("walk", "walk", "8"), ("trans", "trans", NT)):
        if os.environ.get("SM_ONLY") and os.environ["SM_ONLY"] != clip:
            continue
        env = dict(os.environ, SM_STRETCH="1", SM_MODEL_ROOT=str(MAIN), SM_AR_MODE=mode, SM_AR_CLIP=clip, SM_AR_NT=NT,
                   SM_AR_STAND=str(MAIN / f"assets/models/characters/{pers}/{pers}_walk.fbx"),
                   SM_FBX_DIR=str(st / "fbx"), SM_OUTBASE=str(st / clip), SM_CHAR=pers, SM_CLIP=clip, SM_RES=RES,
                   SM_FIXED_NORM=norm, SM_BASE_EXTENT=ext, SM_FITZOOM=zoom, SM_FRAMES=frames, SM_ONLY_WALK="1",
                   SM_TEMPLATE=str(ROOT / f"assets/sprites/characters/{pers}/settings.json"))
        subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools/characters/super_monja_arana.py"), "--", str(ROOT), pers], env=env, check=True, capture_output=True)
        subprocess.run([sys.executable, str(ROOT / "tools/characters/bake_exvoto_super_monja.py")], env=env, check=True)
        print(pers, clip, "ok")
