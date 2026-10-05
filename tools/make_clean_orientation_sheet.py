#!/usr/bin/env python3
"""Clean 4x sheet of the actual baked RGBA sprites, without diagnostics."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\codexlocal\dungeonds")
SRC = ROOT / "assets" / "dungeon_e30"
OUT = ROOT / "walkthroughs" / "02-isometric-renderer" / "assets" / "orientations_e30_4x.png"
NAMES = [
    "WR_crypt", "WC_crypt", "WR_buttress", "WC_buttress",
    "WR_ossuary", "WC_ossuary", "P_soul", "P_broken",
    "AR_row", "AR_col",
]
ROTS = (0, 90, 180, 270)
SCALE = 4
SPRITE = 96
CELL = SPRITE * SCALE
LABEL_H = 36
BG = (22, 24, 34, 255)

sheet = Image.new("RGBA", (len(ROTS) * CELL, len(NAMES) * (CELL + LABEL_H)), BG)
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("arial.ttf", 36)
except OSError:
    font = ImageFont.load_default()

for row, name in enumerate(NAMES):
    y = row * (CELL + LABEL_H)
    for col, rot in enumerate(ROTS):
        x = col * CELL
        im = Image.open(SRC / f"{name}_r{rot:03d}.png").convert("RGBA")
        im = im.resize((CELL, CELL), Image.Resampling.NEAREST)
        sheet.alpha_composite(im, (x, y))
        draw.text((x + 8, y + CELL + 2), f"{name}  r{rot}", fill=(235, 235, 235, 255), font=font)

sheet.save(OUT)
print(f"[OK] {OUT} {sheet.size}")
