#!/usr/bin/env python3
"""GIF of scenarios/cobertura_baja_agachado.json (cathedral-sandbox ROM) for walkthroughs/coberturas-bajas.

  python tools/cobertura_gif.py <run_dir>     run_dir = output folder of run-scenario.ps1

Joins the captured sequences s1_* .. s8_* in order (a capture every 3 game frames = 50 ms, so the GIF plays at real
speed), crops the bottom screen around the bench, scales 4x NEAREST and writes
walkthroughs/coberturas-bajas/assets/cobertura_agachado.gif plus a contact strip of the key moments.
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "walkthroughs" / "coberturas-bajas" / "assets"
CROP = (56, 52, 200, 104)          # x, y, w, h on the bottom screen (captures are 256x384, bottom starts at y = 192)
SCALE = 4
FRAME_MS = 50
LABELS = {
    "s1_agacha": "se pega al banco y se agacha",
    "s2_andar": "anda agachado, mas lento",
    "s3_quieto": "se queda agachado",
    "s4_mira": "el Ojo apunta",
    "s5_haz": "el haz pasa por encima del banco: no le da",
    "s6_levanta": "toca el stylus: se levanta a disparar",
    "s7_haz2": "de pie, el mismo haz le da",
    "s8_suelta": "suelta el stylus",
}


def frames(run_dir):
    items = []
    for key in LABELS:
        files = sorted(p for p in run_dir.glob(f"{key}_*.png") if re.search(r"_\d{4}\.png$", p.name))
        items += [(key, p) for p in files]
    return items


def main():
    run_dir = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    x, y, w, h = CROP
    try:
        font = ImageFont.load_default(size=16)
    except TypeError:
        font = ImageFont.load_default()
    out, firsts = [], {}
    fl = frames(run_dir)
    by = {}
    for i, (key, path) in enumerate(fl):
        by.setdefault(key, []).append(len(out))
        out_idx = len(out)
        out.append(None)
    out = []
    for key, path in fl:
        im = Image.open(path).convert("RGB").crop((x, 192 + y, x + w, 192 + y + h))
        im = im.resize((w * SCALE, h * SCALE), Image.NEAREST)
        bar = Image.new("RGB", (im.width, 26), (20, 18, 16))
        ImageDraw.Draw(bar).text((8, 4), LABELS[key], fill=(232, 220, 190), font=font)
        frame = Image.new("RGB", (im.width, im.height + 26))
        frame.paste(im, (0, 0)); frame.paste(bar, (0, im.height))
        out.append(frame)
    LAST = {"s1_agacha", "s3_quieto", "s6_levanta"}      # moments that are only true once the sequence has settled
    for key, idx in by.items():
        firsts[key] = out[idx[-1] if key in LAST else idx[len(idx) // 2]]
    gif = OUT / "cobertura_agachado.gif"
    out[0].save(gif, save_all=True, append_images=out[1:], duration=FRAME_MS, loop=0, optimize=False)
    print("frames", len(out), "->", gif, "fps", 1000 // FRAME_MS)
    keys = list(LABELS)
    sheet = Image.new("RGB", (out[0].width * 2, out[0].height * 4))
    for i, k in enumerate(keys):
        sheet.paste(firsts[k], ((i % 2) * out[0].width, (i // 2) * out[0].height))
    sheet.save(OUT / "cobertura_agachado_momentos.png")


main()
