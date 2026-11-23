"""PROTOTIPO: remate del Corazon Abierto sobre la Super Monja en forma ARANA ("monjarana").

Secuencia: el heroe se agacha ante la araña tambaleante, le agarra la cabeza (que cuelga invertida bajo el puente, cara
al frente), tira (el cuello se estira) y se la arranca. El cuerpo pierde el puente y se desploma inerte, espatarrado
(brazos y piernas abiertos); el heroe se queda con la cabeza en la mano y la tira a un lado. Corte del cuello y gotas
= cera oscura apagada (nada de rojo).

Fotogramas de celda (60 ms):
   0-2   el heroe entra y se agacha; la araña tiembla aturdida
   3     AGARRE: las dos manos cierran sobre la cabeza
   4-6   TIRON: el cuello se estira, el cuerpo se arrastra hacia el heroe
   7     ARRANQUE: la cabeza sale (corte dentado + gotas de cera oscura)
   7-16  DESPLOME: el cuerpo pierde el puente, cae de espaldas y se abre; rebote y quietud
   8-9   el heroe sostiene la cabeza; 10 la suelta de lado (cae y rueda)
   17-fin quieto; el heroe recupera la pose de reposo
   fin   fotograma de restos (cuerpo espatarrado + cabeza, sin heroe)

Uso (la pose arana se construye con tools/characters/super_monja_arana.py, truncado antes de su render/export):
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/ds_remate_smonja.py -- <raiz> <salida> all
  REMATE_GLB_DIR=<dir> escribe un GLB por fotograma (lab rapido: tools/lab/fast/export_scene_fast.cjs)
  QUICK_DIR=<dir> ademas renderiza una vista rapida (Workbench) de cada fotograma para revisar la pose
"""
import sys, os, math, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A_ = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT = A_[0], A_[1]
FRAMES_ARG = A_[2] if len(A_) > 2 else 'all'
GLB_DIR = os.environ.get('REMATE_GLB_DIR')
QUICK_DIR = os.environ.get('QUICK_DIR')
E = lambda k, d: float(os.environ.get(k, d))

# ---------------------------------------------------------------------------------------------- pose arana (script ajeno)
import bpy
src = open(os.path.join(HERE, 'super_monja_arana.py'), encoding='utf-8').read()
cut = src.index("RENDER = os.environ.get('SM_AR_RENDER')")
_argv = sys.argv
sys.argv = ['blender', '--', os.environ.get('SM_MODEL_ROOT', ROOT), 'exvoto_super_monja']
os.environ.setdefault('SM_AR_MODE', 'static')
G = {'__name__': 'sm_arana', '__file__': os.path.join(HERE, 'super_monja_arana.py')}
exec(compile(src[:cut], 'super_monja_arana', 'exec'), G)
sys.argv = _argv
bpy.ops.object.mode_set(mode='OBJECT')

sys.path.insert(0, HERE)
import ds_remate_exvoto_lib as L
from ds_remate_exvoto_lib import *
import ds_remate_exvoto_lib as _lib

_lib.CELL = (96, 96)
PPM = E('PPM_OVR', '38')
_lib.PPM = PPM

SM_ARM, SM_MESH, SM_PB = G['arm'], G['mesh'], G['PB']
STRETCH = G['STRETCH_Z']
SM_SET_POSE, SM_STATS, SM_PLACE, SM_GZ = G['set_pose'], G['stats'], G['place_hips'], G['gz']
SM_UPD = G['upd']
ARM0_SCALE = SM_ARM.scale.copy()
print('SM arm scale', tuple(ARM0_SCALE), 'rot', tuple(SM_ARM.rotation_euler))

# P0: pose arana (puente) tal como la usa el juego
SM_SET_POSE(0.0, 0.0)
_w = SM_STATS()
SM_PLACE(-SM_GZ(_w))
B0 = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in SM_PB}

# P1: desplomada, de espaldas, brazos y piernas abiertos (se reutiliza toda la maquinaria de set_pose cambiando las direcciones)
D_, ang_ = G['D'], G['ang']
_aims0 = G['aims_puente']
HC = G['HC']
_hc0 = {k: list(v) for k, v in HC.items()}


