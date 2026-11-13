"""Construye los 4 FBX del Cireneo v2 (walk, charge, telegraph, stuck) sobre el modelo nuevo.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_cireneo_v2.py -- <raiz_worktree>

Entradas: modelo nuevo rigeado sin animaciones (source_v2), cruz nueva (source_v2/cruz) y el modelo
antiguo con las animaciones Tripo de walk y charge (source). Walk y charge se transfieren por
COPY_ROTATION (WORLD) y se hornean; el armature antiguo se borra despues.
Salidas (en <raiz>/assets/models/characters/cireneo): cireneo_{walk,charge,telegraph,stuck}.fbx
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix, Quaternion

ROOT = sys.argv[sys.argv.index('--') + 1]
SRC = os.path.join(ROOT, 'assets/models/characters/cireneo/source_v2')
OLD_SRC = os.path.join(ROOT, 'assets/models/characters/cireneo/source')
OUT = os.path.join(ROOT, 'assets/models/characters/cireneo')
CHAR_FBX = os.path.join(SRC, 'tripo_convert_cd715dbe-128f-4b59-b47f-5e36cc9cd8ac.fbx')
OLD_FBX = os.path.join(OLD_SRC, 'tripo_convert_172f5fef-dd4a-431e-99f9-1ab308e5dd5f.fbx')
CRUZ_FBX = os.path.join(SRC, 'cruz/tripo_convert_ed8f6d13-db47-4c2d-be6b-24996b3fd8fe.fbx')
WALK_FBX = os.path.join(SRC, 'anim/Walking.fbx')   # andar Mixamo (32 frames, root motion)
# ---- parametros de la cruz (unidades locales del armature = cm) ----
CRUZ_SCALE = 1.15       # escala uniforme respecto a la cruz original
CRUZ_LOWER_K = 0.70     # compresion del palo por debajo del travesaño
CRUZ_BAR_Z = 58.07      # altura del travesaño = altura de los brazos (hueso LeftArm)
CRUZ_CX = 0.195         # eje X del torso
CRUZ_ARM_EMBED = 2.5    # cm que la cara frontal del travesa�o se mete en la parte trasera de los brazos

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
before_old = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=OLD_FBX)
old_objs = [o for o in bpy.data.objects if o not in before_old]
old_arm = [o for o in old_objs if o.type == 'ARMATURE'][0]
old_mesh = [o for o in old_objs if o.type == 'MESH'][0]
old_walk_act = [a for a in bpy.data.actions if 'walk' in a.name][0]
old_charge_act = [a for a in bpy.data.actions if 'charge' in a.name][0]
before_walk = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=WALK_FBX)
walk_objs = [o for o in bpy.data.objects if o not in before_walk]
walk_arm = [o for o in walk_objs if o.type == 'ARMATURE'][0]
walk_act_src = walk_arm.animation_data.action
before_cruz = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=CRUZ_FBX)
cruz = [o for o in bpy.data.objects if o.type == 'MESH' and o not in before_cruz][0]
cruz.name = 'Cruz'
scene = bpy.context.scene
A_inv = arm.matrix_world.inverted()
PB = arm.pose.bones
P = 'mixamorig:'


def update():
    bpy.context.view_layer.update()



# ------------------------------------------------------------------ transferencia andar/carga (antiguo -> nuevo)
BODY_BONES = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
              'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg', 'RightFoot']


def hips_world_z(o):
    bpy.context.view_layer.update()
    return (o.matrix_world @ o.data.bones[P + 'Hips'].head_local).z


# escala el armature antiguo para que su Hips quede a la misma altura que el del nuevo
_k = hips_world_z(arm) / hips_world_z(old_arm)
old_arm.scale = old_arm.scale * _k
print('TRANSFER hips z new=%.3f old_scaled=%.3f k=%.4f' % (hips_world_z(arm), hips_world_z(old_arm), _k))


def retarget_walk(src_arm, src_act, k):
    """Andar Mixamo -> rig nuevo por delta de rotacion respecto al reposo de cada hueso.
    Un COPY_ROTATION en WORLD copia el reposo del origen (rolls de Mixamo distintos) y gira el cuerpo;
    aqui cada hueso recibe (rotacion_src_pose * rotacion_src_rest^-1) * rotacion_tgt_rest."""
    src_arm.animation_data_create()
    src_arm.animation_data.action = src_act
    arm.animation_data_create()
    arm.animation_data.action = None
    SPB = src_arm.pose.bones
    f0, f1 = int(round(src_act.frame_range[0])), int(round(src_act.frame_range[1]))
    out = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        for pb in PB:
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        update()
        for n in BODY_BONES:
            sp = SPB[P + n]; sb = src_arm.data.bones[P + n]; tb = arm.data.bones[P + n]
            R_src_pose = sp.matrix.to_3x3().normalized()
            R_src_rest = sb.matrix_local.to_3x3().normalized()
            R_des = (R_src_pose @ R_src_rest.inverted()) @ tb.matrix_local.to_3x3().normalized()
            if n == 'Hips':
                head = tb.head_local + (sp.matrix.translation - sb.matrix_local.translation) * k
            else:
                head = PB[P + n].matrix.translation.copy()
            PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
            update()
        out.append({pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB})
    print('RETARGET walk frames', len(out))
    return out


def transfer(src_arm, src_act, name, copy_xy=False):
    src_arm.animation_data_create()
    src_arm.animation_data.action = src_act
    arm.animation_data_create()
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    for n in BODY_BONES:
        c = arm.pose.bones[P + n].constraints.new('COPY_ROTATION')
        c.target = src_arm; c.subtarget = P + n
        c.target_space = 'WORLD'; c.owner_space = 'WORLD'
    c = arm.pose.bones[P + 'Hips'].constraints.new('COPY_LOCATION')
    c.target = src_arm; c.subtarget = P + 'Hips'
    c.target_space = 'WORLD'; c.owner_space = 'WORLD'
    c.use_x = copy_xy; c.use_y = copy_xy; c.use_z = True
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    f0, f1 = int(round(src_act.frame_range[0])), int(round(src_act.frame_range[1]))
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, step=1, only_selected=False,
                     visual_keying=True, clear_constraints=True, clear_parents=False,
                     use_current_action=False, clean_curves=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act = arm.animation_data.action
    act.name = name
    act.use_fake_user = True
    print('TRANSFER baked %s frames %d..%d copy_xy=%s' % (name, f0, f1, copy_xy))
    return act


_kw = hips_world_z(arm) / hips_world_z(walk_arm)
walk_arm.scale = walk_arm.scale * _kw
print('TRANSFER walk hips z new=%.3f walk_scaled=%.3f k=%.4f' % (hips_world_z(arm), hips_world_z(walk_arm), _kw))
# el FBX de Mixamo trae la rotacion del objeto en el armature: se aplica al rig para que
# las rotaciones en WORLD del andar esten en el mismo marco que el armature nuevo
def _hips_dir(o):
    bpy.context.view_layer.update()
    b = o.data.bones[P + 'Hips']
    d = o.matrix_world.to_3x3() @ (b.tail_local - b.head_local)
    return tuple(round(x, 3) for x in d.normalized())
print('WALK_ARM rot before', tuple(round(x, 4) for x in walk_arm.rotation_euler), 'hips dir', _hips_dir(walk_arm))
bpy.ops.object.select_all(action='DESELECT')
walk_arm.select_set(True)
bpy.context.view_layer.objects.active = walk_arm
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
bpy.ops.object.select_all(action='DESELECT')
print('WALK_ARM rot after', tuple(round(x, 4) for x in walk_arm.rotation_euler), 'hips dir', _hips_dir(walk_arm), 'arm hips dir', _hips_dir(arm))
WALK_RAW = retarget_walk(walk_arm, walk_act_src, _kw)
act_charge = transfer(old_arm, old_charge_act, 'Tripo_charge')
# borrar el armature antiguo y sus acciones
for o in old_objs + walk_objs:
    bpy.data.objects.remove(o, do_unlink=True)
for a in (old_walk_act, old_charge_act, walk_act_src):
    a.use_fake_user = False
    bpy.data.actions.remove(a)
arm.animation_data.action = None

# ------------------------------------------------------------------ cruz
def back_of_torso():
    arm.animation_data_create()
    arm.animation_data.action = None
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    mw = A_inv @ char_mesh.matrix_world
    ys = []
    for v in char_mesh.data.vertices:
        p = mw @ v.co
        if 48 < p.z < 62 and abs(p.x) < 8:
            ys.append(p.y)
    return max(ys)


def prepare_cruz(arm_back):
    back_y = back_of_torso()
    M = cruz.matrix_world.copy()
    bm = bmesh.new(); bm.from_mesh(cruz.data)
    # 1) quitar los clavos largos (salen +-0.24 m del travesaño)
    kill = []
    for v in bm.verts:
        w = M @ v.co
        if abs(w.y) > 0.075 and 0.66 < w.z < 0.76:
            kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    # cara frontal del travesa�o (y minima en la zona del travesa�o, fuera del eje del palo)
    bar_front = min((M @ v.co).y for v in bm.verts
                    if 0.66 < (M @ v.co).z < 0.76 and 0.12 < abs((M @ v.co).x) < 0.2)
    cy = arm_back - bar_front * CRUZ_SCALE * 100.0 - CRUZ_ARM_EMBED
    print('CRUZ bar_front_local=%.3f arm_back=%.2f' % (bar_front, arm_back))
    for v in bm.verts:
        w = M @ v.co                      # metros, Z arriba, cruz de pie
        z = w.z
        if z < 0.6:
            z = 0.6 - (0.6 - z) * CRUZ_LOWER_K
        z -= 0.715                        # travesaño a 0
        v.co = Vector((CRUZ_CX + w.x * CRUZ_SCALE * 100.0,
                       cy + w.y * CRUZ_SCALE * 100.0,
                       CRUZ_BAR_Z + z * CRUZ_SCALE * 100.0))
    bm.to_mesh(cruz.data); bm.free()
    cruz.data.update()
    # objeto con transformada neutra, hijo del armature (espacio local del armature)
    cruz.parent = arm
    cruz.parent_type = 'OBJECT'
    cruz.matrix_parent_inverse = Matrix.Identity(4)
    cruz.location = (0, 0, 0); cruz.rotation_euler = (0, 0, 0); cruz.scale = (1, 1, 1)
    # skin: todo a Spine2 con peso 1
    vg = cruz.vertex_groups.new(name=P + 'Spine2')
    vg.add(list(range(len(cruz.data.vertices))), 1.0, 'REPLACE')
    mod = cruz.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    print('CRUZ back_y=%.2f cy=%.2f verts=%d' % (back_y, cy, len(cruz.data.vertices)))



# ------------------------------------------------------------------ utilidades de pose
def read_pose():
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}


def load_pose(d):
    for pb in PB:
        l, q, s = d[pb.name]
        pb.location = l; pb.rotation_quaternion = q; pb.scale = s
    update()


def rot_about(pb, R3, pivot=None):
    """Rota el hueso (espacio armature) con R3 (3x3) alrededor de su cabeza o 'pivot'."""
    m = pb.matrix
    h = pivot if pivot is not None else m.translation.copy()
    T = Matrix.Translation(h)
    pb.matrix = T @ R3.to_4x4() @ T.inverted() @ m
    update()


def pitch(pb, deg):   # + = inclinar hacia delante (-Y)
    rot_about(pb, Matrix.Rotation(math.radians(deg), 3, 'X'))


def move(pb, delta):
    pb.matrix = Matrix.Translation(delta) @ pb.matrix
    update()


def aim(pb, target):
    cur = (pb.tail - pb.head).normalized()
    want = (target - pb.head).normalized()
    rot_about(pb, cur.rotation_difference(want).to_matrix())


def two_bone_ik(side, foot_target):
    up, lg, ft = PB[P + side + 'UpLeg'], PB[P + side + 'Leg'], PB[P + side + 'Foot']
    H = up.head.copy()
    L1 = (up.bone.tail_local - up.bone.head_local).length
    L2 = (lg.bone.tail_local - lg.bone.head_local).length
    d = foot_target - H
    dist = min(d.length, (L1 + L2) * 0.995)
    dirn = d.normalized()
    a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    pole = Vector((0, -1, 0))
    pp = (pole - dirn * pole.dot(dirn)).normalized()
    knee = H + dirn * a + pp * h
    aim(up, knee)
    aim(lg, H + dirn * dist)
    # pie plano (orientacion de reposo) y dedos a reposo
    ft.matrix = Matrix.Translation(ft.head.copy()) @ ft.bone.matrix_local.to_3x3().to_4x4()
    update()
    toe = PB.get(P + side + 'ToeBase')
    if toe:
        toe.rotation_quaternion = (1, 0, 0, 0); toe.location = (0, 0, 0); update()


def rest_foot_pos(side):
    return PB[P + side + 'Foot'].bone.head_local.copy()


# ------------------------------------------------------------------ brazos en cruz (constantes)
ARM_BONES = []
for side, sx in (('Left', 1.0), ('Right', -1.0)):
    ARM_BONES += [(P + side + n, sx) for n in ('Shoulder', 'Arm', 'ForeArm', 'Hand')]
FINGER_KEYS = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')
PALM_TWIST = {'Left': 0.0, 'Right': 0.0}   # grados de torsion extra sobre el eje del hueso (palmas)


def compute_arm_constants():
    arm.animation_data.action = None
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    out = {}
    for name, sx in ARM_BONES:
        pb = PB[name]
        rest3 = pb.bone.matrix_local.to_3x3()
        yaxis = rest3 @ Vector((0, 1, 0))
        arc = yaxis.normalized().rotation_difference(Vector((sx, 0, 0))).to_matrix()
        side = 'Left' if sx > 0 else 'Right'
        tw = Matrix.Rotation(math.radians(PALM_TWIST[side] * sx), 3, 'X')   # X = eje largo tras la rotacion
        tgt3 = tw @ arc @ rest3 if name.endswith('Hand') else arc @ rest3
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
        update()
        pb.matrix = Matrix.Translation(pb.matrix.translation.copy()) @ tgt3.to_4x4()
        update()
        out[name] = (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy())
    return out


ARM_CONST = compute_arm_constants()


def force_arms():
    for pb in PB:
        short = pb.name.replace(P, '')
        if pb.name in ARM_CONST:
            l, q, s = ARM_CONST[pb.name]
            pb.location = l; pb.rotation_quaternion = q; pb.scale = s
        elif ('Hand' in short and any(k in short for k in FINGER_KEYS)):
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()


def arm_back_y():
    arm.animation_data.action = None
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    force_arms()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = char_mesh.evaluated_get(dg)
    me = ev.to_mesh()
    mw = A_inv @ ev.matrix_world
    ys = [(mw @ v.co).y for v in me.vertices if abs((mw @ v.co).x) > 16 and 50 < (mw @ v.co).z < 66]
    ev.to_mesh_clear()
    return max(ys)


prepare_cruz(arm_back_y())


# ------------------------------------------------------------------ bake de acciones Tripo
def hips_ref():
    return PB[P + 'Hips'].matrix.translation.copy()


def bake_tripo(act, lean=None, hips_lock=None, raw_poses=None):
    """Devuelve lista de poses (dict). lean = (hips, spine, spine1, spine2, neck, head) en grados."""
    if raw_poses is not None:
        raw = raw_poses
    else:
        frames = list(range(int(act.frame_range[0]), int(act.frame_range[1]) + 1))
        raw = []
        arm.animation_data.action = act
        for f in frames:
            scene.frame_set(f)
            raw.append(read_pose())
        arm.animation_data.action = None
    out = []
    ref = None
    for d in raw:
        load_pose(d)
        force_arms()
        hp = PB[P + 'Hips']
        if ref is None:
            ref = hp.matrix.translation.copy()
        t = hp.matrix.translation.copy()
        move(hp, Vector((ref.x - t.x, ref.y - t.y, 0)))   # in place
        if lean:
            for n, deg in zip(('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'), lean):
                if deg:
                    pitch(PB[P + n], deg)
        force_arms()
        out.append(read_pose())
    return out


def torso_angle():
    """Inclinacion del tronco respecto a la vertical (grados): Hips -> Neck."""
    v = PB[P + 'Neck'].head - PB[P + 'Hips'].head
    return math.degrees(math.atan2(-v.y, v.z))


def blend(p0, p1, t):
    out = {}
    for n in p0:
        l0, q0, s0 = p0[n]; l1, q1, s1 = p1[n]
        out[n] = (l0.lerp(l1, t), q0.slerp(q1, t), s0.lerp(s1, t))
    return out


def smooth(t):
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ poses a mano
def pose_from(base, fn):
    load_pose(base)
    force_arms()
    fn()
    force_arms()
    return read_pose()


def telegraph_end(base):
    def fn():
        hp = PB[P + 'Hips']
        feet = {s: rest_foot_pos(s) for s in ('Left', 'Right')}
        pitch(hp, 20)
        move(hp, Vector((0, -3.0, -9.0)))
        for n, deg in (('Spine', 24), ('Spine1', 24), ('Spine2', 22), ('Neck', -6), ('Head', 8)):
            pitch(PB[P + n], deg)
        two_bone_ik('Left', feet['Left'] + Vector((9.5, -5.0, 0)))
        two_bone_ik('Right', feet['Right'] + Vector((-9.5, 5.0, 0)))
        print('TELEGRAPH torso angle %.1f' % torso_angle())
    return pose_from(base, fn)


def stuck_frame(base, t):
    ph = 2 * math.pi * 2 * t            # 2 sacudidas por bucle
    ph1 = 2 * math.pi * t               # balanceo lento
    def fn():
        hp = PB[P + 'Hips']
        feet = {s: rest_foot_pos(s) for s in ('Left', 'Right')}
        pitch(hp, 12)
        move(hp, Vector((0.0, 6.0 + 1.6 * math.sin(ph), -6.0 + 1.0 * math.sin(ph + 1.2))))
        for n, deg in (('Spine', 9), ('Spine1', 9), ('Spine2', 7 + 3.5 * math.sin(ph + 0.7)),
                       ('Neck', -2), ('Head', 5)):
            pitch(PB[P + n], deg)
        rot_about(PB[P + 'Spine1'], Matrix.Rotation(math.radians(2.5 * math.sin(ph1)), 3, 'Z'))
        two_bone_ik('Left', feet['Left'] + Vector((6.0, -6.0 - 1.2 * math.sin(ph + 0.4), 0)))
        two_bone_ik('Right', feet['Right'] + Vector((-6.0, -3.0 + 1.2 * math.sin(ph + 0.4), 0)))
    return pose_from(base, fn)


# ------------------------------------------------------------------ escritura de acciones
def write_action(name, poses, fps):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    for i, d in enumerate(poses):
        load_pose(d)
        for pb in PB:
            pb.keyframe_insert('location', frame=i)
            pb.keyframe_insert('rotation_quaternion', frame=i)
            pb.keyframe_insert('scale', frame=i)
    act.frame_range = (0, len(poses) - 1)
    return act, fps


# --- generar
LEAN_CHARGE = (25, 22, 22, 18, -28, -20)
LEAN_WALK = (5, 6, 6, 6, 0, 0)       # andar: encorvado bajo la cruz (Hips, Spine, Spine1, Spine2, Neck, Head)
WALK_FRAMES = 40                     # 32 frames de Mixamo repartidos en 40 (pasos mas lentos)


def resample(poses, n_out):
    n_in = len(poses)
    out = []
    for i in range(n_out):
        x = i * (n_in - 1) / (n_out - 1)
        i0 = int(x); i1 = min(i0 + 1, n_in - 1)
        out.append(blend(poses[i0], poses[i1], x - i0) if i1 != i0 else poses[i0])
    return out


walk = resample(bake_tripo(None, lean=LEAN_WALK, raw_poses=WALK_RAW), WALK_FRAMES)
charge = bake_tripo(act_charge, lean=LEAN_CHARGE)
load_pose(walk[0]); print('WALK torso angle f0 %.1f' % torso_angle())
load_pose(charge[0]); print('CHARGE torso angle f0 %.1f' % torso_angle())

# base de telegrafia y atascado: frame 0 del andar SIN inclinacion (como antes), para que la telegrafia
# mantenga su pose final; la telegrafia arranca desde walk[0] (con inclinacion) para continuar el andar
base = bake_tripo(None, raw_poses=WALK_RAW[:1])[0]
tend = telegraph_end(base)
N_TG = 15
telegraph = [blend(walk[0], tend, smooth(i / N_TG)) for i in range(N_TG + 1)]
N_ST = 15
stuck = [stuck_frame(base, i / N_ST) for i in range(N_ST + 1)]
stuck[-1] = stuck[0]

ACTIONS = [
    ('walk', 'cireneo_walk', walk, 24),
    ('charge', 'cireneo_charge', charge, 24),
    ('telegraph', 'cireneo_telegraph', telegraph, 30),
    ('stuck', 'cireneo_stuck', stuck, 30),
]
made = {}
for key, name, poses, fps in ACTIONS:
    made[key] = write_action(name, poses, fps)

# ------------------------------------------------------------------ exportar
for key, name, poses, fps in ACTIONS:
    act, _ = made[key]
    arm.animation_data.action = act
    scene.name = name
    scene.render.fps = fps
    scene.frame_start = 0
    scene.frame_end = len(poses) - 1
    bpy.ops.object.select_all(action='DESELECT')
    for o in (arm, char_mesh, cruz):
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(OUT, name + '.fbx')
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=False, add_leaf_bones=False, path_mode='COPY', embed_textures=True,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0, mesh_smooth_type='FACE')
    print('EXPORTED', path)
