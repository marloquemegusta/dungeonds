# Variante "arco pasante" del modulo gothic_arch: el arco ciego (panel apuntado en relieve) se recorta de lado a lado,
# de la peana al apice, y las caras del corte (intrados y jambas) se pintan del color medio de la piedra de la textura.
# Uso: blender -b -P arco_pasante.py -- <gothic_arch.fbx> <salida.glb> [<prefijo_png_de_prueba>]
# Reutilizable: from-exec en wall_back_glb.py (define load_module / cut_arch).
import bpy, sys, math, bmesh

STONE_SRGB = (107/255, 100/255, 87/255)   # mediana de gothic_arch_3d_model_basecolor.PNG
HALF_W = 0.105      # semiancho del hueco (m del modulo original, 0.407 de ancho): dentro de la moldura interior (+-0.115)
SPRING = 0.55       # altura donde acaban las jambas rectas y empieza el apuntado
APEX = 0.862        # altura del apice (el relieve ciego llega a 0.87)
FLOOR = -0.02       # el corte baja hasta el suelo (atraviesa la peana)

def srgb_to_lin(c): return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4

def load_module(fbx):
    sc = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=fbx)
    src = [o for o in sc.objects if o.type == 'MESH'][0]
    for o in list(sc.objects):
        if o is not src: bpy.data.objects.remove(o)
    src.parent = None
    bpy.context.view_layer.objects.active = src; src.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for m in src.data.materials:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                for l in list(m.node_tree.links):
                    if l.to_node == n and l.to_socket.name == 'Metallic': m.node_tree.links.remove(l)
                n.inputs['Metallic'].default_value = 0
    return src

def cut_arch(src, half_w=HALF_W, spring=SPRING, apex=APEX):
    """Resta a `src` un prisma con perfil de arco apuntado que lo atraviesa en Y."""
    h = apex - spring
    R = (h*h + half_w*half_w) / (2*half_w)      # radio de cada arco; el centro del izquierdo esta en x=+(R-half_w)
    pts = [(-half_w, FLOOR), (half_w, FLOOR), (half_w, spring)]
    n = 14
    cx = -(R - half_w)                          # arco derecho: centro a la izquierda
    a0 = math.atan2(0, half_w - cx); a1 = math.atan2(h, -cx)
    for i in range(1, n):
        a = a0 + (a1-a0)*i/n; pts.append((cx + R*math.cos(a), spring + R*math.sin(a)))
    pts.append((0, apex))
    cx = R - half_w                             # arco izquierdo: centro a la derecha
    b0 = math.atan2(h, -cx); b1 = math.atan2(0, -half_w - cx)
    for i in range(1, n):
        a = b0 + (b1-b0)*i/n; pts.append((cx + R*math.cos(a), spring + R*math.sin(a)))
    pts.append((-half_w, spring))
    bm = bmesh.new()
    y0, y1 = -0.2, 0.2
    v0 = [bm.verts.new((x, y0, z)) for x, z in pts]
    v1 = [bm.verts.new((x, y1, z)) for x, z in pts]
    bm.faces.new(v0[::-1]); bm.faces.new(v1)
    for i in range(len(pts)):
        j = (i+1) % len(pts); bm.faces.new((v0[i], v0[j], v1[j], v1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('cut'); bm.to_mesh(me); bm.free()
    cut = bpy.data.objects.new('cut', me); bpy.context.scene.collection.objects.link(cut)
    stone = bpy.data.materials.new('intrados')
    stone.use_nodes = True
    p = [n for n in stone.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    p.inputs['Base Color'].default_value = tuple(srgb_to_lin(c) for c in STONE_SRGB) + (1,)
    p.inputs['Roughness'].default_value = 0.9
    src.data.materials.append(stone)
    cut.data.materials.append(stone)
    for poly in cut.data.polygons: poly.material_index = 1
    md = src.modifiers.new('b', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cut; md.solver = 'EXACT'
    try: md.material_mode = 'INDEX'
    except Exception: pass
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.modifier_apply(modifier='b')
    bpy.data.objects.remove(cut)
    return src

if __name__ == '__main__' and '--' in sys.argv:
    a = sys.argv[sys.argv.index('--')+1:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    src = cut_arch(load_module(a[0]))
    bpy.ops.export_scene.gltf(filepath=a[1], export_format='GLB', export_yup=True, export_materials='EXPORT', use_selection=False)
    print("EXPORTED", a[1])
    if len(a) > 2:
        sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
        sc.render.resolution_x = 500; sc.render.resolution_y = 750
        cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.2
        for nm, loc, rot in (('front', (0, -5, 0.5), (90, 0, 0)), ('oblic', (3.5, -3.5, 2.5), (65, 0, 45))):
            cam.location = loc; cam.rotation_euler = [math.radians(r) for r in rot]
            sc.render.filepath = a[2] + '_' + nm + '.png'; bpy.ops.render.render(write_still=True)