def aims_collapsed(ph):
    A = {'Hips': ang_(E('C_HIPS', 4)), 'Spine': ang_(E('C_SP0', 2)), 'Spine1': ang_(E('C_SP1', 0)),
         'Spine2': ang_(E('C_SP2', -4)), 'Neck': ang_(E('C_NECK', -8)), 'Head': ang_(E('C_HEAD', -10))}
    for sd, k in {'Left': -1.0, 'Right': 1.0}.items():
        A[sd + 'Shoulder'] = D_(0.1, 0.0, k)
        A[sd + 'Arm'] = D_(E('C_ARM_S', 0.28), E('C_ARM_Z', 0.0), k * 1.0)       # abiertos hacia los lados y un poco adelante
        A[sd + 'ForeArm'] = D_(E('C_FARM_S', 0.12), E('C_FARM_Z', 0.0), k * 1.0)
        A[sd + 'Hand'] = D_(0.2, 0.0, k)
        A[sd + 'UpLeg'] = D_(E('C_THIGH_S', -0.78), E('C_THIGH_Z', 0.05), k * E('C_THIGH_X', 0.75))   # abiertas hacia atras
        A[sd + 'Leg'] = D_(E('C_SHIN_S', -0.80), E('C_SHIN_Z', 0.0), k * E('C_SHIN_X', 0.65))
        A[sd + 'Foot'] = D_(-0.6, 0.0, k * 0.8)
        A[sd + 'ToeBase'] = D_(-0.6, 0.0, k * 0.8)
    return A


G['aims_puente'] = aims_collapsed
HC['manoI'][:] = [E('C_HAND_PITCH', 0), 0.0]
HC['manoD'][:] = [E('C_HAND_PITCH', 0), 0.0]
HC['pieI'][:] = [E('C_FOOT_PITCH', -50), 0.0]
HC['pieD'][:] = [E('C_FOOT_PITCH', -50), 0.0]
SM_SET_POSE(0.0, 0.0)
_w = SM_STATS()
SM_PLACE(-float(_w[:, 2].min()))
B1 = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in SM_PB}
G['aims_puente'] = _aims0
for _k, _v in _hc0.items():
    HC[_k][:] = _v


# ---------------------------------------------------------------------------------------------- escena
CELL = (96, 96)
CAM = setup_render()
L.ACT['hero_walk'] = L.load_action(ROOT + '/assets/models/animations/corazon/walk.fbx', 'hero_walk')
HEROFBX = ROOT + '/assets/models/characters/corazon/source/corazon.fbx'

DT = 0.06
G_ = 9.0
SM_K = E('SM_K', '1.45')                     # tamaño en pantalla de la araña respecto al modelo (el juego la pinta ~x1,5)
SM_X, SM_Y = E('SM_X', '0.0'), E('SM_Y', '0.0')
HX0 = 0.0

hero = make_char(HEROFBX, 90, 1.0, (HX0, 0, 0))

sroot = bpy.data.objects.new('sm_root', None)
bpy.context.scene.collection.objects.link(sroot)
SM_ARM.parent = sroot
SM_ARM.matrix_parent_inverse = Matrix.Identity(4)
sroot.scale = (SM_K, SM_K, SM_K)
sroot.rotation_euler = (0, 0, math.radians(-90.0))      # la araña mira (-Y del rig) hacia el heroe (-X)
sroot.location = (SM_X, SM_Y, 0.0)
SM_ARM.scale = (ARM0_SCALE.x, ARM0_SCALE.y, ARM0_SCALE.z * STRETCH)
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


def hero_pose(hp):
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
    if hp.get('twist'):
        rot_bone(hero, 'Spine2', 0, 0, hp['twist'])
    rot_bone(hero, 'Head', 0, hp.get('head', 0))
    if hp.get('pin'):
        for side in ('Left', 'Right'):
            hero_ik['leg' + side][1].influence = 1.0
    update()


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


