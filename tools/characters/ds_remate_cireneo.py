"""PROTOTIPO ronda 2 del remate (glory kill) del Corazon Abierto sobre el CIRENEO: tres opciones (A, B, C) en un solo sprite
combinado (heroe + Cireneo + su cruz + trozos), camara diagonal ortografica de 30 grados. Solo prueba: no toca el juego.

  A = el heroe le arranca la cruz de la espalda y lo atraviesa con ella contra el suelo.
  B = lo tumba boca abajo de una patada voladora y le deja caer encima su propia cruz.
  C = suplex aleman: lo levanta agarrandolo por la cruz y lo clava de cabeza en el suelo (silueta vertical, invertida).

Uso (Blender, el resultado son PNG a 4x en <salida_raw>; proto_remate_cireneo_sheet.py los monta):
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/proto_remate_cireneo.py -- <raiz_worktree> <salida_raw> <opcion A|B|C|probe> [modo]
  modo: key (un solo fotograma clave, regla 11) | all (toda la secuencia) | N (un fotograma concreto)

Mundo: Cireneo en el origen mirando a +X; el heroe llega desde -X (por la espalda, el lado de la cruz). El heroe se escala
a HERO_K respecto al Cireneo (escalas reales de la ROM, ver proto_remate_cireneo_lib.py).
"""
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
from ds_remate_cireneo_lib import *
import ds_remate_cireneo_lib as L

A = sys.argv[sys.argv.index('--') + 1:]
ROOT = A[0]
OUT = A[1]
OPT = A[2] if len(A) > 2 else 'A'
MODE = A[3] if len(A) > 3 else 'all'
os.makedirs(OUT, exist_ok=True)

CELL = int(os.environ.get('REMATE_CELL', '80'))
AZ = float(os.environ.get('REMATE_AZ', '-45'))
PPM_CAM = float(os.environ.get('REMATE_PPM', '48'))   # densidad de la camara (celda 80 = 1.67 m de ancho)
CAM_CENTER = Vector((0.04, -0.14, 0.30))     # mismo anclaje para las tres opciones
HERO_X = -0.62                               # sitio del heroe en reposo (y donde acaban las tres opciones)
GAIN_HERO, GAIN_CIR = 3.0, 3.5

bpy.ops.wm.read_factory_settings(use_empty=True)

# ----------------------------------------------------------------------------------------------- personajes
hero = make_char(ROOT + '/assets/models/characters/corazon/source/corazon.fbx', 90, HERO_K, (HERO_X, 0, 0))
cir = make_char(MAIN + '/assets/models/characters/cireneo/cireneo_stuck.fbx', 90, 1.0, (0, 0, 0))
ACT['cir_stuck'] = [a for a in bpy.data.actions if 'cireneo_stuck' in a.name][0]
ACT['cir_stuck'].use_fake_user = True
ACT['hero_walk'] = load_action(ROOT + '/assets/models/animations/corazon/walk.fbx', 'hero_walk')
ACT['hero_shot'] = load_action(ROOT + '/assets/models/animations/corazon/disparo.fbx', 'hero_shot')
gain_textures([hero.mesh], GAIN_HERO)
gain_textures([cir.mesh, cir.cruz], GAIN_CIR)
update()
CAM = setup_render(CELL, PPM_CAM)

# "mundo": todo lo que se renderiza cuelga de aqui para poder aplastarlo/cizallarlo en el pase de sombra
world = bpy.data.objects.new('mundo', None)
bpy.context.scene.collection.objects.link(world)
shadow_par = bpy.data.objects.new('mundo_p', None)
bpy.context.scene.collection.objects.link(shadow_par)
world.parent = shadow_par
for ch in (hero, cir):
    ch.root.parent = world
SHEAR = Matrix(((1, 0, 0.40, 0), (0, 1, 0.0, 0), (0, 0, 0.002, 0), (0, 0, 0, 1)))   # sombra hacia +X (abajo a la derecha en pantalla)

# ----------------------------------------------------------------------------------------------- IK de los brazos del heroe
hero_ik = {}
for side in ('Left', 'Right'):
    hero_ik[side] = add_ik(hero, side + 'ForeArm', 'hG' + side)
    hero_ik['leg' + side] = add_ik(hero, side + 'Leg', 'hF' + side)


