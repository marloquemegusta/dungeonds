#!/usr/bin/env python3
"""Builds the Corazon Abierto walk and sniper-fire previews from headless ROM captures.

Inputs are the capture folders written by run-scenario.ps1 (walk_NNNN.png for each
sandbox_hero_walk_<dir> run, and charge_/shot_/after/00_staged PNGs for sandbox_sniper_fire).
Captures are 256x384; the hero stands on the lower screen at (40, 96) for the east and sniper
scenes and at (120, 96) or (128, 96) for the others, so the lower-screen y is 192 + 96 = 288.

Outputs (in --out):
  andar_<dir>.gif  walk cycle, 2x NEAREST, 55 ms per frame (dir = east, south, north, west)
  andar.gif        copy of andar_east.gif
  andar_juego.png  4 rows (E, S, N, W) x 8 frames, 40x40 window around the hero at 4x NEAREST
  final_contacto.png  sniper states as 4x NEAREST crops of the hero and the beam origin, one row
  final_fuego_llamas.gif  charge + shot captures, 2x NEAREST, 55 ms per frame

Run:
  python tools/corazon_walk_previews.py --walk-runs <dir with run_sandbox_hero_walk_*> \
      --sniper-run <run_sandbox_sniper_fire dir> --out walkthroughs/corazon-abierto/assets
"""
import argparse
import glob
from pathlib import Path

from PIL import Image, ImageDraw

HERO_Y = 288                      # full-capture y of the hero on the lower screen (192 + 96)
WALK_WIN_X = {"east": (0, 96), "west": (64, 160), "south": (72, 168), "north": (72, 168)}
SHEET_WIN_X = {"east": (30, 70), "south": (100, 140), "north": (100, 140), "west": (112, 152)}
DIRS = ["east", "south", "north", "west"]
WALK_MS = 55
FIRE_MS = 55


def walk_frames(walk_runs, d):
    return sorted(glob.glob(str(Path(walk_runs) / f"run_sandbox_hero_walk_{d}" / "walk_*.png")))


def make_walk_gifs(walk_runs, out):
    gifs = {}
    for d in DIRS:
        x0, x1 = WALK_WIN_X[d]
        frames = [Image.open(p).convert("RGB").crop((x0, HERO_Y - 48, x1, HERO_Y + 48))
                  .resize(((x1 - x0) * 2, 192), Image.NEAREST) for p in walk_frames(walk_runs, d)]
        gifs[d] = frames
        frames[0].save(out / f"andar_{d}.gif", save_all=True, append_images=frames[1:],
                       duration=WALK_MS, loop=0, optimize=True)
    gifs["east"][0].save(out / "andar.gif", save_all=True, append_images=gifs["east"][1:],
                         duration=WALK_MS, loop=0, optimize=True)
    return gifs


def make_walk_sheet(walk_runs, out):
    cell, label_h = 160, 18
    sheet = Image.new("RGB", (8 * (cell + 1), 4 * (cell + label_h)), (20, 20, 28))
    draw = ImageDraw.Draw(sheet)
    for r, d in enumerate(DIRS):
        x0, x1 = SHEET_WIN_X[d]
        y = r * (cell + label_h)
        draw.text((4, y + 3), f"{d.upper()}  frames 0-7, 4x NEAREST, 55 ms", fill=(230, 230, 230))
        for c, p in enumerate(walk_frames(walk_runs, d)[:8]):
            im = Image.open(p).convert("RGB").crop((x0, HERO_Y - 26, x1, HERO_Y + 14)).resize((cell, cell), Image.NEAREST)
            sheet.paste(im, (c * (cell + 1), y + label_h))
    sheet.save(out / "andar_juego.png")


