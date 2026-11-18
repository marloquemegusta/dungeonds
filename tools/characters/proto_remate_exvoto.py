"""PROTOTIPO del remate (glory kill) del Corazon Abierto sobre un Exvoto: el heroe lo agarra por las munecas, lo levanta
y lo parte por la cintura (es de cera). Solo prueba de viabilidad: no toca el juego.

Uso (la salida son PNG con cada fotograma a escala DS; la hoja y el GIF los monta tools/characters/proto_remate_sheet.py):
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/proto_remate_exvoto.py -- <raiz_worktree> <salida> [modo] [azimut]
  modo: test (1 fotograma) | all (toda la secuencia) | clips (hoja de poses base para elegir frames de clip)
  azimut: grados de la camara (0 = de lado, 45 = diagonal isometrica)

Escena: heroe en x<0 mirando a +X, Exvoto en x>0 mirando a -X. Camara ortografica a 30 grados de elevacion (la del juego).
El heroe va a 29*1.24 px/m (mas grande que el Exvoto, como en los sprites actuales).
"""
import bpy, sys, os, math, random
import numpy as np
import bmesh
from mathutils import Vector, Matrix, Euler

A = sys.argv[sys.argv.index('--') + 1:]
ROOT = A[0]
OUT = A[1]
MODE = A[2] if len(A) > 2 else 'test'
AZ = float(A[3]) if len(A) > 3 else 45.0
os.makedirs(OUT, exist_ok=True)

MAIN = 'C:/codexlocal/dungeonds'   # derivados (FBX animados) solo en la carpeta principal; lectura
P = 'mixamorig:'
PPM = 29.0            # pixeles por metro (Exvoto)
HERO_K = 1.24         # el heroe se ve mas grande que el Exvoto en los sprites
CELL = (64, 64)       # celda final del prototipo (px)
SS = 4                # supermuestreo del render antes de reducir

scene = bpy.context.scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def update():
    bpy.context.view_layer.update()


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def load_action(path, short):
    """Importa un FBX solo para sacar su accion (y la deja con fake user)."""
    ab = set(bpy.data.actions)
    new = load(path)
    acts = [a for a in bpy.data.actions if a not in ab]
    a = acts[0]
    a.use_fake_user = True
    a.name = short
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return a


# ----------------------------------------------------------------------------------------------- personajes
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
    c.W0 = None
    for pb in c.arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return c


hero = make_char(ROOT + '/assets/models/characters/corazon/source/corazon.fbx', 90, HERO_K, (-0.3, 0, 0))
exv = make_char(ROOT + '/assets/models/characters/exvoto/source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx',
                -90, 1.0, (0.18, 0, 0))
update()

ACT = {
    'hero_walk': load_action(ROOT + '/assets/models/animations/corazon/walk.fbx', 'hero_walk'),
    'hero_shot': load_action(ROOT + '/assets/models/animations/corazon/disparo.fbx', 'hero_shot'),
    'ex_walk': load_action(MAIN + '/assets/models/characters/exvoto/exvoto_walk.fbx', 'ex_walk'),
    'ex_pray': load_action(MAIN + '/assets/models/characters/exvoto/exvoto_pray_stand.fbx', 'ex_pray'),
}
update()


def capture(ch, act_key, frame):
    """Pose de un clip en un fotograma -> {hueso: matrix_basis}."""
    act = ACT[act_key]
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


# ----------------------------------------------------------------------------------------------- partir la malla
CAP_COLOR = (0.78, 0.62, 0.36, 1.0)    # cera por dentro: ocre apagado


def jag(co, c, t1, t2, amp):
    d = co - c
    ang = math.atan2(d.dot(t2), d.dot(t1))
    # onda de dientes de sierra irregular, funcion solo de la posicion (igual en las dos mitades)
    w = (ang / math.pi * 5.0) % 1.0
    tri = abs(w * 2 - 1) * 2 - 1
    w2 = (ang / math.pi * 11.0 + 0.37) % 1.0
    tri2 = abs(w2 * 2 - 1) * 2 - 1
    return amp * (0.7 * tri + 0.3 * tri2)


