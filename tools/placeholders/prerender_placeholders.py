#!/usr/bin/env python3
"""Headless lab pre-render of the placeholder boxes (C2 legibility, prop camera).

  python tools/placeholders/prerender_placeholders.py [name ...]

Reads assets/models/placeholders/<name>.glb and writes assets/sprites/placeholders/source/<name>.png
(RGBA, transparent background). Camera elevation, lighting and render settings are the props ones
(tools/props/props_render_settings.json); the width is the HUD-style 256 px so the bake downsizes.
Lab: tools/lab/export_map_package_headless.cjs (Node + Playwright, headless Chromium).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "assets" / "models" / "placeholders"
SRC = ROOT / "assets" / "sprites" / "placeholders" / "source"
LAB = ROOT / "tools" / "lab" / "export_map_package_headless.cjs"
PROPS_SETTINGS = ROOT / "tools" / "props" / "props_render_settings.json"
NAMES = ["runa_xp", "orbe_vida", "orbe_mana", "maldicion", "aliado_marca"]


def render_settings():
    s = json.loads(PROPS_SETTINGS.read_text(encoding="utf-8"))
    s["width"] = 256
    s["legibility"] = "c2"
    s["lighting"] = {"preset": "neutral"}
    # The neutral preset washes the flat colors out (dark red came back pink). Brightness 0.6 and
    # saturation 1.8 bring the faces back to the intended muted hue (checked on orbe_vida).
    s["brightness"] = 0.6
    s["saturation"] = 1.8
    return s


def render_one(name, settings):
    model = MODELS / (name + ".glb")
    out = SRC / (name + ".png")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg = tmp_path / "settings.json"
        out_dir = tmp_path / "lab_out"
        cfg.write_text(json.dumps(settings), encoding="utf-8")
        r = subprocess.run(
            ["node", str(LAB), str(model), str(cfg), str(out_dir), "--legibility", "c2"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Lab render failed for {name}:\n{r.stdout}\n{r.stderr}")
        world = np.array(Image.open(out_dir / "world.png").convert("RGB"))
        occ = np.array(Image.open(out_dir / "occlusion.png").convert("L")) > 127
        mask = occ | (world.sum(2) > 0)
        rgba = np.zeros((world.shape[0], world.shape[1], 4), dtype=np.uint8)
        rgba[..., :3] = world * mask[..., None]
        rgba[..., 3] = mask.astype(np.uint8) * 255
        Image.fromarray(rgba, "RGBA").save(out)
    ys, xs = np.nonzero(mask)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None
    print(f"RENDERED {name} {rgba.shape[1]}x{rgba.shape[0]} bbox={bbox} px={int(mask.sum())}")


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or NAMES
    settings = render_settings()
    for name in names:
        render_one(name, settings)


if __name__ == "__main__":
    main()
