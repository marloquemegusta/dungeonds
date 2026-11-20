"""Review sheets for the hero's punches taken from the rendered sprites.

  python tools/characters/punch_review.py

Outputs:
  walkthroughs/arpg-predemo/assets/combo_punetazos.gif        punch_a -> punch_b -> gancho, S/SE/E/NE, 4x NEAREST
  walkthroughs/arpg-predemo/assets/combo_punetazos_frames.png all frames of the three clips, SE, 4x NEAREST

Reads only assets/sprites/characters/<clip>/frames/<dir>/<n>.png; the cells are aligned by the clip's
ground anchor (settings.json) so the feet do not jump between clips. No crop: if a frame touches the cell
edge the script says so, which is the lab's CROPPED case and is fixed by raising that clip's resolution.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SPR = ROOT / "assets/sprites/characters"
OUT = ROOT / "walkthroughs/arpg-predemo/assets"

CLIPS = ["corazon_punch_a", "corazon_punch_b", "corazon_gancho"]
GIF_DIRS = ["S", "SE", "E", "NE"]
SHEET_DIR = "SE"
SCALE = 4
FRAME_MS = 60            # 16.7 fps: above the 15 fps floor of the review rule
GAP = 6
PAD = 8
BG = (44, 44, 44)
TEXT = (232, 232, 232)
FONT_PATH = "C:/Windows/Fonts/arial.ttf"


def font(px):
    try:
        return ImageFont.truetype(FONT_PATH, px)
    except OSError:
        return ImageFont.load_default()


def load_clip(clip):
    """(settings, {direction: [frames in order]}) and the ground anchor to align clips."""
    base = SPR / clip
    settings = json.loads((base / "settings.json").read_text(encoding="utf-8"))
    size = int(settings["frameSize"].split("x")[0])
    anchor = settings["anchor"][1]
    frames = {}
    for d in settings["directions"]:
        sub = next(p for p in (base / "frames").iterdir() if p.name.endswith("_" + d))
        idx = sorted(int(p.stem) for p in sub.glob("*.png"))
        ims = [Image.open(sub / f"{i}.png").convert("RGBA") for i in idx]
        for im in ims:
            if im.size != (size, size):
                raise SystemExit(f"{clip} {d}: cell {im.size} != {size}")
            a = im.getchannel("A")
            box = a.getbbox()
            if box and (box[0] <= 0 or box[1] <= 0 or box[2] >= size or box[3] >= size):
                raise SystemExit(f"CROPPED: {clip} {d} touches the cell edge {box}; raise its resolution")
        frames[d] = ims
    return settings, size, anchor, frames


def union_box(data, ground, size, margin=2):
    """Union of the opaque boxes of every frame of every clip, in the shared aligned cell."""
    box = [size, size, 0, 0]
    for _, _, anchor, frames in data.values():
        dy = ground - anchor
        for ims in frames.values():
            for im in ims:
                b = im.getchannel("A").getbbox()
                if not b:
                    continue
                box = [min(box[0], b[0]), min(box[1], b[1] + dy),
                       max(box[2], b[2]), max(box[3], b[3] + dy)]
    return (max(0, box[0] - margin), max(0, box[1] - margin),
            min(size, box[2] + margin), min(size, box[3] + margin))


def cell(entry, direction, n, ground, win):
    """One frame, shifted onto the shared foot line and cropped to the window."""
    _, _, anchor, frames = entry
    ims = frames[direction]
    canvas = Image.new("RGBA", ims[0].size, BG)
    canvas.alpha_composite(ims[n % len(ims)], (0, ground - anchor))
    return canvas.crop(win)


def build_gif():
    data = {c: load_clip(c) for c in CLIPS}
    size = int(data[CLIPS[0]][0]["frameSize"].split("x")[0])
    ground = max(a for (_, _, a, _) in data.values())          # common foot line
    win = union_box(data, ground, size)
    cell_w = (win[2] - win[0]) + 2 * PAD
    cell_h = win[3] - win[1]
    sprite_w = cell_w * len(GIF_DIRS)
    label_px = 22
    f = font(label_px)

    frames = []
    for clip in CLIPS:
        for n in range(len(data[clip][3][GIF_DIRS[0]])):
            low = Image.new("RGBA", (sprite_w, cell_h), BG)
            for col, d in enumerate(GIF_DIRS):
                low.alpha_composite(cell(data[clip], d, n, ground, win), (col * cell_w + PAD, 0))
            hi = low.resize((sprite_w * SCALE, cell_h * SCALE), Image.NEAREST)
            card = Image.new("RGB", (sprite_w * SCALE, (cell_h + label_px) * SCALE), BG)
            card.paste(hi, (0, label_px * SCALE))
            dr = ImageDraw.Draw(card)
            for col, d in enumerate(GIF_DIRS):
                w = dr.textlength(d, font=f)
                dr.text((col * cell_w * SCALE + (cell_w * SCALE - w) / 2, 2), d, font=f, fill=TEXT)
            frames.append(card.convert("P", palette=Image.ADAPTIVE, colors=256))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "combo_punetazos.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=False, disposal=1)
    print(f"GIF  {path}  {len(frames)} frames @ {FRAME_MS} ms, {cell_w - 2 * PAD}x{cell_h} px per sprite")


def build_sheet():
    data = {c: load_clip(c) for c in CLIPS}
    size = int(data[CLIPS[0]][0]["frameSize"].split("x")[0])
    ground = max(a for (_, _, a, _) in data.values())
    win = union_box(data, ground, size)
    cell_w = (win[2] - win[0]) + 2 * PAD
    cell_h = win[3] - win[1]
    f = font(22)
    rows = []
    for clip in CLIPS:
        n = len(data[clip][3][SHEET_DIR])
        low = Image.new("RGBA", (cell_w * n, cell_h), BG)
        for i in range(n):
            low.alpha_composite(cell(data[clip], SHEET_DIR, i, ground, win), (i * cell_w + PAD, 0))
        hi = low.resize((low.width * SCALE, low.height * SCALE), Image.NEAREST)
        row = Image.new("RGB", (hi.width, hi.height + 30), BG)
        row.paste(hi, (0, 30))
        ImageDraw.Draw(row).text((4, 4), f"{clip} {SHEET_DIR}  ({n} frames)", font=f, fill=TEXT)
        rows.append(row)
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), BG)
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "combo_punetazos_frames.png"
    sheet.save(path)
    print(f"PNG  {path}  {sheet.size[0]}x{sheet.size[1]}")


if __name__ == "__main__":
    build_gif()
    build_sheet()
