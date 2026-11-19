"""[derivado de build_abanderado.py] Construye los dos clips del Abanderado (jefe invocador, cabizbajo, estandarte como baston):
abanderado_walk.fbx  (Sad Walk de Mixamo en el sitio, bucle) y
abanderado_point.fbx (gesto generado por programa: levanta la cabeza y adelanta el asta hacia el jugador).

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_abanderado.py -- <raiz_worktree>

Entradas:
  - cuerpo: abanderado/source/tripo_convert_6e3a96b5-*.fbx (rig Mixamo, T-pose, sin animacion).
  - estandarte: abanderado/source/estandarte/*.fbx (malla sin rig; asta de 1,0 de alto con la bandera bajo el travesano).
  - andar: assets/models/animations/walk/sad_walk.fbx (mismo esqueleto Y-bot que walk_normal), transferido por delta de
    rotacion respecto al reposo de cada hueso (como build_ojo.py), cadera en el sitio.
El brazo derecho (el del asta) queda congelado en la pose del andar con los pies juntos; el asta cuelga de un hueso
auxiliar 'mixamorig:AbanderadoStaff' (hijo de la mano, en el punto de agarre) cuya orientacion se fija en espacio de
armature: vertical en el andar, inclinada hacia delante en el gesto. Asi el asta no se balancea con la muneca.
Salida: <raiz>/assets/models/characters/abanderado/abanderado_{walk,point}.fbx
"""
# ----------------------------------------------------------------------------------------------------------------
# build_abanderado_derrota.py: clip unico "abanderado_derrota" (~7 s, se usa con `una vez`).
# Narrativa: Inigo sostiene el estandarte, lo SUELTA (cae al suelo, nunca habia tocado el suelo), se derrumba de
# rodillas, baja la cabeza y GOLPEA EL SUELO con el puño IZQUIERDO 4 veces; se levanta y RECOGE el asta.
# Base: Mixamo "Plant A Plant" (assets/models/animations/derrota/plant_a_plant.fbx), ESPEJADO (el brazo que golpea
# es el izquierdo; el derecho es el del asta). Los golpes son procedurales sobre el brazo izquierdo.
# Uso: blender -b -P tools/characters/build_abanderado_derrota.py -- <raiz_worktree>   (DERROTA_TEST=1: solo capturas)
# Salida: <raiz>/assets/models/characters/abanderado/abanderado_derrota.fbx
# ----------------------------------------------------------------------------------------------------------------
import bpy, sys, os, math, glob
from mathutils import Vector, Matrix

ROOT = sys.argv[sys.argv.index('--') + 1]
OUT = os.path.join(ROOT, 'assets/models/characters/abanderado')
CHAR_FBX = glob.glob(os.path.join(OUT, 'source/tripo_convert_6e3a96b5-*.fbx'))[0]
STD_FBX = glob.glob(os.path.join(OUT, 'source/estandarte/*.fbx'))[0]
WALK_FBX = os.path.join(ROOT, 'assets/models/animations/walk/sad_walk.fbx')

# ---- andar ----
WALK_FRAMES = 48        # 44 intervalos de Mixamo repartidos en 48 (multiplo de 8) + 1 de cierre
LEG_OPEN_DEG = 3.0      # separacion de piernas
BOB_K = 1.0             # fraccion del rebote vertical de cadera

# ---- brazo del asta (derecho), congelado ----
ARM_FWD_DEG = 10.0      # adelanta el brazo entero (giro sobre X; + = hacia delante)
ELBOW_FWD_DEG = 14.0    # flexion extra del codo (antebrazo + mano)
ARM_OPEN_DEG = 16.0     # separa el brazo del cuerpo (el estandarte queda al costado, no tapa el torso de frente)
GRIP_ALONG = 0.55       # punto de agarre: fraccion del hueso mano (muneca -> nudillos)
GRIP_OFFSET_CM = (0.0, 0.0, 0.0)   # ajuste fino del agarre en armature (cm)

# ---- estandarte ----
STAFF_SCALE = 0.92      # el asta mide 1,0 en el FBX; el cuerpo mide ~0,92 (con el pelo). Mas largo no cabe en la celda de 60 px con el cuerpo a ~48 px
STAFF_TIP_ABOVE_GROUND = 0.0       # la contera toca el suelo en la pose del andar (m)
STAFF_WALK_TILT_DEG = 0.0          # + = la cabeza del asta hacia delante
STAFF = 'AbanderadoStaff'