def split_mesh(ch, bone_name='Spine', jag_amp=0.03):
    """Parte la malla en reposo por la cabeza del hueso `bone_name`. Devuelve (mesh_alto, mesh_bajo)."""
    arm, me = ch.arm, ch.mesh
    update()
    pw = arm.matrix_world @ arm.data.bones[P + bone_name].head_local
    M = me.matrix_world
    Mi = M.inverted()
    p_l = Mi @ pw
    n_l = (M.to_3x3().transposed() @ Vector((0, 0, 1))).normalized()
    t1 = n_l.cross(Vector((1, 0, 0)))
    if t1.length < 0.1:
        t1 = n_l.cross(Vector((0, 1, 0)))
    t1.normalize()
    t2 = n_l.cross(t1).normalized()
    cap_mat = bpy.data.materials.new('cera_corte')
    cap_mat.diffuse_color = CAP_COLOR
    halves = []
    for name, clear_inner in (('top', True), ('bot', False)):
        bm = bmesh.new()
        bm.from_mesh(me.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=p_l, plane_no=n_l,
                                     clear_inner=clear_inner, clear_outer=not clear_inner)
        cut = res['geom_cut']
        cverts = [g for g in cut if isinstance(g, bmesh.types.BMVert)]
        cedges = [g for g in cut if isinstance(g, bmesh.types.BMEdge)]
        # c = centro del corte (para el diente de sierra)
        cen = sum((v.co for v in cverts), Vector()) / max(1, len(cverts))
        for v in cverts:
            v.co += n_l * jag(v.co, cen, t1, t2, jag_amp)
        fr = bmesh.ops.holes_fill(bm, edges=cedges, sides=0)
        newf = fr['faces']
        bmesh.ops.triangulate(bm, faces=newf)
        slot = len(me.data.materials)   # se anade luego
        for f in newf:
            f.material_index = slot
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        nm = bpy.data.meshes.new('half_' + name)
        bm.to_mesh(nm)
        bm.free()
        for m in me.data.materials:
            nm.materials.append(m)
        nm.materials.append(cap_mat)
        ob = me.copy()
        ob.data = nm
        for g in me.vertex_groups:            # los nombres de grupo viven en la malla: se recrean en el mismo orden
            if g.name not in ob.vertex_groups:
                ob.vertex_groups.new(name=g.name)
        ob.name = 'half_' + name
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = me.parent
        ob.matrix_parent_inverse = me.matrix_parent_inverse.copy()
        halves.append(ob)
    top, bot = halves
    # pesos: cada mitad sigue solo a su cadena de huesos (la parte alta a la columna, la baja a la cadera)
    for ob, src, dst in ((top, [P + 'Hips'], P + 'Spine'),
                         (bot, [P + 'Spine', P + 'Spine1', P + 'Spine2'], P + 'Hips')):
        vg = ob.vertex_groups
        idx_src = [vg[n].index for n in src if n in vg]
        d = vg[dst]
        for v in ob.data.vertices:
            tot = 0.0
            for g in v.groups:
                if g.group in idx_src:
                    tot += g.weight
            if tot > 0:
                d.add([v.index], tot, 'ADD')
                for i in idx_src:
                    try:
                        vg[i].remove([v.index])
                    except RuntimeError:
                        pass
    me.hide_render = True
    me.hide_viewport = True
    ch.top, ch.bot = top, bot
    ch.cut_center_w = pw
    return top, bot


split_mesh(exv)
update()

# ----------------------------------------------------------------------------------------------- IK
def add_ik(ch, bone, name, chain=2):
    t = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(t)
    pb = ch.arm.pose.bones[P + bone]
    c = pb.constraints.new('IK')
    c.target = t
    c.chain_count = chain
    c.use_tail = True
    c.use_stretch = False
    return t, c


# manos del heroe y munecas del Exvoto se anclan a los mismos puntos de agarre
hero_ik = {}
for side in ('Left', 'Right'):
    hero_ik[side] = add_ik(hero, side + 'ForeArm', 'hG' + side)
    hero_ik['leg' + side] = add_ik(hero, side + 'Leg', 'hF' + side)
