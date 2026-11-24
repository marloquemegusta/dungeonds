"""Campana del campanero con la lengua de Simon de badajo: animacion de tanido para el Codice (videos de lore).

Modelo: assets/models/characters/campanero/source/campana/*.fbx (se le quita el badajo de cuerda y se le cuelga
una lengua humana de una tira de cuero). Se ve desde abajo en 3/4 (campana columpiada hacia la camara: se ve la
boca, la lengua tendida sobre el borde y goteando hacia fuera). 10 fotogramas: balanceo de +-14 grados y un golpe
de la lengua contra el borde.

Salida: assets/sprites/bestiary/campana_lengua/dirs/0_S.gif + settings.json (celda 160x160, como campanero_toque).

  python tools/props/build_campana_lengua.py [--keep DIR] [--yaw 30] [--tilt 68] [--frame N]

Pasos: 1) Blender (-b) genera un GLB por fotograma (campana posada + lengua en malla); 2) el lab (node) renderiza
cada uno con la camara/luz de los sprites; 3) proceso de `prerender_props.process` (alfa 1 bit, contraste c2) con un
recorte y una escala comunes a todos los fotogramas, ya al tamano final (sin encoger despues).
"""
import argparse, json, math, os, subprocess, sys, tempfile

try:
    import bpy  # dentro de Blender
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
FBX = os.path.join(ROOT, "assets/models/characters/campanero/source/campana/tripo_convert_af5a0caa-ab69-4b69-a2ed-1cacfb7efe3a.fbx")
OUT_NAME = "campana_lengua"
N_FRAMES = 10
CLAP_ANG = [-4, -8, -10, -3, 14, 5, -4, -8, -6, -4]   # giro del badajo respecto a la campana (grados); positivo = hacia el borde cercano (golpe)
CELL = 320
FIT = 314          # lado mayor (px) que ocupa la union de los fotogramas dentro de la celda
TONGUE = (0.016, 0.004, 0.008)      # carne rojo oscuro apagado
STRAP = (0.02, 0.012, 0.008)       # cuero


def frame_params(i, tilt, yaw):
    """(inclinacion de la campana, guiñada, 'elevacion' de la punta de la lengua) del fotograma i."""
    ph = 2 * math.pi * i / N_FRAMES
    t = tilt + 10.0 * math.sin(ph)
    y = yaw + 7.0 * math.cos(ph)
    # el golpe: la lengua se despega del borde hacia arriba y cae de nuevo (picos en los fotogramas 4-5)
    lift = 0.0
    for c, a in ((4.0, 1.0), (5.0, 0.55), (3.0, 0.35)):
        lift += a * math.exp(-((i - c) ** 2) / 0.9)
    return t, y, min(lift, 1.0)


