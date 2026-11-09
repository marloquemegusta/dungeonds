#!/usr/bin/env python3
"""Create a small contract-compatible amber light ray for the godrays prototype."""
from pathlib import Path

from PIL import Image


OUT = Path("assets/sprites/godrays/placeholder/ray_placeholder.png")
WIDTH, HEIGHT = 256, 128


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    # A diagonal, narrowing shaft leaves the window at x=0 and reaches the floor.
    for y in range(HEIGHT):
        center = 16 + y * 3
        half_width = 8 + y // 2
        fade = max(0, 255 - y * 3 // 2)
        for x in range(max(0, center - half_width), min(WIDTH, center + half_width)):
            edge = min(x - (center - half_width), (center + half_width) - x)
            strength = min(255, fade * min(255, edge * 40) // 255)
            # A few colored bands make the test texture easy to identify on hardware.
            band = (x + y // 2) // 9
            colors = ((255, 188, 72), (255, 220, 128), (255, 144, 48), (255, 236, 176))
            r, g, b = colors[band % len(colors)]
            image.putpixel((x, y), (r * strength // 255, g * strength // 255, b * strength // 255))
    image.save(OUT, format="PNG", optimize=True)
    print(f"created {OUT} ({WIDTH}x{HEIGHT}, RGB)")


if __name__ == "__main__":
    main()