# ---------------------------------------------------------------------------------------------- la araña: cabeza y cuerpo
def fix_unweighted_vertices(ob):
    me = ob.data
    weighted, unweighted = [], []
    for v in me.vertices:
        (weighted if sum(g.weight for g in v.groups) > 1e-4 else unweighted).append(v)
    if not unweighted or not weighted:
        return
    gnames = {g.index: g.name for g in ob.vertex_groups}
    wco = np.array([v.co[:] for v in weighted])
    for v in unweighted:
        j = int(np.argmin(((wco - np.array(v.co[:])) ** 2).sum(axis=1)))
        for g in weighted[j].groups:
            if g.weight > 1e-4:
                ob.vertex_groups[gnames[g.group]].add([v.index], g.weight, 'REPLACE')
    print('FIX_UNWEIGHTED', ob.name, len(unweighted), 'verts')


CAP_WAX = (0.30, 0.22, 0.15, 1.0)        # cera oscura apagada (corte del cuello), nada de rojo
MAT_BLACK = flat_mat('negro', (0.02, 0.02, 0.025, 1.0))
MAT_W1 = flat_mat('cera_o1', (0.34, 0.26, 0.17, 1.0))
MAT_W2 = flat_mat('cera_o2', (0.22, 0.16, 0.11, 1.0))


def split_head(ob, thr=0.5, jag_amp=E('JAG', '0.014')):
    """Parte la malla skinned en (cabeza, cuerpo) por el peso del hueso Head; el anillo de corte se tapa con cera oscura
    segun su plano (PCA): el cuello de la araña no es vertical."""
    import bmesh
    from mathutils.geometry import convex_hull_2d
    me = ob.data
    gi = ob.vertex_groups[P + 'Head'].index
    wmap = {v.index: next((g.weight for g in v.groups if g.group == gi), 0.0) for v in me.vertices}
    head_faces = set()
    for p in me.polygons:
        vs = p.vertices
        if sum(1 for i in vs if wmap[i] >= thr) * 2 >= len(vs):
            head_faces.add(p.index)
    hv, bv = set(), set()
    for p in me.polygons:
        (hv if p.index in head_faces else bv).update(p.vertices)
    ring = hv & bv
    rp = np.array([me.vertices[i].co[:] for i in ring])
    c0 = rp.mean(axis=0)
    _, _, vt = np.linalg.svd(rp - c0)
    n_l = V(vt[2]); t1 = V(vt[0]); t2 = V(vt[1])
    hc = V(np.array([me.vertices[i].co[:] for i in (hv - bv)]).mean(axis=0))
    if n_l.dot(hc - V(c0)) < 0:
        n_l = -n_l
    print('SPLIT ring', len(ring), 'head faces', len(head_faces), 'of', len(me.polygons), 'n', tuple(round(x, 2) for x in n_l))
    disp = {}
    for i in ring:
        c = me.vertices[i].co
        j = math.sin(c.dot(t1) * 55.0 + 1.3) * 0.6 + math.sin(c.dot(t2) * 41.0) * 0.4
        disp[i] = n_l * (jag_amp * j)
    out = {}
    for side in ('head', 'body'):
        nb = ob.copy()
        nb.data = ob.data.copy()
        nb.name = 'sm_' + side
        bpy.context.scene.collection.objects.link(nb)
        nb.hide_render = True
        cap_mat = flat_mat('cera_corte_' + side, CAP_WAX)
        nb.data.materials.append(cap_mat)
        slot = len(nb.data.materials) - 1
        bm = bmesh.new()
        bm.from_mesh(nb.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for i, d in disp.items():
            bm.verts[i].co += d
        kill_head = (side == 'body')
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.index in head_faces) == kill_head], context='FACES')
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
        ncap = 0
        for vs in comps.values():
            if len(vs) < 3 or not (set(v.index for v in vs) & ring):
                continue
            pts = list(vs)
            cc = sum((v.co for v in pts), V((0, 0, 0))) / len(pts)
            hull = convex_hull_2d([V(((v.co - cc).dot(t1), (v.co - cc).dot(t2))) for v in pts])
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
            ncap += len(nf)
        bm.normal_update()
        bm.to_mesh(nb.data)
        bm.free()
        print('SPLIT', side, 'faces', len(nb.data.polygons), 'cap', ncap)
        out[side] = nb
    ob.hide_render = True
    ob.hide_viewport = True
    return out['head'], out['body']


fix_unweighted_vertices(SM_MESH)
HEAD_SKIN, BODY_SKIN = split_head(SM_MESH)


