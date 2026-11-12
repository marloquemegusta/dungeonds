"""Construye los 4 FBX del Cireneo (walk, charge, telegraph, stuck).

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_cireneo.py -- <raiz_worktree>

Entradas (en <raiz>/assets/models/characters/cireneo/source): FBX Tripo + FBX de la cruz.
Salidas  (en <raiz>/assets/models/characters/cireneo): cireneo_{walk,charge,telegraph,stuck}.fbx
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix, Quaternion

ROOT = sys.argv[sys.argv.index('--') + 1]
SRC = os.path.join(ROOT, 'assets/models/characters/cireneo/source')
OUT = os.path.join(ROOT, 'assets/models/characters/cireneo')
CHAR_FBX = os.path.join(SRC, 'tripo_convert_172f5fef-dd4a-431e-99f9-1ab308e5dd5f.fbx')
CRUZ_FBX = os.path.join(SRC, 'cruz/tripo_convert_aa6eb455-e144-49a5-b7d9-05aae513b67b.fbx')

# ---- parametros de la cruz (unidades locales del armature = cm) ----
CRUZ_SCALE = 1.15       # escala uniforme respecto a la cruz original
CRUZ_LOWER_K = 0.40     # compresion del palo por debajo del travesaño
CRUZ_BAR_Z = 58.07      # altura del travesaño = altura de los brazos (hueso LeftArm)
CRUZ_CX = 0.195         # eje X del torso
CRUZ_ARM_EMBED = 2.5    # cm que la cara frontal del travesa�o se mete en la parte trasera de los brazos

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
act_charge = [a for a in bpy.data.actions if 'charge' in a.name][0]
act_walk = [a for a in bpy.data.actions if 'walk' in a.name][0]
for a in (act_charge, act_walk):
    a.use_fake_user = True
bpy.ops.import_scene.fbx(filepath=CRUZ_FBX)
cruz = [o for o in bpy.data.objects if o.type == 'MESH' and o != char_mesh][0]
cruz.name = 'Cruz'
scene = bpy.context.scene
A_inv = arm.matrix_world.inverted()
PB = arm.pose.bones
P = 'mixamorig:'


def update():
    bpy.context.view_layer.update()


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


def bake_tripo(act, lean=None, hips_lock=None):
    """Devuelve lista de poses (dict). lean = (hips, spine, spine1, spine2, neck, head) en grados."""
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
LEAN_CHARGE = (10, 11, 11, 11, -16, -14)
walk = bake_tripo(act_walk)
charge = bake_tripo(act_charge, lean=LEAN_CHARGE)
load_pose(walk[0]); print('WALK torso angle f0 %.1f' % torso_angle())
load_pose(charge[0]); print('CHARGE torso angle f0 %.1f' % torso_angle())

base = walk[0]
tend = telegraph_end(base)
N_TG = 15
telegraph = [blend(base, tend, smooth(i / N_TG)) for i in range(N_TG + 1)]
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
    made[key] = write_action('Cireneo_' + key, poses, fps)

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
