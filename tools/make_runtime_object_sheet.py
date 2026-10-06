#!/usr/bin/env python3
"""Preview the exact current runtime object PNGs without modifying them."""

from pathlib import Path
from PIL import Image

ROOT = Path(r"C:\codexlocal\dungeonds")
SRC = ROOT / "assets" / "dungeon_e30"
OUT = ROOT / "artifacts" / "runtime_objects_e30_clean_4x.png"
NAMES = [
    "WR_crypt", "WC_crypt", "WR_buttress", "WC_buttress",
    "WR_ossuary", "WC_ossuary", "P_soul", "P_broken",
    "AR_row", "AR_col",
]
SCALE = 4
CELL = 96
COLS = 5
ROWS = 2
BG = (22, 24, 34, 255)

sheet = Image.new("RGBA", (COLS * CELL * SCALE, ROWS * CELL * SCALE), BG)
for i, name in enumerate(NAMES):
    im = Image.open(SRC / f"{name}.png").convert("RGBA")
    assert im.size == (CELL, CELL), (name, im.size)
    im = im.resize((CELL * SCALE, CELL * SCALE), Image.Resampling.NEAREST)
    x = (i % COLS) * CELL * SCALE
    y = (i // COLS) * CELL * SCALE
    sheet.alpha_composite(im, (x, y))

sheet.save(OUT)
print(f"[OK] {OUT} {sheet.size}")
