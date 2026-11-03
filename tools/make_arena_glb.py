"""Builds the v0.1 arena models (assets/arenas/arenas.json -> arena_0N.glb).

The lab (tools/lab/FBX-Web-Renderer-parity.js, renderMap) frames a map model by
the projection of the model's WORLD axis-aligned bounding box, with the camera
at azimuth 45 deg / elevation 30 deg. A room whose walls must run horizontally
and vertically on screen is therefore rotated 45 deg about Y in world space,
which makes its AABB (and so the lab render) much larger than the 384x384
arena. The package is rendered big at exactly 40.42 px/m and cropped to 384x384
by tools/export_arenas.py. To make the crop land on the 4 px collision grid and
the scale exactly 40.42 px/m, each model carries one zero-area triangle
("frame" primitive) that only stretches the AABB; it draws no pixel and is
ignored by the collision/occlusion passes (area <= 1e-6).

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
CROP = 384

COL_FLOOR = (0.078, 0.154, 0.325)
COL_WALL = (0.030, 0.070, 0.165)
COL_BLOCK = (0.120, 0.220, 0.450)
COL_FRAME = (0.0, 0.0, 0.0)

WALL_T = 0.34
SLAB_T = 0.25
# The lab marks a collision cell for every cell an obstacle edge passes through,
# and an edge exactly on a 4 px cell border marks the cell on the wrong side.
# Obstacle faces are therefore moved 1 px off the spec border: blocks shrink and
# the boundary walls retreat outwards, so the blocked cells land on the spec rect.
INSET_PX = 1.0


def world(u, w, y):
    """room coords (u right, w ground-down on screen, y up), metres -> xyz."""
    return (u * RIGHT[0] + w * DOWN[0], y, u * RIGHT[2] + w * DOWN[2])


def uv_of(p):
    """lab projection of an xyz point: (u along right, v along camera up)."""
    return (p[0] * RIGHT[0] + p[2] * RIGHT[2],
            -S * S_E * p[0] + C_E * p[1] + S * S_E * p[2])


class Mesh:
    def __init__(self):
        self.prims = {}  # material index -> (positions, normals, indices)

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

    def box(self, mat, u0, w0, u1, w1, y0, y1):
        """Box over the room rect [u0,u1]x[w0,w1] from y0 to y1, outward
        faces, no bottom face (it would count as floor in the lab collision)."""
        corners = {(i, j, k): world(u1 if i else u0, w1 if j else w0, y1 if k else y0)
                   for i in (0, 1) for j in (0, 1) for k in (0, 1)}
        centre = world((u0 + u1) / 2, (w0 + w1) / 2, (y0 + y1) / 2)
        quads = [
            [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],  # top
            [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],  # back  (w0)
            [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],  # front (w1)
            [(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)],  # left  (u0)
            [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],  # right (u1)
        ]
        for q in quads:
            p = [corners[k] for k in q]
            self.tri(mat, p[0], p[1], p[2], centre)
            self.tri(mat, p[0], p[2], p[3], centre)


def write_glb(path, mesh, colours):
    """Minimal GLB 2.0: one node, one mesh, one primitive per material."""
    blob = bytearray()
    views, accessors, prims, materials = [], [], [], []
    for mi, mat in enumerate(sorted(mesh.prims)):
        pos, nor, idx = mesh.prims[mat]
        materials.append({"name": f"m{mat}", "pbrMetallicRoughness": {
            "baseColorFactor": [*colours[mat], 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.9}})
        entry = {}
        for name, data, ctype, fmt, target in (
                ("POSITION", pos, 5126, "f", 34962), ("NORMAL", nor, 5126, "f", 34962),
                ("indices", idx, 5125, "I", 34963)):
            flat = [v for item in data for v in (item if isinstance(item, tuple) else (item,))]
            raw = struct.pack(f"<{len(flat)}{fmt}", *flat)
            while len(blob) % 4:
                blob.append(0)
            views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(raw), "target": target})
            blob += raw
            acc = {"bufferView": len(views) - 1, "componentType": ctype,
                   "count": len(data), "type": "VEC3" if name != "indices" else "SCALAR"}
            if name == "POSITION":
                acc["min"] = [min(p[i] for p in pos) for i in range(3)]
                acc["max"] = [max(p[i] for p in pos) for i in range(3)]
            accessors.append(acc)
            entry[name] = len(accessors) - 1
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


def solve_frame(room_pts, floor_uv, ppm):
    """Pick lab render size, crop offset and the zero-area helper that stretches
    the world AABB so the 384x384 crop sits on the 4 px grid at exactly ppm."""
    xs, ys, zs = zip(*room_pts)
    x0r, x1r, y0r, y1r, z0r, z1r = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    u_f, v_f = floor_uv  # floor rect top-left corner (spec px 16,120) in lab uv
    dy = y1r - y0r
    best = None
    for map_w in range(448, 1537, 16):
        proj_w = map_w / ppm
        proj_h = S_E * proj_w + C_E * dy
        map_h = round(map_w * proj_h / proj_w)
        if map_h < CROP:
            continue
        pv = map_h / proj_h
        for cx in range(0, map_w - CROP + 1, 4):
            min_u = u_f - (16 + cx) / ppm
            max_u = min_u + proj_w
            a_, b_ = -max_u / S, -min_u / S
            for cy in range(0, map_h - CROP + 1, 4):
                max_v = v_f + (120 + cy) / pv
                c_ = (max_v - C_E * y1r) / (S * S_E)
                lo = max(a_ - z0r, z1r - c_)
                hi = min(x0r, b_ - c_ - x1r)
                if lo <= hi:
                    key = (map_w * map_h, cx + cy)
                    if best is None or key < best[0]:
                        t = (lo + hi) / 2
                        best = (key, dict(map_w=map_w, map_h=map_h, cx=cx, cy=cy,
                                          p_min=(t, y0r, a_ - t), p_max=(b_ - c_ - t, y1r, c_ + t)))
        if best:
            break
    if best is None:
        raise SystemExit("no frame solution")
    return best[1]


def build(arena, spec):
    ppm = spec["pixels_per_metre"]
    fx0, fy0, fx1, fy1 = spec["floor"]["rect"]
    to_u = lambda x: (x - fx0) / ppm
    to_w = lambda y: (y - fy0) / (S_E * ppm)   # screen dy -> ground metres
    W, D = to_u(fx1), to_w(fy1)
    e = INSET_PX / ppm            # horizontal inset in metres
    eg = INSET_PX / (S_E * ppm)   # same inset along the ground depth
    wall_h = spec["boundary_wall_height_m"]
    m = Mesh()
    # materials: 0 floor, 1 walls, 2 blocks, 3 frame helper
    m.box(0, -e, -eg, W + e, D, -SLAB_T, 0.0)
    m.box(1, -WALL_T, -WALL_T, W + WALL_T, -eg, -SLAB_T, wall_h)   # back
    m.box(1, -WALL_T, -eg, -e, D, -SLAB_T, wall_h)                 # left
    m.box(1, W + e, -eg, W + WALL_T, D, -SLAB_T, wall_h)           # right
    for b in arena["blocks"]:
        x0, y0, x1, y1 = b["rect"]
        m.box(2, to_u(x0) + e, to_w(y0) + eg, to_u(x1) - e, to_w(y1) - eg, 0.0, b["height_m"])
    pts = [p for mat in m.prims for p in m.prims[mat][0]]
    f = solve_frame(pts, uv_of(world(0, 0, 0)), ppm)
    pmin, pmax = f.pop("p_min"), f.pop("p_max")
    # zero-area triangle spanning the helper corners (pmin, pmax, pmax)
    pos, nor, idx = m.prims.setdefault(3, ([], [], []))
    pos += [pmin, pmax, pmax]
    nor += [(0.0, 1.0, 0.0)] * 3
    idx += [0, 1, 2]
    f.update(name=arena["name"], ppm=ppm, crop=CROP,
             floor_uv=uv_of(world(0, 0, 0)), helper=[pmin, pmax])
    return m, f


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = {0: COL_FLOOR, 1: COL_WALL, 2: COL_BLOCK, 3: COL_FRAME}
    for arena in spec["arenas"]:
        mesh, frame = build(arena, spec)
        write_glb(OUT_DIR / f"{arena['name']}.glb", mesh, cols)
        with open(OUT_DIR / f"{arena['name']}.frame.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(frame, fh, indent=2)
            fh.write("\n")
        print(arena["name"], {k: frame[k] for k in ("map_w", "map_h", "cx", "cy")})


if __name__ == "__main__":
    main()