def bone_blend(u_torso, u_arm, u_leg, delays=None):
    """Mezcla de pose P0 (puente) -> P1 (desplomada) por hueso: torso, brazos y piernas con su propio avance."""
    for pb in SM_PB:
        n = pb.name.replace(P, '')
        if n.startswith(('LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm', 'LeftHand', 'RightHand')):
            u = u_arm
        elif n.startswith(('LeftUpLeg', 'RightUpLeg', 'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot', 'LeftToe', 'RightToe')):
            u = u_leg
        else:
            u = u_torso
        l0, q0, s0 = B0[pb.name]
        l1, q1, s1 = B1[pb.name]
        if q0.dot(q1) < 0:
            q1 = -q1
        pb.location = l0.lerp(l1, u)
        pb.rotation_quaternion = q0.slerp(q1, u)
        pb.scale = s0.lerp(s1, u)
    update()


def mesh_pts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    vs, _ = eval_world_mesh(ob, dg)
    return vs


def min_z(ob):
    return min(v.z for v in mesh_pts(ob))


def centroid(vs):
    return sum(vs, V((0, 0, 0))) / len(vs)


# suelo del puente: manos y pies (la orla de la tunica cuelga por debajo y no cuenta)
bone_blend(0, 0, 0)
sroot.location.z = 0.0
update()
G_CONTACT_Z0 = None
_w0 = SM_STATS()                    # malla completa evaluada (original, oculta pero evaluable por G)
G_CONTACT_Z0 = float(SM_GZ(_w0))
Z0 = -G_CONTACT_Z0
print('SUELO puente z', round(Z0, 4))


def arana_pose(u_torso, u_arm, u_leg, head_delta=V((0, 0, 0)), root=(0.0, 0.0, 0.0), yaw=0.0, ground_blend=None):
    """Coloca la araña. head_delta: desplazamiento de mundo de la cabeza (tiron). root: (dx, dy, dz) de la araña."""
    bone_blend(u_torso, u_arm, u_leg)
    if head_delta.length > 1e-6:
        hb = SM_PB[P + 'Head']
        m = hb.matrix.copy()
        W3i = SM_ARM.matrix_world.to_3x3().inverted()
        m.translation = m.translation + W3i @ head_delta
        hb.matrix = m
        update()
    sroot.rotation_euler = (0, 0, math.radians(-90.0 + yaw))
    sroot.location = (SM_X + root[0], SM_Y + root[1], 0.0)
    update()
    gb = u_torso if ground_blend is None else ground_blend
    zb = min(min_z(BODY_SKIN), min_z(HEAD_SKIN))
    sroot.location.z = (1.0 - gb) * Z0 + gb * (-zb) + root[2]
    update()


# ---------------------------------------------------------------------------------------------- cabeza suelta y particulas
class Spark:
    n = 0

    def __init__(self, origin, vel, size, mat):
        Spark.n += 1
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=(0, 0, -6))
        o = bpy.context.active_object
        o.name = 'cera%d' % Spark.n
        o.data.materials.append(mat)
        o.hide_render = True
        for p in o.data.polygons:
            p.use_smooth = False
        self.o, self.o0, self.v, self.size, self.landed = o, V(origin), V(vel), size, None

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
            self.o.scale = (1.5, 1.5, 0.4)
        self.o.location = p


def burst(n, origin, speed, size, seed, mats):
    rng = random.Random(seed)
    out = []
    for k in range(n):
        d = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 1.0))).normalized()
        out.append(Spark(origin + d * 0.02, d * speed * rng.uniform(0.5, 1.2), size, mats[k % len(mats)]))
    return out


# ---------------------------------------------------------------------------------------------- guion
N_FRAMES = int(E('N_FRAMES', '36'))
RIP_F = 7
THROW_F = 10
LAND_F = 13
HX_G = E('HX_G', '-0.80')           # raiz del heroe al agarrar
VAR = os.environ.get('SM_VAR', 'B')   # A = arranque corto aprobado; B = arranque exagerado


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def collapse_u(i):
    """Avance del desplome (torso, brazos, piernas). Cae desde el arranque; rebote al tocar el suelo."""
    t = (i - RIP_F) / 6.0
    if t <= 0:
        return 0.0, 0.0, 0.0
    ut = smooth(t * 1.05)
    ua = smooth((t - 0.10) * 1.15)
    ul = smooth((t - 0.05) * 1.10)
    return ut, ua, ul