# ------------------------------------------------------------------ Blender
def blender_prep(out_dir, tilt, yaw, only=None):
    import bmesh
    from mathutils import Vector, Matrix

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX)
    bell0 = [o for o in bpy.data.objects if o.type == "MESH"][0]
    bpy.context.view_layer.objects.active = bell0
    bell0.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me0 = bell0.data
    bm = bmesh.new(); bm.from_mesh(me0)
    # el modelo ya cuelga con la boca abajo (corona y yugo en z=1)
    # fuera el badajo de cuerda: se siembra en su eje y se expande por las aristas dentro de un cilindro estrecho
    def rad(v):
        return (v.co.x ** 2 + v.co.y ** 2) ** 0.5
    # eje del badajo original (z, x, y), medido sobre la malla
    AX = [(0.0, 0.01, -0.27), (0.2, 0.0, -0.13), (0.3, -0.02, -0.07), (0.4, 0.0, -0.05),
          (0.5, -0.02, 0.04), (0.6, -0.03, 0.03), (0.75, -0.05, 0.10)]
    def axis_at(z):
        for k in range(len(AX) - 1):
            z0, z1 = AX[k][0], AX[k + 1][0]
            if z0 <= z <= z1:
                f = (z - z0) / (z1 - z0)
                return (AX[k][1] + f * (AX[k + 1][1] - AX[k][1]), AX[k][2] + f * (AX[k + 1][2] - AX[k][2]))
        return None
    def near_axis(v):
        a = axis_at(v.co.z)
        if a is None:
            return False
        r = ((v.co.x - a[0]) ** 2 + (v.co.y - a[1]) ** 2) ** 0.5
        return r < (0.055 if v.co.z < 0.1 else 0.12)
    def near_c(v):
        a = axis_at(v.co.z)
        if a is None or v.co.z > 0.76:
            return False
        r = ((v.co.x - a[0]) ** 2 + (v.co.y - a[1]) ** 2) ** 0.5
        return r < (0.10 if v.co.z < 0.1 else 0.13)
    bm.verts.ensure_lookup_table()
    seeds = [v for v in bm.verts if 0.3 < v.co.z < 0.5 and axis_at(v.co.z) and
             ((v.co.x - axis_at(v.co.z)[0]) ** 2 + (v.co.y - axis_at(v.co.z)[1]) ** 2) ** 0.5 < 0.06]
    seen = set(v.index for v in seeds)
    stack = list(seeds)
    while stack:
        v = stack.pop()
        for e in v.link_edges:
            w = e.other_vert(v)
            if w.index not in seen and near_c(w):
                seen.add(w.index); stack.append(w)
    print("badajo: verts", len(seen), flush=True)
    # badajo original aparte (para balancearlo respecto a la campana): copia solo con sus caras
    bm2 = bm.copy(); bm2.verts.ensure_lookup_table(); bm2.faces.ensure_lookup_table()
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if not all(v.index in seen for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm2, geom=[v for v in bm2.verts if not v.link_faces], context="VERTS")
    clap_me = bpy.data.meshes.new("badajo"); bm2.to_mesh(clap_me); bm2.free()
    for m in me0.materials:
        clap_me.materials.append(m)
    clap0 = bpy.data.objects.new("badajo", clap_me)
    bpy.context.scene.collection.objects.link(clap0)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.index in seen for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me0); bm.free()
    # opaco (un alfa conectado sale como manchas negras en el lab)
    for m in me0.materials:
        m.use_backface_culling = False   # se mira por dentro de la boca: las caras interiores deben dibujarse
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                for l in list(m.node_tree.links):
                    if l.to_node == n and l.to_socket.name == "Alpha":
                        m.node_tree.links.remove(l)
    pivot_z = 1.0          # el yugo: la campana se columpia sobre el eje X por la corona

    def mat(name, col):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1)
        b.inputs["Roughness"].default_value = 0.55
        return m
    m_tongue, m_strap = mat("lengua", TONGUE), mat("cuero", STRAP)

    def sweep(path, widths, thick, side, mats, n_ring=10):
        """Malla barrida: elipse de ancho w y grosor th a lo largo de `path` (lista de Vector)."""
        bmx = bmesh.new()
        rings = []
        for k, p in enumerate(path):
            a = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]
            a.normalize()
            sd = (side - a * side.dot(a)); sd.normalize()
            nm = a.cross(sd); nm.normalize()
            w, th = widths[k], thick[k]
            ring = []
            for j in range(n_ring):
                ang = 2 * math.pi * j / n_ring
                ring.append(bmx.verts.new(p + sd * (math.cos(ang) * w) + nm * (math.sin(ang) * th)))
            rings.append(ring)
        for k in range(len(rings) - 1):
            for j in range(n_ring):
                f = bmx.faces.new((rings[k][j], rings[k][(j + 1) % n_ring], rings[k + 1][(j + 1) % n_ring], rings[k + 1][j]))
                f.material_index = mats[k]
        bmx.faces.new(rings[-1][::-1]).material_index = mats[-1]
        bmx.faces.new(rings[0]).material_index = mats[0]
        bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces)
        for f in bmx.faces:
            f.smooth = True
        me = bpy.data.meshes.new("lengua")
        bmx.to_mesh(me); bmx.free()
        me.materials.append(m_strap); me.materials.append(m_tongue)
        ob = bpy.data.objects.new("lengua", me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    P = Vector((0, 0.0, 0.74))      # punto de atadura, bajo el casquete
    Q = Vector((0, 0.285, 0.34))   # donde la tira acaba y empieza la lengua, apoyada en la pared de abajo
    R = Vector((0, 0.345, 0.0))    # borde inferior de la boca
    jobs = []
    for i in range(N_FRAMES):
        if only is not None and i != only:
            continue
        t, y, lift = frame_params(i, tilt, yaw)
        M = (Matrix.Rotation(math.radians(y), 4, "Z") @ Matrix.Translation((0, 0, pivot_z))
             @ Matrix.Rotation(-math.radians(t), 4, "X") @ Matrix.Translation((0, 0, -pivot_z)))
        # campana
        bell = bell0.copy(); bell.data = me0
        bpy.context.scene.collection.objects.link(bell)
        bell.matrix_world = M
        # lengua en el sistema de la campana (se pasa a mundo con M); la parte libre cae por gravedad en mundo
        wP, wQ, wR = M @ P, M @ Q, M @ R
        pts = [wP + (wQ - wP) * (k / 3.0) for k in range(4)]                 # tira de cuero P->Q
        n_in = 5
        pts += [wQ + (wR - wQ) * ((k + 1) / n_in) for k in range(n_in)]      # lengua pegada a la pared hasta el borde
        d = (wR - wQ).normalized()
        down = Vector((0, 0, -1))
        out_len, n_out = 0.36, 6
        g0 = 0.30 * (1.0 - lift) - 0.15 * lift          # la lengua cuelga; en el golpe se levanta
        cur = wR
        for k in range(n_out):
            frac = (k + 1) / n_out
            gk = max(-0.2, g0 * (0.4 + 1.2 * frac))
            d = (d * (1 - abs(gk)) + (down if gk >= 0 else -down) * abs(gk)).normalized() if gk != 0 else d
            cur = cur + d * (out_len / n_out)
            pts.append(cur)
        npts = len(pts)
        widths, thick, mats = [], [], []
        for k in range(npts):
            if k < 4:
                widths.append(0.018); thick.append(0.018); mats.append(0)
            else:
                u = (k - 3) / (npts - 4.0)             # 0 empieza la lengua, 1 la punta
                w = 0.04 + 0.05 * min(1.0, u * 2.2)
                if u > 0.82:
                    w *= math.sqrt(max(0.0, (1.0 - u) / 0.18))   # punta redondeada
                widths.append(max(w, 0.012)); thick.append(max(0.034 * (1.0 - 0.35 * u), 0.012)); mats.append(1)
        side = M.to_3x3() @ Vector((1, 0, 0))
        tg = sweep(pts, widths, thick, side, mats)
        # a ras de suelo (lab) y centrado: el mismo desplazamiento en todos los fotogramas
        cl = clap0.copy(); cl.data = clap_me
        bpy.context.scene.collection.objects.link(cl)
        CP = Vector((-0.05, 0.10, 0.75))
        ang = math.radians(CLAP_ANG[i % len(CLAP_ANG)])
        cl.matrix_world = M @ Matrix.Translation(CP) @ Matrix.Rotation(ang, 4, "X") @ Matrix.Translation(-CP)
        jobs.append((i, bell, tg, cl))
    lift_z = 0.6    # la misma subida en todos los fotogramas (la campana cuelga sobre el suelo del lab)
    for i, bell, tg, cl in jobs:
        bell.matrix_world = Matrix.Translation((0, 0, lift_z)) @ bell.matrix_world
        cl.matrix_world = Matrix.Translation((0, 0, lift_z)) @ cl.matrix_world
        tg.matrix_world = Matrix.Identity(4)
        for v in tg.data.vertices:
            v.co.z += lift_z
        bpy.ops.object.select_all(action="DESELECT")
        bell.select_set(True); cl.select_set(True)
        bpy.context.view_layer.objects.active = bell
        for ob in bpy.data.objects:
            ob.hide_set(ob not in (bell, cl))
        bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, f"{OUT_NAME}_{i}.glb"), export_format="GLB",
                                  export_yup=True, export_image_format="AUTO", export_materials="EXPORT",
                                  use_selection=False, use_visible=True)
        for ob in (bell, cl):
            ob.hide_set(True)


