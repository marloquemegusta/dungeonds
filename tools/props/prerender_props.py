"""Prerender props with the lab (character-parity camera/light) into 1-bit-alpha DS sprites.
usage: python tools/props/prerender_props.py [--settings JSON] [--out DIR] [--raw DIR] [piece ...]
Alpha: the lab's world.png has an opaque black background, so the silhouette comes from
occlusion.png (white = geometry) united with any non-black world pixel.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROPS = os.path.join(ROOT, "assets/environment/cathedral/props")
OUT = os.path.join(PROPS, "render")
LAB = os.path.join(ROOT, "tools/lab/export_map_package_headless.cjs")
SETTINGS = os.path.join(ROOT, "tools/props/props_render_settings.json")

def run_lab(name, raw, settings):
    d = os.path.join(raw, name)
    r = subprocess.run(["node", LAB, os.path.join(PROPS, "glb", name + ".glb"), settings, d],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(name + ": " + r.stderr[-500:])
    return d

def silhouette(d):
    world = np.array(Image.open(os.path.join(d, "world.png")).convert("RGB"))
    occ = np.array(Image.open(os.path.join(d, "occlusion.png")).convert("L")) > 127
    return occ | (world.sum(2) > 0)

def process(name, cfg, d, out_root):
    mask = silhouette(d)
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    bw, bh = x1 - x0, y1 - y0
    tw = cfg["target_width"]
    if "exact_px" in cfg:          # optional per-piece exact content box (non-uniform resize)
        nw, nh = cfg["exact_px"]; sc = nw / bw
        cw, ch = cfg.get("canvas_px", [-(-nw // 8) * 8, -(-nh // 8) * 8])
    else:
        sc = tw / bw
        nw, nh = tw, max(1, round(bh * sc))
        cw, ch = -(-nw // 8) * 8, -(-nh // 8) * 8
    ox, oy = (cw - nw) // 2, ch - nh        # ground contact (lowest row) on the bottom edge

    world = np.array(Image.open(os.path.join(d, "world.png")).convert("RGB"))[y0:y1, x0:x1].astype(np.float32)
    m = mask[y0:y1, x0:x1].astype(np.float32)
    # premultiplied resize so the black background does not bleed into edges
    chans = []
    for c in range(3):
        im = Image.fromarray(world[..., c] * m, mode="F").resize((nw, nh), Image.LANCZOS)
        chans.append(np.array(im))
    am = np.array(Image.fromarray(m, mode="F").resize((nw, nh), Image.BOX))
    a = am >= 0.5
    rgb = np.stack(chans, -1) / np.maximum(am[..., None], 1e-3)
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba = np.zeros((nh, nw, 4), np.uint8)
    rgba[..., :3] = rgb * a[..., None]
    rgba[..., 3] = a * 255
    color = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); color.paste(Image.fromarray(rgba), (ox, oy))

    def nearest(fn, mode):
        im = Image.open(os.path.join(d, fn)).convert(mode).crop((int(x0), int(y0), int(x1), int(y1)))
        im = im.resize((nw, nh), Image.NEAREST)
        out = Image.new(mode, (cw, ch)); out.paste(im, (ox, oy)); return out
    foot = nearest("collision.png", "L").point(lambda v: 255 if v > 127 else 0)
    depth = nearest("occlusion_depth.png", "RGB")

    od = os.path.join(out_root, name); os.makedirs(od, exist_ok=True)
    color.save(os.path.join(od, "color.png")); foot.save(os.path.join(od, "footprint.png"))
    depth.save(os.path.join(od, "depth.png"))
    arr = np.array(color); tiles = 0; uniq = set()
    for ty in range(ch // 8):
        for tx in range(cw // 8):
            t = arr[ty*8:ty*8+8, tx*8:tx*8+8]
            if t[..., 3].any():
                tiles += 1; uniq.add(hashlib.md5(t.tobytes()).hexdigest())
    meta = {"piece": name, "size_px": [cw, ch], "content_px": [nw, nh], "target_width": tw,
            "scale_factor": sc, "source_render_px": [int(bw), int(bh)], "yaw": cfg["yaw"],
            "tiles_8x8_nonempty": tiles, "tiles_8x8_unique": len(uniq)}
    json.dump(meta, open(os.path.join(od, "meta.json"), "w", newline=""), indent=2)
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default=SETTINGS)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--raw"); ap.add_argument("--skip-lab", action="store_true")
    ap.add_argument("pieces", nargs="*"); a = ap.parse_args()
    cfg = json.load(open(os.path.join(ROOT, "tools/props/props.json")))
    names = a.pieces or list(cfg)
    raw = a.raw or os.path.join(tempfile.gettempdir(), "props_raw")
    os.makedirs(raw, exist_ok=True)
    if a.skip_lab: dirs = {n: os.path.join(raw, n) for n in names}
    else:
        with ThreadPoolExecutor(3) as ex: dirs = dict(zip(names, ex.map(lambda n: run_lab(n, raw, a.settings), names)))
    for n in names:
        m = process(n, cfg[n], dirs[n], a.out)
        print(n, m["size_px"], "tiles", m["tiles_8x8_nonempty"], "unique", m["tiles_8x8_unique"], "scale %.4f" % m["scale_factor"])

if __name__ == "__main__": main()
