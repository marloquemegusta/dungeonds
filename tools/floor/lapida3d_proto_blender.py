"""Blender headless: damero de rombos de Tripo con UNA lapida hundida en un hueco.

Misma construccion que tools/floor/rombos_tripo_blender.py (losas, texturas A/B, patron, junta con
plano de mortero y caja de referencia 3x3), de modo que al renderizar con el mismo pipeline el bloque
coincide con floor/rombos_tripo. Cambios:
  - Las losas y el mortero se giran -45 (como el giro global del suelo) ANTES de tallar, y el hueco se
    resta con la huella EXACTA de la lapida (cuchilla = contorno aplanado + solidificado). Asi la
    lapida encaja y no queda rendija.
  - La lapida se deja en su pose natural (la del sprite) y se hunde `--sink` metros.
  - El plano de mortero evita ver el fondo entre losas (juntas como el damero real).
Sin sombra pintada: la de contacto la produce el borde de las losas con la luz real.

Usage:
  blender -b --factory-startup --python-exit-code 1 -P tools/floor/lapida3d_proto_blender.py -- \
     --manifest <manifest.json> --lapida <glb> --scale S --sink 0.08 --out <path.glb>
"""
import argparse
import json
import math
import random
import sys

import bmesh
import bpy
from mathutils import Matrix

PXM = 17.9
PYM = 8.95
Dx = 32.0 / PXM
s = Dx / math.sqrt(2.0)
JOINT = 0.026
s_inset = s - JOINT
SLAB_THICK = 0.015
BASE_Z = -0.012
DEC_FACES = 1200
HOLE_SCALE = 0.94          # hueco ~ volumen de la lapida (la losa apenas solapa el borde, sin tapar el relieve)


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--lapida", required=True)
    p.add_argument("--scale", type=float, required=True)
    p.add_argument("--sink", type=float, default=0.08)
    p.add_argument("--plate-texture", required=True)
    p.add_argument("--out", required=True)
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


def make_flat_material(name, rgb, roughness=0.9):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_plate_material(name, png, repeat, roughness=0.88):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png.replace("\\", "/"), check_existing=False)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (repeat, repeat, 1.0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def process_slab(entry):
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
        z = (co.z - zmin) * sz - SLAB_THICK
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
    return me_out


def import_lapida(path):
    before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=path.replace("\\", "/"))
    added = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in added if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("lapida: no se importo ninguna malla")
    obj = meshes[0]
    for o in added:
        if o is not obj:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def bbox(obj):
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    mn = [min(v[i] for v in vs) for i in range(3)]
    mx = [max(v[i] for v in vs) for i in range(3)]
    return mn, mx


def make_cutter(src, mortar):
    cut = bpy.data.objects.new("cutter", src.data.copy())
    bpy.context.scene.collection.objects.link(cut)
    for v in cut.data.vertices:
        v.co.x *= HOLE_SCALE
        v.co.y *= HOLE_SCALE
        v.co.z = 0.0
    cut.data.update()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = cut
    cut.select_set(True)
    sol = cut.modifiers.new("sol", "SOLIDIFY")
    sol.thickness = 0.6
    sol.offset = -1.0
    bpy.ops.object.modifier_apply(modifier="sol")
    mn, mx = bbox(cut)
    print("CUTTER dims", [round(mx[i] - mn[i], 3) for i in range(3)], "verts", len(cut.data.vertices))
    cut.data.materials.clear()
    cut.data.materials.append(mortar)
    return cut


