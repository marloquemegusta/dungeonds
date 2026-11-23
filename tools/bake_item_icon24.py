"""Hornea el icono de 24x24 RGB15 de un objeto del inventario ARPG en include/inv_item_art.h.

Fuente: build/item_spin_tmp/<slug>/icon24_src.png, que sale de
  blender --background --python tools/render_item_spin.py -- --only <slug> --icon24
Mismo tratamiento C2 que los giros de 56 px (LANCZOS + nitidez + contraste).
Escribe (o sustituye) el array s_<slug>_24. Despues: python tools/bake_inv_floor_art.py

Uso: python tools/bake_item_icon24.py <slug>
"""
import os
import re
import sys

from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDR = os.path.join(ROOT, "include", "inv_item_art.h")
S = 24


def bake(slug):
    src = os.path.join(ROOT, "build", "item_spin_tmp", slug, "icon24_src.png")
    im = Image.open(src).convert("RGBA").resize((S, S), Image.Resampling.LANCZOS)
    r, g, b, a = im.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.8, percent=90, threshold=3))
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.08)
    px = Image.merge("RGBA", (*rgb.split(), a)).load()
    vals = []
    for y in range(S):
        for x in range(S):
            r, g, b, al = px[x, y]
            if al < 96:
                vals.append(0)
                continue
            r5, g5, b5 = (min(31, (v + 4) >> 3) for v in (r, g, b))
            vals.append(0x8000 | (b5 << 10) | (g5 << 5) | r5)
    name = "s_%s_24" % slug
    body = ["// %s: 24x24 RGB15 (tools/bake_item_icon24.py)" % name,
            "static const uint16_t %s[24 * 24] = {" % name]
    for i in range(0, S * S, S):
        body.append("    " + ", ".join("0x%04X" % v for v in vals[i:i + S]) + ",")
    body.append("};")
    txt = open(HDR, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in txt else "\n"   # el .h esta guardado con CRLF
    block = nl.join(body) + nl
    pat = re.compile(r"(// %s:[^\r\n]*\r?\n)?static const uint16_t %s\[24 \* 24\] = \{.*?\};\r?\n" % (name, name), re.S)
    if pat.search(txt):
        txt = pat.sub(lambda m: block, txt, count=1)
    else:
        i = txt.rindex("#endif")
        txt = txt[:i] + block + nl + txt[i:]
    open(HDR, "w", encoding="utf-8", newline="").write(txt)
    print("wrote", name)


if __name__ == "__main__":
    bake(sys.argv[1])
