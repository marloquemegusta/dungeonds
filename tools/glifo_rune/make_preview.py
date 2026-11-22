#!/usr/bin/env python3
"""Hoja de contacto y GIF de la previsualizacion del Glifo a partir de la ultima ejecucion de glifo_preview."""
import glob
import os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "walkthroughs", "glifo-pulido", "assets")
CROP = (20, 192, 200, 304)      # pantalla inferior: x 20..200, y 0..112 (cubre el recorrido del stylus)

d = sorted(glob.glob(os.path.join(ROOT, "artifacts", "scenarios", "glifo_preview-*")))[-1]
fs = sorted(glob.glob(os.path.join(d, "glifo_preview_*.png")))
fr = [Image.open(f).convert("RGB").crop(CROP) for f in fs]
fr = [im.resize((im.width * 4, im.height * 4), Image.NEAREST) for im in fr]
os.makedirs(OUT, exist_ok=True)
fr[0].save(os.path.join(OUT, "glifo_preview.gif"), save_all=True, append_images=fr[1:], duration=50, loop=0)   # 1 captura cada 2 frames = 30 fps reales; 50 ms = 20 fps
sel = [fr[i] for i in range(0, len(fr), max(1, len(fr) // 12))][:12]
tw, th = fr[0].width // 2, fr[0].height // 2
sheet = Image.new("RGB", (3 * tw, 4 * th))
for k, im in enumerate(sel):
    sheet.paste(im.resize((tw, th), Image.NEAREST), ((k % 3) * tw, (k // 3) * th))
sheet.save(os.path.join(OUT, "glifo_preview_hoja.png"))
print(len(fr), "frames")
