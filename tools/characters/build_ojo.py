"""Construye los tres clips del Ojo del Tribunal (inquisidor bajo y gordo, farol en lugar de cabeza):
ojo_walk.fbx (andar en el sitio), ojo_look.fbx (mirar: bucle de respiracion) y ojo_sentence.fbx (sentenciar).

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_ojo.py -- <raiz_worktree>

Entradas:
  - cuerpo: ojo/source/tripo_convert_ed4d249d-*.fbx (rig Mixamo, T-pose, sin animacion).
  - andar generico assets/models/animations/walk/walk_normal.fbx (cadera en el sitio), transferido por delta de
    rotacion respecto al reposo de cada hueso (como build_cireneo_v2.py, con TODOS los huesos).
  - CABEZA (opcional): cualquier FBX en ojo/source/cabeza/. Si existe se importa, se escala/orienta con las
    constantes HEAD_* de abajo y se emparenta al hueso mixamorig:RightHand; si no, los clips salen SIN cabeza.
    La variable de entorno OJO_HEAD_FBX fuerza otro FBX (solo para pruebas de la ruta de codigo).
En los tres clips el brazo derecho va extendido hacia delante (la cabeza en la mano, como quien alumbra con un
farol); el izquierdo sigue el andar. Salida: <raiz>/assets/models/characters/ojo/ojo_{walk,look,sentence}.fbx
"""
import bpy, sys, os, math, glob
from mathutils import Vector, Matrix

ROOT = sys.argv[sys.argv.index('--') + 1]
OUT = os.path.join(ROOT, 'assets/models/characters/ojo')
CHAR_FBX = glob.glob(os.path.join(OUT, 'source/tripo_convert_ed4d249d-*.fbx'))[0]
HEAD_DIR = os.path.join(OUT, 'source/cabeza')
WALK_FBX = os.path.join(ROOT, 'assets/models/animations/walk/walk_normal.fbx')
if not os.path.exists(WALK_FBX):
    WALK_FBX = 'C:/codexlocal/dungeonds/assets/models/animations/walk/walk_normal.fbx'

# ---- ajustes del cuerpo gordo (andar) ----
WALK_FRAMES = 40        # 32 frames de Mixamo repartidos en 40 (paso algo mas pesado), +1 de cierre
ARM_OPEN_DEG = 22.0     # abduccion del brazo IZQUIERDO para librar barriga y tunica
FOREARM_OPEN_DEG = 4.0
LEG_OPEN_DEG = 5.0      # separacion de piernas para que los pies no se crucen
BOB_K = 0.8             # fraccion del rebote vertical de cadera
WADDLE_DEG = 3.0        # balanceo de cadera (roll) por ciclo, contrarrestado en la columna

# ---- brazo derecho extendido (comun a los tres clips) ----
ARM_FWD_DEG = 84.0      # giro del brazo derecho sobre la vertical: 90 = justo hacia delante; algo menos = un pelin hacia fuera
ARM_BASE_LIFT_DEG = 6.0 # elevacion fija del brazo (la cabeza queda a la altura del pecho/hombro)

# ---- look: respiracion / balanceo leve (bucle de 8 claves) ----
LOOK_FRAMES = 8
LOOK_SPINE_DEG = 2.0    # cabeceo del torso
LOOK_LIFT_DEG = 4.0     # sube y baja de la cabeza (brazo), con algo de retraso sobre el torso
LOOK_BOB_M = 0.006      # subida de cadera (m)

# ---- sentence: la cabeza se alza al soltar el haz y vuelve (8 claves + cierre; el juego usa 6) ----
SENT_CURVE = (0.0, 0.3, 0.8, 1.0, 1.0, 0.7, 0.35, 0.1, 0.0)
SENT_LIFT_DEG = 38.0    # elevacion extra de la cabeza en el pico
SENT_LEAN_DEG = -8.0    # el torso se echa hacia atras (contrapeso)
SENT_BOB_M = 0.015

