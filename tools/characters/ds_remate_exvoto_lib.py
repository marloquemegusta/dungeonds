"""Base comun para las animaciones de remate del heroe sobre el Exvoto (ronda 2, salida ds_).

Copia propia (prefijo ds_) de la base ya validada tools/characters/proto_remate_exvoto_common.py, con la celda ancha que
necesitan las tres opciones, la escala real del juego y utilidades extra (gotas de cera, manchas, velo, pase de sombra).

No se ejecuta solo: lo importan ds_remate_exvoto.py (Blender headless, vista diagonal) y ds_remate_exvoto_post.py.

Escala REAL: celda de juego 40x40 px; el heroe mide 0.93 m y ocupa ~30 px -> 32.3 px/m. Con la celda de la remate
(72x56 px) y PPM 30 el heroe ocupa 28 px y entra el arco alto de la opcion C.
"""
import bpy, sys, os, math, random
import bmesh
from mathutils import Vector, Matrix

V = Vector
P = 'mixamorig:'
MAIN = 'C:/codexlocal/dungeonds'
PPM = 30.0
EX_K = 0.60
CELL = (72, 56)
SS = 4
ELEV = 30.0
AZ = 45.0
LIGHT = 'FLAT'
CAP_COLOR = (0.48, 0.37, 0.24, 1.0)


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
    ACT['ex_kneel'] = load_action(MAIN + '/assets/models/characters/exvoto/exvoto_pray_kneel.fbx', 'ex_kneel')


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


def aim_bone(ch, name, target_world):
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


def flat_mat(name, col):
    """col en sRGB 0-1 (lo que se quiere ver ANTES de la ganancia de la post); se convierte a lineal para Blender."""
    m = bpy.data.materials.new(name)
    m.diffuse_color = (srgb_lin(col[0]), srgb_lin(col[1]), srgb_lin(col[2]), 1.0)
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
    sc.render.resolution_x = CELL[0] * SS
    sc.render.resolution_y = CELL[1] * SS
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    cd = bpy.data.cameras.new('cam')
    cd.type = 'ORTHO'
    cd.ortho_scale = CELL[0] / PPM
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def place_cam(cam, center, az=AZ, elev=ELEV, zoom=1.0):
    a, e = math.radians(az), math.radians(elev)
    pos = center + V((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 8.0
    cam.location = pos
    cam.rotation_euler = (center - pos).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = CELL[0] / PPM * zoom


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


def new_blob(name, mat, r=0.2, wob=0.18, n=16, z=0.004, seed=0):
    """Charco/mancha: disco de contorno irregular sobre el suelo (lee como cera escurrida a 1x)."""
    rng = random.Random(seed)
    me = bpy.data.meshes.new(name)
    vs = [(0.0, 0.0, z)]
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1.0 + rng.uniform(-wob, wob))
        vs.append((rr * math.cos(a), rr * math.sin(a), z))
    fs = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True
    return ob


# ----------------------------------------------------------------------------------------------- partir la malla por un plano
def cut_halves(ch, plane_co_w, plane_no_w, jag_amp=0.012, cap_color=CAP_COLOR, names=('A', 'B')):
    """Parte la malla (en reposo) por un plano de mundo. Devuelve (lado positivo, lado negativo).
    Los dos objetos comparten armature (pesos intactos) y llevan una cara de corte con material 'cera_corte'."""
    me = ch.mesh
    update()
    M = me.matrix_world
    Mi = M.inverted()
    p_l = Mi @ plane_co_w
    n_l = (M.to_3x3().transposed() @ plane_no_w).normalized()
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
        # la malla es una tela hueca: se rellena el corte con la envolvente convexa de cada componente (cera maciza).
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
        print('CUT', nm, 'edges', len(cedges), 'components', len(comps), 'cap faces', len(newf))
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


def cut_object(ob, plane_co_w, plane_no_w, jag_amp=0.006, cap_color=CAP_COLOR, names=('A', 'B')):
    """Parte un objeto ESTATICO (vertices ya en el mundo, matrix_world identidad) por un plano de mundo.
    Devuelve (lado positivo del plano, lado negativo) con la seccion rellena con cera (`cap_color`)."""
    me = ob.data
    M = ob.matrix_world.copy()
    Mi = M.inverted()
    p_l = Mi @ plane_co_w
    n_l = (M.to_3x3().transposed() @ plane_no_w).normalized()
    t1 = n_l.cross(V((0, 0, 1)))
    if t1.length < 0.1:
        t1 = n_l.cross(V((1, 0, 0)))
    t1.normalize()
    t2 = n_l.cross(t1).normalized()
    cap_mat = flat_mat('cera_corte', cap_color)
    out = []
    for nm, clear_inner in ((names[0], True), (names[1], False)):
        bm = bmesh.new()
        bm.from_mesh(me)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=p_l, plane_no=n_l,
                                     clear_inner=clear_inner, clear_outer=not clear_inner)
        cut = res['geom_cut']
        cverts = [g for g in cut if isinstance(g, bmesh.types.BMVert)]
        cedges = [g for g in cut if isinstance(g, bmesh.types.BMEdge)]
        # diente de sierra solo de la posicion (las dos mitades encajan)
        for v in cverts:
            d = v.co - p_l
            u, w = d.dot(t1), d.dot(t2)
            j = math.sin(u * 55.0 + 1.3) * 0.6 + math.sin(w * 41.0) * 0.4
            v.co += n_l * (jag_amp * j)
        # se rellena la seccion: aro del corte triangulado con su envolvente convexa (cera maciza por dentro)
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
        slot = len(me.materials)
        sign = -1.0 if clear_inner else 1.0
        nf = 0
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
                nf += 1
        print('CUT obj', nm, 'edges', len(cedges), 'comps', len(comps), 'cap faces', nf)
        bm.normal_update()
        nmesh = bpy.data.meshes.new('cut_' + nm)
        bm.to_mesh(nmesh)
        bm.free()
        for m in me.materials:
            if m is not None:
                nmesh.materials.append(m)
        nmesh.materials.append(cap_mat)
        nb = bpy.data.objects.new('cut_' + nm, nmesh)
        bpy.context.scene.collection.objects.link(nb)
        nb.matrix_world = M
        out.append(nb)
    return out[0], out[1]


