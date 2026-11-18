"""PROTOTIPO ronda 2 del remate del Corazon Abierto sobre el Exvoto (Blender headless, vista diagonal, escala real del juego).

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/proto_remate_exvoto_v2.py -- <raiz_worktree> <salida> <A|B|C> <test|all> [fotograma_test]

Escribe en <salida>/exvoto_<X>/raw/ los pases de cada fotograma (fNN_lit, fNN_flat, sNN sombra, hNN calor);
proto_remate_exvoto_post.py los compone en los PNG 1x finales y en el GIF de control.

Opciones:
  A: lo agarra de cada brazo y lo parte en dos MITADES VERTICALES (cabeza -> entrepierna) tirando hacia los lados.
  B: lo abraza contra el pecho abierto y el fuego lo derrite hasta un charco con el velo encima.
  C: lo levanta sobre la cabeza y lo estampa contra el suelo: revienta en trozos de cera.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proto_remate_exvoto_common import *

A_ = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT, OPT, MODE = A_[0], A_[1], A_[2], A_[3]
TEST_F = int(A_[4]) if len(A_) > 4 else 5
RAW = os.path.join(OUT, 'exvoto_' + OPT, 'raw')
os.makedirs(RAW, exist_ok=True)
EXFBX = ROOT + '/assets/models/characters/exvoto/source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx'
HEROFBX = ROOT + '/assets/models/characters/corazon/source/corazon.fbx'

bpy.ops.wm.read_factory_settings(use_empty=True)
CAM = setup_render()
load_acts(ROOT)
G_ = 9.0            # gravedad en unidades de Blender por s^2
DT = 0.06           # s por fotograma

HXF = -0.27         # posicion final del heroe (pies) en las tres opciones: ancla comun
CENTER = V((HXF, 0.0, 0.286))   # punto de mundo al centro de la celda; con el heroe final sus pies caen en el pixel (32,42), ancla comun a las 3 opciones

hero = make_char(HEROFBX, 90, 1.0, (HXF, 0, 0))
update()
MAT_WAX = [flat_mat('gotaA', (0.62, 0.56, 0.40, 1)), flat_mat('gotaB', (0.58, 0.42, 0.22, 1))]
MAT_BLACK = flat_mat('negro', (0, 0, 0, 1))
MAT_PUDDLE = flat_mat('charco', (0.56, 0.46, 0.28, 1))


def new_ex(loc=(0, 0, 0)):
    return make_char(EXFBX, -90, EX_K, loc)


# ----------------------------------------------------------------------------------------------- heroe
hero_ik = {}
for side in ('Left', 'Right'):
    hero_ik[side] = add_ik(hero, side + 'ForeArm', 'hG' + side)
    hero_ik['leg' + side] = add_ik(hero, side + 'Leg', 'hF' + side)

_cache = {}


def base(ch, key):
    k = (id(ch), key)
    if k not in _cache:
        _cache[k] = capture(ch, key[0], key[1])
    return _cache[k]


def hero_pose(hp):
    """hp: hx, hbase=(clip, frame), lean, spine, head, dz, pin (pies clavados), arms_free (dict de rotaciones de brazo)."""
    hero.root.location.x = hp['hx']
    for k in ('Left', 'Right', 'legLeft', 'legRight'):
        hero_ik[k][1].influence = 0.0
    update()
    apply_basis(hero, base(hero, hp['hbase']))
    if hp.get('pin'):
        for side in ('Left', 'Right'):
            hero_ik['leg' + side][0].location = head_world(hero, side + 'Foot')
    Mh = bone_world(hero, 'Hips')
    set_bone_world(hero, 'Hips', xform_about(Mh.translation.copy(), 0, hp.get('lean', 0), 0, (0, 0, hp.get('dz', 0))) @ Mh)
    rot_bone(hero, 'Spine1', 0, hp.get('spine', 0) * 0.5)
    rot_bone(hero, 'Spine2', 0, hp.get('spine', 0) * 0.5)
    rot_bone(hero, 'Head', 0, hp.get('head', 0))
    if hp.get('pin'):
        for side in ('Left', 'Right'):
            hero_ik['leg' + side][1].influence = 1.0
    update()


ARM_L = 0.27          # alcance del brazo del heroe (unidades Blender)


def hero_grip(targets, reach=0.97):
    """targets: {'Left': punto, 'Right': punto} o None. Devuelve la distancia que falta (hueco) por mano."""
    gaps = {}
    for side in ('Left', 'Right'):
        c = hero_ik[side][1]
        if not targets or targets.get(side) is None:
            c.influence = 0.0
            continue
        sh = head_world(hero, side + 'Arm')
        t = targets[side]
        d = t - sh
        gaps[side] = max(0.0, d.length - ARM_L * reach)
        if d.length > ARM_L * reach:
            t = sh + d.normalized() * ARM_L * reach
        hero_ik[side][0].location = t
        c.influence = 1.0
    update()
    return gaps


def hero_arm_free(side, rx=0.0, ry=0.0, rz=0.0, fore=0.0):
    rot_bone(hero, side + 'Arm', rx, ry, rz)
    rot_bone(hero, side + 'ForeArm', 0, fore, 0)


# ----------------------------------------------------------------------------------------------- exvoto: brazos
def ex_arm(ch, side, d):
    """Estira el brazo `side` ('Left'/'Right') del Exvoto en la direccion de mundo d (sin estirar la longitud)."""
    d = V(d).normalized()
    for nm in ('Arm', 'ForeArm', 'Hand'):
        b = side + nm
        head = head_world(ch, b)
        tail = tail_world(ch, b)
        aim_bone(ch, b, head + d * (tail - head).length)


def set_root(ch, loc, rz, extra=None):
    M = Matrix.Translation(V(loc)) @ Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Scale(EX_K, 4)
    ch.root.matrix_world = (extra @ M) if extra is not None else M
    update()


# ----------------------------------------------------------------------------------------------- piezas de cera (gotas)
def new_drop(size, i):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=(0, 0, -5))
    o = bpy.context.active_object
    o.name = 'gota%d' % i
    o.data.materials.append(MAT_WAX[i % 2])
    o.hide_render = True
    for p in o.data.polygons:
        p.use_smooth = False
    return o


class Drop:
    def __init__(self, i, rng, origin, vel_fn, size, t0=0):
        self.o = new_drop(size, i)
        self.o0 = V(origin) + V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.02
        self.v = vel_fn(rng)
        self.size = size
        self.t0 = t0
        self.landed = None


def place_drops(drops, t):
    """t: segundos desde el chasquido (por gota se resta t0)."""
    for d in drops:
        tt = t - d.t0
        if tt < 0:
            d.o.hide_render = True
            continue
        d.o.hide_render = False
        p = d.o0 + d.v * tt + V((0, 0, -0.5 * G_ * tt * tt))
        vel = d.v + V((0, 0, -G_ * tt))
        if p.z <= d.size * 0.55:
            if d.landed is None:
                d.landed = V((p.x, p.y, 0))
            p = V((d.landed.x, d.landed.y, d.size * 0.3))
            d.o.location = p
            d.o.rotation_euler = (0, 0, 0)
            d.o.scale = (1.5, 1.5, 0.45)
        else:
            d.o.location = p
            d.o.scale = (1, 1, 1.0 + min(0.9, vel.length * 0.4))
            if vel.length > 1e-4:
                d.o.rotation_euler = vel.normalized().to_track_quat('Z', 'Y').to_euler()


# ----------------------------------------------------------------------------------------------- render
def eval_world_mesh(ob, dg):
    """(verts_mundo, caras) de la malla evaluada de ob (con armature, etc.)."""
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    M = ev.matrix_world
    vs = [M @ v.co for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return vs, fs


SHADOW = {'ob': None}
LIGHT_DIR = V((1.0, 0.0))     # la sombra cae hacia +X (el heroe mira a +X) y se proyecta con k*z
SH_K = 0.30


def build_shadow(sources, extra=()):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, faces = [], []
    for ob in sources:
        vs, fs = eval_world_mesh(ob, dg)
        off = len(verts)
        for v in vs:
            z = max(v.z, 0.0)
            verts.append((v.x + LIGHT_DIR.x * SH_K * z, v.y + LIGHT_DIR.y * SH_K * z, 0.003))
        faces.extend(tuple(i + off for i in f) for f in fs)
    for (cx, cy, rx, ry) in extra:     # charcos y manchas explicitas (elipses)
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
    me = bpy.data.meshes.new('sombra')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.materials.append(MAT_BLACK)
    ob = bpy.data.objects.new('sombra', me)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True
    SHADOW['ob'] = ob


def render_passes(i, visible, drops=(), extra_vis=(), heat_fn=None):
    """visible: objetos de personaje. Escribe fNN_lit, fNN_flat, sNN (sombra) y, si hay heat_fn, hNN."""
    sc = bpy.context.scene
    everything = list(visible) + list(extra_vis)
    for o in everything:
        o.hide_render = False
    SHADOW['ob'].hide_render = True
    sh = sc.display.shading
    sh.light = 'STUDIO'
    render_to(os.path.join(RAW, 'f%02d_lit.png' % i))
    sh.light = 'FLAT'
    render_to(os.path.join(RAW, 'f%02d_flat.png' % i))
    if heat_fn:
        heat_fn(i)
    # sombra: solo la malla negra
    hid = [(o, o.hide_render) for o in everything + [d.o for d in drops]]
    for o, _ in hid:
        o.hide_render = True
    SHADOW['ob'].hide_render = False
    render_to(os.path.join(RAW, 's%02d.png' % i))
    SHADOW['ob'].hide_render = True
    for o, h in hid:
        o.hide_render = h


def px_of(pw):
    from bpy_extras.object_utils import world_to_camera_view
    co = world_to_camera_view(bpy.context.scene, CAM, pw)
    return (round(co.x * CELL, 1), round((1 - co.y) * CELL, 1))


# ----------------------------------------------------------------------------------------------- malla horneada y deformable
import numpy as np
BAKED = []


def clear_baked():
    for o in BAKED:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    BAKED.clear()


def bake_static(ob, name):
    """Copia estatica (coordenadas de mundo) de la malla evaluada (con armature) de ob, con materiales y UV."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.transform(ev.matrix_world)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    BAKED.append(o)
    return o