# ---- cabeza en la mano (solo si existe un FBX en source/cabeza/) ----
HEAD_HEIGHT_M = 0.255           # cabeza nueva al 150 % del tamaño anterior (0,17 m)
HEAD_ROT_DEG = (0.0, 0.0, -ARM_FWD_DEG)  # Euler XYZ en el T-pose (brazo a -X); la cabeza (cara a -Y) gira con el brazo y acaba mirando hacia delante
HEAD_OFFSET_M = (-0.045, 0.0, 0.03)  # la argolla (arriba del craneo) queda dentro del puño y asoma por arriba; la cabeza cuelga debajo
HEAD_GRIP = 'top'               # punto del FBX de la cabeza que va a la mano: 'top' (argolla) o 'center'
HEAD_BONE = 'RightHand'
# boca de la cabeza: punto (fraccion de la caja: x centro, y 0 = frente de la cara/-Y, z desde abajo) donde se crea el hueso
# auxiliar 'OjoMouth' (hijo de la mano) que usa el lab como muzzle del haz
MOUTH_FRAC = (0.5, 0.0, 0.30)
MOUTH_BONE = 'OjoMouth'

# puño: giro acumulado (grados) de cada falange sobre el eje Y del T-pose (dedos a -X; negativo = hacia la palma, abajo)
FIST_CURL_DEG = {'1': 80.0, '2': 160.0, '3': 215.0}   # falanges 1-3 de indice, corazon, anular y menique
THUMB_CURL_DEG = {'1': 25.0, '2': 55.0, '3': 85.0}    # el pulgar se cierra por encima de los demas dedos
THUMB_ROLL_DEG = 0.0                                  # giro del pulgar sobre su propio eje (ajuste fino)
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
print('OJO hips z new=%.3f src=%.3f k=%.4f' % (world_z(arm, 'Hips'), world_z(src_arm, 'Hips'), K))
f0, f1 = int(round(src_act.frame_range[0])), int(round(src_act.frame_range[1]))
src_arm.animation_data_create()
src_arm.animation_data.action = src_act
arm.animation_data_create()
arm.animation_data.action = None
ORDER = [b.name[len(P):] for b in arm.data.bones]   # padres antes que hijos
LEFT_RIGHT = {'Left': 1.0, 'Right': -1.0}
RIGHT_ARM_CHAIN = set(b.name[len(P):] for b in arm.data.bones['mixamorig:RightArm'].children_recursive) | {'RightArm'}
UPPER = set(b.name[len(P):] for b in arm.data.bones['mixamorig:Spine1'].children_recursive)   # torso (sin Spine1)


