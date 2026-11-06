"""Calibrates the arena palette against the lab render (writes tools/arena_palette.json).

make_arena_glb.py declares the colours each material should SHOW. The lab lights the
map with a warm key and grades it, so feeding those colours straight into the GLB gives
a muddy brown render. This script closes the loop: it renders (make_arena_glb ->
export_arenas), reads each material's colour back from world.png at the centre of its
faces, and nudges the colour fed to the lab until the render matches the target.

    python.exe tools/calibrate_arena_palette.py [iterations]

Run it again after changing a TARGET colour or the lab lighting. The result is data
(tools/arena_palette.json), the arena build stays deterministic without it: with an empty
palette file the targets are fed to the lab as they are (OPTIONAL step).

v0.3: the targets in make_arena_glb.py are dark on purpose (floor luminance ~35-50/255), so the
calibration only has to match the shared lighting profile (assets/lighting/dungeon_lighting.json)
to a dark look; if a profile makes the render darker than the targets it would raise the base
colours, so the gain is capped (MAX_GAIN) and the floor never goes above the target.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_arena_glb as g  # noqa: E402


MAX_GAIN = 1.25      # per-iteration cap on raising a colour: the dungeon must stay dark


def measure(arena, spec, frame):
    """material -> median rendered sRGB at the centres of its faces."""
    world = np.array(Image.open(ROOT / "assets/sprites/arenas" / arena["name"] / "world.png").convert("RGB"))
    mesh = g.Builder(arena, spec)
    mesh.build()
    fx0, fy0 = mesh.floor[0], mesh.floor[1]
    u_f, v_f = frame["floor_uv"]
    ppm = spec["pixels_per_metre"]
    seen = {}
    for name, pts in mesh.m.samples.items():
        px = []
        for p in pts:
            u, v = g.uv_of(p)
            x = int(np.floor(fx0 + (u - u_f) * ppm))
            y = int(np.floor(fy0 + (v_f - v) * ppm))
            if 0 <= x < world.shape[1] and 0 <= y < world.shape[0] and world[y, x].max() > 4:
                px.append(world[y, x])
        if px:
            seen[name] = np.median(np.array(px), axis=0)
    seen["grout"] = np.median(world[1199, 520:760:8], axis=0)   # last pixel row of a tile row in the start room: grout
    return seen


def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    spec = json.loads(g.SPEC.read_text(encoding="utf-8"))
    arena = spec["arenas"][0]
    targets = g.target_materials(arena["zones"], spec.get("floor_styles"))
    current = {n: {"base": list(b), "emissive": list(e) if e else None}
               for n, (b, e) in g.material_inputs(arena["zones"], spec.get("floor_styles")).items()}
    for it in range(iterations):
        g.PALETTE_JSON.write_text(json.dumps(current, indent=1) + "\n", encoding="utf-8", newline="\n")
        subprocess.run([sys.executable, str(ROOT / "tools/export_arenas.py")], check=True, capture_output=True)
        frame = json.loads((g.OUT_DIR / f"{arena['name']}.frame.json").read_text(encoding="utf-8"))
        seen = measure(arena, spec, frame)
        worst = 0.0
        for name, target in targets.items():
            if name not in seen:
                if name != "side":      # never visible: only edge-on faces use it
                    print("not measurable:", name)
                continue
            err = np.abs(seen[name] - np.array(target)).max()
            worst = max(worst, err)
            ratio = (np.array(target, dtype=float) + 4) / (seen[name] + 4)
            factor = np.clip(ratio, 0.6, MAX_GAIN) ** 0.6
            entry = current[name]
            entry["base"] = [int(round(min(255, max(1, v)))) for v in np.array(entry["base"]) * factor]
            if entry.get("emissive"):
                entry["emissive"] = [int(round(min(255, max(0, v)))) for v in np.array(entry["emissive"]) * factor]
        print(f"iteration {it}: worst channel error {worst:.0f}")
    g.PALETTE_JSON.write_text(json.dumps(current, indent=1) + "\n", encoding="utf-8", newline="\n")
    subprocess.run([sys.executable, str(ROOT / "tools/export_arenas.py")], check=True, capture_output=True)
    frame = json.loads((g.OUT_DIR / f"{arena['name']}.frame.json").read_text(encoding="utf-8"))
    seen = measure(arena, spec, frame)
    for name, target in targets.items():
        if name in seen:
            print(f"{name:22s} target {tuple(target)} got {tuple(int(v) for v in seen[name])}")


if __name__ == "__main__":
    main()
