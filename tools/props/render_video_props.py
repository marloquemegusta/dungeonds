"""Re-renderiza los props de la catedral a la densidad de pixel de los sprites del Codice (videos de lore).

Los PNG de `props/render/` son de la DS (el heroe mide 31 px); los sprites del Codice miden ~140 px.
Aqui se vuelven a renderizar desde el modelo 3D con la misma camara/luz del juego (lab) y un ancho
objetivo multiplicado por K = altura de Elias en el Codice / 31 px.

Salida: assets/videos/props/<prop>/color.png (+ shadow.png, meta.json con la altura en metros).

  python tools/props/render_video_props.py [--solo columna_entera,vela] [--k 4.4]

Pasos: 1) Blender (-b) prepara un GLB por prop (yaw, apoyado en el suelo, variantes por codigo:
banco_volcado = banco_entero tumbado, banco_roto = banco_entero partido) en una carpeta temporal;
2) el lab (node) lo renderiza; 3) se reduce con el proceso de `prerender_props.process` (alfa 1 bit,
contraste c2); 4) se pintan la llama de `vela` y la sombra.
Fuentes: .fbx en `assets/models/environment/cathedral/props/` (worktree assets-manifiesto o repo
principal) y los .glb de lapidas en `assets/environment/cathedral/props/glb/` del repo principal.
"""
import argparse, json, math, os, subprocess, sys, tempfile

try:
    import bpy  # dentro de Blender
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAIN = "C:/codexlocal/dungeonds"
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUT = os.path.join(ROOT, "assets", "videos", "props")
GAME_HERO_PX = 31.0   # el heroe mide 2 m = 31 px en el juego (TECHNICAL.md, escala personaje/mapa)
HERO_M = 2.0

FBX_DIRS = [os.path.join(r, "assets", "models", "environment", "cathedral", "props")
            for r in (ROOT, MAIN, MAIN + "/.worktrees/assets-manifiesto")]
GLB_DIRS = [os.path.join(r, "assets", "environment", "cathedral", "props", "glb") for r in (ROOT, MAIN)]

# name: fuente, yaw, ancho a escala de juego (px), variante, extras
PROPS = {
    "columna_entera": {"src": "columna_antigua_7b241e8d", "yaw": 0, "w": 35, "shadow_elevation": 17},
    "banco_entero": {"src": "banco_gotico_c2b65edd", "yaw": -45, "w": 64, "shadow_elevation": 50},
    "banco_roto": {"src": "banco_gotico_c2b65edd", "yaw": -45, "w": 72, "variant": "roto"},
    "banco_volcado": {"src": "banco_gotico_c2b65edd", "yaw": -45, "w": 72, "variant": "volcado"},
    # vela: 14 px de juego x 0,45 (una vela votiva real, ~0,35 m, no el cirio del modelo). Se renderiza ya al tamano final
    # (antes 14 y el generador la encogia x0,45, lo que afinaba su pixel respecto al de los sprites del Codice).
    "vela": {"src": "vela_derretida_cb025b38", "yaw": 0, "w": 6.3, "keep_largest": True, "flame": True, "flame_k": 0.45},
    "vela_apagada": {"src": "vela_derretida_cb025b38", "yaw": 0, "w": 6.3, "keep_largest": True},
    "relicario": {"src": "relicario_7db9333c", "yaw": 45, "w": 32},
    "santo": {"src": "estatua_caballero_c83faa86", "yaw": 180, "w": 32, "shadow_elevation": 35},
    "lapida_cruz_h": {"glb": "lapida_cruz_v2.glb", "yaw": 45, "w": 64},
    "lapida_cruz_v": {"glb": "lapida_cruz_v2.glb", "yaw": -45, "w": 53},
    "lapida_caballero_h": {"glb": "lapida_caballero_v2.glb", "yaw": 45, "w": 64},
}


def find_fbx(src):
    for d in FBX_DIRS:
        p = os.path.join(d, src)
        if os.path.isdir(p):
            for f in os.listdir(p):
                if f.lower().endswith(".fbx"):
                    return os.path.join(p, f)
    raise FileNotFoundError(src)


