#!/usr/bin/env python3
"""Keep the cathedral asset masks wired to real ground-plane collision and occlusion."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import bake_cathedral_kit as baker  # noqa: E402


def check_physical(name, piece):
    assert piece["foot_runs"], f"{name}: no collision footprint was baked"
    assert piece["depth_runs"], f"{name}: no sprite occlusion depth was baked"
    assert all(n > 0 and 0 <= x and 0 <= y for x, y, n in piece["foot_runs"]), name
    assert all(x + n <= piece["w"] // 4 and y < piece["h"] // 4
               for x, y, n in piece["foot_runs"]), name
    assert len({y for _, y, _ in piece["foot_runs"]}) > 1, (
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


def check_bench_plan(name, piece):
    """The bench must be a real planta (several cell rows, wide, under the sprite)."""
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


def main():
    for name in ("columna_entera", "relicario", "vela", "santo"):
        check_physical(name, baker.source_layout(name))
    for name in ("banco_entero", "banco_grupo4"):
        piece = baker.source_layout(name)
        check_physical(name, piece)
        check_bench_plan(name, piece)

    # banco_grupo4: four banks, 24 px apart; the footprint must be the union of the four
    # shifted footprints, and the depth must reach the lowest bank's ground.
    bank = baker.source_layout("banco_entero")
    group = baker.source_layout("banco_grupo4")
    one = baker.crop_bench_canvas(bank)
    assert group["h"] == 3 * baker.GROUP_STEP_PX + one["h"], "banco_grupo4 height"

    def cells(runs):
        return {(cx, cy) for cx0, cy, n in runs for cx in range(cx0, cx0 + n)}

    cells_one, cells_group = cells(one["foot_runs"]), cells(group["foot_runs"])
    expected = {(x, y + k * (baker.GROUP_STEP_PX // 4)) for k in range(baker.GROUP_BANKS) for x, y in cells_one}
    assert cells_group == expected, "banco_grupo4 footprint is not the union of the four banks"

    for name in baker.LAPIDA_NAMES:
        piece = baker.source_layout(name)
        assert not piece["foot_runs"], f"{name}: flat floor decoration must stay walkable"
        assert not piece["depth_runs"], f"{name}: flat floor decoration must not occlude actors"

    print("CATHEDRAL_KIT_CONTRACT=PASS physical_props=4 bench_props=2 group_union=ok flat_decor=4")


if __name__ == "__main__":
    main()
