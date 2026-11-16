#!/usr/bin/env python3
"""Builds the A | B | C comparison GIF of one upgrade-system visual from the frames of scenarios/abc_<element>.json.

  python tools/abc_gif.py <element> [--run] [--runs-dir DIR]

--run first runs the scenario on dungeonds-cathedral-sandbox.nds (build it with build-project.ps1 -Variant
cathedral-sandbox). Each variant's captured sequence (v0_*, v1_*, v2_*) is cropped to the same window of the bottom
screen, scaled 4x NEAREST, placed side by side under a small label and written to
walkthroughs/mejoras-v04/assets/gif/abc_<element>.gif (60 ms per frame, looping).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "walkthroughs" / "mejoras-v04" / "assets" / "gif"
SKILL = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts\run-scenario.ps1")
ROM = ROOT / "dungeonds-cathedral-sandbox.nds"
SCALE = 4
FRAME_MS = 60
LABEL_H = 22
BOTTOM_Y = 192                       # captures are 256x384; the bottom screen starts at y = 192

# Crop window on the bottom screen (x, y, w, h); the hero stands at (128, 133) feet in every scene.
CROPS = {
    "burn": (96, 62, 128, 96),
    "votiva": (100, 62, 128, 96),
    "flagelado": (64, 62, 128, 96),
    "martirio": (100, 62, 128, 96),
    "autofe": (108, 62, 128, 96),
    "llaga": (0, 0, 256, 192),           # whole bottom screen: the vignette (C) lives on its border
    "llaga_hero": (88, 66, 80, 76),      # same scene, zoomed on the hero (A ring, B tint and drops)
    "viatico": (100, 60, 112, 84),
}
SCENARIO = {"llaga_hero": "llaga"}      # elements that reuse another element's scenario / frames
SCALES = {"llaga": 2}
TITLES = {
    "burn": ("A  brasas y lengua", "B  anillo de llamas"),
    "votiva": ("A  llama en la linea", "B  chispas dispersas", "C  manchas solares"),
    "flagelado": ("A", "B", "C"),
    "martirio": ("A  anillo", "B  cruz de lenguas", "C  columna"),
    "autofe": ("A  chispas al impacto", "C  consume el anillo B"),
    "llaga": ("B  gotea y asciende", "C  vineta roja"),
    "llaga_hero": ("B  gotea y asciende", "C  vineta roja"),
    "viatico": ("A  hilo de sangre", "C  alma palida"),
}
# Variant ids shown per element (left to right); default A | B | C.
VARIANTS = {"autofe": (0, 2), "burn": (0, 1), "llaga": (1, 2), "llaga_hero": (1, 2), "viatico": (0, 2)}


def run_scenario(el, runs):
    out = runs / el
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SKILL),
           "-ProjectPath", str(ROOT), "-ScenarioPath", str(ROOT / "scenarios" / f"abc_{SCENARIO.get(el, el)}.json"),
           "-RomPath", str(ROM), "-OutputPath", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-400:])
    if "PASS" not in r.stdout:
        sys.exit("scenario did not pass:\n" + r.stdout[-1500:] + r.stderr[-800:])


def variant_frames(run_dir, vi):
    files = [p for p in run_dir.glob(f"v{vi}_*_*.png") if re.search(r"_\d{4}\.png$", p.name)]
    files.sort(key=lambda p: (re.sub(r"_\d{4}\.png$", "", p.name), p.name))
    return files


def label(text, width):
    img = Image.new("RGB", (width, LABEL_H), (20, 18, 16))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    d.text((8, 3), text, fill=(232, 220, 190), font=font)
    return img


def compose(el, run_dir):
    x, y, w, h = CROPS[el]
    vis = VARIANTS.get(el, (0, 1, 2))
    cols = [variant_frames(run_dir, vi) for vi in vis]
    n = min(len(c) for c in cols)
    if n == 0 or len({len(c) for c in cols}) != 1:
        sys.exit(f"frame counts differ or empty: {[len(c) for c in cols]}")
    scale = SCALES.get(el, SCALE)
    cw, ch = w * scale, h * scale
    gap = 6
    nc = len(vis)
    total_w = nc * cw + (nc - 1) * gap
    labels = [label(t, cw) for t in TITLES[el]]
    frames = []
    for i in range(n):
        canvas = Image.new("RGB", (total_w, ch + LABEL_H), (20, 18, 16))
        for c in range(nc):
            im = Image.open(cols[c][i]).convert("RGB")
            crop = im.crop((x, BOTTOM_Y + y, x + w, BOTTOM_Y + y + h)).resize((cw, ch), Image.NEAREST)
            ox = c * (cw + gap)
            canvas.paste(labels[c], (ox, 0))
            canvas.paste(crop, (ox, LABEL_H))
        frames.append(canvas)
    # One global palette from a sample of the frames keeps the colours stable between frames and the file small.
    step = max(1, n // 8)
    sample = Image.new("RGB", (total_w, (ch + LABEL_H) * len(frames[::step])))
    for k, f in enumerate(frames[::step]):
        sample.paste(f, (0, k * (ch + LABEL_H)))
    pal = sample.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    # PIL merges identical neighbouring frames (summing their duration, which would break the 60 ms rule): a corner
    # pixel of the label bar alternates between two near-identical palette entries so every frame is kept.
    plt = pal.getpalette()
    bg = q[0].getpixel((0, 0))
    def dist(i):
        return sum((plt[3 * i + k] - plt[3 * bg + k]) ** 2 for k in range(3))
    alt = min((i for i in range(96) if i != bg), key=dist)
    for i, f in enumerate(q):
        f.putpixel((total_w - 1, 0), alt if i & 1 else bg)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"abc_{el}.gif"
    n = len(frames)
    q[0].save(path, save_all=True, append_images=q[1:], duration=FRAME_MS, loop=0, optimize=True, disposal=1)
    print(f"{path}  {n} frames  {path.stat().st_size / 1024:.0f} KB")
    return path, frames


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("element", choices=sorted(CROPS))
    ap.add_argument("--run", action="store_true", help="run the scenario first")
    ap.add_argument("--runs-dir", default=str(ROOT / ".ds-game-dev" / "abc_runs"))
    a = ap.parse_args()
    runs = Path(a.runs_dir)
    src = SCENARIO.get(a.element, a.element)
    if a.run:
        run_scenario(src, runs)
    compose(a.element, runs / src)
