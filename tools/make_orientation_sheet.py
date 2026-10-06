#!/usr/bin/env python3
"""Assemble the real Blender-baked 4-orientation object sheet at 4x."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\codexlocal\dungeonds")
SRC = ROOT / "artifacts" / "orientations_e30"
OUT = ROOT / "artifacts" / "wall_objects_orientations_e30_4x.png"
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
        path = SRC / f"{name}_r{rot:03d}.png"
        im = Image.open(path).convert("RGBA").resize((CELL, CELL), Image.Resampling.NEAREST)
        sheet.alpha_composite(im, (x, y))
        # 4x marker: canvas centre x=48, runtime anchor y=72.
        draw.line((x + 48 * SCALE, y + 38 * SCALE, x + 48 * SCALE, y + 84 * SCALE), fill=(255, 70, 70, 230), width=2)
        draw.line((x + 30 * SCALE, y + 72 * SCALE, x + 66 * SCALE, y + 72 * SCALE), fill=(255, 70, 70, 230), width=2)
        draw.text((x + 8, y + CELL + 2), f"{name}  r{rot}", fill=(235, 235, 235, 255), font=font)

sheet.save(OUT)
print(f"[OK] {OUT} {sheet.size}")
