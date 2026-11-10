#!/usr/bin/env python3
"""Keep the cathedral asset masks wired to real ground-plane collision and occlusion."""
import sys
from pathlib import Path

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

    for name in ("lapida_cruz_h", "lapida_cruz_v", "lapida_caballero_h", "lapida_caballero_v"):
        piece = baker.piece_layout(name)
        assert not piece["foot_runs"], f"{name}: flat floor decoration must stay walkable"
        assert not piece["depth_runs"], f"{name}: flat floor decoration must not occlude actors"

    print("CATHEDRAL_KIT_CONTRACT=PASS physical_props=6 depth=6 planar_footprints=6 flat_decor=4")


if __name__ == "__main__":
    main()
