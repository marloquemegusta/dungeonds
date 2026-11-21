"""PROTOTIPO: remate del Corazon Abierto sobre el Ojo del Tribunal (le arranca el farol y lo patea).

Estilo visual: el de las ejecuciones del Exvoto (misma celda, misma camara diagonal, mismos pases y misma post).
Celda de 96x96 px a 38 px/m; pies del heroe en el pixel (48,42) como el remate del Exvoto (dir 0, `remate_sprites.c`).

Secuencia (16 fotogramas a 60 ms, ~15 fps):
  0-1  el heroe entra y el Ojo, que se tambalea, se inclina hacia el.
  2    AGARRE: las dos manos del heroe cierran sobre la jaula del farol.
  3    TIRON: el heroe se echa atras y arranca el farol de los hombros.
  4    el farol se desprende; el cuerpo del Ojo se desploma.
  5-7  el heroe lo voltea y lo lanza al suelo (arco balistico).
  8-12 el farol cae y espera en el suelo.
  13-19 PATADA: el heroe sigue la animacion del inbox (`assets/inbox/Zombie Kicking.fbx`, tramo del hachazo
        descendente); el pie aplasta el farol y lo manda volando.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/ds_remate_ojo.py -- <raiz> <salida> <test|all> [fotograma]
  Luego: python tools/characters/ds_remate_ojo_post.py <salida>/ds_ojo/raw <salida> 96
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_remate_exvoto_lib as L
from ds_remate_exvoto_lib import *
import ds_remate_exvoto_lib as _lib

_lib.CELL = (96, 96)
PPM = float(os.environ.get('PPM_OVR', '46'))
_lib.PPM = PPM
CELL = (96, 96)
ANCHOR_Y = float(os.environ.get('ANCHOR_Y', '60'))
CX = float(os.environ.get('CX', '0.30'))

A_ = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT, MODE = A_[0], A_[1], A_[2]
TEST_F = A_[3] if len(A_) > 3 else '2'
RAW = os.path.join(OUT, 'ds_ojo', 'raw')
os.makedirs(RAW, exist_ok=True)

HEROFBX = ROOT + '/assets/models/characters/corazon/source/corazon.fbx'
OJOFBX = ROOT + '/assets/models/characters/ojo/ojo_walk.fbx'
KICKFBX = os.environ.get('KICK_FBX', 'C:/codexlocal/dungeonds/assets/inbox/Zombie Kicking.fbx')

DT = 0.06                 # s por fotograma (15 fps como los GIFs de aprobacion)
G_ = 9.0                  # gravedad en unidades de Blender por s^2
OJO_K = float(os.environ.get('OJO_K', '1.32'))
OJO_X, OJO_Y = float(os.environ.get('OJO_X', '0.62')), float(os.environ.get('OJO_Y', '0.10'))
HX0 = float(os.environ.get('HXF', '0.0'))     # posicion base del heroe (pies) en X
HERO_ONLY = os.environ.get('HERO_ONLY') == '1'
CENTER = V((CX, 0.0, (ANCHOR_Y - 48.0) / (PPM * math.cos(math.radians(30.0)))))

bpy.ops.wm.read_factory_settings(use_empty=True)
CAM = setup_render()

L.ACT['hero_walk'] = L.load_action(ROOT + '/assets/models/animations/corazon/walk.fbx', 'hero_walk')
L.ACT['ojo_walk'] = L.load_action(ROOT + '/assets/models/characters/ojo/ojo_walk.fbx', 'ojo_walk')


def load_kick(path):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in pre]
    arm = [o for o in new if o.type == 'ARMATURE'][0]
    act = arm.animation_data.action if arm.animation_data else [a for a in bpy.data.actions][0]
    act.use_fake_user = True
    act.name = 'kick'
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    for o in new:
        if o.type == 'MESH':
            o.hide_render = True
    print('KICK action', act.name, 'range', tuple(act.frame_range))
    return arm, act


KICK_ARM, KICK_ACT = load_kick(KICKFBX)
KICK_REF = int(round(KICK_ACT.frame_range[0]))
KICK_END = int(round(KICK_ACT.frame_range[1]))


def kick_sample(f):
    bpy.context.scene.frame_set(f)
    update()
    return {pb.name: pb.matrix.copy() for pb in KICK_ARM.pose.bones}


def kick_world(f, bone):
    bpy.context.scene.frame_set(f)
    update()
    return KICK_ARM.matrix_world @ KICK_ARM.pose.bones[P + bone].head


# /m de la patada -> /m del heroe (la cadera del FBX esta a 1.043 m; la del heroe a 0.455 m)
K_SCALE = 0.455 / 1.043
RZ = Matrix.Rotation(math.radians(90.0), 3, 'Z')     # el FBX mira a -Y; el heroe, a +X
K_REF_HIPS = kick_world(KICK_REF, 'Hips')
K_MS3 = KICK_ARM.matrix_world.to_3x3().normalized()
KICK_CHAIN = [b.name[len(P):] for b in KICK_ARM.data.bones
              if b.name[len(P):] in ('Hips', 'Spine', 'Spine1', 'Spine2')
              or b.name[len(P):].endswith(('UpLeg', 'Leg', 'Foot', 'ToeBase', 'Toe_End'))]
_bones = {b.name[len(P):]: b for b in KICK_ARM.data.bones}
KICK_CHAIN.sort(key=lambda n: len(_bones[n].parent_recursive))


def kick_hips_offset(f):
    """Desplazamiento de cadera de la patada, escalado y girado al frente del heroe."""
    d = kick_world(f, 'Hips') - K_REF_HIPS
    return RZ @ (d * K_SCALE)


def apply_kick(f):
    """Copia la rotacion de la patada sobre la cadena del heroe (sin traslacion: el largo del hueso ya escala)."""
    src = kick_sample(f)
    MT3 = hero.arm.matrix_world.to_3x3().normalized()
    for n in KICK_CHAIN:
        sp = src[P + n]
        sb = KICK_ARM.data.bones[P + n]
        tb = hero.arm.data.bones[P + n]
        rest3 = tb.matrix_local.to_3x3().normalized()
        R_delta = sp.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
        R_world = RZ @ K_MS3 @ R_delta @ K_MS3.inverted()     # el FBX mira a -Y; se gira al frente del heroe (+X)
        R_des = (MT3.inverted() @ R_world @ MT3) @ rest3
        pb = hero.arm.pose.bones[P + n]
        head = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()


# ----------------------------------------------------------------------------------------------- heroe
MAT_EMBER = flat_mat('brasa', (0.86, 0.52, 0.24, 1.0))      # FX_SH_GOLD / AMBER apagados
MAT_EMBER2 = flat_mat('brasa2', (0.72, 0.33, 0.16, 1.0))
MAT_GLASS = flat_mat('vidrio', (0.58, 0.68, 0.55, 1.0))     # vidrio verdoso apagado del farol

hero = make_char(HEROFBX, 90, 1.0, (HX0, 0, 0))
ojo = make_char(OJOFBX, -90, OJO_K, (OJO_X, OJO_Y, 0))
update()

hero_ik = {}
for side in ('Left', 'Right'):
    hero_ik[side] = add_ik(hero, side + 'ForeArm', 'hG' + side)
    hero_ik['leg' + side] = add_ik(hero, side + 'Leg', 'hF' + side)

REACH = (tail_world(hero, 'LeftArm') - head_world(hero, 'LeftArm')).length \
    + (tail_world(hero, 'LeftForeArm') - head_world(hero, 'LeftForeArm')).length
print('REACH', round(REACH, 3))

CACHE = {}


def base(ch, key):
    k = (id(ch), key)
    if k not in CACHE:
        CACHE[k] = capture(ch, key[0], key[1])
    return CACHE[k]


def hero_pose(hp, kick_f=None):
    """hp: hx, hy, hbase=(clip,fotograma), lean (Y), spine, head, dz, pin."""
    hero.root.location.x = hp['hx']
    hero.root.location.y = hp.get('hy', 0.0)
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
    if kick_f is not None:
        for side in ('legLeft', 'legRight'):
            hero_ik[side][1].influence = 0.0
        apply_kick(kick_f)


def grip(targets):
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


# ----------------------------------------------------------------------------------------------- Ojo
def ojo_pose(ch, lean=0.0, sway=0.0, dz=0.0, twist=0.0, thigh=0.0, shin=0.0, spread=0.0):
    """Ojo arrodillado/desplomado: muslos al frente (thigh, sobre Y), espinillas replegadas (shin) y tronco caido."""
    apply_basis(ch, base(ch, ('ojo_walk', 1)))
    for side in ('Left', 'Right'):
        sg = 1.0 if side == 'Left' else -1.0
        rot_bone(ch, side + 'UpLeg', 0, thigh, sg * spread)
        rot_bone(ch, side + 'Leg', 0, shin)
        rot_bone(ch, side + 'Foot', 0, -shin * 0.35)
    rot_bone(ch, 'Spine1', 0, -lean * 0.5, twist * 0.5)
    rot_bone(ch, 'Spine2', 0, -lean * 0.5, twist * 0.5)
    rot_bone(ch, 'Head', 0, -lean * 0.35)
    Mh = bone_world(ch, 'Hips')
    set_bone_world(ch, 'Hips', xform_about(Mh.translation.copy(), 0, sway, 0, (0, 0, dz)) @ Mh)
    update()


# ----------------------------------------------------------------------------------------------- farol
OJO_LEAN = float(os.environ.get('OJO_LEAN', '24'))
OJO_THIGH = float(os.environ.get('OJO_THIGH', '64'))
OJO_SHIN = float(os.environ.get('OJO_SHIN', '-102'))
OJO_DZ = float(os.environ.get('OJO_DZ', '-0.20'))
ojo_pose(ojo, lean=OJO_LEAN, dz=OJO_DZ, thigh=OJO_THIGH, shin=OJO_SHIN, spread=5.0)
update()
# apoyar en el suelo: se baja el Ojo hasta que su punto mas bajo toque z=0
_dg0 = bpy.context.evaluated_depsgraph_get()
_mnz = min(min(v.z for v in eval_world_mesh(o, _dg0)[0])
           for o in bpy.data.objects if o.type == 'MESH' and o.parent and o.parent.name == ojo.arm.name)
ojo.root.location.z -= _mnz
update()
print('OJO suelo dz', round(-_mnz, 3))
NECK_P = head_world(ojo, 'Neck')
HEAD_P = head_world(ojo, 'Head')
NECK_DIR = (HEAD_P - NECK_P).normalized()
CUT_P = NECK_P + NECK_DIR * 0.012
print('NECK', tuple(round(x, 3) for x in NECK_P), 'dir', tuple(round(x, 3) for x in NECK_DIR))

OJO_MESHES = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent and o.parent.name == ojo.arm.name]
BODY_BAKED, HAND_HEAD = None, None
for o in OJO_MESHES:
    b = bake(o, 'ojo_static_' + o.name)
    dg = bpy.context.evaluated_depsgraph_get()
    vs, _ = eval_world_mesh(b, dg)
    zr = max(v.z for v in vs) - min(v.z for v in vs)
    if zr > 0.5:
        BODY_BAKED = b
    else:
        HAND_HEAD = b
    o.hide_render = True
    o.hide_viewport = True
update()

LANTERN, STUMP = cut_object(BODY_BAKED, CUT_P, NECK_DIR, jag_amp=0.024, cap_color=(0.20, 0.07, 0.06, 1.0))
BODY_BAKED.hide_render = True
HAND_HEAD.hide_render = True
LANTERN.hide_render = True
STUMP.hide_render = True
update()
_vs_dg = bpy.context.evaluated_depsgraph_get()
lvs, _ = eval_world_mesh(LANTERN, _vs_dg)
LANTERN_C = sum(lvs, V((0, 0, 0))) / len(lvs)
print('LANTERN z', round(min(v.z for v in lvs), 3), round(max(v.z for v in lvs), 3),
      'cent', tuple(round(x, 3) for x in LANTERN_C))
GRAB_L = LANTERN_C + V((-0.105, 0.065, -0.020))
GRAB_R = LANTERN_C + V((-0.105, -0.065, -0.020))
BODY_PIVOT = head_world(ojo, 'Hips')      # el cuerpo se vuelca sobre su propia cadera (no sobre los pies)
MAT_BLACK = flat_mat('negro', (0.02, 0.02, 0.025, 1.0))
REST_ROT = Matrix.Rotation(math.radians(120.0), 4, 'Y')
_rest_pts = [REST_ROT @ (V(v) - LANTERN_C) for v in lvs]
REST_DZ = -min(p.z for p in _rest_pts)


def body_xform(tilt_back=0.0, tilt_side=0.0, drag=(0, 0, 0)):
    return xform_about(BODY_PIVOT, tilt_side, tilt_back, 0, drag)


def place_body(M):
    STUMP.matrix_world = M
    HAND_HEAD.matrix_world = M
    update()


# ----------------------------------------------------------------------------------------------- chispas
_SPARK_N = [0]


class Spark:
    def __init__(self, rng, origin, vel, size, mat=None):
        _SPARK_N[0] += 1
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=(0, 0, -6))
        o = bpy.context.active_object
        o.name = 'chispa%d' % _SPARK_N[0]
        if mat is not None:
            o.data.materials.append(mat)
        else:
            o.data.materials.append(MAT_EMBER if _SPARK_N[0] % 2 else MAT_EMBER2)
        o.hide_render = True
        for p in o.data.polygons:
            p.use_smooth = False
        self.o = o
        self.o0 = V(origin)
        self.v = V(vel)
        self.size = size
        self.landed = None

    def place(self, t):
        if t < 0:
            self.o.hide_render = True
            return
        self.o.hide_render = False
        p = self.o0 + self.v * t + V((0, 0, -0.5 * G_ * t * t))
        if p.z <= self.size * 0.5 and t > 0.02:
            if self.landed is None:
                self.landed = V((p.x, p.y, 0))
            p = V((self.landed.x, self.landed.y, self.size * 0.3))
            self.o.scale = (1.4, 1.4, 0.4)
        self.o.location = p


def burst(tag, n, origin, speed, size, seed, mat=None):
    rng = random.Random(seed)
    out = []
    for k in range(n):
        d = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 1.0))).normalized()
        out.append(Spark(rng, origin + d * 0.02, d * speed * rng.uniform(0.5, 1.2), size, mat))
    return out


# ----------------------------------------------------------------------------------------------- secuencia
# fotograma de la celda -> fotograma del clip de patada (30 fps). Se avanza ~2 fotogramas de clip por celda
# (0,06 s), asi la patada se juega a velocidad casi natural.
KICK_MAP = {i: 13 + 2 * (i - 7) for i in range(7, 20)}       # arranque y bajada, ~natural
KICK_MAP.update({i: 37 + 2 * (i - 20) for i in range(20, 26)})  # acompanamiento
CONTACT_PREVIEW = 18          # clip 35: el pie entra al cuerpo del Ojo, a la altura de la rodilla/cadera
RIP_F = 4
RELEASE_F = 6
LAND_F = 8
N_FRAMES = 26


def hp_for(i):
    """Pose base del heroe en el fotograma i (sin la patada)."""
    T = {
        0: dict(hx=HX0 - 0.34, hbase=('hero_walk', 9), lean=12, spine=6, head=-4, pin=False),
        1: dict(hx=HX0 - 0.12, hbase=('hero_walk', 13), lean=22, spine=10, head=-6, pin=False),
        2: dict(hx=HX0 + 0.12, lean=16, spine=10, head=-6, dz=-0.04, pin=True),
        3: dict(hx=HX0 + 0.08, lean=-8, spine=-8, head=2, dz=-0.02, pin=True),
        RIP_F: dict(hx=HX0 + 0.04, lean=-10, spine=-8, head=4, dz=-0.01, pin=True),
        5: dict(hx=HX0 + 0.04, lean=12, spine=8, head=-4, dz=-0.03, pin=True),
        RELEASE_F: dict(hx=HX0 + 0.10, lean=26, spine=18, head=-8, dz=-0.06, pin=True),
        7: dict(hx=HX0 + 0.14, lean=16, spine=10, head=-4, dz=-0.03, pin=True),
    }
    hp = dict(T.get(i, dict(hx=HX0 + 0.16, lean=0, spine=0, head=0, pin=True)))
    hp.setdefault('hbase', ('hero_walk', 1))
    return hp


place_cam(CAM, CENTER, 45.0, 30.0, 1.0)

# pre-pase: punto del impacto (pie extendido en el fotograma de contacto) para las chispas y el farol
_off0 = kick_hips_offset(KICK_MAP[CONTACT_PREVIEW])
hero_pose(dict(hx=HX0 + 0.16 + _off0.x, hy=_off0.y, dz=_off0.z, hbase=('hero_walk', 1), pin=True),
          kick_f=KICK_MAP[CONTACT_PREVIEW])
FOOT_HIT = hero.arm.matrix_world @ hero.arm.pose.bones[P + 'RightFoot'].head
IMPACT = V((FOOT_HIT.x, FOOT_HIT.y, 0.0))
print('IMPACT', tuple(round(x, 3) for x in IMPACT))
# el farol se tira delante del heroe; la patada entra al cuerpo en el 17 y, al bajar, roza el farol en el 21
LAND = V((0.44, -0.06, 0.0))
LANTERN_KICK_F = 19
print('LAND', tuple(round(x, 3) for x in LAND))

rip_sparks = burst('rip', 12, NECK_P + V((0, 0, 0.03)), 1.25, 0.011, 21)
rip_glass = burst('ripg', 8, NECK_P + V((0, 0, 0.05)), 1.6, 0.008, 22, MAT_GLASS)
land_sparks = burst('land', 8, LAND + V((0, 0, 0.05)), 0.9, 0.008, 33)
kick_sparks = burst('kick', 14, IMPACT + V((0, 0, 0.12)), 1.7, 0.009, 45)
kick_glass = burst('kickg', 6, IMPACT + V((0, 0, 0.14)), 2.0, 0.007, 46, MAT_GLASS)

# vuelo del farol: de la mano (fotograma RELEASE_F) al suelo (LAND_F) al punto de contacto
C0 = LANTERN_C.copy()
T_FLY = (LAND_F - RELEASE_F) * DT
V_KICK = V((1.4, -1.6, 0.7))     # la patada lo manda a ras de suelo, hacia el espectador


# farol en la mano: (centro de mundo, giro sobre Y en grados)
HELD = {
    0: (C0, 0.0), 1: (C0, 0.0), 2: (C0, 0.0),
    3: (C0 + V((-0.030, -0.010, 0.020)), 4.0),
    4: (C0 + V((-0.135, -0.020, 0.085)), -26.0),      # arrancado: se levanta y se echa atras
    5: (C0 + V((-0.160, 0.000, -0.020)), 14.0),
}
REL_C = C0 + V((-0.190, 0.010, -0.190))
V_FLY = (LAND - REL_C - V((0, 0, -0.5 * G_ * T_FLY * T_FLY))) / T_FLY


def held_matrix(c, deg):
    return Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, 'Y') @ Matrix.Translation(-C0)


def lantern_matrix(i):
    """Transformacion de mundo del farol (identidad = colgado en los hombros del Ojo)."""
    if i < RIP_F:
        if i < 2:
            return Matrix.Identity(4)
        if i == 2:
            return Matrix.Translation((0, 0, 0.004))
        c, d = HELD[3]
        return held_matrix(c, d)
    if i < RELEASE_F:
        c, d = HELD[i]
        return held_matrix(c, d)
    if i < LAND_F:
        t = (i - RELEASE_F) * DT
        c = REL_C + V_FLY * t + V((0, 0, -0.5 * G_ * t * t))
        rot = Matrix.Rotation(math.radians(90.0 - 380.0 * t), 4, 'Y')
        return Matrix.Translation(c) @ rot @ Matrix.Translation(-C0)
    if i < LANTERN_KICK_F:
        # reposa en el suelo
        c = V((LAND.x, LAND.y, REST_DZ))
        return Matrix.Translation(c) @ REST_ROT @ Matrix.Translation(-C0)
    # rozado por el pie al bajar: sale a ras y rueda
    t = (i - LANTERN_KICK_F) * DT
    c = V((LAND.x, LAND.y, REST_DZ)) + V_KICK * t + V((0, 0, -0.5 * G_ * t * t))
    if c.z < REST_DZ:
        c = V((c.x, c.y, REST_DZ))
    rot = REST_ROT @ Matrix.Rotation(math.radians(620.0 * t), 4, 'Y')
    return Matrix.Translation(c) @ rot @ Matrix.Translation(-C0)


BODY_FEET = V((OJO_X, OJO_Y, 0.0))


def body_sway(i):
    """Cuerpo sin farol: se tambalea sobre sus pies, cada vez mas, sin caerse."""
    s = 4.2 * math.sin(2 * math.pi * (i - (RIP_F + 1)) / 5.6)
    f = 2.0 + 1.6 * math.sin(2 * math.pi * (i - (RIP_F + 1)) / 9.0)
    return xform_about(BODY_FEET, s, f, 0)


# el desplome empieza EN el impacto y acelera: el 18 es el golpe, del 19 al 25 cae
FALL_DEG = {18: 0.0, 19: 11.0, 20: 36.0, 21: 62.0, 22: 77.0, 23: 83.0, 24: 85.0, 25: 86.0}


def body_matrix(i):
    """Aguanta de pie (tambaleandose) hasta que llega la patada; entonces se desploma."""
    if i < RIP_F:
        return body_xform(tilt_back=0.0, tilt_side=1.5 if i % 2 else -1.5)
    if i == RIP_F:
        return xform_about(BODY_FEET, 0.0, -3.0, 0.0)
    if i < CONTACT_PREVIEW:
        return body_sway(i)
    tilt = FALL_DEG.get(i, 83.0)
    k = tilt / 83.0
    fall = xform_about(BODY_PIVOT, -10.0 * k, tilt, 0, (0.24 * k, 0.10 * k, 0.0))
    M = fall @ body_sway(CONTACT_PREVIEW - 1)
    if i == CONTACT_PREVIEW:
        M = Matrix.Translation((0, 0, -0.025)) @ M     # el golpe le hunde las piernas, aun de pie
    STUMP.matrix_world = M
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    vs, _ = eval_world_mesh(STUMP, dg)
    return Matrix.Translation((0, 0, -min(v.z for v in vs))) @ M


def pose_frame(i):
    if i in KICK_MAP:
        hp = hp_for(i)
        off = kick_hips_offset(KICK_MAP[i])
        hp['hx'] += off.x
        hp['hy'] = off.y
        hp['dz'] = hp.get('dz', 0.0) + off.z
        hero_pose(hp, kick_f=KICK_MAP[i])
        return grip(None)
    hero_pose(hp_for(i))
    if 2 <= i < RIP_F:
        # agarre: manos a los lados de la jaula (en el sitio o levantada por el tiron)
        M = lantern_matrix(i)
        return grip({'Left': M @ GRAB_L, 'Right': M @ GRAB_R})
    if RIP_F <= i <= RELEASE_F:
        M = lantern_matrix(i)
        lc = M @ LANTERN_C
        r = M.to_3x3().normalized()
        return grip({'Left': lc + r @ V((0, 0.070, -0.030)), 'Right': lc + r @ V((0, -0.070, -0.030))})
    # suelta: los brazos acompanan
    for side in ('Left', 'Right'):
        hero_ik[side][1].influence = 0.0
    update()
    return {}


def render_passes(d, i, visible):
    sc = bpy.context.scene
    sh = sc.display.shading
    raw = os.path.join(RAW, 'raw_d%d' % d)
    for o in visible:
        o.hide_render = False
    if SHADOW['ob'] is not None:
        SHADOW['ob'].hide_render = True
    sh.light = 'STUDIO'
    render_to(os.path.join(raw, 'f%02d_lit.png' % i))
    sh.light = 'FLAT'
    render_to(os.path.join(raw, 'f%02d_flat.png' % i))
    hid = [(o, o.hide_render) for o in visible]
    for o, _ in hid:
        o.hide_render = True
    if SHADOW['ob'] is not None:
        SHADOW['ob'].hide_render = False
        render_to(os.path.join(raw, 's%02d.png' % i))
        SHADOW['ob'].hide_render = True
    for o, h in hid:
        o.hide_render = h


DIRS = [int(x) for x in os.environ.get('DIRS', '0,1,2,3,4,5,6,7').split(',')]
for _d in DIRS:
    os.makedirs(os.path.join(RAW, 'raw_d%d' % _d), exist_ok=True)

frames = [int(x) for x in str(TEST_F).split(',')] if MODE == 'test' else list(range(N_FRAMES))
for i in frames:
    gaps = pose_frame(i)
    t_rip = (i - RIP_F) * DT
    t_land = (i - LAND_F) * DT
    t_kick = (i - CONTACT_PREVIEW) * DT
    M = lantern_matrix(i)
    LANTERN.matrix_world = M
    LANTERN.hide_render = False
    place_body(body_matrix(i))
    for s in rip_sparks + rip_glass:
        s.place(t_rip)
    for s in land_sparks:
        s.place(t_land)
    for s in kick_sparks + kick_glass:
        s.place(t_kick)
    update()
    vis = [hero.mesh] + ([] if HERO_ONLY else [STUMP, HAND_HEAD, LANTERN]) \
        + [s.o for s in rip_sparks + rip_glass + land_sparks + kick_sparks + kick_glass]
    if i in KICK_MAP:
        _rf = hero.arm.matrix_world @ hero.arm.pose.bones[P + 'RightFoot'].head
        _rt = hero.arm.matrix_world @ hero.arm.pose.bones[P + 'RightToe_End'].head
        _kn = hero.arm.matrix_world @ hero.arm.pose.bones[P + 'RightLeg'].head
        print('  KICK clip', KICK_MAP[i], 'ankle', tuple(round(x, 3) for x in _rf),
              'toe', tuple(round(x, 3) for x in _rt), 'knee', tuple(round(x, 3) for x in _kn))
    for d in DIRS:
        # la pareja se queda quieta y giran la camara y el sol: equivale a rotar el remate bajo una luz fija
        place_cam(CAM, CENTER, 45.0 - d * 45.0, 30.0, 1.0)
        _t = math.radians(-d * 45.0)
        _lib.LIGHT_DIR = V((math.cos(_t), math.sin(_t)))
        build_shadow(vis, mat=MAT_BLACK)
        render_passes(d, i, vis)
    from bpy_extras.object_utils import world_to_camera_view
    _co = world_to_camera_view(bpy.context.scene, CAM, V((0, 0, 0)))
    print('FRAME', i, 'gaps', gaps, 'feet_px', (round(_co.x * 96, 1), round((1 - _co.y) * 96, 1)))
print('OK', frames, 'dirs', DIRS, 'cell', CELL)
