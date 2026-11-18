# RONDA 3, OPCION A «Clavado al suelo»: el heroe agarra el travesaño de la cruz por detras, la arranca, barre al Cireneo (una pierna),
# que cae boca arriba con los brazos en cruz, y le clava su propia cruz en vertical en el pecho.
# (se ejecuta dentro de proto_remate_cireneo_r3_seq.py: comparte su espacio de nombres)
HYA = -0.16
PLANT_X = -0.24          # x del pecho del Cireneo tumbado (donde se clava la cruz)


def bar_pts(dy=0.12, z=58.0, yl=1.0):
    M = cruz_attached(cir.arm)
    return M @ V((-dy * 100, yl, z)), M @ V((dy * 100, yl, z))


def chest_pt():
    """Punto del pecho del Cireneo tumbado (la cruz se clava aqui)."""
    p = (head_world(cir, 'Spine2') + head_world(cir, 'Spine1')) * 0.5
    return V((p.x, p.y, top_at(cir, p.x, 0.05, 0.0, 0.08)))


def frame_A(i):
    reset_frame()
    if i == 0:
        cir_pose(frame=8, hips_pitch=2, head=4)
        hero_pose(-0.66, ('hero_walk', 9), hips_lean=16, spine=8, head=-6, hy=-0.24)
    elif i == 1:
        # salto: el heroe se lanza con las manos al travesaño
        cir_pose(frame=10, hips_pitch=4, head=4)
        bl, br = bar_pts(0.13)
        hero_pose(-0.52, ('hero_walk', 13), hips_lean=22, spine=10, head=-8, hips_dz=0.05, hy=-0.14, legs_planted=False,
                  airborne=tuck(hero, -35, 25, 50, 20), hands=(bl, br))
        hero_reach('1')
    elif i == 2:
        # agarra: las dos manos en el travesaño, detras de la cabeza
        cir_pose(frame=11, hips_pitch=4, head=-6)
        bl, br = bar_pts(0.13)
        hero_pose(-0.48, ('hero_walk', 1), hips_lean=26, spine=18, head=-12, hips_dz=-0.03, hy=-0.14, hands=(bl, br))
        hero_reach('2')
    elif i == 3:
        # tiron: la cruz se despega de la espalda, saltan las cuerdas
        cir_pose(frame=13, hips_pitch=-6, hips_dx=-0.03, spine=-24, head=-14)
        Ma = cruz_attached(cir.arm).copy()
        bl, br = bar_pts(0.13)
        pull = V((-0.10, 0, 0.03))
        hero_pose(-0.50, ('hero_walk', 1), hips_lean=-10, spine=-14, head=-6, hips_dz=-0.04, hy=-0.14, hands=(bl + pull, br + pull))
        mid = (bl + br) * 0.5 + pull
        cruz_place(mid, V((-0.20, 0, 0.98)), V((0, 1, 0)), 58)
        Mf = cir.cruz.matrix_world.copy()
        cruz_lerp_free(Ma, Mf, 0.7)
        burst(cruz_attached(cir.arm) @ V((0, 5, 50)), DT * 0.5, 'astilla', 8, 0.5, up=0.5, seed=1)
        burst(cruz_attached(cir.arm) @ V((0, 5, 40)), DT * 0.5, 'polvo', 3, 0.25, up=0.2, seed=2)
        hero_reach('3')
    elif i == 4:
        # arrancada: el Cireneo trastabilla hacia atras, la cruz libre en las manos del heroe
        cir_pose(frame=14, hips_pitch=-8, hips_dx=-0.05, spine=-18, head=-10, feet=feet_at(-0.03, 0, 0.0))
        hero_pose(-0.48, ('hero_walk', 1), hips_lean=-18, spine=-14, head=0, hips_dz=-0.02, hy=-0.20)
        hold((0.02, 0, 0.08), V((-0.35, 0, 0.94)), 30)
        burst(V((-0.05, 0, 0.45)), DT * 0.8, 'astilla', 8, 0.6, up=0.6, seed=3)
        burst(V((-0.05, 0, 0.42)), DT * 0.8, 'polvo', 4, 0.3, up=0.2, seed=4)
    elif i == 5:
        # barrido de UNA pierna a los tobillos; el Cireneo empieza a caer de espaldas
        supine(-22, head=-8, spine=-8)
        foot = V((0.05, 0.0, 0.05))
        hero_pose(-0.20, ('hero_walk', 1), hips_lean=-6, spine=-4, head=0, hy=-0.26, legs_planted=False,
                  airborne=lambda: hero_legs(None, lfoot=V((-0.20, -0.20, 0.0)), rfoot=V((0.04, -0.06, 0.05)), pole=V((0.3, -1, 0.6))))
        hold((0.0, 0, 0.02), V((-0.55, -0.3, 0.8)), 30)
    elif i == 6:
        supine(-62, head=-10, spine=-10)
        hero_pose(-0.20, ('hero_walk', 1), hips_lean=8, spine=6, head=-4, hy=-0.26)
        hold((0.03, 0, 0.0), V((-0.5, -0.3, 0.8)), 30)
        burst(V((-0.10, 0, 0.05)), DT * 0.4, 'polvo', 5, 0.35, up=0.2, seed=5)
    elif i == 7:
        # impacto: tumbado boca arriba, brazos en cruz
        supine(-90)
        hero_pose(-0.04, ('hero_walk', 1), hips_lean=10, spine=6, head=-4, hy=-0.24)
        hold((0.03, 0, 0.0), V((-0.2, -0.2, 0.95)), 30)
        burst(V((-0.25, 0, 0.04)), DT * 0.5, 'polvo', 10, 0.55, up=0.15, seed=6, size_k=1.2)
    elif i == 8:
        # la levanta en vertical con las dos manos, el pie hacia abajo
        supine(-90)
        c = chest_pt()
        foot = c + V((0, 0, 0.13))
        hands = shaft_hands(foot, V((0, 0, 1)), 0.20, 0.33, off=V((0, -0.03, 0)))
        hero_pose(-0.74, ('hero_walk', 1), hips_lean=-4, spine=-6, head=2, hips_dz=0.0, hy=-0.10, hands=hands)
        hero_reach('8')
    elif i == 9:
        # CLAVADA: el pie de la cruz entra en el pecho (fotograma clave)
        supine(-90)
        c = chest_pt()
        foot = c + V((0, 0, -0.01))
        vv = [float(x) for x in os.environ.get('V9', '-0.72,-0.10,0,0.0,90').split(',')]
        up9 = Matrix.Rotation(math.radians(vv[2]), 3, 'Y') @ Matrix.Rotation(math.radians(vv[3]), 3, 'Z') @ V((0, 0, 1))
        hands = shaft_hands(foot, up9, 0.20, 0.33, off=V((0, -0.03, 0)))
        hero_pose(vv[0], ('hero_walk', 1), hips_lean=22, spine=16, head=-8, hips_dz=-0.05, hy=vv[1], hands=hands, hrz=vv[4])
        hero_reach('9')
        burst(c, DT * 0.4, 'astilla', 10, 0.8, up=0.9, seed=7)
        burst(c, DT * 0.4, 'polvo', 8, 0.5, up=0.2, seed=8)
        burst(c, DT * 0.4, 'sangre', 4, 0.35, up=0.5, seed=9)
    else:
        k = i - 10
        supine(-90)
        c = chest_pt()
        ang = 4 * math.cos(k * 1.7) * (0.55 ** k)
        up = Matrix.Rotation(math.radians(ang), 3, 'Y') @ V((0, 0, 1))
        cruz_place(c + V((0, 0, -0.01)), up, V((0, 1, 0)), -3.0)
        hx = -0.04 + (hero_end_x() + 0.04) * min(1.0, k / 2.0)
        if k == 0:
            hands = shaft_hands(c + V((0, 0, -0.01)), V((0, 0, 1)), 0.20, 0.33, off=V((0, -0.03, 0)))
            hero_pose(-0.04, ('hero_walk', 1), hips_lean=14, spine=8, head=-6, hy=-0.24, hands=hands)
            cruz_place(c + V((0, 0, -0.01)), up, V((0, 1, 0)), -3.0)
        else:
            hero_pose(hx, ('hero_walk', 1), hips_lean=8 * (1 - k / 3.0), spine=4 * (1 - k / 3.0), head=0, hy=-0.24 - 0.02 * k)
        burst(c, DT * (1.4 + k), 'polvo', 8, 0.5, up=0.15, seed=8, size_k=1.1)
        burst(c, DT * (1.4 + k), 'astilla', 6, 0.8, up=0.9, seed=7)
        if k < 2:
            burst(c, DT * (1.4 + k), 'sangre', 3, 0.3, up=0.5, seed=9)


FRAMES['A'] = (frame_A, 14)
KEY['A'] = 9
