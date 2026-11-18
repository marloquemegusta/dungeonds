# OPCION B: le arranca la cruz, lo tumba boca abajo de una patada y le deja caer encima la cruz, que lo aplasta.
# (se ejecuta dentro de ds_remate_cireneo_seq.py: comparte su espacio de nombres)
HYB = -0.22       # el heroe va por delante del cuerpo caido (lado camara) para no quedar tapado
GRIPZ = 20        # las manos agarran la parte baja del palo: la cruz se extiende hacia delante


def kick_legs():
    """Pierna derecha extendida al frente (patada), izquierda recogida."""
    bend(hero, 'RightUpLeg', -84)
    bend(hero, 'RightLeg', -8)
    bend(hero, 'LeftUpLeg', 30)
    bend(hero, 'LeftLeg', 70)


def tuck_legs():
    bend(hero, 'RightUpLeg', -42)
    bend(hero, 'RightLeg', 72)
    bend(hero, 'LeftUpLeg', -16)
    bend(hero, 'LeftLeg', 56)


def cross_held(grip, up, bar=V((0, 1, 0)), sep=0.05, one_hand=None):
    """Las manos del heroe en el palo (a `grip` de mundo) y la cruz colocada ahi. `one_hand` = 'Left'/'Right' suelta la otra."""
    bdir = V(bar).normalized()
    for s, sign in (('Left', 1), ('Right', -1)):
        if one_hand is not None and s != one_hand:
            hero_ik[s][1].influence = 0.0
            continue
        hero_ik[s][0].location = V(grip) + bdir * sep * sign
        hero_ik[s][1].influence = 1.0
    update()
    if one_hand is None:
        gp = (head_world(hero, 'LeftHand') + head_world(hero, 'RightHand')) * 0.5
    else:
        gp = head_world(hero, one_hand + 'Hand')
    cruz_place(gp, up, bar, GRIPZ)


def prone(ang, dz, dx=0.10, rz=0.0):
    """Cuerpo boca abajo: gira alrededor de los dedos de los pies y se desplaza hacia +X."""
    cir_pose(frame=9, hips_pitch=0, feet=feet_at(0, 0, 0))
    pv = toes_pivot() + V((dx, 0, 0))
    root_matrix(cir, pivot=pv, ry=ang, rz=rz, trans=(dx, 0, dz))