def main():
    opt = parse_args()
    manifest = json.loads(open(opt.manifest, encoding="utf-8").read())
    clear_scene()
    scene = bpy.context.scene
    coll = scene.collection
    mat_mortar = make_flat_material("mortar", (0.0030, 0.0025, 0.0020))

    lisa = [e["name"] for e in manifest["slabs"] if e["rol"] == "lisa"][0]
    especiales = [e["name"] for e in manifest["slabs"] if e["rol"] == "especial"]
    n_esp = int(manifest["especiales_por_bloque"])
    mesh_A, mesh_B = {}, {}
    for e in manifest["slabs"]:
        me = process_slab(e)
        me.materials.clear()
        me.materials.append(make_stone_material(f"stone_A_{e['name']}", e["a_png"]))
        mesh_A[e["name"]] = me
        mb = me.copy()
        mb.name = e["name"] + "_B"
        mb.materials.clear()
        mb.materials.append(make_stone_material(f"stone_B_{e['name']}", e["b_png"]))
        mesh_B[e["name"]] = mb

    rng = random.Random(20261108)
    sites = rng.sample([("A", iy, ix) for iy in range(8) for ix in range(4)]
                       + [("B", iy, ix) for iy in range(8) for ix in range(4)], n_esp)
    grid = {}
    for fam, iy, ix in sites:
        grid[(fam, iy, ix)] = rng.choice(especiales)
    var_A = [[grid.get(("A", iy, ix), lisa) for ix in range(4)] for iy in range(8)]
    var_B = [[grid.get(("B", iy, ix), lisa) for ix in range(4)] for iy in range(8)]

    W_b = 128.0 / PXM
    D_b = 128.0 / PYM
    slab_objs = []
    for bx in (-1, 0, 1):
        for by in (-1, 0, 1):
            base_x = bx * W_b
            base_y = by * D_b
            for iy in range(8):
                cy_m = base_y + (iy * 16 + 8 - 64.0) / PYM
                for ix in range(4):
                    cx_m = base_x - (ix * 32 + 16 - 64.0) / PXM
                    ob = bpy.data.objects.new(f"A_{bx}_{by}_{iy}_{ix}", mesh_A[var_A[iy][ix]])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)
                    slab_objs.append(ob)
            for iy in range(8):
                cy_m = base_y + (iy * 16 - 64.0) / PYM
                for ix in range(4):
                    cx_m = base_x - (ix * 32 - 64.0) / PXM
                    ob = bpy.data.objects.new(f"B_{bx}_{by}_{iy}_{ix}", mesh_B[var_B[iy][ix]])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)
                    slab_objs.append(ob)

    # Plano de junta (mortero) como el suelo: caja fina con tope en BASE_Z
    bm_g = bmesh.new()
    bmesh.ops.create_grid(bm_g, x_segments=1, y_segments=1, size=1.0)
    for v in bm_g.verts:
        v.co.x *= 1.5 * W_b
        v.co.y *= 1.5 * D_b
        v.co.z = BASE_Z
    me_g = bpy.data.meshes.new("joint_ground")
    bm_g.to_mesh(me_g)
    bm_g.free()
    me_g.materials.append(mat_mortar)
    mortar = bpy.data.objects.new("joint_ground", me_g)
    coll.objects.link(mortar)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = mortar
    mortar.select_set(True)
    mg = mortar.modifiers.new("thick", "SOLIDIFY")
    mg.thickness = 0.02
    mg.offset = -1.0
    bpy.ops.object.modifier_apply(modifier="thick")
    mortar.select_set(False)

    # Caja de referencia identica al suelo
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
    me_ref.materials.append(mat_mortar)
    ref = bpy.data.objects.new("ref_corners", me_ref)
    coll.objects.link(ref)

    # Girar -45 (como el giro global del suelo) a losas + mortero + referencia
    Rz = Matrix.Rotation(math.radians(-45), 3, "Z")
    done = set()
    for ob in slab_objs + [mortar, ref]:
        if id(ob.data) not in done:
            for v in ob.data.vertices:
                v.co = Rz @ v.co
            ob.data.update()
            done.add(id(ob.data))
        ob.location = Rz @ ob.location

    # Lapida en su pose natural (la del sprite), centrada, tope en z=0
    lap = import_lapida(opt.lapida)
    lap.scale = (opt.scale, opt.scale, opt.scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mn, mx = bbox(lap)
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
    lap.location = (-cx, -cy, -mx[2])
    bpy.ops.object.transform_apply(location=True)
    mn, mx = bbox(lap)
    footprint = [round(mx[0] - mn[0], 4), round(mx[1] - mn[1], 4)]
    print("LAPIDA dims", [round(mx[i] - mn[i], 3) for i in range(3)],
          "min", [round(v, 3) for v in mn], "max", [round(v, 3) for v in mx])

    cut = make_cutter(lap, mat_mortar)

    # Restar el hueco de las losas y del mortero
    cut_targets = 0
    for ob in list(coll.objects):
        if ob.type != "MESH" or ob is lap:
            continue
        is_slab = ob.name[0] in "AB"
        if not is_slab and ob is not mortar:
            continue
        if is_slab and math.hypot(ob.location.x, ob.location.y) > 6.0:
            continue
        ob.data = ob.data.copy()
        md = ob.modifiers.new("hole", "BOOLEAN")
        md.operation = "DIFFERENCE"
        md.solver = "EXACT"
        md.object = cut
        md.material_mode = "TRANSFER"
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        try:
            bpy.ops.object.modifier_apply(modifier="hole")
        except RuntimeError as exc:
            print("boolean skip", ob.name, exc)
        ob.select_set(False)
        cut_targets += 1
    bpy.data.objects.remove(cut, do_unlink=True)

    # Placa de piedra que rellena el hueco (opcion A): cubre todo el fondo, losa_a algo mas clara
    plate_half = 2.6
    plate_z = (-abs(opt.sink) - 0.035) if opt.sink > 0 else -0.02
    bm_p = bmesh.new()
    bmesh.ops.create_grid(bm_p, x_segments=1, y_segments=1, size=1.0)
    uvl = bm_p.loops.layers.uv.new("UVMap")
    for f in bm_p.faces:
        for lp in f.loops:
            lp[uvl].uv = (lp.vert.co.x * 0.5 + 0.5, lp.vert.co.y * 0.5 + 0.5)
    for v in bm_p.verts:
        v.co.x *= plate_half
        v.co.y *= plate_half
        v.co.z = plate_z
    me_p = bpy.data.meshes.new("hole_plate")
    bm_p.to_mesh(me_p)
    bm_p.free()
    me_p.materials.append(make_plate_material("plate_stone", opt.plate_texture, 4.0))
    coll.objects.link(bpy.data.objects.new("hole_plate", me_p))

    # Dar un poco de canto a la lapida (para que proyecte sombra como solido)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = lap
    lap.select_set(True)
    solb = lap.modifiers.new("base", "SOLIDIFY")
    solb.thickness = 0.06
    solb.offset = -1.0
    bpy.ops.object.modifier_apply(modifier="base")
    lap.select_set(False)

    # Hundir (sink > 0) o elevar (sink < 0) la lapida respecto al tope de las losas
    mn, mx = bbox(lap)
    lap.location = (0.0, 0.0, -opt.sink - mx[2])
    bpy.ops.object.transform_apply(location=True)
    lap.name = "lapida_sunk"

    info = {"scale": opt.scale, "sink_m": opt.sink, "lapida_footprint_m": footprint,
            "cut_targets": cut_targets, "joint_m": JOINT}
    with open(opt.out + ".compose.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    bpy.ops.export_scene.gltf(filepath=opt.out, export_format="GLB")
    print("BLENDER_EXPORT_OK:", opt.out, info)


if __name__ == "__main__":
    main()
