#!/usr/bin/env python3
"""Contact sheet (4x NEAREST) of one laser look from the frames of scenarios/abc_laser.json (see tools/abc_scenes.py).

  python tools/laser_contact.py <A|B|C|actual> [--frames name:idx,...] [--out FILE]

Key frames by default: 50 % of the charge, the frame just before READY, the READY frame, held, the shot and the fade.
The run directory is the one tools/abc_gif.py laser --run writes (.ds-game-dev/abc_runs/laser).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".ds-game-dev" / "abc_runs" / "laser"
OUT = ROOT / "walkthroughs" / "laser-abc" / "assets"
VI = {"actual": 0, "A": 1, "B": 2, "C": 3}
BOTTOM_Y = 192
CROP = (96, 30, 160, 92)
# (label, sequence, index): index into the sequence (3ready is one frame per game frame; READY = index 15 -> first READY frame)
KEY = [("50 % de carga", "2charge", 10), ("antes de LISTO", "3ready", 14), ("LISTO (1er frame)", "3ready", 15),
       ("LISTO +8", "3ready", 17), ("mantenido", "4hold", 20), ("disparo +0", "6shot", 0), ("disparo +3", "6shot", 3),
       ("disparo +8", "6shot", 8), ("desvanecido +14", "6shot", 14), ("desvanecido +22", "6shot", 22)]


def font():
    try:
        return ImageFont.load_default(size=14)
    except TypeError:
        return ImageFont.load_default()


def sheet(look, keys, out, cols=2, scale=4):
    vi = VI[look]
    x, y, w, h = CROP
    cw, ch = w * scale, h * scale
    rows = (len(keys) + cols - 1) // cols
    W = Image.new("RGB", (cols * cw + (cols - 1) * 6, rows * (ch + 20) + (rows - 1) * 6), (20, 18, 16))
    d = ImageDraw.Draw(W)
    for i, (lab, seq, idx) in enumerate(keys):
        f = RUN / f"v{vi}_{seq}_{idx:04d}.png"
        if not f.exists():
            print("missing", f.name)
            continue
        im = Image.open(f).convert("RGB").crop((x, BOTTOM_Y + y, x + w, BOTTOM_Y + y + h)).resize((cw, ch), Image.NEAREST)
        ox, oy = (i % cols) * (cw + 6), (i // cols) * (ch + 26)
        d.text((ox + 4, oy + 2), f"{look}  {lab}  ({seq} {idx})", fill=(232, 220, 190), font=font())
        W.paste(im, (ox, oy + 20))
    out.parent.mkdir(parents=True, exist_ok=True)
    W.save(out)
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("look", choices=list(VI))
    ap.add_argument("--frames", help="label:seq:idx,label:seq:idx (default: key frames)")
    ap.add_argument("--out")
    a = ap.parse_args()
    keys = KEY
    if a.frames:
        keys = [(p.split(":")[0], p.split(":")[1], int(p.split(":")[2])) for p in a.frames.split(",")]
    sheet(a.look, keys, Path(a.out) if a.out else OUT / f"contact_{a.look}.png")
