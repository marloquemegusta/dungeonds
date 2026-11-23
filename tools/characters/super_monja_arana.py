"""ARANA de la Super Monja (fase 1: pose estatica): "pino puente" bocarriba con la cara del derecho mirando
en el sentido de la marcha (el -Y del rig = delante). Fuera de la ROM; no toca las hojas vigentes.
Uso: python tools/characters/super_monja_arana.py     (Blender -> FBX 1 frame -> lab rapido)
Salida: assets/staging/super_monja_arana/{fbx,bake}/  (palancas SM_AR_* abajo)
Blender directo: blender -b -P tools/characters/super_monja_arana.py -- <raiz> exvoto_super_monja
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "assets/staging/super_monja_arana"
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"

if "--" not in sys.argv:
    env = dict(os.environ, SM_RES=os.environ.get("SM_RES", "64"), SM_FIXED_NORM=str(1.8464e-4 * float(os.environ.get("SM_AR_SCALE", "1.5"))),
               SM_ONLY_WALK="1", SM_AR_MODE=os.environ.get("SM_AR_MODE", "walk"), SM_OUTBASE=str(STAGE / "bake"), SM_FBX_DIR=str(STAGE / "fbx"))
    subprocess.run([BLENDER, "-b", "-P", str(Path(__file__)), "--", str(ROOT), "exvoto_super_monja"], env=env, check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/characters/bake_exvoto_super_monja.py")], env=env, check=True)
    sys.exit(0)

import bpy, glob, math
import numpy as np
from mathutils import Vector, Matrix

R_, PERS = sys.argv[sys.argv.index('--') + 1], sys.argv[sys.argv.index('--') + 2]
P = 'mixamorig:'
E = lambda k, d: float(os.environ.get(k, d))
STRETCH_Z, ARM_LEN, NECK_LEN = E('SM_STRETCH', 1.35), E('SM_ARM_LEN', 1.5), E('SM_NECK_LEN', 2.5)
bpy.ops.wm.read_factory_settings(use_empty=True)
MODEL_ROOT = os.environ.get('SM_MODEL_ROOT', R_)   # raiz donde viven los originales LFS (en un worktree pueden ser punteros)
bpy.ops.import_scene.fbx(filepath=glob.glob(os.path.join(MODEL_ROOT, 'assets/models/characters', PERS, 'source/tripo_convert_*.fbx'))[0])
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
PB = arm.pose.bones
for pb in PB:
    pb.rotation_mode = 'QUATERNION'
upd = bpy.context.view_layer.update
AW = arm.matrix_world.to_3x3().normalized()


# Direcciones en el rig: delante = -Y (marcha), arriba = +Z, izquierda del personaje = +X. 's' = hacia delante.
def D(s, z, x=0.0):
    return Vector((x, -s, z)).normalized()


def ang(deg, x=0.0):  # angulo en el plano s-z: 0 = hacia delante, 90 = arriba, 180 = hacia atras
    r = math.radians(deg)
    return D(math.cos(r), math.sin(r), x)


# la cabeza se separa del cuello (bone no conectado) para poder alejarla a lo largo de el: cuello largo sin escalar huesos
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
arm.data.edit_bones[P + 'Head'].use_connect = False
bpy.ops.object.mode_set(mode='POSE')
ORDER = []


def _w(b):
    ORDER.append(b.name)
    for c in b.children:
        _w(c)


for b in arm.data.bones:
    if b.parent is None:
        _w(b)

MODE = os.environ.get('SM_AR_MODE', 'static')      # static (1 frame) | walk (ciclo de andar a cuatro patas)
NF = int(E('SM_AR_FRAMES', 8))
HEAD_PITCH = E('SM_AR_HEAD_PITCH', 0)    # grados: mirar un poco hacia arriba
HEAD_YAW = E('SM_AR_HEAD_YAW', 0)         # giro extra en mundo sobre la vertical (diagnostico)
HEAD_ROLL = E('SM_AR_HEAD_ROLL', 0)     # 180 = cabeza invertida (barbilla arriba), como la nina de El Exorcista
SCALE = {'LeftArm': ARM_LEN, 'RightArm': ARM_LEN}   # el cuello NO se escala (cizalla la cabeza): se alarga desplazando la cabeza
# palancas del andar
SW_ARM, SW_LEG, LIFT_ARM, LIFT_LEG = E('SM_AR_SW_ARM', 0.30), E('SM_AR_SW_LEG', 16), E('SM_AR_LIFT_ARM', 0.45), E('SM_AR_LIFT_LEG', 30)
TUG = E('SM_AR_TUG', 35)
ARM_SW, ARM_LIFT, FARM_LIFT = E('SM_AR_ARM_SW', 10), E('SM_AR_ARM_LIFT', 26), E('SM_AR_FARM_LIFT', 44)   # brazos de araña: avance, levantada y codo (grados)
STUT = 0.0


def bump(ph, c, wd):
    d = (ph - c + 0.5) % 1.0 - 0.5
    return max(0.0, 1.0 - abs(d) / wd) ** 2


POSE = os.environ.get('SM_AR_POSE', 'puente')    # puente (rueda de yoga: vientre al cielo, manos delante) | m (cuatro patas bocabajo, version anterior)


def aims_puente(ph):
    """Pino puente. s>0 = delante (hacia las manos). Angulos en el plano s-z (0 = delante, 90 = arriba, 270 = abajo).
    Torso boca arriba en arco (cadera lo mas alto), brazos casi verticales hasta el suelo, piernas hacia atras con los pies planos."""
    A = {'Hips': ang(E('SM_AR_HIPS', 8)), 'Spine': ang(E('SM_AR_SP0', 0)), 'Spine1': ang(E('SM_AR_SP1', -6)),
         'Spine2': ang(E('SM_AR_SP2', -12)), 'Neck': ang(E('SM_AR_NECK', -80)), 'Head': ang(E('SM_AR_HEAD_A', -90))}
    for sd, k in {'Left': -1.0, 'Right': 1.0}.items():   # con el vientre al cielo la izquierda del personaje cae del lado -X
        p_arm = ph if sd == 'Left' else ph + 0.5
        p_leg = ph + 0.5 if sd == 'Left' else ph
        ca, sa = (math.cos(2 * math.pi * p_arm), math.sin(2 * math.pi * p_arm)) if MODE == 'walk' else (0, 0)
        cl, sl = (math.cos(2 * math.pi * p_leg), math.sin(2 * math.pi * p_leg)) if MODE == 'walk' else (0, 0)
        la, ll = max(0.0, sa), max(0.0, sl)
        A[sd + 'Shoulder'] = D(0.1, 0.0, k)
        A[sd + 'Arm'] = ang(E('SM_AR_ARM_A', 275) + ARM_SW * ca + ARM_LIFT * la, k * E('SM_AR_ARM_X', 0.5))
        A[sd + 'ForeArm'] = ang(E('SM_AR_FARM_A', 270) + ARM_SW * ca + FARM_LIFT * la, k * E('SM_AR_FARM_X', 0.2))
        A[sd + 'Hand'] = ang(E('SM_AR_HAND_A', 180), 0.0)
        A[sd + 'UpLeg'] = ang(E('SM_AR_THIGH', 205) + SW_LEG * cl + LIFT_LEG * ll * 0.5, k * E('SM_AR_LEG_X', 0.9))
        A[sd + 'Leg'] = ang(E('SM_AR_SHIN', 262) + SW_LEG * 0.8 * cl - LIFT_LEG * ll, k * E('SM_AR_LEG_X', 0.9) * E('SM_AR_SHIN_X', 0.7))
        A[sd + 'Foot'] = ang(E('SM_AR_FOOT', 197) + 25 * ll)
        A[sd + 'ToeBase'] = ang(E('SM_AR_TOE', 180) + 25 * ll)
    return A


def aims(ph):
    """Direcciones deseadas por hueso en la fase ph (0..1). Diagonal: mano izq + pie dcho en fase, y al reves."""
    A = {
        'Hips': ang(E('SM_AR_HIPS', 100)),
        'Spine': ang(E('SM_AR_SP0', 130)), 'Spine1': ang(E('SM_AR_SP1', 160)), 'Spine2': ang(E('SM_AR_SP2', 200)),
        'Neck': ang(E('SM_AR_NECK', 125)),
    }
    for sd, k in {'Left': 1.0, 'Right': -1.0}.items():
        p_arm = ph if sd == 'Left' else ph + 0.5
        p_leg = ph + 0.5 if sd == 'Left' else ph
        ca, sa = (math.cos(2 * math.pi * p_arm), math.sin(2 * math.pi * p_arm)) if MODE == 'walk' else (0, 0)
        cl, sl = (math.cos(2 * math.pi * p_leg), math.sin(2 * math.pi * p_leg)) if MODE == 'walk' else (0, 0)
        la, ll = max(0.0, sa), max(0.0, sl)      # solo se levanta en la mitad adelantada del paso
        A[sd + 'Shoulder'] = D(-0.15, 0.0, k)
        A[sd + 'Arm'] = D(E('SM_AR_ARM_S', -0.30) + SW_ARM * ca, -1.0 + LIFT_ARM * la, k * E('SM_AR_ARM_X', 0.35))
        A[sd + 'ForeArm'] = D(E('SM_AR_FARM_S', -0.30) + SW_ARM * ca * 1.2, -1.0 + LIFT_ARM * la * 1.6, k * E('SM_AR_FARM_X', 0.15))
        A[sd + 'Hand'] = D(E('SM_AR_HAND_S', -0.6), -0.8, k * 0.1)
        A[sd + 'UpLeg'] = ang(E('SM_AR_THIGH', 20) + SW_LEG * cl, k * E('SM_AR_LEG_X', 0.35))
        A[sd + 'Leg'] = ang(E('SM_AR_SHIN', -80) + SW_LEG * 0.8 * cl + LIFT_LEG * ll, k * E('SM_AR_LEG_X', 0.35) * 0.3)
        A[sd + 'Foot'] = ang(E('SM_AR_FOOT', -20) + 25 * ll)
    return A


def rest_yaw(short):
    """Mano, dedos, pie y dedos del pie: la orientacion de reposo (palma y planta planas) girada sobre la vertical.
    Manos: dedos hacia atras (los pies); pies: dedos hacia atras."""
    for sd, yaw in (('Left', 90.0), ('Right', -90.0)):
        if short.startswith(sd + 'Hand'):
            return yaw
        if short.startswith(sd + 'Foot') or short.startswith(sd + 'Toe'):
            return 180.0
    return None


def k_side(short):
    return 1.0 if short.startswith('Left') else -1.0


def _perp_sz(y, sign):      # perpendicular a y en el plano s-z (s=-Y mundo): sign=+1 gira +90, -1 gira -90
    s_, z_ = -y.y, y.z
    ns, nz = (-z_ * sign, s_ * sign)
    return Vector((0, -ns, nz))


HC = {'manoI': [E('SM_AR_HAND_PITCH', 36), 0.0], 'manoD': [E('SM_AR_HAND_PITCH', 36), 0.0],
      'pieI': [E('SM_AR_FOOT_PITCH', 17), 0.0], 'pieD': [E('SM_AR_FOOT_PITCH', 17), 0.0]}   # [cabeceo, giro lateral] en grados (mundo); los ajusta calibrate_flat()


def _key(short):
    return ('mano' if 'Hand' in short else 'pie') + ('I' if short.startswith('Left') else 'D')


FRAME_HINT = {}
for _n in ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'):
    FRAME_HINT[_n] = (lambda y, k: ('X', _perp_sz(y, +1)))
for _sd in ('Left', 'Right'):
    for _n in ('UpLeg', 'Leg'):
        FRAME_HINT[_sd + _n] = (lambda y, k: ('X', _perp_sz(y, -1)))
    FRAME_HINT[_sd + 'Foot'] = (lambda y, k: ('Z', Vector((0, 0, 1))))
    FRAME_HINT[_sd + 'ToeBase'] = (lambda y, k: ('Z', Vector((0, 0, 1))))   # planta plana: dorso hacia +Z
    FRAME_HINT[_sd + 'Hand'] = (lambda y, k: ('Z', Vector((0, 0, 1.0 * k))))   # palma al suelo: izq -Z local, dcha +Z local


def set_pose(ph, tug_t):
    """tug_t: 0..1 intensidad del tiron seco de cabeza."""
    A = aims_puente(ph) if POSE == "puente" else aims(ph)
    tug = tug_t if MODE == 'walk' else 0.0
    A['Neck'] = ang(E('SM_AR_NECK', -80 if POSE == 'puente' else 125) + TUG * 0.6 * tug)
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    for n, s in SCALE.items():
        PB[P + n].scale = (1, s, 1)
    upd()
    for n in ORDER:
        pb = PB[n]; short = n.replace(P, '')
        m = pb.matrix.copy()
        rz = rest_yaw(short) if POSE == 'puente' else None
        if rz is not None:
            if short.startswith(('LeftHand', 'RightHand')):   # mano y dedos: todos con la orientacion de la mano (dedos rectos y paralelos) y cabeceo que la deja plana
                base = AW @ arm.data.bones[P + ('Left' if short.startswith('Left') else 'Right') + 'Hand'].matrix_local.to_3x3().normalized()
                pitch = Matrix.Rotation(math.radians(HC[_key(short)][0]), 3, 'X') @ Matrix.Rotation(math.radians(HC[_key(short)][1]), 3, 'Y')
            elif short.startswith(('LeftFoot', 'RightFoot')):   # pie y dedos: misma orientacion del pie, cabeceo que deja la planta plana
                base = AW @ arm.data.bones[P + ('Left' if short.startswith('Left') else 'Right') + 'Foot'].matrix_local.to_3x3().normalized()
                pitch = Matrix.Rotation(math.radians(HC[_key(short)][0]), 3, 'X') @ Matrix.Rotation(math.radians(HC[_key(short)][1]), 3, 'Y')
            else:
                base = AW @ arm.data.bones[n].matrix_local.to_3x3().normalized(); pitch = Matrix.Identity(3)
            R3 = pitch @ Matrix.Rotation(math.radians(rz), 3, 'Z') @ base
            m = Matrix.Translation(m.translation) @ (AW.inverted() @ R3).to_4x4()
        elif POSE == 'puente' and short in FRAME_HINT:
            y = A[short].normalized()
            kind, hv = FRAME_HINT[short](y, k_side(short))
            h = hv - y * hv.dot(y)
            h.normalize()
            if kind == 'X':
                z_ = h.cross(y); x_ = h          # Z = X x Y
            else:
                z_ = h; x_ = y.cross(z_)
            Rw = Matrix(((x_.x, y.x, z_.x), (x_.y, y.y, z_.y), (x_.z, y.z, z_.z)))
            sc_y = SCALE[('Left' if short.startswith('Left') else 'Right') + 'Arm'] if short in ('LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm') else 1.0
            m = Matrix.Translation(m.translation) @ ((AW.inverted() @ Rw) @ Matrix.Diagonal((1, sc_y, 1))).to_4x4()
        elif short in A:
            cur = (AW @ m.to_3x3() @ Vector((0, 1, 0))).normalized()
            R = cur.rotation_difference(A[short]).to_matrix()
            m3 = (AW.inverted() @ R @ AW) @ m.to_3x3()
            m = Matrix.Translation(m.translation) @ m3.to_4x4()
        elif short == 'Head' and POSE != 'puente':
            rest = arm.data.bones[n].matrix_local.to_3x3().normalized()
            # cabeza de reposo (cara a -Y), cabeceo, y giro sobre el eje de la cara (-Y): 180 = invertida
            m3 = Matrix.Rotation(math.radians(HEAD_ROLL + TUG * 0.5 * tug), 3, 'Y') @ \
                 Matrix.Rotation(math.radians(-HEAD_PITCH), 3, 'X') @ rest
            nd = (AW @ PB[P + 'Neck'].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()   # cuello largo: la cabeza se aleja a lo largo del cuello
            off = AW.inverted() @ nd * (arm.data.bones[P + 'Neck'].length * (NECK_LEN - 1))
            m = Matrix.Translation(m.translation + off) @ m3.to_4x4()   # escala final 1: la cabeza no hereda el estiramiento del cuello
        pb.matrix = m
        upd()


def stats():
    upd()
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); w = co @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear()
    return w


_gn = {g.index: g.name for g in mesh.vertex_groups}
CONTACT = np.array([i for i, v in enumerate(mesh.data.vertices) if v.groups and any(
    k in _gn[max(v.groups, key=lambda g: g.weight).group] for k in ('Hand', 'Foot', 'Toe'))])


def gz(w):
    """Altura del suelo: puente = punto mas bajo de manos y pies (la orla de la tunica puede colgar por debajo); resto = malla."""
    return w[CONTACT, 2].min() if POSE == 'puente' else w[:, 2].min()


def _grp(prefixes):
    return np.array([i for i, v in enumerate(mesh.data.vertices) if v.groups and any(
        _gn[max(v.groups, key=lambda g: g.weight).group].replace(P, '').startswith(pf) for pf in prefixes)])


GRP = {'manoI': _grp(['LeftHand']), 'manoD': _grp(['RightHand']), 'pieI': _grp(['LeftFoot', 'LeftToe']), 'pieD': _grp(['RightFoot', 'RightToe'])}


def contact_report(w, title=''):
    out = []
    for k, ix in GRP.items():
        z = np.sort(w[ix, 2]); n = max(1, len(z) // 4)
        out.append('%s zmin=%.3f p25=%.3f zmax=%.3f' % (k, z[0], z[n], z[-1]))
    print('DIAG apoyos', title, ' | '.join(out))


def _flat_cost(w, ix):
    z = np.sort(w[ix, 2]); n = max(3, int(len(z) * 0.35))
    return float(z[:n].mean() - z[0])      # lo que sobresale del suelo el 35% mas bajo: 0 = totalmente plano


def calibrate_flat():
    """Ajusta cabeceo y giro lateral de cada mano y pie hasta que su superficie de apoyo quede horizontal (busqueda por coordenadas)."""
    global MODE
    old = MODE; MODE = 'static'
    def costs():
        set_pose(0.0, 0.0); w = stats()
        return {k: _flat_cost(w, GRP[k]) for k in GRP}
    cur = costs()
    for step in (10, 5, 2.5, 1.2, 0.6):
        for _ in range(3):
            for ax in (0, 1):
                for sg in (1, -1):
                    for k in HC:
                        HC[k][ax] += sg * step
                    new = costs()
                    for k in HC:
                        if new[k] < cur[k] - 1e-5:
                            cur[k] = new[k]
                        else:
                            HC[k][ax] -= sg * step
                    cur = costs()
    print('FLAT ' + ' | '.join('%s pitch=%.1f roll=%.1f coste=%.4f' % (k, HC[k][0], HC[k][1], cur[k]) for k in HC))
    MODE = old


def solve_arms():
    """Calibra manos y pies planos y ajusta cada brazo por separado hasta que su mano apoye en el mismo plano z que los pies."""
    global MODE, ARM_LEN
    old = MODE; MODE = 'static'
    calibrate_flat()
    for it in range(10):
        set_pose(0.0, 0.0); w = stats()
        zf = min(w[GRP['pieI'], 2].min(), w[GRP['pieD'], 2].min())
        ok = True
        for sd, key in (('Left', 'manoI'), ('Right', 'manoD')):
            zh = w[GRP[key], 2].min()
            av = (arm.matrix_world @ PB[P + sd + 'Shoulder'].head).z - zh
            print('SOLVE it%d %s ARM_LEN=%.3f mano_z=%.4f pie_z=%.4f' % (it, sd, SCALE[sd + 'Arm'], zh, zf))
            if abs(zh - zf) >= 0.002:
                ok = False
                SCALE[sd + 'Arm'] *= 1 + (zh - zf) / av
        if ok:
            break
    ARM_LEN = SCALE['LeftArm']
    MODE = old
    return ARM_LEN


def place_hips(dz):
    hp = PB[P + 'Hips']
    m = hp.matrix.copy()
    m.translation += Vector((0, 0, dz)) / arm.matrix_world.to_scale().x
    m.translation.x = hp.bone.head_local.x; m.translation.y = hp.bone.head_local.y
    hp.matrix = m; upd()


BURST = int(E('SM_AR_BURST', 6))
CYC = E('SM_AR_CYC', 2)   # ciclos de pata completos dentro de la racha (correteo nervioso)   # fotogramas de racha (patas rapidas); el resto del ciclo es pausa quieta


def frame_phase(i):
    """Ritmo de arana: racha de BURST fotogramas con un ciclo de pata completo y pausa en seco el resto; tiron de cabeza al parar."""
    if MODE != 'walk':
        return 0.0, 0.0
    ph = min(1.0, (i + 1) / BURST) * CYC
    tg = {NF - 2: 0.5, NF - 1: 1.0}.get(i, 0.0)
    return ph, tg



if POSE == 'puente' and os.environ.get('SM_AR_AUTOARM', '1') == '1':
    solve_arms()
frames = list(range(NF)) if MODE == 'walk' else [0]   # (trans: ver arriba)
FIT = {}      # por fotograma: escala de cada brazo para que la mano que apoya toque el suelo aunque el brazo avance


def arm_planted(sd, i):
    ph, _ = frame_phase(i); p = ph if sd == 'Left' else ph + 0.5
    return math.sin(2 * math.pi * p) <= 0.0


def fit_arms():
    """Brazos de araña: en cada fotograma la mano que apoya se alarga/acorta para pisar el mismo suelo que los pies; la que se levanta usa la media."""
    base = dict(SCALE); zf = 9.0
    for i in frames:
        ph, tg = frame_phase(i); set_pose(ph, tg); w = stats()
        zf = min(zf, w[GRP['pieI'], 2].min(), w[GRP['pieD'], 2].min())
    acc = {'Left': [], 'Right': []}
    for i in frames:
        ph, tg = frame_phase(i); FIT[i] = {}
        for it in range(5):
            set_pose(ph, tg); w = stats(); done = True
            for sd, key in (('Left', 'manoI'), ('Right', 'manoD')):
                if not arm_planted(sd, i): continue
                zh = w[GRP[key], 2].min(); av = (arm.matrix_world @ PB[P + sd + 'Shoulder'].head).z - zh
                if abs(zh - zf) > 0.002:
                    done = False; SCALE[sd + 'Arm'] *= 1 + (zh - zf) / av
            if done: break
        for sd in ('Left', 'Right'):
            FIT[i][sd] = SCALE[sd + 'Arm']
            if arm_planted(sd, i): acc[sd].append(SCALE[sd + 'Arm'])
        SCALE.update(base)
    for sd in ('Left', 'Right'):
        m = sum(acc[sd]) / max(1, len(acc[sd]))
        for i in frames:
            if not arm_planted(sd, i): FIT[i][sd] = m
    print('FIT brazos', {i: (round(FIT[i]['Left'], 2), round(FIT[i]['Right'], 2)) for i in frames})


def use_fit(i):
    if i in FIT:
        SCALE['LeftArm'], SCALE['RightArm'] = FIT[i]['Left'], FIT[i]['Right']


if MODE == 'walk' and os.environ.get('SM_AR_FITARMS', '1') == '1':
    fit_arms()
RENDER = os.environ.get('SM_AR_RENDER')   # diagnostico: render grande de la pose quieta (workbench) en SM_AR_RENDER=<prefijo>
if RENDER:
    for n in ('Neck', 'Head'):
        b = PB[P + n]
        print('AXES %s rest local cols(x,y,z)=%s' % (n, [tuple(round(v, 2) for v in arm.data.bones[P + n].matrix_local.to_3x3().col[i]) for i in range(3)]))
    _rf = int(E('SM_AR_RF', 0)); use_fit(_rf); _ph, _tg = frame_phase(_rf); set_pose(_ph, _tg); w = stats(); place_hips(-gz(w)); w = stats()
    contact_report(w, '(tras suelo)')
    fing = [b.name for b in arm.data.bones if 'Hand' in b.name and b.name.replace(P, '')[4:].startswith(('Hand', )) and len(b.name) > len(P) + 8]
    mx = 0.0
    for nm in fing:
        pbn = PB[nm]
        if pbn.parent and pbn.parent.name != P + 'LeftHand' and pbn.parent.name != P + 'RightHand':
            a1 = (AW @ pbn.matrix.to_3x3() @ Vector((0, 1, 0))).normalized(); a0 = (AW @ pbn.parent.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
            mx = max(mx, math.degrees(a0.angle(a1)))
    print('DIAG curvatura maxima entre falanges consecutivas: %.1f grados' % mx)
    for n in ('Neck', 'Head'):
        b = PB[P + n]; h = arm.matrix_world @ b.head; t = arm.matrix_world @ b.tail
        print('AXES %s pose head=%s tail=%s dir=%s' % (n, tuple(round(v, 3) for v in h), tuple(round(v, 3) for v in t), tuple(round(v, 2) for v in (t - h).normalized())))
    arm.scale = (0.01, 0.01, 0.01 * STRETCH_Z); upd()
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'; sc.display.shading.show_shadows = False
    sc.render.resolution_x = sc.render.resolution_y = 512
    sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.5, 0.5, 0.5)
    cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = float(os.environ.get('SM_AR_ORTHO', '1.3'))
    co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
    ctr = Vector((0, 0, 0.45))
    for n in ('Neck', 'Head', 'LeftShoulder', 'RightShoulder', 'Spine2', 'Hips'):
        b = PB[P + n]; h = arm.matrix_world @ b.head; t = arm.matrix_world @ b.tail
        print('DIAG %-13s head(x,s,z)=(%.3f,%.3f,%.3f) tail=(%.3f,%.3f,%.3f)' % (n, h.x, -h.y, h.z, t.x, -t.y, t.z))
    fx = (AW @ PB[P + 'Head'].matrix.to_3x3() @ Vector((1, 0, 0))).normalized()
    print('DIAG normal de la cara (eje X local de Head) en mundo (x,s,z) = (%.2f,%.2f,%.2f)  (s>0 = delante, z>0 = arriba)' % (fx.x, -fx.y, fx.z))
    hw = (arm.matrix_world @ PB[P + 'Head'].head)
    inside = np.sum(np.linalg.norm(w - np.array([hw.x, hw.y, hw.z / STRETCH_Z]), axis=1) < 0.05)
    print('DIAG z minima malla %.3f | contacto manos/pies %.3f | z cadera %.3f | z hombros %.3f | z cabeza(origen) %.3f coronilla %.3f' % (w[:, 2].min(), gz(w), (arm.matrix_world @ PB[P + 'Hips'].head).z, (arm.matrix_world @ PB[P + 'LeftShoulder'].head).z, (arm.matrix_world @ PB[P + 'Head'].head).z, (arm.matrix_world @ PB[P + 'Head'].tail).z))
    for hn in ('LeftHand', 'RightHand'):
        zl = (AW @ PB[P + hn].matrix.to_3x3() @ Vector((0, 0, 1))).normalized(); pal = -zl if hn == 'LeftHand' else zl
        yl = (AW @ PB[P + hn].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
        print('DIAG %s normal de la palma (x,s,z)=(%.2f,%.2f,%.2f) dedos(x,s,z)=(%.2f,%.2f,%.2f)' % (hn, pal.x, -pal.y, pal.z, yl.x, -yl.y, yl.z))
    for fn in ('LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase'):
        M3 = AW @ PB[P + fn].matrix.to_3x3(); sol = -M3.col[2]; hh = arm.matrix_world @ PB[P + fn].head; tt = arm.matrix_world @ PB[P + fn].tail
        print('DIAG %s normal de la planta (x,s,z)=(%.2f,%.2f,%.2f) z head=%.3f tail=%.3f' % (fn, sol.x, -sol.y, sol.z, hh.z, tt.z))
    for hn in ('Neck', 'Head'):
        M3 = AW @ PB[P + hn].matrix.to_3x3()
        print('DIAG ejes %s  Y(coronilla)=(%.2f,%.2f,%.2f)  X(cara)=(%.2f,%.2f,%.2f)  Z(lat)=(%.2f,%.2f,%.2f)  [x,s,z]' % ((hn,) + tuple(v for c in (M3.col[1], M3.col[0], M3.col[2]) for v in (c.x, -c.y, c.z))))
    print('DIAG vertices a <5 cm del origen de la cabeza:', inside)
    if os.environ.get('SM_AR_PAINT') == '1':   # cabeza roja, cuello verde, resto gris (por pesos de vertice)
        gi = {g.name: g.index for g in mesh.vertex_groups}
        ca = mesh.data.color_attributes.new('dbg', 'FLOAT_COLOR', 'POINT')
        for v in mesh.data.vertices:
            wd = {g.group: g.weight for g in v.groups}
            wh, wn = wd.get(gi[P + 'Head'], 0), wd.get(gi[P + 'Neck'], 0)
            c = (0.65, 0.65, 0.65, 1)
            if wh > 0.5: c = (1, 0, 0, 1)
            elif wn > 0.5: c = (0, 0.9, 0, 1)
            elif wh > 0.1: c = (1, 0.5, 0.5, 1)
            elif wn > 0.1: c = (0.5, 0.9, 0.5, 1)
            ca.data[v.index].color = c
        mesh.data.color_attributes.active_color = ca
        sc.display.shading.color_type = 'VERTEX'
    PROJ = {}
    for nm, az, el in (('SE', 45, 30), ('E', 90, 30), ('perfil', 90, 0), ('frente0', 0, 0), ('arriba', 0, 89)):
        a, e = math.radians(az), math.radians(el)
        pos = ctr + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 4
        co.location = pos
        co.rotation_euler = (ctr - pos).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = RENDER + '_' + nm + '.png'
        bpy.ops.render.render(write_still=True)
        from bpy_extras.object_utils import world_to_camera_view
        sc.frame_current = sc.frame_current; upd()
        pr = {}
        for key, bn in (('manoI', 'LeftHand'), ('manoD', 'RightHand'), ('pieI', 'LeftFoot'), ('pieD', 'RightFoot'), ('suelo', None)):
            wp = (arm.matrix_world @ PB[P + bn].head) if bn else Vector((0, 0, 0))
            if bn is None: wp = Vector((0, ctr.y, 0))
            c = world_to_camera_view(sc, co, wp); pr[key] = (c.x * 512, (1 - c.y) * 512)
        PROJ[nm] = pr
    import json; json.dump(PROJ, open(RENDER + '_proj.json', 'w'))
    sys.exit(0)
# ---- modo 'trans': transicion de pie -> arana (la vuelta es la misma al reves) ----
NT = int(E('SM_AR_NT', 8))
STAND = {}
ARANA_B = {}


def _qs(m):
    l, q, sc = m.decompose()
    return l, q, sc


def load_stand():
    """Pose de pie = fotograma SM_AR_STAND_FRAME del clip de andar del propio personaje (SM_AR_STAND = fbx), valores locales por hueso."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.environ['SM_AR_STAND'])
    new = [o for o in bpy.data.objects if o not in before]
    sa = [o for o in new if o.type == 'ARMATURE'][0]
    act = sa.animation_data.action
    bpy.context.scene.frame_set(int(act.frame_range[0]) + int(E('SM_AR_STAND_FRAME', 0)))
    upd()
    for pb in sa.pose.bones:
        STAND[pb.name] = _qs(pb.matrix_basis)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.objects.active = arm