exv_ik = {}
for side in ('Left', 'Right'):
    exv_ik[side] = add_ik(exv, side + 'ForeArm', 'eG' + side)

# ----------------------------------------------------------------------------------------------- utilidades de pose
def W(ch):
    return ch.arm.matrix_world


def bone_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].matrix


def set_bone_world(ch, name, Mw):
    ch.arm.pose.bones[P + name].matrix = W(ch).inverted() @ Mw
    update()


def head_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].head


def xform_about(pivot, rot_y_deg=0.0, rot_z_deg=0.0, rot_x_deg=0.0, trans=(0, 0, 0)):
    """Transformada de mundo: rotar alrededor de `pivot` (Y: inclinacion adelante/atras sobre el eje del duelo) y trasladar."""
    R = Matrix.Rotation(math.radians(rot_z_deg), 4, 'Z') @ Matrix.Rotation(math.radians(rot_y_deg), 4, 'Y') \
        @ Matrix.Rotation(math.radians(rot_x_deg), 4, 'X')
    return Matrix.Translation(Vector(trans)) @ Matrix.Translation(pivot) @ R @ Matrix.Translation(-Vector(pivot))


def bend(ch, name, rot_y_deg, rot_x_deg=0.0, rot_z_deg=0.0):
    """Gira el hueso (y sus hijos) alrededor de su cabeza, en ejes de mundo."""
    Mw = bone_world(ch, name)
    p = Mw.translation.copy()
    set_bone_world(ch, name, xform_about(p, rot_y_deg, rot_z_deg, rot_x_deg) @ Mw)