# ---- gesto de apuntar ----
POINT_FRAMES = 10       # frames de la transicion (t con salida suave 0..1)
POINT_HOLD = 2          # frames extra con la pose sostenida: el lab toma 8 muestras y la ultima cae en la pose final
POINT_STAFF_TILT_DEG = 45.0   # inclinacion del asta desde la vertical, hacia delante (-Y)
POINT_ARM_FWD_DEG = 14.0      # el brazo entero sube hacia delante
POINT_ELBOW_FWD_DEG = 16.0
POINT_HEAD_UP_DEG = 38.0      # levanta la cabeza (cuello + cabeza)
POINT_SPINE_DEG = -10.0       # endereza la espalda (- = hacia atras)
P = 'mixamorig:'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=WALK_FBX)
src_arm = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE'][0]
src_act = src_arm.animation_data.action
scene = bpy.context.scene
PB = arm.pose.bones
MS3 = src_arm.matrix_world.to_3x3().normalized()
MT3 = arm.matrix_world.to_3x3().normalized()
SPB = src_arm.pose.bones


def update():
    bpy.context.view_layer.update()


def world_z(o, n):
    update()
    return (o.matrix_world @ o.data.bones[P + n].head_local).z


K = world_z(arm, 'Hips') / world_z(src_arm, 'Hips')
f0, f1 = int(round(src_act.frame_range[0])), int(round(src_act.frame_range[1]))
src_arm.animation_data_create()
src_arm.animation_data.action = src_act
arm.animation_data_create()
arm.animation_data.action = None
LEFT_RIGHT = {'Left': 1.0, 'Right': -1.0}
RIGHT_ARM_CHAIN = set(b.name[len(P):] for b in arm.data.bones['mixamorig:RightArm'].children_recursive) | {'RightArm'}
FOREARM_CHAIN = set(b.name[len(P):] for b in arm.data.bones['mixamorig:RightForeArm'].children_recursive) | {'RightForeArm'}
UPPER = set(b.name[len(P):] for b in arm.data.bones['mixamorig:Spine1'].children_recursive) | {'Spine1'}
HEADCH = set(b.name[len(P):] for b in arm.data.bones['mixamorig:Neck'].children_recursive) | {'Neck'}


def src_rot(n, rest3):
    """Rotacion absoluta (espacio armature destino) del hueso n segun el frame actual del andar."""
    sp = SPB.get(P + n); sb = src_arm.data.bones.get(P + n)
    R_delta = sp.matrix.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
    R_world = MS3 @ R_delta @ MS3.inverted()
    return (MT3.inverted() @ R_world @ MT3) @ rest3


def foot_gap(x):
    scene.frame_set(int(math.floor(x)), subframe=x - math.floor(x))
    update()
    l = src_arm.matrix_world @ SPB[P + 'LeftFoot'].head
    r = src_arm.matrix_world @ SPB[P + 'RightFoot'].head
    return math.hypot(l.x - r.x, l.y - r.y)


cands = [f0 + i * (f1 - f0) / 64.0 for i in range(64)]
X_STAND = min(cands, key=foot_gap)
print('ABANDERADO X_STAND frame %.2f gap %.4f' % (X_STAND, foot_gap(X_STAND)))

# cache del brazo derecho congelado en la pose X_STAND
scene.frame_set(int(math.floor(X_STAND)), subframe=X_STAND - math.floor(X_STAND))
update()
ARM_BASE = {}
for n in RIGHT_ARM_CHAIN:
    if SPB.get(P + n) is not None:
        ARM_BASE[n] = src_rot(n, arm.data.bones[P + n].matrix_local.to_3x3().normalized())

ORDER = None


def rot_x(deg):
    return Matrix.Rotation(math.radians(deg), 3, 'X')


