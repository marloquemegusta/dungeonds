"""Construye los 4 FBX de un Exvoto de tier (bebe, parroco, monja) replicando build_exvoto.py.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_exvoto_tier.py -- <raiz_worktree> <personaje>

<personaje> es el nombre de la carpeta en assets/models/characters/ (exvoto_bebe, exvoto_parroco, exvoto_monja)
y el prefijo de las animaciones exportadas. Requiere rig Mixamo (mixamorig:*) de 65 huesos, el mismo del Exvoto.
Salidas: assets/models/characters/<personaje>/<personaje>_{pray_stand,pray_kneel,stand_up,walk}.fbx

Con --run-only (tercer argumento tras --) solo se construye <personaje>_run.fbx desde walk/running.fbx (Mixamo
«Running»), sin tocar los otros cuatro: es el clip de correr del Parroco (CHAR_EXVOTO_PARROCO_RUN, NitroFS).

Con --crawl-only solo se construye <personaje>_crawl.fbx desde crawl/crawling.fbx (Mixamo «Crawling», a gatas):
es el gateo del Bebe para los videos de lore (no va a la ROM). Brazos del propio clip, sin pose de rezo.
"""
import bpy, sys, os, math, glob
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = sys.argv[sys.argv.index('--') + 1]
PERSONAJE = sys.argv[sys.argv.index('--') + 2]
OUT = os.path.join(ROOT, 'assets/models/characters', PERSONAJE)
CHAR_FBX = glob.glob(os.path.join(OUT, 'source/tripo_convert_*.fbx'))[0]
ANIM = os.path.join(ROOT, 'assets/models/animations')
SRC_FILES = {
    'stand': os.path.join(ANIM, 'pray/pray_standing.fbx'),
    'kneel': os.path.join(ANIM, 'pray/pray_kneeling.fbx'),
    'k2s': os.path.join(ANIM, 'pray/pray_kneel_to_stand.fbx'),
    'walk': os.path.join(ANIM, 'walk/walk_normal.fbx'),
    'run': os.path.join(ANIM, 'walk/running.fbx'),
    'crawl': os.path.join(ANIM, 'crawl/crawling.fbx'),
}
RUN_ONLY = '--run-only' in sys.argv
CRAWL_ONLY = '--crawl-only' in sys.argv
if RUN_ONLY or CRAWL_ONLY:
    _solo = 'run' if RUN_ONLY else 'crawl'
    SRC_FILES = {k: v for k, v in SRC_FILES.items() if k in ('walk', _solo)}  # 'walk' fija la orientacion de referencia
else:
    del SRC_FILES['crawl']
FPS = 30
P = 'mixamorig:'

# ---- parametros ajustables (identicos al Exvoto) ----
STAND_UP_START = 138
STAND_UP_START_BLEND = 8
STAND_UP_ARMS_BLEND = 24
STAND_UP_BLEND = 10
WALK_FRAMES = 44
WALK_STRIDE = 0.8
WALK_SPINE_DAMP = 0.5
WALK_LEAN = {'Spine': 7, 'Spine1': 7, 'Spine2': 7, 'Neck': 12, 'Head': 12}
WALK_ARMS_FRAME = 1
RUN_FRAMES = 33              # fotogramas del ciclo de correr a 30 fps (el cierre repite el primero); se muestrea a 8 en el lab
RUN_LEAN = {}                # la inclinacion de la carrera ya viene en el clip de Mixamo
# Gateo: grados extra por hueso (positivo = inclina hacia delante, negativo = levanta). El Bebe tiene los brazos
# muy cortos: sin bajar el pecho las manos flotan. Hombros hacia abajo para apoyarlas y cabeza alzada para que
# la camara (picada) le vea la cara. Se puede probar otra pose con la variable de entorno CRAWL_LEAN.
CRAWL_LEAN = {'Spine': 22, 'Spine1': 12, 'LeftShoulder': -34, 'RightShoulder': -34, 'Neck': -56, 'Head': -50}
CRAWL_LEAN.update({k: float(v) for k, v in (x.split('=') for x in os.environ.get('CRAWL_LEAN', '').split(',') if x)})
HEAD_TILT = 0.0
ARM_BONES_KEYS = ('Shoulder', 'Arm', 'ForeArm', 'Hand')


