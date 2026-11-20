#!/usr/bin/env python3
"""Generates the 23x23 C2-baked Sunburst Viril (active spell container) for the HUD.

Outputs:
  assets/sprites/hud/source/viril_solar_256.png
  assets/sprites/hud/viril_solar.png
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HUD = ROOT / "assets" / "sprites" / "hud"
ALPHA_THRESH = 0.30


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


def render_viril_hires(num_rays=12, size=256):
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2.0
    dx, dy = xx - cx, yy - cy
    dist = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)

    r_inner = size * 0.19
    r_ring = size * 0.24
    r_tip = size * 0.49

    phase = (ang / (2 * math.pi) * num_rays) % 1.0
    tri = 1.0 - np.abs(phase * 2.0 - 1.0)
    alt = 0.95 + 0.05 * np.cos(ang * (num_rays / 2.0))
    r_outer = r_ring + (r_tip - r_ring) * (tri ** 2.1) * alt

    nx = dx / (size * 0.45)
    ny = dy / (size * 0.45)
    lit = 0.88 - 0.32 * (nx * 0.7 + ny * 0.7)
    ray_bevel = np.where(phase < 0.5, 1.10, 0.82)
    in_ray = (dist > r_ring - 2) & (dist <= r_outer)
    in_ring = (dist >= r_inner) & (dist <= r_ring)
    in_host = dist < r_inner

    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    bronze = np.array([184, 144, 78], dtype=np.float32)

    for c in range(3):
        rgba[..., c] = np.where(in_ray, np.clip(bronze[c] * lit * ray_bevel, 0, 255), rgba[..., c])
    ring_t = (dist - r_inner) / max(1.0, r_ring - r_inner)
    ring_bev = 0.85 + 0.28 * np.sin(ring_t * math.pi)
    for c in range(3):
        rgba[..., c] = np.where(in_ring, np.clip(bronze[c] * lit * ring_bev, 0, 255), rgba[..., c])
    host_lit = 0.97 - 0.10 * (nx + ny)
    host_col = np.array([218, 206, 182], dtype=np.float32)
    for c in range(3):
        rgba[..., c] = np.where(in_host, np.clip(host_col[c] * host_lit, 0, 255), rgba[..., c])

    rgba[..., 3] = np.where(in_ray | in_ring | in_host, 255, 0)
    return Image.fromarray(rgba, "RGBA")


def bake_c2(src, box=23):
    src = src.crop(src.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    scale = min(box / src.width, box / src.height)
    cw, ch = max(1, round(src.width * scale)), max(1, round(src.height * scale))
    arr = np.array(src)
    rgb_src = arr[..., :3].astype(np.float32)
    m_src = (arr[..., 3] > 127).astype(np.float32)
    chans = [np.array(Image.fromarray(rgb_src[..., c] * m_src, mode="F").resize((cw, ch), Image.LANCZOS)) for c in range(3)]
    am = np.array(Image.fromarray(m_src, mode="F").resize((cw, ch), Image.BOX))
    a = am >= ALPHA_THRESH
    rgb = np.clip(np.stack(chans, -1) / np.maximum(am[..., None], 1e-3), 0, 255).astype(np.uint8)
    rgba = np.zeros((ch, cw, 4), np.uint8)
    rgba[..., :3] = rgb * a[..., None]
    rgba[..., 3] = a * 255
    if a.any():
        rgba[..., :3][a] = soft_contrast(rgba[..., :3][a].astype(float)[None], 1.45)[0].astype(np.uint8)
        rgba = sharpen_rgba(rgba, 0.5)
    return Image.fromarray(rgba, "RGBA")


def tint_viril(img, ring_mul, host_mul):
    arr = np.array(img).astype(np.float32)
    h, w, _ = arr.shape
    cx, cy = w / 2.0, h / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    is_host = np.hypot(xx - cx, yy - cy) < 4.9
    for c in range(3):
        arr[..., c] = np.where(is_host, np.clip(arr[..., c] * host_mul[c], 0, 255),
                                        np.clip(arr[..., c] * ring_mul[c], 0, 255))
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def draw_pixels(im, cx, cy, coords, fg, sh):
    for dx, dy in coords:
        if 0 <= cx + dx + 1 < im.width and 0 <= cy + dy + 1 < im.height:
            im.putpixel((cx + dx + 1, cy + dy + 1), sh)
    for dx, dy in coords:
        if 0 <= cx + dx < im.width and 0 <= cy + dy < im.height:
            im.putpixel((cx + dx, cy + dy), fg)


SPELLS = {
    "rayo": (
        (1.06, 1.04, 1.02), (1.12, 1.12, 1.14),
        (108, 86, 44, 255), (200, 194, 180, 160),
        [(0,-4),(0,-3),(0,-2),(-2,0),(-1,0),(0,0),(1,0),(2,0),(0,1),(0,2),(0,3),(0,4),(-1,-1),(1,-1),(-1,1),(1,1)],
    ),
    "glifo": (
        (0.76, 0.98, 0.78), (0.82, 0.98, 0.80),
        (44, 78, 52, 255), (146, 174, 144, 160),
        [(0,-4),(-1,-3),(1,-3),(-2,-2),(2,-2),(-3,-1),(3,-1),(-4,0),(4,0),(-3,1),(3,1),(-2,2),(2,2),(-1,3),(1,3),(0,4),(0,0)],
    ),
    "ejecucion": (
        (1.02, 0.74, 0.72), (1.00, 0.80, 0.78),
        (118, 32, 34, 255), (186, 148, 144, 160),
        [(0,-4),(0,-3),(-3,-2),(-2,-2),(-1,-2),(0,-2),(1,-2),(2,-2),(3,-2),(0,-1),(0,0),(0,1),(0,2),(0,3),(0,4)],
    ),
    "levantar": (
        (0.48, 0.48, 0.52), (0.20, 0.20, 0.22),
        (212, 204, 184, 255), (14, 12, 14, 220),
        [(-3,-3),(-3,-2),(-2,-1),(-1,-4),(-1,-3),(-1,-2),(1,-4),(1,-3),(1,-2),(3,-3),(3,-2),(2,-1),
         (-2,0),(-1,0),(0,0),(1,0),(2,0),(-1,1),(0,1),(1,1),(0,2),(0,3),(-3,3),(-2,3),(2,3),(3,3)],
    ),
}


def main():
    (HUD / "source").mkdir(parents=True, exist_ok=True)
    hi = render_viril_hires(12, 256)
    hi.save(HUD / "source" / "viril_solar_256.png")
    low = bake_c2(hi, 26)
    low.save(HUD / "viril_solar.png")
    for name, (rmul, hmul, fg, sh, coords) in SPELLS.items():
        im = tint_viril(low, rmul, hmul)
        draw_pixels(im, im.width // 2, im.height // 2, coords, fg, sh)
        im.save(HUD / f"viril_{name}.png")
    print("Saved viril_solar.png + 4 spell virils", low.size)


if __name__ == "__main__":
    main()
