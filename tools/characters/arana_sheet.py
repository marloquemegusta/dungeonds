"""Hoja de evidencia de la ARANA: 8 direcciones (columna 0 de cada fila) 4x NEAREST sobre gris medio + la Super Monja vigente de pie.
Uso: python tools/characters/arana_sheet.py <spritesheet_arana.png> <salida.png>"""
import sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
src = Image.open(sys.argv[1]).convert("RGBA")
std = Image.open(ROOT / "assets/staging/super_monja_anim/B/exvoto_super_monja/spritesheet.png").convert("RGBA")
C, Z, GRAY = 56, 4, (128, 128, 128, 255)
names = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
W = C * Z
sheet = Image.new("RGBA", (W * 4, W * 4), GRAY)
for d in range(8):
    cell = src.crop((0, d * C, C, d * C + C)).resize((W, W), Image.NEAREST)
    sheet.alpha_composite(cell, ((d % 4) * W, (d // 4) * W))
ref = std.crop((0, 0, C, C)).resize((W, W), Image.NEAREST)  # de pie, mirando al sur
sheet.alpha_composite(ref, (0, 2 * W))
Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
sheet.save(sys.argv[2])
