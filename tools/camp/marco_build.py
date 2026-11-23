#!/usr/bin/env python3
"""Builds the camp wall FRAME (north wall + both side walls) from the 3-piece kit and writes the sprites.

Kit (assets/environment/camp/muros_src/): panel_liso.jpg, panel_porton.jpg (same footprint, base and cornice),
contrafuerte.jpg. All three are straight-on, flat-lit images used directly as textures (no generative 3D).

Projection (one for the whole frame, so every joint is built the same way):
  * the game camera is orthographic, elevation 30 deg: a wall running across the screen and facing the camera
    shows its front face with the height scaled by cos(30) = 0.866, plus its top face (thickness * sin 30);
  * the side walls run down the nave: their inner face is seen foreshortened 2:1 along the nave (sin 30 = 0.5)
    and across its height, as a vertical band of SIDE_W px, top of the wall on the outside edge, base on the
    inside edge (what a camera in the middle of the room sees);
  * a flat orthographic projection of textured boxes is exactly an affine map, so the frame is composed by
    placing faces (north to south, painter's order) in ONE canvas instead of going through a renderer: the
    result is the same as a Blender ortho render, without the matte/resampling of a second pass.

Night grading is done on the finished frame: cold dark moon for everything and a warm bath by distance to the
bonfire (same 2:1 ellipse falloff as `light_map` in bake_camp_arena.py). The frame is not lit by anything else.

Outputs: nitrofiles/camp/marco_norte.bin (256 x NORTH_H), marco_izq.bin / marco_der.bin (SIDE_W x SIDE_H),
all RGB15 with BIT(15), 0 = transparent; include/camp_marco.h; assets/environment/camp/marco_work/ (not versioned).

Run: python tools/camp/marco_build.py
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets/environment/camp/muros_src"
WORK = ROOT / "assets/environment/camp/marco_work"
WORK.mkdir(parents=True, exist_ok=True)
NITRO = ROOT / "nitrofiles/camp"

W, H = 256, 384
BG = np.array([194.0, 195.0, 190.0])
K = 0.866                       # cos 30
FIRE_X, FIRE_Y = 128, 300

# --- scale ------------------------------------------------------------------------------------------------
PANEL_X0 = 24                   # panels between the two corner pillars: 208 px = 3 panels
PANEL_W = [69, 70, 69]          # centre panel (the gate) centred on x = 128
PILLAR_W = 24
SIDE_W = 24                     # inner face band of the side walls (collision edge, camp.c)
BASE_N = 106                    # ground line of the north wall panels
PILLAR_FWD = 2                  # pillars stand 2 px in front of the wall (thicker): their base is lower
LAT_PERIOD = 173                # rows between side pillars (5 panels along the nave at 0.5)
TOP_PANEL = 4                   # top face of the panel wall (cap thickness * sin 30)
TOP_PILLAR = 6
NORTH_H = 112                   # rows of the north strip
SIDE_Y0 = NORTH_H
CATH_WALL = ROOT / "assets/environment/cathedral/muros/muro_izq_128.png"
SIDE_MODE = os.environ.get("DS_CAMP_SIDE", "D")   # A rotated (current), B slanted, C frontal, D cathedral walls + weathering
NORTH_WALL = ROOT / "assets/environment/cathedral/muros/muro_fondo_pasante.png"
if SIDE_MODE == "D":                                # whole frame from the cathedral kit: north wall squashed to 128 rows
    BASE_N = 128
    NORTH_H = BASE_N + 6
    SIDE_Y0 = NORTH_H


def extract(name):
    im = Image.open(SRC / name).convert("RGB")
    a = np.asarray(im, np.float64)
    d = np.abs(a - BG).sum(axis=2)
    m = d > 40
    m = ndimage.binary_opening(m, iterations=2)
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    m = lab == (1 + int(np.argmax(sizes)))
    m = ndimage.binary_fill_holes(m)
    m = ndimage.binary_erosion(m, iterations=2)       # drops the matte halo
    ys, xs = np.where(m)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    return a[box[1]:box[3], box[0]:box[2]], m[box[1]:box[3], box[0]:box[2]]


def resize(rgb, mask, size):
    """Area-average resize with premultiplied alpha. Returns float rgb, float alpha."""
    rgba = np.dstack([rgb, mask.astype(np.float64) * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA").convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
    o = np.asarray(im, np.float64)
    return o[..., :3], o[..., 3] / 255.0


def find_joint(lum_rows, y0, y1):
    """Row of the darkest mortar line (lowest mean luminance, smoothed) in [y0, y1)."""
    s = ndimage.uniform_filter1d(lum_rows, 9)
    return y0 + int(np.argmin(s[y0:y1]))


class Canvas:
    def __init__(self):
        self.rgb = np.zeros((H, W, 3))
        self.a = np.zeros((H, W), bool)
        self.gain = np.ones((H, W))        # per-face light multiplier (top faces catch more moon, bands less)

    def put(self, x, y, rgb, alpha, gain=1.0):
        h, w = alpha.shape
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, W), min(y + h, H)
        if x1 <= x0 or y1 <= y0:
            return
        sa = alpha[y0 - y:y1 - y, x0 - x:x1 - x] >= 0.5
        sr = rgb[y0 - y:y1 - y, x0 - x:x1 - x]
        self.rgb[y0:y1, x0:x1][sa] = sr[sa]
        self.a[y0:y1, x0:x1] |= sa
        self.gain[y0:y1, x0:x1][sa] = gain


def north_from_cathedral(c):
    """North wall = the cathedral's back wall with the arched passage (muro_fondo_pasante), cropped to its opaque rows and
    squashed to BASE_N rows. Returns the boolean mask (H, W) of the passage (the gate hole)."""
    im = np.asarray(Image.open(NORTH_WALL).convert("RGBA"), np.float64)
    ys = np.where(im[..., 3].max(axis=1) > 128)[0]
    im = im[ys.min():ys.max() + 1]
    # The corner pillars of the source are 22 px wide; the side bands are SIDE_W: stretch each pillar to exactly SIDE_W
    # (and the middle to fit) so the pillar's inner edge lands on the side bands' inner edge, pixel for pixel.
    PIL = 22
    segs = [(0, PIL, SIDE_W), (PIL, W - PIL, W - 2 * SIDE_W), (W - PIL, W, SIDE_W)]
    parts = [resize(im[:, x0:x1, :3], im[:, x0:x1, 3] > 128, (w, BASE_N)) for x0, x1, w in segs]
    rgb = np.concatenate([q[0] for q in parts], axis=1)
    a = np.concatenate([q[1] for q in parts], axis=1)
    a_op = a >= 0.5
    c.put(0, 0, rgb, a)
    c.gain[:BASE_N][a_op] = 1.0
    # the passage: the transparent region that touches the bottom row at the centre
    lab, _ = ndimage.label(~a_op)
    k = lab[BASE_N - 2, W // 2]
    hole = np.zeros((H, W), bool)
    if k:
        hole[:BASE_N] = lab == k
    c.rgb[hole] = (4, 4, 8)
    c.a |= hole
    return hole


def weather(c):
    """Open-air courtyard: cracks and climbing ivy over the walls (deterministic, painted before the night grade)."""
    rng = np.random.default_rng(11)
    greens = [(96, 150, 70), (74, 124, 62), (128, 168, 80), (60, 100, 56)]
    crack = (36, 34, 40)
    stem = (50, 84, 48)

    def put(x, y, col, box):
        if box[0] <= x < box[1] and box[2] <= y < box[3] and c.a[y, x] and c.rgb[y, x].sum() > 40:
            c.rgb[y, x] = col

    def shade(x, y, k, box):
        if box[0] <= x < box[1] and box[2] <= y < box[3] and c.a[y, x] and c.rgb[y, x].sum() > 40:
            c.rgb[y, x] = np.clip(c.rgb[y, x] * k, 0, 255)

    def cracks(box, n):
        # Darken the stone it crosses (not a flat black line): a dark core, a faint dark halo and a lit lip on one side.
        for _ in range(n):
            x = int(rng.integers(box[0] + 2, box[1] - 2)); y = int(rng.integers(box[2] + 4, box[3] - 20))
            for step in range(int(rng.integers(12, 44))):
                shade(x, y, 0.50 if step % 5 else 0.62, box)
                shade(x - 1, y, 0.82, box)
                shade(x + 1, y, 1.12, box)
                y += 1
                x += int(rng.choice([-1, -1, 0, 1, 1]))
                if rng.random() < 0.25:                      # zig-zag: the crack steps sideways
                    shade(x, y, 0.55, box)
                    y += 1
                if rng.random() < 0.05:                      # branch
                    d = 1 if rng.random() < .5 else -1
                    for k in range(int(rng.integers(3, 8))):
                        shade(x + d * k, y + k // 2, 0.58, box)
                        shade(x + d * k, y + k // 2 + 1, 1.1, box)

    def ivy(box, n, length, x_lo, x_hi, y_start):
        for _ in range(n):
            x = int(rng.integers(x_lo, x_hi)); y = y_start(rng)
            for _ in range(int(rng.integers(length[0], length[1]))):
                put(x, y, stem, box)
                for _ in range(2):
                    if rng.random() < 0.7:
                        lx, ly = x + int(rng.integers(-3, 4)), y + int(rng.integers(-2, 3))
                        col = greens[int(rng.integers(0, len(greens)))]
                        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0)):
                            put(lx + dx, ly + dy, col, box)
                y -= 1
                x += int(rng.choice([-1, 0, 0, 0, 1]))
                x = min(max(x, x_lo), x_hi - 1)

    for x0 in (0, W - SIDE_W):
        box = (x0, x0 + SIDE_W, BASE_N, H)
        cracks(box, 26)
        ivy(box, 16, (40, 130), x0 + 3, x0 + SIDE_W - 3, lambda r: int(r.integers(BASE_N + 60, H - 4)))
    box = (0, W, 0, BASE_N)
    cracks(box, 30)
    ivy(box, 13, (14, 70), 6, W - 6, lambda r: BASE_N - 2)


def build():
    liso, liso_m = extract("panel_liso.jpg")
    port, port_m = extract("panel_porton.jpg")
    pil, pil_m = extract("contrafuerte.jpg")
    print("pieces: liso", liso.shape[:2][::-1], "porton", port.shape[:2][::-1], "contrafuerte", pil.shape[:2][::-1])

    # Drop the dark chipped rim of the panels' left/right edges (it would show as a seam line between neighbours).
    RIM = 10
    liso, liso_m = liso[:, RIM:-RIM], liso_m[:, RIM:-RIM]
    port, port_m = port[:, RIM:-RIM], port_m[:, RIM:-RIM]
    # Panels and gate share footprint: same size by construction (both bboxes are ~ equal; resample to the liso one).
    ph, pw = liso.shape[:2]
    if port.shape[:2] != (ph, pw):
        port, port_m = resize(port, port_m, (pw, ph))
        port_m = port_m > 0.5
    s_panel = (sum(PANEL_W) / 3.0) / pw
    face_h = int(round(ph * s_panel * K))
    print(f"panel: {pw}x{ph} -> {PANEL_W} x {face_h}  (px/texel {s_panel:.4f})")

    # Pillar: same block scale as the panel (blocks in the kit are ~1.2x bigger in the pillar image): its
    # width fixes its scale; then cut a band of courses at mortar joints so it is as tall as the panel.
    pw2 = pil.shape[1]
    s_pil = PILLAR_W / pw2
    need = int(round(face_h / (s_pil * K)))
    cut = pil.shape[0] - need
    lum = (0.3 * pil[..., 0] + 0.59 * pil[..., 1] + 0.11 * pil[..., 2])
    shaft = lum[:, int(pw2 * 0.25):int(pw2 * 0.75)]
    rows = shaft.mean(axis=1)
    # joint candidates around 22% and 22% + cut (after the cap, before the plinth)
    j0 = find_joint(rows, int(pil.shape[0] * 0.17), int(pil.shape[0] * 0.27))
    j1 = find_joint(rows, j0 + cut - 60, j0 + cut + 60)
    print(f"pillar {pil.shape[1]}x{pil.shape[0]}: cut texels {j0}..{j1} ({j1 - j0}, wanted {cut})")
    pil_cut = np.concatenate([pil[:j0], pil[j1:]], axis=0)
    pil_cut_m = np.concatenate([pil_m[:j0], pil_m[j1:]], axis=0)
    pillar_h = face_h
    p_rgb, p_a = resize(pil_cut, pil_cut_m, (PILLAR_W, pillar_h))

    # Top-face colours (mean of the cornice / cap), a little lighter than the faces.
    cornice = liso[int(ph * 0.03):int(ph * 0.06)]
    top_panel_rgb = cornice.reshape(-1, 3).mean(axis=0)
    cap = pil[int(pil.shape[0] * 0.052):int(pil.shape[0] * 0.075)]
    top_pillar_rgb = cap.reshape(-1, 3).mean(axis=0)

    c = Canvas()

    # ---- side bands: the plain panel, rotated: u (along the nave) -> y at 0.5, height -> x (top outside) ----
    band_len = int(round(PANEL_W[0] * 0.5))          # rows per panel
    for side in (0, 1):
        n_rows = H - BASE_N + 40
        stack_rgb = np.zeros((n_rows, SIDE_W, 3))
        stack_a = np.zeros((n_rows, SIDE_W))
        y = 0
        while y < n_rows:
            if SIDE_MODE == "D":                             # cathedral side wall (assets/environment/cathedral/muros)
                strip = np.asarray(Image.open(CATH_WALL).convert("RGBA"), np.float64)[:, 48 - SIDE_W:]
                rgb, a = strip[..., :3], strip[..., 3] / 255.0
                step = rgb.shape[0]
            elif SIDE_MODE == "C":                             # frontal courses, compressed across the band
                rgb, a = resize(liso, liso_m, (SIDE_W, face_h))
                step = face_h
            else:                                            # rotated: u (along the nave) -> y at 0.5, height -> x
                rgb, a = resize(liso, liso_m, (band_len, SIDE_W))
                rgb = rgb.transpose(1, 0, 2)
                a = a.T
                step = band_len
            h = min(step, n_rows - y)
            stack_rgb[y:y + h], stack_a[y:y + h] = rgb[:h], a[:h]
            y += step
        if SIDE_MODE == "B":                                 # courses slanted 2:1 like the floor diamonds
            for col in range(SIDE_W):
                sh = col // 2
                stack_rgb[:, col] = np.roll(stack_rgb[:, col], sh, axis=0)
                stack_a[:, col] = np.roll(stack_a[:, col], sh, axis=0)
        if side == 1:
            stack_rgb, stack_a = stack_rgb[:, ::-1], stack_a[:, ::-1]
        c.put(0 if side == 0 else W - SIDE_W, BASE_N, stack_rgb[:H - BASE_N], stack_a[:H - BASE_N], gain=(1.0 if SIDE_MODE == "D" else 0.8))

    # ---- north wall: panels (the central one is the gate) --------------------------------------------------
    xs = [PANEL_X0]
    for w in PANEL_W[:-1]:
        xs.append(xs[-1] + w)
    for i, (x, w) in enumerate(zip(xs, PANEL_W) if SIDE_MODE != "D" else []):
        src, srcm = (port, port_m) if i == 1 else (liso, liso_m)
        rgb, a = resize(src, srcm, (w, face_h))
        # outer panels continue 8 px under the corner pillars (edge texels repeated): no gap beside the pillar shaft
        pad = 8
        if i == 0:
            rgb = np.concatenate([np.repeat(rgb[:, :1], pad, 1), rgb], 1)
            a = np.concatenate([np.repeat(a[:, :1], pad, 1), a], 1)
            x, w = x - pad, w + pad
        if i == len(PANEL_W) - 1:
            rgb = np.concatenate([rgb, np.repeat(rgb[:, -1:], pad, 1)], 1)
            a = np.concatenate([a, np.repeat(a[:, -1:], pad, 1)], 1)
            w = w + pad
        # the sliver of top face above it
        top = np.tile(top_panel_rgb, (TOP_PANEL, w, 1))
        c.put(x, BASE_N - face_h - TOP_PANEL, top, np.ones((TOP_PANEL, w)), gain=1.15)
        c.put(x, BASE_N - face_h, rgb, a)
    # Panels were matted on their own bbox: close hairline gaps between neighbours by stretching the join.
    # (handled in grade: any 1-px transparent column between panels takes the left neighbour)

    # ---- pillars: corners and side rhythm (same sprite) ------------------------------------------------------
    def pillar(x, base, mirror=False):
        rgb, a = p_rgb, p_a
        if mirror:
            rgb, a = rgb[:, ::-1], a[:, ::-1]
        top = np.tile(top_pillar_rgb, (TOP_PILLAR, PILLAR_W, 1))
        c.put(x, base - pillar_h - TOP_PILLAR, top, np.ones((TOP_PILLAR, PILLAR_W)), gain=1.15)
        c.put(x, base - pillar_h, rgb, a)

    # side pillars north to south (painter's order), then the corners over the join with the north wall
    base = BASE_N + PILLAR_FWD + LAT_PERIOD
    while base - pillar_h - TOP_PILLAR < H:
        pillar(0, base)
        pillar(W - PILLAR_W, base, mirror=True)
        base += LAT_PERIOD
    if SIDE_MODE != "D":
        pillar(0, BASE_N + PILLAR_FWD)
        pillar(W - PILLAR_W, BASE_N + PILLAR_FWD, mirror=True)

    hole = None
    if SIDE_MODE == "D":
        hole = north_from_cathedral(c)
        weather(c)

    # gate hole: near black and opaque
    hole_x0 = xs[1]
    return c, dict(hole_mask_full=hole, face_h=face_h, xs=xs, hole_x=hole_x0, panel_wh=(pw, ph), s_panel=s_panel)


def grade(c):
    """Cold moon for all, warm bath by distance to the bonfire. Returns RGB uint8 canvas (H, W, 3)."""
    rgb = c.rgb
    lum = 0.3 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]
    m = c.a
    mean = lum[m].mean()
    # keep the relief: local contrast stretch about the mean luminance
    ln = np.clip(1.0 + (lum - mean) / mean * 1.5, 0.05, 2.2)
    # keep a little of the stone's own hue (the kit is grey-brown); the rest is the grading tint
    hue = rgb / np.maximum(lum[..., None], 1.0)
    hue = 1.0 + (hue - 1.0) * 0.5
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    d = np.sqrt((xx - FIRE_X) ** 2 + (2 * (yy - FIRE_Y)) ** 2)
    f = np.clip(1.0 - d / 290.0, 0, 1) ** 1.9
    moon_tint = np.array([0.50, 0.62, 1.00])
    fire_tint = np.array([1.00, 0.70, 0.42])
    moon = (ln * c.gain)[..., None] * moon_tint * hue * MOON_LEVEL
    fire = (ln * c.gain)[..., None] * fire_tint * hue * (f[..., None] * FIRE_LEVEL)
    out = moon + fire
    grey = (0.3 * out[..., 0] + 0.59 * out[..., 1] + 0.11 * out[..., 2])[..., None]
    out = grey + (out - grey) * 0.68           # muted (DESIGN 6.10)
    return np.clip(out, 0, 255)


MOON_LEVEL = 56.0     # peak moon brightness of average stone, 0..255 (floor far from the fire is ~ 20..40)
FIRE_LEVEL = 150.0


def finish(c, info):
    out = grade(c)
    if info.get("hole_mask_full") is not None:
        hm = info["hole_mask_full"]
        out[hm] = (4, 4, 8)
        info["hole_box"] = (int(np.where(hm.any(0))[0].min()), int(np.where(hm.any(0))[0].max()) + 1,
                            int(np.where(hm.any(1))[0].min()), int(np.where(hm.any(1))[0].max()) + 1)
        return out
    # the gate hole: near black (opaque). Dark pixels of the original inside the gate panel.
    x0, w = info["xs"][1], PANEL_W[1]
    y0 = BASE_N - info["face_h"]
    reg = c.rgb[y0:BASE_N, x0:x0 + w]
    lumr = 0.3 * reg[..., 0] + 0.59 * reg[..., 1] + 0.11 * reg[..., 2]
    hole = lumr < 45
    hole = ndimage.binary_opening(hole, iterations=1)
    lab, n = ndimage.label(hole)
    if n:
        sizes = ndimage.sum(hole, lab, range(1, n + 1))
        hole = lab == (1 + int(np.argmax(sizes)))
    sub = out[y0:BASE_N, x0:x0 + w]
    sub[hole] = (4, 4, 8)
    info["hole_mask"] = hole
    info["hole_box"] = (x0 + int(np.where(hole.any(0))[0].min()), x0 + int(np.where(hole.any(0))[0].max()) + 1,
                        y0 + int(np.where(hole.any(1))[0].min()), y0 + int(np.where(hole.any(1))[0].max()) + 1)
    return out


def to_rgb15(out, a):
    q = (out / 8.0).round().astype(np.int32).clip(0, 31)
    v = q[..., 0] | (q[..., 1] << 5) | (q[..., 2] << 10) | 0x8000
    return np.where(a, v, 0).astype(np.uint16)


def write_bin(path, arr):
    path.write_bytes(np.ascontiguousarray(arr.astype("<u2")).tobytes())


def main():
    c, info = build()
    # close vertical hairline seams inside the north strip: a transparent pixel with opaque neighbours left+right
    a = c.a
    for y in range(NORTH_H):
        for x in range(1, W - 1):
            if not a[y, x] and a[y, x - 1] and a[y, x + 1] and y >= 6:
                c.rgb[y, x] = c.rgb[y, x - 1]
                a[y, x] = True
    out = finish(c, info)
    v = to_rgb15(out, c.a)
    # preview of the colour canvas as the game would show it (on a floor-ish dark grey)
    prev = np.zeros((H, W, 3), np.uint8) + np.array([30, 32, 40], np.uint8)
    q = (v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31
    col = np.dstack(q).astype(np.uint8)
    prev[c.a] = col[c.a]
    Image.fromarray(prev).save(WORK / "marco_canvas.png")
    Image.fromarray(prev).resize((W * 3, H * 3), Image.NEAREST).save(WORK / "marco_canvas_3x.png")
    Image.fromarray(np.clip(c.rgb, 0, 255).astype(np.uint8)).save(WORK / "marco_plano.png")   # flat light, before grading

    north = v[:NORTH_H, :]
    izq = v[SIDE_Y0:, :SIDE_W]
    der = v[SIDE_Y0:, W - SIDE_W:]
    write_bin(NITRO / "marco_norte.bin", north)
    write_bin(NITRO / "marco_izq.bin", izq)
    write_bin(NITRO / "marco_der.bin", der)
    opaque = int((v != 0).sum())
    hb = info["hole_box"]
    hdr = [
        "// GENERATED by tools/camp/marco_build.py. Do not edit.",
        "#ifndef CAMP_MARCO_H",
        "#define CAMP_MARCO_H",
        f"#define CAMP_MARCO_NORTH_H {NORTH_H}",
        f"#define CAMP_MARCO_SIDE_W {SIDE_W}",
        f"#define CAMP_MARCO_SIDE_Y0 {SIDE_Y0}",
        f"#define CAMP_MARCO_SIDE_H {H - SIDE_Y0}",
        f"#define CAMP_MARCO_BASE_N {BASE_N}",
        f"#define CAMP_MARCO_DOOR_X0 {hb[0]}",
        f"#define CAMP_MARCO_DOOR_X1 {hb[1]}",
        f"#define CAMP_MARCO_DOOR_Y0 {hb[2]}",
        f"#define CAMP_MARCO_DOOR_Y1 {hb[3]}",
        "#endif",
        "",
    ]
    (ROOT / "include/camp_marco.h").write_text("\n".join(hdr), encoding="utf-8", newline="")
    print(f"opaque px in the frame: {opaque}  north {(north != 0).sum()}  sides {(izq != 0).sum()}+{(der != 0).sum()}")
    print("gate hole box x0,x1,y0,y1:", hb)


if __name__ == "__main__":
    main()
