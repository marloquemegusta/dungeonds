"""Base comun de los prototipos del remate del Exvoto (ronda 2): escena, escala real, pose, render y utilidades.

No se ejecuta solo: lo importan proto_remate_exvoto_v2.py y las pruebas (Blender headless, vista diagonal).

Escala REAL del juego (assets/sprites/characters/*/settings.json): una celda de 40 px cubre extent/fitZoom metros.
  Corazon: 1.8116 / 0.86 = 2.107 m -> 18.99 px/m.   Exvoto: 2.0392 / 0.86 = 2.371 m -> 16.87 px/m.
Una sola camara a 18.99 px/m; el Exvoto se escala 16.87/18.99 = 0.888 para respetar su tamano de juego.
"""
import bpy, sys, os, math, random
import bmesh
from mathutils import Vector, Matrix

V = Vector
P = 'mixamorig:'
MAIN = 'C:/codexlocal/dungeonds'
PPM = 40.5
EX_K = 0.677
CELL = 64
SS = 4
ELEV = 30.0
AZ = 45.0
LIGHT = 'FLAT'
CAP_COLOR = (0.44, 0.35, 0.24, 1.0)


def update():
    bpy.context.view_layer.update()


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def load_action(path, short):
    ab = set(bpy.data.actions)
    new = load(path)
    a = [x for x in bpy.data.actions if x not in ab][0]
    a.use_fake_user = True
    a.name = short
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return a


class Char:
    pass


def make_char(fbx, rz_deg, scale, loc):
    c = Char()
    new = load(fbx)
    c.arm = [o for o in new if o.type == 'ARMATURE'][0]
    c.mesh = [o for o in new if o.type == 'MESH'][0]
    c.root = bpy.data.objects.new('root', None)
    bpy.context.scene.collection.objects.link(c.root)
    c.arm.parent = c.root
    c.root.scale = (scale, scale, scale)
    c.root.rotation_euler = (0, 0, math.radians(rz_deg))
    c.root.location = loc
    for pb in c.arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return c


ACT = {}


def load_acts(root):
    ACT['hero_walk'] = load_action(root + '/assets/models/animations/corazon/walk.fbx', 'hero_walk')
    ACT['hero_shot'] = load_action(root + '/assets/models/animations/corazon/disparo.fbx', 'hero_shot')
    ACT['ex_walk'] = load_action(MAIN + '/assets/models/characters/exvoto/exvoto_walk.fbx', 'ex_walk')
    ACT['ex_pray'] = load_action(MAIN + '/assets/models/characters/exvoto/exvoto_pray_stand.fbx', 'ex_pray')


def capture(ch, key, frame):
    act = ACT[key]
    ch.arm.animation_data_create()
    ch.arm.animation_data.action = act
    try:
        ch.arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(frame)
    update()
    d = {pb.name: pb.matrix_basis.copy() for pb in ch.arm.pose.bones}
    ch.arm.animation_data.action = None
    return d


def apply_basis(ch, d):
    for pb in ch.arm.pose.bones:
        pb.matrix_basis = d[pb.name]
    update()


def W(ch):
    return ch.arm.matrix_world


def bone_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].matrix


def set_bone_world(ch, name, Mw):
    ch.arm.pose.bones[P + name].matrix = W(ch).inverted() @ Mw
    update()


def head_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].head


def tail_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].tail


def xform_about(pivot, rot_x=0.0, rot_y=0.0, rot_z=0.0, trans=(0, 0, 0)):
    R = Matrix.Rotation(math.radians(rot_z), 4, 'Z') @ Matrix.Rotation(math.radians(rot_y), 4, 'Y') \
        @ Matrix.Rotation(math.radians(rot_x), 4, 'X')
    return Matrix.Translation(V(trans)) @ Matrix.Translation(pivot) @ R @ Matrix.Translation(-V(pivot))


def rot_bone(ch, name, rx=0.0, ry=0.0, rz=0.0):
    """Gira el hueso (y sus hijos) alrededor de su cabeza, en ejes de mundo."""
    Mw = bone_world(ch, name)
    set_bone_world(ch, name, xform_about(Mw.translation.copy(), rx, ry, rz) @ Mw)


def add_ik(ch, bone, name, chain=2):
    t = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(t)
    c = ch.arm.pose.bones[P + bone].constraints.new('IK')
    c.target = t
    c.chain_count = chain
    c.use_tail = True
    c.use_stretch = False
    c.influence = 0.0
    return t, c


def aim_bone(ch, name, target_world, roll_free=True):
    """Apunta el eje Y del hueso (cabeza->cola) hacia un punto de mundo (sin IK: rotacion directa, longitud intacta)."""
    Mw = bone_world(ch, name)
    head = Mw.translation.copy()
    cur = (Mw.to_3x3() @ V((0, 1, 0))).normalized()
    want = (target_world - head).normalized()
    q = cur.rotation_difference(want).to_matrix().to_4x4()
    set_bone_world(ch, name, Matrix.Translation(head) @ q @ Matrix.Translation(-head) @ Mw)


# ----------------------------------------------------------------------------------------------- materiales y luz
def srgb_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


GLB_GAIN = float(os.environ.get("REMATE_GLB_GAIN", "1.0"))  # factor solo para el color que va al GLB (no toca el Workbench)


