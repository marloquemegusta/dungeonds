#!/usr/bin/env python3
"""Contact sheet (4x NEAREST) of the night camp props with their baked shadow, old row above, new row below.
usage: python tools/props/props_night_sheet.py [out.png]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
R = os.path.join(ROOT, "assets/environment/cathedral/props/render")
PAIRS = [("camp_mesa", "camp_n_mesa"), ("camp_arcon", "camp_n_arcon"), ("camp_atril", "camp_n_atril"),
         ("camp_jergon", "camp_n_jergon"), ("camp_hoguera", "camp_n_hoguera"), ("puerta", "camp_n_puerta")]
BG = (52, 50, 56, 255)

def tile(name):
    d = os.path.join(R, name)
    col = Image.open(os.path.join(d, "color.png")).convert("RGBA")
    meta = json.load(open(os.path.join(d, "meta.json")))
    sh = Image.open(os.path.join(d, "shadow.png")).convert("L") if os.path.exists(os.path.join(d, "shadow.png")) else None
    dx, dy = meta.get("shadow_offset_px", [0, 0])
    sw, shh = meta.get("shadow_canvas_px", col.size)
    out = Image.new("RGBA", (sw, shh), BG)
    if sh is not None:
        m = np.array(sh) > 127
        a = np.array(out); a[m, :3] = (30, 28, 34); out = Image.fromarray(a)
    out.alpha_composite(col, (-dx, -dy))
    return out

def main():
    rows = []
    for row in (0, 1):
        rows.append([tile(p[row]) for p in PAIRS if os.path.exists(os.path.join(R, p[row]))])
    pad = 8
    W = max(sum(t.width + pad for t in r) for r in rows) + pad
    H = sum(max(t.height for t in r) + pad for r in rows) + pad
    sheet = Image.new("RGBA", (W, H), BG)
    y = pad
    for r in rows:
        x = pad
        for t in r:
            sheet.alpha_composite(t, (x, y)); x += t.width + pad
        y += max(t.height for t in r) + pad
    sheet = sheet.resize((W * 4, H * 4), Image.NEAREST)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "walkthroughs/campamento-nocturno/assets/props_hoja_contacto.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out); print(out, sheet.size)

if __name__ == "__main__":
    main()
