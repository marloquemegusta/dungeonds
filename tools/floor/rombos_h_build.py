"""Blender-side builder for the rhombus damero floor (rombos_h). Run by rombos_h.py, not by hand.

  blender -b --factory-startup --python-exit-code 1 -P tools/floor/rombos_h_build.py -- \
      --variant h|b --seed 7 --half 15.1679 --out <glb>

Geometry is in metres. Squares of side S = 32 / (17.9 * sqrt 2) = 1.2641 m, axis-aligned in the
world, form a two-colour checkerboard. The lab camera is at azimuth 45 deg, 30 deg elevation,
orthographic: an axis-aligned square comes out as a 32 x 16 px rhombus (at 17.9 px/m) and the
rhombi touch by their vertices. Tile centres in screen px are (16 (a + b), 8 (b - a)); colour is
(a + b) mod 2.

The lab frames the projected bounding box of the GLB. The floor is a diamond |x| + |y| <= half:
its projection is an axis-aligned 2:1 rectangle that sits in the centre of the frame, with the
rest of the frame black. Tiles crossing the diamond edge are clipped to it, so the rectangle is
covered up to its border.

Periodicity: the pattern repeats with 128 px in screen X and Y. The per-tile variant (geometry
jitter, chipped corner, crack) is a pure function of the screen centre modulo 128, so every copy
of the 128 px block is identical.
"""
import math
import random
import sys
import zlib

import bmesh
import bpy
from mathutils import Vector

PXM = 17.9
S = 32.0 / (PXM * math.sqrt(2.0))   # square side, metres (diagonal = 32 px horizontal)
JOINT = 0.025                         # joint width, metres
BEV = 0.015                           # bevel on the top edges
SLAB_BOTTOM = -0.01                   # slab bottoms (hidden)
JOINT_Z = -0.012                      # joint floor, 1.2 cm below the slab tops (kept apart from SLAB_BOTTOM: no z-fight)
NVAR = 4                              # geometry variants per colour
HALF_DEFAULT = 15.1679                # diamond half-diagonal: 2:1 coverage 384 x 192 px at 1x

# stone colours, sRGB. Tuned on the lab render (see rombos_h.py stats): small L* gap.
PALETTES = {
    "h": {"A": (0.228, 0.205, 0.179), "B": (0.178, 0.172, 0.171)},
    "b": {"A": (0.275, 0.237, 0.199), "B": (0.168, 0.168, 0.165)},
}


def script_args():
    a = sys.argv
    a = a[a.index("--") + 1:] if "--" in a else []
    opt = {"variant": "h", "seed": 7, "half": HALF_DEFAULT, "out": "floor.glb", "palette": None}
    i = 0
    while i < len(a):
        k = a[i].lstrip("-").replace("-", "_")
        if k in ("variant", "out", "palette"):
            opt[k] = a[i + 1]
        elif k == "half":
            opt[k] = float(a[i + 1])
        else:
            opt[k] = int(a[i + 1])
        i += 2
    return opt


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_mat(name, srgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*[srgb_to_lin(c) for c in srgb], 1.0)
    b.inputs["Roughness"].default_value = rough
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs:
            b.inputs[key].default_value = 0.25
            break
    return m


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def key_hash(kx, ky, seed):
    return zlib.crc32(f"{seed}:{kx}:{ky}".encode())


def slab_bm(rng, chip, crack):
    """One bevelled slab in local coordinates (centred on the origin, top at z = 0).

    Material index 0 is the stone, 1 the crack."""
    h = (S - JOINT) / 2.0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        v.co = Vector((x * 2 * h, y * 2 * h, SLAB_BOTTOM + (z + 0.5) * (-SLAB_BOTTOM)))
    top = [v for v in bm.verts if v.co.z > -0.005]
    for v in top:
        v.co.z += rng.uniform(-0.002, 0.002)
    if chip:
        c = rng.choice(top)
        dx, dy = -c.co.x, -c.co.y
        n = math.hypot(dx, dy)
        c.co.x += dx / n * 0.03
        c.co.y += dy / n * 0.03
        c.co.z -= 0.005
    top_edges = [e for e in bm.edges if all(v.co.z > -0.005 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=top_edges, offset=BEV, offset_type="OFFSET", segments=2, profile=0.5,
                    affect="EDGES", clamp_overlap=True)
    if crack:
        ln = rng.uniform(0.22, 0.30)
        wd, ht = 0.010, 0.002
        ang = rng.uniform(0, math.pi)
        cx = rng.uniform(-0.25, 0.25)
        cy = rng.uniform(-0.25, 0.25)
        ret = bmesh.ops.create_cube(bm, size=1.0)
        nv = set(ret["verts"])
        cs, sn = math.cos(ang), math.sin(ang)
        for v in ret["verts"]:
            lx, ly, lz = v.co.x * ln, v.co.y * wd, v.co.z * ht
            v.co = Vector((cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, 0.0015 + lz))
        for f in bm.faces:
            if all(v in nv for v in f.verts):
                f.material_index = 1
    return bm


def bm_to_mesh(bm, name, mat_top, mat_crack):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_top)
    me.materials.append(mat_crack)
    for p in me.polygons:
        p.use_smooth = False
    return me