def sample(x, bob_m=0.0, spine_deg=0.0, lift_deg=0.0, walk_bob=True):
    """Pose del andar en el frame (fraccional) x con el brazo derecho extendido hacia delante;
    devuelve {hueso: (loc, rotq, scale)}. bob_m: subida extra de cadera; spine_deg: cabeceo del torso (+ = hacia
    delante); lift_deg: elevacion extra del brazo derecho."""
    fi = int(math.floor(x)); sub = x - fi
    scene.frame_set(fi, subframe=sub)
    update()
    ph = (x - f0) / (f1 - f0) * 2 * math.pi      # fase del ciclo 0..2pi
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    E_up = Matrix.Rotation(math.radians(spine_deg), 3, 'X')     # cabeceo del torso (todo lo que cuelga de Spine1)
    for n in ORDER:
        sp = SPB.get(P + n); sb = src_arm.data.bones.get(P + n); tb = arm.data.bones[P + n]
        if sp is None:
            continue
        rest3 = tb.matrix_local.to_3x3().normalized()
        if n in RIGHT_ARM_CHAIN:
            # brazo derecho rigido hacia delante: giro sobre la vertical (T-pose -> hacia -Y) y elevacion sobre X
            curl = 0.0
            if n.startswith('RightHand') and n[-1] in '123':
                curl = (THUMB_CURL_DEG if 'Thumb' in n else FIST_CURL_DEG)[n[-1]]
            R_des = (Matrix.Rotation(-math.radians(ARM_BASE_LIFT_DEG + lift_deg), 3, 'X')
                     @ Matrix.Rotation(math.radians(ARM_FWD_DEG), 3, 'Z')
                     @ Matrix.Rotation(-math.radians(curl), 3, 'Y') @ rest3)
        else:
            # delta de rotacion respecto al reposo, llevado a espacio de mundo: los dos armatures tienen ejes
            # de armature distintos (origen Y arriba, destino Z arriba), asi que se pasa por el mundo
            R_delta = sp.matrix.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
            R_world = MS3 @ R_delta @ MS3.inverted()
            R_des = (MT3.inverted() @ R_world @ MT3) @ rest3
            side = LEFT_RIGHT.get(n[:4] if n.startswith('Left') else (n[:5] if n.startswith('Right') else ''), 0.0)
            # espacio de armature del destino: Z arriba, mira a -Y; brazos y piernas cuelgan hacia -Z, abrir = girar sobre Y
            if n in ('LeftArm', 'LeftForeArm'):
                deg = ARM_OPEN_DEG if n == 'LeftArm' else FOREARM_OPEN_DEG
                R_des = Matrix.Rotation(-math.radians(deg) * side, 3, 'Y') @ R_des
            elif n in ('LeftUpLeg', 'RightUpLeg'):
                R_des = Matrix.Rotation(-math.radians(LEG_OPEN_DEG) * side, 3, 'Y') @ R_des
            elif n == 'Hips':
                R_des = Matrix.Rotation(math.radians(WADDLE_DEG) * math.sin(ph), 3, 'Y') @ R_des
            elif n == 'Spine1':
                R_des = Matrix.Rotation(-math.radians(WADDLE_DEG) * math.sin(ph), 3, 'Y') @ R_des
        if n in UPPER or n in ('Spine1',):
            R_des = E_up @ R_des
        if n == 'Hips':
            # cadera en el sitio: solo rebote vertical (Z de mundo) del andar, escalado a la altura del destino
            dz = ((src_arm.matrix_world @ sp.matrix).translation.z - (src_arm.matrix_world @ sb.matrix_local).translation.z)
            dz = dz * K * BOB_K if walk_bob else 0.0
            d = MT3.inverted() @ Vector((0, 0, (dz + bob_m) * 100.0))  # m -> cm del armature
            head = tb.head_local + d
        else:
            head = PB[P + n].matrix.translation.copy()
        PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}


