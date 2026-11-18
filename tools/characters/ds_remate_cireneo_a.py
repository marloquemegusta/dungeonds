# OPCION A: el heroe le arranca la cruz de la espalda y lo atraviesa con ella contra el suelo.
# (se ejecuta dentro de proto_remate_cireneo_seq.py: comparte su espacio de nombres)
HYA = -0.22      # el heroe se pone entre la camara y la cruz para que no lo tape (mismo anclaje en las tres opciones)


def frame_A(i):
    reset_frame()
    TIP = V((0.20, 0.0, -0.035))
    if i <= 2:
        sway = {0: 8, 1: 10, 2: 12}[i]
        cir_pose(frame=sway, hips_pitch=2, head=4)
        if i == 0:
            hero_pose(-0.68, ('hero_walk', 9), hips_lean=16, spine=8, head=-6, hy=-0.30)
        elif i == 1:
            hero_pose(-0.58, ('hero_walk', 13), hips_lean=22, spine=10, head=-8, hy=-0.22, legs_planted=False,
                      airborne=tuck(hero, -35, 25, 50, 20))
        else:
            hero_pose(-0.46, ('hero_walk', 1), hips_lean=24, spine=16, head=-12, hips_dz=-0.05, hy=-0.10)
            tail = cruz_attached(cir.arm) @ V((0, 5, 12))
            for s, p in zip(('Left', 'Right'), (tail + V((0, 0.045, 0)), tail - V((0, 0.045, 0)))):
                hero_ik[s][0].location = p
                hero_ik[s][1].influence = 1.0
            update()
    elif i == 3:
        # tiron: la cruz se despega de la espalda; el Cireneo se arquea hacia atras
        cir_pose(frame=13, hips_pitch=-4, hips_dx=-0.04, spine=-22, head=-12)
        Ma = cruz_attached(cir.arm).copy()
        hero_pose(-0.47, ('hero_walk', 1), hips_lean=-6, spine=-10, head=-6, hips_dz=-0.03, hy=-0.11)
        hold((0.05, 0, -0.16), V((0.35, 0, 0.94)), 12)
        Mf = cir.cruz.matrix_world.copy()
        cruz_lerp_free(Ma, Mf, 0.55)
        burst(cruz_attached(cir.arm) @ V((0, 5, 50)), DT * 0.5, 'astilla', 6, 0.5, up=0.5, seed=1)
    elif i == 4:
        cir_pose(frame=14, hips_pitch=26, hips_dz=-0.06, hips_dx=0.05, spine=26, head=24, feet=feet_at(0.08, 0, 0.0))
        cir_arms((0.1, 1, -0.5), (0.1, -1, -0.5))
        hero_pose(-0.46, ('hero_walk', 1), hips_lean=-22, spine=-16, head=-4, hips_dz=-0.04, hy=-0.13)
        hold((0.03, 0, -0.04), V((0.25, 0, 0.97)), 12)
        burst(V((0.0, 0, 0.45)), DT * 0.8, 'astilla', 8, 0.6, up=0.8, seed=2)
        burst(V((-0.05, 0, 0.4)), DT * 0.8, 'polvo', 4, 0.25, up=0.3, seed=3)
    elif i == 5:
        cir_pose(frame=15, hips_pitch=44, hips_dz=-0.14, hips_dx=0.09, spine=34, head=30, feet=feet_at(0.10, 0, 0.0))
        cir_arms((0.3, 1, -0.9), (0.3, -1, -0.9))
        hero_pose(-0.46, ('hero_walk', 1), hips_lean=-26, spine=-20, head=0, hips_dz=-0.02, hy=HYA)
        hold((0.04, 0, 0.10), V((-0.30, 0.20, 0.93)), 26)
    elif i == 6:
        cir_pose(frame=16, hips_pitch=50, hips_dz=-0.18, hips_dx=0.12, spine=36, head=32, feet=feet_at(0.10, 0, 0.0))
        cir_arms((0.3, 1, -1.0), (0.3, -1, -1.0))
        hero_pose(-0.44, ('hero_walk', 1), hips_lean=-32, spine=-22, head=4, hips_dz=0.0, hy=HYA)
        hold_tip((0.03, 0, 0.16), V((0.28, 0.0, 0.30)))
    elif i == 7:
        # golpe: la punta de la cruz entra en la espalda; el Cireneo se estampa contra el suelo
        lying(62, 0.10)
        cir_arms((0.0, 1, -0.7), (0.0, -1, -0.7))
        hero_pose(-0.34, ('hero_walk', 1), hips_lean=26, spine=14, head=-8, hips_dz=-0.08, hy=HYA)
        hold_tip((0.14, 0, -0.02), V((0.25, 0, 0.12)))
        burst(V((0.22, 0, 0.10)), DT * 0.4, 'astilla', 12, 0.9, up=1.0, seed=4)
        burst(V((0.22, 0, 0.08)), DT * 0.4, 'polvo', 6, 0.5, up=0.3, seed=5)
    elif i == 8:
        lying(90, 0.075)
        hero_pose(-0.30, ('hero_walk', 1), hips_lean=30, spine=18, head=-10, hips_dz=-0.10, hy=HYA)
        hold_tip((0.15, 0, -0.04), TIP)
        burst(V((0.22, 0, 0.08)), DT * 1.4, 'astilla', 12, 0.9, up=1.0, seed=4)
        burst(V((0.22, 0, 0.06)), DT * 1.4, 'polvo', 8, 0.5, up=0.3, seed=5)
        burst(V((0.22, 0, 0.06)), DT * 1.4, 'sangre', 5, 0.35, up=0.6, seed=6)
    else:
        k = i - 9
        lying(90, 0.075)
        hx = -0.30 - 0.12 * (k + 1) / 3.0
        hero_pose(min(hx, HERO_X) if k >= 2 else hx, ('hero_walk', 1), hips_lean=18 - 6 * k, spine=8 - 3 * k, head=-4,
                  hips_dz=-0.05 + 0.017 * k, hy=HYA)
        ang = 5 * math.cos(k * 1.6) * (0.6 ** k)
        up = Matrix.Rotation(math.radians(ang), 3, 'Y') @ V((-0.55, HYA, 0.8))
        cruz_place(TIP, up, V((0, 1, 0)), -3.5)
        burst(V((0.22, 0, 0.06)), DT * (2.4 + k), 'polvo', 8, 0.5, up=0.3, seed=5)
        burst(V((0.22, 0, 0.06)), DT * (2.4 + k), 'astilla', 8, 0.9, up=1.0, seed=4)
        burst(V((0.22, 0, 0.05)), DT * (2.4 + k), 'sangre', 3, 0.35, up=0.6, seed=6)


FRAMES['A'] = (frame_A, 12)
KEY['A'] = 7