def _smooth(t):
    return t * t * (3 - 2 * t)


TV = os.environ.get('SM_AR_TV', 'slerp')   # slerp (rueda, version anterior) | A (media vuelta + puente atras) | B (puente atras directo, de pie mirando al reves)
STW, STY, ARY, AFIN = {}, {}, {}, {}


def _s(u, a, b):
    x = min(1.0, max(0.0, (u - a) / (b - a)))
    return 0.5 * x + 0.5 * x * x * (3 - 2 * x)      # mitad lineal, mitad suave: reparte el movimiento entre los 8 fotogramas


def _wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def prep_fk():
    """Mundo de la pose de pie (rotaciones por hueso) y alfa final (cabeceo atras en el plano s-z) de cada hueso hasta la arana."""
    for pb in PB:
        l, q, sc_ = STAND[pb.name]; pb.location = l; pb.rotation_quaternion = q; pb.scale = sc_
    upd()
    Rz180 = Matrix.Rotation(math.pi, 3, 'Z')
    for pb in PB:
        STW[pb.name] = (AW @ pb.matrix.to_3x3()).normalized()
        STY[pb.name] = (Rz180 @ STW[pb.name] @ Vector((0, 1, 0))).normalized()
    for pb in PB:   # pose arana estatica -> direcciones objetivo
        la, qa, sa = ARANA_B[pb.name]; pb.location = la; pb.rotation_quaternion = qa; pb.scale = sa
    upd()
    for pb in PB:
        ARY[pb.name] = (AW @ pb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
        y0, y1 = STY[pb.name], ARY[pb.name]
        AFIN[pb.name] = math.degrees(math.atan2(y1.z, y1.y) - math.atan2(y0.z, y0.y)) % 360.0


def alpha_curves(u):
    """Cabeceo absoluto (grados, + = hacia atras del que mira) por hueso en el instante u (0..1) del arqueo."""
    f = lambda n: AFIN[P + n]
    fs = lambda n: _wrap(f(n))
    a = {}
    a['Hips'] = fs('Hips') * _s(u, 0.0, 0.95)
    a['Spine'] = fs('Spine') * _s(u, 0.05, 1.0)
    a['Spine1'] = fs('Spine1') * _s(u, 0.10, 1.0)
    a['Spine2'] = fs('Spine2') * _s(u, 0.15, 1.0)
    a['Neck'] = (f('Neck')) * _s(u, 0.20, 1.0)
    a['Head'] = (f('Head')) * _s(u, 0.25, 1.0)
    for sd in ('Left', 'Right'):
        arm = 180.0 * _s(u, 0.0, 0.6) + (f(sd + 'Arm') - 180.0) * _s(u, 0.4, 1.0)      # sube por delante, pasa sobre la cabeza y baja por detras
        fa = 180.0 * _s(u, 0.06, 0.66) + (f(sd + 'ForeArm') - 180.0) * _s(u, 0.46, 1.0)
        a[sd + 'Arm'] = arm; a[sd + 'ForeArm'] = fa
        a[sd + 'Hand'] = fa + _wrap(f(sd + 'Hand') - f(sd + 'ForeArm')) * _s(u, 0.55, 1.0)
        a[sd + 'UpLeg'] = fs(sd + 'UpLeg') * _s(u, 0.35, 1.0)                 # rodillas se doblan al final
        a[sd + 'Leg'] = fs(sd + 'Leg') * _s(u, 0.30, 1.0)
        a[sd + 'Foot'] = a[sd + 'Leg'] + _wrap(f(sd + 'Foot') - f(sd + 'Leg')) * _s(u, 0.6, 1.0)
        a[sd + 'ToeBase'] = a[sd + 'Foot'] + _wrap(f(sd + 'ToeBase') - f(sd + 'Foot')) * _s(u, 0.6, 1.0)
    return {P + k: v for k, v in a.items()}


def fk_pose(i):
    if TV == 'A':
        yaw = (0.0, 90.0, 180.0)[min(i, 2)]; u = (max(0, i - 1) / float(NT - 2)) ** E('SM_AR_UPOW', 0.75)
    else:
        yaw = 180.0; u = (i / float(NT - 1)) ** E('SM_AR_UPOW', 0.75)
    for pb in PB:
        l, q, sc_ = STAND[pb.name]; pb.location = l; pb.rotation_quaternion = q; pb.scale = sc_
    upd()
    AL = alpha_curves(u); Rz = Matrix.Rotation(math.radians(yaw), 3, 'Z'); cur = {}
    for n in ORDER:
        pb = PB[n]
        a = AL.get(n, cur.get(pb.parent.name, 0.0) if pb.parent else 0.0); cur[n] = a
        R3 = Matrix.Rotation(math.radians(a), 3, 'X') @ Rz @ STW[n]
        m = pb.matrix.copy()
        pb.matrix = Matrix.Translation(m.translation) @ (AW.inverted() @ R3).to_4x4(); upd()
    if u >= 0.999:   # diagnostico: desvio (grados) local del FK final respecto a la pose arana exacta
        dv = []
        for pb in PB:
            q0 = _qs(pb.matrix_basis)[1]; qb = ARANA_B[pb.name][1]
            dv.append((round(math.degrees(2 * math.acos(min(1.0, abs(q0.dot(qb))))), 0), pb.name.replace(P, '')))
        print('FK desvio', sorted([d for d in dv if d[0] > 12], reverse=True)[:14])
    wend = _s(u, 0.35, 1.0)      # al final se mezcla con la pose arana exacta (manos y pies planos, brazos largos)
    for pb in PB:
        l0, q0, s0 = _qs(pb.matrix_basis); lb, qb, sb = ARANA_B[pb.name]
        if q0.dot(qb) < 0:
            qb = -qb
        pb.location = l0.lerp(lb, wend); pb.rotation_quaternion = q0.slerp(qb, wend); pb.scale = s0.lerp(sb, wend)
    upd()
    w = stats(); zf = min(w[GRP['pieI'], 2].min(), w[GRP['pieD'], 2].min()); wg = _s(u, 0.7, 1.0)
    place_hips(-((1 - wg) * zf + wg * gz(w)))
    return u


def trans_pose(i):
    if TV in ('A', 'B'):
        return fk_pose(i)
    t = i / float(NT - 1); te = _smooth(t) if os.environ.get('SM_AR_TEASE', '1') == '1' else t
    for pb in PB:
        la, qa, sa = STAND[pb.name]; lb, qb, sb = ARANA_B[pb.name]
        if qa.dot(qb) < 0:
            qb = -qb
        pb.location = la.lerp(lb, te); pb.rotation_quaternion = qa.slerp(qb, te); pb.scale = sa.lerp(sb, te)
    upd()
    w = stats()
    place_hips(-((1 - te) * w[:, 2].min() + te * gz(w)))
    return te


if MODE == 'trans':
    load_stand()
    set_pose(0.0, 0.0)
    for pb in PB:
        ARANA_B[pb.name] = _qs(pb.matrix_basis)
    if TV in ('A', 'B'):
        prep_fk()
    TR = os.environ.get('SM_AR_TRENDER')
    if TR:
        sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
        sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'; sc.display.shading.show_shadows = False
        sc.render.resolution_x = sc.render.resolution_y = int(E('SM_AR_TRES', 384))
        sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.5, 0.5, 0.5)
        cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = float(os.environ.get('SM_AR_ORTHO', '2.0'))
        co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
        arm.scale = (0.01, 0.01, 0.01 * STRETCH_Z); upd()
        ctr = Vector((0, 0, E('SM_AR_CZ', 0.85)))
        for i in range(NT):
            trans_pose(i)
            for nm, az, el in (('SE', 45, 25), ('perfil', 90, 0)):
                a, e = math.radians(az), math.radians(el)
                pos = ctr + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 6
                co.location = pos; co.rotation_euler = (ctr - pos).to_track_quat('-Z', 'Y').to_euler()
                sc.render.filepath = '%s_f%d_%s.png' % (TR, i, nm); bpy.ops.render.render(write_still=True)
        sys.exit(0)
