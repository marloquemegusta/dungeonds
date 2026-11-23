"""Construye los clips del Campanero de Animas (jefe ARPG, arrastra una campana agrietada de bronce):
campanero_idle (Sad Idle, bucle), campanero_walk (Injured Walk en el sitio, bucle, fase III),
campanero_toque (Standing Melee Attack Downward recortado: 6 fotogramas de alzar = telegrafia, 2 de golpe),
campanero_tanido (balanceo procedural de la campana desde la pose de reposo: el toque menor) y
campanero_death (Falling Back Death).

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_campanero.py -- <raiz_worktree> [idle walk toque tanido death]

Entradas:
  - cuerpo: campanero/source/tripo_convert_0865ecc9-*.fbx (rig Mixamo, T-pose; barba y sombrero de bruja).
  - campana: campanero/source/campana/*.fbx (malla sin rig; boca abajo, el yugo de madera arriba).
  - clips de Mixamo: assets/models/animations/campanero/{sad_idle,injured_walk,melee_downward,falling_back_death}.fbx
    (esqueleto Y-bot), transferidos por delta de rotacion respecto al reposo de cada hueso (como build_abanderado.py),
    cadera en el sitio (solo el rebote vertical; la caida de la muerte conserva la mitad del desplazamiento).
La campana cuelga de la mano derecha por el yugo con un hueso auxiliar 'mixamorig:CampaneroBell' (hijo de la mano) cuya
orientacion es en espacio de armature: vertical (boca abajo) y, segun el clip, sigue una fraccion del giro de la mano.
Todos los clips llevan el mismo mesh degenerado de limites (todos los fotogramas de todos los clips) para que el lab los
encuadre igual (misma escala y mismo ancla de suelo).
Cada clip son 8 muestras + 1 de cierre (bucles: el cierre repite la primera; el resto: repite la ultima), a 24 fps: el lab
toma duration*i/8 y cae justo en cada muestra.
Salida: <raiz>/assets/models/characters/campanero/campanero_{idle,walk,toque,tanido,death}.fbx
"""
import bpy, sys, os, math, glob
from mathutils import Vector, Matrix, Quaternion

ARGV = sys.argv[sys.argv.index('--') + 1:]
ROOT = ARGV[0]
ONLY = ARGV[1:] or ['idle', 'walk', 'toque', 'tanido', 'death']
OUT = os.path.join(ROOT, 'assets/models/characters/campanero')
CHAR_FBX = glob.glob(os.path.join(OUT, 'source/tripo_convert_0865ecc9-*.fbx'))[0]
BELL_FBX = glob.glob(os.path.join(OUT, 'source/campana/*.fbx'))[0]
ANIM = os.path.join(ROOT, 'assets/models/animations/campanero')
SRC_FILES = {'idle': 'sad_idle.fbx', 'walk': 'injured_walk.fbx', 'toque': 'melee_downward.fbx', 'death': 'falling_back_death.fbx'}

# ---- campana ----
BELL_GRIP_Z = 0.72        # altura (0 boca .. 1 yugo) de la malla donde la mano la agarra
LIP_CLEARANCE = 0.05      # m entre el labio y el suelo en la pose de reposo
BELL_YAW_DEG = 90.0       # giro de la campana sobre la vertical (yugo de lado -> de frente al andar)

# ---- clips: fotogramas fuente (Mixamo) de las 8 muestras ----
TOQUE_SRC = [1, 5, 9, 13, 17, 21, 26, 30]   # 0-5 alzar (telegrafia), 6-7 golpe
DEATH_SRC = [1, 6, 12, 20, 28, 40, 58, 79]
HIP_XY = {'death': 0.2}
BELL_FOLLOW = {'idle': 0.0, 'walk': 0.0, 'toque': 0.75, 'tanido': 0.0, 'death': 1.0}
TANIDO_SWING_DEG = 48.0
P = 'mixamorig:'
BELL = 'CampaneroBell'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
scene = bpy.context.scene
PB = arm.pose.bones
MT3 = arm.matrix_world.to_3x3().normalized()
SRC = {}
for key in ('idle', 'walk', 'toque', 'death'):
    if key not in ONLY and not (key == 'idle' and ('tanido' in ONLY)):
        continue
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ANIM, SRC_FILES[key]))
    a = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE'][0]
    act = a.animation_data.action
    SRC[key] = dict(arm=a, act=act, f0=int(round(act.frame_range[0])), f1=int(round(act.frame_range[1])))
    # el resto de objetos del clip (malla de Y-bot) estorba al exportar: se borra
    for o in [o for o in bpy.data.objects if o not in before and o.type != 'ARMATURE']:
        bpy.data.objects.remove(o, do_unlink=True)
