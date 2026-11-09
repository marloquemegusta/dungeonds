"""Blender headless script to model 3D cathedral diamond-checkerboard slabs and export GLB.

Usage:
  blender -b --factory-startup --python-exit-code 1 -P tools/floor/rombos_blender.py -- \
      --variant rombos|rombos_b --seed 20261108 --out <path.glb>
"""
import argparse
import math
import random
import sys
import bmesh
import bpy
from mathutils import Matrix, Vector

PXM = 17.9
PYM = 8.95
Dx = 32.0 / PXM          # diagonal along X in metres (1.7877 m)
Dy = 16.0 / PYM          # diagonal along depth in metres (1.7877 m)
s = Dx / math.sqrt(2.0)  # square side (1.2641 m)
JOINT = 0.026            # joint width in metres (~2.6 cm)
BEV = 0.014              # bevel radius on slab edges (~1.4 cm)
s_inset = s - JOINT      # inset slab side
BASE_Z = -0.012          # bottom of joints (sunken ~1.2 cm)
SLAB_THICK = 0.015       # slab thickness in metres


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--variant", choices=("rombos", "rombos_b"), default="rombos")
    p.add_argument("--seed", type=int, default=20261108)
    p.add_argument("--out", type=str, required=True)
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(col):
            if item.users == 0:
                col.remove(item)


def make_material(name, rgb, roughness=0.88):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    for k in ("Specular IOR Level", "Specular"):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = 0.2
            break
    return mat


def build_slab_mesh(name, variant_idx, mat_stone, mat_crack):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= s_inset
        v.co.y *= s_inset
        v.co.z = (v.co.z + 0.5) * SLAB_THICK - SLAB_THICK

    rot = Matrix.Rotation(math.radians(45), 3, "Z")
    for v in bm.verts:
        v.co = rot @ v.co

    top_verts = [v for v in bm.verts if v.co.z > -0.005]

    tilts = [
        (0.0006, -0.0005, 0.0000),   # var 0: clean
        (-0.0010, 0.0006, -0.0008),  # var 1: chip corner near
        (0.0006, 0.0010, 0.0004),    # var 2: hairline crack
        (-0.0012, -0.0006, -0.0006), # var 3: chip corner right
        (0.0008, -0.0008, 0.0006),   # var 4: slight wear
    ]
    tx, ty, tz = tilts[variant_idx % len(tilts)]
    for v in top_verts:
        v.co.z += tz + tx * (v.co.x / (Dx / 2)) + ty * (v.co.y / (Dy / 2))

    # Chipped corner on variant 1 (near corner: y is min)
    if variant_idx == 1:
        c = min(top_verts, key=lambda v: v.co.y)
        c.co.y += 0.06
        c.co.z -= 0.005

    # Chipped corner on variant 3 (right corner: x is max)
    if variant_idx == 3:
        c = max(top_verts, key=lambda v: v.co.x)
        c.co.x -= 0.06
        c.co.z -= 0.005

    # Bevel top edges
    top_edges = [e for e in bm.edges if all(v.co.z > -0.005 for v in e.verts)]
    bmesh.ops.bevel(
        bm,
        geom=top_edges,
        offset=BEV,
        offset_type="OFFSET",
        segments=2,
        profile=0.5,
        affect="EDGES",
        clamp_overlap=True,
    )

    # Hairline crack on variant 2
    if variant_idx == 2:
        L, W, H = 0.35, 0.014, 0.004
        ret = bmesh.ops.create_cube(bm, size=1.0)
        crack_verts = set(ret["verts"])
        ang = math.radians(35)
        ca, sa = math.cos(ang), math.sin(ang)
        for v in ret["verts"]:
            lx, ly, lz = v.co.x * L, v.co.y * W, v.co.z * H
            v.co = Vector((lx * ca - ly * sa + 0.1, lx * sa + ly * ca - 0.05, lz + 0.001))
        for f in bm.faces:
            if all(v in crack_verts for v in f.verts):
                f.material_index = 1

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_stone)
    me.materials.append(mat_crack)
    return me


