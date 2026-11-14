#!/usr/bin/env python3
"""Bakes the Sacred Heart lab render into the two HUD icons using the C2 pipeline.

  assets/sprites/hud/source/heart_render.png  ->  assets/sprites/hud/heart_full.png + heart_empty.png

Uses the same C2 downscale & legibility post-process as tools/props/prerender_props.py:
premultiplied LANCZOS resize, BOX alpha resize with 0.30 threshold, soft_contrast(1.45),
and alpha-aware sharpen_rgba(0.5), no outline. The empty icon is the same silhouette in dark ash.
Then run tools/generate_hud_icons_c.py.   Usage: python tools/hud/bake_hud_heart.py [box] [drop_cut]
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HUD = ROOT / "assets" / "sprites" / "hud"
ALPHA_THRESH = 0.30  # C2 legibility threshold


def soft_contrast(rgb, gain=1.45):
    f = rgb / 255.0
    L = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    p = float(np.median(L))
    d = L - p
    m = np.where(d < 0, p, 1 - p)
    out = p + d * gain / (1 + (gain - 1) * np.abs(d) / np.maximum(m, 1e-4))
    scale = np.where(L > 1e-4, out / np.maximum(L, 1e-4), 1)
    return np.clip(f * scale[..., None], 0, 1) * 255.0


def blur3(x):
    k = np.array([1.0, 2.0, 1.0]) / 4.0
    p = np.pad(x, ((1, 1), (1, 1)) + ((0, 0),) * (x.ndim - 2), mode="edge")
    h = k[0] * p[:, :-2] + k[1] * p[:, 1:-1] + k[2] * p[:, 2:]
    return k[0] * h[:-2] + k[1] * h[1:-1] + k[2] * h[2:]


def sharpen_rgba(rgba, amount=0.5):
    rgb = rgba[..., :3].astype(float)
    m = (rgba[..., 3] > 0).astype(float)
    bl = blur3(rgb * m[..., None]) / np.maximum(blur3(m), 1e-3)[..., None]
    out = rgba.copy()
    out[..., :3] = np.clip(rgb + amount * (rgb - bl), 0, 255).astype(np.uint8)
    return out


def main():
    box = int(sys.argv[1]) if len(sys.argv) > 1 else 18          # icon fits in box x box
    drop_cut = float(sys.argv[2]) if len(sys.argv) > 2 else 0.18  # fraction of height cut at the bottom (blood drop)
    src = Image.open(HUD / "source" / "heart_render.png").convert("RGBA")
    src = src.crop(src.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    src = src.crop((0, 0, src.width, round(src.height * (1 - drop_cut))))
    src = src.crop(src.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())

    scale = min(box / src.width, box / src.height)
    cw, ch = max(1, round(src.width * scale)), max(1, round(src.height * scale))

    arr = np.array(src)
    rgb_src = arr[..., :3].astype(np.float32)
    m_src = (arr[..., 3] > 127).astype(np.float32)
    chans = []
    for c in range(3):
        im = Image.fromarray(rgb_src[..., c] * m_src, mode="F").resize((cw, ch), Image.LANCZOS)
        chans.append(np.array(im))
    am = np.array(Image.fromarray(m_src, mode="F").resize((cw, ch), Image.BOX))
    a = am >= ALPHA_THRESH
    rgb = np.stack(chans, -1) / np.maximum(am[..., None], 1e-3)
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    rgba = np.zeros((ch, cw, 4), np.uint8)
    rgba[..., :3] = rgb * a[..., None]
    rgba[..., 3] = a * 255
    if a.any():
        rgba[..., :3][a] = soft_contrast(rgba[..., :3][a].astype(float)[None], 1.45)[0].astype(np.uint8)
        rgba = sharpen_rgba(rgba, 0.5)

    full = Image.fromarray(rgba, "RGBA")
    full_px = full.load()

    empty = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    e_px = empty.load()
    for y in range(ch):
        for x in range(cw):
            r, g, b, al = full_px[x, y]
            if not al:
                continue
            lum = 0.3 * r + 0.59 * g + 0.11 * b
            v = int(30 + lum * 0.25)
            e_px[x, y] = (v + 2, v, v, 255)

    full.save(HUD / "heart_full.png")
    empty.save(HUD / "heart_empty.png")
    print(f"icons (C2) {cw}x{ch}")


if __name__ == "__main__":
    main()
