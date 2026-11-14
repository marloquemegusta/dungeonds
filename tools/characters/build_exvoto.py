"""Construye los 4 FBX del Exvoto (monja de cera): rezar de pie, rezar de rodillas, levantarse y andar rezando.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_exvoto.py -- <raiz_worktree>

Entradas: modelo Tripo con rig Mixamo sin animaciones (assets/models/characters/exvoto/source) y clips
Mixamo del esqueleto Y-bot (assets/models/animations/pray/*.fbx, walk/walk_normal.fbx).
Transferencia: por hueso, en espacio de MUNDO, delta de rotacion respecto al reposo de cada esqueleto
(R_obj = R_pose_src * R_rest_src^-1 * R_rest_tgt); la traslacion de la cadera se escala por la relacion
de alturas. Todo se calcula con matematicas de matrices (sin depsgraph) y se escribe como acciones.
Salidas (en <raiz>/assets/models/characters/exvoto): exvoto_{pray_stand,pray_kneel,stand_up,walk}.fbx
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = sys.argv[sys.argv.index('--') + 1]
OUT = os.path.join(ROOT, 'assets/models/characters/exvoto')
CHAR_FBX = os.path.join(OUT, 'source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx')
ANIM = os.path.join(ROOT, 'assets/models/animations')
SRC_FILES = {
    'stand': os.path.join(ANIM, 'pray/pray_standing.fbx'),
    'kneel': os.path.join(ANIM, 'pray/pray_kneeling.fbx'),
    'k2s': os.path.join(ANIM, 'pray/pray_kneel_to_stand.fbx'),
    'walk': os.path.join(ANIM, 'walk/walk_normal.fbx'),
}
FPS = 30
P = 'mixamorig:'

# ---- parametros ajustables ----
STAND_UP_START = 138          # frame de pray_kneel_to_stand donde empieza el tramo (manos ya en los muslos)
STAND_UP_START_BLEND = 8      # primeros frames que se funden desde la pose de pray_kneel
STAND_UP_ARMS_BLEND = 24      # ultimos frames en que las manos vuelven al rezo
STAND_UP_BLEND = 10           # ultimos frames que se funden hacia la pose inicial del andar
WALK_FRAMES = 44              # 32 frames de Mixamo repartidos en 44 (pasos mas lentos)
WALK_STRIDE = 0.8             # factor de zancada sobre rotaciones de UpLeg/Leg
WALK_SPINE_DAMP = 0.5         # fraccion del giro de columna del andar que se conserva
WALK_LEAN = {'Spine': 7, 'Spine1': 7, 'Spine2': 7, 'Neck': 12, 'Head': 12}   # grados, + = hacia delante
WALK_ARMS_FRAME = 1           # frame de pray_standing del que salen los brazos
ARM_BONES_KEYS = ('Shoulder', 'Arm', 'ForeArm', 'Hand')   # incluye dedos (nombres con 'Hand' + dedo)

scene = bpy.context.scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
PB = arm.pose.bones
A_W = arm.matrix_world.copy()
A_RW = A_W.to_3x3().normalized()
A_INV = A_W.inverted()
for pb in PB:
    pb.rotation_mode = 'QUATERNION'


def update():
    bpy.context.view_layer.update()


def load_src(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    a = [o for o in new if o.type == 'ARMATURE'][0]
    for o in new:
        if o.type == 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return a


SRC = {k: load_src(v) for k, v in SRC_FILES.items()}

# orden de huesos padre -> hijo
ORDER = []
def _walk(b):
    ORDER.append(b.name)
    for c in b.children:
        _walk(c)
for b in arm.data.bones:
    if b.parent is None:
        _walk(b)
assert len(ORDER) == 65, len(ORDER)
REST_REL = {}
for n in ORDER:
    b = arm.data.bones[n]
    REST_REL[n] = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy()


def facing(o, foot='mixamorig:LeftFoot', toe='mixamorig:LeftToeBase'):
    update()
    d = o.matrix_world @ o.data.bones[toe].head_local - o.matrix_world @ o.data.bones[foot].head_local
    return Vector((d.x, d.y, 0)).normalized()


# Mixamo importado mira a +Y? (el Exvoto mira a -Y). Se corrige con un giro de 180 grados en Z si difiere.
_ft, _fs = facing(arm), facing(SRC['walk'])
print('FACING target', tuple(round(x, 2) for x in _ft), 'source', tuple(round(x, 2) for x in _fs))
F = _fs.rotation_difference(_ft).to_matrix()   # rotacion en Z que lleva la direccion de la fuente a la del destino
F = Matrix(F)

HIPS_K = (A_W @ arm.data.bones[P + 'Hips'].head_local).z / (SRC['walk'].matrix_world @ SRC['walk'].data.bones[P + 'Hips'].head_local).z
print('HIPS K (altura Exvoto / altura Beta) = %.4f' % HIPS_K)


# ------------------------------------------------------------------ transferencia
def src_frame_world(src, frame):
    scene.frame_set(frame)
    update()
    return src


def retarget_frame(src, frame, damp=None):
    """Devuelve (M, basis): M = matrices en espacio armature por hueso; basis = (loc, quat) por hueso.
    damp: dict nombre_corto -> factor [0..1] sobre el delta de rotacion (para amortiguar)."""
    scene.frame_set(frame)
    update()
    SM = src.matrix_world
    SR = SM.to_3x3().normalized()
    SPB = src.pose.bones
    M = {}
    basis = {}
    for n in ORDER:
        sp = SPB[n]; sb = src.data.bones[n]; tb = arm.data.bones[n]
        Rs_pose = SR @ sp.matrix.to_3x3().normalized()
        Rs_rest = SR @ sb.matrix_local.to_3x3().normalized()
        D = F @ (Rs_pose @ Rs_rest.inverted()) @ F.inverted()
        short = n.replace(P, '')
        if damp and short in damp:
            q = D.to_quaternion()
            D = Quaternion((1, 0, 0, 0)).slerp(q, damp[short]).to_matrix()
        Rt_rest = A_RW @ tb.matrix_local.to_3x3().normalized()
        R_arm = A_RW.inverted() @ (D @ Rt_rest)
        par = tb.parent.name if tb.parent else None
        Pm = (M[par] @ REST_REL[n]) if par else REST_REL[n]
        if n == P + 'Hips':
            dw = F @ ((SM @ sp.head) - (SM @ sb.head_local)) * HIPS_K
            head_w = (A_W @ tb.head_local) + dw
            head = A_INV @ head_w
        else:
            head = Pm.translation.copy()
        Md = Matrix.Translation(head) @ R_arm.to_4x4()
        M[n] = Md
        B = Pm.inverted() @ Md
        loc, rot, _ = B.decompose()
        basis[n] = (loc, rot)
    return basis


def fk(basis):
    """basis -> M (espacio armature) por hueso."""
    M = {}
    for n in ORDER:
        loc, rot = basis[n]
        B = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
        tb = arm.data.bones[n]
        Pm = (M[tb.parent.name] @ REST_REL[n]) if tb.parent else REST_REL[n]
        M[n] = Pm @ B
    return M


def hips_world(basis):
    M = fk(basis)
    return A_W @ M[P + 'Hips'].translation


def apply_lean(basis, lean):
    """Inclina cada hueso (grados, + = hacia delante = -Y) alrededor de su cabeza, arrastrando a sus hijos."""
    out = dict(basis)
    M = {}
    for n in ORDER:
        loc, rot = out[n]
        B = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
        tb = arm.data.bones[n]
        Pm = (M[tb.parent.name] @ REST_REL[n]) if tb.parent else REST_REL[n]
        Mo = Pm @ B
        deg = lean.get(n.replace(P, ''), 0)
        if deg:
            h = Mo.translation.copy()
            T = Matrix.Translation(h)
            R = Matrix.Rotation(math.radians(deg), 4, 'X')
            Mo = T @ R @ T.inverted() @ Mo
            l2, r2, _ = (Pm.inverted() @ Mo).decompose()
            out[n] = (l2, r2)
        M[n] = Mo
    return out


def shift_hips(basis, delta_arm):
    """Traslada la cadera delta_arm (Vector en espacio armature)."""
    out = dict(basis)
    n = P + 'Hips'
    loc, rot = out[n]
    B = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    Mo = REST_REL[n] @ B
    Mo = Matrix.Translation(delta_arm) @ Mo
    l2, r2, _ = (REST_REL[n].inverted() @ Mo).decompose()
    out[n] = (l2, r2)
    return out


def blend_basis(b0, b1, t):
    out = {}
    for n in b0:
        l0, q0 = b0[n]; l1, q1 = b1[n]
        out[n] = (l0.lerp(l1, t), q0.slerp(q1, t))
    return out


def smooth(t):
    return t * t * (3 - 2 * t)


def anchor_hips_xy(poses, ref_world=None):
    """Quita el desplazamiento horizontal de la cadera respecto al primer frame (o ref_world)."""
    ref = ref_world if ref_world is not None else hips_world(poses[0])
    out = []
    for b in poses:
        h = hips_world(b)
        d = Vector((ref.x - h.x, ref.y - h.y, 0)) * 100.0 / (A_W.to_scale().x * 100.0)   # mundo m -> armature cm
        out.append(shift_hips(b, Vector((d.x, d.y, 0)) ))
    return out


# ------------------------------------------------------------------ medicion y escritura
def load_pose(basis):
    for pb in PB:
        l, q = basis[pb.name]
        pb.location = l; pb.rotation_quaternion = q; pb.scale = (1, 1, 1)


def mesh_z_min():
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = char_mesh.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(n, 3)
    mw = np.array(ev.matrix_world)
    z = co @ mw[2, :3] + mw[2, 3]
    ev.to_mesh_clear()
    return float(z.min())


def clip_zmin(poses, step=3):
    idx = sorted(set(list(range(0, len(poses), step)) + [len(poses) - 1]))
    res = {}
    for i in idx:
        load_pose(poses[i])
        res[i] = mesh_z_min()
    return res


def ground(poses, mode='const', z_end=0.0):
    """Desplaza la cadera en Z para que la z minima de la malla sea 0. mode const: un solo desplazamiento
    (el minimo del clip); lerp: interpola entre el desplazamiento del primer y del ultimo frame."""
    zs = clip_zmin(poses)
    if mode == 'const':
        dz = -min(zs.values())
        dzs = [dz] * len(poses)
    else:
        i0, i1 = 0, len(poses) - 1
        dz0, dz1 = -zs[i0], z_end - zs[i1]
        dzs = [dz0 + (dz1 - dz0) * i / (len(poses) - 1) for i in range(len(poses))]
    return [shift_hips(b, Vector((0, 0, dz / A_W.to_scale().x))) for b, dz in zip(poses, dzs)]


def write_action(name, poses):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if not arm.animation_data:
        arm.animation_data_create()
    arm.animation_data.action = act
    for i, d in enumerate(poses):
        load_pose(d)
        for pb in PB:
            pb.keyframe_insert('location', frame=i)
            pb.keyframe_insert('rotation_quaternion', frame=i)
            pb.keyframe_insert('scale', frame=i)
    act.frame_range = (0, len(poses) - 1)
    return act


def report(name, poses, src_range):
    zs = clip_zmin(poses, step=1)
    hz = [hips_world(b).z for b in poses]
    print('CLIP %-14s src_frames=%s n=%d  zmin(mesh) first=%.4f last=%.4f min=%.4f max=%.4f | hips z first=%.3f last=%.3f min=%.3f max=%.3f' % (
        name, src_range, len(poses), zs[0], zs[len(poses) - 1], min(zs.values()), max(zs.values()),
        hz[0], hz[-1], min(hz), max(hz)))


def pose_diff(a, b):
    """Mayor distancia entre cabezas de hueso (m) de dos poses."""
    Ma, Mb = fk(a), fk(b)
    return max((A_W @ Ma[n].translation - A_W @ Mb[n].translation).length for n in ORDER)


def clip_from(src, f0, f1):
    return [retarget_frame(src, f) for f in range(f0, f1 + 1)]


# ------------------------------------------------------------------ generar
clips = {}

# 1) rezar de pie
raw = clip_from(SRC['stand'], 1, 98)
print('LOOP pray_stand diff f1 vs f98: %.4f m' % pose_diff(raw[0], raw[-1]))
poses = anchor_hips_xy(raw)
poses[-1] = poses[0]
clips['pray_stand'] = (ground(poses), '1-98')

# 2) rezar de rodillas
raw = clip_from(SRC['kneel'], 1, 59)
print('LOOP pray_kneel diff f1 vs f59: %.4f m' % pose_diff(raw[0], raw[-1]))
poses = anchor_hips_xy(raw)
poses[-1] = poses[0]
clips['pray_kneel'] = (ground(poses), '1-59')

# 3) andar rezando (se hace antes que levantarse para poder fundir el final con su pose inicial)
walk_raw_src = [retarget_frame(SRC['walk'], f, damp={
    'Spine': WALK_SPINE_DAMP, 'Spine1': WALK_SPINE_DAMP, 'Spine2': WALK_SPINE_DAMP,
    'Neck': WALK_SPINE_DAMP, 'Head': WALK_SPINE_DAMP,
    'LeftUpLeg': WALK_STRIDE, 'RightUpLeg': WALK_STRIDE, 'LeftLeg': WALK_STRIDE, 'RightLeg': WALK_STRIDE,
}) for f in range(1, 33)]
arms_pose = retarget_frame(SRC['stand'], WALK_ARMS_FRAME)
ARM_SET = set()
for n in ORDER:
    short = n.replace(P, '')
    side_less = short.replace('Left', '').replace('Right', '')
    if short.startswith(('Left', 'Right')) and (side_less in ARM_BONES_KEYS or side_less.startswith('Hand')):
        ARM_SET.add(n)
print('ARM_SET', len(ARM_SET))
walk_in = []
for b in walk_raw_src:
    b2 = dict(b)
    for n in ARM_SET:
        b2[n] = arms_pose[n]
    walk_in.append(b2)
# bucle: 32 frames de Mixamo + frame 33 = frame 1; remuestreo a WALK_FRAMES+1 (ultimo = primero)
loop = walk_in + [walk_in[0]]
res = []
for i in range(WALK_FRAMES + 1):
    x = i * (len(loop) - 1) / WALK_FRAMES
    i0 = int(x); i1 = min(i0 + 1, len(loop) - 1)
    res.append(blend_basis(loop[i0], loop[i1], x - i0) if i1 != i0 else loop[i0])
res = anchor_hips_xy(res)
res = [apply_lean(b, WALK_LEAN) for b in res]
res[-1] = res[0]
walk_poses = ground(res)
clips['walk'] = (walk_poses, '1-32 (+1 cierre) -> %d frames' % (WALK_FRAMES + 1))

# 4) levantarse: de rodillas rezando -> de pie. Tramo de pray_kneel_to_stand desde que las manos dejan el rezo
#    (se apoyan en los muslos) hasta de pie. Para que encadene con el bucle de rodillas se funde el INICIO desde
#    la pose de pray_kneel, y para que encadene con el andar se funden las manos hacia el rezo (ultimos
#    STAND_UP_ARMS_BLEND frames) y el cuerpo entero hacia el primer frame del andar (ultimos STAND_UP_BLEND).
k2s_raw = clip_from(SRC['k2s'], 1, 207)
hz = [hips_world(b).z for b in k2s_raw]
print('K2S hips z (cada 10 frames):', [(i + 1, round(z, 3)) for i, z in enumerate(hz) if i % 10 == 0], 'f207=%.3f' % hz[-1])
seg = k2s_raw[STAND_UP_START - 1:207]
kneel_raw0 = anchor_hips_xy(clip_from(SRC['kneel'], 1, 1))[0]
kref = hips_world(kneel_raw0)
seg = anchor_hips_xy(seg, ref_world=Vector((kref.x, kref.y, 0)))   # cadera en el sitio, donde esta el bucle de rodillas
n = len(seg)
walk0 = clips['walk'][0][0]


def blend_part(b0, b1, t, names):
    out = dict(b0)
    for k in names:
        l0, q0 = b0[k]; l1, q1 = b1[k]
        out[k] = (l0.lerp(l1, t), q0.slerp(q1, t))
    return out


fin = []
for i, b in enumerate(seg):
    if i < STAND_UP_START_BLEND:                       # inicio: desde la pose de rodillas rezando
        b = blend_basis(kneel_raw0, b, smooth((i + 0.0) / STAND_UP_START_BLEND))
    ja = i - (n - 1 - STAND_UP_ARMS_BLEND)
    if ja > 0:                                         # manos hacia el rezo
        b = blend_part(b, walk0, smooth(ja / STAND_UP_ARMS_BLEND), ARM_SET)
    j = i - (n - 1 - STAND_UP_BLEND)
    if j > 0:                                          # cuerpo entero hacia el primer frame del andar
        b = blend_basis(b, walk0, smooth(j / STAND_UP_BLEND))
    fin.append(b)
walk0_z = clip_zmin([walk0], step=1)[0]      # el primer frame del andar flota 1-2 cm: se encadena con el mismo suelo
clips['stand_up'] = (ground(fin, mode='lerp', z_end=walk0_z), '%d-207' % STAND_UP_START)
print('STAND_UP end vs walk f0 head dist max: %.4f m' % pose_diff(clips['stand_up'][0][-1], walk0))
print('STAND_UP start vs pray_kneel f0 head dist max: %.4f m' % pose_diff(clips['stand_up'][0][0], clips['pray_kneel'][0][0]))

# ------------------------------------------------------------------ escribir y exportar
NAMES = {'pray_stand': 'exvoto_pray_stand', 'pray_kneel': 'exvoto_pray_kneel',
         'stand_up': 'exvoto_stand_up', 'walk': 'exvoto_walk'}
made = {}
for key, (poses, rng) in clips.items():
    report(key, poses, rng)       # antes de escribir acciones (una accion asignada pisaria la pose medida)
for key, (poses, rng) in clips.items():
    made[key] = write_action(NAMES[key], poses)

for key, (poses, rng) in clips.items():
    arm.animation_data.action = made[key]
    scene.name = NAMES[key]
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = len(poses) - 1
    bpy.ops.object.select_all(action='DESELECT')
    for o in (arm, char_mesh):
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(OUT, NAMES[key] + '.fbx')
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=False, add_leaf_bones=False, path_mode='COPY', embed_textures=True,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0, mesh_smooth_type='FACE')
    print('EXPORTED', path, 'frames 0-%d' % (len(poses) - 1))
