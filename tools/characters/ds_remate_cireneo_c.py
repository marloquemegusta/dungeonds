# OPCION C (propia): el heroe arranca la cruz y la blande como una guadana (barrido horizontal) que derriba al Cireneo;
# despues la clava de pie junto al cuerpo. Silueta final: cruz vertical plantada con el cuerpo tendido a su pie,
# nada que ver con la estocada diagonal (A) ni con la cruz plana (B).
# (se ejecuta dentro de ds_remate_cireneo_seq.py: comparte su espacio de nombres)
HYC = -0.24


def body_c(ang, dz, dx, rz):
    """Cuerpo que vuelca alrededor de los dedos de los pies (se queda pegado al suelo) y gira sobre la vertical."""
    cir_pose(frame=9, hips_pitch=0, feet=feet_at(0, 0, 0))
    pv = toes_pivot() + V((dx, 0, 0))
    root_matrix(cir, pivot=pv, ry=ang, rz=rz, trans=(dx, 0, dz))


def plant_cross(x, y, bar):
    cruz_place((x, y, 0.58), V((0, 0, 1)), bar, 58)


def frame_C(i):
    reset_frame()
    if i == 0:
        cir_pose(frame=6, hips_pitch=2, head=4)
        hero_pose(-0.68, ('hero_walk', 9), hips_lean=18, spine=8, head=-6, hy=-0.26)
    elif i == 1:
        # agarra la cruz por el palo
        cir_pose(frame=9, hips_pitch=4, head=5)
        hero_pose(-0.52, ('hero_walk', 1), hips_lean=30, spine=16, head=-12, hips_dz=-0.05, hy=-0.18)
        tail = cruz_attached(cir.arm) @ V((0, 5, 34))
        for s, p in zip(('Left', 'Right'), (tail + V((0, 0.05, 0)), tail - V((0, 0.05, 0)))):
            hero_ik[s][0].location = p
            hero_ik[s][1].influence = 1.0
        update()
    elif i == 2:
        # tiron: se la arranca y el Cireneo se arquea
        cir_pose(frame=13, hips_pitch=-4, hips_dx=-0.04, spine=-20, head=-12)
        cir_arms((-0.4, 1, 0.2), (-0.4, -1, 0.2))
        hero_pose(-0.46, ('hero_walk', 1), hips_lean=-8, spine=-8, head=-4, hy=-0.20)
        Ma = cruz_attached(cir.arm).copy()
        hold((0.0, 0.0, 0.18), V((-0.35, 0.30, 0.88)), 18)
        Mf = cir.cruz.matrix_world.copy()
        cruz_lerp_free(Ma, Mf, 0.6)
        burst(cruz_attached(cir.arm) @ V((0, 5, 44)), DT * 0.4, 'astilla', 6, 0.5, up=0.6, seed=21)
    elif i == 3:
        # molinete: gira el cuerpo y se lleva la cruz al otro lado
        cir_pose(frame=14, hips_pitch=-6, spine=-8, head=-2, feet=feet_at(0.04, 0, 0.02))
        cir_arms((-0.2, 1, 0.4), (-0.2, -1, 0.4))
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=6, spine=4, head=-2, hy=-0.22, spin=-48)
        hold((-0.02, 0.03, 0.16), V((-0.28, 0.42, 0.86)), 20)
    elif i == 4:
        # cargado atras, a punto de barrer
        cir_pose(frame=15, hips_pitch=0, spine=0, head=2, feet=feet_at(0.02, 0, 0.01))
        cir_arms((-0.5, 1, 0.5), (-0.5, -1, 0.5))
        hero_pose(-0.42, ('hero_walk', 1), hips_lean=10, spine=6, head=-2, hy=-0.22, spin=-14)
        hold((0.0, 0.02, 0.10), V((-0.05, 0.78, 0.62)), 16)
    elif i == 5:
        # impacto: la cruz barre el costado a media altura
        cir_pose(frame=16, hips_pitch=8, spine=-16, head=-10, feet=feet_at(0.03, 0, 0))
        cir_arms((-0.9, 1, 0.1), (-0.9, -1, -0.3))
        body_c(24, 0.02, 0.04, -8)
        hero_pose(-0.38, ('hero_walk', 1), hips_lean=4, spine=2, head=-2, hy=-0.24, spin=12)
        hold((0.06, 0.0, -0.02), V((0.97, 0.05, 0.18)), 14)
        burst(V((0.16, 0.0, 0.42)), DT * 0.3, 'sangre', 5, 0.4, up=0.6, seed=22)
    elif i == 6:
        # sigue el barrido; el cuerpo vuelca de lado
        cir_pose(frame=16, hips_pitch=0, spine=-8, head=-6)
        cir_arms((-1.0, 1, 0.0), (-1.0, -1, -0.4))
        body_c(56, 0.04, 0.05, -19)
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=-2, spine=-2, head=0, hy=-0.24, spin=34)
        hold((0.04, 0.0, 0.04), V((0.55, -0.70, 0.45)), 14)
    elif i == 7:
        cir_pose(frame=16, hips_pitch=0, spine=-4, head=-2)
        cir_arms((-1.0, 1, -0.2), (-1.0, -1, -0.5))
        body_c(82, 0.06, 0.05, -28)
        hero_pose(-0.50, ('hero_walk', 1), hips_lean=4, spine=2, head=0, hy=-0.24, spin=44)
        hold((0.0, 0.0, 0.02), V((0.20, -0.95, 0.24)), 14)
    elif i == 8:
        # aterriza tendido, de costado
        cir_pose(frame=16, hips_pitch=0, spine=0, head=4)
        cir_arms((-1.0, 1, -0.4), (-1.0, -1, -0.6))
        body_c(92, 0.045, 0.05, -32)
        hero_pose(-0.56, ('hero_walk', 1), hips_lean=6, spine=4, head=-2, hy=-0.24, spin=26)
        for s in ('Left', 'Right'):
            hero_ik[s][1].influence = 0.0
        update()
        cruz_place((0.02, 0.34, 0.07), V((0.85, -0.30, 0.12)), V((0.20, 0.95, 0.0)), 40)
        burst(V((0.30, 0.06, 0.06)), DT * 0.4, 'polvo', 8, 0.5, up=0.3, seed=23)
    elif i == 9:
        # se recompone y levanta la cruz para clavarla
        cir_pose(frame=16, hips_pitch=0, spine=0, head=4)
        cir_arms((-1.0, 1, -0.5), (-1.0, -1, -0.7))
        body_c(92, 0.045, 0.05, -32)
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=8, spine=4, head=-2, hy=-0.24)
        hold((-0.04, 0.02, 0.16), V((0.05, 0.20, 0.98)), 58)
    elif i == 10:
        # la clava de pie detras del cuerpo
        cir_pose(frame=16, hips_pitch=0, spine=0, head=4)
        cir_arms((-1.0, 1, -0.5), (-1.0, -1, -0.7))
        body_c(92, 0.045, 0.05, -32)
        hero_pose(-0.34, ('hero_walk', 1), hips_lean=16, spine=9, head=-7, hy=-0.24)
        bar = V((0.22, 0.97, 0.0))
        for s, p in zip(('Left', 'Right'), (V((-0.20, 0.30, 0.58)), V((-0.20, 0.14, 0.58)))):
            hero_ik[s][0].location = p
            hero_ik[s][1].influence = 1.0
        update()
        plant_cross(-0.20, 0.22, bar)
        burst(V((-0.20, 0.22, 0.04)), DT * 0.3, 'polvo', 5, 0.3, up=0.2, seed=24)
    elif i == 11:
        cir_pose(frame=16, hips_pitch=0, spine=0, head=4)
        cir_arms((-1.0, 1, -0.5), (-1.0, -1, -0.7))
        body_c(92, 0.045, 0.05, -32)
        hero_pose(-0.50, ('hero_walk', 1), hips_lean=8, spine=4, head=-2, hy=-0.24)
        for s in ('Left', 'Right'):
            hero_ik[s][1].influence = 0.0
        update()
        ang = 2.0 * math.cos(1.4)
        plant_cross(-0.20, 0.22, Matrix.Rotation(math.radians(ang), 3, 'Y') @ V((0.22, 0.97, 0.0)))
    else:
        cir_pose(frame=16, hips_pitch=0, spine=0, head=4)
        cir_arms((-1.0, 1, -0.5), (-1.0, -1, -0.7))
        body_c(92, 0.045, 0.05, -32)
        hero_pose(-0.62, ('hero_walk', 1), hips_lean=2, spine=1, head=0, hy=-0.22)
        for s in ('Left', 'Right'):
            hero_ik[s][1].influence = 0.0
        update()
        plant_cross(-0.20, 0.22, V((0.22, 0.97, 0.0)))


FRAMES['C'] = (frame_C, 13)
KEY['C'] = 5
