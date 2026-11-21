#!/usr/bin/env python3
"""Animated bonfire flame of the night camp (DESIGN.md 7.5), precalculated offline: no float on the console.

FRAMES frames of W x H RGB15 pixels (BIT(15) = opaque, 0 = transparent), stacked vertically in one strip
(nitrofiles/camp/hoguera_fuego.bin, little endian uint16). The flame root is the bottom-centre of each frame
(BASE_X, H-1). Colours are the muted FX_SH_* ramp of source/weapons.c (ivory, gold, amber, ember, crimson):
no primaries, no neon (DESIGN.md 6.10). The sway is a closed loop (phase = t / FRAMES), so the strip tiles.
usage: python tools/camp/fuego_frames.py [preview.png]   (also imported by generate_camp_gfx.py)
"""
import sys
import numpy as np

W, H, FRAMES = 32, 52, 8
BASE_X = W // 2
FLAME_H = 46.0                         # px of flame body above the root (the rest is the tongue tips / sparks)

def rgb15(r, g, b):
    return (r | (g << 5) | (b << 10)) | 0x8000

IVORY, GOLD, AMBER, EMBER, CRIMSON = (rgb15(29, 25, 19), rgb15(27, 20, 11), rgb15(24, 15, 7),
                                      rgb15(20, 9, 5), rgb15(15, 5, 4))
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5

# (x offset at the root, height as a fraction of FLAME_H, half-width at the root, sway amplitude, loop harmonic, phase)
TONGUES = (
    (0.0, 1.00, 6.5, 2.6, 1, 0.0),     # main tongue, tall and slow
    (-6.0, 0.62, 5.0, 2.2, 2, 1.7),
    (6.5, 0.74, 5.0, 2.4, 1, 3.9),
    (-2.5, 0.82, 4.8, 2.0, 2, 5.1),
    (3.0, 0.50, 4.2, 1.8, 3, 2.6),
)

def frame(k):
    ph = 2 * np.pi * k / FRAMES
    ys, xs = np.mgrid[0:H, 0:W].astype(float)
    hp = H - 1 - ys                                  # px above the root
    x = xs - BASE_X
    best = np.zeros((H, W))
    for off, tall, w0, amp, m, p0 in TONGUES:
        ht = FLAME_H * tall * (1.0 + 0.05 * np.sin(ph * m + p0))      # height pulses a little
        h = hp / ht
        inside = (h >= 0) & (h < 1.0)
        c = off * (1.0 - 0.35 * h) + amp * np.sin(ph * m + p0 + 2.4 * h) * h ** 1.3
        # Pear shape: round belly low, long narrow tip that curls; the edge wobbles.
        hw = w0 * (np.clip(1.0 - h, 0, 1) ** 0.9) * (1.0 + 0.12 * np.sin(9.0 * h - 2 * ph * m + p0))
        r = np.abs(x - c) / np.maximum(hw, 0.35)
        v = np.where(inside & (r < 1.0), (1.0 - r ** 1.5) * (1.0 - 0.9 * h) * (0.55 + 0.45 * tall), 0.0)
        best = np.maximum(best, v)
    body = best > 0
    v = best + np.tile(BAYER, (H // 4, W // 4)) * 0.12            # ordered dither: crisp, not smooth
    col = np.where(v > 0.74, IVORY, np.where(v > 0.50, GOLD, np.where(v > 0.28, AMBER,
                   np.where(v > 0.12, EMBER, CRIMSON))))
    out = np.zeros((H, W), np.uint16)
    out[body] = col[body]
    # A few embers rising on their own loop (1-px sparks above the flame).
    for i, (sx, p0) in enumerate(((-5, 0.0), (4, 0.37), (0, 0.71))):
        t = (k / FRAMES + p0) % 1.0
        ey = int(H - 1 - FLAME_H * (0.50 + 0.50 * t) - 1)
        ex = int(BASE_X + sx + round(2.0 * np.sin(2 * np.pi * (t + i / 3.0))))
        if 0 <= ey < H and 0 <= ex < W and t < 0.85 and not out[ey, ex]:
            out[ey, ex] = EMBER if t > 0.5 else AMBER
    return out

def frames():
    return [frame(k) for k in range(FRAMES)]

def strip_bytes():
    return b"".join(f.astype("<u2").tobytes() for f in frames())

def to_rgba(f):
    r, g, b = (f & 31) << 3, ((f >> 5) & 31) << 3, ((f >> 10) & 31) << 3
    a = np.where(f & 0x8000, 255, 0)
    return np.stack([r, g, b, a], -1).astype(np.uint8)

if __name__ == "__main__":
    from PIL import Image
    fs = frames()
    pad = 4
    sheet = Image.new("RGBA", (FRAMES * (W + pad) + pad, H + 2 * pad), (22, 22, 30, 255))
    for k, f in enumerate(fs):
        sheet.alpha_composite(Image.fromarray(to_rgba(f), "RGBA"), (pad + k * (W + pad), pad))
    sheet = sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST)
    out = sys.argv[1] if len(sys.argv) > 1 else "fuego_hoja.png"
    sheet.save(out); print(out, sheet.size)