def clip_to_diamond(bm, half):
    """Keep the part of bm with |x| + |y| <= half. Cuts with the four edge planes, then deletes
    the vertices on the outer side (explicit test, no reliance on bmesh clear flags)."""
    nrm = 1.0 / math.sqrt(2.0)
    planes = [((nrm, nrm), (half / 2, half / 2)), ((-nrm, -nrm), (-half / 2, -half / 2)),
              ((nrm, -nrm), (half / 2, -half / 2)), ((-nrm, nrm), (-half / 2, half / 2))]
    for (nx, ny), (px, py) in planes:
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=(px, py, 0.0),
                               plane_no=(nx, ny, 0.0), clear_outer=False, clear_inner=False)
        out = [v for v in bm.verts if nx * (v.co.x - px) + ny * (v.co.y - py) > 1e-6]
        if out:
            bmesh.ops.delete(bm, geom=out, context="VERTS")
    return bm


def rot2(x, y, t):
    return (x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t))


def screen_centre(cx, cy):
    """Screen position in px of a world point for the lab camera (azimuth 45, elevation 30)."""
    k = PXM * math.sqrt(0.5)
    return k * (cx + cy), k * 0.5 * (cy - cx)


def main():
    opt = script_args()
    clear_scene()
    scene = bpy.context.scene
    M = opt["half"]
    pal = PALETTES[opt["palette"] or opt["variant"]]
    mats = {"A": make_mat("stone_A", pal["A"], 0.92), "B": make_mat("stone_B", pal["B"], 0.92)}
    crack_mat = make_mat("crack", (0.02, 0.02, 0.02), 1.0)
    joint_mat = make_mat("joint", (0.035, 0.032, 0.03), 1.0)

    h = (S - JOINT) / 2.0
    meshes, counts, clipped = {}, {"A": 0, "B": 0}, 0
    coll = scene.collection
    created = []
    n = int(M / S) + 4
    for a in range(-n, n + 1):
        for b in range(-n, n + 1):
            cx, cy = a * S, b * S
            if abs(cx) + abs(cy) > M + S:
                continue
            col = "A" if (a + b) % 2 == 0 else "B"
            sx, sy = screen_centre(cx, cy)
            hv = key_hash(round(sx) % 128, round(sy) % 128, opt["seed"])
            var = hv % NVAR
            chip = ((hv >> 8) % 8) == 0
            crack = ((hv >> 16) % 32) == 0
            inside = all(abs(cx + px) + abs(cy + py) <= M
                         for px, py in ((-h, -h), (h, -h), (h, h), (-h, h)))
            if inside:
                k = (col, var, chip, crack)
                if k not in meshes:
                    prng = random.Random(zlib.crc32(repr(k).encode()) ^ opt["seed"])
                    meshes[k] = bm_to_mesh(slab_bm(prng, chip, crack),
                                           f"slab_{col}{var}_{int(chip)}{int(crack)}",
                                           mats[col], crack_mat)
                ob = bpy.data.objects.new(f"t_{a}_{b}", meshes[k])
                ob.location = (cx, cy, 0.0)
            else:
                prng = random.Random(zlib.crc32(repr(("clip", a, b)).encode()) ^ opt["seed"])
                bm = slab_bm(prng, chip, crack)
                for v in bm.verts:
                    v.co.x += cx
                    v.co.y += cy
                bm = clip_to_diamond(bm, M)
                if len(bm.verts) == 0:
                    bm.free()
                    continue
                clipped += 1
                ob = bpy.data.objects.new(f"c_{a}_{b}", bm_to_mesh(bm, f"clip_{a}_{b}", mats[col],
                                                                   crack_mat))
            coll.objects.link(ob)
            created.append(ob)
            counts[col] += 1

    # joint base: one diamond at the joint depth, covering the whole region
    bme = bpy.data.meshes.new("joint_base")
    bme.from_pydata([(M, 0, JOINT_Z), (0, M, JOINT_Z), (-M, 0, JOINT_Z), (0, -M, JOINT_Z)], [],
                    [(0, 1, 2, 3)])
    bme.materials.append(joint_mat)
    bob = bpy.data.objects.new("joint_base", bme)
    coll.objects.link(bob)
    created.append(bob)

    bpy.ops.object.select_all(action="DESELECT")
    for o in created:
        o.select_set(True)
    bpy.context.view_layer.objects.active = bob
    bpy.ops.export_scene.gltf(filepath=opt["out"], export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_normals=True,
                              export_materials="EXPORT")
    print("ROMBOS_BUILD_OK", opt["out"], "tiles", counts, "clipped", clipped, "meshes", len(meshes),
          "half", M, "S", round(S, 5))


main()
