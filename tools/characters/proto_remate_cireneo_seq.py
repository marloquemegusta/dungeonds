# (se ejecuta dentro de proto_remate_cireneo.py: comparte su espacio de nombres)
DT = 0.06
FEET0 = None
# Desplazamiento de camara por opcion (m, en X de mundo): centra en la misma celda la secuencia mas ancha (B: el Cireneo cae
# lejos). El sitio final del heroe es el mismo PIXEL en las tres opciones: HERO_END + desplazamiento.
CAM_DX = {'A': 0.0, 'B': 0.17, 'C': 0.0}
HERO_END = V((-0.50, -0.14, 0.0))


def hero_end_x():
    return HERO_END.x + CAM_DX.get(OPT, 0.0)


def reset_frame():
    cruz_skinned(cir.cruz, cir.arm)
    cir.cruz.parent = cir.arm
    cir.root.matrix_world = Matrix.Rotation(math.radians(90), 4, 'Z')
    parts_reset()
    set_ik(0.0, 0.0)
    place_cam(CAM, AZ, CAM_CENTER + V((CAM_DX.get(OPT, 0.0), 0, 0)))
    update()


def feet_rest():
    global FEET0
    if FEET0 is None:
        cruz_skinned(cir.cruz, cir.arm)
        cir_pose(frame=9, hips_pitch=0)
        FEET0 = {s: W(cir) @ cir.arm.pose.bones[P + s + 'Foot'].head for s in ('Left', 'Right')}
        FEET0 = {s: V((v.x, v.y, v.z)) for s, v in FEET0.items()}
    return FEET0


def feet_at(dx=0.0, dz=0.0, spread=0.0, close=0.0):
    f = feet_rest()
    return {'Left': f['Left'] + V((dx, spread - close, dz)), 'Right': f['Right'] + V((dx, -spread + close, dz))}


def cir_arms(dl, dr):
    """Dirige los brazos del Cireneo (hombro->codo y codo->mano) hacia direcciones de mundo dl/dr (izq +Y, der -Y)."""
    for side, d in (('Left', dl), ('Right', dr)):
        d = V(d).normalized()
        sh = head_world(cir, side + 'Arm')
        aim_bone(cir, side + 'Arm', sh + d)
        el = head_world(cir, side + 'ForeArm')
        aim_bone(cir, side + 'ForeArm', el + d)


def hold(off, up, grip_z, bar=V((0, 1, 0)), sep=0.045):
    """Las dos manos del heroe en un punto delante del pecho (offset de mundo desde su Spine2); la cruz sigue a las manos."""
    ref = head_world(hero, 'Spine2')
    C = ref + V(off)
    bd = V(bar).normalized()
    for s, p in zip(('Left', 'Right'), (C + bd * sep, C - bd * sep)):
        hero_ik[s][0].location = p
        hero_ik[s][1].influence = 1.0
    update()
    hl, hr = head_world(hero, 'LeftHand'), head_world(hero, 'RightHand')
    cruz_place((hl + hr) * 0.5, up, bar, grip_z)


def hold_tip(off, tip, bar=V((0, 1, 0)), sep=0.045):
    """Como hold(), pero la cruz se orienta y se desliza por las manos para que la punta de su palo (el pie) caiga en `tip`."""
    ref = head_world(hero, 'Spine2')
    C = ref + V(off)
    bd = V(bar).normalized()
    for s, p in zip(('Left', 'Right'), (C + bd * sep, C - bd * sep)):
        hero_ik[s][0].location = p
        hero_ik[s][1].influence = 1.0
    update()
    Cg = (head_world(hero, 'LeftHand') + head_world(hero, 'RightHand')) * 0.5
    d = Cg - V(tip)
    cruz_place(Cg, d, bar, d.length * 100.0 - 3.5)


def snap_foot(target, side='Left', extra=V((0, 0, 0))):
    """Desplaza al heroe entero para que su pie caiga justo en `target` (patadas que de verdad conectan)."""
    f = head_world(hero, side + 'Foot')
    hero.root.matrix_world = Matrix.Translation(V(target) + extra - f) @ hero.root.matrix_world
    update()


def toes_pivot():
    f = feet_rest()
    return V(((f['Left'].x + f['Right'].x) * 0.5, 0, 0))


def lying(ch_ry, trans_z=0.07, pitch_pivot=None, spine=-14, head=-18, legs_apart=0.0):
    """Cireneo cuerpo a tierra: pose recta (se quita el encorvamiento del aturdido) y giro rigido hacia delante."""
    cir_pose(frame=9, hips_pitch=-16, spine=spine, head=head, feet=feet_at(0, 0, 0, 0.07 + legs_apart))
    pv = pitch_pivot or toes_pivot()
    cir.root.matrix_world = Matrix.Rotation(math.radians(90), 4, 'Z')
    root_matrix(cir, pivot=pv, ry=ch_ry, trans=(0, 0, trans_z))


def tuck(hero_ch, th_l, th_r, kn_l, kn_r):
    """Piernas en el aire: muslo (negativo = adelante) y rodilla (positivo = pie hacia atras), en ejes de mundo."""
    def f():
        bend(hero_ch, 'LeftUpLeg', th_l)
        bend(hero_ch, 'RightUpLeg', th_r)
        bend(hero_ch, 'LeftLeg', kn_l)
        bend(hero_ch, 'RightLeg', kn_r)
    return f


# =============================================================================================== ejecucion
FRAMES = {}
KEY = {}
for _o in ('a', 'b', 'c'):
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proto_remate_cireneo_%s.py' % _o)
    if os.path.exists(_p):
        exec(open(_p, encoding='utf-8').read())


def run(opt, mode):
    fn, n = FRAMES[opt]
    if mode == 'key':
        idx = [KEY[opt]]
    elif mode == 'all':
        idx = range(n)
    else:
        idx = [int(x) for x in mode.split(',')]
    for i in idx:
        fn(i)
        if os.environ.get('REMATE_DBG'):
            print('DBG', i, {n: tuple(round(x, 2) for x in head_world(cir, n)) for n in ('Hips', 'Head', 'LeftFoot')},
                  'hero', {n: tuple(round(x, 2) for x in head_world(hero, n)) for n in ('Hips', 'Head', 'LeftHand')})
        render_pass(i, OUT)


if OPT == 'probe':
    for f in (1, 5, 9, 13):
        reset_frame()
        cir_pose(frame=f, hips_pitch=0)
        hero_pose(HERO_X, ('hero_walk', 1))
        render_pass(f, OUT)
else:
    run(OPT, MODE)
