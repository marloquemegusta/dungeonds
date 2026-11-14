#!/usr/bin/env python3
"""Headless lab pre-render of the Sacred Heart model for the HUD hearts (C2 legibility).

  python tools/hud/prerender_hud_heart.py [model.fbx] [out.png]

Uses tools/lab/export_map_package_headless.cjs with --legibility c2, neutral lighting,
and front-on orthographic camera (elevation 0). Combines world.png and occlusion.png into
an RGBA PNG with transparent background.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "assets" / "models" / "hud" / "sacred_heart" / "tripo_convert_d96dac8c-dc43-495d-9495-f318e45fae13.fbx"
DEFAULT_OUT = ROOT / "assets" / "sprites" / "hud" / "source" / "heart_render.png"
LAB = ROOT / "tools" / "lab" / "export_map_package_headless.cjs"


def main():
    model = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MODEL
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)

    settings = {
        "width": 256,
        "cameraElevationDegrees": 0,
        "contrast": 1.0,
        "saturation": 1.0,
        "brightness": 1,
        "legibility": "c2",
        "lighting": {"preset": "neutral"},
        "waitTextures": True,
        "waitTexturesMs": 3000,
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg_path = tmp_path / "settings.json"
        out_dir = tmp_path / "lab_out"
        cfg_path.write_text(json.dumps(settings), encoding="utf-8")
        r = subprocess.run(
            ["node", str(LAB), str(model), str(cfg_path), str(out_dir), "--legibility", "c2"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Lab render failed:\n{r.stdout}\n{r.stderr}")

        world = np.array(Image.open(out_dir / "world.png").convert("RGB"))
        occ = np.array(Image.open(out_dir / "occlusion.png").convert("L")) > 127
        mask = occ | (world.sum(2) > 0)
        rgba = np.zeros((world.shape[0], world.shape[1], 4), dtype=np.uint8)
        rgba[..., :3] = world * mask[..., None]
        rgba[..., 3] = mask.astype(np.uint8) * 255
        Image.fromarray(rgba, "RGBA").save(out)
        print("RENDERED (lab C2)", out, rgba.shape[1], "x", rgba.shape[0])


if __name__ == "__main__":
    main()