if IN_BLENDER and "--prep" in sys.argv:
    a = sys.argv[sys.argv.index("--prep") + 1:]
    blender_prep(a[0], float(a[1]), float(a[2]), int(a[3]) if len(a) > 3 and a[3] != "-" else None)
    sys.exit(0)


# ------------------------------------------------------------------ host
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", help="carpeta de trabajo (GLB y renders del lab)")
    ap.add_argument("--yaw", type=float, default=115.0)
    ap.add_argument("--tilt", type=float, default=50.0)
    ap.add_argument("--frame", type=int, help="solo un fotograma (prueba minima)")
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "sprites", "bestiary", OUT_NAME))
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    import numpy as np
    import prerender_props as pp
    from PIL import Image
    tmp = a.keep or tempfile.mkdtemp(prefix="campana_lengua_")
    os.makedirs(os.path.join(tmp, "glb"), exist_ok=True)
    subprocess.run([BLENDER, "-b", "-P", os.path.abspath(__file__), "--", "--prep", os.path.join(tmp, "glb"),
                    str(a.tilt), str(a.yaw), str(a.frame) if a.frame is not None else "-"], check=True,
                   stdout=subprocess.DEVNULL)
    settings = json.load(open(os.path.join(ROOT, "tools/props/props_render_settings.json")))
    settings["width"] = 1536
    settings["lighting"] = {"preset": "neutral", "world": 0.7}
    settings["shadows"] = False   # con la sombra propia el interior de la campana sale negro (0,0,0) y se pierde como fondo
    sf = os.path.join(tmp, "settings.json")
    json.dump(settings, open(sf, "w"))
    pp.PROPS = tmp
    raws = os.path.join(tmp, "raw")
    os.makedirs(raws, exist_ok=True)
    idx = [a.frame] if a.frame is not None else list(range(N_FRAMES))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(3) as ex:
        dirs = list(ex.map(lambda i: pp.run_lab(f"{OUT_NAME}_{i}", raws, sf, "c2"), idx))
    masks = [pp.silhouette(d) for d in dirs]
    ys = [np.nonzero(m)[0] for m in masks]; xs = [np.nonzero(m)[1] for m in masks]
    x0, x1 = min(x.min() for x in xs), max(x.max() for x in xs) + 1
    y0, y1 = min(y.min() for y in ys), max(y.max() for y in ys) + 1
    bw, bh = int(x1 - x0), int(y1 - y0)
    print("union bbox raw", (int(x0), int(y0), int(x1), int(y1)), "size", bw, bh, flush=True)
    sc = FIT / max(bw, bh)
    nw, nh = max(1, round(bw * sc)), max(1, round(bh * sc))
    ox, oy = (CELL - nw) // 2, (CELL - nh) // 2
    frames = []
    for d, mask in zip(dirs, masks):
        world = np.array(Image.open(os.path.join(d, "world.png")).convert("RGB"))[y0:y1, x0:x1].astype(np.float32)
        m = mask[y0:y1, x0:x1].astype(np.float32)
        chans = [np.array(Image.fromarray(world[..., c] * m, mode="F").resize((nw, nh), Image.LANCZOS)) for c in range(3)]
        am = np.array(Image.fromarray(m, mode="F").resize((nw, nh), Image.BOX))
        al = am >= 0.30
        rgb = np.clip(np.stack(chans, -1) / np.maximum(am[..., None], 1e-3), 0, 255).astype(np.uint8)
        rgba = np.zeros((nh, nw, 4), np.uint8)
        rgba[..., :3] = rgb * al[..., None]
        rgba[..., 3] = al * 255
        if al.any():
            rgba[..., :3][al] = pp.soft_contrast(rgba[..., :3][al].astype(float)[None], 1.45)[0].astype(np.uint8)
            rgba = pp.sharpen_rgba(rgba, 0.5)
        cell = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
        cell.paste(Image.fromarray(rgba), (ox, oy))
        frames.append(cell)
    os.makedirs(os.path.join(a.out, "dirs"), exist_ok=True)
    # GIF: el fondo transparente es el indice 0; ningun pixel del sprite es negro puro (el generador usa RGB>0 como mascara)
    gif = []
    for f in frames:
        arr = np.array(f)
        solid = arr[..., 3] > 0
        arr[..., :3][solid] = np.maximum(arr[..., :3][solid], 1)
        g = Image.fromarray(arr, "RGBA")
        p = g.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = p.getpalette()
        pal = [0, 0, 0] + pal[:255 * 3]
        q = np.array(p).astype(np.uint8) + 1
        q[~solid] = 0
        im = Image.fromarray(q, "P"); im.putpalette(pal[:768] + [0] * (768 - len(pal[:768])))
        im.info["transparency"] = 0
        gif.append(im)
    if a.frame is None:
        gif[0].save(os.path.join(a.out, "dirs", "0_S.gif"), save_all=True, append_images=gif[1:], duration=130,
                    loop=0, transparency=0, disposal=2)
        cfg = {"name": OUT_NAME, "model": "campana (Tripo) + lengua en malla", "animation": "tanido (10 fotogramas)",
               "directions": ["S"], "dirsRendered": ["S"], "framesPerDirection": N_FRAMES,
               "frameSize": f"{CELL}x{CELL}", "spritesheet": None, "anchor": [CELL // 2, CELL // 2],
               "ticksPerFrame": 8, "inPlace": True, "cameraElevationDegrees": 30, "contrast": 1.2, "saturation": 1.0,
               "legibility": "c2", "renderEngine": "Lab (node) via build_campana_lengua.py",
               "tiltDegrees": a.tilt, "yawDegrees": a.yaw, "fitPx": FIT}
        json.dump(cfg, open(os.path.join(a.out, "settings.json"), "w"), indent=2)
    sheet = Image.new("RGBA", (CELL * 5 * 4, CELL * ((len(frames) + 4) // 5) * 4), (24, 24, 28, 255))
    for k, f in enumerate(frames):
        big = f.resize((CELL * 4, CELL * 4), Image.NEAREST)
        sheet.alpha_composite(big, ((k % 5) * CELL * 4, (k // 5) * CELL * 4))
    sheet.convert("RGB").save(os.path.join(tmp, "sheet.png"))
    print("hoja", os.path.join(tmp, "sheet.png"), "tmp", tmp)


if __name__ == "__main__":
    main()
