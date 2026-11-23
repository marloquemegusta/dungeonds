"""Tira de los 8 fotogramas de Blender (perfil y 3/4) de arana_puente.py render. Uso: python tools/characters/arana_puente_strip.py <pers> <var>"""
import sys
from pathlib import Path
from PIL import Image
R = Path(__file__).resolve().parents[2] / "walkthroughs/arpg-exvoto-ramas/assets/arana_exvotos_puente/render"
pers, v = sys.argv[1:3]
for view in ("perfil", "SE"):
    ims = [Image.open(R / f"{pers}_{v}_f{i}_{view}.png").convert("RGB") for i in range(8)]
    w, h = ims[0].size
    out = Image.new("RGB", (w * 4, h * 2))
    for i, im in enumerate(ims):
        out.paste(im, ((i % 4) * w, (i // 4) * h))
    out.save(R / f"{pers}_{v}_{view}_8f.png"); print(R / f"{pers}_{v}_{view}_8f.png")