def is_arm_bone(name):
    """Huesos del brazo (hombro, brazo, antebrazo, mano y dedos) de los dos lados."""
    short = name.replace(P, '')
    if not short.startswith(('Left', 'Right')):
        return False
    side_less = short.replace('Left', '').replace('Right', '')
    return side_less in ARM_BONES_KEYS or side_less.startswith('Hand')


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


def facing(o, left='mixamorig:LeftShoulder', right='mixamorig:RightShoulder'):
    """Direccion frontal desde la linea lateral de los hombros (up x lateral_derecha).
    Los dedos de los pies no valen: estos modelos Tripo los traen abiertos (Parroco 16 grados, Monja 63)."""
    update()
    lat = o.matrix_world @ o.data.bones[right].head_local - o.matrix_world @ o.data.bones[left].head_local
    lat = Vector((lat.x, lat.y, 0)).normalized()
    return Vector((-lat.y, lat.x, 0)).normalized()


_ft, _fs = facing(arm), facing(SRC['walk'])
print('FACING target', tuple(round(x, 2) for x in _ft), 'source', tuple(round(x, 2) for x in _fs))
F = Matrix(_fs.rotation_difference(_ft).to_matrix())

HIPS_K = (A_W @ arm.data.bones[P + 'Hips'].head_local).z / (SRC['walk'].matrix_world @ SRC['walk'].data.bones[P + 'Hips'].head_local).z
print('HIPS K (altura %s / altura Beta) = %.4f' % (PERSONAJE, HIPS_K))


def retarget_frame(src, frame, damp=None):
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
        short = n.replace(P, '')
        Rt_rest = A_RW @ tb.matrix_local.to_3x3().normalized()
        if is_arm_bone(n):
            # Los tier Tripo no comparten el reposo del Y-bot del Exvoto en el brazo: reposo a 22,5 / 53,8 /
            # 60,2 / 77,2 grados de diferencia en hombro/brazo/antebrazo/mano (el Bebe 9,9 / 7,2 / 5,2 / 2,8).
            # Trasladar el delta de mundo hereda ese desfase y acaba con las manos abiertas a la altura de la
            # cabeza. Se transfiere la DIRECCION del hueso en mundo (giro minimo que lleva la direccion de reposo
            # del destino a la direccion de pose del origen) y DESPUES el giro sobre ese mismo eje que alinea la
            # palma con la del origen: sin el, la mano lleva el roll del cuerpo (~152 grados en el antebrazo de la
            # Monja) y sale la palma del reves. Con los dos, direccion y palma quedan a 0 grados.
            axis = (F @ Rs_pose.col[1]).normalized()
            R0 = Rt_rest.col[1].normalized().rotation_difference(axis).to_matrix() @ Rt_rest
            z_src = (F @ Rs_pose.col[2]).normalized()
            z_now = R0.col[2].normalized()
            p_now = z_now - axis * z_now.dot(axis)
            p_src = z_src - axis * z_src.dot(axis)
            if p_now.length > 1e-4 and p_src.length > 1e-4:
                p_now.normalize(); p_src.normalize()
                roll = math.atan2(axis.dot(p_now.cross(p_src)), p_now.dot(p_src))
                R0 = Quaternion(axis, roll).to_matrix() @ R0
            R_arm = A_RW.inverted() @ R0
        else:
            D = F @ (Rs_pose @ Rs_rest.inverted()) @ F.inverted()
            if damp and short in damp:
                q = D.to_quaternion()
                D = Quaternion((1, 0, 0, 0)).slerp(q, damp[short]).to_matrix()
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
        tilt = HEAD_TILT if n.replace(P, '') in ('Neck', 'Head') else 0
        if tilt:
            h = Mo.translation.copy()
            T = Matrix.Translation(h)
            R = Matrix.Rotation(math.radians(tilt / 2), 4, 'Y')
            Mo = T @ R @ T.inverted() @ Mo
        if deg or tilt:
            l2, r2, _ = (Pm.inverted() @ Mo).decompose()
            out[n] = (l2, r2)
        M[n] = Mo
    return out