def solve_pose(x, arm_fwd, elbow_fwd, spine_deg, head_up, walk_bob, staff_tilt, bob_m=0.0):
    """Coloca el armature en la pose del andar en el frame x con los parametros del gesto."""
    fi = int(math.floor(x)); sub = x - fi
    scene.frame_set(fi, subframe=sub)
    update()
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    E_up = rot_x(spine_deg)
    E_head = rot_x(-head_up)
    E_arm = rot_x(-arm_fwd)
    E_elb = rot_x(-elbow_fwd)
    E_open = Matrix.Rotation(math.radians(ARM_OPEN_DEG), 3, 'Y')
    for n in ORDER:
        tb = arm.data.bones[P + n]
        rest3 = tb.matrix_local.to_3x3().normalized()
        if n == STAFF:
            R_des = rot_x(staff_tilt) @ rest3
            PB[P + n].matrix = Matrix.Translation(PB[P + n].matrix.translation.copy()) @ R_des.to_4x4()
            update()
            continue
        if SPB.get(P + n) is None:
            continue
        if n in RIGHT_ARM_CHAIN:
            R_des = E_open @ E_arm @ ARM_BASE[n]
            if n in FOREARM_CHAIN:
                R_des = E_elb @ R_des
        else:
            R_des = src_rot(n, rest3)
            side = LEFT_RIGHT.get(n[:4] if n.startswith('Left') else (n[:5] if n.startswith('Right') else ''), 0.0)
            if n in ('LeftUpLeg', 'RightUpLeg'):
                R_des = Matrix.Rotation(-math.radians(LEG_OPEN_DEG) * side, 3, 'Y') @ R_des
        if n in UPPER:
            R_des = E_up @ R_des
        if n in HEADCH:
            R_des = E_head @ R_des
        if n == 'Hips':
            sp = SPB[P + n]; sb = src_arm.data.bones[P + n]
            dz = ((src_arm.matrix_world @ sp.matrix).translation.z - (src_arm.matrix_world @ sb.matrix_local).translation.z)
            dz = dz * K * BOB_K if walk_bob else 0.0
            d = MT3.inverted() @ Vector((0, 0, (dz + bob_m) * 100.0))
            head = tb.head_local + d
        else:
            head = PB[P + n].matrix.translation.copy()
        PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}


ORDER = [b.name[len(P):] for b in arm.data.bones]
# pose de referencia del andar (sin hueso del asta todavia)
solve_pose(X_STAND, ARM_FWD_DEG, ELBOW_FWD_DEG, 0.0, 0.0, False, 0.0)
hb = arm.data.bones[P + 'RightHand']
hp = PB[P + 'RightHand']
Mh_pose = hp.matrix.copy()                       # armature (cm)
Mh_rest = hb.matrix_local.copy()
g_ref = Mh_pose.translation + (Mh_pose.to_3x3().normalized() @ Vector((0, hb.length * GRIP_ALONG, 0))) + Vector(GRIP_OFFSET_CM)
local_grip = Mh_pose.inverted() @ g_ref
rest_head = Mh_rest @ local_grip                  # cabeza del hueso del asta en reposo (armature, cm)
g_world = arm.matrix_world @ g_ref
print('ABANDERADO agarre ref (m, mundo)', tuple(round(v, 3) for v in g_world))

# ---- estandarte: se hornea a metros de mundo y se emparenta al hueso auxiliar ----
pre = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=STD_FBX)
new = [o for o in bpy.data.objects if o not in pre]
std = [o for o in new if o.type == 'MESH']
assert std, 'el estandarte no trae malla'
update()
for o in std:
    o.parent = None
