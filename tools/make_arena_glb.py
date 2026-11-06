"""Builds the arena models (assets/arenas/arenas.json -> <name>.glb + <name>.frame.json).

The lab (tools/lab/FBX-Web-Renderer-parity.js, renderMap) frames a map model by
the projection of the model's WORLD axis-aligned bounding box, with the camera
at azimuth 45 deg / elevation 30 deg. A room whose walls must run horizontally
and vertically on screen is therefore rotated 45 deg about Y in world space,
which makes its AABB (and so the lab render) much larger than the arena image.
The package is rendered big at exactly 40.42 px/m and cropped to the arena image
size by tools/export_arenas.py. To make the crop land on the 4 px collision grid
and the scale exactly 40.42 px/m, each model carries one zero-area triangle
("frame" primitive) that only stretches the AABB; it draws no pixel and is
ignored by the collision/occlusion passes (area <= 1e-6).

Look (dungeon + cyberpunk accents), all by geometry and flat colours, no textures:
  * floor: 32x16 px tiles in three tones per zone (checker / rows / scatter) with
    1 px grout, thresholds in the doorways;
  * walls: front face split into flush bands (plinth, body, neon strip, trim,
    cornice) with a neon colour per zone and door frames at the wall ends;
  * pillars: same bands plus a glowing cap.
Decoration never protrudes from the spec footprints: bands are flush with the face,
the only raised pieces are 1-2 cm floor quads and the pillar cap, so the lab's
collision (0.30-1.20 m slab) and occlusion (>0.25 m) passes see the spec geometry.
All patterns are periodic on the 8 px tile grid so the baker's tile budget holds.

Usage: python.exe tools/make_arena_glb.py   (writes the .glb and a .frame.json)
Units are metres. Model axes: screen-right R, screen-down-on-ground D, up Y.
"""
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "assets/arenas/arenas.json"
OUT_DIR = ROOT / "assets/models/environment/arenas"

S = math.sqrt(0.5)
ELEV = math.radians(30.0)
C_E, S_E = math.cos(ELEV), math.sin(ELEV)
# Lab camera (AZIMUTH = pi/4): right = (-S,0,-S), up = (-S*sinE, cosE, S*sinE).
RIGHT = (-S, 0.0, -S)
DOWN = (S, 0.0, -S)  # ground direction that points down the screen

WALL_T = 0.34
SLAB_T = 0.25
# The lab marks a collision cell for every cell an obstacle edge passes through,
# and an edge exactly on a 4 px cell border marks the cell on the wrong side.
# Obstacle faces are therefore moved a hair (0.1 px) off the spec border: blocks shrink
# and the boundary walls retreat outwards, so the blocked cells land on the spec rect.
# The inset must stay well below 1 px: a wider one leaves a sliver of floor beside every
# wall and pillar, and each sliver multiplies the distinct 8x8 tiles the baker needs.
INSET_PX = 0.1
# A block side that lies flat against a wall/boundary that covers the whole side is
# pushed this far into it instead of being inset (otherwise a 2 px slit would show).
OVERLAP_PX = 6.0
TILE_W, TILE_H = 32, 16          # floor tile on screen (32x32 ground px)
FLOOR_LIFT = 0.01                # tiles above the slab top, thresholds above the tiles
THRESHOLD_LIFT = 0.02


def srgb(r, g, b):
    """sRGB 0..255 -> linear glTF factor."""
    return tuple(round(min(1.0, max(0.0, v / 255.0)) ** 2.2, 5) for v in (r, g, b))


def scale(rgb, k):
    return tuple(min(255, int(round(v * k))) for v in rgb)


