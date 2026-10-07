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
    parser.add_argument("--crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--skip-initial", type=int, default=0)
    args = parser.parse_args()

    frames = sorted(args.input_dir.glob(f"{args.prefix}_*.png"))
    if args.skip_initial < 0:
        parser.error("--skip-initial cannot be negative")
    frames = frames[args.skip_initial:]
    if len(frames) < 2:
        raise SystemExit(f"need at least two real captures matching {args.prefix}_*.png")
    if args.scale < 1:
        parser.error("--scale must be at least 1")
    rgb_images = [Image.open(path).convert("RGB") for path in frames]
    if args.crop:
        box = tuple(args.crop)
        width, height = rgb_images[0].size
        if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height or box[0] >= box[2] or box[1] >= box[3]:
            parser.error(f"--crop must fit within captured frame size {width}x{height}")
        rgb_images = [im.crop(box) for im in rgb_images]
    if args.scale > 1:
        rgb_images = [im.resize((im.width * args.scale, im.height * args.scale), Image.Resampling.NEAREST)
                      for im in rgb_images]
    first_p = rgb_images[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
    quantized = [first_p] + [im.quantize(palette=first_p) for im in rgb_images[1:]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(args.output, save_all=True, append_images=quantized[1:],
                      duration=args.duration_ms, loop=0, disposal=2)
    print(f"[OK] {args.output} frames={len(quantized)}")


if __name__ == "__main__":
    main()