def get_co(o):
    n = len(o.data.vertices)
    a = np.empty(n * 3, np.float64)
    o.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3)


def set_co(o, co):
    o.data.vertices.foreach_set('co', co.reshape(-1).astype(np.float64))
    o.data.update()


def _set_attr(me, rgba):
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    at = me.color_attributes.new('heat', 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set('color', rgba.reshape(-1))
    me.color_attributes.active_color = at
    me.color_attributes.render_color_index = 0


def set_heat(o, h):
    """h: array (N,) 0..1 -> atributo de color 'heat' (gris) para el pase de calor."""
    rgba = np.zeros((len(h), 4), np.float32)
    rgba[:, 0] = rgba[:, 1] = rgba[:, 2] = np.clip(h, 0, 1)
    rgba[:, 3] = 1.0
    _set_attr(o.data, rgba)


def black_attr(ob):
    rgba = np.zeros((len(ob.data.vertices), 4), np.float32)
    rgba[:, 3] = 1.0
    _set_attr(ob.data, rgba)


def render_heat(i, hide):
    """Pase de calor hNN.png: Exvoto en gris segun su atributo, heroe en negro (tapa), el resto oculto."""
    sh = bpy.context.scene.display.shading
    hid = [(o, o.hide_render) for o in hide]
    for o, _ in hid:
        o.hide_render = True
    sh.light = 'FLAT'
    sh.color_type = 'VERTEX'
    render_to(os.path.join(RAW, 'h%02d.png' % i))
    sh.color_type = 'TEXTURE'
    for o, h in hid:
        o.hide_render = h


def disc_obj(name, mat, r, n=18, noise=0.0, seed=3):
    rg = random.Random(seed)
    verts = [(0, 0, 0.004)]
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + noise * rg.uniform(-1, 1))
        verts.append((rr * math.cos(a), rr * math.sin(a), 0.004))
    faces = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.hide_render = True
    return o