def shift_hips(basis, delta_arm):
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
    ref = ref_world if ref_world is not None else hips_world(poses[0])
    out = []
    for b in poses:
        h = hips_world(b)
        d = Vector((ref.x - h.x, ref.y - h.y, 0)) * 100.0 / (A_W.to_scale().x * 100.0)
        out.append(shift_hips(b, Vector((d.x, d.y, 0))))
    return out


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
    Ma, Mb = fk(a), fk(b)
    return max((A_W @ Ma[n].translation - A_W @ Mb[n].translation).length for n in ORDER)


def clip_from(src, f0, f1):
    return [retarget_frame(src, f) for f in range(f0, f1 + 1)]


def build_run():
    """Ciclo de correr: Running de Mixamo retargeteado entero (brazos incluidos), en el sitio y cerrado en bucle."""
    src = SRC['run']
    act = src.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    print('RUN source frames', f0, f1, 'fps', scene.render.fps)
    raw = [retarget_frame(src, f) for f in range(f0, f1 + 1)]
    print('LOOP run diff first vs last: %.4f m' % pose_diff(raw[0], raw[-1]))
    # Mixamo repite el primer pose al final: se descarta el ultimo para que el ciclo no pare un fotograma.
    loop = raw[:-1] if pose_diff(raw[0], raw[-1]) < 0.03 else raw
    loop = loop + [loop[0]]
    res = []
    for i in range(RUN_FRAMES + 1):
        x = i * (len(loop) - 1) / RUN_FRAMES
        i0 = int(x); i1 = min(i0 + 1, len(loop) - 1)
        res.append(blend_basis(loop[i0], loop[i1], x - i0) if i1 != i0 else loop[i0])
    res = anchor_hips_xy(res)
    if RUN_LEAN:
        res = [apply_lean(b, RUN_LEAN) for b in res]
    res[-1] = res[0]
    return ground(res), '%d-%d -> %d frames' % (f0, f1, RUN_FRAMES + 1)


def build_crawl():
    """Ciclo de gateo: Crawling de Mixamo retargeteado entero (brazos incluidos), en el sitio y cerrado en bucle."""
    src = SRC['crawl']
    act = src.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    print('CRAWL source frames', f0, f1, 'fps', scene.render.fps)
    res = anchor_hips_xy([retarget_frame(src, f) for f in range(f0, f1 + 1)])
    print('LOOP crawl diff first vs last: %.4f m' % pose_diff(res[0], res[-1]))
    if CRAWL_LEAN:
        res = [apply_lean(b, CRAWL_LEAN) for b in res]
    res[-1] = res[0]
    return ground(res), '%d-%d' % (f0, f1)


clips = {}
if CRAWL_ONLY:
    clips['crawl'] = build_crawl()
