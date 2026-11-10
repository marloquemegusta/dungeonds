"""Prerender props with the lab (character-parity camera/light) into 1-bit-alpha DS sprites.
usage: python tools/props/prerender_props.py [--settings JSON] [--out DIR] [--raw DIR] [piece ...]
Alpha: the lab's world.png has an opaque black background, so the silhouette comes from
occlusion.png (white = geometry) united with any non-black world pixel.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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

def sprite_depth(depth, y0, scale_y, oy):
    """The lab encodes the ground Y under each surface in raw-render pixels. Resizing the image
    does not touch those values, so convert them to this sprite's local Y (R,G big endian,
    B>=128 marks a surface): the runtime compares them with actor feet in world pixels."""
    d = np.array(depth).astype(np.int32)
    valid = d[..., 2] >= 128
    raw = d[..., 0] * 256 + d[..., 1]
    local = np.clip(np.rint((raw - int(y0)) * scale_y + oy), 0, 65535).astype(np.int32)
    out = np.zeros_like(d)
    out[..., 0] = np.where(valid, local >> 8, 0)
    out[..., 1] = np.where(valid, local & 255, 0)
    out[..., 2] = np.where(valid, 255, 0)
    return Image.fromarray(out.astype(np.uint8), "RGB")

def convex_hull(pts):
    """Monotone chain over integer (x, y) points; returns the hull polygon."""
    pts = sorted(set(map(tuple, pts)))
    if len(pts) < 3: return pts
    def half(seq):
        h = []
        for q in seq:
            while len(h) >= 2 and (h[-1][0]-h[-2][0])*(q[1]-h[-2][1]) - (h[-1][1]-h[-2][1])*(q[0]-h[-2][0]) <= 0:
                h.pop()
            h.append(q)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]

def footprint_from_depth(d, x0, x1, y0, y1, nw, nh, close_px=9, min_cover=0.35):
    """Plan of the piece on the floor, derived from the depth pass instead of collision.png (which
    only marks the 0.30-1.20 m slab and misses seats and low pieces). Two point sets, both at
    raw resolution:
      * occluder pixels (B>=128, surfaces above 0.25 m): (x, ground Y stored in R,G) is a point
        of the real plan (backrest, posts, tall parts);
      * low pixels (silhouette but not occluder, below 0.25 m: legs, seat boards, fallen planks):
        the lab drops their depth, but they sit on the floor, so they are projected straight
        down (ground Y = own Y; error under 0.25 m of height).
    Small holes are closed, the convex hull is filled (no filler rectangle) and the result is reduced with a box filter
    (area coverage >= min_cover) to the sprite content size, not NEAREST."""
    dep = np.array(Image.open(os.path.join(d, "occlusion_depth.png")).convert("RGB")).astype(np.int32)
    valid = dep[..., 2] >= 128
    low = silhouette(d) & ~valid
    m = np.zeros(valid.shape, np.uint8)
    ys, xs = np.nonzero(valid)
    gy = np.clip(dep[..., 0] * 256 + dep[..., 1], int(y0), int(y1) - 1)[valid]
    m[gy, xs] = 255
    # Silhouette-only pixels above the farthest ground point are edge/antialias leftovers of tall
    # parts (finials), not low parts on the floor.
    if len(gy): low[:int(gy.min())] = False
    m[low] = 255
    pad = close_px
    sub = np.pad(m[int(y0):int(y1), int(x0):int(x1)], pad)
    im = Image.fromarray(sub).filter(ImageFilter.MaxFilter(close_px | 1)).filter(ImageFilter.MinFilter(close_px | 1))
    sub = np.array(im)[pad:-pad, pad:-pad] > 127
    # A bench plan is convex: the front edge runs leg to leg. Fill the convex hull.
    py, px = np.nonzero(sub)
    hull = convex_hull(zip(px.tolist(), py.tolist()))
    if len(hull) >= 3:
        hm = Image.new("L", (sub.shape[1], sub.shape[0]), 0)
        ImageDraw.Draw(hm).polygon(hull, fill=255)
        sub = sub | (np.array(hm) > 127)
    cover = np.array(Image.fromarray(sub.astype(np.float32), mode="F").resize((nw, nh), Image.BOX))
    return Image.fromarray(((cover >= min_cover) * 255).astype(np.uint8), "L")

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
    if cfg.get("footprint_from") == "depth":
        fi = footprint_from_depth(d, x0, x1, y0, y1, nw, nh)
        foot = Image.new("L", (cw, ch)); foot.paste(fi, (ox, oy))
    else:
        foot = nearest("collision.png", "L").point(lambda v: 255 if v > 127 else 0)
    depth = sprite_depth(nearest("occlusion_depth.png", "RGB"), y0, nh / bh, oy)

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
            "depth_units": "sprite_px",
            "tiles_8x8_nonempty": tiles, "tiles_8x8_unique": len(uniq)}
    meta_path = os.path.join(od, "meta.json")
    if os.path.exists(meta_path):   # keep keys written by later tools (prop_shadows.py)
        meta = {**json.load(open(meta_path, encoding="utf-8")), **meta}
    with open(meta_path, "w", newline="") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
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
