"""Blender-side renderer for the 3D slab floor (losas3d_h). Run by losas3d_h.py, not by hand.

  blender -b --factory-startup -P tools/floor/losas3d_h_render.py -- \
      --variant h|b --seed 7 --blocks 1 --samples 256 --out <png> --layout-out <json>

Geometry is in metres. The camera is orthographic, 30 deg elevation, azimuth 0 (screen axes are
world axes). Screen scale is 17.9 px/m horizontal; depth is foreshortened by sin(30) = 0.5, so
8.95 px/m in depth. One slab unit P = 32 / 17.9 m = 32 px wide and 16 px deep on screen.
A block is 4 x 8 units (128 x 128 px). --blocks 2 renders a 2 x 2 block area to test the seam.
"""
import json
import math
import random
import sys

import bmesh
import bpy
from mathutils import Vector

PXM = 17.9
P = 32.0 / PXM          # one slab unit, metres (1.7877)
JOINT = 0.03            # joint width, metres
BEV = 0.015             # bevel radius on slab edges
BASE_Z = -0.01          # bottom of the joints (1 cm below the slab tops)
ELEV = math.radians(30.0)
DIST = 20.0
SUPER = 4               # supersampling factor per output pixel (512 px per block -> 128)


def script_args():
    a = sys.argv
    a = a[a.index("--") + 1:] if "--" in a else []
    opt = {"variant": "h", "seed": 7, "blocks": 1, "samples": 256, "out": "render.png",
           "layout_out": None, "nvar": 10}
    i = 0
    while i < len(a):
        k = a[i].lstrip("-").replace("-", "_")
        if k in ("variant", "out", "layout_out"):
            opt[k] = a[i + 1]
        else:
            opt[k] = int(a[i + 1])
        i += 2
    return opt


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def make_mat(name, rgb, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Roughness"].default_value = rough
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs:
            b.inputs[key].default_value = 0.25
            break
    return m


def layout_h(rng):
    """Regular 1x1 layout: 4 x 8 units per block."""
    return [(ix, iy, 1, 1) for iy in range(8) for ix in range(4)]


def layout_b(rng):
    """Mixed layout: 1x1, 2x1 and 2x2 pieces, every piece wholly inside the block (periodic)."""
    occ = [[False] * 4 for _ in range(8)]
    out = []
    for iy in range(8):
        for ix in range(4):
            if occ[iy][ix]:
                continue
            r = rng.random()
            can22 = ix + 1 < 4 and iy + 1 < 8 and not occ[iy][ix + 1] and not occ[iy + 1][ix] and not occ[iy + 1][ix + 1]
            can21 = ix + 1 < 4 and not occ[iy][ix + 1]
            if r < 0.2 and can22:
                w, d = 2, 2
            elif r < 0.55 and can21:
                w, d = 2, 1
            else:
                w, d = 1, 1
            for dy in range(d):
                for dx in range(w):
                    occ[iy + dy][ix + dx] = True
            out.append((ix, iy, w, d))
    return out


def build_piece_mesh(name, w, d, rng, chip, broken, crack, stone, crack_mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    x0, x1 = JOINT / 2, w * P - JOINT / 2
    y0, y1 = JOINT / 2, d * P - JOINT / 2
    z0 = -0.25
    z1 = rng.uniform(-0.004, 0.004)
    for v in bm.verts:
        ux, uy, uz = v.co.x + 0.5, v.co.y + 0.5, v.co.z + 0.5
        v.co = Vector((x0 + ux * (x1 - x0), y0 + uy * (y1 - y0), z0 + uz * (z1 - z0)))
    top = [v for v in bm.verts if v.co.z > -0.1]
    for v in top:
        v.co.z += rng.uniform(-0.002, 0.002)
    if chip:
        c = rng.choice(top)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = cx - c.co.x, cy - c.co.y
        n = math.hypot(dx, dy)
        amt = 0.12 if broken else 0.04
        c.co.x += dx / n * amt
        c.co.y += dy / n * amt
        c.co.z -= 0.008 if broken else 0.003
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=BEV, offset_type="OFFSET",
                    segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    if crack:
        L = rng.uniform(0.25, 0.45)
        W, H = 0.022, 0.004
        ang = rng.uniform(0, math.pi)
        cx = rng.uniform(x0 + 0.25, x1 - 0.25)
        cy = rng.uniform(y0 + 0.25, y1 - 0.25)
        ret = bmesh.ops.create_cube(bm, size=1.0)
        nv = set(ret["verts"])
        c, s = math.cos(ang), math.sin(ang)
        for v in ret["verts"]:
            lx, ly, lz = v.co.x * L, v.co.y * W, v.co.z * H
            v.co = Vector((cx + lx * c - ly * s, cy + lx * s + ly * c, z1 + lz))
        for f in bm.faces:
            if all(v in nv for v in f.verts):
                f.material_index = 1
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(stone)
    me.materials.append(crack_mat)
    for p in me.polygons:
        p.use_smooth = False
    return me


def main():
    opt = script_args()
    rng = random.Random(opt["seed"])
    clear_scene()
    scene = bpy.context.scene
    B = opt["blocks"]

    # --- layout
    base_layout = layout_h(rng) if opt["variant"] == "h" else layout_b(rng)
    shapes = sorted({(w, d) for _, _, w, d in base_layout})
    pool_n = {(1, 1): opt["nvar"], (2, 1): 4, (2, 2): 3}
    var_of = {}
    for s in shapes:
        var_of[s] = [rng.randrange(pool_n[s]) for _ in base_layout if (_[2], _[3]) == s]
    # assign variant index per piece
    pieces = []
    counters = {s: 0 for s in shapes}
    for (ix, iy, w, d) in base_layout:
        s = (w, d)
        v = var_of[s][counters[s]]
        counters[s] += 1
        pieces.append((ix, iy, w, d, v))

    # --- materials
    stones = {}
    base_tone = (0.10, 0.092, 0.078)
    def stone_for(s, v):
        key = (s, v)
        if key not in stones:
            j = rng.uniform(-0.03, 0.03)  # one brightness factor only: same hue on every slab
            rgb = tuple(max(0.0, c * (1 + j)) for c in base_tone)
            stones[key] = make_mat(f"stone_{s[0]}{s[1]}_{v}", rgb)
        return stones[key]
    crack_mat = make_mat("crack", (0.008, 0.008, 0.008), 1.0)
    base_mat = make_mat("joint_base", (0.035, 0.032, 0.029), 1.0)

    # --- piece meshes (one per shape x variant), instanced by linking the same mesh data
    meshes = {}
    def mesh_for(s, v):
        key = (s, v)
        if key not in meshes:
            prng = random.Random(opt["seed"] * 1000 + s[0] * 100 + s[1] * 10 + v)
            chip = v in (1, 4, 7)
            broken = v == 3
            crack = v in (2, 6)
            meshes[key] = build_piece_mesh(f"piece_{s[0]}x{s[1]}_{v}", s[0], s[1], prng, chip, broken,
                                           crack, stone_for(s, v), crack_mat)
        return meshes[key]

    coll = scene.collection
    counts = {}
    for bx in range(B):
        for by in range(B):
            for (ix, iy, w, d, v) in pieces:
                s = (w, d)
                me = mesh_for(s, v)
                ob = bpy.data.objects.new(f"p_{bx}{by}_{ix}{iy}", me)
                ob.location = (bx * 4 * P + ix * P, by * 8 * P + iy * P, 0.0)
                coll.objects.link(ob)
    for (ix, iy, w, d, v) in pieces:
        counts[f"{w}x{d}"] = counts.get(f"{w}x{d}", 0) + 1
    variants_used = {f"{s[0]}x{s[1]}": sorted({p[4] for p in pieces if (p[2], p[3]) == s}) for s in shapes}

    # base plane (joint floor)
    W, D = B * 4 * P, B * 8 * P
    bme = bpy.data.meshes.new("joint_base")
    bme.from_pydata([(0, 0, BASE_Z), (W, 0, BASE_Z), (W, D, BASE_Z), (0, D, BASE_Z)], [], [(0, 1, 2, 3)])
    bme.materials.append(base_mat)
    bob = bpy.data.objects.new("joint_base", bme)
    coll.objects.link(bob)

    # --- light: one neutral sun, no shadows (keeps every block periodic and copies identical)
    sun = bpy.data.lights.new("key", "SUN")
    sun.energy = 4.2
    for attr in ("use_shadow",):
        if hasattr(sun, attr):
            setattr(sun, attr, False)
    if hasattr(sun, "cycles") and hasattr(sun.cycles, "cast_shadow"):
        sun.cycles.cast_shadow = False
    so = bpy.data.objects.new("key", sun)
    coll.objects.link(so)
    travel = Vector((0.55, 0.65, -0.45)).normalized()
    so.rotation_euler = travel.to_track_quat("-Z", "Y").to_euler()

    # fill: a second sun from overhead instead of a world/environment light. Environment sampling
    # leaves per-pixel noise; suns with angle 0 and no shadows are deterministic.
    fill = bpy.data.lights.new("fill", "SUN")
    fill.energy = 0.9
    fill.angle = 0.0
    fill.use_shadow = False
    fo = bpy.data.objects.new("fill", fill)
    coll.objects.link(fo)
    fo.rotation_euler = Vector((0.0, 0.0, -1.0)).to_track_quat("-Z", "Y").to_euler()
    sun.angle = 0.0
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    scene.world = world

    # --- camera: ortho, 30 deg elevation, centred on the block area
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = 128.0 * B / PXM
    cam = bpy.data.objects.new("cam", cam_d)
    coll.objects.link(cam)
    cx, cy = B * 2 * P, B * 4 * P
    dvec = Vector((0.0, math.cos(ELEV), -math.sin(ELEV)))
    cam.location = Vector((cx, cy, 0.0)) - dvec * DIST
    cam.rotation_euler = (math.radians(90) - ELEV, 0.0, 0.0)
    scene.camera = cam

    # --- render settings
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x = r.resolution_y = 128 * SUPER * B
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.color_depth = "8"
    r.film_transparent = False
    r.dither_intensity = 0.0  # no 8-bit output dither: identical copies must give identical pixels
    vs = scene.view_settings
    vs.view_transform = "Standard"
    vs.look = "None"
    vs.exposure = 0.0
    vs.gamma = 1.0
    c = scene.cycles
    c.device = "CPU"
    c.samples = opt["samples"]
    c.use_denoising = False
    c.use_adaptive_sampling = False  # every pixel gets the same sample count (copies must match)
    c.max_bounces = 0
    c.diffuse_bounces = 0
    c.glossy_bounces = 0
    c.transmission_bounces = 0
    c.volume_bounces = 0
    c.transparent_max_bounces = 0
    c.seed = opt["seed"]
    r.filepath = opt["out"]
    bpy.ops.render.render(write_still=True)

    if opt["layout_out"]:
        with open(opt["layout_out"], "w", encoding="utf-8") as f:
            json.dump({"variant": opt["variant"], "pieces": pieces, "counts": counts,
                       "variants_used": variants_used, "block_units": [4, 8], "unit_m": P},
                      f, indent=1)
    print("LOSAS3D_RENDER_OK", opt["out"], "pieces", counts)


main()