arm.animation_data_create()
arm.animation_data.action = None


def update():
    bpy.context.view_layer.update()


def world_z(o, n):
    update()
    return (o.matrix_world @ o.data.bones[P + n].head_local).z


def src_rot(S, n, rest3):
    """Rotacion absoluta (espacio armature destino) del hueso n segun el frame actual de la fuente S."""
    sa = S['arm']
    sp = sa.pose.bones.get(P + n); sb = sa.data.bones.get(P + n)
    MS3 = sa.matrix_world.to_3x3().normalized()
    R_delta = sp.matrix.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
    R_world = MS3 @ R_delta @ MS3.inverted()
    return (MT3.inverted() @ R_world @ MT3) @ rest3


for S in SRC.values():
    S['K'] = world_z(arm, 'Hips') / world_z(S['arm'], 'Hips')
    S['arm'].animation_data_create()
    S['arm'].animation_data.action = S['act']


def set_src_frame(S, x):
    fi = int(math.floor(x))
    scene.frame_set(fi, subframe=x - fi)
    update()


ORDER = [b.name[len(P):] for b in arm.data.bones]
HAND_REF = {}


def solve_pose(key, x, bell_follow=0.0, bell_swing=0.0, hip_xy=0.0, bell_swing_y=0.0):
    """Pose del armature en el frame x de la fuente `key`. bell_follow: fraccion del giro de la mano (respecto a HAND_REF)
    que sigue la campana; bell_swing: balanceo adelante/atras (grados) de la campana alrededor del agarre."""
    S = SRC[key]
    set_src_frame(S, x)
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    sa = S['arm']
    for n in ORDER:
        tb = arm.data.bones[P + n]
        rest3 = tb.matrix_local.to_3x3().normalized()
        if n == BELL:
            hand_rot = PB[P + 'RightHand'].matrix.to_3x3().normalized()
            R = Quaternion()
            if 'rot' in HAND_REF:
                d = (hand_rot @ HAND_REF['rot'].inverted()).to_quaternion()
                R = Quaternion().slerp(d, bell_follow)
            R_des = R.to_matrix() @ Matrix.Rotation(math.radians(bell_swing_y), 3, 'Y') @ Matrix.Rotation(math.radians(bell_swing), 3, 'X') @ rest3
            PB[P + n].matrix = Matrix.Translation(PB[P + n].matrix.translation.copy()) @ R_des.to_4x4()
            update()
            continue
        if sa.pose.bones.get(P + n) is None:
            continue
        R_des = src_rot(S, n, rest3)
        if n == 'Hips':
            sp = sa.pose.bones[P + n]; sb = sa.data.bones[P + n]
            dW = (sa.matrix_world @ sp.matrix).translation - (sa.matrix_world @ sb.matrix_local).translation
            if hip_xy:
                set_src_frame(S, S['f0']); update()
                d0 = (sa.matrix_world @ sa.pose.bones[P + n].matrix).translation - (sa.matrix_world @ sb.matrix_local).translation
                set_src_frame(S, x); update()
                dW = Vector((dW.x - d0.x, dW.y - d0.y, dW.z)) * 1.0
                dW = Vector((dW.x * hip_xy, dW.y * hip_xy, dW.z))
            else:
                dW = Vector((0, 0, dW.z))
            d = MT3.inverted() @ (dW * S['K'] * 100.0)
            head = tb.head_local + d
        else:
            head = PB[P + n].matrix.translation.copy()
        PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}