# The palette below is what the render should SHOW (sRGB). The lab lights the map with a
# strong warm key and grades it (contrast, saturation), so the colours written into the
# GLB are not these: tools/calibrate_arena_palette.py measures the render and stores the
# colours to feed the lab in tools/arena_palette.json (material -> base / emissive).
PALETTE_JSON = ROOT / "tools/arena_palette.json"
# One uniform warm accent (DESIGN.md 6): dim amber trims, no per-room colours. Dark dungeon: the
# palette targets keep the floor around luminance 35-50/255 (calibrate_arena_palette.py never has
# to push brightness up, see its docstring).
ACCENTS = {"amber": (150, 100, 44)}
DEEP = {"amber": (255, 175, 40)}
GROUT = (26, 27, 36)
THRESHOLDS = {"amber": (70, 52, 38)}
WALL = {
    "plinth": (36, 38, 50), "body": (24, 25, 36), "cornice": (50, 54, 70),
    "top": (20, 22, 30), "side": (24, 25, 36), "slab": (20, 19, 28),
    "pillar": (38, 42, 58), "pillar_top": (34, 37, 50),
}
# materials seen as an emissive colour (target is the colour on screen)
EMISSIVE_PREFIXES = ("neon_", "dneon_", "glow_")
DEFAULT_STYLES = {"plain": {"tones": [[44, 47, 58], [38, 41, 52], [41, 44, 55]], "shade": 1.0}}


def target_materials(zones, styles=None):
    """material name -> target sRGB as seen in the render (insertion order is stable)."""
    styles = styles or DEFAULT_STYLES
    t = {"grout": GROUT}
    t.update(WALL)
    for acc, rgb in ACCENTS.items():
        t[f"neon_{acc}"] = rgb
        t[f"dneon_{acc}"] = rgb
        t[f"glow_{acc}"] = rgb
        t[f"trim_{acc}"] = scale(DEEP[acc], 0.22)
        t[f"frame_{acc}"] = scale(DEEP[acc], 0.30)
        t[f"thresh_{acc}"] = THRESHOLDS[acc]
    for name, st in styles.items():
        for k, tone in enumerate(st["tones"]):
            t[f"floor_{name}_{k}"] = scale(tuple(tone), st.get("shade", 1.0))
    return t


def is_emissive(name):
    return name.startswith(EMISSIVE_PREFIXES)


def material_inputs(zones, styles=None):
    """material name -> (base sRGB, emissive sRGB or None) fed to the lab."""
    stored = json.loads(PALETTE_JSON.read_text(encoding="utf-8")) if PALETTE_JSON.exists() else {}
    out = {}
    for name, target in target_materials(zones, styles).items():
        if name in stored:
            e = stored[name]
            out[name] = (tuple(e["base"]), tuple(e["emissive"]) if e.get("emissive") else None)
        elif is_emissive(name):
            out[name] = (scale(target, 0.3), target)
        else:
            out[name] = (target, None)
    return out


def build_materials(zones, styles=None):
    """name -> (linear base colour, linear emissive or None)."""
    mats = {"frame": ((0.0, 0.0, 0.0), None)}
    for name, (base, emis) in material_inputs(zones, styles).items():
        mats[name] = (srgb(*base), srgb(*emis) if emis else None)
    return mats


def world(u, w, y):
    """room coords (u right, w ground-down on screen, y up), metres -> xyz."""
    return (u * RIGHT[0] + w * DOWN[0], y, u * RIGHT[2] + w * DOWN[2])


def uv_of(p):
    """lab projection of an xyz point: (u along right, v along camera up)."""
    return (p[0] * RIGHT[0] + p[2] * RIGHT[2],
            -S * S_E * p[0] + C_E * p[1] + S * S_E * p[2])


