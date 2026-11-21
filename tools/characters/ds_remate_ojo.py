"""PROTOTIPO: remate del Corazon Abierto sobre el Ojo del Tribunal.

Secuencia: el heroe le arranca el farol (que es su cabeza) de los hombros, lo lanza al suelo, el cuerpo
descabezado se levanta tambaleandose y, cuando llega la patada, se desploma hacia atras con la animacion
del inbox (`assets/inbox/Falling Back Death.fbx`) y se queda muerto.

Estilo visual: el de las ejecuciones del Exvoto (misma celda, misma camara diagonal, mismos pases y post).

Fotogramas de celda (60 ms):
   0-1   el heroe entra; el Ojo esta arrodillado
   2     AGARRE: las manos cierran sobre la jaula del farol
   3     TIRON
   4     ARRANQUE: el farol se suelta de la base del cuello (borde dentado + cera)
   4-10  el cuerpo descabezado se levanta, tambaleandose
   5-8   el heroe voltea el farol y lo tira al suelo (arco balistico)
   10-17 el Ojo de pie se tambalea (sway sobre los pies)
   12-18 PATADA: clip del inbox (`Zombie Kicking.fbx`), contacto en el 18
   18-35 DESPLOME: clip `Falling Back Death.fbx` desde el contacto; el cuerpo cae y se queda
   31-37 el heroe vuelve de la patada a su pose de reposo (la recuperacion del clip, recortada)

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
PPM = float(os.environ.get('PPM_OVR', '38'))
_lib.PPM = PPM
CELL = (96, 96)
ANCHOR_Y = float(os.environ.get('ANCHOR_Y', '60'))
CX = float(os.environ.get('CX', '0.68'))
CY = float(os.environ.get('CY', '0.06'))

A_ = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT, MODE = A_[0], A_[1], A_[2]
TEST_F = A_[3] if len(A_) > 3 else '2'
RAW = os.path.join(OUT, 'ds_ojo', 'raw')
os.makedirs(RAW, exist_ok=True)

HEROFBX = ROOT + '/assets/models/characters/corazon/source/corazon.fbx'
OJOFBX = ROOT + '/assets/models/characters/ojo/ojo_walk.fbx'
KICKFBX = os.environ.get('KICK_FBX', 'C:/codexlocal/dungeonds/assets/inbox/Zombie Kicking.fbx')
FALLFBX = os.environ.get('FALL_FBX', 'C:/codexlocal/dungeonds/assets/inbox/Falling Back Death.fbx')

DT = 0.06                 # s por fotograma de celda
G_ = 9.0                  # gravedad en unidades de Blender por s^2
OJO_K = float(os.environ.get('OJO_K', '1.32'))
OJO_X, OJO_Y = float(os.environ.get('OJO_X', '0.72')), float(os.environ.get('OJO_Y', '0.10'))
HX0 = float(os.environ.get('HXF', '0.0'))
HERO_ONLY = os.environ.get('HERO_ONLY') == '1'
CENTER = V((CX, CY, (ANCHOR_Y - 48.0) / (PPM * math.cos(math.radians(30.0)))))

bpy.ops.wm.read_factory_settings(use_empty=True)
CAM = setup_render()

L.ACT['hero_walk'] = L.load_action(ROOT + '/assets/models/animations/corazon/walk.fbx', 'hero_walk')
L.ACT['ojo_walk'] = L.load_action(ROOT + '/assets/models/characters/ojo/ojo_walk.fbx', 'ojo_walk')


# ----------------------------------------------------------------------------------------------- clips del inbox
def load_clip(path, name):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in pre]
    arm = [o for o in new if o.type == 'ARMATURE'][0]
    act = arm.animation_data.action if arm.animation_data else [a for a in bpy.data.actions][0]
    act.use_fake_user = True
    act.name = name
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    for o in new:
        if o.type == 'MESH':
            o.hide_render = True
    print(name, 'range', tuple(act.frame_range))
    return arm, act


KICK_ARM, KICK_ACT = load_clip(KICKFBX, 'kick')
KICK_REF = int(round(KICK_ACT.frame_range[0]))
FALL_ARM, FALL_ACT = load_clip(FALLFBX, 'fall')
FALL_REF = 7              # primer fotograma con reaccion real (antes esta quieto de pie)

P_ = P


def clip_pose(arm, f):
    """Matrices de pose del clip en el espacio de SU armadura (como el remate del Exvoto)."""
    bpy.context.scene.frame_set(f)
    update()
    return {b.name: b.matrix.copy() for b in arm.pose.bones}


def clip_head(arm, f, bone):
    """Cabeza del hueso del clip en mundo."""
    bpy.context.scene.frame_set(f)
    update()
    return arm.matrix_world @ arm.pose.bones[P + bone].head


# /m del clip -> /m del heroe (la cadera del clip esta a 1.043 m; la del heroe a 0.455 m)
K_SCALE = 0.455 / 1.043
K_RZ = Matrix.Rotation(math.radians(90.0), 3, 'Z')     # el FBX mira a -Y; el heroe, a +X
K_MS3 = KICK_ARM.matrix_world.to_3x3().normalized()
K_REF_HIPS = KICK_ARM.matrix_world @ clip_pose(KICK_ARM, KICK_REF)[P_ + 'Hips'].translation.copy()

KICK_CHAIN = [b.name[len(P_):] for b in KICK_ARM.data.bones
              if b.name[len(P_):] in ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head')
              or b.name[len(P_):].endswith(('Shoulder', 'UpLeg', 'Leg', 'Foot', 'ToeBase', 'Toe_End'))
              or b.name[len(P_):].endswith(('Arm', 'ForeArm', 'Hand'))]
_kb = {b.name[len(P_):]: b for b in KICK_ARM.data.bones}
KICK_CHAIN.sort(key=lambda n: len(_kb[n].parent_recursive))


def kick_hips_offset(f):
    """Desplazamiento de cadera de la patada, escalado y girado al frente del heroe."""
    d = clip_head(KICK_ARM, f, 'Hips') - K_REF_HIPS
    return K_RZ @ (d * K_SCALE)


def apply_kick(f):
    """Copia la rotacion de la patada sobre la cadena del heroe (sin traslacion: el largo del hueso escala)."""
    src = clip_pose(KICK_ARM, f)
    MT3 = hero.arm.matrix_world.to_3x3().normalized()
    for n in KICK_CHAIN:
        sp = src[P_ + n]
        sb = KICK_ARM.data.bones[P_ + n]
        tb = hero.arm.data.bones[P_ + n]
        rest3 = tb.matrix_local.to_3x3().normalized()
        R_delta = sp.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
        R_world = K_RZ @ K_MS3 @ R_delta @ K_MS3.inverted()     # el FBX mira a -Y; se gira al frente del heroe (+X)
        R_des = (MT3.inverted() @ R_world @ MT3) @ rest3
        pb = hero.arm.pose.bones[P_ + n]
        head = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()


# desplome: se aplica el movimiento del clip (delta respecto a FALL_REF) sobre la pose de pie del Ojo
FALL_RZ = Matrix.Rotation(math.radians(-100.0), 3, 'Z')  # el FBX mira a -Y; el Ojo mira a -X: cae hacia +X
FALL_K = float(os.environ.get('FALL_K', '0.52'))         # escala del desplazamiento de cadera
FALL_CHAIN = [n for n in (b.name for b in FALL_ARM.data.bones) if n.replace(P_, '') in (
    'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
    'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
    'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
    'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase')]
_fb = {b.name: b for b in FALL_ARM.data.bones}
FALL_CHAIN.sort(key=lambda n: len(_fb[n].parent_recursive))
FALL_WREF = clip_pose(FALL_ARM, FALL_REF)
FALL_MS3 = FALL_ARM.matrix_world.to_3x3().normalized()
FALL_HIPS0 = FALL_ARM.matrix_world @ FALL_WREF[P_ + 'Hips'].translation.copy()


def fall_rot(src, n):
    return FALL_MS3 @ src[n].to_3x3().normalized()


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


def wrot(ch, name):
    return (ch.arm.matrix_world @ ch.arm.pose.bones[P + name].matrix).to_3x3().normalized()


def set_wrot(ch, name, R):
    """Fija la rotacion de mundo del hueso (conservando su cabeza)."""
    MT3 = ch.arm.matrix_world.to_3x3().normalized()
    pb = ch.arm.pose.bones[P + name]
    pb.matrix = Matrix.Translation(pb.matrix.translation) @ (MT3.inverted() @ R).to_4x4()
    update()


def hero_pose(hp, kick_f=None, kick_w=1.0):
    """hp: hx, hy, hbase=(clip,fotograma), lean (Y), spine, head, dz, pin, root_off."""
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
        update()
        R0 = {n: wrot(hero, n) for n in KICK_CHAIN}
        apply_kick(kick_f)
        if kick_w < 1.0:
            for n in KICK_CHAIN:
                q = R0[n].to_quaternion().slerp(wrot(hero, n).to_quaternion(), kick_w)
                set_wrot(hero, n, q.to_matrix())


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


# ----------------------------------------------------------------------------------------------- Ojo: partir la cabeza
OJO_MESHES = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent and o.parent.name == ojo.arm.name]
BODY = [o for o in OJO_MESHES if any(m.type == 'ARMATURE' for m in o.modifiers)][0]
for o in OJO_MESHES:
    if o is not BODY:
        o.hide_render = True       # duplicado sin skin (mismo farol: no se usa)
print('OJO body', BODY.name, len(BODY.data.vertices), 'verts')


def split_by_head(ob, thr=0.5, jag_amp=0.020, cap_color=(0.20, 0.07, 0.06, 1.0)):
    """Parte la malla skinned en (cabeza, cuerpo) por el peso del hueso Head. Las dos mitades comparten
    la arista de corte dentada y cada una tapa su hueco con cera. Ambas siguen skinned."""
    me = ob.data
    gi = ob.vertex_groups[P + 'Head'].index
    wmap = {}
    for v in me.vertices:
        ww = 0.0
        for g in v.groups:
            if g.group == gi:
                ww = g.weight
        wmap[v.index] = ww
    head_faces = set()
    for p in me.polygons:
        vs = p.vertices
        if sum(1 for i in vs if wmap[i] >= thr) * 2 >= len(vs):
            head_faces.add(p.index)
    hv, bv = set(), set()
    for p in me.polygons:
        (hv if p.index in head_faces else bv).update(p.vertices)
    ring = hv & bv
    n_l = V((0.0, 0.0, 1.0))
    t1 = V((1.0, 0.0, 0.0))
    t2 = V((0.0, 1.0, 0.0))
    disp = {}
    for i in ring:
        c = me.vertices[i].co
        j = math.sin(c.dot(t1) * 55.0 + 1.3) * 0.6 + math.sin(c.dot(t2) * 41.0) * 0.4
        disp[i] = n_l * (jag_amp * j)
    out = {}
    for side in ('head', 'body'):
        nb = ob.copy()
        nb.data = ob.data.copy()
        nb.name = 'ojo_' + side
        bpy.context.scene.collection.objects.link(nb)
        nb.hide_render = True
        cap_mat = flat_mat('cera_corte_' + side, cap_color)
        nb.data.materials.append(cap_mat)
        slot = len(nb.data.materials) - 1
        bm = bmesh.new()
        bm.from_mesh(nb.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for i, d in disp.items():
            bm.verts[i].co += d
        kill_head = (side == 'body')
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.index in head_faces) == kill_head],
                         context='FACES')
        bm.faces.ensure_lookup_table()
        bcount = {}
        for f in bm.faces:
            for e in f.edges:
                bcount[e] = bcount.get(e, 0) + 1
        bnd = [e for e, c in bcount.items() if c == 1]
        parent = {e: e for e in bnd}

        def find(e):
            while parent[e] is not e:
                parent[e] = parent[parent[e]]
                e = parent[e]
            return e
        v2e = {}
        for e in bnd:
            for v in e.verts:
                v2e.setdefault(v, []).append(e)
        for es in v2e.values():
            for k in range(1, len(es)):
                a_, b_ = find(es[0]), find(es[k])
                if a_ is not b_:
                    parent[a_] = b_
        comps = {}
        for e in bnd:
            comps.setdefault(find(e), set()).update(e.verts)
        from mathutils.geometry import convex_hull_2d
        nan = 0
        for vs in comps.values():
            if len(vs) < 3 or not (set(v.index for v in vs) & ring):
                continue
            pts = list(vs)
            c0 = sum((v.co for v in pts), V((0, 0, 0))) / len(pts)
            hull = convex_hull_2d([V(((v.co - c0).dot(t1), (v.co - c0).dot(t2))) for v in pts])
            if len(hull) < 3:
                continue
            nf = []
            for k in range(1, len(hull) - 1):
                try:
                    f = bm.faces.new((pts[hull[0]], pts[hull[k]], pts[hull[k + 1]]))
                except ValueError:
                    continue
                f.material_index = slot
                nf.append(f)
            bm.normal_update()
            sign = 1.0 if side == 'body' else -1.0
            for f in nf:
                if f.normal.dot(n_l) * sign < 0:
                    f.normal_flip()
            nan += len(nf)
        bm.normal_update()
        bm.to_mesh(nb.data)
        bm.free()
        print('SPLIT', side, 'faces', len(nb.data.polygons), 'ring', len(ring), 'cap', nan)
        out[side] = nb
    ob.hide_render = True
    ob.hide_viewport = True
    return out['head'], out['body']


HEAD_SKIN, BODY_SKIN = split_by_head(BODY)


def ojo_pose(ch, k, sway=0.0, dz_extra=0.0, twist=0.0):
    """k=1: arrodillado (para que el heroe alcance el farol); k=0: de pie."""
    apply_basis(ch, base(ch, ('ojo_walk', 1)))
    thigh, shin, spread, lean = 64.0 * k, -102.0 * k, 5.0 * k, 24.0 * k
    for side in ('Left', 'Right'):
        sg = 1.0 if side == 'Left' else -1.0
        rot_bone(ch, side + 'UpLeg', 0, thigh, sg * spread)
        rot_bone(ch, side + 'Leg', 0, shin)
        rot_bone(ch, side + 'Foot', 0, -shin * 0.35)
    rot_bone(ch, 'Spine1', 0, -lean * 0.5, twist * 0.5)
    rot_bone(ch, 'Spine2', 0, -lean * 0.5, twist * 0.5)
    rot_bone(ch, 'Head', 0, -lean * 0.35)
    Mh = bone_world(ch, 'Hips')
    set_bone_world(ch, 'Hips', xform_about(Mh.translation.copy(), 0, sway, 0,
                                           (0, 0, -0.20 * k + dz_extra)) @ Mh)
    update()


def ground(ch, clamp=False):
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    vs, _ = eval_world_mesh(BODY_SKIN, dg)
    mn = min(v.z for v in vs)
    if clamp and mn >= 0.0:
        return
    ch.root.location.z -= mn
    update()


# pose de agarre (arrodillado) para tallar el farol y el hombro
ojo_pose(ojo, 1.0)
ground(ojo)
NECK_P = head_world(ojo, 'Neck')
HEAD_P = head_world(ojo, 'Head')
NECK_DIR = (HEAD_P - NECK_P).normalized()
print('NECK', tuple(round(x, 3) for x in NECK_P))
HEAD_BAKED = bake(HEAD_SKIN, 'ojo_farol')
HEAD_SKIN.hide_render = True
_vs = bpy.context.evaluated_depsgraph_get()
lvs, _ = eval_world_mesh(HEAD_BAKED, _vs)
LANTERN_C = sum(lvs, V((0, 0, 0))) / len(lvs)
print('FAROL bbox', tuple(round(min(v[i] for v in lvs), 3) for i in range(3)),
      tuple(round(max(v[i] for v in lvs), 3) for i in range(3)))
GRAB_L = LANTERN_C + V((-0.100, 0.070, -0.020))
GRAB_R = LANTERN_C + V((-0.100, -0.070, -0.020))
MAT_BLACK = flat_mat('negro', (0.02, 0.02, 0.025, 1.0))
REST_ROT = Matrix.Rotation(math.radians(120.0), 4, 'Y')
_rest_pts = [REST_ROT @ (V(v) - LANTERN_C) for v in lvs]
REST_DZ = -min(p.z for p in _rest_pts)
HEAD_BAKED.hide_render = True


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
        c = V((LAND.x, LAND.y, REST_DZ))
        return Matrix.Translation(c) @ REST_ROT @ Matrix.Translation(-C0)
    # rozado por el pie al bajar: sale un palmo, rueda y se para
    t = (i - LANTERN_KICK_F) * DT
    tau = 0.22
    d = V_KICK * tau * (1.0 - math.exp(-t / tau))
    hop = 0.15 * math.exp(-t / 0.24) * math.sin(math.pi * min(1.0, t / 0.36))
    c = V((LAND.x + d.x, LAND.y + d.y, REST_DZ + max(0.0, hop)))
    rot = REST_ROT @ Matrix.Rotation(math.radians(240.0 * tau * (1.0 - math.exp(-t / tau))), 4, 'Y')
    return Matrix.Translation(c) @ rot @ Matrix.Translation(-C0)


def held_matrix(c, deg):
    return Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, 'Y') @ Matrix.Translation(-C0)


# ----------------------------------------------------------------------------------------------- chispas
_SPARK_N = [0]


class Spark:
    def __init__(self, rng, origin, vel, size, mat=None):
        _SPARK_N[0] += 1
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=(0, 0, -6))
        o = bpy.context.active_object
        o.name = 'chispa%d' % _SPARK_N[0]
        o.data.materials.append(mat if mat is not None else (MAT_EMBER if _SPARK_N[0] % 2 else MAT_EMBER2))
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


def burst(n, origin, speed, size, seed, mat=None):
    rng = random.Random(seed)
    out = []
    for k in range(n):
        d = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 1.0))).normalized()
        out.append(Spark(rng, origin + d * 0.02, d * speed * rng.uniform(0.5, 1.2), size, mat))
    return out


# ----------------------------------------------------------------------------------------------- guion
RIP_F = 4
RELEASE_F = 6
LAND_F = 8
RISE = (4, 11)                 # el cuerpo descabezado se levanta
CONTACT_F = 17                 # la patada entra (clip 23: el pie toca); el desplome arranca en este mismo fotograma
N_FRAMES = 38
KICK_C0, KICK_C1 = 12, 30      # celdas con clip de patada (contacto en el 18)
BLEND_C = 31                   # desde aqui la patada vuelve a la pose de reposo
BLEND_N = 7
FALL_C0 = CONTACT_F
FALL_CLIP = {i: FALL_REF + 2 * (i - FALL_C0) for i in range(FALL_C0, N_FRAMES)}
LANTERN_KICK_F = 19
LAND = V((0.46, -0.12, 0.0))
C0 = LANTERN_C.copy()
HELD = {
    0: (C0, 0.0), 1: (C0, 0.0), 2: (C0, 0.0),
    3: (C0 + V((-0.030, -0.010, 0.020)), 4.0),
    4: (C0 + V((-0.135, -0.020, 0.085)), -26.0),
    5: (C0 + V((-0.160, 0.000, -0.020)), 14.0),
}
REL_C = C0 + V((-0.190, 0.010, -0.190))
T_FLY = (LAND_F - RELEASE_F) * DT
V_FLY = (LAND - REL_C - V((0, 0, -0.5 * G_ * T_FLY * T_FLY))) / T_FLY
V_KICK = V((1.4, -1.6, 0.7))
OJO_FEET = V((OJO_X, OJO_Y, 0.0))


def ojo_k(i):
    """1 = arrodillado, 0 = de pie; con la subida repartida en RISE y un pequeno rebote."""
    if i < RISE[0]:
        return 1.0
    if i >= RISE[1]:
        return 0.0
    t = (i - RISE[0]) / float(RISE[1] - RISE[0])
    e = t * t * (3 - 2 * t)
    return 1.0 - (e + 0.10 * math.sin(math.pi * t) * (1 - t))


def ojo_wobble(i):
    """Balanceo sobre los pies ya de pie (sin farol)."""
    if i < RISE[1]:
        return 0.0
    s = 4.4 * math.sin(2 * math.pi * (i - RISE[1]) / 5.2)
    f = 1.8 + 1.4 * math.sin(2 * math.pi * (i - RISE[1]) / 8.5)
    return s, f


def ojo_standing(i):
    """Pose del Ojo en la celda i (sin la patada): arrodillado, subiendo, de pie o cayendo."""
    k = ojo_k(i)
    sw = ojo_wobble(i)
    ojo_pose(ojo, k, sway=sw[0] if sw else 0.0, twist=sw[1] if sw else 0.0)
    ground(ojo)
    if i in FALL_CLIP:
        apply_fall(ojo, FALL_CLIP[i])
        ground(ojo, clamp=True)


def apply_fall(ch, f):
    src = clip_pose(FALL_ARM, f)
    MT3 = ch.arm.matrix_world.to_3x3().normalized()
    W3i = ch.arm.matrix_world.to_3x3().inverted()
    for n in FALL_CHAIN:
        pb = ch.arm.pose.bones[n]
        par = _fb[n].parent
        pn = par.name if par is not None else None
        Rn = fall_rot(src, n)
        if pn in src:
            Dc = Rn @ fall_rot(src, pn).inverted()
        else:
            Dc = Rn @ (FALL_MS3 @ FALL_WREF[n].to_3x3().normalized()).inverted()
        D = FALL_RZ @ Dc @ FALL_RZ.inverted()
        head = pb.matrix.translation.copy()
        if n == P_ + 'Hips':
            hw = FALL_ARM.matrix_world @ src[n].translation
            head = head + W3i @ (FALL_RZ @ ((hw - FALL_HIPS0) * FALL_K))
        pb.matrix = Matrix.Translation(head) @ ((MT3.inverted() @ D @ MT3) @ pb.matrix.to_3x3()).to_4x4()
        update()


def hero_stand(i):
    return dict(hx=HX0 + 0.16, lean=0, spine=0, head=0, pin=True)


def hp_for(i):
    """Pose base del heroe en el fotograma i (sin la patada)."""
    T = {
        0: dict(hx=HX0 - 0.24, hbase=('hero_walk', 9), lean=12, spine=6, head=-4, pin=False),
        1: dict(hx=HX0 - 0.10, hbase=('hero_walk', 13), lean=22, spine=10, head=-6, pin=False),
        2: dict(hx=HX0 + 0.22, lean=16, spine=10, head=-6, dz=-0.04, pin=True),
        3: dict(hx=HX0 + 0.18, lean=-8, spine=-8, head=2, dz=-0.02, pin=True),
        RIP_F: dict(hx=HX0 + 0.14, lean=-10, spine=-8, head=4, dz=-0.01, pin=True),
        5: dict(hx=HX0 + 0.14, lean=12, spine=8, head=-4, dz=-0.03, pin=True),
        RELEASE_F: dict(hx=HX0 + 0.20, lean=26, spine=18, head=-8, dz=-0.06, pin=True),
        7: dict(hx=HX0 + 0.18, lean=16, spine=10, head=-4, dz=-0.03, pin=True),
    }
    hp = dict(T.get(i, hero_stand(i)))
    hp.setdefault('hbase', ('hero_walk', 1))
    return hp


def kick_clip(i):
    """Fotograma del clip de patada para la celda i, o None si el heroe ya no la esta haciendo."""
    if KICK_C0 <= i <= 18:
        return 13 + 2 * (i - KICK_C0)
    if 18 < i <= KICK_C1:
        return 27 + 2 * (i - 19)
    if KICK_C1 < i < BLEND_C + BLEND_N:
        return 49                      # pose final del clip, que se mezcla con el reposo
    return None


place_cam(CAM, CENTER, 45.0, 30.0, 1.0)

# pre-pase: punto del impacto (pie extendido en el fotograma de contacto)
_o = kick_hips_offset(kick_clip(CONTACT_F))
hero_pose(dict(hx=HX0 + 0.16 + _o.x, hy=_o.y, dz=_o.z, hbase=('hero_walk', 1), pin=True),
          kick_f=kick_clip(CONTACT_F))
FOOT_HIT = hero.arm.matrix_world @ hero.arm.pose.bones[P + 'RightFoot'].head
FOOT_TOE = hero.arm.matrix_world @ hero.arm.pose.bones[P + 'RightToe_End'].head
IMPACT = V((FOOT_TOE.x, FOOT_TOE.y, FOOT_TOE.z))
print('IMPACT', tuple(round(x, 3) for x in IMPACT))

rip_sparks = burst(12, NECK_P + V((0, 0, 0.03)), 1.25, 0.011, 21)
rip_glass = burst(8, NECK_P + V((0, 0, 0.05)), 1.6, 0.008, 22, MAT_GLASS)
land_sparks = burst(8, LAND + V((0, 0, 0.05)), 0.9, 0.008, 33)
kick_sparks = burst(14, IMPACT, 1.7, 0.009, 45)
kick_glass = burst(6, IMPACT, 2.0, 0.007, 46, MAT_GLASS)


def pose_frame(i):
    """Coloca heroe, Ojo y farol en la celda i."""
    kf = kick_clip(i)
    hp = hp_for(i)
    if kf is not None:
        off = kick_hips_offset(kf)
        w = 1.0
        if i >= BLEND_C:
            w = max(0.0, 1.0 - (i - BLEND_C + 1) / float(BLEND_N))
        hp['hx'] += off.x * w
        hp['hy'] = off.y * w
        hp['dz'] = hp.get('dz', 0.0) + off.z * w
        hero_pose(hp, kick_f=kf, kick_w=w)
        ojo_standing(i)
        return {}
    hero_pose(hp)
    ojo_standing(i)
    if 2 <= i < RIP_F:
        M = lantern_matrix(i)
        return grip({'Left': M @ GRAB_L, 'Right': M @ GRAB_R})
    if RIP_F <= i <= RELEASE_F:
        M = lantern_matrix(i)
        lc = M @ LANTERN_C
        r = M.to_3x3().normalized()
        return grip({'Left': lc + r @ V((0, 0.070, -0.030)), 'Right': lc + r @ V((0, -0.070, -0.030))})
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
DIRBB = {}
for _d in DIRS:
    os.makedirs(os.path.join(RAW, 'raw_d%d' % _d), exist_ok=True)

from bpy_extras.object_utils import world_to_camera_view

frames = [int(x) for x in str(TEST_F).split(',')] if MODE == 'test' else list(range(N_FRAMES))
for i in frames:
    gaps = pose_frame(i)
    M = lantern_matrix(i)
    HEAD_BAKED.matrix_world = M
    HEAD_BAKED.hide_render = False
    for s in rip_sparks + rip_glass:
        s.place((i - RIP_F) * DT)
    for s in land_sparks:
        s.place((i - LAND_F) * DT)
    for s in kick_sparks + kick_glass:
        s.place((i - CONTACT_F) * DT)
    update()
    vis = [hero.mesh] + ([] if HERO_ONLY else [BODY_SKIN, HEAD_BAKED]) \
        + [s.o for s in rip_sparks + rip_glass + land_sparks + kick_sparks + kick_glass]
    for d in DIRS:
        if os.environ.get('NO_RENDER') == '1':
            break
        place_cam(CAM, CENTER, 45.0 - d * 45.0, 30.0, 1.0)
        _t = math.radians(-d * 45.0)
        _lib.LIGHT_DIR = V((math.cos(_t), math.sin(_t)))
        build_shadow(vis, mat=MAT_BLACK)
        render_passes(d, i, vis)
    place_cam(CAM, CENTER, 45.0, 30.0, 1.0)
    # encuadre: caja de los personajes (sin chispas) proyectada a px de celda
    dg = bpy.context.evaluated_depsgraph_get()
    px = []
    for o in vis[:1 + (0 if HERO_ONLY else 2)]:
        vs, _ = eval_world_mesh(o, dg)
        for v in vs:
            co = world_to_camera_view(bpy.context.scene, CAM, v)
            px.append((co.x * 96, (1 - co.y) * 96))
    if px:
        print('FRAME %2d gaps %s bbox_px x %.1f..%.1f y %.1f..%.1f'
              % (i, gaps, min(p[0] for p in px), max(p[0] for p in px),
                 min(p[1] for p in px), max(p[1] for p in px)))
    print('       hero hips %s head %s rfoot %s | ojo hips %s'
          % (tuple(round(x, 2) for x in head_world(hero, 'Hips')),
             tuple(round(x, 2) for x in head_world(hero, 'Head')),
             tuple(round(x, 2) for x in head_world(hero, 'RightFoot')),
             tuple(round(x, 2) for x in head_world(ojo, 'Hips'))))
    _co = world_to_camera_view(bpy.context.scene, CAM, V((0, 0, 0)))
    print('       pies_px', (round(_co.x * 96, 1), round((1 - _co.y) * 96, 1)))
for d in sorted(DIRBB):
    bb = DIRBB[d]
    print('DIR %d bbox_px x %.1f..%.1f y %.1f..%.1f' % (d, bb[0], bb[1], bb[2], bb[3]))
print('OK', frames, 'dirs', DIRS, 'cell', CELL)