def set_ik(infl_arms=None, infl_legs=None):
    for s in ('Left', 'Right'):
        if infl_arms is not None:
            hero_ik[s][1].influence = infl_arms
        if infl_legs is not None:
            hero_ik['leg' + s][1].influence = infl_legs


_cache = {}


def base(ch, key):
    k = (id(ch), key)
    if k not in _cache:
        _cache[k] = capture(ch, key[0], key[1])
    return _cache[k]


# ----------------------------------------------------------------------------------------------- IK de piernas (analitico, mundo)
def aim_bone(ch, name, target):
    pb = ch.arm.pose.bones[P + name]
    hd = W(ch) @ pb.head
    tl = W(ch) @ pb.tail
    cur = (tl - hd).normalized()
    want = (target - hd).normalized()
    R = cur.rotation_difference(want).to_matrix().to_4x4()
    Mw = bone_world(ch, name)
    T = Matrix.Translation(hd)
    set_bone_world(ch, name, T @ R @ T.inverted() @ Mw)


def leg_ik(ch, side, foot, pole):
    """Pierna de dos huesos a un punto del mundo; `pole` = direccion de la rodilla."""
    up, lg = side + 'UpLeg', side + 'Leg'
    pu, pl, pf = ch.arm.pose.bones[P + up], ch.arm.pose.bones[P + lg], ch.arm.pose.bones[P + side + 'Foot']
    H = W(ch) @ pu.head
    K0 = W(ch) @ pl.head
    A0 = W(ch) @ pf.head
    L1 = (K0 - H).length
    L2 = (A0 - K0).length
    d = foot - H
    dist = min(d.length, (L1 + L2) * 0.998)
    dirn = d.normalized()
    a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    pp = (pole - dirn * pole.dot(dirn))
    pp = pp.normalized() if pp.length > 1e-6 else Vector((0, 0, 1))
    knee = H + dirn * a + pp * h
    aim_bone(ch, up, knee)
    aim_bone(ch, lg, H + dirn * dist)


def foot_flat(ch, side):
    pb = ch.arm.pose.bones[P + side + 'Foot']
    Mw = bone_world(ch, side + 'Foot')
    sc = Mw.to_scale()
    R = (W(ch).to_3x3().normalized() @ pb.bone.matrix_local.to_3x3().normalized() @ Matrix.Diagonal(sc)).to_4x4()
    set_bone_world(ch, side + 'Foot', Matrix.Translation(Mw.translation) @ R)


# ----------------------------------------------------------------------------------------------- cuerpo rigido de un personaje
def root_matrix(ch, pivot=None, rx=0.0, ry=0.0, rz=0.0, trans=(0, 0, 0), base_loc=None, base_rz=90.0, scale=1.0, sz=1.0):
    """Coloca el nodo raiz: rotacion base (de cara a +X) mas un giro rigido en ejes de mundo alrededor de `pivot`."""
    loc = base_loc if base_loc is not None else Vector((0, 0, 0))
    M0 = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(base_rz), 4, 'Z') @ Matrix.Diagonal((scale, scale, scale * sz, 1))
    pv = pivot if pivot is not None else loc
    Mx = xform_about(pv, ry, rz, rx, trans) @ M0
    ch.root.matrix_world = Mx
    update()


# ----------------------------------------------------------------------------------------------- Cireneo
CIR_BASE = ('cir_stuck', 9)


