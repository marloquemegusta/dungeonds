#!/usr/bin/env python3
"""A | B | C comparison GIF and contact sheet of the Ojo del Tribunal's sentence (scenarios/abc_ojo_sentencia.json),
plus the single-column "antes" GIF of the old look.

  python tools/abc_ojo_gif.py [--run] [--antes DIR]

--run first runs the scenario on dungeonds-cathedral-sandbox.nds (build it with build-project.ps1 -Variant
cathedral-sandbox). Output in walkthroughs/ojo-sentencia/assets/: abc2_ojo_c.gif, abc2_ojo_c_hoja.png
and, with --antes DIR (a folder with the v0_*.png frames of the old build), antes_ojo.gif. 4x NEAREST, 60 ms per frame.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abc_gif as G   # noqa: E402

ROOT = G.ROOT
OUT = ROOT / "walkthroughs" / "ojo-sentencia" / "assets"
CROP = (14, 34, 144, 104)           # x, y, w, h on the bottom screen: the Ojo and the hero whole, flames and scar
SCALE = 4
FRAME_MS = 60
TITLES = ("C1  fiel", "C2  ojos que miran", "C3  mirada encendida")
# Key instants of the contact sheet: (frame-sequence prefix, index, caption)
SHEET = [("0busca", 4, "busca"), ("1trackA", 1, "farol"), ("1trackA", 4, "punta avanza"), ("1trackB", 2, "sigue"),
         ("2lock", 4, "carga"), ("2lock", 8, "aviso"), ("3sentencia", 1, "golpe"), ("3sentencia", 4, "arde"),
         ("3sentencia", 12, "disipa"), ("4cicatriz", 6, "cicatriz")]


def frames_of(run_dir, vi):
    files = [p for p in run_dir.glob(f"v{vi}_*_*.png") if re.search(r"_\d{4}\.png$", p.name)]
    files.sort(key=lambda p: (re.sub(r"_\d{4}\.png$", "", p.name), p.name))
    return files


def pick(run_dir, vi, prefix, idx):
    return run_dir / f"v{vi}_{prefix}_{idx:04d}.png"


def crop(path, scale):
    x, y, w, h = CROP
    im = Image.open(path).convert("RGB")
    return im.crop((x, G.BOTTOM_Y + y, x + w, G.BOTTOM_Y + y + h)).resize((w * scale, h * scale), Image.NEAREST)


def save_gif(frames, path):
    n = len(frames)
    total_w, total_h = frames[0].size
    step = max(1, n // 10)
    sample = Image.new("RGB", (total_w, total_h * len(frames[::step])))
    for k, f in enumerate(frames[::step]):
        sample.paste(f, (0, k * total_h))
    pal = sample.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    plt = pal.getpalette()
    bg = q[0].getpixel((0, 0))
    def dist(i):
        return sum((plt[3 * i + k] - plt[3 * bg + k]) ** 2 for k in range(3))
    alt = min((i for i in range(128) if i != bg), key=dist)
    for i, f in enumerate(q):          # keep identical neighbouring frames apart (PIL would merge them and sum the duration)
        f.putpixel((total_w - 1, 0), alt if i & 1 else bg)
    OUT.mkdir(parents=True, exist_ok=True)
    q[0].save(path, save_all=True, append_images=q[1:], duration=FRAME_MS, loop=0, optimize=True, disposal=1)
    print(f"{path}  {n} frames  {path.stat().st_size / 1024:.0f} KB")


def abc_gif(run_dir):
    cols = [frames_of(run_dir, vi) for vi in (0, 1, 2)]
    n = len(cols[0])
    if n == 0 or len({len(c) for c in cols}) != 1:
        sys.exit(f"frame counts differ or empty: {[len(c) for c in cols]}")
    cw, ch = CROP[2] * SCALE, CROP[3] * SCALE
    gap = 6
    labels = [G.label(t, cw) for t in TITLES]
    frames = []
    for i in range(n):
        canvas = Image.new("RGB", (3 * cw + 2 * gap, ch + G.LABEL_H), (20, 18, 16))
        for c in range(3):
            canvas.paste(labels[c], (c * (cw + gap), 0))
            canvas.paste(crop(cols[c][i], SCALE), (c * (cw + gap), G.LABEL_H))
        frames.append(canvas)
    save_gif(frames, OUT / "abc2_ojo_c.gif")


def antes_gif(src):
    files = frames_of(Path(src), 0)
    cw, ch = CROP[2] * SCALE, CROP[3] * SCALE
    lab = G.label("ANTES  banda verde y haz", cw)
    frames = []
    for p in files:
        canvas = Image.new("RGB", (cw, ch + G.LABEL_H), (20, 18, 16))
        canvas.paste(lab, (0, 0))
        canvas.paste(crop(p, SCALE), (0, G.LABEL_H))
        frames.append(canvas)
    save_gif(frames, OUT / "antes_ojo.gif")


def sheet(run_dir, scale=2):
    cw, ch = CROP[2] * scale, CROP[3] * scale
    cap_h, side = 18, 26
    ncol = len(SHEET)
    W = side + ncol * cw
    H = 3 * (ch + cap_h)
    img = Image.new("RGB", (W, H), (20, 18, 16))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:
        font = ImageFont.load_default()
    for vi in range(3):
        y0 = vi * (ch + cap_h)
        d.text((8, y0 + ch // 2 - 8), "ABC"[vi], fill=(232, 220, 190), font=font)
        for k, (prefix, idx, cap) in enumerate(SHEET):
            x0 = side + k * cw
            img.paste(crop(pick(run_dir, vi, prefix, idx), scale), (x0, y0 + cap_h))
            if vi == 0:
                d.text((x0 + 4, y0 + 2), cap, fill=(232, 220, 190), font=font)
    path = OUT / "abc2_ojo_c_hoja.png"
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"{path}  {img.size}")


def sheet_c1(run_dir, scale=2):
    """One row (the C1 look, vi 0) with the same instants: c1_final_hoja.png."""
    cw, ch = CROP[2] * scale, CROP[3] * scale
    cap_h = 18
    ncol = len(SHEET)
    img = Image.new("RGB", (ncol * cw, ch + cap_h), (20, 18, 16))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:
        font = ImageFont.load_default()
    for k, (prefix, idx, cap) in enumerate(SHEET):
        img.paste(crop(pick(run_dir, 0, prefix, idx), scale), (k * cw, cap_h))
        d.text((k * cw + 4, 2), cap, fill=(232, 220, 190), font=font)
    path = OUT / "c1_final_hoja.png"
    img.save(path)
    print(f"{path}  {img.size}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--c1", action="store_true", help="only the C1 contact sheet (c1_final_hoja.png)")
    ap.add_argument("--antes", help="folder with the old build's v0_*.png frames")
    ap.add_argument("--runs-dir", default=str(ROOT / ".ds-game-dev" / "abc_runs"))
    a = ap.parse_args()
    runs = Path(a.runs_dir)
    if a.run:
        G.run_scenario("ojo_sentencia", runs)
    run_dir = runs / "ojo_sentencia"
    if a.c1:
        sheet_c1(run_dir)
    elif a.antes:
        antes_gif(a.antes)
    else:
        abc_gif(run_dir)
        sheet(run_dir)