def pull_delta(i):
    """Cuanto se estira el cuello (m, hacia el heroe y un pelin arriba) mientras el heroe tira; 0 antes del agarre."""
    tab = {3: 0.0, 4: 0.05, 5: 0.12, 6: 0.20}
    if VAR == 'B':
        tab = {3: 0.0, 4: 0.06, 5: 0.14, 6: 0.22}
    d = tab.get(i, 0.0) if i < RIP_F else 0.0
    return V((-d, 0.0, d * 0.35))


def body_root(i):
    """Arrastre del cuerpo hacia el heroe durante el tiron y rebote del desplome."""
    tab = {3: 0.0, 4: -0.02, 5: -0.05, 6: -0.08, 7: -0.04}
    dx = tab.get(i, 0.0)
    if i > RIP_F:
        dx = -0.04 + 0.05 * smooth((i - RIP_F) / 8.0)
    if VAR == 'B':
        tb = {3: 0.0, 4: -0.06, 5: -0.14, 6: -0.22, 7: 0.02, 8: 0.14, 9: 0.15, 10: 0.11, 11: 0.07, 12: 0.04}
        dx = tb.get(i, 0.0 if i > 12 else 0.0)
    dz = 0.0
    if i in (14,):
        dz = 0.012
    return (dx, 0.0, dz)


def tremor(i):
    """Tambaleo antes del agarre: se mece sobre el puente."""
    if i >= 4:
        return 0.0
    return 3.0 * math.sin(i * 1.7)


def hp_for(i):
    hx = HX_G
    T = {
        0: dict(hx=hx - 0.28, hbase=('hero_walk', 9), lean=12, spine=6, head=-4, pin=False),
        1: dict(hx=hx - 0.14, hbase=('hero_walk', 13), lean=22, spine=10, head=-6, dz=-0.04, pin=False),
        2: dict(hx=hx - 0.04, lean=34, spine=18, head=-10, dz=-0.15, pin=True),
        3: dict(hx=hx, lean=38, spine=20, head=-12, dz=-0.18, pin=True),
        4: dict(hx=hx - 0.02, lean=30, spine=14, head=-8, dz=-0.15, pin=True),
        5: dict(hx=hx - 0.05, lean=18, spine=8, head=-4, dz=-0.11, pin=True),
        6: dict(hx=hx - 0.08, lean=4, spine=0, head=0, dz=-0.07, pin=True),
        7: dict(hx=hx - 0.11, lean=-12, spine=-8, head=4, dz=-0.03, pin=True),
        8: dict(hx=hx - 0.10, lean=-6, spine=-4, head=2, dz=-0.02, pin=True),
        9: dict(hx=hx - 0.08, lean=4, spine=4, head=-4, dz=-0.04, pin=True),
        THROW_F: dict(hx=hx - 0.06, lean=14, spine=8, head=-8, dz=-0.07, pin=True),
        11: dict(hx=hx - 0.05, lean=10, spine=6, head=-6, dz=-0.06, pin=True),
    }
    if VAR == 'B':
        pd = pull_delta(i).x + (body_root(i)[0] if i < RIP_F else 0.0)
        T = {
            0: T[0], 1: T[1],
            2: dict(hx=hx - 0.06, lean=22, spine=10, head=-8, dz=-0.10, pin=True),
            3: dict(hx=hx - 0.04, lean=16, spine=8, head=-6, dz=-0.08, pin=True),
            4: dict(hx=hx + pd - 0.02, lean=0, spine=0, head=0, dz=-0.10, twist=10, pin=True),
            5: dict(hx=hx + pd - 0.04, lean=-16, spine=-8, head=4, dz=-0.14, twist=22, pin=True),
            6: dict(hx=hx + pd - 0.06, lean=-28, spine=-14, head=8, dz=-0.17, twist=32, pin=True),
            7: dict(hx=hx - 0.42, lean=-34, spine=-16, head=10, dz=-0.18, twist=38, pin=True),
            8: dict(hx=hx - 0.46, lean=-26, spine=-12, head=8, dz=-0.17, twist=30, pin=True),
            9: dict(hx=hx - 0.42, lean=-12, spine=-6, head=2, dz=-0.12, twist=14, pin=True),
            THROW_F: dict(hx=hx - 0.32, lean=6, spine=4, head=-6, dz=-0.08, twist=0, pin=True),
            11: dict(hx=hx - 0.22, lean=10, spine=6, head=-6, dz=-0.06, pin=True),
            12: dict(hx=hx - 0.10, lean=4, spine=2, head=-2, dz=-0.04, pin=True),
        }
    hp = dict(T.get(i, dict(hx=hx - 0.04, lean=0, spine=0, head=0, pin=True)))
    hp.setdefault('hbase', ('hero_walk', 1))
    return hp