# ------------------------------------------------------------------ Blender
def blender_prep(out_dir, jobs):
    import bmesh
    from mathutils import Vector

    def comps(bm):
        seen, res = set(), []
        for v in bm.verts:
            if v.index in seen:
                continue
            st, c = [v], []
            seen.add(v.index)
            while st:
                a = st.pop()
                c.append(a)
                for e in a.link_edges:
                    b = e.other_vert(a)
                    if b.index not in seen:
                        seen.add(b.index)
                        st.append(b)
            res.append(c)
        return res

    def bounds(obj):
        vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
        return (Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)]))

    def apply(obj):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    for name, c in jobs.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if c.get("fbx"):
            bpy.ops.import_scene.fbx(filepath=c["fbx"])
        else:
            bpy.ops.import_scene.gltf(filepath=c["glb"])
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        obj = meshes[0]
        for o in meshes[1:]:
            bpy.data.objects.remove(o)
        apply(obj)
        if c.get("keep_largest"):
            bm = bmesh.new(); bm.from_mesh(obj.data)
            cs = sorted(comps(bm), key=len, reverse=True)
            bmesh.ops.delete(bm, geom=[v for k in cs[1:] for v in k], context="VERTS")
            bm.to_mesh(obj.data); bm.free()
        mn, mx = bounds(obj)
        d = mx - mn
        variant = c.get("variant")
        if variant:
            # eje largo horizontal del banco (X o Y); u = coordenada a lo largo, centrada
            ax = 0 if d.x >= d.y else 1
            ctr = (mn + mx) / 2
            if variant == "volcado":
                # tumbado sobre el respaldo: 90 grados alrededor del eje largo
                rot = (math.radians(90), 0, 0) if ax == 0 else (0, math.radians(90), 0)
                obj.rotation_euler = rot
                apply(obj)
            elif variant == "roto":
                L = d[ax]
                g = L * 0.07
                bm = bmesh.new(); bm.from_mesh(obj.data)
                no = Vector((1, 0, 0)) if ax == 0 else Vector((0, 1, 0))
                for s in (-g, g):
                    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
                    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=ctr + no * s, plane_no=no)
                bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs((f.calc_center_median() - ctr)[ax]) < g - 1e-4],
                                 context="FACES")
                bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
                # mitad derecha hundida en el centro, mitad izquierda casi en pie
                pivot = ctr[ax] + L / 2
                ang = math.radians(16)
                for v in bm.verts:
                    u = v.co[ax] - ctr[ax]
                    if u > 0:
                        r = pivot - v.co[ax]           # distancia al extremo exterior
                        v.co.z -= math.sin(ang) * r * 0.9
                        v.co[ax] += (math.cos(ang) - 1) * r * -1 * 0.0
                    else:
                        r = v.co[ax] - (ctr[ax] - L / 2)
                        v.co.z -= math.sin(math.radians(5)) * r * 0.9
                bm.to_mesh(obj.data); bm.free()
        obj.rotation_euler = (0, 0, math.radians(c["yaw"]))
        apply(obj)
        mn, mx = bounds(obj)
        obj.location = Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))
        apply(obj)
        for m in obj.data.materials:   # opaco: un alfa conectado sale como manchas negras
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    for l in list(m.node_tree.links):
                        if l.to_node == n and l.to_socket.name == "Alpha":
                            m.node_tree.links.remove(l)
        mn, mx = bounds(obj)
        dims = [round(x, 4) for x in (mx - mn)]
        print("DIMS", name, dims, flush=True)
        with open(os.path.join(out_dir, name + ".dims.json"), "w") as f:
            json.dump(dims, f)
        bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, name + ".glb"), export_format="GLB",
                                  export_yup=True, export_image_format="AUTO", export_materials="EXPORT")


if IN_BLENDER and "--prep" in sys.argv:
    a = sys.argv[sys.argv.index("--prep") + 1:]
    blender_prep(a[0], json.load(open(a[1])))
    sys.exit(0)


