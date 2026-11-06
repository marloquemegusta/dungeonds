#!/usr/bin/env python3
"""Contact sheet of the sniper collimation captures: 4x NEAREST crop around the hero and the beam.

Run: python tools/collim_contact_sheet.py   (reads test_output/sandbox_sniper_collim_{A,B,C}/charge_*.png)
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "walkthroughs" / "sniper-collimation" / "assets"
FRAMES = (0, 4, 8, 12, 16, 20, 24, 30)
BOX = (20, 192 + 56, 140, 192 + 100)   # x0, y0, x1, y1 in the 256x384 capture (lower screen)
S = 4

for style in "ABC":
    cap = ROOT / "test_output" / f"sandbox_sniper_collim_{style}"
    w, h = (BOX[2] - BOX[0]) * S, (BOX[3] - BOX[1]) * S
    sheet = Image.new("RGB", (2 * w + 6, 4 * (h + 14)), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(FRAMES):
        im = Image.open(cap / f"charge_{f:04d}.png").convert("RGB").crop(BOX).resize((w, h), Image.NEAREST)
        x, y = (i % 2) * (w + 6), (i // 2) * (h + 14) + 12
        sheet.paste(im, (x, y))
        d.text((x + 2, y - 11), f"ROM real, estilo {style}, frame {f}", fill=(255, 255, 255))
    sheet.save(OUT / f"contact_collim_{style}.png")