HEAD_BAKED = None
HOLD_OFF = V((0, 0, 0))
HEAD_RIP_C = None
HEAD_ROT0 = Matrix.Identity(4)
HEAD_R = 0.10
SPARKS = []
V_THROW = V((0, 0, 0))
HAND_PATH = {}


def head_world_pts():
    return mesh_pts(HEAD_SKIN)


def frame_arana(i):
    ut, ua, ul = collapse_u(i)
    arana_pose(ut, ua, ul, head_delta=pull_delta(i), root=body_root(i), yaw=tremor(i), ground_blend=ut)


# ---- pasada previa: donde esta la cabeza colgante en reposo (para el agarre) y cuanto mide
frame_arana(0)
_hp = head_world_pts()
HEAD_C0 = centroid(_hp)
HEAD_HALF_Y = (max(v.y for v in _hp) - min(v.y for v in _hp)) * 0.5
print('CABEZA reposo', tuple(round(x, 3) for x in HEAD_C0), 'half y', round(HEAD_HALF_Y, 3))
frame_arana(N_FRAMES - 1)
_bp = mesh_pts(BODY_SKIN)
print('CUERPO caido bbox x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (min(v.x for v in _bp), max(v.x for v in _bp),
      min(v.y for v in _bp), max(v.y for v in _bp), min(v.z for v in _bp), max(v.z for v in _bp)))

# particulas: gotas de cera oscura del arranque (1) y del golpe de la cabeza contra el suelo (2). Existen en todos los
# fotogramas (misma topologia); aparcadas ocultas hasta su momento.
PULL_RIP = V((-0.25, 0.0, 0.09)) if VAR == 'A' else V((-0.32, 0.0, 0.12))            # estiramiento del cuello justo antes de soltarse
LAND = V((E('LAND_X', '-0.95'), E('LAND_Y', '-0.50'), 0.0))
rip_sparks = burst(14 if VAR == 'A' else 28, V((-0.6, 0.0, 0.5)), 1.1, 0.011, 31, [MAT_W1, MAT_W2])
land_sparks = burst(7, V((0, 0, 0.1)), 0.8, 0.009, 33, [MAT_W2, MAT_W1])
SPARKS = rip_sparks + land_sparks
SPARK_REL = [V(sp.o0) for sp in rip_sparks]

HEAD_BAKED = None
HEAD_PTS = None
HEAD_C = None


def bake_head():
    """Hornea la cabeza rigida en el instante del arranque (con el cuello estirado) y fija sus datos."""
    global HEAD_BAKED, HEAD_PTS, HEAD_C
    arana_pose(0, 0, 0, head_delta=PULL_RIP, root=body_root(6), yaw=0.0, ground_blend=0.0)
    HEAD_BAKED = bake(HEAD_SKIN, 'sm_cabeza_suelta')
    HEAD_BAKED.hide_render = True
    vs = mesh_pts(HEAD_BAKED)
    HEAD_C = centroid(vs)
    HEAD_PTS = np.array([(v - HEAD_C)[:] for v in vs])
    neck = V(SM_ARM.matrix_world @ SM_PB[P + 'Neck'].tail)
    for sp, rel in zip(rip_sparks, SPARK_REL):
        sp.o0 = neck + rel
    print('CABEZA arrancada centro', tuple(round(x, 3) for x in HEAD_C), 'cuello', tuple(round(x, 3) for x in neck))


def rot_matrix(deg_x=0.0, deg_y=0.0, deg_z=0.0):
    return (Matrix.Rotation(math.radians(deg_z), 3, 'Z') @ Matrix.Rotation(math.radians(deg_y), 3, 'Y')
            @ Matrix.Rotation(math.radians(deg_x), 3, 'X'))


