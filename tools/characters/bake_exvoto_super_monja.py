"""Hornea las 4 hojas de la Super Monja (Tripo 9713149f) a assets/staging/exvoto_super_monja/ con el lab rapido.
Replica la receta de tools/rebuild_all.py para exvoto_monja (walk = referencia de escala, fitZoom 0.93, celda 40)
sin tocar characters.json. Uso: python tools/characters/bake_exvoto_super_monja.py
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = os.environ.get("SM_CHAR", "exvoto_super_monja")
CLIP = os.environ.get("SM_CLIP", "walk")   # fbx/animacion = <CH>_<CLIP>
FITZOOM = os.environ.get("SM_FITZOOM", "0.93")
FRAMES = os.environ.get("SM_FRAMES")        # n.o de fotogramas por direccion (trans: NT)
RES = os.environ.get("SM_RES", "40")  # celda cuadrada (el lab no admite ancho/alto distintos)
# Fijo (misma escala px/m que la Monja de 40 px): normScale del rig estirado y extent de referencia escalado a la celda.
FIXED = os.environ.get("SM_FIXED_NORM")  # p.ej. 1.8464e-4
BASE_EXTENT = float(os.environ.get("SM_BASE_EXTENT", "1.9782330363787424"))
FAST = ROOT / "tools/lab/fast/export_character_fast.cjs"
TEMPLATE = Path(os.environ["SM_TEMPLATE"]) if os.environ.get("SM_TEMPLATE") else ROOT / "assets/sprites/characters/skeleton/settings.json"
OUTBASE = Path(os.environ["SM_OUTBASE"]) if os.environ.get("SM_OUTBASE") else ROOT / "assets/staging/exvoto_super_monja"
FBXDIR = Path(os.environ["SM_FBX_DIR"]) if os.environ.get("SM_FBX_DIR") else ROOT / f"assets/models/characters/{CH}"
ONLY_WALK = os.environ.get("SM_ONLY_WALK") == "1"
CLIPS = {  # nombre: (anim, es_ref)
    CH: (CH + "_" + CLIP, True),
    CH + "_pray_stand": (CH + "_pray_stand", False),
    CH + "_pray_kneel": (CH + "_pray_kneel", False),
    CH + "_stand_up": (CH + "_stand_up", False),
}
ANIMTXT = sys.argv[1:] and dict(a.split("=", 1) for a in sys.argv[1:]) or {}


def cmd(name, anim, ref_fit=None):
    c = ["node", str(FAST), str(FBXDIR / f"{anim}.fbx"), str(OUTBASE / name),
         "--template", str(TEMPLATE), "--anim", ANIMTXT.get(name, anim), "--resolution", RES, "--fitZoom", FITZOOM,
         "--light", "neutral", "--outline", "none", "--saturation", "1.0", "--legibility", "c2"]
    if FRAMES:
        c += ["--frames", FRAMES]
    if ref_fit:
        c += ["--fitExtent", repr(ref_fit[0])]
        if ref_fit[1]:
            c += ["--normScale", repr(ref_fit[1])]
    return c


def run(c):
    r = subprocess.run(c, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr); sys.exit(1)
    fit = None
    for l in r.stdout.splitlines():
        if l.startswith("WARNING"): print(l)
        if l.startswith("FIT "): fit = json.loads(l[4:])
    return fit

ref = run(cmd(CH, CH + "_" + CLIP, (BASE_EXTENT * int(RES) / 40, float(FIXED)) if FIXED else None))
rf = (ref["extent"], ref.get("normScale"))
if FIXED:
    rf = (BASE_EXTENT * int(RES) / 40, float(FIXED))
print("ref FIT", ref)
for n, (a, isref) in CLIPS.items():
    if not isref and not ONLY_WALK:
        print(n, run(cmd(n, a, rf)))
