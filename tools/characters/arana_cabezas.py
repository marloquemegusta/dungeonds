"""Hoja comparativa de candidatas de cabeza: filas = candidatas, columnas = frente / SE / perfil (512 px reducidos a 384)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
d = Path(sys.argv[1]); names = sys.argv[3:]
views = ["frente", "SE", "perfil"]; S = 384
sheet = Image.new("RGB", (S * 3, S * len(names)), (128, 128, 128))
dr = ImageDraw.Draw(sheet)
for r, n in enumerate(names):
    for c, v in enumerate(views):
        sheet.paste(Image.open(d / f"{n}_{v}.png").convert("RGB").resize((S, S), Image.LANCZOS), (c * S, r * S))
        dr.text((c * S + 6, r * S + 6), f"{n} | {v}", fill=(255, 255, 0))
sheet.save(sys.argv[2])