def cir_pose(frame=9, hips_pitch=12.0, hips_dz=0.0, hips_dx=0.0, spine=0.0, head=0.0, feet=None, pole=V((1, 0, 0)),
             flat=True, extra=None):
    """Pose base del clip de aturdido + inclinaciones en mundo. `feet`: dict side->posicion de mundo (o None = no tocar piernas)."""
    cir.cruz_state = 'skin'
    apply_basis(cir, base(cir, ('cir_stuck', frame)))
    update()
    f0 = {s: W(cir) @ cir.arm.pose.bones[P + s + 'Foot'].head for s in ('Left', 'Right')}
    Mh = bone_world(cir, 'Hips')
    set_bone_world(cir, 'Hips', xform_about(Mh.translation.copy(), hips_pitch, 0, 0, (hips_dx, 0, hips_dz)) @ Mh)
    for n, share in (('Spine', 0.4), ('Spine1', 0.3), ('Spine2', 0.3)):
        bend(cir, n, spine * share)
    bend(cir, 'Head', head)
    tgt = feet if feet is not None else f0
    for s in ('Left', 'Right'):
        leg_ik(cir, s, tgt[s] if s in tgt else f0[s], pole)
        if flat:
            foot_flat(cir, s)
    if extra:
        extra()
    return f0


def cir_feet_rest():
    apply_basis(cir, base(cir, CIR_BASE))
    return {s: W(cir) @ cir.arm.pose.bones[P + s + 'Foot'].head for s in ('Left', 'Right')}


# ----------------------------------------------------------------------------------------------- heroe
def hero_pose(hx, hbase=('hero_walk', 1), hips_lean=0.0, spine=0.0, head=0.0, hips_dz=0.0, hy=0.0, legs_planted=True,
              hands=None, extra=None, airborne=None, spin=0.0):
    """Heroe: base del andar + inclinaciones. `hands` = (puntoIzq, puntoDer) en mundo (IK de brazos); None = brazos de la base.
    `airborne` = funcion que dobla las piernas (si no, los pies se clavan donde los deja la base). `spin` = giro sobre la vertical."""
    set_ik(0.0, 0.0)
    hero.root.matrix_world = Matrix.Translation(V((hx, hy, 0))) @ Matrix.Rotation(math.radians(90 + spin), 4, 'Z') @ Matrix.Diagonal((HERO_K,) * 3 + (1,))
    update()
    apply_basis(hero, base(hero, hbase))
    feet0 = {s: head_world(hero, s + 'Foot') for s in ('Left', 'Right')}
    Mh = bone_world(hero, 'Hips')
    ph = Mh.translation.copy()
    set_bone_world(hero, 'Hips', xform_about(ph, hips_lean, 0, 0, (0, 0, hips_dz)) @ Mh)
    bend(hero, 'Spine1', spine * 0.5)
    bend(hero, 'Spine2', spine * 0.5)
    bend(hero, 'Head', head)
    if legs_planted:
        for s in ('Left', 'Right'):
            tgt, c = hero_ik['leg' + s]
            tgt.location = feet0[s]
            c.influence = 1.0
    if airborne:
        airborne()
    if hands is not None:
        for s, p in zip(('Left', 'Right'), hands):
            hero_ik[s][0].location = p
            hero_ik[s][1].influence = 1.0
    update()
    if extra:
        extra()


# ----------------------------------------------------------------------------------------------- cruz libre
CRUZ_Y0 = 5.0   # cm: profundidad del centro del palo en el espacio local del armature


def cruz_place(grip_world, up, bar, grip_z_cm, y_cm=CRUZ_Y0):
    """Cruz como solido libre: el punto del palo a `grip_z_cm` (cm locales) cae en `grip_world`; `up` = direccion del palo
    (de la base hacia arriba), `bar` = direccion del travesaño."""
    u = Vector(up).normalized()
    b = Vector(bar)
    b = (b - u * b.dot(u)).normalized()
    y = u.cross(b)
    R = Matrix(((b.x, y.x, u.x, 0), (b.y, y.y, u.y, 0), (b.z, y.z, u.z, 0), (0, 0, 0, 1)))
    M = Matrix.Translation(Vector(grip_world)) @ R @ Matrix.Scale(0.01, 4) @ Matrix.Translation(-Vector((0.0, y_cm, grip_z_cm)))
    cruz_free(cir.cruz, cir.arm, M, world)


def cruz_lerp_free(M_a, M_b, t):
    """Mezcla entre dos matrices de mundo (loc/rot/escala)."""
    la, qa, sa = M_a.decompose()
    lb, qb, sb = M_b.decompose()
    M = Matrix.LocRotScale(la.lerp(lb, t), qa.slerp(qb, t), sa.lerp(sb, t))
    cruz_free(cir.cruz, cir.arm, M, world)