# pasada 1: suelo comun (la malla mas baja de todo el ciclo = 0)
zmins = []
for i in frames:
    use_fit(i); ph, tg = frame_phase(i); set_pose(ph, tg); zmins.append(gz(stats()))
GROUND = min(zmins)
print('ARANA suelo comun zmin', round(GROUND, 4), 'por frame', [round(z, 3) for z in zmins])

act = bpy.data.actions.new(PERS + '_' + os.environ.get('SM_AR_CLIP', 'walk')); act.use_fake_user = True
arm.animation_data_create(); arm.animation_data.action = act
nkeys = NF + 1 if MODE == 'walk' else (NT + 1 if MODE == 'trans' else 2)
for k in range(nkeys):
    i = k % NF if MODE == 'walk' else 0
    if MODE == 'trans':
        trans_pose(min(k, NT - 1))   # la clave NT repite la ultima: el lab muestrea justo en las claves 0..NT-1
    else:
        use_fit(i); ph, tg = frame_phase(i); set_pose(ph, tg); place_hips(-GROUND)
    w = stats()
    if k < NF or MODE == 'static':
        print('ARANA f%d zmin %.3f zmax %.3f x %.3f..%.3f s %.3f..%.3f' % (k, w[:, 2].min(), w[:, 2].max(), w[:, 0].min(), w[:, 0].max(), -w[:, 1].max(), -w[:, 1].min()))
    for pb in PB:
        pb.keyframe_insert('location', frame=k); pb.keyframe_insert('rotation_quaternion', frame=k); pb.keyframe_insert('scale', frame=k)
act.frame_range = (0, nkeys - 1)
arm.scale = (1, 1, STRETCH_Z)
sc = bpy.context.scene; sc.name = PERS + '_' + os.environ.get('SM_AR_CLIP', 'walk'); sc.render.fps = 30; sc.frame_start = 0; sc.frame_end = nkeys - 1
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
for o in (arm, mesh):
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
out = os.path.join(os.environ.get('SM_FBX_DIR', os.path.join(R_, 'assets/staging/super_monja_arana/fbx')), PERS + '_' + os.environ.get('SM_AR_CLIP', 'walk') + '.fbx')
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'ARMATURE', 'MESH'}, use_mesh_modifiers=False,
    add_leaf_bones=False, path_mode='COPY', embed_textures=True, bake_anim=True, bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0, bake_anim_step=1.0, mesh_smooth_type='FACE')
print('EXPORTED', out)