class Mesh:
    def __init__(self):
        self.prims = {}  # material name -> (positions, normals, indices)
        self.samples = {}  # material name -> face centres (xyz), for tools/calibrate_arena_palette.py

    def tri(self, mat, a, b, c, centre):
        pos, nor, idx = self.prims.setdefault(mat, ([], [], []))
        e1 = [b[i] - a[i] for i in range(3)]
        e2 = [c[i] - a[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2],
             e1[0] * e2[1] - e1[1] * e2[0])
        mid = [(a[i] + b[i] + c[i]) / 3 - centre[i] for i in range(3)]
        if sum(n[i] * mid[i] for i in range(3)) < 0:
            b, c = c, b
            n = (-n[0], -n[1], -n[2])
        ln = math.sqrt(sum(v * v for v in n)) or 1.0
        n = tuple(v / ln for v in n)
        base = len(pos)
        for p in (a, b, c):
            pos.append(p)
            nor.append(n)
        idx.extend([base, base + 1, base + 2])

    def quad(self, mat, pts, centre):
        if len(self.samples.setdefault(mat, [])) < 60:
            self.samples[mat].append(tuple(sum(p[i] for p in pts) / 4 for i in range(3)))
        self.tri(mat, pts[0], pts[1], pts[2], centre)
        self.tri(mat, pts[0], pts[2], pts[3], centre)

    # --- axis-aligned faces in room coordinates -----------------------------------
    def top(self, mat, u0, w0, u1, w1, y):
        pts = [world(u0, w0, y), world(u1, w0, y), world(u1, w1, y), world(u0, w1, y)]
        self.quad(mat, pts, world((u0 + u1) / 2, (w0 + w1) / 2, y - 1))

    def face_w(self, mat, u0, u1, w, y0, y1, outward):
        """Face on the plane w = const (front faces look down the screen, outward=+1)."""
        pts = [world(u0, w, y0), world(u1, w, y0), world(u1, w, y1), world(u0, w, y1)]
        self.quad(mat, pts, world((u0 + u1) / 2, w - outward, (y0 + y1) / 2))

    def face_u(self, mat, u, w0, w1, y0, y1, outward):
        pts = [world(u, w0, y0), world(u, w1, y0), world(u, w1, y1), world(u, w0, y1)]
        self.quad(mat, pts, world(u - outward, (w0 + w1) / 2, (y0 + y1) / 2))


def write_glb(path, mesh, mats):
    """Minimal GLB 2.0: one node, one mesh, one primitive per material."""
    blob = bytearray()
    views, accessors, prims, materials = [], [], [], []
    for mi, name in enumerate(sorted(mesh.prims)):
        pos, nor, idx = mesh.prims[name]
        colour, emissive = mats[name]
        m = {"name": name, "pbrMetallicRoughness": {
            "baseColorFactor": [*colour, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.9}}
        if emissive:
            m["emissiveFactor"] = list(emissive)
        materials.append(m)
        entry = {}
        for acc_name, data, ctype, fmt, target in (
                ("POSITION", pos, 5126, "f", 34962), ("NORMAL", nor, 5126, "f", 34962),
                ("indices", idx, 5125, "I", 34963)):
            flat = [v for item in data for v in (item if isinstance(item, tuple) else (item,))]
            raw = struct.pack(f"<{len(flat)}{fmt}", *flat)
            while len(blob) % 4:
                blob.append(0)
            views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(raw), "target": target})
            blob += raw
            acc = {"bufferView": len(views) - 1, "componentType": ctype,
                   "count": len(data), "type": "VEC3" if acc_name != "indices" else "SCALAR"}
            if acc_name == "POSITION":
                acc["min"] = [min(p[i] for p in pos) for i in range(3)]
                acc["max"] = [max(p[i] for p in pos) for i in range(3)]
            accessors.append(acc)
            entry[acc_name] = len(accessors) - 1
        prims.append({"attributes": {"POSITION": entry["POSITION"], "NORMAL": entry["NORMAL"]},
                      "indices": entry["indices"], "material": mi})
    gltf = {"asset": {"version": "2.0", "generator": "tools/make_arena_glb.py"},
            "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "arena"}],
            "meshes": [{"primitives": prims}], "materials": materials,
            "bufferViews": views, "accessors": accessors,
            "buffers": [{"byteLength": len(blob)}]}
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    blob += b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    out = (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
           + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob))
    path.write_bytes(out)


