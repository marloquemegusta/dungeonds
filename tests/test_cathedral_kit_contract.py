#!/usr/bin/env python3
"""Keep the cathedral asset masks wired to real ground-plane collision and occlusion."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import bake_cathedral_kit as baker  # noqa: E402


def main():
    physical = ("banco_roto", "banco_volcado", "columna", "relicario", "santo", "vela")
    for name in physical:
        piece = baker.piece_layout(name)
        assert piece["foot_runs"], f"{name}: no collision footprint was baked"
        assert piece["depth_runs"], f"{name}: no sprite occlusion depth was baked"
        assert all(n > 0 and 0 <= x and 0 <= y for x, y, n in piece["foot_runs"]), name
        assert all(x + n <= piece["w"] // 4 and y < piece["h"] // 4
                   for x, y, n in piece["foot_runs"]), name
        assert len({y for _, y, _ in piece["foot_runs"]}) > 1 or name == "banco_roto", (
            f"{name}: footprint collapsed to a one-cell billboard"
        )
        # Depth is the world Y of the ground under each surface pixel, in sprite pixels (the
        # runtime compares it with actor feet). It must land inside the sprite, near the
        # footprint; raw lab-render units are 8-20x larger and broke occlusion.
        anchor, h = piece["foot_anchor_y_px"], piece["h"]
        foot_top = min(y for _, y, _ in piece["foot_runs"]) * 4
        ground = [anchor + d for _, _, _, d in piece["depth_runs"]]
        assert 0 <= min(ground) and max(ground) <= h, f"{name}: depth outside sprite ({min(ground)}..{max(ground)})"
        assert min(ground) >= foot_top - 24 and max(ground) <= anchor + 4, (
            f"{name}: depth {min(ground)}..{max(ground)} does not sit on footprint {foot_top}..{anchor}"
        )

    # The benches' plan must be the real planta (several cell rows, wide, under the sprite), not the
    # thin 0.30-1.20 m collision slice nor a filler rectangle.
    for name in ("banco_roto", "banco_volcado"):
        piece = baker.piece_layout(name)
        runs = piece["foot_runs"]
        assert len({y for _, y, _ in runs}) >= 3, f"{name}: footprint spans fewer than 3 cell rows"
        cols = {x + i for x, _, n in runs for i in range(n)}
        sprite_cols = np.nonzero((piece["rgba"][:, :, 3] > 0).any(axis=0))[0]
        sprite_w = int(sprite_cols.max() - sprite_cols.min() + 1)
        assert len(cols) * 4 >= 0.4 * sprite_w, (
            f"{name}: footprint {len(cols) * 4}px wide vs sprite {sprite_w}px")
        low_y = max(y for _, y, _ in runs)
        low_w = sum(n for _, y, n in runs if y == low_y)
        assert low_w * 4 >= 0.6 * len(cols) * 4, f"{name}: lowest footprint row covers {low_w} of {len(cols)} cells"
        alpha = piece["rgba"][:, :, 3] > 0
        for x, y, n in runs:
            for cx in range(x, x + n):
                assert alpha[:, cx * 4:cx * 4 + 4].any(), f"{name}: solid cell ({cx},{y}) has no sprite in its column"

    for name in ("lapida_cruz_h", "lapida_cruz_v", "lapida_caballero_h", "lapida_caballero_v"):
        piece = baker.piece_layout(name)
        assert not piece["foot_runs"], f"{name}: flat floor decoration must stay walkable"
        assert not piece["depth_runs"], f"{name}: flat floor decoration must not occlude actors"

    print("CATHEDRAL_KIT_CONTRACT=PASS physical_props=6 depth=6 planar_footprints=6 flat_decor=4")


if __name__ == "__main__":
    main()