def head_ground_z(R3):
    """Altura del centro de la cabeza para apoyar sobre el suelo con la rotacion R3."""
    q = HEAD_PTS @ np.array(R3).T
    return float(-q[:, 2].min())


HOLD_PATH = {                           # desplazamiento de la cabeza sujeta por la mano derecha respecto al arranque
    7: V((0.00, 0.00, 0.00)),
    8: V((0.05, -0.04, 0.10)),
    9: V((0.08, -0.09, 0.19)),
    THROW_F: V((0.04, -0.17, 0.13)),
}
if VAR == 'B':
    HOLD_PATH = {
        7: V((0.00, 0.00, 0.00)),
        8: V((-0.12, -0.08, 0.24)),
        9: V((-0.22, -0.18, 0.42)),
        THROW_F: V((-0.14, -0.28, 0.30)),
    }
HEAD_SPIN_DEG = E('SPIN_X', '440')


def hold_pos(i):
    return V(HEAD_C) + HOLD_PATH[max(RIP_F, min(i, THROW_F))]


def head_state(i):
    """(centro, rotacion 3x3) de la cabeza arrancada en la celda i >= RIP_F."""
    if i < THROW_F:
        swing = 14.0 * math.sin((i - RIP_F) * 1.3)
        return hold_pos(i), rot_matrix(swing, 0.0, 0.0)
    c0 = hold_pos(THROW_F)
    Rland = rot_matrix(HEAD_SPIN_DEG + 38.0, 0.0, 30.0)
    cland = V((LAND.x, LAND.y, head_ground_z(Rland)))
    T = (LAND_F - THROW_F) * DT
    vel = (cland - c0 - V((0, 0, -0.5 * G_ * T * T))) / T
    t = (i - THROW_F) * DT
    if i < LAND_F:
        c = c0 + vel * t + V((0, 0, -0.5 * G_ * t * t))
        a = t / T
        R = rot_matrix(HEAD_SPIN_DEG * a, 0.0, 30.0 * a)
        return V((c.x, c.y, max(c.z, head_ground_z(R)))), R
    tt = (i - LAND_F) * DT
    tau = 0.16
    d = V((vel.x, vel.y, 0.0)) * 0.55 * tau * (1.0 - math.exp(-tt / tau))
    roll = 38.0 * (1.0 - math.exp(-tt / tau))
    R = rot_matrix(HEAD_SPIN_DEG + roll, 0.0, 30.0)
    hop = 0.05 * math.exp(-tt / 0.10) * math.sin(math.pi * min(1.0, tt / 0.16))
    return V((cland.x + d.x, cland.y + d.y, head_ground_z(R) + max(0.0, hop))), R


def head_matrix(i):
    c, R = head_state(i)
    return Matrix.Translation(c) @ R.to_4x4() @ Matrix.Translation(-V(HEAD_C))


def grab_points(c, ry=None):
    r = (HEAD_HALF_Y if ry is None else ry) * 0.95
    return c + V((0.0, r, 0.0)), c + V((0.0, -r, 0.0))


# ---------------------------------------------------------------------------------------------- export GLB
SCENE_OFF = Matrix.Translation(V((-SM_X, -SM_Y, 0.0)))


def export_glb(path, slots):
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    tmp = []
    for name, o, vis in slots:
        if o is None or o.type != 'MESH':
            continue
        eo = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(eo, preserve_all_data_layers=True, depsgraph=dg)
        me.name = name
        no = bpy.data.objects.new(name, me)
        M = SCENE_OFF @ o.matrix_world.copy()
        if not vis:
            M = M @ Matrix.Scale(1e-5, 4)
        no.matrix_world = M
        bpy.context.scene.collection.objects.link(no)
        tmp.append((no, me))
    bpy.ops.object.select_all(action='DESELECT')
    for no, _ in tmp:
        no.select_set(True)
    if tmp:
        bpy.context.view_layer.objects.active = tmp[0][0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_materials='EXPORT', export_yup=True,
                              export_animations=False, export_apply=False)
    for no, me in tmp:
        bpy.data.objects.remove(no, do_unlink=True)
        bpy.data.meshes.remove(me)