# ---- cabeza opcional ----
HEAD_OBJS = []
head_candidates = sorted(glob.glob(os.path.join(HEAD_DIR, '*.fbx')) + glob.glob(os.path.join(HEAD_DIR, '*.FBX')))
preferred_head = os.path.join(HEAD_DIR, 'tripo_convert_5f17753f-45e7-4137-b616-5fe4530a11f8.fbx')
head_fbx = os.environ.get('OJO_HEAD_FBX') or (preferred_head if os.path.isfile(preferred_head) else (head_candidates or [None])[0])
if head_fbx:
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=head_fbx)
    new = [o for o in bpy.data.objects if o not in pre]
    for o in new:                       # la cabeza llega sola: fuera de cualquier armature/padre que traiga el FBX
        if o.type == 'ARMATURE':
            print('OJO head FBX trae armature; se ignora', o.name)
    hmeshes = [o for o in new if o.type == 'MESH']
    for o in hmeshes:
        o.parent = None
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    update()
    pts = [o.matrix_world @ v.co for o in hmeshes for v in o.data.vertices]
    mn = Vector((min(p[i] for p in pts) for i in range(3))); mx = Vector((max(p[i] for p in pts) for i in range(3)))
    height = mx.z - mn.z
    s = HEAD_HEIGHT_M / height
    grip_local = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mx.z if HEAD_GRIP == 'top' else (mn.z + mx.z) / 2))
    hb = arm.data.bones[P + HEAD_BONE]
    hand_pos = arm.matrix_world @ hb.head_local
    Rm = Matrix.Rotation(math.radians(HEAD_ROT_DEG[2]), 4, 'Z') @ Matrix.Rotation(math.radians(HEAD_ROT_DEG[1]), 4, 'Y') @ Matrix.Rotation(math.radians(HEAD_ROT_DEG[0]), 4, 'X')
    # mundo de la cabeza: escala s, rota alrededor del punto de agarre y lleva ese punto a la mano
    W = Matrix.Translation(hand_pos + Vector(HEAD_OFFSET_M)) @ Rm @ Matrix.Scale(s, 4) @ Matrix.Translation(-grip_local)
    parent_inv = (arm.matrix_world @ hb.matrix_local @ Matrix.Translation((0, hb.length, 0))).inverted()
    for o in hmeshes:
        o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = P + HEAD_BONE
        o.matrix_parent_inverse = parent_inv
        o.matrix_basis = W @ o.matrix_world
    update()
    HEAD_OBJS = hmeshes
    # hueso auxiliar en la boca (mundo = W @ punto local de la caja)
    mouth_local = Vector((mn.x + (mx.x - mn.x) * MOUTH_FRAC[0], mn.y + (mx.y - mn.y) * MOUTH_FRAC[1], mn.z + (mx.z - mn.z) * MOUTH_FRAC[2]))
    mouth_arm = arm.matrix_world.inverted() @ (W @ mouth_local)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones.new(P + MOUTH_BONE)
    eb.head = mouth_arm
    eb.tail = mouth_arm + Vector((0, -2.0, 0))   # 2 cm hacia delante (cm del armature)
    eb.parent = arm.data.edit_bones[P + HEAD_BONE]
    eb.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    print('OJO boca en armature', tuple(round(v, 2) for v in mouth_arm))
    print('OJO cabeza pegada: %s (alto %.3f m -> %.3f m, escala %.4f)' % (os.path.basename(head_fbx), height, HEAD_HEIGHT_M, s))
else:
    print('OJO SIN CABEZA: no hay FBX en %s; los clips salen sin ella' % HEAD_DIR)


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
    for o in [arm] + meshes + HEAD_OBJS:
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


def foot_gap(x):
    """Separacion en Y entre los pies del andar en x (para elegir la pose de pies juntos del look/sentence)."""
    scene.frame_set(int(math.floor(x)), subframe=x - math.floor(x))
    update()
    l = src_arm.matrix_world @ SPB[P + 'LeftFoot'].head
    r = src_arm.matrix_world @ SPB[P + 'RightFoot'].head
    return math.hypot(l.x - r.x, l.y - r.y)    # distancia horizontal en mundo (Z arriba)


# 1) andar
poses = [sample(f0 + i * (f1 - f0) / WALK_FRAMES) for i in range(WALK_FRAMES + 1)]
poses[-1] = poses[0]            # cierre exacto del ciclo
export_clip('ojo_walk', poses)

# 2) pose de pies juntos (cruce de piernas del andar) como base de look y sentence
cands = [f0 + i * (f1 - f0) / 64.0 for i in range(64)]
X_STAND = min(cands, key=foot_gap)
print('OJO X_STAND frame %.2f gap %.4f' % (X_STAND, foot_gap(X_STAND)))

# 3) look: bucle de respiracion
look = []
for k in range(LOOK_FRAMES):
    ph = 2 * math.pi * k / LOOK_FRAMES
    look.append(sample(X_STAND, bob_m=LOOK_BOB_M * (1 + math.sin(ph)) / 2, spine_deg=LOOK_SPINE_DEG * math.sin(ph),
                       lift_deg=LOOK_LIFT_DEG * math.sin(ph - 0.7), walk_bob=False))
look.append(look[0])
export_clip('ojo_look', look)

# 4) sentence: la cabeza se alza y vuelve
sent = []
for c in SENT_CURVE:
    sent.append(sample(X_STAND, bob_m=SENT_BOB_M * c, spine_deg=SENT_LEAN_DEG * c, lift_deg=SENT_LIFT_DEG * c, walk_bob=False))
export_clip('ojo_sentence', sent)
