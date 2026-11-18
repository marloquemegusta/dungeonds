"""Remate (glory kill) del Corazon Abierto sobre el Exvoto, ronda 2: las tres opciones en la MISMA celda y anclaje.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/ds_remate_exvoto.py -- <raiz> <salida> <A|B|C> <test|all> [fotograma]

Escribe en <salida>/ds_exvoto_<X>/raw los pases de cada fotograma (fNN_lit, fNN_flat, sNN sombra, hNN calor).
ds_remate_exvoto_post.py los compone en los PNG 1x y en el GIF de control (paleta global).

Opciones:
  A: lo agarra de cada muneca y tira hacia los lados: se parte en VERTICAL (de la cabeza a la entrepierna); las dos
     mitades caen a los lados y quedan tumbadas con la cara de corte (cera ocre) hacia arriba. Silueta: V ancha y baja.
  B: lo abraza contra el pecho abierto y el fuego del Corazon lo derrite: se hunde y se escurre hasta un charco con el
     velo encima. Silueta: una sola masa baja, sin arcos.
  C: lo levanta por la cintura hasta encima de su cabeza y lo estampa contra el suelo partido por la cintura; la mitad
     alta sale despedida hacia delante. Silueta: arco vertical alto, distinta de A y B.

Mundo: el heroe mira a +X con los pies en x=HXF; el Exvoto a su derecha mira a -X. Camara ortografica a 30 grados de
elevacion y azimut 45 (la vista diagonal del juego). La celda y el anclaje (pies del heroe) son iguales en las tres.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ds_remate_exvoto_lib import *

A_ = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT, OPT, MODE = A_[0], A_[1], A_[2], A_[3]
TEST_F = int(A_[4]) if len(A_) > 4 else 5
RAW = os.path.join(OUT, 'ds_exvoto_' + OPT, 'raw')
os.makedirs(RAW, exist_ok=True)

EXFBX = ROOT + '/assets/models/characters/exvoto/source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx'
HEROFBX = ROOT + '/assets/models/characters/corazon/source/corazon.fbx'

bpy.ops.wm.read_factory_settings(use_empty=True)
CAM = setup_render()
load_acts(ROOT)
DT = 0.06

MAT_WAX = [flat_mat('gotaA', (0.55, 0.48, 0.34, 1)), flat_mat('gotaB', (0.48, 0.35, 0.20, 1))]
set_wax(MAT_WAX)
MAT_BLACK = flat_mat('negro', (0.02, 0.02, 0.025, 1))
MAT_PUDDLE = flat_mat('charco', (0.46, 0.37, 0.22, 1))
MAT_VEIL = flat_mat('velo', (0.05, 0.045, 0.05, 1))
MAT_HEAT = flat_mat('calor', (1.0, 0.74, 0.40, 1))

HXF = -0.30
CENTER = V((0.01, 0.00, 0.46))
EX_K = 0.86

hero = make_char(HEROFBX, 90, 1.0, (HXF, 0, 0))
update()

hero_ik = {}
for side in ('Left', 'Right'):
    hero_ik[side] = add_ik(hero, side + 'ForeArm', 'hG' + side)
    hero_ik['leg' + side] = add_ik(hero, side + 'Leg', 'hF' + side)

REACH = (tail_world(hero, 'LeftArm') - head_world(hero, 'LeftArm')).length \
    + (tail_world(hero, 'LeftForeArm') - head_world(hero, 'LeftForeArm')).length
print('REACH', round(REACH, 3))


def new_ex(loc=(0, 0, 0)):
    return make_char(EXFBX, -90, EX_K, loc)


CACHE = {}


def base(ch, key):
    k = (id(ch), key)
    if k not in CACHE:
        CACHE[k] = capture(ch, key[0], key[1])
    return CACHE[k]


def hero_pose(hp):
    hero.root.location.x = hp['hx']
    for k in ('Left', 'Right', 'legLeft', 'legRight'):
        hero_ik[k][1].influence = 0.0
    update()
    apply_basis(hero, base(hero, hp['hbase']))
    if hp.get('pin'):
        for side in ('Left', 'Right'):
            hero_ik['leg' + side][0].location = head_world(hero, side + 'Foot')
    Mh = bone_world(hero, 'Hips')
    set_bone_world(hero, 'Hips', xform_about(Mh.translation.copy(), 0, hp.get('lean', 0), 0,
                                             (0, 0, hp.get('dz', 0))) @ Mh)
    rot_bone(hero, 'Spine1', 0, hp.get('spine', 0) * 0.5)
    rot_bone(hero, 'Spine2', 0, hp.get('spine', 0) * 0.5)
    rot_bone(hero, 'Head', 0, hp.get('head', 0))
    if hp.get('pin'):
        for side in ('Left', 'Right'):
            hero_ik['leg' + side][1].influence = 1.0
    update()


def hero_grip(targets):
    """IK de las manos a los puntos de mundo; el objetivo se recorta al alcance (nunca estira el brazo)."""
    gaps = {}
    for side in ('Left', 'Right'):
        c = hero_ik[side][1]
        t = targets.get(side) if targets else None
        if t is None:
            c.influence = 0.0
            continue
        sh = head_world(hero, side + 'Arm')
        d = t - sh
        gaps[side] = round(max(0.0, d.length - REACH), 3)
        hero_ik[side][0].location = sh + d.normalized() * min(d.length, REACH)
        c.influence = 1.0
    update()
    return gaps


def ex_arm(ch, side, d):
    """Orienta el brazo del Exvoto en la direccion de mundo d (sin estirar la cadena)."""
    d = V(d).normalized()
    for nm in ('Arm', 'ForeArm', 'Hand'):
        b = side + nm
        h, t = head_world(ch, b), tail_world(ch, b)
        aim_bone(ch, b, h + d * (t - h).length)


def pose_ex(ch, key, exlean=0.0, x=0.0, extra=None, sq=1.0):
    """Pose base + inclinacion + traslacion rigida en el mundo (extra va antes del root)."""
    M = Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z') \
        @ Matrix.Scale(EX_K, 4) @ Matrix.Diagonal((1.0, 1.0, sq, 1.0)).to_4x4()
    ch.root.matrix_world = (extra @ M) if extra is not None else M
    apply_basis(ch, base(ch, key))
    rot_bone(ch, 'Spine1', 0, -exlean * 0.5)
    rot_bone(ch, 'Spine2', 0, -exlean * 0.5)
    update()


def zmin(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    vs, _ = eval_world_mesh(ob, dg)
    return min(v.z for v in vs)


def settle(ob, floor=0.0):
    """Deja el punto mas bajo del objeto en `floor`: nada flota ni queda hundido."""
    ob.matrix_world = Matrix.Translation((0, 0, floor - zmin(ob))) @ ob.matrix_world
    update()


# ----------------------------------------------------------------------------------------------- render
def render_passes(i, visible, heat=None):
    sc = bpy.context.scene
    sh = sc.display.shading
    for o in visible:
        o.hide_render = False
    if SHADOW['ob'] is not None:
        SHADOW['ob'].hide_render = True
    sh.light = 'STUDIO'
    render_to(os.path.join(RAW, 'f%02d_lit.png' % i))
    sh.light = 'FLAT'
    render_to(os.path.join(RAW, 'f%02d_flat.png' % i))
    hid = [(o, o.hide_render) for o in visible]
    for o, _ in hid:
        o.hide_render = True
    if SHADOW['ob'] is not None:
        SHADOW['ob'].hide_render = False
        render_to(os.path.join(RAW, 's%02d.png' % i))
        SHADOW['ob'].hide_render = True
    if heat is not None:
        sh.color_type = 'SINGLE'
        sh.single_color = MAT_HEAT.diffuse_color
        heat.hide_render = False
        render_to(os.path.join(RAW, 'h%02d.png' % i))
        heat.hide_render = True
        sh.color_type = 'TEXTURE'
    for o, h in hid:
        o.hide_render = h


def px_of(pw):
    from bpy_extras.object_utils import world_to_camera_view
    co = world_to_camera_view(bpy.context.scene, CAM, pw)
    return (round(co.x * CELL[0], 1), round((1 - co.y) * CELL[1], 1))


def hide_all(objs):
    for o in objs:
        o.hide_render = True


BAKED = []


def clear_baked():
    for o in BAKED:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me, do_unlink=True)
    del BAKED[:]


def bake_move(ob, extra, name):
    """Congela el trozo con su deformacion actual y le aplica `extra` en el mundo (movimiento rigido)."""
    nb = bake(ob, name)
    nb.matrix_world = extra
    BAKED.append(nb)
    return nb


def make_blob(name, mat, r, wob, n, z, seed):
    return new_blob(name, mat, r=r, wob=wob, n=n, z=z, seed=seed)


def frame_visible(i, ob):
    return not ob.hide_render


# =============================================================================================== OPCION A
def run_A():
    ex = new_ex()
    hide_all([ex.mesh, hero.mesh])
    live = []                              # pase del fotograma (cuerpo entero antes del corte, luego las mitades)
    halves = {}                            # mitades rigidas, creadas en el fotograma del corte
    EB = ('ex_walk', 8)
    HB = ('hero_walk', 1)
    SPLIT = 5
    # ex: x del Exvoto | exlean: inclinacion | arm: (angulo desde el frente, alzado) | gap: separacion de las mitades
    # (m) | tilt: caida de cada mitad a su lado (grados) | drop: caida vertical (m)
    SEQ = [
        dict(hx=HXF - 0.50, hbase=('hero_walk', 9), lean=14, spine=6, head=-6, pin=False,
             ex=0.14, exlean=10, arm=None, gap=0.0, tilt=0, drop=0.0),
        dict(hx=HXF - 0.26, hbase=('hero_walk', 13), lean=24, spine=10, head=-8, pin=False,
             ex=0.08, exlean=16, arm=None, gap=0.0, tilt=0, drop=0.0),
        dict(hx=HXF, hbase=HB, lean=16, spine=10, head=-8, dz=-0.02, pin=True,
             ex=0.02, exlean=8, arm=(26, 0.30), gap=0.0, tilt=0, drop=0.0),
        dict(hx=HXF, hbase=HB, lean=26, spine=18, head=-10, dz=-0.08, pin=True,
             ex=0.01, exlean=20, arm=(30, 0.34), gap=0.0, tilt=0, drop=0.0),
        dict(hx=HXF, hbase=HB, lean=28, spine=20, head=-10, dz=-0.09, pin=True,
             ex=0.01, exlean=24, arm=(34, 0.36), gap=0.0, tilt=0, drop=0.0),
        dict(hx=HXF, hbase=HB, lean=10, spine=4, head=-4, dz=-0.04, pin=True,
             ex=0.01, exlean=2, arm=(50, 0.22), gap=0.045, tilt=14, drop=0.0),
        dict(hx=HXF, hbase=HB, lean=2, spine=0, head=-2, dz=-0.03, pin=True,
             ex=0.02, exlean=-2, arm=(64, 0.14), gap=0.085, tilt=38, drop=0.0),
        dict(hx=HXF, hbase=HB, lean=-2, spine=-2, head=0, dz=-0.03, pin=True,
             ex=0.03, exlean=-4, arm=(72, 0.08), gap=0.115, tilt=64, drop=0.02),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, dz=-0.02, pin=True,
             ex=0.04, exlean=-4, arm=(76, 0.04), gap=0.132, tilt=84, drop=0.08),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, dz=-0.01, pin=True,
             ex=0.04, exlean=-4, arm=(78, 0.02), gap=0.138, tilt=92, drop=0.14),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, pin=True,
             ex=0.04, exlean=-4, arm=(78, 0.02), gap=0.138, tilt=95, drop=0.15),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, pin=True,
             ex=0.04, exlean=-4, arm=(78, 0.02), gap=0.138, tilt=95, drop=0.15),
    ]
    rng = random.Random(3)
    drops = [Drop(k, rng, (0, 0, 0.55),
                  lambda r: V((r.uniform(-0.20, 0.28), r.uniform(-0.55, 0.55), r.uniform(0.35, 0.95))),
                  rng.choice((0.028, 0.036, 0.046)), 0.0) for k in range(12)]
    state = {'cut': None}
    temp = []

    def free_temp():
        for o in temp:
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me, do_unlink=True)
        del temp[:]

    def pose(i, sp):
        hero_pose(sp)
        free_temp()
        del live[:]
        out = {}
        phi, lift = sp['arm'] if sp['arm'] else (0, 0)
        ph = math.radians(phi)
        ex_arm(ex, 'Right', V((-math.cos(ph), math.sin(ph), lift - 0.35)))
        ex_arm(ex, 'Left', V((-math.cos(ph), -math.sin(ph), lift - 0.35)))
        pose_ex(ex, EB, sp['exlean'], sp['ex'])
        out['R'] = head_world(ex, 'RightHand')
        out['L'] = head_world(ex, 'LeftHand')
        if i < SPLIT:
            whole = bake(ex.mesh, 'wholeA%02d' % i)
            temp.append(whole)
            live.append(whole)
        else:
            if state['cut'] is None:
                whole = bake(ex.mesh, 'wholeAcut')
                c = head_world(ex, 'Hips')
                pos, neg = cut_object(whole, c, V((0, 1, 0)), jag_amp=0.006)
                state['cut'] = c
                halves['pos'], halves['neg'] = pos, neg
                wme = whole.data
                bpy.data.objects.remove(whole, do_unlink=True)
                if wme.users == 0:
                    bpy.data.meshes.remove(wme, do_unlink=True)
            for key, sg in (('pos', 1), ('neg', -1)):
                ob = halves[key]
                piv = V((0, sg * 0.04, 0))
                ob.matrix_world = xform_about(piv, sg * sp['tilt'], 0, 0,
                                              (0, sg * sp['gap'], -sp['drop']))
                update()
                settle(ob)
                live.append(ob)
        if sp['arm'] is not None and i <= SPLIT:
            return hero_grip({'Left': out['R'], 'Right': out['L']}), out
        hero_grip(None)
        return {}, out
    return SEQ, pose, (), {'SPLIT': SPLIT, 'drops': drops, 'heat': None,
                           'draw': lambda i, parts: list(live),
                           'cut_fn': lambda: state['cut'] or V((0, 0, 0.4))}


# =============================================================================================== OPCION B
def run_B():
    ex = new_ex()
    EB = ('ex_pray', 10)
    HB = ('hero_walk', 1)
    SPLIT = 3
    SEQ = [
        dict(hx=HXF - 0.48, hbase=('hero_walk', 9), lean=12, spine=6, head=-6, pin=False, sq=1.00, hug=0.0, ex=0.14),
        dict(hx=HXF - 0.26, hbase=('hero_walk', 13), lean=20, spine=10, head=-8, pin=False, sq=1.00, hug=0.0, ex=0.08),
        dict(hx=HXF, hbase=HB, lean=16, spine=12, head=-4, dz=-0.03, pin=True, sq=1.00, hug=0.55, ex=0.02),
        dict(hx=HXF, hbase=HB, lean=12, spine=8, head=-2, dz=-0.05, pin=True, sq=0.99, hug=1.0, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=10, spine=6, head=0, dz=-0.06, pin=True, sq=0.95, hug=1.0, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=8, spine=4, head=0, dz=-0.07, pin=True, sq=0.86, hug=1.0, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=8, spine=2, head=0, dz=-0.08, pin=True, sq=0.73, hug=1.0, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=6, spine=0, head=0, dz=-0.09, pin=True, sq=0.58, hug=1.0, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=4, spine=0, head=0, dz=-0.09, pin=True, sq=0.44, hug=0.9, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=2, spine=0, head=0, dz=-0.09, pin=True, sq=0.32, hug=0.6, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, dz=-0.08, pin=True, sq=0.22, hug=0.25, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, dz=-0.08, pin=True, sq=0.16, hug=0.0, ex=0.01),
        dict(hx=HXF, hbase=HB, lean=0, spine=0, head=0, dz=-0.07, pin=True, sq=0.14, hug=0.0, ex=0.01),
    ]
    rng = random.Random(5)
    puddle = make_blob('charco', MAT_PUDDLE, 0.26, 0.30, 18, 0.006, 4)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(0, 0, 0.05))
    veil = bpy.context.active_object
    veil.name = 'velo'
    veil.data.materials.append(MAT_VEIL)
    veil.scale = (0.17, 0.13, 0.055)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.16, location=(0, 0, -5))
    heat = bpy.context.active_object
    heat.name = 'calor'
    heat.data.materials.append(MAT_HEAT)
    heat.hide_render = True
    parts = (puddle, veil)
    hide_all(list(parts) + [hero.mesh])
    drops = [Drop(k, rng, (0, 0, 0.55),
                   lambda r: V((r.uniform(-0.08, 0.12), r.uniform(-0.12, 0.12), r.uniform(-0.25, -0.05))),
                   rng.choice((0.026, 0.034, 0.042)), 0.0) for k in range(12)]

    def pose(i, sp):
        hero_pose(sp)
        sq = sp['sq']
        wt = 1.0 + 0.26 * (1.0 - sq)
        extra = Matrix.Diagonal((wt, wt, 1.0, 1.0)).to_4x4()
        pose_ex(ex, EB, 4.0 + 10.0 * (1.0 - sq), sp['ex'], extra, sq)
        if sp['hug'] > 0.01:
            tR = head_world(ex, 'RightShoulder') + V((0.01, -0.10, -0.06))
            tL = head_world(ex, 'LeftShoulder') + V((0.01, 0.10, -0.06))
            mid = (tR + tL) * 0.5
            k = sp['hug']
            return hero_grip({'Left': mid + (tR - mid) * k, 'Right': mid + (tL - mid) * k}), {'R': tR, 'L': tL}
        hero_grip(None)
        return {}, {'R': head_world(ex, 'RightShoulder'), 'L': head_world(ex, 'LeftShoulder')}

    def post(i):
        k = max(0.0, min(1.0, (i - (SPLIT + 3)) / float(len(SEQ) - 1 - (SPLIT + 3))))
        puddle.hide_render = i < SPLIT + 3
        puddle.scale = (0.30 + 1.00 * k, 0.30 + 0.90 * k, 1)
        puddle.location = (0.02, 0.0, 0.006)
        veil.hide_render = i < len(SEQ) - 3
        veil.location = (0.02, 0.0, 0.10 - 0.05 * k + 0.02)
        veil.scale = (0.17 + 0.02 * k, 0.13 + 0.02 * k, 0.055 - 0.02 * k)
        c = head_world(hero, 'Spine2')
        heat.location = (c.x + 0.05, c.y, c.z - 0.03)
        heat.scale = (0.85, 0.6, 0.7)

    def draw(i, parts):
        return [o for o in parts if not o.hide_render] + [ex.mesh]
    return SEQ, pose, parts, {'SPLIT': SPLIT, 'drops': drops, 'heat': heat, 'post': post, 'draw': draw,
                               'cut_fn': lambda: head_world(ex, 'Spine')}


# =============================================================================================== OPCION C
def run_C():
    ex = new_ex()
    hide_all([ex.mesh, hero.mesh])
    live = []
    halves = {}
    EB = ('ex_walk', 8)
    HB = ('hero_walk', 1)
    SPLIT = 8
    # lift: altura del Exvoto entero sobre el suelo | tilt: vuelco de la mitad alta hacia +X (grados) | fy: caida de la
    # mitad alta hasta el suelo (m). La mitad baja se queda donde cae.
    SEQ = [
        dict(hx=HXF - 0.50, hbase=('hero_walk', 9), lean=14, spine=6, head=-6, pin=False,
             ex=0.12, exlean=12, lift=0.0, tilt=0.0),
        dict(hx=HXF - 0.26, hbase=('hero_walk', 13), lean=24, spine=12, head=-8, pin=False,
             ex=0.06, exlean=18, lift=0.0, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=28, spine=20, head=-10, dz=-0.09, pin=True,
             ex=0.00, exlean=26, lift=0.0, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=22, spine=14, head=-6, dz=-0.06, pin=True,
             ex=-0.02, exlean=10, lift=0.10, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=10, spine=4, head=-2, dz=-0.02, pin=True,
             ex=-0.04, exlean=-6, lift=0.26, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=-6, spine=-6, head=0, dz=0.02, pin=True,
             ex=-0.05, exlean=-16, lift=0.42, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=-14, spine=-12, head=2, dz=0.04, pin=True,
             ex=-0.05, exlean=-22, lift=0.50, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=12, spine=10, head=-6, dz=-0.03, pin=True,
             ex=-0.04, exlean=4, lift=0.26, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=36, spine=28, head=-14, dz=-0.14, pin=True,
             ex=-0.03, exlean=44, lift=0.0, tilt=0.0),
        dict(hx=HXF, hbase=HB, lean=32, spine=24, head=-12, dz=-0.12, pin=True,
             ex=-0.03, exlean=44, lift=0.0, tilt=52.0),
        dict(hx=HXF, hbase=HB, lean=26, spine=18, head=-8, dz=-0.09, pin=True,
             ex=-0.03, exlean=44, lift=0.0, tilt=84.0),
        dict(hx=HXF, hbase=HB, lean=22, spine=14, head=-6, dz=-0.08, pin=True,
             ex=-0.03, exlean=44, lift=0.0, tilt=90.0),
    ]
    rng = random.Random(13)
    drops = [Drop(k, rng, (0, 0, 0.60),
                   lambda r: V((r.uniform(-0.05, 0.45), r.uniform(-0.40, 0.40), r.uniform(-0.10, 0.35))),
                   rng.choice((0.030, 0.040, 0.050)), 0.0) for k in range(12)]
    state = {'cut': None, 'piv': None}

    def pose(i, sp):
        hero_pose(sp)
        for ob in live:
            bpy.data.meshes.remove(ob.data, do_unlink=True)
        del live[:]
        pose_ex(ex, EB, sp['exlean'], sp['ex'])
        whole = bake(ex.mesh, 'wholeC%02d' % i)
        BAKED.append(whole)
        if i < SPLIT:
            whole.matrix_world = Matrix.Translation((0, 0, sp['lift'])) @ whole.matrix_world
            live.append(whole)
            hip = head_world(ex, 'Hips') + V((0, 0, sp['lift']))
            if sp['lift'] > 0.02:
                return hero_grip({'Left': hip + V((0, 0.09, 0.0)), 'Right': hip + V((0, -0.09, 0.0))}), {}
            hero_grip(None)
            return {}, {}
        if state['cut'] is None:
            c = head_world(ex, 'Spine')
            state['cut'] = c
            whole.matrix_world = Matrix.Translation((0, 0, sp['lift'])) @ whole.matrix_world
            update()
            top, bot = cut_object(whole, c, V((0, 0, 1)), jag_amp=0.006)
            state['piv'] = c
            BAKED.extend((top, bot))
            halves['top'], halves['bot'] = top, bot
        bpy.data.objects.remove(whole, do_unlink=True)
        BAKED.remove(whole)
        bot = halves['bot']
        top = halves['top']
        bot.matrix_world = Matrix.Identity(4)
        top.matrix_world = xform_about(state['piv'], 0, sp['tilt'], 0, (0.02, 0.0, 0.0))
        update()
        settle(bot, 0.0)
        settle(top, 0.0)
        live.extend((top, bot))
        hero_grip(None)
        return {}, {}
    return SEQ, pose, (), {'SPLIT': SPLIT, 'drops': drops, 'heat': None,
                            'draw': lambda i, parts: list(live),
                            'cut_fn': lambda: state['cut'] or V((0, 0, 0.4))}


# =============================================================================================== bucle
def main():
    SEQ, pose, parts, info = {'A': run_A, 'B': run_B, 'C': run_C}[OPT]()
    SPLIT = info['SPLIT']
    place_cam(CAM, CENTER, float(os.environ.get('DBG_AZ', AZ)), float(os.environ.get('DBG_ELEV', ELEV)),
              float(os.environ.get('DBG_ZOOM', 1.0)))
    info['hidden'] = []
    frames = [TEST_F] if MODE == 'test' else list(range(len(SEQ)))
    for i in frames:
        sp = SEQ[i]
        gaps, _ = pose(i, sp)
        if 'post' in info:
            info['post'](i)
        t = max(0.0, (i - SPLIT) * DT)
        if info.get('drops'):
            cut = info['cut_fn']()
            if i == SPLIT:
                for k, d in enumerate(info['drops']):
                    d.o0 = cut + V((0, 0, 0))
            for d in info['drops']:
                d.place(t if i >= SPLIT else -1)
        vis = [hero.mesh] + info['draw'](i, parts) + [d.o for d in info['drops'] if not d.o.hide_render]
        build_shadow(vis, mat=MAT_BLACK)
        render_passes(i, vis, info.get('heat'))
        print('FRAME', OPT, i, 'gaps', gaps, 'feet', px_of(V((sp['hx'], 0, 0))))
    print(OPT, 'OK', frames, 'cell', CELL)


main()
