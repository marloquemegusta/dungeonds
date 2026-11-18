# OPCION B: lo tumba boca abajo (patada voladora a la espalda) y le deja caer encima su propia cruz, que lo aplasta.
# (se ejecuta dentro de proto_remate_cireneo_seq.py: comparte su espacio de nombres)


def cir_prone(ry, trans_z=None, sz=1.0, spine=-14, head=-18):
    """Cireneo cayendo hacia delante (ry 0..90) con la pose recta; sz < 1 lo aplasta contra el suelo."""
    cir_pose(frame=9, hips_pitch=-16, spine=spine, head=head, feet=feet_at(0, 0, 0, 0.07))
    cir_arms((0.0, 0.3, -1), (0.0, -0.3, -1))
    cir.root.matrix_world = Matrix.Rotation(math.radians(90), 4, 'Z')
    pv = toes_pivot()
    tz = trans_z if trans_z is not None else 0.075 * min(1.0, ry / 90.0)
    root_matrix(cir, pivot=pv, ry=ry, trans=(0, 0, tz), sz=sz)


def back_pt(dz=0.0):
    p = head_world(cir, 'Spine1')
    return V((p.x, p.y, p.z + dz))


def tail_hands(hx_, hy_, tail_z=12):
    """Las manos del heroe en el pie del palo de la cruz (aun atada)."""
    tail = cruz_attached(cir.arm) @ V((0, 5, tail_z))
    for s, p in zip(('Left', 'Right'), (tail + V((0, 0.045, 0)), tail - V((0, 0.045, 0)))):
        hero_ik[s][0].location = p
        hero_ik[s][1].influence = 1.0
    update()


HYB = -0.12