def frame_B(i):
    reset_frame()
    if i == 0:
        cir_pose(frame=6, hips_pitch=2, head=4)
        hero_pose(-0.60, ('hero_walk', 9), hips_lean=16, spine=8, head=-6, hy=-0.26)
    elif i == 1:
        # se acerca y agarra la cruz por el palo
        cir_pose(frame=8, hips_pitch=4, head=6)
        hero_pose(-0.52, ('hero_walk', 1), hips_lean=30, spine=16, head=-12, hips_dz=-0.05, hy=-0.18)
        tail = cruz_attached(cir.arm) @ V((0, 5, 38))
        for s, p in zip(('Left', 'Right'), (tail + V((0, 0.05, 0)), tail - V((0, 0.05, 0)))):
            hero_ik[s][0].location = p
            hero_ik[s][1].influence = 1.0
        update()
    elif i == 2:
        # tiron: la cruz se despega y el Cireneo se arquea
        cir_pose(frame=13, hips_pitch=-4, hips_dx=-0.03, spine=-20, head=-12)
        cir_arms((-0.4, 1, 0.2), (-0.4, -1, 0.2))
        hero_pose(-0.46, ('hero_walk', 1), hips_lean=-8, spine=-8, head=-4, hy=-0.20)
        Ma = cruz_attached(cir.arm).copy()
        hold((0.0, 0.0, 0.20), V((-0.35, 0.25, 0.90)), GRIPZ)
        Mf = cir.cruz.matrix_world.copy()
        cruz_lerp_free(Ma, Mf, 0.6)
        burst(cruz_attached(cir.arm) @ V((0, 5, 44)), DT * 0.4, 'astilla', 6, 0.5, up=0.6, seed=11)
    elif i == 3:
        # la levanta y carga la patada
        cir_pose(frame=14, hips_pitch=4, hips_dz=-0.01, spine=4, head=4, feet=feet_at(0.02, 0, 0))
        cir_arms((-0.5, 1, 0.5), (-0.5, -1, 0.5))
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=14, spine=8, head=-2, hy=-0.26, spin=-10)
        cross_held((-0.10, 0.02, 0.58), V((-0.18, 0.10, 0.98)), one_hand='Left')
    elif i == 4:
        # patada voladora en la espalda
        cir_pose(frame=15, hips_pitch=12, hips_dz=-0.02, hips_dx=0.04, spine=12, head=10,
                 feet=feet_at(0.05, 0, 0))
        cir_arms((-0.7, 1, 0.3), (-0.7, -1, 0.3))
        hero_pose(-0.40, ('hero_walk', 1), hips_lean=2, spine=2, head=-2, hy=-0.34, hips_dz=0.09,
                  legs_planted=False, airborne=kick_legs, spin=-8)
        cross_held((-0.12, 0.04, 0.58), V((-0.30, 0.15, 0.94)), one_hand='Left')
        burst(V((0.02, -0.05, 0.42)), DT * 0.2, 'polvo', 4, 0.35, up=0.3, seed=10)
    elif i == 5:
        # cae de bruces
        prone(42, 0.02, dx=0.10)
        cir_arms((-0.6, 1, -0.2), (-0.6, -1, -0.2))
        hero_pose(-0.38, ('hero_walk', 1), hips_lean=20, spine=10, head=-6, hy=-0.24)
        cross_held((-0.04, 0.02, 0.56), V((-0.12, 0.12, 0.98)), one_hand='Left')
    elif i == 6:
        prone(72, 0.06, dx=0.12)
        cir_arms((0.4, 1, -0.7), (0.4, -1, -0.7))
        hero_pose(-0.32, ('hero_walk', 1), hips_lean=-2, spine=-2, head=0, hy=-0.22)
        cross_held((0.0, 0.0, 0.46), V((0.55, 0.0, 0.84)), one_hand='Left')
    elif i == 7:
        # la cruz, horizontal y alta, sobre la espalda del caido
        prone(90, 0.085, dx=0.12)
        cir_arms((0.5, 1, -0.9), (0.5, -1, -0.9))
        hero_pose(-0.28, ('hero_walk', 1), hips_lean=-4, spine=-4, head=0, hy=-0.22)
        cross_held((-0.08, 0.0, 0.60), V((1, 0, 0)))
    elif i == 8:
        # la suelta: cae plana
        prone(92, 0.075, dx=0.12)
        cir_arms((0.5, 1, -1.0), (0.5, -1, -1.0))
        hero_pose(-0.24, ('hero_walk', 1), hips_lean=8, spine=4, head=-2, hy=-0.22)
        for s in ('Left', 'Right'):
            hero_ik[s][1].influence = 0.0
        update()
        cruz_place((0.00, 0.0, 0.50), V((1, 0, 0)), V((0, 1, 0)), GRIPZ)
    elif i == 9:
        # impacto: la cruz aplasta la espalda
        prone(94, 0.045, dx=0.12)
        cir_arms((0.4, 1, -1.0), (0.4, -1, -1.0))
        hero_pose(-0.18, ('hero_walk', 1), hips_lean=16, spine=8, head=-6, hy=-0.22)
        for s in ('Left', 'Right'):
            hero_ik[s][1].influence = 0.0
        update()
        cruz_place((0.12, 0.0, 0.205), V((1, 0, 0)), V((0, 1, 0)), GRIPZ)
        burst(V((0.30, 0, 0.16)), DT * 0.3, 'astilla', 12, 0.9, up=1.0, seed=12)
        burst(V((0.32, 0, 0.12)), DT * 0.3, 'polvo', 8, 0.55, up=0.35, seed=13)
        burst(V((0.36, 0, 0.10)), DT * 0.3, 'sangre', 5, 0.35, up=0.5, seed=14)
    elif i == 10:
        prone(94, 0.043, dx=0.12)
        cir_arms((0.3, 1, -0.9), (0.3, -1, -0.9))
        hero_pose(-0.36, ('hero_walk', 1), hips_lean=8, spine=4, head=-2, hy=-0.22)
        cruz_place((0.12, 0.0, 0.20), V((1, 0, 0)), V((0, 1, 0)), GRIPZ)
        burst(V((0.30, 0, 0.14)), DT * 1.6, 'astilla', 10, 0.9, up=1.0, seed=12)
        burst(V((0.32, 0, 0.10)), DT * 1.6, 'polvo', 8, 0.55, up=0.35, seed=13)
        burst(V((0.36, 0, 0.09)), DT * 1.6, 'sangre', 4, 0.35, up=0.5, seed=14)
    else:
        k = i - 11
        prone(94, 0.043, dx=0.12)
        cir_arms((0.3, 1, -0.9), (0.3, -1, -0.9))
        hero_pose(-0.36 - 0.26 * min(1.0, (k + 1) / 2.0), ('hero_walk', 1), hips_lean=4 - 2 * k,
                  spine=2 - 1 * k, head=0, hy=-0.22)
        ang = 2.5 * math.cos(k * 1.7) * (0.5 ** k)
        up = Matrix.Rotation(math.radians(ang), 3, 'Y') @ V((1, 0, 0))
        cruz_place((0.12, 0.0, 0.20), up, V((0, 1, 0)), GRIPZ)
        burst(V((0.30, 0, 0.12)), DT * (2.0 + k), 'polvo', 8, 0.55, up=0.35, seed=13)
        burst(V((0.30, 0, 0.12)), DT * (2.0 + k), 'astilla', 6, 0.9, up=1.0, seed=12)


FRAMES['B'] = (frame_B, 13)
KEY['B'] = 9