def hand_pts(h):
    return head_world(hero, 'LeftHand'), head_world(hero, 'RightHand')


# ----------------------------------------------------------------------------------------------- trozos (astillas, polvo, sangre apagados)
MAT = {
    'wood': flat_mat('astilla', (0.43, 0.30, 0.20, 1)),        # ASH/EMBER apagado
    'wood2': flat_mat('astilla2', (0.30, 0.22, 0.16, 1)),
    'dust': flat_mat('polvo', (0.66, 0.60, 0.52, 1)),          # FX_SH_SMOKE_L
    'dust2': flat_mat('polvo2', (0.48, 0.44, 0.39, 1)),
    'blood': flat_mat('sangre', (0.29, 0.10, 0.10, 1)),        # FX_SH_DEEP
    'ember': flat_mat('ascua', (0.64, 0.29, 0.16, 1)),         # FX_SH_EMBER
}
MAT_SHADOW = flat_mat('sombra', (0, 0, 0, 1))
rng = random.Random(11)
PARTS = []      # (obj, kind) pool


def make_pool(n, kind, size, mats):
    for i in range(n):
        o = new_cube('%s%d' % (kind, i), size, MAT[mats[i % len(mats)]])
        o.parent = world
        PARTS.append(dict(o=o, kind=kind, used=False))


make_pool(18, 'astilla', 0.03, ['wood', 'wood2'])
make_pool(10, 'polvo', 0.05, ['dust', 'dust2'])
make_pool(8, 'sangre', 0.025, ['blood'])
make_pool(6, 'ascua', 0.022, ['ember'])


def parts_reset():
    for p in PARTS:
        p['o'].hide_render = True
        p['used'] = False


def burst(origin, t, kind, n, speed, up=0.9, seed=0, spread=1.0, grav=2.6, dirv=None, stretch=None, size_k=1.0):
    """Estalla n trozos de `kind` desde `origin`, t segundos despues. Posiciones balisticas deterministas."""
    r = random.Random(seed)
    pool = [p for p in PARTS if p['kind'] == kind and not p['used']]
    for p in pool[:n]:
        p['used'] = True
        ang = r.uniform(0, 2 * math.pi)
        sp = speed * r.uniform(0.5, 1.0) * spread
        v = V((math.cos(ang) * sp, math.sin(ang) * sp, up * r.uniform(0.5, 1.2)))
        if dirv is not None:
            v = v + dirv * r.uniform(0.4, 1.0)
        o = p['o']
        pos = Vector(origin) + V((r.uniform(-.02, .02), r.uniform(-.02, .02), r.uniform(0, .02))) + v * t + V((0, 0, -0.5 * grav * t * t))
        if pos.z < 0.012:
            pos.z = 0.012
        o.location = pos
        o.rotation_euler = (r.uniform(0, 6) * t * 3, r.uniform(0, 6) * t * 3, r.uniform(0, 6) * t * 3)
        k = size_k * (1.0 if kind != 'polvo' else (0.7 + 1.6 * t))
        sc = (k, k * (0.3 if kind == 'astilla' else 1), k * (3.0 if kind == 'astilla' else 1))
        o.scale = sc
        o.hide_render = False


# ----------------------------------------------------------------------------------------------- render de un fotograma (color + sombra)
def render_pass(i, outdir):
    # 1) color
    world.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.scene.display.shading.color_type = 'TEXTURE'
    update()
    render_frame(os.path.join(outdir, 'f%02d.png' % i))
    # 2) sombra: todo plano contra el suelo y cizallado hacia +X, en negro
    sc = bpy.context.scene
    world.matrix_parent_inverse = SHEAR
    sc.display.shading.color_type = 'SINGLE'
    sc.display.shading.single_color = (0, 0, 0)
    update()
    render_frame(os.path.join(outdir, 's%02d.png' % i))
    world.matrix_parent_inverse = Matrix.Identity(4)
    sc.display.shading.color_type = 'TEXTURE'
    update()


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ds_remate_cireneo_seq.py'), encoding='utf-8').read())
