"""Blender headless: damero de rombos con las losas de Tripo (FBX) y exportacion a GLB.

Igual geometria que tools/floor/rombos_blender.py (rombos de 32x16 px, junta 2.6 cm, hundida 1.2 cm),
pero cada losa es un FBX importado: se escala a la cara del rombo, se gira 45 deg, se reduce con
Decimate (para que 576 instancias quepan en el render del lab) y se le pone un material con solo
la textura base (la unica que lee el cargador del lab).

Usage:
  blender -b --factory-startup --python-exit-code 1 -P tools/floor/rombos_tripo_blender.py -- \
      --manifest <manifest.json> --seed 20261108 --out <path.glb>
Escribe ademas <path.glb>.placement.json con conteos y dimensiones.
"""
import argparse
import json
import math
import random
import sys

import bmesh  # noqa: F401  (disponible en Blender; no se usa aqui)
import bpy
from mathutils import Matrix

PXM = 17.9
PYM = 8.95
Dx = 32.0 / PXM
s = Dx / math.sqrt(2.0)     # lado del rombo (1.2641 m)
JOINT = 0.026
s_inset = s - JOINT         # cara de la losa
SLAB_THICK = 0.015
BASE_Z = -0.012
DEC_FACES = 1200            # caras objetivo por losa tras Decimate


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=str, required=True)
    p.add_argument("--seed", type=int, default=20261108)
    p.add_argument("--out", type=str, required=True)
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.images):
        for item in list(col):
            if item.users == 0:
                col.remove(item)


def make_stone_material(name, png, roughness=0.88):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png.replace("\\", "/"), check_existing=False)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_flat_material(name, rgb, roughness=0.88):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def process_slab(entry):
    """Importa el FBX, lo deja como losa plana centrada, girada 45 deg y reducida."""
    before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.fbx(filepath=entry["fbx"].replace("\\", "/"))
    new = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"{entry['name']}: {len(meshes)} mallas tras importar")
    obj = meshes[0]
    for o in new:
        if o is not obj:
            bpy.data.objects.remove(o, do_unlink=True)

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    me = obj.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    xmin, xmax, ymin, ymax, zmin, zmax = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
    sx, sy, sz = s_inset / dx, s_inset / dy, SLAB_THICK / dz
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    rot = Matrix.Rotation(math.radians(45), 3, "Z")
    for v in me.vertices:
        co = v.co
        x = (co.x - cx) * sx
        y = (co.y - cy) * sy
        z = (co.z - zmin) * sz - SLAB_THICK  # cara superior en z=0, como el procedural
        v.co = rot @ type(co)((x, y, z))
    me.update()

    faces_in = len(me.polygons)
    mod = obj.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = min(1.0, DEC_FACES / max(1, faces_in))
    dg = bpy.context.evaluated_depsgraph_get()
    me_out = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(mod)
    me_out.name = entry["name"]
    bpy.data.objects.remove(obj, do_unlink=True)
    info = {"faces_in": faces_in, "faces_out": len(me_out.polygons),
            "dims_fbx": [round(dx, 4), round(dy, 4), round(dz, 4)],
            "scale_xy_yz_z": [round(sx, 4), round(sy, 4), round(sz, 4)]}
    return me_out, info


def main():
    opt = parse_args()
    manifest = json.loads(open(opt.manifest, encoding="utf-8").read())
    clear_scene()
    scene = bpy.context.scene
    coll = scene.collection

    lisa = [e["name"] for e in manifest["slabs"] if e["rol"] == "lisa"][0]
    especiales = [e["name"] for e in manifest["slabs"] if e["rol"] == "especial"]
    n_esp = int(manifest["especiales_por_bloque"])
    mat_joint = make_flat_material("mortar", (0.0030, 0.0025, 0.0020))

    mesh_A, mesh_B, info = {}, {}, {}
    for e in manifest["slabs"]:
        me, inf = process_slab(e)
        info[e["name"]] = inf
        me.materials.clear()
        me.materials.append(make_stone_material(f"stone_A_{e['name']}", e["a_png"]))
        mesh_A[e["name"]] = me
        mb = me.copy()
        mb.name = e["name"] + "_B"
        mb.materials.clear()
        mb.materials.append(make_stone_material(f"stone_B_{e['name']}", e["b_png"]))
        mesh_B[e["name"]] = mb

    # Bloque 128 px = 2 familias x 8 filas x 4 rombos. Lisa en todas salvo n_esp celdas especiales.
    rng = random.Random(opt.seed)
    sites = rng.sample([("A", iy, ix) for iy in range(8) for ix in range(4)]
                       + [("B", iy, ix) for iy in range(8) for ix in range(4)], n_esp)
    grid = {}
    for fam, iy, ix in sites:
        grid[(fam, iy, ix)] = rng.choice(especiales)
    var_A = [[grid.get(("A", iy, ix), lisa) for ix in range(4)] for iy in range(8)]
    var_B = [[grid.get(("B", iy, ix), lisa) for ix in range(4)] for iy in range(8)]
    names = [lisa] + especiales
    counts = {n: 0 for n in names}

    W_b = 128.0 / PXM
    D_b = 128.0 / PYM
    for bx in (-1, 0, 1):
        for by in (-1, 0, 1):
            base_x = bx * W_b
            base_y = by * D_b
            for iy in range(8):
                cy_m = base_y + (iy * 16 + 8 - 64.0) / PYM
                for ix in range(4):
                    cx_m = base_x - (ix * 32 + 16 - 64.0) / PXM
                    n = var_A[iy][ix]
                    counts[n] += 1 if (bx, by) == (0, 0) else 0
                    ob = bpy.data.objects.new(f"A_{bx}_{by}_{iy}_{ix}", mesh_A[n])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)
            for iy in range(8):
                cy_m = base_y + (iy * 16 - 64.0) / PYM
                for ix in range(4):
                    cx_m = base_x - (ix * 32 - 64.0) / PXM
                    n = var_B[iy][ix]
                    counts[n] += 1 if (bx, by) == (0, 0) else 0
                    ob = bpy.data.objects.new(f"B_{bx}_{by}_{iy}_{ix}", mesh_B[n])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)

    # Juntas: plano de fondo oscuro hundido (mismo criterio que el procedural)
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
    coll.objects.link(bpy.data.objects.new("joint_ground", me_g))

    # Cuatro triangulos en Z=0 para que la caja del GLB coincida con el bloque 3x3
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
    coll.objects.link(bpy.data.objects.new("ref_corners", me_ref))

    placement = {"counts_bloque_central": counts, "slabs": info, "seed": opt.seed}
    with open(opt.out + ".placement.json", "w", encoding="utf-8") as f:
        json.dump(placement, f, indent=2)

    bpy.ops.export_scene.gltf(filepath=opt.out, export_format="GLB")
    print("BLENDER_EXPORT_OK:", opt.out)


if __name__ == "__main__":
    main()
