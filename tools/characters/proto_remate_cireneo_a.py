# OPCION A: el heroe le arranca la cruz de la espalda y lo atraviesa con ella contra el suelo.
# (se ejecuta dentro de proto_remate_cireneo_seq.py: comparte su espacio de nombres)
HYA = -0.14      # el heroe se pone entre la camara y la cruz para que no lo tape


def frame_A(i):
    reset_frame()
    TIP = V((0.20, 0.0, -0.035))
    if i <= 2:
        sway = {0: 8, 1: 10, 2: 12}[i]
        cir_pose(frame=sway, hips_pitch=2, head=4)
        if i == 0:
            hero_pose(-0.44, ('hero_walk', 9), hips_lean=16, spine=8, head=-6, hy=-0.30)
        elif i == 1:
            hero_pose(-0.43, ('hero_walk', 13), hips_lean=22, spine=10, head=-8, hy=-0.22, legs_planted=False,
                      airborne=tuck(hero, -35, 25, 50, 20))
        else:
            hero_pose(-0.42, ('hero_walk', 1), hips_lean=24, spine=16, head=-12, hips_dz=-0.05, hy=-0.10)
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
        cir_pose(frame=14, hips_pitch=26, hips_dz=-0.06, hips_dx=0.05, spine=26, head=24, feet=feet_at(0.03, 0, 0.0))
        cir_arms((0.1, 1, -0.5), (0.1, -1, -0.5))
        hero_pose(-0.46, ('hero_walk', 1), hips_lean=-22, spine=-16, head=-4, hips_dz=-0.04, hy=-0.13)
        hold((0.03, 0, -0.06), V((0.55, 0, 0.84)), 12)
        burst(V((0.0, 0, 0.45)), DT * 0.8, 'astilla', 8, 0.6, up=0.8, seed=2)
        burst(V((-0.05, 0, 0.4)), DT * 0.8, 'polvo', 4, 0.25, up=0.3, seed=3)
    elif i == 5:
        # postura de lanza: la cruz atras y arriba, la punta (el pie del palo) apuntando a su espalda
        cir_collapse(0.0)
        hero_pose(-0.33, ('hero_walk', 1), hips_lean=-18, spine=-14, head=2, hips_dz=-0.02, hy=HYA)
        hold_tip((0.03, 0, 0.10), spine_tip(0.42))
    elif i == 6:
        # golpe: la punta entra en la espalda y lo aplasta contra el suelo
        cir_collapse(0.6)
        hero_pose(-0.28, ('hero_walk', 1), hips_lean=28, spine=16, head=-8, hips_dz=-0.08, hy=HYA)
        hold_tip((0.14, 0, -0.02), spine_tip(0.12))
        sp = spine_tip(0.0)
        burst(sp, DT * 0.4, 'astilla', 12, 0.9, up=1.0, seed=4)
        burst(sp, DT * 0.4, 'polvo', 6, 0.5, up=0.3, seed=5)
    elif i == 7:
        cir_collapse(1.0)
        hero_pose(-0.30, ('hero_walk', 1), hips_lean=32, spine=18, head=-10, hips_dz=-0.10, hy=HYA)
        hold_tip((0.15, 0, -0.04), spine_tip(-0.03))
        sp = spine_tip(0.0)
        burst(sp, DT * 1.4, 'astilla', 12, 0.9, up=1.0, seed=4)
        burst(sp, DT * 1.4, 'polvo', 8, 0.5, up=0.3, seed=5)
        burst(sp, DT * 1.4, 'sangre', 5, 0.35, up=0.6, seed=6)
    else:
        k = i - 8
        cir_collapse(1.0)
        hx = -0.28 + (hero_end_x() + 0.28) * min(1.0, (k + 1) / 4.0)
        hero_pose(hx, ('hero_walk', 1), hips_lean=22 - 6 * k, spine=10 - 3 * k, head=-4,
                  hips_dz=-0.08 + 0.02 * k, hy=HYA)
        # la cruz queda clavada y vibra
        ang = 5 * math.cos(k * 1.6) * (0.6 ** k)
        tip = spine_tip(-0.03)
        d = Matrix.Rotation(math.radians(ang), 3, 'Y') @ V((-0.60, -0.15, 0.78))
        cruz_place(tip, d, V((0, 1, 0)), -3.5)
        sp = spine_tip(0.0)
        burst(sp, DT * (2.4 + k), 'polvo', 8, 0.5, up=0.3, seed=5)
        burst(sp, DT * (2.4 + k), 'astilla', 6, 0.9, up=1.0, seed=4)
        burst(sp, DT * (2.4 + k), 'sangre', 3, 0.35, up=0.6, seed=6)


def cir_collapse(t):
    """Cireneo de rodillas que se va desplomando hacia delante (t: 0 = arrodillado, 1 = hundido sobre la cara)."""
    cir_pose(frame=16, hips_pitch=48 + 26 * t, hips_dz=-0.17 - 0.03 * t, hips_dx=0.10 + 0.04 * t, spine=34 + 10 * t,
             head=30 + 12 * t, feet=feet_at(0.0, 0, 0.0, 0.05))
    cir_arms((0.4 + 0.5 * t, 1, -0.45), (0.4 + 0.5 * t, -1, -0.45))


def spine_tip(dz):
    """Un punto sobre la espalda del Cireneo (para la punta de la cruz), a altura relativa dz sobre el suelo."""
    p = head_world(cir, 'Spine1')
    return V((p.x, 0.0, max(p.z + dz, -0.03) if dz > -0.03 else dz))


FRAMES['A'] = (frame_A, 12)
KEY['A'] = 7