# ------------------------------------------------------------------ host
def hero_px():
    """Altura (px) de Elias en el Codice: mediana de los fotogramas de corazon_walk 0_S."""
    from PIL import Image
    import numpy as np
    im = Image.open(os.path.join(ROOT, "assets", "sprites", "bestiary", "corazon_walk", "dirs", "0_S.gif"))
    hs = []
    for i in range(im.n_frames):
        im.seek(i)
        bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
        bg.alpha_composite(im.convert("RGBA"))
        ys = np.nonzero((np.array(bg.convert("RGB")).max(2) > 30).any(1))[0]
        hs.append(int(ys.max() - ys.min() + 1))
    hs.sort()
    return hs[len(hs) // 2]


def draw_flame(rgba_img, k):
    """Llama apagada (paleta desaturada del juego) sobre la mecha mas alta de la vela."""
    from PIL import Image, ImageDraw
    import numpy as np
    a = np.array(rgba_img)[..., 3] > 0
    ys, xs = np.nonzero(a)
    top = ys.min()
    # mecha = columna mas alta; si hay varias, la central de las del 10 % superior
    cand = xs[ys <= top + max(1, int(0.08 * (ys.max() - top)))]
    cx = int(np.median(cand))
    w, h = max(3, int(round(2.2 * k))), max(5, int(round(4.2 * k)))
    pad = h + 2
    im = Image.new("RGBA", (rgba_img.width, rgba_img.height + pad), (0, 0, 0, 0))
    im.paste(rgba_img, (0, pad))
    d = ImageDraw.Draw(im)
    y1 = top + pad            # base de la llama sobre la cera
    for (sx, sy, col) in ((1.0, 1.0, (150, 82, 40, 255)), (0.62, 0.78, (205, 150, 78, 255)),
                          (0.3, 0.5, (226, 205, 150, 255))):
        ww, hh = max(1, int(w * sx / 2)), int(h * sy)
        d.polygon([(cx - ww, y1), (cx, y1 - hh), (cx + ww, y1)], fill=col)
        d.ellipse([cx - ww, y1 - int(hh * 0.45), cx + ww, y1 + 1], fill=col)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", help="props separados por coma")
    ap.add_argument("--k", type=float, help="factor sobre la escala del juego (por defecto: Elias del Codice / 31)")
    ap.add_argument("--keep", help="carpeta temporal donde dejar GLB y renders del lab")
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    import prerender_props as pp
    import prop_shadows as ps
    from PIL import Image
    names = a.solo.split(",") if a.solo else list(PROPS)
    hp = hero_px()
    k = a.k or hp / GAME_HERO_PX
    print(f"Elias en el Codice: {hp} px; juego {GAME_HERO_PX:.0f} px -> K = {k:.3f}")
    tmp = a.keep or tempfile.mkdtemp(prefix="video_props_")
    os.makedirs(tmp, exist_ok=True)
    jobs = {}
    for n in names:
        c = dict(PROPS[n])
        if "src" in c:
            c["fbx"] = find_fbx(c["src"])
        else:
            c["glb"] = next(os.path.join(d, c["glb"]) for d in GLB_DIRS if os.path.exists(os.path.join(d, c["glb"])))
        jobs[n] = c
    jf = os.path.join(tmp, "jobs.json")
    json.dump(jobs, open(jf, "w"))
    subprocess.run([BLENDER, "-b", "-P", os.path.abspath(__file__), "--", "--prep", tmp, jf], check=True,
                   stdout=subprocess.DEVNULL)
    settings = json.load(open(os.path.join(ROOT, "tools/props/props_render_settings.json")))
    settings["width"] = 1536   # mas resolucion de origen: el reescalado grande no se ve borroso
    sf = os.path.join(tmp, "settings.json")
    json.dump(settings, open(sf, "w"))
    pp.PROPS = tmp   # run_lab busca PROPS/glb/<n>.glb
    os.makedirs(os.path.join(tmp, "glb"), exist_ok=True)
    for n in names:
        g = os.path.join(tmp, n + ".glb")
        os.replace(g, os.path.join(tmp, "glb", n + ".glb"))
    raws = os.path.join(tmp, "raw")
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(raws, exist_ok=True)
    with ThreadPoolExecutor(3) as ex:
        dirs = dict(zip(names, ex.map(lambda n: pp.run_lab(n, raws, sf, "c2"), names)))
    for n in names:
        c = PROPS[n]
        cfg = {"yaw": c["yaw"], "target_width": int(round(c["w"] * k)), "footprint_from": None}
        meta = pp.process(n, cfg, dirs[n], OUT, "c2")
        od = os.path.join(OUT, n)
        for junk in ("footprint.png", "depth.png"):
            if os.path.exists(os.path.join(od, junk)):
                os.remove(os.path.join(od, junk))
        dims = json.load(open(os.path.join(tmp, n + ".dims.json")))
        col = Image.open(os.path.join(od, "color.png")).convert("RGBA")
        if not n.startswith("lapida_"):   # las lapidas van a ras de suelo: sin sombra
            sh_cfg = os.path.join(tmp, "shadow_cfg.json")
            json.dump({n: {"shadow_elevation": c["shadow_elevation"]} if "shadow_elevation" in c else {}}, open(sh_cfg, "w"))
            ps.PROPS_JSON, ps.RENDER, ps.GLB_DIR = sh_cfg, OUT, os.path.join(tmp, "glb")
            ps.MARGIN_SCALE_TOL = max(k, 1.0)
            ps.MARGIN_SCALE = 100.0   # sin tope de margen: aqui no hay retícula de suelo
            ps.process(n)
        if c.get("flame"):
            col = draw_flame(col, k * c.get("flame_k", 1.0))   # la llama sigue la escala de la vela
            pad = col.height - Image.open(os.path.join(od, "color.png")).height
            col.save(os.path.join(od, "color.png"))
            m2 = json.load(open(os.path.join(od, "meta.json")))
            if "shadow_offset_px" in m2:   # el lienzo de color crecio por arriba
                m2["shadow_offset_px"][1] += pad
                m2["size_px"][1] += pad
                m2["content_px"][1] += pad
                json.dump(m2, open(os.path.join(od, "meta.json"), "w"), indent=2)
            meta = {**meta, **{kk: m2[kk] for kk in ("shadow_offset_px", "shadow_canvas_px", "size_px", "content_px") if kk in m2}}
        bb = col.getchannel("A").getbbox()
        ppm = hp / HERO_M   # px por metro vertical (Elias = 2 m); el GLB de Tripo no esta en metros
        meta.update({"video_k": round(k, 3), "alto_px": bb[3] - bb[1], "px_por_m": round(ppm, 2),
                     "alto_m": round((bb[3] - bb[1]) / ppm, 2), "hero_px": hp})
        with open(os.path.join(od, "meta.json"), "w", newline="") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
        print(n, col.size, "alto", bb[3] - bb[1], "px =", meta["alto_m"], "m")


if __name__ == "__main__":
    main()