elif not RUN_ONLY:

    raw = clip_from(SRC['stand'], 1, 98)
    print('LOOP pray_stand diff f1 vs f98: %.4f m' % pose_diff(raw[0], raw[-1]))
    poses = anchor_hips_xy(raw)
    poses[-1] = poses[0]
    clips['pray_stand'] = (ground(poses), '1-98')

    raw = clip_from(SRC['kneel'], 1, 59)
    print('LOOP pray_kneel diff f1 vs f59: %.4f m' % pose_diff(raw[0], raw[-1]))
    poses = anchor_hips_xy(raw)
    poses[-1] = poses[0]
    clips['pray_kneel'] = (ground(poses), '1-59')

    walk_raw_src = [retarget_frame(SRC['walk'], f, damp={
        'Spine': WALK_SPINE_DAMP, 'Spine1': WALK_SPINE_DAMP, 'Spine2': WALK_SPINE_DAMP,
        'Neck': WALK_SPINE_DAMP, 'Head': WALK_SPINE_DAMP,
        'LeftUpLeg': WALK_STRIDE, 'RightUpLeg': WALK_STRIDE, 'LeftLeg': WALK_STRIDE, 'RightLeg': WALK_STRIDE,
    }) for f in range(1, 33)]
    arms_pose = retarget_frame(SRC['stand'], WALK_ARMS_FRAME)
    ARM_SET = set(n for n in ORDER if is_arm_bone(n))
    print('ARM_SET', len(ARM_SET))
    walk_in = []
    for b in walk_raw_src:
        b2 = dict(b)
        for n in ARM_SET:
            b2[n] = arms_pose[n]
        walk_in.append(b2)
    loop = walk_in + [walk_in[0]]
    res = []
    for i in range(WALK_FRAMES + 1):
        x = i * (len(loop) - 1) / WALK_FRAMES
        i0 = int(x); i1 = min(i0 + 1, len(loop) - 1)
        res.append(blend_basis(loop[i0], loop[i1], x - i0) if i1 != i0 else loop[i0])
    res = anchor_hips_xy(res)
    res = [apply_lean(b, WALK_LEAN) for b in res]
    res[-1] = res[0]
    clips['walk'] = (ground(res), '1-32 (+1 cierre) -> %d frames' % (WALK_FRAMES + 1))

    k2s_raw = clip_from(SRC['k2s'], 1, 207)
    hz = [hips_world(b).z for b in k2s_raw]
    print('K2S hips z (cada 10 frames):', [(i + 1, round(z, 3)) for i, z in enumerate(hz) if i % 10 == 0], 'f207=%.3f' % hz[-1])
    seg = k2s_raw[STAND_UP_START - 1:207]
    kneel_raw0 = anchor_hips_xy(clip_from(SRC['kneel'], 1, 1))[0]
    kref = hips_world(kneel_raw0)
    seg = anchor_hips_xy(seg, ref_world=Vector((kref.x, kref.y, 0)))
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
        if i < STAND_UP_START_BLEND:
            b = blend_basis(kneel_raw0, b, smooth((i + 0.0) / STAND_UP_START_BLEND))
        ja = i - (n - 1 - STAND_UP_ARMS_BLEND)
        if ja > 0:
            b = blend_part(b, walk0, smooth(ja / STAND_UP_ARMS_BLEND), ARM_SET)
        j = i - (n - 1 - STAND_UP_BLEND)
        if j > 0:
            b = blend_basis(b, walk0, smooth(j / STAND_UP_BLEND))
        fin.append(b)
    walk0_z = clip_zmin([walk0], step=1)[0]
    clips['stand_up'] = (ground(fin, mode='lerp', z_end=walk0_z), '%d-207' % STAND_UP_START)
    print('STAND_UP end vs walk f0 head dist max: %.4f m' % pose_diff(clips['stand_up'][0][-1], walk0))
    print('STAND_UP start vs pray_kneel f0 head dist max: %.4f m' % pose_diff(clips['stand_up'][0][0], clips['pray_kneel'][0][0]))

else:
    clips["run"] = build_run()

NAMES = {'pray_stand': PERSONAJE + '_pray_stand', 'pray_kneel': PERSONAJE + '_pray_kneel',
         'stand_up': PERSONAJE + '_stand_up', 'walk': PERSONAJE + '_walk', 'run': PERSONAJE + '_run',
         'crawl': PERSONAJE + '_crawl'}
made = {}
for key, (poses, rng) in clips.items():
    report(key, poses, rng)
if CRAWL_ONLY:
    print('APOYOS (z en m de la articulacion) frame: caderas cabeza manoI manoD rodillaI rodillaD pieI pieD')
    for i in range(0, len(clips['crawl'][0]), 4):
        M = fk(clips['crawl'][0][i])
        print('APOYO %2d ' % i + ' '.join('%.3f' % (A_W @ M[P + b].translation).z for b in (
            'Hips', 'Head', 'LeftHand', 'RightHand', 'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot')))
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
