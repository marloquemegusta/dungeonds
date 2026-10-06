#!/usr/bin/env python3
"""Create a labeled diagnostic sheet of the raw baked dungeon objects."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\codexlocal\dungeonds")
SRC = ROOT / "assets" / "dungeon_e30"
OUT = ROOT / "artifacts" / "wall_assets_e30_sheet.png"
NAMES = [
    "WR_crypt", "WC_crypt", "WR_buttress", "WC_buttress",
    "WR_ossuary", "WC_ossuary", "P_soul", "P_broken",
    "AR_row", "AR_col",
]
SPRITE = 96
CELL = 128
LABEL_H = 20
COLS = 5
ROWS = (len(NAMES) + COLS - 1) // COLS
BG = (22, 24, 34, 255)

sheet = Image.new("RGBA", (COLS * CELL, ROWS * (CELL + LABEL_H)), BG)
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("arial.ttf", 11)
except OSError:
    font = ImageFont.load_default()

for i, name in enumerate(NAMES):
    x = (i % COLS) * CELL
    y = (i // COLS) * (CELL + LABEL_H)
    im = Image.open(SRC / f"{name}.png").convert("RGBA")
    sheet.alpha_composite(im, (x + 16, y))
    # Sprite canvas centre and runtime ground anchor (x=48, y=72).
    draw.line((x + 16 + 48, y + 40, x + 16 + 48, y + 84), fill=(255, 70, 70, 220), width=1)
    draw.line((x + 16 + 32, y + 72, x + 16 + 64, y + 72), fill=(255, 70, 70, 220), width=1)
    draw.text((x + 4, y + CELL + 2), name, fill=(235, 235, 235, 255), font=font)

sheet.save(OUT)
print(f"[OK] {OUT}")