# =============================================================================================== OPCION A
def run_A():
    exR = new_ex()       # mitad +Y (brazo derecho del Exvoto)
    exL = new_ex()       # mitad -Y (brazo izquierdo)
    update()
    center = head_world(exR, 'Hips')
    center = V((center.x, 0.0, 0.0))
    for ch, keep in ((exR, 0), (exL, 1)):
        halves = cut_halves(ch, center, V((0, 1, 0)), jag_amp=0.006)
        ch.half = halves[keep]
        bpy.data.objects.remove(halves[1 - keep], do_unlink=True)
        ch.mesh.hide_render = True
    ch_list = (exR, exL)
    EB = ('ex_walk', 8)
    HB = ('hero_walk', 1)
    # fotogramas: hx heroe, arm = (phi): angulo del brazo respecto al frente (grados), sep, tilt (grados), fx
    SEQ = [
        dict(hx=-0.80, hbase=('hero_walk', 9), lean=16, spine=8, head=-6, pin=False, arm=None, sep=0, tilt=0, ex_lean=4),
        dict(hx=-0.54, hbase=('hero_walk', 13), lean=24, spine=12, head=-8, pin=False, arm=None, sep=0, tilt=0, ex_lean=6),
        dict(hx=HXF, hbase=HB, lean=20, spine=14, head=-10, dz=-0.05, pin=True, arm=(14, 0.30), sep=0, tilt=0, ex_lean=4),
        dict(hx=HXF, hbase=HB, lean=14, spine=10, head=-8, dz=-0.06, pin=True, arm=(30, 0.40), sep=0, tilt=0, ex_lean=2),
        dict(hx=HXF, hbase=HB, lean=6, spine=4, head=-4, dz=-0.07, pin=True, arm=(42, 0.45), sep=0.01, tilt=0, ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=-4, spine=-4, head=-2, dz=-0.06, pin=True, arm=(50, 0.5), sep=0.035, tilt=5, ex_lean=0, burst=True),
        dict(hx=HXF, hbase=HB, lean=-8, spine=-8, head=-2, dz=-0.05, pin=True, arm=(56, 0.55), sep=0.05, tilt=20, ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=-4, spine=-4, head=-2, dz=-0.03, pin=True, arm=(75, 0.4), sep=0.09, tilt=44, ex_lean=0, release=True),
        dict(hx=HXF, hbase=HB, lean=4, spine=2, head=0, dz=-0.02, pin=True, arm=(90, 0.2), sep=0.11, tilt=70, ex_lean=0, release=True),
        dict(hx=HXF, hbase=HB, lean=2, spine=0, head=0, dz=-0.01, pin=True, arm=(95, 0.1), sep=0.115, tilt=80, ex_lean=0, release=True),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, pin=True, arm=(95, 0.1), sep=0.12, tilt=84, ex_lean=0, release=True),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, pin=True, arm=(95, 0.1), sep=0.12, tilt=84, ex_lean=0, release=True),
    ]
    SPLIT = 5
    rng = random.Random(11)
    drops = []
    cut_pt = V((0.0, 0.0, 0.30))

    def vel(r):
        s = r.choice((-1, 1))
        return V((r.uniform(-0.25, 0.25), s * r.uniform(0.25, 0.9), r.uniform(0.5, 1.4)))
    for k in range(16):
        drops.append(Drop(k, rng, cut_pt + V((0, 0, rng.uniform(-0.18, 0.2))), vel, rng.choice((0.016, 0.022, 0.028)), 0))

    def pose(i, sp):
        for ch in ch_list:
            for pb in ch.arm.pose.bones:
                pass
        hero_pose(sp)
        gaps = {}
        for ch, side, hside, sg in ((exR, 'Right', 'Left', 1), (exL, 'Left', 'Right', -1)):
            ch.root.location = (0, 0, 0)
            ch.root.matrix_world = Matrix.Translation((0, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Scale(EX_K, 4)
            update()
            apply_basis(ch, base(ch, EB))
            rot_bone(ch, 'Spine1', 0, -sp.get('ex_lean', 0) * 0.5)
            rot_bone(ch, 'Spine2', 0, -sp.get('ex_lean', 0) * 0.5)
            if sp['arm'] is not None:
                phi, lift = sp['arm']
                ph = math.radians(phi)
                # delante del Exvoto = -X (hacia el heroe); phi=0 hacia delante, 90 hacia el lado
                ex_arm(ch, side, V((-math.cos(ph), sg * math.sin(ph), lift)))
            sep, tilt = sp['sep'], sp['tilt']
            piv = V((0, sg * 0.045, 0))
            extra = Matrix.Translation(V((0, sg * sep, 0))) @ xform_about(piv, -sg * tilt, 0, 0)
            if tilt > 0:
                # al caer, la mitad se hunde un poco hacia el suelo (el lado cortado queda a ras)
                extra = Matrix.Translation(V((0, sg * sep, -0.012 * min(1.0, tilt / 90.0)))) @ xform_about(piv, -sg * tilt, 0, 0)
            ch.root.matrix_world = extra @ ch.root.matrix_world
            update()
        # el heroe sigue las munecas del Exvoto mientras las sostiene
        if sp['arm'] is not None and not sp.get('release'):
            gaps = hero_grip({'Left': head_world(exR, 'RightHand'), 'Right': head_world(exL, 'LeftHand')})
        else:
            hero_grip(None)
            if sp.get('release'):
                hero_arm_free('Left', 0, 0, 0)
        return gaps

    def do_frame(i):
        sp = SEQ[i]
        gaps = pose(i, sp)
        place_drops(drops, max(0.0, (i - SPLIT) * DT) if i >= SPLIT else -1)
        for d in drops:
            if i < SPLIT:
                d.o.hide_render = True
        srcs = [hero.mesh, exR.half, exL.half]
        build_shadow(srcs)
        render_passes(i, srcs, drops)
        print('FRAME', i, 'gaps', {k: round(v, 3) for k, v in gaps.items()},
              'hero feet px', px_of(V((sp['hx'], 0, 0))))

    # camara: ancla comun
    place_cam(CAM, CENTER, float(os.environ.get('DBG_AZ', AZ)), float(os.environ.get('DBG_ELEV', ELEV)))
    CAM.data.ortho_scale = CELL / PPM * float(os.environ.get('DBG_ZOOM', 1.0))
    for ch in (exR, exL):
        ch.half.hide_render = False
    frames = [TEST_F] if MODE == 'test' else list(range(len(SEQ)))
    for i in frames:
        do_frame(i)
    print('A OK', frames)


# =============================================================================================== OPCION B
def run_B():
    ex = new_ex()
    update()
    EB = ('ex_walk', 8)
    HB = ('hero_walk', 1)
    EXX = HXF + 0.21
    black_attr(hero.mesh)
    H0 = 0.62
    SEQ = [
        dict(hx=-0.80, hbase=('hero_walk', 9), lean=16, spine=8, head=-6, pin=False, exx=0.0, lift=0, m=0, heat=0, grip=None, arms=None, ex_lean=4),
        dict(hx=-0.54, hbase=('hero_walk', 13), lean=24, spine=12, head=-8, pin=False, exx=0.0, lift=0, m=0, heat=0, grip=None, arms=None, ex_lean=6),
        dict(hx=HXF, hbase=HB, lean=18, spine=12, head=-8, dz=-0.04, pin=True, exx=EXX + 0.10, lift=0.0, m=0, heat=0, grip='shoulders', arms=(-0.5, 0.35, 0.7), ex_lean=2),
        dict(hx=HXF, hbase=HB, lean=8, spine=4, head=-4, dz=-0.03, pin=True, exx=EXX + 0.03, lift=0.12, m=0, heat=0.25, grip='back', arms=(-0.3, 0.45, 0.85), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=2, spine=0, head=-2, dz=-0.02, pin=True, exx=EXX, lift=0.22, m=0.05, heat=0.6, grip='back', arms=(-0.1, 0.6, 0.75), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=-2, dz=-0.02, pin=True, exx=EXX, lift=0.23, m=0.15, heat=0.85, grip='back', arms=(0.0, 0.7, 0.55), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, dz=-0.02, pin=True, exx=EXX, lift=0.22, m=0.30, heat=1.0, grip='back', arms=(0.1, 0.8, 0.2), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=2, spine=2, head=0, dz=-0.03, pin=True, exx=EXX, lift=0.18, m=0.50, heat=1.0, grip='back', arms=(0.2, 0.7, -0.3), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=6, spine=6, head=0, dz=-0.03, pin=True, exx=EXX + 0.02, lift=0.08, m=0.70, heat=0.8, grip=None, arms=(0.2, 0.5, -0.7), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=6, spine=6, head=-4, dz=-0.02, pin=True, exx=EXX + 0.04, lift=0.0, m=0.85, heat=0.55, grip=None, arms=(0.2, 0.4, -0.9), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=3, spine=3, head=-4, dz=-0.01, pin=True, exx=EXX + 0.05, lift=0.0, m=0.95, heat=0.35, grip=None, arms=(0.2, 0.4, -0.9), ex_lean=0),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, pin=True, exx=EXX + 0.05, lift=0.0, m=1.0, heat=0.2, grip=None, arms=(0.2, 0.4, -0.9), ex_lean=0),
    ]
    rng = random.Random(5)
    drops = []

    def dvel(r):
        return V((r.uniform(-0.05, 0.12), r.uniform(-0.1, 0.1), r.uniform(0.0, 0.25)))
    for k in range(14):
        drops.append(Drop(k, rng, V((EXX + 0.02, rng.uniform(-0.05, 0.05), rng.uniform(0.12, 0.34))), dvel,
                          rng.choice((0.014, 0.018, 0.022)), t0=DT * (4 + k * 0.45)))
    puddle = disc_obj('charco', MAT_PUDDLE, 1.0, noise=0.18)

    def do_frame(i):
        sp = SEQ[i]
        clear_baked()
        hero_pose(sp)
        ex.root.matrix_world = Matrix.Translation((sp['exx'], 0, sp['lift'])) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Scale(EX_K, 4)
        update()
        apply_basis(ex, base(ex, EB))
        rot_bone(ex, 'Spine1', 0, -sp.get('ex_lean', 0) * 0.5)
        rot_bone(ex, 'Spine2', 0, -sp.get('ex_lean', 0) * 0.5)
        if sp['arms'] is not None:
            ax, ay, az_ = sp['arms']
            ex_arm(ex, 'Left', V((ax, -ay, az_)))
            ex_arm(ex, 'Right', V((ax, ay, az_)))
        g = sp['grip']
        if g == 'shoulders':
            hero_grip({'Left': head_world(ex, 'RightArm') + V((0, 0.02, 0)), 'Right': head_world(ex, 'LeftArm') + V((0, -0.02, 0))})
        elif g == 'back':
            zc = 0.46 + sp['lift']
            hero_grip({'Left': V((sp['exx'] + 0.05, 0.055, zc)), 'Right': V((sp['exx'] + 0.05, -0.055, zc))})
        else:
            hero_grip(None)
        m, heat = sp['m'], sp['heat']
        b = bake_static(ex.mesh, 'ex_baked')
        co = get_co(b)
        chest = head_world(hero, 'Spine2') + V((0.06, 0.0, 0.0))
        dist = np.sqrt(((co - np.array(chest)) ** 2).sum(1))
        hv = np.clip(1.0 - dist / 0.20, 0, 1) ** 0.8 * heat
        if m > 0:
            hv = np.clip(hv + m * 0.35 * np.clip(1 - (co[:, 2] - sp['lift']) / H0, 0, 1), 0, 1)
            Fx, Fy = sp['exx'], 0.0
            zr = np.clip(co[:, 2] - sp['lift'], 0, None)
            hn = np.clip(zr / H0, 0, 1)
            zf = 1.0 - 0.93 * m ** 0.9
            dx, dy = co[:, 0] - Fx, co[:, 1] - Fy
            ang = np.arctan2(dy, dx)
            spread = 1.0 + m * 1.5 * (1 - hn) ** 1.3
            spread = spread * (1 + 0.12 * m * np.sin(ang * 5 + zr * 30))
            foot_z = sp['lift'] * max(0.0, 1.0 - 1.4 * m)
            co[:, 0] = Fx + dx * spread
            co[:, 1] = Fy + dy * spread
            co[:, 2] = foot_z + zr * zf
            set_co(b, co)
        set_heat(b, hv)
        print('BBOX ex', co.min(0).round(3), co.max(0).round(3), 'hero chest', tuple(round(x, 3) for x in chest), 'hero hips', tuple(round(x, 3) for x in head_world(hero, 'Hips')))
        rr = 0.04 + 0.19 * (m ** 0.75) if m > 0.12 else 0.0
        puddle.hide_render = rr <= 0.0
        if rr > 0:
            puddle.scale = (rr, rr * 0.9, 1)
            puddle.location = (sp['exx'] + 0.02 * m, 0, 0)
        place_drops(drops, i * DT if i >= 4 else -1)
        for d in drops:
            if i < 4:
                d.o.hide_render = True
        ex.mesh.hide_render = True
        if os.environ.get('DBG_NOHERO'):
            hero.mesh.hide_render = True
        srcs = [b] if os.environ.get('DBG_NOHERO') else [hero.mesh, b]
        build_shadow(srcs, extra=[(sp['exx'] + 0.02 * m, 0, rr * 0.95, rr * 0.8)] if rr > 0 else [])

        def heat_fn(k):
            render_heat(k, [d.o for d in drops] + [puddle])
        render_passes(i, srcs, drops, extra_vis=[puddle] if rr > 0 else [], heat_fn=heat_fn)
        print('FRAME', i, 'hero feet px', px_of(V((sp['hx'], 0, 0))))

    place_cam(CAM, CENTER, float(os.environ.get('DBG_AZ', AZ)), float(os.environ.get('DBG_ELEV', ELEV)))
    CAM.data.ortho_scale = CELL / PPM * float(os.environ.get('DBG_ZOOM', 1.0))
    frames = [TEST_F] if MODE == 'test' else list(range(len(SEQ)))
    for i in frames:
        do_frame(i)
    print('B OK', frames)



# =============================================================================================== OPCION C
def run_C():
    exH = new_ex()       # copia que conserva la cabeza
    exB = new_ex()       # copia que conserva el cuerpo
    update()
    zn = head_world(exH, 'Head').z
    center = V((0, 0, zn))
    for ch, keep in ((exH, 0), (exB, 1)):
        halves = cut_halves(ch, center, V((0, 0, 1)), jag_amp=0.006)
        ch.half = halves[keep]
        bpy.data.objects.remove(halves[1 - keep], do_unlink=True)
        ch.mesh.hide_render = True
    EB = ('ex_walk', 8)
    HB = ('hero_walk', 1)
    EXX = HXF + 0.21
    P0 = V((EXX, 0.0, zn + 0.035))          # centro de la cabeza con el Exvoto en pie
    HAND = V((HXF + 0.03, -0.30, 0.90))     # mano alzada del heroe
    # head: 'at' posicion del centro de la cabeza; tilt/roll en grados (alrededor de Y y X); sq aplastamiento 0..1; fall: sin mano
    SEQ = [
        dict(hx=-0.80, hbase=('hero_walk', 9), lean=16, spine=8, head=-6, pin=False, th=0, hat=P0 + V((0.06, 0, 0)), sq=0, grip=None, ex_lean=4, exx=EXX + 0.06),
        dict(hx=-0.54, hbase=('hero_walk', 13), lean=24, spine=12, head=-8, pin=False, th=0, hat=P0 + V((0.06, 0, 0)), sq=0, grip=None, ex_lean=6, exx=EXX + 0.06),
        dict(hx=HXF, hbase=HB, lean=14, spine=10, head=-8, dz=-0.03, pin=True, th=0, hat=P0, sq=0, grip='both', ex_lean=2, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=6, spine=4, head=-6, dz=-0.04, pin=True, th=0, hat=P0 + V((-0.01, 0, 0.03)), tilt=-12, sq=0, grip='both', ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=-4, spine=-4, head=-2, dz=-0.03, pin=True, th=0, hat=P0 + V((-0.03, 0, 0.10)), tilt=-28, sq=0, grip='both', ex_lean=0, exx=EXX, burst=True),
        dict(hx=HXF, hbase=HB, lean=-8, spine=-8, head=0, dz=-0.01, pin=True, th=4, hat=V((HXF + 0.11, -0.07, 0.86)), hand=V((HXF + 0.06, -0.20, 0.80)), tilt=-15, sq=0, grip='right', ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=-10, spine=-10, head=0, dz=0.0, pin=True, th=14, hat=HAND, hand=HAND, tilt=0, sq=0.05, grip='right', ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=-10, spine=-10, head=0, dz=0.0, pin=True, th=32, hat=HAND, hand=HAND, tilt=0, sq=0.35, grip='right', ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=-8, spine=-8, head=0, dz=0.0, pin=True, th=58, hat=HAND, hand=HAND, tilt=0, sq=0.65, grip='right', ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=-2, spine=-2, head=0, dz=0.0, pin=True, th=82, hat=HAND, hand=HAND, tilt=0, sq=0.85, grip='right', ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=2, spine=2, head=0, dz=-0.01, pin=True, th=90, hat=V((HXF + 0.15, -0.12, 0.45)), tilt=40, sq=0.95, grip=None, ex_lean=0, exx=EXX),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, pin=True, th=90, hat=V((HXF + 0.17, -0.13, 0.03)), tilt=80, sq=1.0, grip=None, ex_lean=0, exx=EXX),
    ]
    rng = random.Random(9)
    drops = []

    def v_neck(r):
        return V((r.uniform(-0.1, 0.1), r.uniform(-0.15, 0.15), r.uniform(0.35, 0.8)))

    def v_drip(r):
        return V((r.uniform(-0.04, 0.04), r.uniform(-0.04, 0.04), r.uniform(0.0, 0.1)))
    for k in range(8):
        drops.append(Drop(k, rng, V((EXX, 0, zn)), v_neck, rng.choice((0.016, 0.022, 0.028)), t0=DT * 4))
    for k in range(10):
        d = Drop(10 + k, rng, HAND + V((0, 0, -0.03)), v_drip, rng.choice((0.012, 0.016, 0.02)), t0=DT * (7 + k * 0.4))
        drops.append(d)
    state = {}

    def do_frame(i):
        sp = SEQ[i]
        clear_baked()
        hero_pose(sp)
        # cuerpo: en pie y, tras el tiron, cae hacia atras (+X) como un tronco, rotando sobre los pies
        th = sp['th']
        exx = sp['exx']
        Mb = Matrix.Translation((exx, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Scale(EX_K, 4)
        exB.root.matrix_world = Mb
        update()
        apply_basis(exB, base(exB, EB))
        rot_bone(exB, 'Spine1', 0, -sp.get('ex_lean', 0) * 0.5)
        rot_bone(exB, 'Spine2', 0, -sp.get('ex_lean', 0) * 0.5)
        if i >= 4:
            ex_arm(exB, 'Left', V((0.25, -0.35, -0.9)))
            ex_arm(exB, 'Right', V((0.25, 0.35, -0.9)))
        if th > 0:
            exB.root.matrix_world = xform_about(V((exx, 0, 0)), 0, th, 0) @ Mb
            update()
        # cabeza: misma pose base, trasladada al punto indicado
        exH.root.matrix_world = Matrix.Translation((exx, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Scale(EX_K, 4)
        update()
        apply_basis(exH, base(exH, EB))
        rot_bone(exH, 'Spine1', 0, -sp.get('ex_lean', 0) * 0.5)
        rot_bone(exH, 'Spine2', 0, -sp.get('ex_lean', 0) * 0.5)
        hat = sp['hat']
        g = sp['grip']
        if g == 'right' and 'hand' in sp:
            hero_grip({'Right': sp['hand']})
            hat = V(head_world(hero, 'RightHand')) + V((0, -0.01, 0.045))
        pivot = V(head_world(exH, 'Head')) + V((0, 0, 0.035))
        Mh0 = exH.root.matrix_world.copy()
        tilt = sp.get('tilt', 0)
        exH.root.matrix_world = Matrix.Translation(hat - pivot) @ xform_about(pivot, 0, tilt, 0) @ Mh0
        update()
        if g == 'both':
            hero_grip({'Left': hat + V((0, 0.05, -0.01)), 'Right': hat + V((0, -0.05, -0.01))})
        elif g == 'right' and 'hand' not in sp:
            hero_grip({'Right': hat + V((0, -0.01, -0.03))})
        elif g is None:
            hero_grip(None)
        # horneado: cabeza aplastada y cuerpo
        bh = bake_static(exH.half, 'head_baked')
        bb = bake_static(exB.half, 'body_baked')
        sq = sp['sq']
        if sq > 0:
            co = get_co(bh)
            c = np.array(hat)
            sxy, sz = 1.0 + 0.45 * sq, 1.0 - 0.60 * sq
            co[:, 0] = c[0] + (co[:, 0] - c[0]) * sxy
            co[:, 1] = c[1] + (co[:, 1] - c[1]) * sxy
            co[:, 2] = c[2] + (co[:, 2] - c[2]) * sz
            set_co(bh, co)
        exH.half.hide_render = True
        exB.half.hide_render = True
        place_drops(drops, i * DT)
        srcs = [hero.mesh, bh, bb]
        build_shadow(srcs)
        render_passes(i, srcs, drops)
        print('FRAME', i, 'hero feet px', px_of(V((sp['hx'], 0, 0))))

    place_cam(CAM, CENTER, float(os.environ.get('DBG_AZ', AZ)), float(os.environ.get('DBG_ELEV', ELEV)))
    CAM.data.ortho_scale = CELL / PPM * float(os.environ.get('DBG_ZOOM', 1.0))
    frames = [TEST_F] if MODE == 'test' else list(range(len(SEQ)))
    for i in frames:
        do_frame(i)
    print('C OK', frames)



def main():
    {'A': run_A, 'B': run_B, 'C': run_C}[OPT]()


main()