for o in new:
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
update()
for o in std:
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
update()
pts = [v.co.copy() for o in std for v in o.data.vertices]
mn = Vector((min(p[i] for p in pts) for i in range(3))); mx = Vector((max(p[i] for p in pts) for i in range(3)))
print('ABANDERADO estandarte bbox', tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
# contera a STAFF_TIP_ABOVE_GROUND del suelo con el agarre en la mano de referencia
grip_z_local = (g_world.z - STAFF_TIP_ABOVE_GROUND) / STAFF_SCALE + mn.z
grip_local = Vector((cx, cy, grip_z_local))
print('ABANDERADO agarre a %.2f de la contera (asta de %.2f)' % ((grip_z_local - mn.z) * STAFF_SCALE, (mx.z - mn.z) * STAFF_SCALE))

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones.new(P + STAFF)
eb.head = rest_head
eb.tail = rest_head + Vector((0, 0, 5.0))
eb.roll = 0.0
eb.parent = arm.data.edit_bones[P + 'RightHand']
eb.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')
update()
ORDER = [b.name[len(P):] for b in arm.data.bones]
sb_ = arm.data.bones[P + STAFF]
rest_head_w = arm.matrix_world @ rest_head
W = Matrix.Translation(rest_head_w) @ Matrix.Scale(STAFF_SCALE, 4) @ Matrix.Translation(-grip_local)
parent_inv = (arm.matrix_world @ sb_.matrix_local @ Matrix.Translation((0, sb_.length, 0))).inverted()
for o in std:
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = P + STAFF
    o.matrix_parent_inverse = parent_inv
    o.matrix_basis = W @ o.matrix_world
update()


def staff_axis():
    """(punto mas bajo, punto mas alto) del asta en mundo, con la pose actual."""
    update()
    ev = bpy.context.evaluated_depsgraph_get()
    pts_w = []
    for o in std:
        eo = o.evaluated_get(ev)
        m = eo.matrix_world
        pts_w += [m @ v.co for v in eo.data.vertices]
    return min(pts_w, key=lambda p: p.z), max(pts_w, key=lambda p: p.z)


def pole_ends():
    """Extremos del asta (contera y punta) en mundo con la pose actual."""
    update()
    m = std[0].matrix_world
    return [m @ Vector((cx, cy, mn.z)), m @ Vector((cx, cy, mx.z))]


def apply_pose(d):
    for pb in PB:
        l, q, s_ = d[pb.name]
        pb.location = l; pb.rotation_quaternion = q; pb.scale = s_


def add_bounds_helper(all_poses):
    """El lab encuadra cada clip por separado segun sus puntos. Para que andar y apuntar tengan la MISMA escala y centro
    se anade a ambos un mesh de triangulos degenerados (area 0, invisibles) en los extremos del asta de todos los frames."""
    pts = []
    for d in all_poses:
        apply_pose(d)
        pts += pole_ends()
    me = bpy.data.meshes.new('AbanderadoBounds')
    verts = []; faces = []
    for p in pts:
        i = len(verts); verts += [tuple(p)] * 3; faces.append((i, i + 1, i + 2))
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new('AbanderadoBounds', me)
    scene.collection.objects.link(ob)
    return ob


def export_clip(name, poses):
    act = bpy.data.actions.new(name)
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
    scene.name = name
    scene.render.fps = 24
    scene.frame_start = 0
    scene.frame_end = len(poses) - 1
    bpy.ops.object.select_all(action='DESELECT')
    for o in [arm] + meshes + std + [bounds]:
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


def report(tag, d):
    for pb in PB:
        l, q, s = d[pb.name]
        pb.location = l; pb.rotation_quaternion = q; pb.scale = s
    lo, hi = staff_axis()
    h = arm.matrix_world @ PB[P + 'Head'].head
    print('ABANDERADO %s asta abajo=%s arriba=%s cabeza=%s' % (tag, tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi), tuple(round(v, 2) for v in h)))




# =====================================================================================================
# DERROTA
# =====================================================================================================
PLANT_FBX = os.path.join(ROOT, 'assets/models/animations/derrota/plant_a_plant.fbx')
TEST = os.environ.get('DERROTA_TEST')
BOW_NECK_DEG = float(os.environ.get('BOW_NECK', 25))   # cabeza lo mas cerca del suelo que permita la pose
BOW_HEAD_DEG = float(os.environ.get('BOW_HEAD', 10))
BOW_SPINE_DEG = float(os.environ.get('BOW_SPINE', 25))
PUNCH_ARM_DEG = float(os.environ.get('PUNCH_ARM', -135))   # giro del brazo izquierdo sobre el eje lateral (- = sube)
PUNCH_ELBOW_DEG = float(os.environ.get('PUNCH_ELBOW', -30))
STAFF_LIE_DEG = float(os.environ.get('STAFF_DIR', 20))    # direccion del asta caida: 0 = a la derecha del heroe, + hacia atras
STAFF_ROLL_DEG = float(os.environ.get('STAFF_ROLL', 70))
STAFF_R = 0.03                 # radio aprox. del asta (m) para que repose sobre el suelo
G_M = g_world.z - STAFF_TIP_ABOVE_GROUND   # contera -> punto de agarre del mesh (m)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=PLANT_FBX)
pl = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE'][0]
pl_act = pl.animation_data.action
pl.animation_data.action = pl_act
PPB = pl.pose.bones
PMS3 = pl.matrix_world.to_3x3().normalized()
update()
MWinv = arm.matrix_world.inverted()
MIR = Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, 1)))
K2 = None  # se fija tras leer la altura de cadera de pie del clip (frame 1)
SA = arm.matrix_world.to_scale()[0]


