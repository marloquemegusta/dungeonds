"""Transicion de pie -> arana como PINO PUENTE (se echan hacia atras). Variantes: A (media vuelta en el sitio + puente) y B (puente directo, sin girar).
Reutiliza super_monja_arana.py (SM_AR_TV=A|B) y bake_exvoto_super_monja.py. Fuera de la ROM.
Uso: python tools/characters/arana_puente.py <render|bake> <exvoto|monaguillo> <A|B> [...]
  render: 8 fotogramas grandes de Blender (perfil y 3/4) en walkthroughs/arpg-exvoto-ramas/assets/arana_exvotos_puente/render/
  bake:   fbx + hoja 8 direcciones en assets/staging/arana_exvotos_puente/<pers>/<variante>/
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ.get("SM_MODEL_ROOT", "C:/codexlocal/dungeonds"))
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
CFG = {"exvoto": ("1.862710668667068e-4", "2.0391720414700383", "0.86", "40"),
       "monaguillo": ("1.885375751417045e-4", "2.049601262247646", "1", "48")}
mode, pers, vars_ = sys.argv[1], sys.argv[2], sys.argv[3:] or ["A", "B"]
norm, ext, zoom, res = CFG[pers]
for v in vars_:
    st = ROOT / "assets/staging/arana_exvotos_puente" / pers / v
    env = dict(os.environ, SM_STRETCH="1", SM_MODEL_ROOT=str(MAIN), SM_AR_MODE="trans", SM_AR_CLIP="trans", SM_AR_NT="8", SM_AR_TV=v,
               SM_AR_STAND=str(MAIN / f"assets/models/characters/{pers}/{pers}_walk.fbx"),
               SM_FBX_DIR=str(st / "fbx"), SM_OUTBASE=str(st / "trans"), SM_CHAR=pers, SM_CLIP="trans", SM_RES=res,
               SM_FIXED_NORM=norm, SM_BASE_EXTENT=ext, SM_FITZOOM=zoom, SM_FRAMES="8", SM_ONLY_WALK="1",
               SM_TEMPLATE=str(ROOT / f"assets/sprites/characters/{pers}/settings.json"))
    if mode == "render":
        out = ROOT / "walkthroughs/arpg-exvoto-ramas/assets/arana_exvotos_puente/render"; out.mkdir(parents=True, exist_ok=True)
        env["SM_AR_TRENDER"] = str(out / f"{pers}_{v}"); env["SM_AR_TRES"] = os.environ.get("SM_AR_TRES", "384")
    r = subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools/characters/super_monja_arana.py"), "--", str(ROOT), pers], env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:]); sys.exit(1)
    for l in r.stdout.splitlines():
        if l.startswith(("DIAG", "FK", "ARANA", "EXPORTED")): print(l)
    if mode == "bake":
        subprocess.run([sys.executable, str(ROOT / "tools/characters/bake_exvoto_super_monja.py")], env=env, check=True)
    print(pers, v, mode, "ok")
