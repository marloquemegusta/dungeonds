#!/usr/bin/env python3
"""Package real DeSmuME PNG captures into an animated GIF without rendering frames."""

import argparse
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-ms", type=int, default=80)
    args = parser.parse_args()

    frames = sorted(args.input_dir.glob(f"{args.prefix}_*.png"))
    if len(frames) < 2:
        raise SystemExit(f"need at least two real captures matching {args.prefix}_*.png")
    rgb_images = [Image.open(path).convert("RGB") for path in frames]
    first_p = rgb_images[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
    quantized = [first_p] + [im.quantize(palette=first_p) for im in rgb_images[1:]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(args.output, save_all=True, append_images=quantized[1:],
                      duration=args.duration_ms, loop=0, disposal=2)
    print(f"[OK] {args.output} frames={len(quantized)}")


if __name__ == "__main__":
    main()