def opp(n):
    if n.startswith('Left'): return 'Right' + n[4:]
    if n.startswith('Right'): return 'Left' + n[5:]
    return n


def chain(b):
    return set(x.name[len(P):] for x in arm.data.bones[P + b].children_recursive) | {b}


LEFT_CHAIN = chain('LeftArm')
LEFT_FORE = chain('LeftForeArm')
NECKCH = chain('Neck')
HEADONLY = chain('Head')
SPINECH = chain('Spine1')


def rxw(deg):
    return Matrix.Rotation(math.radians(deg), 3, 'X')   # eje lateral en mundo


def pl_set(x):
    fi = int(math.floor(x))
    scene.frame_set(fi, subframe=x - fi)
    update()


def pl_hips_delta():
    cur = (pl.matrix_world @ PPB[P + 'Hips'].matrix).translation
    rest = (pl.matrix_world @ pl.data.bones[P + 'Hips'].matrix_local).translation
    return cur - rest


pl_set(1.0)
HIPS0 = pl_hips_delta()
K2 = world_z(arm, 'Hips') / (pl.matrix_world @ PPB[P + 'Hips'].matrix).translation.z   # el clip esta a otra escala que su reposo

print('DERROTA K2 %.3f SA %.4f G_M %.3f' % (K2, SA, G_M))


def grip_now():
    """Punto de agarre en la mano derecha del heroe (mundo, m)."""
    return arm.matrix_world @ (PB[P + 'RightHand'].matrix @ local_grip)


GA = {'L': 0.0, 'R': 0.0}      # giro extra de cada brazo para apoyar la mano en el suelo (se resuelve abajo)
RIGHT_CHAIN = chain('RightArm')


def gw_of(xs):
    if xs <= F_H:
        return smooth((xs - 55.0) / 30.0)
    return 1.0 - smooth((xs - 190.0) / 15.0)


def body_pose(xsrc, bow, punch, sway):
    """Pose del cuerpo con el clip Plant A Plant espejado en el frame fuente xsrc."""
    pl_set(xsrc)
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    dh = pl_hips_delta() - HIPS0
    for n in ORDER:
        if n == STAFF or PPB.get(P + opp(n)) is None:
            continue
        tb = arm.data.bones[P + n]
        rest3 = tb.matrix_local.to_3x3().normalized()
        o = opp(n)
        sp = PPB[P + o]; sb = pl.data.bones[P + o]
        Rd = sp.matrix.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
        Dw = PMS3 @ Rd @ PMS3.inverted()
        Dw = MIR @ Dw @ MIR
        if n in NECKCH: Dw = rxw(bow * BOW_NECK_DEG) @ Dw
        if n in HEADONLY: Dw = rxw(bow * BOW_HEAD_DEG) @ Dw
        if n in SPINECH: Dw = rxw(bow * BOW_SPINE_DEG + sway) @ Dw
        gw = gw_of(xsrc)
        if n in LEFT_CHAIN: Dw = rxw(GA['L'] * gw) @ Dw
        if n in RIGHT_CHAIN: Dw = rxw(GA['R'] * gw) @ Dw
        if n in LEFT_CHAIN and punch is not None:
            Dw = rxw(punch * PUNCH_ARM_DEG) @ Dw
            if n in LEFT_FORE:
                Dw = rxw(punch * PUNCH_ELBOW_DEG) @ Dw
        R_des = (MT3.inverted() @ Dw @ MT3) @ rest3
        if n == 'Hips':
            dv = Vector((-dh.x, dh.y, dh.z)) * K2
            head = tb.head_local + (MT3.inverted() @ dv) / SA
        else:
            head = PB[P + n].matrix.translation.copy()
        PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()