def frame_B(i):
    reset_frame()
    if i == 0:
        cir_pose(frame=8, hips_pitch=2, head=4)
        hero_pose(-0.42, ('hero_walk', 9), hips_lean=18, spine=8, head=-6, hy=-0.18)
    elif i == 1:
        # salto: el heroe despega con los pies por delante
        cir_pose(frame=10, hips_pitch=4, head=4)
        hero_pose(-0.40, ('hero_walk', 13), hips_lean=-30, spine=-10, head=-4, hips_dz=0.14, hy=-0.14, legs_planted=False,
                  airborne=tuck(hero, -70, -55, 25, 35))
    elif i == 2:
        # contacto: las dos botas en la espalda (cruz) del Cireneo
        cir_pose(frame=11, hips_pitch=14, hips_dx=0.03, spine=-10, head=-14, feet=feet_at(0.0, 0, 0, 0.02))
        hero_pose(-0.36, ('hero_walk', 13), hips_lean=-58, spine=-14, head=-4, hips_dz=0.26, hy=-0.10, legs_planted=False,
                  airborne=tuck(hero, -92, -84, 4, 12))
        snap_foot(cruz_attached(cir.arm) @ V((0, 5, 30)), 'Left', V((-0.03, -0.02, 0.0)))
    elif i == 3:
        # el Cireneo se va de cara; el heroe cae de pie detras
        cir_prone(38)
        hero_pose(-0.33, ('hero_walk', 1), hips_lean=14, spine=10, head=-6, hips_dz=-0.10, hy=-0.10)
        burst(V((-0.05, 0, 0.35)), DT * 0.5, 'polvo', 5, 0.3, up=0.3, seed=3)
        burst(V((-0.05, 0, 0.35)), DT * 0.5, 'astilla', 6, 0.5, up=0.5, seed=1)
    elif i == 4:
        cir_prone(88)
        hero_pose(-0.36, ('hero_walk', 1), hips_lean=22, spine=14, head=-8, hips_dz=-0.08, hy=-0.14)
        tail_hands(0, 0)
        burst(V((0.30, 0, 0.06)), DT * 0.8, 'polvo', 8, 0.6, up=0.2, seed=7)
    elif i == 5:
        cir_prone(90)
        hero_pose(-0.40, ('hero_walk', 1), hips_lean=24, spine=16, head=-8, hips_dz=-0.10, hy=-0.14)
        tail_hands(0, 0)
        burst(V((0.30, 0, 0.06)), DT * 1.6, 'polvo', 8, 0.6, up=0.2, seed=7)
    elif i == 6:
        # tiron: arranca la cruz de la espalda
        cir_prone(90)
        Ma = cruz_attached(cir.arm).copy()
        hero_pose(-0.42, ('hero_walk', 1), hips_lean=-10, spine=-12, head=-6, hips_dz=-0.04, hy=-0.14)
        hold((0.05, 0, 0.02), V((0.93, 0, 0.36)), 12)
        Mf = cir.cruz.matrix_world.copy()
        cruz_lerp_free(Ma, Mf, 0.6)
        burst(back_pt(0.02), DT * 0.5, 'astilla', 8, 0.5, up=0.8, seed=2)
    elif i == 7:
        # en alto: la cruz horizontal sobre su cabeza, el heroe arqueado
        cir_prone(90)
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=-22, spine=-20, head=6, hips_dz=0.0, hy=-0.14)
        hold((0.03, 0, 0.30), V((0.96, 0, 0.18)), 12)
    elif i == 8:
        # la suelta: cae girando un poco
        cir_prone(90)
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=-12, spine=-10, head=2, hips_dz=0.0, hy=-0.14)
        hold((0.03, 0, 0.30), V((0.96, 0, 0.18)), 12)
        Mup = cir.cruz.matrix_world.copy()
        cross_down_B(0.0, Mup, 0.45)
    elif i == 9:
        # aplasta
        cir_prone(90, sz=0.72)
        hero_pose(-0.46, ('hero_walk', 1), hips_lean=18, spine=10, head=-6, hips_dz=-0.04, hy=-0.14)
        cross_down_B(0.0, None, 1.0, squash=0.72)
        sp = V((0.28, 0, 0.12))
        burst(sp, DT * 0.4, 'polvo', 10, 0.7, up=0.2, seed=5, size_k=1.2)
        burst(sp, DT * 0.4, 'astilla', 10, 0.9, up=1.0, seed=4)
        burst(sp, DT * 0.4, 'sangre', 4, 0.4, up=0.5, seed=6)
    elif i == 10:
        cir_prone(90, sz=0.70)
        hero_pose(-0.46 + (hero_end_x() + 0.46) * 0.5, ('hero_walk', 1), hips_lean=10, spine=6, head=-4, hips_dz=-0.02, hy=-0.14)
        cross_down_B(0.02, None, 1.0, squash=0.70)
        sp = V((0.28, 0, 0.12))
        burst(sp, DT * 1.4, 'polvo', 10, 0.7, up=0.2, seed=5, size_k=1.2)
        burst(sp, DT * 1.4, 'astilla', 8, 0.9, up=1.0, seed=4)
        burst(sp, DT * 1.4, 'sangre', 4, 0.4, up=0.5, seed=6)
    else:
        cir_prone(90, sz=0.70)
        hero_pose(hero_end_x(), ('hero_walk', 1), hips_lean=0, spine=0, head=0, hips_dz=0.0, hy=-0.14)
        cross_down_B(0.0, None, 1.0, squash=0.70)
        sp = V((0.28, 0, 0.12))
        burst(sp, DT * 2.4, 'polvo', 10, 0.7, up=0.2, seed=5, size_k=1.2)
        burst(sp, DT * 2.4, 'astilla', 6, 0.9, up=1.0, seed=4)


def cross_down_B(lift, M_from, t, squash=1.0):
    """Cruz tumbada de plano sobre la espalda del Cireneo (palo hacia la cabeza), con `lift` metros de rebote.
    Si hay M_from, se mezcla con la cruz en alto (t = fraccion de caida)."""
    p = back_pt(0.0)
    z = 0.075 * 2 * squash + 0.045
    cruz_place(V((p.x - 0.14, p.y, z + lift)), V((1, 0, 0)), V((0, 1, 0)), 40)
    if M_from is not None:
        Mf = cir.cruz.matrix_world.copy()
        cruz_lerp_free(M_from, Mf, t)


FRAMES['B'] = (frame_B, 12)
KEY['B'] = 2