def quick_render(path, ctr=V((-0.35, 0.05, 0.4)), az=45.0, ortho=2.6, res=384, elev=30.0):
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = res
    cam = CAM
    a, e = math.radians(az), math.radians(elev)
    pos = ctr + V((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 8.0
    cam.location = pos
    cam.rotation_euler = (ctr - pos).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = ortho
    sc.display.shading.light = 'FLAT'
    render_to(path)


# ---------------------------------------------------------------------------------------------- bucle de fotogramas
if FRAMES_ARG == 'all':
    frames = list(range(N_FRAMES))
else:
    frames = [int(x) for x in FRAMES_ARG.split(',')]


def hero_hands_for(i, hc):
    """Objetivos de las manos del heroe en la celda i (o None)."""
    if 2 <= i < RIP_F:
        c = hc if hc is not None else HEAD_C0
        if i == 2:
            c = HEAD_C0 + V((-0.04, 0, 0.05))
        gl, gr = grab_points(c)
        return {'Left': gl, 'Right': gr}
    if RIP_F <= i <= THROW_F:
        c = hold_pos(i)
        gl, gr = grab_points(c)
        t = {'Right': gr}
        if i == RIP_F:
            t['Left'] = gl
        return t
    return None


for i in frames:
    if i >= RIP_F and HEAD_BAKED is None:
        bake_head()
    frame_arana(i)
    hc = centroid(head_world_pts()) if i < RIP_F else None
    hero_pose(hp_for(i))
    tg = hero_hands_for(i, hc)
    if tg:
        gaps = grip(tg)
    else:
        gaps = {}
        for side in ('Left', 'Right'):
            hero_ik[side][1].influence = 0.0
        update()
    head_ob = HEAD_SKIN
    if i >= RIP_F:
        head_ob = HEAD_BAKED
        HEAD_SKIN.hide_render = True
        HEAD_BAKED.matrix_world = head_matrix(i)
    # gotas: arranque desde RIP_F; aterrizaje de la cabeza en LAND_F
    for sp in rip_sparks:
        sp.place((i - RIP_F) * DT)
    if HEAD_BAKED is not None:
        cl = head_state(LAND_F)[0]
        for sp in land_sparks:
            sp.o0 = V((cl.x, cl.y, 0.06))
    for sp in land_sparks:
        sp.place((i - LAND_F) * DT)
    update()
    _hc = centroid(mesh_pts(head_ob)); _bb = mesh_pts(BODY_SKIN)
    print('FRAME', i, 'gaps', gaps, 'head', tuple(round(x, 3) for x in _hc),
          'body x %.2f..%.2f z %.2f..%.2f' % (min(v.x for v in _bb), max(v.x for v in _bb), min(v.z for v in _bb), max(v.z for v in _bb)))
    sparks_o = [sp.o for sp in SPARKS]
    if QUICK_DIR:
        os.makedirs(QUICK_DIR, exist_ok=True)
        hid = [(o, o.hide_render) for o in [hero.mesh, BODY_SKIN, head_ob]]
        for o, _ in hid:
            o.hide_render = False
        for nm, az, el in (('a', 0.0, 30.0), ('b', 300.0, 30.0), ('t', 0.0, 89.0)):
            quick_render(os.path.join(QUICK_DIR, 'q%02d_%s.png' % (i, nm)), az=az, elev=el)
        for o, h in hid:
            o.hide_render = h
    if GLB_DIR:
        os.makedirs(GLB_DIR, exist_ok=True)
        slots = [(hero.mesh.name + '_baked', hero.mesh, True), ('body', BODY_SKIN, True), ('head', head_ob, True)]
        for k, sp in enumerate(SPARKS):
            slots.append(('spark%02d' % k, sp.o, not sp.o.hide_render))
        export_glb(os.path.join(GLB_DIR, 'f%02d.glb' % i), slots)
        if i == N_FRAMES - 1:    # fotograma de restos: cuerpo espatarrado y cabeza, sin heroe ni gotas
            export_glb(os.path.join(GLB_DIR, 'f%02d.glb' % N_FRAMES),
                       [(nm, ob, nm in ('body', 'head')) for nm, ob, _ in slots])
print('OK', frames)
