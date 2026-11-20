#!/usr/bin/env python3
"""Contact sheet of the baked placeholder sprites, 4x NEAREST on dark grey, labelled.

  python tools/placeholders/contact_sheet.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SPR = ROOT / "assets" / "sprites" / "placeholders"
OUT = ROOT / "walkthroughs" / "arpg-predemo" / "assets" / "placeholders_4x.png"
NAMES = ["runa_xp", "orbe_vida", "orbe_mana", "maldicion", "aliado_marca"]
ZOOM = 4
CELL = 96
PAD = 24


def main():
    W = PAD + len(NAMES) * (CELL + PAD)
    H = CELL + 2 * PAD + 20
    sheet = Image.new("RGB", (W, H), (48, 48, 48))
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(NAMES):
        spr = Image.open(SPR / (name + ".png")).convert("RGBA")
        big = spr.resize((spr.width * ZOOM, spr.height * ZOOM), Image.NEAREST)
        x = PAD + i * (CELL + PAD)
        bg = Image.new("RGBA", (CELL, CELL), (72, 72, 72, 255))
        bg.alpha_composite(big, ((CELL - big.width) // 2, CELL - big.height))
        sheet.paste(bg.convert("RGB"), (x, PAD))
        draw.text((x, PAD + CELL + 6), f"{name} {spr.width}x{spr.height}", fill=(220, 220, 220))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