def bake(ob, name, attrs=()):
    """Congela la malla deformada de `ob` (armature incluido) en un objeto estatico con los vertices ya en el mundo
    (matrix_world identidad). Sirve para mover trozos de forma rigida sin que el esqueleto los siga deformando."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.name = name
    M = ev.matrix_world.copy()
    me.transform(M)
    if len(me.materials) == 0:
        for m in ob.data.materials:
            if m is not None:
                me.materials.append(m)
    nb = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(nb)
    nb.hide_render = False
    return nb


def obj_static(ob):
    """Quita modificadores y padre de un objeto para que su matrix_world sea su unica transformacion."""
    for md in list(ob.modifiers):
        ob.modifiers.remove(md)
    ob.parent = None
    ob.matrix_parent_inverse = Matrix.Identity(4)
    update()
    return ob


# ----------------------------------------------------------------------------------------------- sombra proyectada
def eval_world_mesh(ob, dg):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    M = ev.matrix_world
    vs = [M @ v.co for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return vs, fs


SHADOW = {'ob': None}
LIGHT_DIR = V((1.0, 0.0))
SH_K = 0.30


def build_shadow(sources, extra=(), mat=None):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, faces = [], []
    for ob in sources:
        vs, fs = eval_world_mesh(ob, dg)
        off = len(verts)
        for v in vs:
            z = max(v.z, 0.0)
            verts.append((v.x + LIGHT_DIR.x * SH_K * z, v.y + LIGHT_DIR.y * SH_K * z, 0.003))
        faces.extend(tuple(i + off for i in f) for f in fs)
    for (cx, cy, rx, ry) in extra:
        off = len(verts)
        n = 20
        verts.append((cx, cy, 0.003))
        for k in range(n):
            a = 2 * math.pi * k / n
            verts.append((cx + rx * math.cos(a), cy + ry * math.sin(a), 0.003))
        for k in range(n):
            faces.append((off, off + 1 + k, off + 1 + (k + 1) % n))
    if SHADOW['ob'] is not None:
        bpy.data.objects.remove(SHADOW['ob'], do_unlink=True)
        SHADOW['ob'] = None
    if not verts:
        return
    me = bpy.data.meshes.new('sombra')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new('sombra', me)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True
    SHADOW['ob'] = ob


# ----------------------------------------------------------------------------------------------- gotas de cera
G_ = 9.0


class Drop:
    def __init__(self, i, rng, origin, vel_fn, size, t0=0):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=(0, 0, -5))
        o = bpy.context.active_object
        o.name = 'gota%d' % i
        o.data.materials.append(MAT_WAX[i % 2])
        o.hide_render = True
        for p in o.data.polygons:
            p.use_smooth = False
        self.o = o
        self.o0 = V(origin) + V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.015
        self.v = vel_fn(rng)
        self.size = size
        self.t0 = t0
        self.landed = None

    def place(self, t, spin=0.0):
        tt = t - self.t0
        if tt < 0:
            self.o.hide_render = True
            return
        self.o.hide_render = False
        p = self.o0 + self.v * tt + V((0, 0, -0.5 * G_ * tt * tt))
        vel = self.v + V((0, 0, -G_ * tt))
        if p.z <= self.size * 0.5:
            if self.landed is None:
                self.landed = V((p.x, p.y, 0))
            p = V((self.landed.x, self.landed.y, self.size * 0.22))
            self.o.location = p
            self.o.rotation_euler = (0, 0, math.atan2(self.v.y, self.v.x))
            self.o.scale = (1.7, 1.7, 0.35)     # goteron: se aplasta al caer, no queda una miga
        else:
            self.o.location = p
            self.o.scale = (0.8, 0.8, 1.0 + min(1.3, vel.length * 0.7))
            if vel.length > 1e-4:
                q = vel.normalized().to_track_quat('Z', 'Y')
                if spin:
                    q = Matrix.Rotation(spin, 4, 'Y').to_quaternion() @ q
                self.o.rotation_euler = q.to_euler()


def set_wax(mats):
    global MAT_WAX
    MAT_WAX = list(mats)


MAT_WAX = []