def solve_frame(room_pts, floor_uv, ppm, size, floor_xy):
    """Pick lab render size, crop offset and the zero-area helper that stretches
    the world AABB so the image-sized crop sits on the 4 px grid at exactly ppm.

    The helper's top is raised until the model height is a whole number of image
    pixels, which makes the vertical scale exactly ppm too (otherwise the lab
    rounds the render height and the scale drifts by up to 0.5 px per render).

    The conditions on (cx, cy) are monotone: lo <= hi splits into bounds that depend on cx only,
    on cy only, and one joint condition that grows with both, so the smallest admissible cx and
    cy (multiples of 4) decide each candidate map_w in O(1)."""
    iw, ih = size
    fx0, fy0 = floor_xy
    xs, ys, zs = zip(*room_pts)
    x0r, x1r, y0r, y1r, z0r, z1r = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    y1r = y0r + math.ceil((y1r - y0r) * C_E * ppm - 1e-6) / (C_E * ppm)
    u_f, v_f = floor_uv  # floor rect top-left corner in lab uv
    dy = y1r - y0r

    def a_of(cx, proj_w):
        return -(u_f - (fx0 + cx) / ppm + proj_w) / S

    def b_of(cx):
        return -(u_f - (fx0 + cx) / ppm) / S

    def c_of(cy, pv):
        return (v_f + (fy0 + cy) / pv - C_E * y1r) / (S * S_E)

    best = None
    for map_w in range(max(448, (iw + 15) // 16 * 16), 16385, 16):
        proj_w = map_w / ppm
        proj_h = S_E * proj_w + C_E * dy
        map_h = round(map_w * proj_h / proj_w)
        if map_h < ih:
            continue
        pv = map_h / proj_h
        # cx: b_ >= z1r + x1r needs a large enough cx, a_ <= x0r + z0r a small enough one
        cx = 0
        while cx <= map_w - iw and b_of(cx) < z1r + x1r:
            cx += 4
        if cx > map_w - iw or a_of(cx, proj_w) - z0r > x0r:
            continue
        cy = 0
        while cy <= map_h - ih and z1r - c_of(cy, pv) > x0r:
            cy += 4
        if cy > map_h - ih:
            continue
        a_, b_, c_ = a_of(cx, proj_w), b_of(cx), c_of(cy, pv)
        lo = max(a_ - z0r, z1r - c_)
        hi = min(x0r, b_ - c_ - x1r)
        if lo <= hi:
            t = (lo + hi) / 2
            best = dict(map_w=map_w, map_h=map_h, cx=cx, cy=cy,
                        p_min=(t, y0r, a_ - t), p_max=(b_ - c_ - t, y1r, c_ + t))
            break
    if best is None:
        raise SystemExit("no frame solution")
    return best


def normalize_blocks(blocks):
    """Splits blocks so that each side is either fully against one neighbour or fully free:
    a block side that touches several neighbours (or part neighbour, part floor) is cut at the
    neighbours' edges. side_extent can then treat every piece side as a unit (no slits between
    adjacent solid pieces)."""
    pieces = [dict(b) for b in blocks]
    while True:
        out, changed = [], False
        for b in pieces:
            x0, y0, x1, y1 = b["rect"]
            cx, cy = {x0, x1}, {y0, y1}
            for o in pieces:
                if o is b:
                    continue
                ox0, oy0, ox1, oy1 = o["rect"]
                if (oy1 == y0 or oy0 == y1) and ox0 < x1 and ox1 > x0:
                    cx |= {ox0, ox1}
                if (ox1 == x0 or ox0 == x1) and oy0 < y1 and oy1 > y0:
                    cy |= {oy0, oy1}
            xs = sorted(c for c in cx if x0 <= c <= x1)
            ys = sorted(c for c in cy if y0 <= c <= y1)
            if len(xs) > 2 or len(ys) > 2:
                changed = True
            for ya, yb in zip(ys, ys[1:]):
                for xa, xb in zip(xs, xs[1:]):
                    nb = dict(b)
                    nb["rect"] = [xa, ya, xb, yb]
                    out.append(nb)
        pieces = out
        if not changed:
            return pieces


class Builder:
    def __init__(self, arena, spec):
        self.arena = arena
        self.ppm = spec["pixels_per_metre"]
        self.size = tuple(arena.get("image", spec["image"]))
        self.floor = arena.get("floor", spec["floor"])["rect"]
        self.wall_h = spec["boundary_wall_height_m"]
        self.zones = arena["zones"]
        self.doors = arena.get("doors", [])
        self.blocks = normalize_blocks(arena["blocks"])
        self.styles = spec.get("floor_styles")
        self.pxv = C_E * self.ppm            # image px per metre of height
        self.e = INSET_PX / self.ppm         # horizontal inset in metres
        self.eg = INSET_PX / (S_E * self.ppm)
        self.m = Mesh()

    # image px -> room metres
    def u(self, x):
        return (x - self.floor[0]) / self.ppm

    def w(self, y):
        return (y - self.floor[1]) / (S_E * self.ppm)

    def zone_at(self, x, y):
        for z in self.zones:
            x0, y0, x1, y1 = z["rect"]
            if x0 <= x < x1 and y0 <= y < y1:
                return z
        return min(self.zones, key=lambda z: abs((z["rect"][0] + z["rect"][2]) / 2 - x)
                   + abs((z["rect"][1] + z["rect"][3]) / 2 - y))

    # ---- front-face facade ------------------------------------------------------
    def facade(self, xa, xb, height_m, bands, accent_at, frame_ranges=()):
        """Flush cells (ua, ub, ya, yb, material) for a front face spanning image
        x in [xa, xb]. bands = [(y0_px, y1_px, kind)]; accent kinds follow the zone."""
        cuts = {xa, xb}
        for z in self.zones:
            for edge in (z["rect"][0], z["rect"][2]):
                if xa < edge < xb:
                    cuts.add(edge)
        for f0, f1 in frame_ranges:
            for edge in (f0, f1):
                if xa < edge < xb:
                    cuts.add(edge)
        cuts = sorted(cuts)
        cells = []
        for s0, s1 in zip(cuts, cuts[1:]):
            mid = (s0 + s1) / 2
            acc = accent_at(mid)
            framed = any(f0 <= mid < f1 for f0, f1 in frame_ranges)
            for i, (b0, b1, kind) in enumerate(bands):
                if kind in ("neon", "trim"):
                    mat = f"{kind}_{acc}"
                elif kind == "body" and framed:
                    mat = f"frame_{acc}"
                else:
                    mat = kind
                ya = b0 / self.pxv
                yb = height_m if i == len(bands) - 1 else b1 / self.pxv
                cells.append((self.u(s0), self.u(s1), ya, yb, mat))
        return cells

    def box(self, u0, w0, u1, w1, y0, y1, top, front):
        """Solid with a split front face; `front` is a material name or a cell list."""
        m = self.m
        m.top(top, u0, w0, u1, w1, y1)
        m.face_w("side", u0, u1, w0, y0, y1, -1)
        if isinstance(front, str):
            m.face_w(front, u0, u1, w1, y0, y1, +1)
        else:
            if y0 < front[0][2]:
                m.face_w("side", u0, u1, w1, y0, front[0][2], +1)
            for ua, ub, ya, yb, mat in front:
                m.face_w(mat, ua, ub, w1, ya, yb, +1)
        m.face_u("side", u0, w0, w1, y0, y1, -1)
        m.face_u("side", u1, w0, w1, y0, y1, +1)

    # ---- floor --------------------------------------------------------------------
    def floor_tiles(self):
        fx0, fy0, fx1, fy1 = self.floor
        m = self.m
        W, D = self.u(fx1), self.w(fy1)
        e, eg = self.e, self.eg
        # slab: grout-coloured top, dark edge
        m.top("grout", -e, -eg, W + e, D, 0.0)
        m.face_w("slab", -e, W + e, D, -SLAB_T, 0.0, +1)
        m.face_w("side", -e, W + e, -eg, -SLAB_T, 0.0, -1)
        m.face_u("side", -e, -eg, D, -SLAB_T, 0.0, -1)
        m.face_u("side", W + e, -eg, D, -SLAB_T, 0.0, +1)
        for z in self.zones:
            zx0, zy0, zx1, zy1 = z["rect"]
            zx0, zy0 = max(zx0, fx0), max(zy0, fy0)
            zx1, zy1 = min(zx1, fx1), min(zy1, fy1)
            for j in range(zy0 // TILE_H, (zy1 + TILE_H - 1) // TILE_H):
                for i in range(zx0 // TILE_W, (zx1 + TILE_W - 1) // TILE_W):
                    x0, x1 = max(zx0, i * TILE_W), min(zx1, (i + 1) * TILE_W)
                    y0, y1 = max(zy0, j * TILE_H), min(zy1, (j + 1) * TILE_H)
                    if x1 - x0 < 2 or y1 - y0 < 2:
                        continue
                    st = (self.styles or {}).get(z.get("style"), {})
                    k = tone_index(st.get("pattern", z.get("pattern", "checker")), i, j)
                    m.top(f"floor_{z['style']}_{k}", self.u(x0), self.w(y0),
                          self.u(x1 - 1), self.w(y1 - 1), FLOOR_LIFT)
        for d in self.doors:
            x0, y0, x1, y1 = d
            acc = self.zone_at((x0 + x1) / 2, y1 + 2)["accent"]
            m.top(f"thresh_{acc}", self.u(x0), self.w(y0), self.u(x1), self.w(y1), THRESHOLD_LIFT)
            if x1 - x0 > y1 - y0:   # a neon line across the doorway
                m.top(f"dneon_{acc}", self.u(x0 + 4), self.w(y1 - 6), self.u(x1 - 4), self.w(y1 - 4),
                      THRESHOLD_LIFT + FLOOR_LIFT)

    # ---- block geometry -------------------------------------------------------------
    def side_extent(self, b, side):
        """Image px coordinate of one side of a block: inset by 0.1 px (against the floor and
        against neighbouring solid pieces alike: all borders sit on integer pixels, so the 0.2 px
        crack between two pieces never holds a pixel centre), or pushed into the boundary wall."""
        x0, y0, x1, y1 = b["rect"]
        fx0, fy0, fx1, fy1 = self.floor
        if side == "l":
            return -WALL_T * self.ppm + fx0 + 2 if x0 == fx0 else x0 + INSET_PX
        if side == "r":
            return fx1 + WALL_T * self.ppm - 2 if x1 == fx1 else x1 - INSET_PX
        if side == "t":
            return fy0 - WALL_T * S_E * self.ppm + 2 if y0 == fy0 else y0 + INSET_PX
        return y1 if y1 == fy1 else y1 - INSET_PX

    def frame_columns(self, b):
        """Image-x ranges of the front face that are door frame."""
        x0, y0, x1, y1 = b["rect"]
        cols = []
        for d in self.doors:
            dx0, dy0, dx1, dy1 = d
            if dx1 - dx0 > dy1 - dy0:                       # gap in a horizontal wall
                if (dy0, dy1) == (y0, y1):
                    if dx0 == x1:
                        cols.append((x1 - 8, x1))
                    if dx1 == x0:
                        cols.append((x0, x0 + 8))
            elif (dx0, dx1) == (x0, x1) and dy0 == y1:      # wall end above a vertical gap
                cols += [(x0, x0 + 4), (x1 - 4, x1)]
        return cols

    def build(self):
        m = self.m
        fx0, fy0, fx1, fy1 = self.floor
        W, D = self.u(fx1), self.w(fy1)
        e, eg = self.e, self.eg
        wall_px = round(self.wall_h * self.pxv)
        def bands_for(hpx):
            if hpx < 44:
                return [(0, 5, "plinth"), (5, hpx - 6, "body"), (hpx - 6, hpx, "cornice")]
            bands = [(0, 6, "plinth"), (6, hpx - 14, "body"),
                     (hpx - 14, hpx - 10, "trim"), (hpx - 10, hpx, "cornice")]
            if hpx >= 60:                      # one dim amber strip near the top
                bands[1:2] = [(6, hpx - 32, "body"), (hpx - 32, hpx - 28, "neon"), (hpx - 28, hpx - 14, "body")]
            return bands
        wall_bands = bands_for(wall_px)
        pillar_bands_for = lambda hpx: [(0, 6, "plinth"), (6, hpx - 24, "pillar"), (hpx - 24, hpx - 20, "neon"),
                                        (hpx - 20, hpx - 8, "pillar"), (hpx - 8, hpx, "cornice")]
        self.floor_tiles()
        # boundary walls: back (neon colour follows the zone in front of it), left and right
        accent_back = lambda x: self.zone_at(x, fy0 + 2)["accent"]
        back_x0, back_x1 = fx0 - WALL_T * self.ppm, fx1 + WALL_T * self.ppm
        self.box(-WALL_T, -WALL_T, W + WALL_T, -eg, -SLAB_T, self.wall_h, "top",
                 self.facade(back_x0, back_x1, self.wall_h, wall_bands, accent_back))
        # only the south end of the side walls faces the camera
        accent_south = lambda x: self.zone_at(x, fy1 - 2)["accent"]
        self.box(-WALL_T, -eg, -e, D, -SLAB_T, self.wall_h, "top",
                 self.facade(fx0 - WALL_T * self.ppm, fx0 - INSET_PX, self.wall_h, wall_bands, accent_south))
        self.box(W + e, -eg, W + WALL_T, D, -SLAB_T, self.wall_h, "top",
                 self.facade(fx1 + INSET_PX, fx1 + WALL_T * self.ppm, self.wall_h, wall_bands, accent_south))
        first_pillar = True
        for b in self.blocks:
            x0, y0, x1, y1 = b["rect"]
            xa, xb = self.side_extent(b, "l"), self.side_extent(b, "r")
            ya, yb = self.side_extent(b, "t"), self.side_extent(b, "b")
            u0, u1, w0, w1 = self.u(xa), self.u(xb), self.w(ya), self.w(yb)
            h = b["height_m"]
            hpx = round(h * self.pxv)
            accent_at = lambda x, b=b: self.zone_at(x, b["rect"][3] + 2)["accent"]
            if b.get("kind", "wall") == "pillar":
                cells = self.facade(xa, xb, h, pillar_bands_for(hpx), accent_at)
                self.box(u0, w0, u1, w1, 0.0, h, "pillar_top", cells)
                rim = world(self.u(x0 + 2), self.w((y0 + y1) / 2), h)   # rim pixel: the glow covers the centre
                self.m.samples["pillar_top"] = [rim] if first_pillar else self.m.samples["pillar_top"] + [rim]
                first_pillar = False
                acc = accent_at((x0 + x1) / 2)
                m.top(f"glow_{acc}", self.u(x0 + 6), self.w(y0 + 3), self.u(x1 - 6), self.w(y1 - 3),
                      h + 0.01)
            else:
                bands = bands_for(hpx)
                cells = self.facade(xa, xb, h, bands, accent_at, self.frame_columns(b))
                self.box(u0, w0, u1, w1, 0.0, h, "top", cells)
        pts = [p for name in m.prims for p in m.prims[name][0]]
        f = solve_frame(pts, uv_of(world(0, 0, 0)), self.ppm, self.size, (fx0, fy0))
        pmin, pmax = f.pop("p_min"), f.pop("p_max")
        # zero-area triangle spanning the helper corners (pmin, pmax, pmax)
        pos, nor, idx = m.prims.setdefault("frame", ([], [], []))
        pos += [pmin, pmax, pmax]
        nor += [(0.0, 1.0, 0.0)] * 3
        idx += [0, 1, 2]
        f.update(name=self.arena["name"], ppm=self.ppm, image=list(self.size),
                 floor_uv=uv_of(world(0, 0, 0)), helper=[pmin, pmax])
        return m, f


def tone_index(pattern, i, j):
    if pattern == "checker":
        return (i + j) & 1
    if pattern == "rows":
        return j & 1 if (j % 4) != 3 else 2
    h = (i * 73856093) ^ (j * 19349663)
    return (h >> 3) % 3


def build(arena, spec):
    return Builder(arena, spec).build()


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for arena in spec["arenas"]:
        mesh, frame = build(arena, spec)
        write_glb(OUT_DIR / f"{arena['name']}.glb", mesh, build_materials(arena["zones"], spec.get("floor_styles")))
        with open(OUT_DIR / f"{arena['name']}.frame.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(frame, fh, indent=2)
            fh.write("\n")
        print(arena["name"], {k: frame[k] for k in ("map_w", "map_h", "cx", "cy")})


if __name__ == "__main__":
    main()