# ----------------------------------------------------------------------------------------------- camara y render
def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.show_cavity = False
    sc.display.shading.show_shadows = False
    sc.display.render_aa = '8'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = CELL[0] * SS
    sc.render.resolution_y = CELL[1] * SS
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    cam_d = bpy.data.cameras.new('cam')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = CELL[0] / PPM
    cam = bpy.data.objects.new('cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


CAM = setup_render()
CENTER = Vector((0.0, 0.0, 0.52))    # punto que cae en el centro de la celda (se retoca)


def place_cam(az_deg, center=CENTER, elev=30.0):
    az, el = math.radians(az_deg), math.radians(elev)
    D = 6.0
    pos = center + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * D
    CAM.location = pos
    CAM.rotation_euler = (center - pos).to_track_quat('-Z', 'Y').to_euler()


def render_frame(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ----------------------------------------------------------------------------------------------- modos de prueba
def pose_base(hero_key, hero_f, ex_key, ex_f):
    apply_basis(hero, capture(hero, hero_key, hero_f))
    apply_basis(exv, capture(exv, ex_key, ex_f))
    for ik in list(hero_ik.values()) + list(exv_ik.values()):
        ik[1].influence = 0.0
    for ob in (hero.mesh, exv.top, exv.bot):
        pass
    update()


if MODE == 'test':
    for ik in list(hero_ik.values()) + list(exv_ik.values()):
        ik[1].influence = 0.0
    pose_base('hero_walk', 8, 'ex_pray', 10)
    for az in (0, 45):
        place_cam(az)
        render_frame(os.path.join(OUT, 'test_az%d.png' % az))
    print('TEST OK')


if MODE == 'clips':
    for ik in list(hero_ik.values()) + list(exv_ik.values()):
        ik[1].influence = 0.0
    place_cam(AZ)
    for f in range(1, 33, 4):
        pose_base('hero_walk', f, 'ex_walk', 1 + (f - 1) * 44 // 32)
        render_frame(os.path.join(OUT, 'clip_walk_%02d.png' % f))


# ----------------------------------------------------------------------------------------------- coreografia
# Fotogramas clave (uno por fotograma de la tira final). Mundo: heroe en x<0 mirando a +X, Exvoto en x>0 mirando a -X.
# rot_y positivo = inclinar hacia +X (para el Exvoto: hacia atras, huyendo del heroe).
SPLIT = 6                      # fotograma del chasquido
DT = 0.067                     # s entre fotogramas (4 ticks a 60 Hz)
V = Vector


def G(z, y=0.15, x=-0.08):
    """Puntos de agarre (izq, der del heroe: Left = +Y)."""
    return (V((x, y, z)), V((x, -y, z)))


HB = ('hero_walk', 1)
EB = ('ex_pray', 10)
SEQ = [
    # f0: el heroe corre hacia el Exvoto tambaleante
    dict(hx=-0.95, hbase=('hero_walk', 9), hips_lean=14, spine=8, head=-6, pin=False, grip=None,
         ebase=('ex_walk', 8), ex=0.18, top=dict(ry=8), bot=dict()),
    # f1: salto final
    dict(hx=-0.72, hbase=('hero_walk', 13), hips_lean=22, spine=12, head=-8, pin=False, grip=None,
         ebase=('ex_walk', 12), ex=0.18, top=dict(ry=14), bot=dict(ry=3)),
    # f2: agarra las munecas
    dict(hx=-0.52, hbase=HB, hips_lean=22, spine=14, head=-10, pin=True, grip=G(0.62, 0.10, -0.06),
         ebase=EB, ex=0.20, top=dict(ry=12), bot=dict(ry=2)),
    # f3: se agacha y tira de el
    dict(hx=-0.46, hbase=HB, hips_lean=26, spine=20, head=-14, hips_dz=-0.07, pin=True,
         grip=G(0.56, 0.12, -0.05), ebase=EB, ex=0.17, top=dict(ry=-6, dx=-0.01), bot=dict(ry=-2, dx=-0.01)),
    # f4: lo levanta
    dict(hx=-0.46, hbase=HB, hips_lean=8, spine=2, head=-4, hips_dz=-0.02, pin=True,
         grip=G(1.02, 0.17, -0.07), ebase=EB, ex=0.17, top=dict(dz=0.15, ry=2), bot=dict(dz=0.10)),
    # f5: en alto, la cintura se estira y se agrieta
    dict(hx=-0.46, hbase=HB, hips_lean=-8, spine=-10, head=-2, hips_dz=0.02, pin=True,
         grip=G(1.30, 0.22, -0.10), ebase=EB, ex=0.17,
         top=dict(dz=0.32, dx=-0.01, ry=-4), bot=dict(dz=0.20, ry=2), chips=3),
    # f6: CHASQUIDO
    dict(hx=-0.46, hbase=HB, hips_lean=-12, spine=-14, head=-2, hips_dz=0.03, pin=True,
         grip=G(1.34, 0.24, -0.11), ebase=EB, ex=0.17,
         top=dict(dz=0.42, dx=-0.03, ry=-12), bot=dict(dz=0.10, dx=0.05, ry=14), burst=True),
    # f7: la mitad de abajo cae; el heroe sostiene la de arriba
    dict(hx=-0.46, hbase=HB, hips_lean=-10, spine=-12, head=-2, hips_dz=0.02, pin=True,
         grip=G(1.36, 0.24, -0.11), ebase=EB, ex=0.17,
         top=dict(dz=0.46, dx=-0.04, ry=-14), bot=dict(dz=-0.14, dx=0.14, ry=-40)),
    # f8: lanza la mitad de arriba hacia delante y abajo
    dict(hx=-0.46, hbase=HB, hips_lean=14, spine=16, head=-8, hips_dz=-0.03, pin=True,
         grip=G(0.95, 0.30, 0.10), grip_released=True, ebase=EB, ex=0.17,
         top=dict(dz=0.10, dx=0.17, dy=-0.18, ry=-50, rx=40), bot=dict(dz=-0.32, dx=0.20, ry=-68)),
    # f9: aterrizan
    dict(hx=-0.46, hbase=HB, hips_lean=6, spine=8, head=-2, hips_dz=-0.01, pin=True, grip=None,
         ebase=EB, ex=0.17,
         top=dict(dz=-0.47, dx=0.22, dy=-0.32, ry=-86, rx=70), bot=dict(dz=-0.42, dx=0.25, ry=-88)),
    # f10: rebotan los trozos
    dict(hx=-0.46, hbase=HB, hips_lean=2, spine=3, head=0, pin=True, grip=None,
         ebase=EB, ex=0.17,
         top=dict(dz=-0.47, dx=0.22, dy=-0.34, ry=-88, rx=90), bot=dict(dz=-0.42, dx=0.26, ry=-90)),
    # f11: reposo
    dict(hx=-0.46, hbase=HB, hips_lean=0, spine=0, head=0, pin=True, grip=None,
         ebase=EB, ex=0.17,
         top=dict(dz=-0.47, dx=0.22, dy=-0.34, ry=-88, rx=90), bot=dict(dz=-0.42, dx=0.26, ry=-90)),
]

_cache = {}


def base(ch, key):
    k = (id(ch), key)
    if k not in _cache:
        _cache[k] = capture(ch, key[0], key[1])
    return _cache[k]


def flat_mat(name, col):
    m = bpy.data.materials.new(name)
    m.diffuse_color = col
    return m


MAT_SHARD = [flat_mat('trozoA', (0.80, 0.74, 0.55, 1)), flat_mat('trozoB', (0.78, 0.62, 0.36, 1))]
MAT_SHADOW = flat_mat('sombra', (0.0, 0.0, 0.0, 1))


def new_shard(i, size):
    bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, -5))
    o = bpy.context.active_object
    o.name = 'trozo%d' % i
    o.data.materials.append(MAT_SHARD[i % 2])
    o.hide_render = True
    return o


def new_disc(name):
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=1.0, fill_type='NGON', location=(0, 0, 0.002))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(MAT_SHADOW)
    o.hide_render = True
    return o


