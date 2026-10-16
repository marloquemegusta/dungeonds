#!/usr/bin/env python3
"""Compare the Blender Shader Lab and the 3JS sprite lab on the same FBX/clip.

Usage:
  python tools/lab/compare_labs.py [--fbx assets/characters/charger/Run.fbx]
      [--clip mixamo.com] [--size 48] [--out walkthroughs/lab3js-blender-parity/assets/<tag>]
      [--reuse-blender DIR]   # reuse an existing Blender 'processed' dir

Writes metrics.json and side_by_side.png into --out. Browser runs headless only.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
BLENDER_ACTION = "Armature|mixamo.com|Layer0"


def render_blender(fbx, size, elevation, action):
    import shader_lab_server as srv
    res = srv.execute_render_job({
        "custom_fbx": str(fbx), "resolution_px": size, "elevation": elevation,
        "azimuth": 45.0, "samples": 16, "outline": True, "action_name": action,
    })
    return Path(srv.RUNS_DIR) / res["job_id"] / "processed"


def render_3js(fbx, size, elevation, clip, frames=8):
    from playwright.sync_api import sync_playwright
    html = (HERE / "FBX-Web-Renderer-offline.html").resolve().as_uri()
    with sync_playwright() as p:
        launch_args = ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
        try:
            browser = p.chromium.launch(headless=True, args=launch_args)
        except Exception:
            import glob
            cands = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-*\*\chrome-headless-shell.exe")))
            if not cands:
                raise
            browser = p.chromium.launch(headless=True, executable_path=cands[-1], args=launch_args)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(html)
        page.wait_for_function("$.renderer && !$.renderer.getContext().isContextLost()", timeout=60000)
        page.set_input_files("#fbxInput", str(fbx))
        page.wait_for_function("!document.getElementById('btnRender').disabled", timeout=60000)
        page.evaluate("""([clip]) => {
            const s = document.getElementById('animSelect');
            const o = [...s.options].find(o => o.textContent.includes(clip));
            if (o) { s.value = o.value; s.dispatchEvent(new Event('change')); }
        }""", [clip])
        page.evaluate("""([size, elev, frames]) => {
            const set = (id, v) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event('input', {bubbles: true})); };
            set('resolution', size); set('frameCount', frames); set('elevation', elev);
            set('contrast', 1.15); set('saturation', 1.15);
        }""", [size, elevation, frames])
        page.click("#btnRender")
        page.wait_for_function(
            f"window.__spriteLab.frames.length === 8 * {frames} && !document.getElementById('btnRender').disabled",
            timeout=300000)
        data = page.evaluate("""() => window.__spriteLab.frames.map(f => {
            let s = ''; const a = f.pixels; for (let i = 0; i < a.length; i += 8192) s += String.fromCharCode.apply(null, a.subarray(i, i + 8192));
            return {w: f.width, h: f.height, b64: btoa(s)};
        })""")
        browser.close()
    if errors:
        print("pageerrors:", errors[:3])
    out = {}
    for i, f in enumerate(data):
        arr = np.frombuffer(base64.b64decode(f["b64"]), dtype=np.uint8).reshape(f["h"], f["w"], 4)
        out[(i // frames, i % frames)] = arr
    return out


def load_blender(proc_dir, frames=8):
    out = {}
    for d in range(8):
        for f in range(frames):
            out[(d, f)] = np.array(Image.open(Path(proc_dir) / f"d{d:02d}_f{f:03d}.png").convert("RGBA"))
    return out


def mask(a):
    return a[..., 3] > 0


def bbox(m):
    ys, xs = np.where(m)
    if len(xs) == 0:
        return (0, 0, 0, 0, 0.0, 0.0)
    return (xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1, xs.mean(), ys.mean())


def iou(a, b):
    ma, mb = mask(a), mask(b)
    u = (ma | mb).sum()
    return float((ma & mb).sum() / u) if u else 1.0


def lum(a):
    m = mask(a)
    if not m.any():
        return 0.0
    rgb = a[..., :3][m].astype(np.float64)
    return float((0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2]).mean())


def side_by_side(js, bl, frames, path, scale=4):
    size = js[(0, 0)].shape[0]
    bg = np.array([16, 14, 20, 255], dtype=np.uint8)
    cell = size * scale
    W = 2 * cell + 30 + 40
    img = Image.new("RGBA", (W, 8 * (cell + 6)), (16, 14, 20, 255))
    for d in range(8):
        for col, src in enumerate((js, bl)):
            a = src[(d, 0)].copy()
            a[a[..., 3] == 0] = bg
            im = Image.fromarray(a, "RGBA").resize((cell, cell), Image.NEAREST)
            img.paste(im, (40 + col * (cell + 30), d * (cell + 6)))
    img.convert("RGB").save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fbx", default="assets/characters/charger/Run.fbx")
    ap.add_argument("--clip", default="mixamo.com")
    ap.add_argument("--size", type=int, default=48)
    ap.add_argument("--elevation", type=float, default=35.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reuse-blender", default=None)
    args = ap.parse_args()
    fbx = (ROOT / args.fbx).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    bl_dir = Path(args.reuse_blender) if args.reuse_blender else render_blender(fbx, args.size, args.elevation, BLENDER_ACTION)
    bl = load_blender(bl_dir)
    js = render_3js(fbx, args.size, args.elevation, args.clip)
    frames = 8
    per = []
    for d in range(8):
        for f in range(frames):
            a, b = js[(d, f)], bl[(d, f)]
            ba, bb = bbox(mask(a)), bbox(mask(b))
            per.append({"d": d, "f": f, "iou": iou(a, b),
                        "js_box": [int(ba[2]), int(ba[3])], "bl_box": [int(bb[2]), int(bb[3])],
                        "centroid_dx": float(ba[4] - bb[4]), "centroid_dy": float(ba[5] - bb[5]),
                        "lum_js": lum(a), "lum_bl": lum(b)})
    # Direction cross-matrix on frame 0..frames-1 mean IoU: reveals rotation offsets.
    cross = [[float(np.mean([iou(js[(i, f)], bl[(j, f)]) for f in range(frames)])) for j in range(8)] for i in range(8)]
    best = [int(np.argmax(r)) for r in cross]
    summary = {
        "mean_iou": float(np.mean([p["iou"] for p in per])),
        "mean_iou_by_dir": [float(np.mean([p["iou"] for p in per if p["d"] == d])) for d in range(8)],
        "best_blender_dir_for_js_dir": best,
        "mean_js_box": [float(np.mean([p["js_box"][0] for p in per])), float(np.mean([p["js_box"][1] for p in per]))],
        "mean_bl_box": [float(np.mean([p["bl_box"][0] for p in per])), float(np.mean([p["bl_box"][1] for p in per]))],
        "mean_centroid_dx": float(np.mean([p["centroid_dx"] for p in per])),
        "mean_centroid_dy": float(np.mean([p["centroid_dy"] for p in per])),
        "mean_lum_js": float(np.mean([p["lum_js"] for p in per])),
        "mean_lum_bl": float(np.mean([p["lum_bl"] for p in per])),
        "cross_iou": cross, "blender_dir": str(bl_dir),
    }
    (out / "metrics.json").write_text(json.dumps({"summary": summary, "frames": per}, indent=1))
    side_by_side(js, bl, frames, out / "side_by_side.png")
    for k in ("mean_iou", "mean_iou_by_dir", "best_blender_dir_for_js_dir", "mean_js_box", "mean_bl_box",
              "mean_centroid_dx", "mean_centroid_dy", "mean_lum_js", "mean_lum_bl"):
        print(k, summary[k])


if __name__ == "__main__":
    main()
