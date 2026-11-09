#!/usr/bin/env python3
"""Prepare deterministic seamless albedo and normalized height maps for floor tiles."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def make_tileable(image):
    """Periodic image: cross-fade the original (centre) with a half-shifted copy (edges).

    np.roll wraps, so the shifted copy is periodic. The fade weight is 0 on every
    border, where only the shifted copy shows, and 1 in the middle, where the
    original shows, so opposite edges match.
    """
    a = np.asarray(image, dtype=np.float32)
    h, w = a.shape[:2]
    rolled = np.roll(a, (h // 2, w // 2), axis=(0, 1))
    wx = np.sin(np.pi * (np.arange(w) + .5) / w) ** 2
    wy = np.sin(np.pi * (np.arange(h) + .5) / h) ** 2
    weight = (wy[:, None] * wx[None, :])[..., None].astype(np.float32)
    out = a * weight + rolled * (1 - weight)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image", type=Path)
    p.add_argument("--out-dir", type=Path, default=Path("assets/models/environment/floor_proto/source"))
    p.add_argument("--height-blur", type=float, default=1.4)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    color = make_tileable(Image.open(args.image).convert("RGB"))
    color.save(args.out_dir / "albedo_tileable.png")

    # Luminance plus local contrast. Dark, smooth puddles are lowered; bright and
    # high-frequency material (boards, stones, debris) is raised. Normalize and
    # blur slightly to avoid pixel-scale spikes while retaining small relief.
    rgb = np.asarray(color, dtype=np.float32) / 255.0
    lum = rgb[..., 0] * .2126 + rgb[..., 1] * .7152 + rgb[..., 2] * .0722
    smooth = np.asarray(color.filter(ImageFilter.GaussianBlur(10)), dtype=np.float32) / 255.0
    low = smooth[..., 0] * .2126 + smooth[..., 1] * .7152 + smooth[..., 2] * .0722
    local = lum - low
    height = np.clip(.53 + (lum - .42) * .72 + local * 1.15, 0, 1)
    height = np.asarray(Image.fromarray((height * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(args.height_blur)))
    Image.fromarray(height.astype(np.uint8), "L").save(args.out_dir / "height.png")
    print(f"prepared {color.size} deterministic maps in {args.out_dir}")


if __name__ == "__main__":
    main()
