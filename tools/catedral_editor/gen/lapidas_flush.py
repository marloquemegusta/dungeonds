#!/usr/bin/env python3
"""Blender headless: construccion de bloque de suelo con lapidas integradas 3D (Via A y Via B).

Pipeline unificado para Three.js Shader Lab:
- Reconstruye el damero de rombos identico a rombos_tripo_blender.py (576 losas en 3x3 bloques).
- Identifica las N x M o N x N teselas a sustituir en el centro (u, v).
- Omite esas teselas y en su lugar crea una UNICA losa de piedra continua con la junta oficial (JOINT=0.026 m).
- Incrusta el modelo 3D de la lapida (cruz o caballero) en la losa:
    * Via A: orientada a lo largo del eje del rectangulo diagonal (3x2 teselas = 80x40 px).
    * Via B: rotada 45 deg respecto a los bordes de la losa para quedar horizontal en pantalla (3x3 teselas = 96x48 px).
- Sin rebordes artificiales, sin cajeados oscuros, sin 2D outline:
  la lapida ES el relieve en la losa de piedra.
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
s = Dx / math.sqrt(2.0)  # 1.264099 m
JOINT = 0.026
s_inset = s - JOINT
SLAB_THICK = 0.015
BASE_Z = -0.012
DEC_FACES = 1200


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--kind", choices=["via_a", "via_b"], required=True)
    p.add_argument("--lapida", required=True)
    p.add_argument("--tiles-n", type=int, default=3)
    p.add_argument("--tiles-m", type=int, default=2)
    p.add_argument("--vertical", type=int, default=0)
    p.add_argument("--relief-h", type=float, default=0.10,
                   help="Altura del relieve esculpido sobre la losa en metros (defecto 0.10 m = 10 cm)")
    p.add_argument("--seed", type=int, default=20261108)
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
        raise RuntimeError(f"lapida {path}: no se importo ninguna malla")
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


def make_large_slab(x0, x1, y0, y1, mat_stone):
    """Crea una losa solida cubriendo [x0, x1] x [y0, y1] con cara superior en z=0 y grosor SLAB_THICK."""
    bm = bmesh.new()
    # 4 vertices superiores
    v0 = bm.verts.new((x0, y0, 0.0))
    v1 = bm.verts.new((x1, y0, 0.0))
    v2 = bm.verts.new((x1, y1, 0.0))
    v3 = bm.verts.new((x0, y1, 0.0))
    # 4 vertices inferiores
    v4 = bm.verts.new((x0, y0, -SLAB_THICK))
    v5 = bm.verts.new((x1, y0, -SLAB_THICK))
    v6 = bm.verts.new((x1, y1, -SLAB_THICK))
    v7 = bm.verts.new((x0, y1, -SLAB_THICK))

    f_top = bm.faces.new((v0, v1, v2, v3))
    bm.faces.new((v7, v6, v5, v4))  # bottom
    bm.faces.new((v0, v4, v5, v1))  # front
    bm.faces.new((v1, v5, v6, v2))  # right
    bm.faces.new((v2, v6, v7, v3))  # back
    bm.faces.new((v3, v7, v4, v0))  # left

    # UV mapping en f_top continuo con el suelo
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for loop in f_top.loops:
        loop[uv_layer].uv = (loop.vert.co.x / s, loop.vert.co.y / s)

    me = bpy.data.meshes.new("tombstone_base_slab")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_stone)
    obj = bpy.data.objects.new("tombstone_base_slab", me)
    return obj


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

    # Mismo sorteo que rombos_tripo
    rng = random.Random(opt.seed)
    sites = rng.sample([("A", iy, ix) for iy in range(8) for ix in range(4)]
                       + [("B", iy, ix) for iy in range(8) for ix in range(4)], n_esp)
    grid = {}
    for fam, iy, ix in sites:
        grid[(fam, iy, ix)] = rng.choice(especiales)
    var_A = [[grid.get(("A", iy, ix), lisa) for ix in range(4)] for iy in range(8)]
    var_B = [[grid.get(("B", iy, ix), lisa) for ix in range(4)] for iy in range(8)]

    # Determinar el conjunto de teselas a sustituir S_replace en coordenadas (u, v)
    N = opt.tiles_n
    M = opt.tiles_m
    if opt.kind == "via_a":
        # Via A: N x M teselas centradas en (0, 0)
        # N filas a lo largo de u (longitud), M columnas a lo largo de v (anchura)
        u_min = -(N // 2)
        u_max = u_min + N - 1
        v_min = 0 if M == 2 else -(M // 2)
        v_max = v_min + M - 1
    else:
        # Via B: N x N teselas centradas en (0, 0)
        u_min = -(N // 2)
        u_max = u_min + N - 1
        v_min = -(N // 2)
        v_max = v_min + N - 1
        M = N

    s_replace = {(u, v) for u in range(u_min, u_max + 1) for v in range(v_min, v_max + 1)}
    print(f"Modo {opt.kind}: N={N}, M={M}. Teselas sustituidas: {len(s_replace)}. u:[{u_min},{u_max}], v:[{v_min},{v_max}]")

    W_b = 128.0 / PXM
    D_b = 128.0 / PYM
    slab_objs = []
    skipped_count = 0

    for bx in (-1, 0, 1):
        for by in (-1, 0, 1):
            base_x = bx * W_b
            base_y = by * D_b
            # Familia A
            for iy in range(8):
                cy_m = base_y + (iy * 16 + 8 - 64.0) / PYM
                for ix in range(4):
                    cx_m = base_x - (ix * 32 + 16 - 64.0) / PXM
                    # Coordenadas (u, v) rotadas
                    xr = (cx_m + cy_m) / math.sqrt(2.0)
                    yr = (-cx_m + cy_m) / math.sqrt(2.0)
                    u = int(round(yr / s))
                    v = int(round(xr / s))
                    if (u, v) in s_replace:
                        skipped_count += 1
                        continue
                    ob = bpy.data.objects.new(f"A_{bx}_{by}_{iy}_{ix}", mesh_A[var_A[iy][ix]])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)
                    slab_objs.append(ob)

            # Familia B
            for iy in range(8):
                cy_m = base_y + (iy * 16 - 64.0) / PYM
                for ix in range(4):
                    cx_m = base_x - (ix * 32 - 64.0) / PXM
                    xr = (cx_m + cy_m) / math.sqrt(2.0)
                    yr = (-cx_m + cy_m) / math.sqrt(2.0)
                    u = int(round(yr / s))
                    v = int(round(xr / s))
                    if (u, v) in s_replace:
                        skipped_count += 1
                        continue
                    ob = bpy.data.objects.new(f"B_{bx}_{by}_{iy}_{ix}", mesh_B[var_B[iy][ix]])
                    ob.location = (cx_m, cy_m, 0.0)
                    coll.objects.link(ob)
                    slab_objs.append(ob)

    print(f"Colocadas {len(slab_objs)} losas del suelo. Omitidas {skipped_count} teselas para la lapida.")

    # Plano de mortero continuo
    bm_g = bmesh.new()
    bmesh.ops.create_grid(bm_g, x_segments=1, y_segments=1, size=1.0)
    for vert in bm_g.verts:
        vert.co.x *= 1.5 * W_b
        vert.co.y *= 1.5 * D_b
        vert.co.z = BASE_Z
    me_g = bpy.data.meshes.new("joint_ground")
    bm_g.to_mesh(me_g)
    bm_g.free()
    me_g.materials.append(mat_mortar)
    mortar = bpy.data.objects.new("joint_ground", me_g)
    coll.objects.link(mortar)

    # Cuatro triangulos en Z=0 para referencia de encuadre en el lab
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

    # Rotar todo el damero, mortero y referencia por -45 deg alrededor de Z
    Rz = Matrix.Rotation(math.radians(-45), 3, "Z")
    done = set()
    for ob in slab_objs + [mortar, ref]:
        if id(ob.data) not in done:
            for vert in ob.data.vertices:
                vert.co = Rz @ vert.co
            ob.data.update()
            done.add(id(ob.data))
        ob.location = Rz @ ob.location

    # Ahora en el espacio rotado (x', y'):
    # Cada tesela esta centrada en (v*s, u*s) con caras en [x - s_inset/2, x + s_inset/2].
    # El hueco dejado por s_replace abarca exactamente:
    #   x' de (v_min - 0.5)*s a (v_max + 0.5)*s
    #   y' de (u_min - 0.5)*s a (u_max + 0.5)*s
    x_hole_min = (v_min - 0.5) * s
    x_hole_max = (v_max + 0.5) * s
    y_hole_min = (u_min - 0.5) * s
    y_hole_max = (u_max + 0.5) * s

    # Aplicamos la junta oficial JOINT/2 en cada borde
    x_slab_min = x_hole_min + JOINT / 2.0
    x_slab_max = x_hole_max - JOINT / 2.0
    y_slab_min = y_hole_min + JOINT / 2.0
    y_slab_max = y_hole_max - JOINT / 2.0

    slab_w = x_slab_max - x_slab_min
    slab_l = y_slab_max - y_slab_min
    slab_cx = (x_slab_min + x_slab_max) / 2.0
    slab_cy = (y_slab_min + y_slab_max) / 2.0

    print(f"Losa continua: W={slab_w:.3f} m, L={slab_l:.3f} m, centro=({slab_cx:.3f}, {slab_cy:.3f})")

    # Crear la losa continua de piedra con el material de losa_a
    mat_losa_a = mesh_A["losa_a"].materials[0]
    base_slab = make_large_slab(x_slab_min, x_slab_max, y_slab_min, y_slab_max, mat_losa_a)
    coll.objects.link(base_slab)

    # Importar e incrustar la lapida
    lap = import_lapida(opt.lapida)
    # Centrar la malla de la lapida en su bounding box nativo
    mn, mx = bbox(lap)
    cx = (mn[0] + mx[0]) / 2.0
    cy = (mn[1] + mx[1]) / 2.0
    z_min = mn[2]
    # Mover pivote al centro en XY y base a Z=0
    for v in lap.data.vertices:
        v.co.x -= cx
        v.co.y -= cy
        v.co.z -= z_min
    lap.data.update()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    mn, mx = bbox(lap)
    dx = mx[0] - mn[0]
    dy = mx[1] - mn[1]
    dz = mx[2] - mn[2]
    print(f"Lapida importada: dx={dx:.3f}, dy={dy:.3f}, dz={dz:.3f}")

    # Escala y rotacion segun la via elegida
    if opt.kind == "via_a":
        # Via A: la losa es rectangular a 45 deg respecto a la pantalla (paralela a los ejes x', y')
        # La lapida va alineada con el eje largo (y')
        scale_xy = min((0.85 * slab_w) / dx, (0.85 * slab_l) / dy)
        # GIRO (2026-11-11): cabeza / travesano hacia el fondo de la pantalla (se lee desde los pies)
        rot_z = 0.0
    else:
        # Via B: la losa es un rombo/cuadrado en x', y'.
        # La lapida se incrusta rotada 45 deg para alinearse con la diagonal horizontal en pantalla
        if opt.vertical == 1:
            rot_z = math.radians(45)   # vertical en pantalla
        else:
            rot_z = math.radians(-45)  # horizontal en pantalla

        # Ajuste de escala para que la lapida quepa dentro del rombo sin salirse
        # Caja proyectada rotada 45 deg: (dx + dy) / sqrt(2) * scale <= 0.88 * slab_w
        scale_xy = (0.85 * slab_w) / ((dx + dy) / math.sqrt(2.0))
        # Tope de escala razonable (longitud ~ 2.5 m)
        scale_xy = min(scale_xy, 2.6)

    # Altura del relieve esculpido sobre la losa
    target_relief_h = max(0.01, opt.relief_h)
    scale_z = target_relief_h / dz

    if opt.kind == "via_a":
        # FILL (2026-11-11): la piedra tallada ocupa el bloque entero de NxM losas, borde en las juntas
        lap.scale = (slab_w / dx, slab_l / dy, scale_z)
    else:
        lap.scale = (scale_xy, scale_xy, scale_z)
    bpy.ops.object.transform_apply(scale=True)

    # Rotacion si aplica
    if abs(rot_z) > 1e-4:
        lap.rotation_euler = (0.0, 0.0, rot_z)
        bpy.ops.object.transform_apply(rotation=True)

    # Posicion: centrado en la losa, con la base ligeramente hundida (-0.005 m) en la losa
    # FLUSH (2026-11-11): la cara superior de la lapida queda a ras del suelo (z = 0) y la talla hacia abajo.
    lap.location = (slab_cx, slab_cy, -target_relief_h)
    base_slab.location.z -= target_relief_h + 0.02
    # Hueco en el mortero bajo el bloque (si no, el plano a BASE_Z tapa la talla hundida)
    import bmesh as _bm
    me = mortar.data; bmm = _bm.new(); bmm.from_mesh(me)
    _bm.ops.subdivide_edges(bmm, edges=bmm.edges[:], cuts=0)
    bmm.free()
    cutter_me = bpy.data.meshes.new("cutter"); bc = _bm.new()
    _bm.ops.create_cube(bc, size=1.0); bc.to_mesh(cutter_me); bc.free()
    cutter = bpy.data.objects.new("cutter", cutter_me); bpy.context.scene.collection.objects.link(cutter)
    cutter.location = (slab_cx, slab_cy, BASE_Z); cutter.scale = (slab_w, slab_l, 0.2)
    mod = mortar.modifiers.new("hole", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cutter; mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = mortar
    for o in bpy.context.scene.objects: o.select_set(o is mortar)
    bpy.ops.object.modifier_apply(modifier="hole")
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.ops.object.transform_apply(location=True)

    # Informacion de montaje
    mn_final, mx_final = bbox(lap)
    info = {
        "kind": opt.kind, "N": N, "M": M,
        "slab_w_m": round(slab_w, 4), "slab_l_m": round(slab_l, 4),
        "scale_xy": round(scale_xy, 4), "scale_z": round(scale_z, 4),
        "lapida_bbox_final": [round(mx_final[i] - mn_final[i], 4) for i in range(3)],
        "lapida_z_range": [round(mn_final[2], 4), round(mx_final[2], 4)],
        "skipped_tiles": skipped_count
    }
    with open(opt.out + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    bpy.ops.export_scene.gltf(filepath=opt.out, export_format="GLB")
    print("BLENDER_EXPORT_OK:", opt.out, info)


if __name__ == "__main__":
    main()