# ---- pose de referencia (idle, fotograma 0): agarre de la campana ----
solve_pose('idle', SRC['idle']['f0'])
hb = arm.data.bones[P + 'RightHand']
hp = PB[P + 'RightHand']
HAND_REF['rot'] = hp.matrix.to_3x3().normalized()
Mh_pose = hp.matrix.copy()
Mh_rest = hb.matrix_local.copy()
g_ref = Mh_pose.translation + (Mh_pose.to_3x3().normalized() @ Vector((0, hb.length * 0.5, 0)))
local_grip = Mh_pose.inverted() @ g_ref
rest_head = Mh_rest @ local_grip
g_world = arm.matrix_world @ g_ref
print('CAMPANERO K', {k: round(v['K'], 3) for k, v in SRC.items()}, 'agarre ref (m)', tuple(round(v, 3) for v in g_world))

# ---- campana: se hornea a metros de mundo y se emparenta al hueso auxiliar ----
pre = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=BELL_FBX)
new = [o for o in bpy.data.objects if o not in pre]
bell = [o for o in new if o.type == 'MESH']
assert bell, 'la campana no trae malla'
update()
for o in bell:
    o.parent = None
for o in new:
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
update()
for o in bell:
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
update()
pts = [v.co.copy() for o in bell for v in o.data.vertices]
mn = Vector((min(p[i] for p in pts) for i in range(3))); mx = Vector((max(p[i] for p in pts) for i in range(3)))
print('CAMPANERO campana bbox', tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
body = [p for p in pts if mn.z + 0.25 * (mx.z - mn.z) <= p.z <= mn.z + 0.5 * (mx.z - mn.z)]
cx = sum(p.x for p in body) / len(body); cy = sum(p.y for p in body) / len(body)
H = mx.z - mn.z
grip_local = Vector((cx, cy, mn.z + BELL_GRIP_Z * H))
BELL_SCALE = (g_world.z - LIP_CLEARANCE) / (BELL_GRIP_Z * H)
print('CAMPANERO campana alto %.3f m (escala %.3f), eje en (%.3f, %.3f), labio a %.3f del suelo' % (H * BELL_SCALE, BELL_SCALE, cx, cy, LIP_CLEARANCE))

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones.new(P + BELL)
eb.head = rest_head
eb.tail = rest_head + Vector((0, 0, 5.0))
eb.roll = 0.0
eb.parent = arm.data.edit_bones[P + 'RightHand']
eb.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')
update()
ORDER = [b.name[len(P):] for b in arm.data.bones]
sb_ = arm.data.bones[P + BELL]
rest_head_w = arm.matrix_world @ rest_head
W = (Matrix.Translation(rest_head_w) @ Matrix.Scale(BELL_SCALE, 4) @ Matrix.Rotation(math.radians(BELL_YAW_DEG), 4, 'Z')
     @ Matrix.Translation(-grip_local))
parent_inv = (arm.matrix_world @ sb_.matrix_local @ Matrix.Translation((0, sb_.length, 0))).inverted()
for o in bell:
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = P + BELL
    o.matrix_parent_inverse = parent_inv
    o.matrix_basis = W @ o.matrix_world
update()


def apply_pose(d):
    for pb in PB:
        l, q, s_ = d[pb.name]
        pb.location = l; pb.rotation_quaternion = q; pb.scale = s_


def all_points():
    """Todos los vertices (cuerpo + campana) en mundo, con la pose actual."""
    update()
    ev = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in meshes + bell:
        eo = o.evaluated_get(ev)
        m = eo.matrix_world
        out += [m @ v.co for v in eo.data.vertices]
    return out


def report(tag, d):
    apply_pose(d)
    p = all_points()
    lo = Vector((min(v[i] for v in p) for i in range(3))); hi = Vector((max(v[i] for v in p) for i in range(3)))
    print('CAMPANERO %s bbox %s .. %s' % (tag, tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi)))