def flat_mat(name, col):
    """col en sRGB 0-1 (lo que se quiere ver ANTES de la ganancia de la post, 1.38x); se convierte a lineal para Blender."""
    m = bpy.data.materials.new(name)
    lin = (srgb_lin(col[0]), srgb_lin(col[1]), srgb_lin(col[2]), 1.0)
    m.diffuse_color = lin  # Workbench
    # Mismo color en el Principled BSDF: es lo que lee el exportador glTF (laboratorio web). GLB_GAIN ajusta solo el GLB.
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf is not None:
        g = GLB_GAIN
        bsdf.inputs['Base Color'].default_value = (min(lin[0] * g, 1.0), min(lin[1] * g, 1.0), min(lin[2] * g, 1.0), 1.0)
        bsdf.inputs['Roughness'].default_value = 0.9
        bsdf.inputs['Metallic'].default_value = 0.0
        for k in ('Specular IOR Level', 'Specular'):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = 0.0
    return m


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = LIGHT
    sh.color_type = 'TEXTURE'
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_specular_highlight = False
    sc.display.render_aa = '8'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = CELL * SS
    sc.render.resolution_y = CELL * SS
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    cd = bpy.data.cameras.new('cam')
    cd.type = 'ORTHO'
    cd.ortho_scale = CELL / PPM
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def place_cam(cam, center, az=AZ, elev=ELEV):
    a, e = math.radians(az), math.radians(elev)
    pos = center + V((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 8.0
    cam.location = pos
    cam.rotation_euler = (center - pos).to_track_quat('-Z', 'Y').to_euler()


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def new_disc(name, mat):
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=1.0, fill_type='NGON', location=(0, 0, 0.002))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    o.hide_render = True
    return o


# ----------------------------------------------------------------------------------------------- partir la malla por un plano
def cut_halves(ch, plane_co_w, plane_no_w, jag_amp=0.012, cap_color=CAP_COLOR, names=('A', 'B')):
    """Parte la malla (en reposo) por un plano de mundo. Devuelve (objeto_lado_positivo, objeto_lado_negativo).
    Los dos objetos comparten armature (pesos intactos) y llevan una cara de corte con material 'cera_corte'."""
    me = ch.mesh
    update()
    M = me.matrix_world
    Mi = M.inverted()
    p_l = Mi @ plane_co_w
    n_l = (M.to_3x3().transposed() @ plane_no_w).normalized()
    # base del plano para el diente de sierra
    t1 = n_l.cross(V((0, 0, 1)))
    if t1.length < 0.1:
        t1 = n_l.cross(V((1, 0, 0)))
    t1.normalize()
    t2 = n_l.cross(t1).normalized()
    cap_mat = flat_mat('cera_corte', cap_color)
    out = []
    for nm, clear_inner in ((names[0], True), (names[1], False)):
        bm = bmesh.new()
        bm.from_mesh(me.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=p_l, plane_no=n_l,
                                     clear_inner=clear_inner, clear_outer=not clear_inner)
        cut = res['geom_cut']
        cverts = [g for g in cut if isinstance(g, bmesh.types.BMVert)]
        cedges = [g for g in cut if isinstance(g, bmesh.types.BMEdge)]
        for v in cverts:
            d = v.co - p_l
            u, w = d.dot(t1), d.dot(t2)
            j = math.sin(u * 55.0 + 1.3) * 0.6 + math.sin(w * 41.0) * 0.4
            v.co += n_l * (jag_amp * j)
        # la malla es una tela hueca: el corte solo deja contornos finos. Se rellena la seccion con la envolvente convexa de cada
        # componente conectado del corte (cera maciza por dentro), reutilizando vertices existentes (conservan sus pesos).
        parent = {v.index: v.index for v in cverts}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for e in cedges:
            a_, b_ = find(e.verts[0].index), find(e.verts[1].index)
            if a_ != b_:
                parent[a_] = b_
        comps = {}
        for v in cverts:
            comps.setdefault(find(v.index), []).append(v)
        from mathutils.geometry import convex_hull_2d
        slot = len(me.data.materials)
        sign = -1.0 if clear_inner else 1.0
        newf = []
        for vs in comps.values():
            if len(vs) < 3:
                continue
            pts = [V(((vv.co - p_l).dot(t1), (vv.co - p_l).dot(t2))) for vv in vs]
            hull = convex_hull_2d(pts)
            if len(hull) < 3:
                continue
            for k in range(1, len(hull) - 1):
                try:
                    f = bm.faces.new((vs[hull[0]], vs[hull[k]], vs[hull[k + 1]]))
                except ValueError:
                    continue
                f.material_index = slot
                if f.normal.dot(n_l) * sign < 0:
                    f.normal_flip()
                newf.append(f)
        print('CUT', nm, 'cut edges', len(cedges), 'components', len(comps), 'cap faces', len(newf))
        bm.normal_update()
        nmesh = bpy.data.meshes.new('half_' + nm)
        bm.to_mesh(nmesh)
        bm.free()
        for m in me.data.materials:
            nmesh.materials.append(m)
        nmesh.materials.append(cap_mat)
        ob = me.copy()
        ob.data = nmesh
        for g in me.vertex_groups:
            if g.name not in ob.vertex_groups:
                ob.vertex_groups.new(name=g.name)
        ob.name = 'half_' + nm
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = me.parent
        ob.matrix_parent_inverse = me.matrix_parent_inverse.copy()
        out.append(ob)
    me.hide_render = True
    me.hide_viewport = True
    return out[0], out[1]


# ----------------------------------------------------------------------------------------------- post
def tone_to_game(img, gain):
    """Aclara RGB (el render de Workbench sale mas oscuro que los sprites del juego) conservando alfa."""
    from PIL import Image
    r, g, b, a = img.split()
    f = lambda v: min(255, int(v * gain))
    return Image.merge('RGBA', (r.point(f), g.point(f), b.point(f), a))