def staff_pose(C, u):
    """Asta con la contera en C (mundo, m) y el eje hacia u (unitario)."""
    sb = arm.data.bones[P + STAFF]
    rest3 = sb.matrix_local.to_3x3().normalized()
    Rw = Vector((0, 0, 1)).rotation_difference(u).to_matrix()
    Rw = Matrix.Rotation(math.radians(STAFF_ROLL_DEG) * (1.0 - u.z), 3, u) @ Rw   # tumbada: la tela se tiende en el suelo
    R_des = (MT3.inverted() @ Rw @ MT3) @ rest3
    head_w = Vector(C) + u * G_M
    PB[P + STAFF].matrix = Matrix.Translation(MWinv @ head_w) @ R_des.to_4x4()
    update()


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---- guion de fotogramas (24 fps) ----
N_INTRO, N_KNEEL, N_SETTLE, N_PUNCH, N_POST, N_RISE, N_END = 18, 34, 14, 14, 10, 28, 8
N_TOTAL = N_INTRO + N_KNEEL + N_SETTLE + 4 * N_PUNCH + N_POST + N_RISE + N_END
F_REST, F_H, F_RISE0, F_RISE1 = 1.0, 88.0, 190.0, 217.0
REL = 6                  # frame en que suelta el asta
FALL = 12                # duracion de la caida
I_SET0 = N_INTRO + N_KNEEL
I_PUN0 = I_SET0 + N_SETTLE
I_POST0 = I_PUN0 + 4 * N_PUNCH
I_RISE0 = I_POST0 + N_POST
I_END0 = I_RISE0 + N_RISE
PICK0, PICK1 = I_RISE0 - 2, I_RISE0 + 16


def plan(i):
    """-> (frame fuente, arco de cabeza 0..1, golpe 0..1 o None, vaiven)"""
    punch = None; bow = 0.0; sway = 0.0
    if i < N_INTRO:
        xs = F_REST + (10.0 - F_REST) * i / N_INTRO
    elif i < I_SET0:
        xs = 10.0 + (F_H - 10.0) * smooth((i - N_INTRO) / N_KNEEL)
        bow = 0.35 * smooth((i - N_INTRO - 12) / (N_KNEEL - 12))
    elif i < I_PUN0:
        xs = F_H
        bow = 0.35 + 0.65 * smooth((i - I_SET0) / N_SETTLE)
    elif i < I_POST0:
        xs = F_H; bow = 1.0
        j = (i - I_PUN0) % N_PUNCH
        k = (i - I_PUN0) // N_PUNCH
        if j <= 5:
            p0 = 0.0 if k == 0 else 0.25
            punch = p0 + (1.0 - p0) * smooth(j / 5.0)
        elif j == 6: punch = 0.45
        elif j <= 10: punch = 0.0
        else: punch = 0.25 * (j - 10) / 3.0
        sway = 1.6 * math.sin(i * 0.9)
    elif i < I_RISE0:
        xs = F_H; bow = 1.0
        sway = 1.2 * math.sin(i * 0.9)
    elif i < I_END0:
        t = (i - I_RISE0) / N_RISE
        xs = F_H + (F_RISE0 - F_H) * smooth(t * 3.0) if t < 0.33 else F_RISE0 + (F_RISE1 - F_RISE0) * smooth((t - 0.33) / 0.67)
        bow = 1.0 - smooth(t * 2.5)
    else:
        xs = F_RISE1
    return xs, bow, punch, sway


def lie_dir():
    a = math.radians(STAFF_LIE_DEG)
    return Vector((-math.cos(a), math.sin(a), 0.0))


# resolver el giro de brazos que apoya las muñecas en el suelo con el cuerpo encogido (F_H, cabeza abajo)
GROUND_Z = float(os.environ.get('GROUND_Z', 0.035))
best = {}
for a in range(-90, 31, 3):
    GA['L'] = GA['R'] = float(a)
    body_pose(F_H, 1.0, None, 0.0)
    for side, bn in (('L', 'LeftHand'), ('R', 'RightHand')):
        z = (arm.matrix_world @ PB[P + bn].head).z
        if side not in best or abs(z - GROUND_Z) < best[side][0]:
            best[side] = (abs(z - GROUND_Z), float(a), z)
GA['L'], GA['R'] = best['L'][1], best['R'][1]
print('DERROTA brazos al suelo', best)

# primera pasada: agarre de la mano en cada frame (para colocar el asta caida bajo la mano que la recoge)
HAND = {}
SOLVED = {}
for i in range(N_TOTAL):
    xs, bow, punch, sway = plan(i)
    body_pose(xs, bow, punch, sway)
    HAND[i] = grip_now()
    SOLVED[i] = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}
