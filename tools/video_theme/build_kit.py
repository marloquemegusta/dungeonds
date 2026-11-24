#!/usr/bin/env python3
"""Genera el kit del tema visual de vídeo a partir del arte de inventario de la ROM (rama proto/arpg).

Lee include/inv_art.h (git show proto/arpg:include/inv_art.h, o --header <ruta>) y escribe en kit/:
  stone_red_64.png, bar_gold_16x5.png, corner_gold_14.png, glyphs (en theme.json) y theme.json.
theme.json lo leen theme.py (Python) y devlog/src/theme (Remotion). Con --public <carpeta> lo copia allí.
Tipografía: Palatino 1 bit (pala.ttf / palai.ttf de C:\\Windows\\Fonts) rasterizada a 13 px nativos.
"""
import argparse
import json
import os
import re
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "kit")
FD = "C:/Windows/Fonts/"
CHARS = [chr(c) for c in range(32, 127)] + list("áéíóúüñÁÉÍÓÚÜÑ¡¿«»—–·…“”‘’°ºª€")


def read_header(path):
    if path:
        return open(path, encoding="utf-8").read()
    return subprocess.check_output(["git", "show", "proto/arpg:include/inv_art.h"], cwd=HERE).decode("utf-8")


def arr(txt, name):
    m = re.search(name + r"\[\d*\]\s*=\s*\{(.*?)\};", txt, re.S)
    return [int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]+", m.group(1))]


def rgba(vals, w, h):
    a = np.zeros((h, w, 4), dtype="uint8")
    for i, v in enumerate(vals):
        r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
        a[i // w, i % w] = (r * 8 + r // 4, g * 8 + g // 4, b * 8 + b // 4, 255 if (v & 0x8000) else 0)
    return a


def tint_stone(a):
    """Piedra gris pizarra de la ROM -> rojo óxido en 6 tonos."""
    lum = a[..., :3].astype(float).mean(axis=2)
    lo, hi = np.percentile(lum, 2), np.percentile(lum, 98)
    n = np.round(np.clip((lum - lo) / (hi - lo), 0, 1) * 5) / 5
    c0, c1 = np.array([40, 14, 12]), np.array([104, 42, 32])
    out = np.zeros(a.shape, dtype="uint8")
    out[..., :3] = (c0 + (c1 - c0) * n[..., None]).astype("uint8")
    out[..., 3] = 255
    return out


def hexs(a, alpha):
    h, w = a.shape[:2]
    return "".join(("%02x%02x%02x%02x" % tuple(a[y, x]) if alpha else "%02x%02x%02x" % tuple(a[y, x][:3]))
                   for y in range(h) for x in range(w))


def glyphs(font):
    asc = font.getmetrics()[0]
    out = {}
    for ch in CHARS:
        adv = int(round(font.getlength(ch, mode="1")))
        im = Image.new("L", (48, 48), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((8, 24), ch, font=font, fill=255, anchor="ls")
        bb = im.getbbox()
        if not bb:
            out[ch] = {"a": adv, "x": 0, "y": 0, "w": 0, "h": 0, "d": []}
            continue
        c = im.crop(bb)
        rows = ["".join("1" if c.getpixel((x, y)) else "0" for x in range(c.width)) for y in range(c.height)]
        out[ch] = {"a": adv, "x": bb[0] - 8, "y": bb[1] - 24, "w": c.width, "h": c.height, "d": rows}
    return out, asc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--header")
    ap.add_argument("--public", action="append", default=[], help="carpeta destino de la copia de theme.json (devlog/public/theme)")
    a = ap.parse_args()
    txt = read_header(a.header)
    os.makedirs(KIT, exist_ok=True)
    stone = tint_stone(rgba(arr(txt, "s_stone_tex_64"), 64, 64))
    bar = rgba(arr(txt, "s_gold_bar_h_16x5"), 16, 5)
    corner = rgba(arr(txt, "s_gold_corner_14"), 14, 14)
    Image.fromarray(stone, "RGBA").save(os.path.join(KIT, "stone_red_64.png"))
    Image.fromarray(bar, "RGBA").save(os.path.join(KIT, "bar_gold_16x5.png"))
    Image.fromarray(corner, "RGBA").save(os.path.join(KIT, "corner_gold_14.png"))
    fr = ImageFont.truetype(FD + "pala.ttf", 13)
    fi = ImageFont.truetype(FD + "palai.ttf", 13)
    gr, asc = glyphs(fr)
    gi, _ = glyphs(fi)
    theme = {
        "scale": 5,
        "fontSize": 13,
        "ascent": asc,
        "line": 16,
        "pad": 9,
        "bar": 5,
        "shadow": 1,
        "min_box_h": 140,
        "inner_line": [22, 6, 6],
        "colors": {"ivory": [232, 200, 152], "gold": [216, 160, 88], "ash": [150, 134, 122], "dark": [16, 6, 8]},
        "stone": hexs(stone, False),
        "bar_px": hexs(bar, True),
        "corner": hexs(corner, True),
        "font": {"regular": gr, "italic": gi},
        "source": "include/inv_art.h (proto/arpg): s_stone_tex_64 teñida, s_gold_bar_h_16x5, s_gold_corner_14; Palatino 13 px 1 bit",
    }
    with open(os.path.join(KIT, "theme.json"), "w", encoding="utf-8") as f:
        json.dump(theme, f, ensure_ascii=False, separators=(",", ":"))
    for p in a.public:
        os.makedirs(p, exist_ok=True)
        shutil.copy(os.path.join(KIT, "theme.json"), os.path.join(p, "theme.json"))
        for n in ("stone_red_64.png", "bar_gold_16x5.png", "corner_gold_14.png"):
            shutil.copy(os.path.join(KIT, n), os.path.join(p, n))
    print("kit ok, ascent", asc)


if __name__ == "__main__":
    main()
