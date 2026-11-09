"""Blender script to generate 3D cathedral floor slabs and export to GLB.

Usage:
  blender -b --python-exit-code 1 -P tools/floor/losas_3d_blender.py -- \
      --variant losas_3d|losas_3d_b --seed 20261108 --blocks 3 --out <path.glb>
"""
import argparse
import math
import random
import sys

import bmesh
import bpy
from mathutils import Vector

PXM = 17.9
P = 32.0 / PXM  # 1.7877095 m per slab unit (square in 3D: 32x16 px on screen)
JOINT = 0.03    # 3 cm joint width
BEV = 0.015     # 1.5 cm bevel on slab edges
JOINT_Z = -0.012 # recessed joint gutter


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("losas_3d", "losas_3d_b"), default="losas_3d")
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--blocks", type=int, default=3)
    parser.add_argument("--out", type=str, required=True)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


def create_material(name, base_rgb, roughness=0.88):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (base_rgb[0], base_rgb[1], base_rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    for spec_key in ("Specular IOR Level", "Specular"):
        if spec_key in bsdf.inputs:
            bsdf.inputs[spec_key].default_value = 0.2
            break
    return mat


def layout_losas_3d():
    """Regular 4x8 slabs per block (1x1 units)."""
    return [(col, row, 1, 1) for row in range(8) for col in range(4)]


def layout_losas_3d_b():
    """Mixed layout: 1x1, 2x1 and 2x2 slabs, periodic across 4x8."""
    # 4 columns (0..3) x 8 rows (0..7)
    # Staggers joints across rows to eliminate brick appearance
    return [
        # Row 0
        (0, 0, 2, 1), (2, 0, 1, 1), (3, 0, 1, 1),
        # Row 1
        (0, 1, 1, 1), (1, 1, 2, 1), (3, 1, 1, 1),
        # Rows 2 & 3
        (0, 2, 2, 2), (2, 2, 2, 1),
                      (2, 3, 1, 1), (3, 3, 1, 1),
        # Row 4
        (0, 4, 1, 1), (1, 4, 1, 1), (2, 4, 2, 1),
        # Row 5
        (0, 5, 2, 1), (2, 5, 2, 1),
        # Row 6
        (0, 6, 1, 1), (1, 6, 2, 1), (3, 6, 1, 1),
        # Row 7
        (0, 7, 2, 1), (2, 7, 1, 1), (3, 7, 1, 1)
    ]


def build_slab_mesh(name, w_units, d_units, variant_idx, rng, mat_stone, mat_dark):
    """Build a beveled slab with wear, tilt, chipped corner, or cracks."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)

    # In Blender: X is width, Y is depth, Z is up
    w_m = w_units * P - JOINT
    d_m = d_units * P - JOINT
    x0, x1 = -w_m / 2, w_m / 2
    y0, y1 = -d_m / 2, d_m / 2
    z_bottom = -0.05

    # Base tilt (±3-4 mm)
    tilt_x = rng.uniform(-0.003, 0.003) if variant_idx != 0 else 0.0
    tilt_y = rng.uniform(-0.003, 0.003) if variant_idx != 0 else 0.0
    height_offset = rng.uniform(-0.002, 0.002) if variant_idx != 0 else 0.0

    for v in bm.verts:
        ux = v.co.x + 0.5  # 0..1
        uy = v.co.y + 0.5  # 0..1
        uz = v.co.z + 0.5  # 0..1
        if uz > 0.5:
            # Top vertex
            top_z = height_offset + (ux - 0.5) * tilt_x + (uy - 0.5) * tilt_y
            v.co = Vector((x0 + ux * (x1 - x0), y0 + uy * (y1 - y0), top_z))
        else:
            v.co = Vector((x0 + ux * (x1 - x0), y0 + uy * (y1 - y0), z_bottom))

    top_verts = [v for v in bm.verts if v.co.z > -0.02]

    # Subtle surface noise on top face
    for v in top_verts:
        v.co.z += rng.uniform(-0.0008, 0.0008)

    # Chipped corner on specific variants
    if variant_idx in (2, 5, 8):
        c = rng.choice(top_verts)
        dx = -c.co.x
        dy = -c.co.y
        dist = math.hypot(dx, dy)
        if dist > 1e-4:
            chip_amt = 0.05 if variant_idx != 8 else 0.08
            c.co.x += (dx / dist) * chip_amt
            c.co.y += (dy / dist) * chip_amt
            c.co.z -= 0.005

    # Bevel top edges
    top_edges = [e for e in bm.edges if all(v.co.z > -0.02 for v in e.verts)]
    if top_edges:
        bmesh.ops.bevel(
            bm,
            geom=top_edges,
            offset=BEV,
            offset_type="OFFSET",
            segments=2,
            profile=0.5,
            affect="EDGES",
            clamp_overlap=True
        )

    # Hairline crack on variants 3, 6, 9
    if variant_idx in (3, 6, 9):
        crack_len = rng.uniform(0.3, 0.6)
        crack_w = 0.015
        crack_d = 0.006
        ang = rng.uniform(0, math.pi)
        cx = rng.uniform(x0 * 0.4, x1 * 0.4)
        cy = rng.uniform(y0 * 0.4, y1 * 0.4)
        ret = bmesh.ops.create_cube(bm, size=1.0)
        c_cos, s_sin = math.cos(ang), math.sin(ang)
        for v in ret["verts"]:
            lx = v.co.x * crack_len
            ly = v.co.y * crack_w
            lz = v.co.z * crack_d
            v.co = Vector((cx + lx * c_cos - ly * s_sin, cy + lx * s_sin + ly * c_cos, lz - crack_d / 2))
        for f in bm.faces:
            if all(v in ret["verts"] for v in f.verts):
                f.material_index = 1

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()

    me.materials.append(mat_stone)
    me.materials.append(mat_dark)
    for p in me.polygons:
        p.use_smooth = False
    return me


def main():
    args = parse_args()
    rng = random.Random(args.seed)
    clear_scene()

    # Materials: dark, tranquil, warm brownish gray cathedral stone
    # Linear values around (0.024, 0.021, 0.017) -> renders around sRGB [72, 68, 62]
    mat_stone = create_material("Stone", (0.024, 0.021, 0.017), roughness=0.88)
    mat_joint = create_material("JointBase", (0.007, 0.006, 0.005), roughness=0.95)
    mat_crack = create_material("Crack", (0.005, 0.004, 0.003), roughness=0.98)

    # Layout for one 4x8 block
    if args.variant == "losas_3d":
        block_layout = layout_losas_3d()
    else:
        block_layout = layout_losas_3d_b()

    # Distinct slab prototype shapes: (w_units, d_units)
    shapes = sorted({(w, d) for _, _, w, d in block_layout})

    # Pool of variants per shape (8-12 variants)
    pool_sizes = {(1, 1): 10, (2, 1): 6, (2, 2): 3}
    prototypes = {}
    for w, d in shapes:
        n_vars = pool_sizes.get((w, d), 6)
        for v in range(n_vars):
            prng = random.Random(args.seed * 1000 + w * 100 + d * 10 + v)
            name = f"slab_{w}x{d}_v{v}"
            prototypes[(w, d, v)] = build_slab_mesh(name, w, d, v, prng, mat_stone, mat_crack)

    # Assign variant indices to block pieces
    piece_assignments = []
    counters = {s: 0 for s in shapes}
    for col, row, w, d in block_layout:
        s = (w, d)
        n_vars = pool_sizes.get(s, 6)
        v = (counters[s] * 7 + 3) % n_vars
        counters[s] += 1
        piece_assignments.append((col, row, w, d, v))

    # Grid of blocks: args.blocks x args.blocks (3x3)
    B = args.blocks
    scene_coll = bpy.context.scene.collection

    total_w = B * 4 * P
    total_d = B * 8 * P
    x_start = -total_w / 2
    y_start = -total_d / 2

    for bx in range(B):
        for by in range(B):
            base_col = bx * 4
            base_row = by * 8
            for col, row, w, d, v in piece_assignments:
                mesh = prototypes[(w, d, v)]
                obj = bpy.data.objects.new(f"slab_b{bx}{by}_{col}_{row}", mesh)
                px = x_start + (base_col + col + w / 2) * P
                py = y_start + (base_row + row + d / 2) * P
                obj.location = (px, py, 0.0)
                scene_coll.objects.link(obj)

    # Underneath: continuous joint gutter plane at JOINT_Z
    bme = bpy.data.meshes.new("JointGutterPlane")
    bme.from_pydata(
        [
            (x_start, y_start, JOINT_Z),
            (x_start + total_w, y_start, JOINT_Z),
            (x_start + total_w, y_start + total_d, JOINT_Z),
            (x_start, y_start + total_d, JOINT_Z),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    bme.materials.append(mat_joint)
    gutter_obj = bpy.data.objects.new("JointGutter", bme)
    scene_coll.objects.link(gutter_obj)

    # Export to GLB
    bpy.ops.export_scene.gltf(
        filepath=args.out,
        export_format="GLB",
        use_selection=False,
        export_apply=False
    )
    print(f"Exported {args.variant} ({B}x{B} blocks) to {args.out}")


if __name__ == "__main__":
    main()
