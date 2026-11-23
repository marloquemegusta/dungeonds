"""PROTOTIPO v4: remate del Corazon Abierto sobre el Parroco, "Derretirlo desde dentro". Solo GLB para el lab rapido.

Fotogramas de celda (4 ticks cada uno en el juego; 40 + 1 de restos):
   0-1    el heroe de pie, erguido y relajado (fotograma de reposo de corazon_walk_normal; sin guardia)
   2-8    solo su brazo izquierdo se extiende despacio (IK de dos huesos), mano abierta, y atraviesa el pecho
   9-12   la mano se cierra dentro, como agarrando el corazon; del agujero sale un BRILLO (anillos marfil/ambar, rayos cortos iguales)
   11-30  DERRETIDO DE ABAJO ARRIBA: pies y piernas se funden en el charco; el TORSO ENTERO (pecho con la mano, hombros,
          cabeza) se mantiene intacto y baja recto; el brazo del heroe baja con el
   31-38  el torso, ya casi a ras de suelo, se funde en el charco; el heroe saca la mano; el brillo se apaga
   40     RESTOS: charco de cera con el monton, sin heroe ni brillo.
La deformacion se aplica a la malla ya posada (numpy) y se hornea en un GLB por fotograma con la misma topologia.

Uso:
  REMATE_GLB_DIR=<dir> "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
     -P tools/characters/ds_remate_parroco.py -- <raiz_con_assets_reales> <salida> <test|all> [fotogramas,...]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import ds_remate_exvoto_lib as L
from ds_remate_exvoto_lib import *

A_ = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT, MODE = A_[0], A_[1], A_[2]
TEST_F = A_[3] if len(A_) > 3 else '8'
GLB_DIR = os.environ.get('REMATE_GLB_DIR')
K = float(os.environ.get('PAR_K', '1.0'))
N_FRAMES = 40
MC = ROOT + '/assets/models/characters/'

bpy.ops.wm.read_factory_settings(use_empty=True)
hero = make_char(MC + 'corazon/source/corazon.fbx', 90, 1.0, (-0.8, 0.02, 0))
par = make_char(MC + 'exvoto_parroco/exvoto_parroco_walk.fbx', -90, K, (0, 0, 0))
L.ACT['walk'] = load_action(MC + 'corazon/corazon_walk_normal.fbx', 'walk')
L.ACT['standup'] = load_action(MC + 'exvoto_parroco/exvoto_parroco_stand_up.fbx', 'standup')
update()


def fix_unweighted(ob):
    weighted, unw = [], []
    for v in ob.data.vertices:
        (weighted if sum(g.weight for g in v.groups) > 1e-4 else unw).append(v)
    if not unw or not weighted:
        return
    names = {g.index: g.name for g in ob.vertex_groups}
    for v in unw:
        b = min(weighted, key=lambda w: (w.co - v.co).length_squared)
        for g in b.groups:
            if g.weight > 1e-4:
                ob.vertex_groups[names[g.group]].add([v.index], g.weight, 'REPLACE')


fix_unweighted(hero.mesh)
fix_unweighted(par.mesh)


# ------------------------------------------------------------------------------------------------ materiales
def emissive(name, col):
    m = flat_mat(name, col)
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is not None:
        lin = (srgb_lin(col[0]), srgb_lin(col[1]), srgb_lin(col[2]), 1.0)
        try:
            b.inputs['Emission Color'].default_value = lin
            b.inputs['Emission Strength'].default_value = 1.0
        except KeyError:
            pass
    return m


def sm(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def rgb15(r, g, b):
    return (r / 31.0, g / 31.0, b / 31.0, 1.0)


WAX = (0.66, 0.55, 0.47)       # mediana de la textura real del Parroco (exvoto_elite_hombre_basecolor.png)
MAT_CRATER = flat_mat('crater', (0.20, 0.05, 0.04, 1.0))
GL_IVORY = emissive('brillo_marfil', rgb15(29, 25, 19))     # FX_SH_IVORY
GL_GOLD = emissive('brillo_oro', rgb15(27, 20, 11))         # FX_SH_GOLD
GL_AMBER = emissive('brillo_ambar', rgb15(24, 15, 7))       # FX_SH_AMBER
MAT_DROP = flat_mat('goteron', (WAX[0] + 0.04, WAX[1] + 0.03, WAX[2] + 0.02, 1.0))
MAT_PUD_RIM = flat_mat('charco_borde', (0.38, 0.28, 0.22, 1.0))
MAT_PUD = flat_mat('charco', (WAX[0] + 0.04, WAX[1] + 0.03, WAX[2] + 0.02, 1.0))


def mk(name, vs, fs, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in vs], [], [tuple(f) for f in fs])
    for m in mats:
        me.materials.append(m)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True
    return ob


def ico(name, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = False
    o.hide_render = True
    return o


def torus(name, mat, R, r, seg=14, sides=6):
    """Anillo de eje X (se pone alrededor del brazo, que entra al pecho por -X)."""
    vs, fs = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for j in range(sides):
            bb = 2 * math.pi * j / sides
            rr = R + r * math.cos(bb)
            vs.append((r * math.sin(bb), rr * math.cos(a), rr * math.sin(a)))
    for i in range(seg):
        for j in range(sides):
            a0, a1 = i * sides + j, i * sides + (j + 1) % sides
            b0, b1 = ((i + 1) % seg) * sides + j, ((i + 1) % seg) * sides + (j + 1) % sides
            fs.append((a0, a1, b1, b0))
    return mk(name, vs, fs, [mat])


def cone(name, mat, r=0.03):
    vs = [(r * math.cos(k * math.pi / 2), r * math.sin(k * math.pi / 2), 0.0) for k in range(4)] + [(0, 0, 1.0)]
    fs = [(k, (k + 1) % 4, 4) for k in range(4)] + [(3, 2, 1, 0)]
    return mk(name, vs, fs, [mat])


def blob(name, mat, n=22, wob=0.12, seed=3):
    rng = random.Random(seed)
    vs = [(0.0, 0.0, 0.0)]
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = 1.0 + rng.uniform(-wob, wob)
        vs.append((rr * math.cos(a), rr * math.sin(a), 0.0))
    fs = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    return mk(name, vs, fs, [mat])


# ------------------------------------------------------------------------------------------------ poses
def blend(d1, d2, w):
    out = {}
    for n, m1 in d1.items():
        l1, q1, s1 = m1.decompose()
        l2, q2, s2 = d2[n].decompose()
        out[n] = Matrix.LocRotScale(l1.lerp(l2, w), q1.slerp(q2, w), s1.lerp(s2, w))
    return out


BASE = capture(hero, 'walk', 2)      # de pie, pies juntos, brazos colgando


PAR_BASIS = capture(par, 'standup', 47)


def verts(ob):
    update()
    vs, _ = eval_world_mesh(ob, bpy.context.evaluated_depsgraph_get())
    return np.array([(v.x, v.y, v.z) for v in vs], dtype=np.float64)


def par_pose(i):
    apply_basis(par, PAR_BASIS)
    if i < 7:
        rot_bone(par, 'Spine1', rx=3.5 * math.sin(i * 1.3))
    ry = 3.0 * sm((i - 6) / 6.0)
    if ry:
        rot_bone(par, 'Spine', ry=ry * 0.6)
        rot_bone(par, 'Spine2', ry=ry * 0.4)
    if 12 <= i <= 30:
        rot_bone(par, 'Spine1', rx=0.4 * (-1) ** i)       # tiembla por dentro
    return verts(par.mesh)


V0 = par_pose(-1)
par.root.location.z -= V0[:, 2].min()
update()
V0 = par_pose(-1)
H0 = V0[:, 2].max()
CX, CY = float(V0[:, 0].mean()), 0.0
ZC = 0.68
sel = (np.abs(V0[:, 1]) < 0.12) & (np.abs(V0[:, 2] - ZC) < 0.08)
P = np.array([float(V0[sel, 0].min()), 0.0, ZC])

hero.root.location.x = 0.0
apply_basis(hero, BASE)
SH0 = head_world(hero, 'LeftArm')
D0 = float(os.environ.get('PAR_D0', '0.23'))
XC = P[0] + 0.03 - D0 - SH0.x           # el heroe esta SIEMPRE aqui (pies plantados)
print('PARROCO H0', H0, 'P', P, 'C', CX, 'HERO XC', round(XC, 3))

S_MAX = float(os.environ.get('PAR_SMAX', '0.17'))   # cuanto baja el torso rigido (m)
ZCUT = 0.46                 # por debajo: piernas que se funden; por encima: torso que baja entero
T_LEG0, T_LEG1 = 11, 30     # fusion de las piernas
T_TOR0, T_TOR1 = 31, 38     # el torso se funde en el charco
OUT_A, OUT_B = 31, 36       # el heroe saca la mano


def sm(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def s_of(i):
    return S_MAX * sm((i - T_LEG0) / float(T_LEG1 - T_LEG0))


def c_of(i):
    return sm((i - T_TOR0) / float(T_TOR1 - T_TOR0))


FEET_REF = {}
HAND_ERR = []


FING = {'Index': 1.0, 'Middle': 1.0, 'Ring': 1.05, 'Pinky': 1.1}
CURL = {'sign': None}


def finger_basis(d, cu):
    """Mano abierta = reposo del rig (dedos rectos); cerrada = dedos y pulgar flexionados."""
    d = dict(d)
    for side in ('Left',):
        for f, k in FING.items():
            for j, ang in ((1, 55), (2, 70), (3, 50)):
                d[L.P + side + 'Hand' + f + str(j)] = Matrix.Rotation(math.radians(CURL['sign'] * ang * k * cu), 4, 'X')
        for j, ang in ((1, 25), (2, 30), (3, 30)):
            d[L.P + side + 'HandThumb' + str(j)] = Matrix.Rotation(math.radians(CURL['sign'] * ang * cu), 4, 'Y')                 if False else d[L.P + side + 'HandThumb' + str(j)]
    return d


def pick_curl_sign():
    best = None
    for sg in (1.0, -1.0):
        CURL['sign'] = sg
        apply_basis(hero, finger_basis(BASE, 1.0))
        dist = (head_world(hero, 'LeftHandMiddle4') - head_world(hero, 'LeftHand')).length
        if best is None or dist < best[0]:
            best = (dist, sg)
    CURL['sign'] = best[1]
    apply_basis(hero, finger_basis(BASE, 0.0))
    print('CURL sign', best)


pick_curl_sign()
HREST = {}


def hero_pose(i, s):
    w_in = sm((i - 1) / 7.0) if i >= 1 else 0.0
    w_out = sm((i - OUT_A + 1) / float(OUT_B - OUT_A + 1)) if i >= OUT_A else 0.0
    cu = sm((i - 9) / 4.0) * (1.0 - w_out)
    d = finger_basis(BASE, cu)
    hero.root.location.x = XC
    hero.root.location.z = 0.0
    apply_basis(hero, d)
    mn = verts(hero.mesh)[:, 2].min()
    hero.root.location.z = -mn
    update()
    # pies clavados: se compensa con la raiz para que no resbalen entre fotogramas
    h = verts(hero.mesh)
    c = h[h[:, 2] < h[:, 2].min() + 0.03]
    f = (float(c[:, 0].mean()), float(c[:, 1].mean()))
    if 'ref' not in FEET_REF:
        FEET_REF['ref'] = f
    hero.root.location.x += FEET_REF['ref'][0] - f[0]
    hero.root.location.y += FEET_REF['ref'][1] - f[1]
    update()
    # solo el brazo izquierdo trabaja: IK de dos huesos desde el reposo hasta el agujero del pecho, y baja con el torso
    S0 = head_world(hero, 'LeftArm')
    E0 = head_world(hero, 'LeftForeArm')
    Hh = head_world(hero, 'LeftHand')
    if 'rest' not in HREST:
        HREST['rest'] = Hh.copy()
    w = w_in * (1.0 - w_out)
    if w > 1e-3:
        chest = Vector((P[0] + 0.03, 0.0, P[2] - s))
        tgt = HREST['rest'].lerp(chest, w)
        a_, b_ = (E0 - S0).length, (Hh - E0).length
        dv = tgt - S0
        dl = min(dv.length, a_ + b_ - 0.004)
        dr = dv.normalized()
        xx = (a_ * a_ + dl * dl - b_ * b_) / (2 * dl)
        hh = math.sqrt(max(a_ * a_ - xx * xx, 0.0))
        pole = (E0 - S0) - dr * (E0 - S0).dot(dr)
        pole = pole.normalized() if pole.length > 0.02 else Vector((-0.3, 0.4, -1.0)).normalized()
        pole = pole.lerp(Vector((-0.3, 0.4, -1.0)).normalized(), w_in).normalized()
        E = S0 + dr * xx + pole * hh
        aim_bone(hero, 'LeftArm', E)
        aim_bone(hero, 'LeftForeArm', S0 + dr * dl)
        HAND_ERR.append((i, round((head_world(hero, 'LeftHand') - tgt).length, 3)))
        update()


# ------------------------------------------------------------------------------------------------ deformaciones
def dent(V, amt):
    if amt <= 0:
        return V
    V = V.copy()
    d = np.hypot(V[:, 1] - P[1], V[:, 2] - P[2])
    f = np.clip(1 - d / 0.14, 0, 1)
    f = f * f * (3 - 2 * f)
    V[:, 0] += np.where(V[:, 0] < P[0] + 0.10, 0.075 * amt * f, 0.0)
    return V


def melt(V, m):
    """Hundimiento: la altura baja de verdad (a ras de suelo), cabeza y hombros se desploman, la base se ensancha
    a media fusion y al final el monton se recoge sobre el charco."""
    if m <= 0:
        return V
    V = V.copy()
    u = np.clip(V[:, 2] / H0, 0, 1)
    w = (1 + 0.28 * math.sin(math.pi * m) * (1 - u) ** 1.2 + 0.10 * math.sin(math.pi * m)) * (1 - 0.40 * m * m)
    ang = np.arctan2(V[:, 1] - CY, V[:, 0] - CX)
    lump = 1 + 0.10 * math.sin(math.pi * m) * np.sin(5 * ang + 7 * u)
    V[:, 0] = CX + (V[:, 0] - CX) * w * lump
    V[:, 1] = CY + (V[:, 1] - CY) * w * lump
    V[:, 2] = V[:, 2] * (1 - 0.95 * m)
    return V


def descend(V, s):
    """Las piernas se funden (se aplastan y se ensanchan en falda) y el torso baja entero, sin deformarse."""
    if s <= 0:
        return V
    V = V.copy()
    z = V[:, 2].copy()
    f = (ZCUT - s) / ZCUT
    V[:, 2] = np.where(z < ZCUT, z * f, z - s)
    k = s / ZCUT
    wl = 1 + 0.55 * k * np.clip(1 - z / ZCUT, 0, 1) ** 0.8
    ang = np.arctan2(V[:, 1] - CY, V[:, 0] - CX)
    lump = 1 + 0.08 * k * np.clip(1 - z / ZCUT, 0, 1) * np.sin(4 * ang + 5 * z)
    V[:, 0] = CX + (V[:, 0] - CX) * wl * lump
    V[:, 1] = CY + (V[:, 1] - CY) * wl * lump
    return V


def body_t(V, i):
    return melt(descend(V, s_of(i)), c_of(i))


def setv(ob, V):
    ob.data.vertices.foreach_set('co', V.astype(np.float32).ravel())
    ob.data.update()


# ------------------------------------------------------------------------------------------------ actores
PAR = bake(par.mesh, 'parroco_baked')
CRATER = ico('crater', MAT_CRATER)
CR_BASE = np.array([(v.co.x * 0.035 + P[0] + 0.075, v.co.y * 0.11, v.co.z * 0.11 + P[2]) for v in CRATER.data.vertices])
CRATER.data.vertices.foreach_set('co', CR_BASE.astype(np.float32).ravel())
RING_A = torus('anillo_ambar', GL_AMBER, 0.15, 0.042)
RING_I = torus('anillo_marfil', GL_IVORY, 0.11, 0.032)
HALO = ico('halo', GL_GOLD)
SPIKES = [cone('rayo%d' % k, GL_IVORY if k % 2 == 0 else GL_GOLD) for k in range(8)]
DROPS = [ico('gota%d' % k, MAT_DROP) for k in range(8)]
RIM = blob('charco_borde', MAT_PUD_RIM, seed=3)
FILL = blob('charco', MAT_PUD, seed=3)


def V3(*a):
    return Vector(a)


def glow_g(i):
    if i < 8:
        return 0.0
    if i < 14:
        return [0.30, 0.55, 0.75, 0.9, 1.0, 1.0][i - 8]
    if i <= 33:
        return 1.0
    return {34: 0.8, 35: 0.6, 36: 0.42, 37: 0.26, 38: 0.12}.get(i, 0.0)


def export_glb(path, slots):
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    tmp = []
    for name, o, vis in slots:
        eo = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(eo, preserve_all_data_layers=True, depsgraph=dg)
        me.name = name
        no = bpy.data.objects.new(name, me)
        M = o.matrix_world.copy()
        if not vis:
            M = M @ Matrix.Scale(1e-5, 4)
        no.matrix_world = M
        bpy.context.scene.collection.objects.link(no)
        tmp.append((no, me))
    bpy.ops.object.select_all(action='DESELECT')
    for no, _ in tmp:
        no.select_set(True)
    bpy.context.view_layer.objects.active = tmp[0][0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_materials='EXPORT',
                              export_yup=True, export_animations=False, export_apply=False)
    for no, me in tmp:
        bpy.data.objects.remove(no, do_unlink=True)
        bpy.data.meshes.remove(me)


DROP_SPEC = []     # (nacimiento, duracion, tipo, parametro)
for k, b in enumerate((14, 18, 22, 26)):
    DROP_SPEC.append((b, 5, 'brazo', (-0.05 + 0.04 * (k % 2), (-0.045, 0.04, 0.0, 0.025)[k])))
for k, b in enumerate((13, 17, 21, 25)):
    DROP_SPEC.append((b, 5, 'cuerpo', k * 1.7 + 0.5))


def build(i, remnant=False):
    ii = N_FRAMES - 1 if remnant else i
    s = s_of(ii)
    V = par_pose(ii)
    V = dent(V, sm((ii - 6) / 4.0))
    V = body_t(V, ii)
    setv(PAR, V)
    setv(CRATER, body_t(CR_BASE, ii))
    hero_pose(ii, s)
    # brillo: anillo alrededor del brazo en el agujero (sigue al agujero cuando el cuerpo baja bajo el puno)
    g = 0.0 if remnant else glow_g(ii)
    gc = np.array([P[0] + 0.03, 0.0, P[2]])
    gc = body_t(np.array([gc]), ii)[0]
    pulse = 1.0 + 0.10 * math.sin(ii * 1.9) + 0.05 * math.sin(ii * 4.1)
    gs = max(g * pulse, 1e-4)
    Tg = Matrix.Translation(V3(*gc))
    RING_A.matrix_world = Tg @ Matrix.Diagonal((gs, gs, gs, 1))
    RING_I.matrix_world = Matrix.Translation(V3(gc[0] - 0.012, gc[1], gc[2])) @ Matrix.Diagonal((gs, gs, gs, 1))
    HALO.matrix_world = Matrix.Translation(V3(gc[0] + 0.13, gc[1], gc[2])) @ Matrix.Diagonal((0.19 * gs,) * 3 + (1,))
    sp_vis = []
    for k, sp in enumerate(SPIKES):
        phi = k * math.pi / 4 + 0.2
        d = V3(-0.40, math.cos(phi), math.sin(phi)).normalized()
        L_ = (0.19 + 0.02 * math.sin(ii * 2.3 + k)) * g
        q = d.to_track_quat('Z', 'Y')
        start = V3(*gc) + V3(0, math.cos(phi), math.sin(phi)) * 0.13 * gs
        sp.matrix_world = Matrix.Translation(start) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((1, 1, max(L_, 1e-4), 1))
        sp_vis.append(g > 0.05)
    # goterones
    drop_vis = []
    for k, d in enumerate(DROPS):
        b, dur, kind, prm = DROP_SPEC[k]
        t = (ii - b) / float(dur)
        vis = 0.0 <= t < 1.0 and not remnant
        tt = max(0.0, min(1.0, t))
        if kind == 'brazo':
            x, y = P[0] + prm[0], prm[1]
            z0 = P[2] - 0.08 - s
        else:
            rad = 0.20 + 0.10 * s / S_MAX
            x, y = CX + rad * math.cos(prm), CY + rad * math.sin(prm)
            z0 = max(0.12, 0.62 - s)
        z = z0 + (0.03 - z0) * tt * tt
        d.matrix_world = Matrix.Translation(V3(x, y, z)) @ Matrix.Diagonal((0.032, 0.032, 0.06, 1))
        drop_vis.append(vis)
    # charco
    mp = max(0.0, min(1.0, (ii - 11) / 27.0))
    Rr = 0.10 + 0.34 * mp ** 0.8
    RIM.matrix_world = Matrix.Translation(V3(CX, CY, 0.003)) @ Matrix.Diagonal((Rr * 1.09, Rr * 1.09, 1, 1))
    FILL.matrix_world = Matrix.Translation(V3(CX, CY, 0.008)) @ Matrix.Diagonal((Rr, Rr, 1, 1))
    pud_vis = ii >= 12
    glow_vis = g > 0.05
    slots = [(hero.mesh.name + '_baked', hero.mesh, not remnant), ('parroco', PAR, True), ('crater', CRATER, ii >= 7),
             ('anillo_ambar', RING_A, glow_vis), ('anillo_marfil', RING_I, glow_vis), ('halo', HALO, glow_vis)]
    slots += [('rayo%d' % k, s, sp_vis[k]) for k, s in enumerate(SPIKES)]
    slots += [('gota%d' % k, d, drop_vis[k]) for k, d in enumerate(DROPS)]
    slots += [('charco_borde', RIM, pud_vis), ('charco', FILL, pud_vis)]
    return slots


def feet():
    h = verts(hero.mesh)
    c = h[h[:, 2] < h[:, 2].min() + 0.03]
    return c[:, 0].mean(), c[:, 1].mean()


frames = [int(x) for x in TEST_F.split(',')] if MODE == 'test' else list(range(N_FRAMES))
FT = []
for i in frames:
    slots = build(i)
    FT.append(feet())
    if GLB_DIR:
        os.makedirs(GLB_DIR, exist_ok=True)
        export_glb(os.path.join(GLB_DIR, 'f%02d.glb' % i), slots)
        if i == N_FRAMES - 1:
            export_glb(os.path.join(GLB_DIR, 'f%02d.glb' % N_FRAMES), build(i, remnant=True))
    print('FRAME', i, 's %.2f c %.2f' % (s_of(i), c_of(i)), 'glow %.2f' % glow_g(i), 'feet %.3f %.3f' % FT[-1])
fx = [f[0] for f in FT]
fy = [f[1] for f in FT]
print('FEET drift x %.3f y %.3f' % (max(fx) - min(fx), max(fy) - min(fy)))
print('HANDERR', HAND_ERR)
print('OK', frames)