def main():
    opt = parse_args()
    clear_scene()
    scene = bpy.context.scene

    if opt.variant == "rombos":
        # Low contrast: warm dark stone vs slightly cooler stone (delta L* ~ 4.5 in Lab)
        col_A = (0.0095, 0.0080, 0.0068)
        col_B = (0.0135, 0.0120, 0.0110)
    else:
        # rombos_b: clear damero (delta L* ~ 9.5 in Lab)
        col_A = (0.0085, 0.0070, 0.0058)
        col_B = (0.0210, 0.0185, 0.0165)

    col_joint = (0.0030, 0.0025, 0.0020)
    col_crack = (0.0020, 0.0018, 0.0015)

    mat_A = make_material("stone_A", col_A)
    mat_B = make_material("stone_B", col_B)
    mat_joint = make_material("mortar", col_joint)
    mat_crack = make_material("crack", col_crack)

    meshes_A = [build_slab_mesh(f"slab_A_{i}", i, mat_A, mat_crack) for i in range(5)]
    meshes_B = [build_slab_mesh(f"slab_B_{i}", i, mat_B, mat_crack) for i in range(5)]

    rng = random.Random(opt.seed)
    var_A = [[rng.randrange(5) for _ in range(4)] for _ in range(8)]
    var_B = [[rng.randrange(5) for _ in range(4)] for _ in range(8)]

    W_b = 128.0 / PXM
    D_b = 128.0 / PYM

    coll = scene.collection

    for bx in (-1, 0, 1):
        for by in (-1, 0, 1):
            base_x = bx * W_b
            base_y = by * D_b

            # Color A rhombuses: centers at cx=16+ix*32, cy=8+iy*16
            for iy in range(8):
                cy_px = iy * 16 + 8
                cy_m = base_y + (cy_px - 64.0) / PYM
                for ix in range(4):
                    cx_px = ix * 32 + 16
                    cx_m = base_x - (cx_px - 64.0) / PXM
                    v = var_A[iy][ix]
                    ob = bpy.data.objects.new(f"A_{bx}_{by}_{iy}_{ix}", meshes_A[v])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)

            # Color B rhombuses: centers at cx=ix*32, cy=iy*16
            for iy in range(8):
                cy_px = iy * 16
                cy_m = base_y + (cy_px - 64.0) / PYM
                for ix in range(4):
                    cx_px = ix * 32
                    cx_m = base_x - (cx_px - 64.0) / PXM
                    v = var_B[iy][ix]
                    ob = bpy.data.objects.new(f"B_{bx}_{by}_{iy}_{ix}", meshes_B[v])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)

    # Mortar joint ground plane covering 3x3 block area
    bm_g = bmesh.new()
    bmesh.ops.create_grid(bm_g, x_segments=1, y_segments=1, size=1.0)
    for v in bm_g.verts:
        v.co.x *= (1.5 * W_b)
        v.co.y *= (1.5 * D_b)
        v.co.z = BASE_Z
    me_g = bpy.data.meshes.new("joint_ground")
    bm_g.to_mesh(me_g)
    bm_g.free()
    me_g.materials.append(mat_joint)
    ob_g = bpy.data.objects.new("joint_ground", me_g)
    coll.objects.link(ob_g)

    # 4 corner triangles at Z=0 to anchor the bounding box tightly to [-1.5*W_b, 1.5*W_b] x [-1.5*D_b, 1.5*D_b] at Z=0
    bm_ref = bmesh.new()
    eps = 0.001
    for rx in (-1.5 * W_b, 1.5 * W_b - eps):
        for ry in (-1.5 * D_b, 1.5 * D_b - eps):
            v0 = bm_ref.verts.new((rx, ry, 0.0))
            v1 = bm_ref.verts.new((rx + eps, ry, 0.0))
            v2 = bm_ref.verts.new((rx, ry + eps, 0.0))
            bm_ref.faces.new((v0, v1, v2))
    me_ref = bpy.data.meshes.new("ref_corners")
    bm_ref.to_mesh(me_ref)
    bm_ref.free()
    me_ref.materials.append(mat_joint)
    ob_ref = bpy.data.objects.new("ref_corners", me_ref)
    coll.objects.link(ob_ref)

    bpy.ops.export_scene.gltf(filepath=opt.out, export_format="GLB")
    print("BLENDER_EXPORT_OK:", opt.out)


if __name__ == "__main__":
    main()