rng = random.Random(7)
SHARDS = []
for i in range(14):
    sz = rng.choice([0.035, 0.045, 0.055, 0.07])
    o = new_shard(i, sz)
    ang = rng.uniform(0, 2 * math.pi)
    sp_ = rng.uniform(0.4, 1.0)
    SHARDS.append(dict(o=o, v=V((math.cos(ang) * sp_, math.sin(ang) * sp_, rng.uniform(0.5, 1.4))),
                       off=V((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), rng.uniform(-0.02, 0.02))),
                       spin=V((rng.uniform(-9, 9), rng.uniform(-9, 9), rng.uniform(-9, 9)))))
DISC = {k: new_disc('sombra_' + k) for k in ('hero', 'top', 'bot')}
state = {'cut': None}


def foot_pins(ch):
    for side in ('Left', 'Right'):
        tgt, c = hero_ik['leg' + side]
        tgt.location = head_world(ch, side + 'Foot')


def set_ik_infl(d, v):
    for k in ('Left', 'Right'):
        d[k][1].influence = v


def make_pose(i, sp):
    hero.root.location.x = sp['hx']
    exv.root.location.x = sp['ex']
    for side in ('Left', 'Right'):
        hero_ik['leg' + side][1].influence = 0.0
    set_ik_infl(hero_ik, 0.0)
    set_ik_infl(exv_ik, 0.0)
    update()
    apply_basis(hero, base(hero, sp['hbase']))
    apply_basis(exv, base(exv, sp['ebase']))
    if sp['pin']:
        foot_pins(hero)
    Mh = bone_world(hero, 'Hips')
    ph = Mh.translation.copy()
    dz = sp.get('hips_dz', 0.0)
    set_bone_world(hero, 'Hips', xform_about(ph, sp['hips_lean'], trans=(0, 0, dz)) @ Mh)
    bend(hero, 'Spine1', sp['spine'] * 0.5)
    bend(hero, 'Spine2', sp['spine'] * 0.5)
    bend(hero, 'Head', sp['head'])
    if sp['pin']:
        for side in ('Left', 'Right'):
            hero_ik['leg' + side][1].influence = 1.0
    grip = sp['grip']
    held = grip is not None
    if held:
        gl, gr = grip
        hero_ik['Left'][0].location = gl
        hero_ik['Right'][0].location = gr
        # Left del heroe (+Y) agarra la muneca derecha del Exvoto (+Y)
        exv_ik['Right'][0].location = gl
        exv_ik['Left'][0].location = gr
        set_ik_infl(hero_ik, 1.0)
        if not sp.get('grip_released'):
            set_ik_infl(exv_ik, 1.0)
    update()
    # Exvoto: dos solidos rigidos (mitad alta y mitad baja)
    Mhip = bone_world(exv, 'Hips')
    Msp = bone_world(exv, 'Spine')
    top, bot = sp['top'], sp['bot']
    pb_ = Mhip.translation.copy()
    pt_ = Msp.translation.copy()
    Tb = xform_about(pb_, bot.get('ry', 0), 0, bot.get('rx', 0), (bot.get('dx', 0), bot.get('dy', 0), bot.get('dz', 0)))
    Tt = xform_about(pt_, top.get('ry', 0), 0, top.get('rx', 0), (top.get('dx', 0), top.get('dy', 0), top.get('dz', 0)))
    set_bone_world(exv, 'Hips', Tb @ Mhip)
    set_bone_world(exv, 'Spine', Tt @ Msp)
    return held