def make_fire(sniper_run, out):
    run = Path(sniper_run)
    states = [("0 % (00_staged)", run / "00_staged.png"), ("50 % (charge_0011)", run / "charge_0011.png"),
              ("listo (charge_0026)", run / "charge_0026.png"), ("disparo (shot_0003)", run / "shot_0003.png"),
              ("apagado (after)", run / "after.png")]
    # hero crop: 96 x 64 around the hero, which also shows where the beam leaves it, at 4x NEAREST
    x0, x1, y0, y1 = 8, 104, HERO_Y - 32, HERO_Y + 32
    cw, ch, label_h = (x1 - x0) * 4, (y1 - y0) * 4, 18
    sheet = Image.new("RGB", (len(states) * (cw + 8), ch + label_h), (20, 20, 28))
    draw = ImageDraw.Draw(sheet)
    for i, (lab, p) in enumerate(states):
        x = i * (cw + 8)
        draw.text((x + 4, 3), lab, fill=(230, 230, 230))
        im = Image.open(p).convert("RGB").crop((x0, y0, x1, y1)).resize((cw, ch), Image.NEAREST)
        sheet.paste(im, (x, label_h))
    sheet.save(out / "final_contacto.png")

    seq = sorted(glob.glob(str(run / "charge_*.png"))) + sorted(glob.glob(str(run / "shot_*.png")))
    frames = [Image.open(p).convert("RGB").crop((0, 192, 256, 384)).resize((512, 384), Image.NEAREST) for p in seq]
    frames[0].save(out / "final_fuego_llamas.gif", save_all=True, append_images=frames[1:],
                   duration=FIRE_MS, loop=0, optimize=True)
    return len(seq)


AURA_LOOKS = ["L", "G", "E", "H"]
AURA_MS = 55
AURA_GIF_WIN = (8, 104, HERO_Y - 32, HERO_Y + 32)     # 96 x 64 around the hero; GIF at 2x NEAREST
AURA_CELL_WIN = (16, 64, HERO_Y - 36, HERO_Y + 12)    # 48 x 48 around the hero; sheet cells at 4x NEAREST
# Contact sheet columns: capture names of the charge (every frame from the touch) and of the shot. The aim takes
# 24 frames (aim_min_frames), so 25 / 50 / 75 % are charge frames 6 / 12 / 18 and READY is around 26.
AURA_COLS = [("25 %", "charge_0006"), ("50 %", "charge_0012"), ("75 %", "charge_0018"),
             ("listo", "charge_0026"), ("disparo", "shot_0003")]


def make_aura2(aura_root, out):
    """Second round of sniper auras (DESIGN.md, segunda ronda de auras): one GIF per look and one contact sheet.
    aura_root holds run_sandbox_sniper_fire_aura_<L|G|E|H>/ (the captures of run-scenario.ps1)."""
    runs = {look: Path(aura_root) / f"run_sandbox_sniper_fire_aura_{look}" for look in AURA_LOOKS}
    x0, x1, y0, y1 = AURA_GIF_WIN
    for look in AURA_LOOKS:
        seq = sorted(glob.glob(str(runs[look] / "charge_*.png"))) + sorted(glob.glob(str(runs[look] / "shot_*.png")))
        frames = [Image.open(p).convert("RGB").crop((x0, y0, x1, y1))
                  .resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST) for p in seq]
        frames[0].save(out / f"aura2_{look}.gif", save_all=True, append_images=frames[1:],
                       duration=AURA_MS, loop=0, optimize=True)
    x0, x1, y0, y1 = AURA_CELL_WIN
    cw, ch, label_h, gap = (x1 - x0) * 4, (y1 - y0) * 4, 18, 6
    sheet = Image.new("RGB", (len(AURA_COLS) * (cw + gap), len(AURA_LOOKS) * (ch + label_h + gap)), (20, 20, 28))
    draw = ImageDraw.Draw(sheet)
    for r, look in enumerate(AURA_LOOKS):
        y = r * (ch + label_h + gap)
        for c, (lab, name) in enumerate(AURA_COLS):
            x = c * (cw + gap)
            draw.text((x + 4, y + 3), f"{look}  {lab}", fill=(230, 230, 230))
            im = Image.open(runs[look] / f"{name}.png").convert("RGB").crop((x0, y0, x1, y1))
            sheet.paste(im.resize((cw, ch), Image.NEAREST), (x, y + label_h))
    sheet.save(out / "contacto_aura2.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--walk-runs", required=True, help="folder holding run_sandbox_hero_walk_<dir>/")
    ap.add_argument("--sniper-run", required=True, help="run_sandbox_sniper_fire folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--aura-root", help="folder holding run_sandbox_sniper_fire_aura_<L|G|E|H>/ (second round)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    make_walk_gifs(a.walk_runs, out)
    make_walk_sheet(a.walk_runs, out)
    n = make_fire(a.sniper_run, out)
    print("walk frames", {d: len(walk_frames(a.walk_runs, d)) for d in DIRS}, "fire frames", n)
    if a.aura_root:
        make_aura2(a.aura_root, out)
        print("aura2 written to", out)


if __name__ == "__main__":
    main()