# ---- clips ----
def loop_poses(key, frames, **kw):
    poses = [solve_pose(key, x, **kw) for x in frames]
    return poses + [poses[0]]


def hold_poses(poses):
    return poses + [poses[-1]]


CLIPS = {}
if 'idle' in ONLY:
    s = SRC['idle']
    CLIPS['idle'] = loop_poses('idle', [s['f0'] + i * (s['f1'] - s['f0']) / 8.0 for i in range(8)], bell_follow=BELL_FOLLOW['idle'])
if 'walk' in ONLY:
    s = SRC['walk']
    CLIPS['walk'] = loop_poses('walk', [s['f0'] + i * (s['f1'] - s['f0']) / 8.0 for i in range(8)], bell_follow=BELL_FOLLOW['walk'])
if 'toque' in ONLY:
    CLIPS['toque'] = hold_poses([solve_pose('toque', x, bell_follow=BELL_FOLLOW['toque']) for x in TOQUE_SRC])
if 'death' in ONLY:
    CLIPS['death'] = hold_poses([solve_pose('death', x, bell_follow=BELL_FOLLOW['death'], hip_xy=HIP_XY['death']) for x in DEATH_SRC])
if 'tanido' in ONLY:
    s = SRC['idle']
    poses = []
    for i in range(8):
        t = i / 7.0
        env = 1.0 - 0.55 * t   # sale fuerte y se amortigua
        a = t * math.pi * 1.6
        # balanceo conico (adelante/atras y de lado) para que se lea desde cualquier direccion
        poses.append(solve_pose('idle', s['f0'], bell_follow=0.0, bell_swing=-TANIDO_SWING_DEG * math.cos(a) * env,
                                bell_swing_y=0.8 * TANIDO_SWING_DEG * math.sin(a) * env))
    CLIPS['tanido'] = hold_poses(poses)

for k, v in CLIPS.items():
    report(k + '0', v[0]); report(k + 'N', v[7])


def add_bounds_helper(all_poses):
    """El lab encuadra cada clip por separado: un mesh de triangulos degenerados (area 0) con los extremos de todos los
    fotogramas de todos los clips da a todos el mismo centro y escala (como build_abanderado.py)."""
    pts_ = []
    for d in all_poses:
        apply_pose(d)
        p = all_points()
        for ax in range(3):
            pts_.append(min(p, key=lambda v: v[ax])); pts_.append(max(p, key=lambda v: v[ax]))
    me = bpy.data.meshes.new('CampaneroBounds')
    verts = []; faces = []
    for p in pts_:
        i = len(verts); verts += [tuple(p)] * 3; faces.append((i, i + 1, i + 2))
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new('CampaneroBounds', me)
    scene.collection.objects.link(ob)
    return ob


def export_clip(name, poses):
    act = bpy.data.actions.new('campanero_' + name)
    act.use_fake_user = True
    arm.animation_data.action = act
    for i, d in enumerate(poses):
        for pb in PB:
            l, q, s = d[pb.name]
            pb.location = l; pb.rotation_quaternion = q; pb.scale = s
            pb.keyframe_insert('location', frame=i)
            pb.keyframe_insert('rotation_quaternion', frame=i)
            pb.keyframe_insert('scale', frame=i)
    act.frame_range = (0, len(poses) - 1)
    scene.name = 'campanero_' + name
    scene.render.fps = 24
    scene.frame_start = 0
    scene.frame_end = len(poses) - 1
    bpy.ops.object.select_all(action='DESELECT')
    for o in [arm] + meshes + bell + [bounds]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(OUT, 'campanero_' + name + '.fbx')
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=False, add_leaf_bones=False, path_mode='COPY', embed_textures=True,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0, mesh_smooth_type='FACE')
    print('EXPORTED', path)


# Los limites comunes salen de TODOS los clips: con `ONLY` parcial el encuadre depende de lo construido; para el definitivo
# se construyen todos de una vez.
bounds = add_bounds_helper([p for v in CLIPS.values() for p in v])
for name, poses in CLIPS.items():
    export_clip(name, poses)