def place_shards(i, sp):
    for k, sh in enumerate(SHARDS):
        o = sh['o']
        if i < SPLIT - 1 or state['cut'] is None and i >= SPLIT:
            o.hide_render = True
            continue
        c = state['cut'] if state['cut'] is not None else V((0.1, 0, 1.0))
        if i == SPLIT - 1:   # grietas: pocos trozos pegados al corte
            o.hide_render = k >= sp.get('chips', 0)
            o.location = c + sh['off'] * 2
            continue
        o.hide_render = False
        tt = max((i - SPLIT) * DT, 0.0)
        p = c + sh['off'] + sh['v'] * tt + V((0, 0, -0.5 * 28.0 * tt * tt))
        if p.z < 0.025:
            p.z = 0.025
        o.location = p
        o.rotation_euler = (sh['spin'].x * tt, sh['spin'].y * tt, sh['spin'].z * tt)


def place_shadows(i, sp):
    hero_h = head_world(hero, 'Hips')
    d = DISC['hero']
    d.location = (hero_h.x, hero_h.y, 0.002)
    d.scale = (0.20, 0.16, 1)
    hb = head_world(exv, 'Hips')
    d = DISC['bot']
    lying = abs(sp['bot'].get('ry', 0)) > 45
    d.location = (hb.x + (0.12 if lying else 0), hb.y, 0.002)
    d.scale = (0.26, 0.12, 1) if lying else (0.13, 0.11, 1)
    ht = head_world(exv, 'Spine')
    d = DISC['top']
    lying = abs(sp['top'].get('rx', 0)) > 45
    d.location = (ht.x, ht.y, 0.002)
    d.scale = (0.12, 0.26, 1) if lying else (0.12, 0.10, 1)


def render_pass(i, outdir):
    for d in DISC.values():
        d.hide_render = True
    hero.mesh.hide_render = False
    exv.top.hide_render = False
    exv.bot.hide_render = False
    render_frame(os.path.join(outdir, 'f%02d.png' % i))
    saved = [(s['o'], s['o'].hide_render) for s in SHARDS]
    for s in SHARDS:
        s['o'].hide_render = True
    hero.mesh.hide_render = True
    exv.top.hide_render = True
    exv.bot.hide_render = True
    for d in DISC.values():
        d.hide_render = False
    render_frame(os.path.join(outdir, 's%02d.png' % i))
    for o, h in saved:
        o.hide_render = h
    for d in DISC.values():
        d.hide_render = True


if MODE == 'all':
    place_cam(AZ, V((-0.12, 0.0, 0.58)))
    for i, sp in enumerate(SEQ):
        make_pose(i, sp)
        if i == SPLIT:
            a = head_world(exv, 'Spine')
            b = head_world(exv, 'Hips') + V((0, 0, 0.055))
            state['cut'] = (a + b) * 0.5
        place_shards(i, sp)
        place_shadows(i, sp)
        render_pass(i, OUT)
    print('ALL OK', len(SEQ))