D = lie_dir()
H_PICK = HAND[PICK0]
C_LAND = Vector((H_PICK.x, H_PICK.y, 0.0)) - D * G_M
C_LAND.z = STAFF_R
C0 = Vector((HAND[REL].x, HAND[REL].y, 0.0))
print('DERROTA agarre en reposo', tuple(round(v, 3) for v in HAND[0]), 'C0', tuple(round(v, 3) for v in C0), 'C_LAND', tuple(round(v, 3) for v in C_LAND))


def staff_state(i):
    """-> (contera, eje)"""
    h = HAND[i]
    held = Vector((h.x, h.y, 0.0))
    up = Vector((0, 0, 1))
    if i < REL:
        return held, up
    if i < REL + FALL:
        t = (i - REL) / FALL
        th = (math.pi / 2) * (t * t)
        u = Vector((D.x * math.sin(th), D.y * math.sin(th), math.cos(th)))
        C = C0.lerp(C_LAND, t * t)
        return Vector((C.x, C.y, STAFF_R * (1 - u.z))), u
    if i < PICK0:
        return C_LAND.copy(), D.copy()
    s = smooth((i - PICK0) / float(PICK1 - PICK0))
    u = D.lerp(up, s).normalized()
    C = C_LAND.lerp(held, s)
    return Vector((C.x, C.y, STAFF_R * (1 - u.z))), u


def pose_frame(i):
    d = SOLVED[i]
    for pb in PB:
        l, q, s_ = d[pb.name]
        pb.location = l; pb.rotation_quaternion = q; pb.scale = s_
    update()
    C, u = staff_state(i)
    staff_pose(C, u)
    lo, _hi = staff_axis()
    if lo.z < 0.0:        # nada del asta ni de la tela bajo el suelo
        staff_pose(Vector((C.x, C.y, C.z - lo.z)), u)
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}


if TEST:
    # prueba minima (regla 11): metricas y capturas de unos pocos fotogramas
    frames = [int(v) for v in os.environ.get('TEST_FRAMES', '0,12,25,60,100,115,150,167').split(',')]
    SHOT = os.environ.get('SHOT_DIR')
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 540; scene.render.resolution_y = 540
    scene.display.shading.light = 'FLAT'; scene.world = bpy.data.worlds.new('w'); scene.world.color = (0.3, 0.3, 0.35); scene.display.shading.color_type = 'TEXTURE'
    cams = {}
    for name, loc, rot in (('front', (0, -5, 0.6), (math.pi / 2, 0, 0)), ('side', (5, 0, 0.6), (math.pi / 2, 0, math.pi / 2)),
                           ('top34', (3.5, -3.5, 3.5), (math.radians(55), 0, math.radians(45)))):
        cd = bpy.data.cameras.new(name); cd.type = 'ORTHO'; cd.ortho_scale = 1.8
        co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co)
        co.location = loc; co.rotation_euler = rot; cams[name] = co
    for o in list(bpy.data.objects):          # ocultar el esqueleto fuente y sus mallas
        if o.type == 'ARMATURE' and o is not arm:
            o.hide_render = True
        if o.type == 'MESH' and o.parent is not None and o.parent is not arm:
            o.hide_render = True
    for i in frames:
        pose_frame(i)
        lo, hi = staff_axis()
        wl = arm.matrix_world @ PB[P + 'LeftHand'].head; wr = arm.matrix_world @ PB[P + 'RightHand'].head
        hd = arm.matrix_world @ PB[P + 'Head'].head
        print('TESTF %d src %.1f contera %s punta %s | muneca I z=%.3f D z=%.3f | cabeza z=%.2f y=%.2f' % (
            i, plan(i)[0], tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi), wl.z, wr.z, hd.z, hd.y))
        if SHOT:
            for cn, co in cams.items():
                scene.camera = co
                scene.render.filepath = os.path.join(SHOT, 'f%03d_%s.png' % (i, cn))
                bpy.ops.render.render(write_still=True)
    sys.exit(0)

poses = [pose_frame(i) for i in range(N_TOTAL)]
report('derrota0', poses[0]); report('derrotaN', poses[-1])
bounds = add_bounds_helper(poses)
export_clip('abanderado_derrota', poses)
