# OPCION C: crucifixion. El heroe salta y estampa el talon sobre el pie del palo de la cruz (que sobresale por detras): la
# cruz se hinca en el suelo, endereza de golpe al Cireneo y lo deja colgando de ella, con los brazos en cruz, y se descuelga
# sin vida. Silueta VERTICAL en T (A: oblicua larga, B: plana en el suelo).
# (se ejecuta dentro de proto_remate_cireneo_seq.py: comparte su espacio de nombres)


def tail_pt():
    return cruz_attached(cir.arm) @ V((0, 5, -3.5))


def cir_hang(tilt, arch=0.0, head=0.0, plant=0.0, sway=0.0, legs=0.0):
    """Cireneo atado a su cruz. tilt = inclinacion de la cruz desde la vertical hacia delante (53 en el aturdido, 0 = derecha);
    arch/head = torso y cabeza hacia atras (+); plant 0..1: el pie del palo baja hasta clavarse en el suelo."""
    d = tilt - 53.0
    cir_pose(frame=9, hips_pitch=d * 0.35 + 2, spine=d * 0.65 - arch, head=head, feet=feet_at(0.0, legs, 0, 0.05))
    if sway:
        cir_arms((0, 1, sway), (0, -1, sway))
    tp = tail_pt()
    target = 0.157 + (-0.03 - 0.157) * plant
    # el pie del palo sigue la altura que toque (clavado = bajo el suelo)
    if plant > 0:
        root_matrix(cir, trans=(0, 0, target - tp.z), pivot=V((0, 0, 0)))
        cir.root.matrix_world = Matrix.Translation(V((0, 0, target - tp.z))) @ Matrix.Rotation(math.radians(90), 4, 'Z')
        update()


def kick_pose(f, pos_x, lean, dz, th_l, th_r, kn_l, kn_r, hy=-0.12):
    hero_pose(pos_x, ('hero_walk', f), hips_lean=lean, spine=-10, head=-4, hips_dz=dz, hy=hy, legs_planted=False,
              airborne=tuck(hero, th_l, th_r, kn_l, kn_r))


HYC = -0.14


def frame_C(i):
    reset_frame()
    if i == 0:
        cir_hang(53, 0, 4)
        hero_pose(-0.70, ('hero_walk', 9), hips_lean=16, spine=8, head=-6, hy=HYC)
    elif i == 1:
        cir_hang(53, 0, 4)
        kick_pose(13, -0.62, -28, 0.20, -60, -48, 28, 40)
    elif i == 2:
        # el talon cae sobre el pie del palo
        cir_hang(46, 4, 4, plant=0.15)
        tp = tail_pt()
        kick_pose(13, tp.x - 0.10, -50, 0.26, -88, -78, 4, 12)
        snap_foot(tp, 'Left', V((0.0, -0.01, 0.0)))
    elif i == 3:
        # estampa: el palo se hinca y endereza al Cireneo de golpe
        cir_hang(20, 18, -20, plant=0.75)
        tp = tail_pt()
        kick_pose(1, tp.x - 0.06, -40, 0.12, -80, -50, 8, 36)
        snap_foot(tp, 'Left', V((0.0, -0.01, 0.03)))
        burst(V((tp.x, tp.y, 0.02)), DT * 0.4, 'polvo', 8, 0.6, up=0.3, seed=3)
        burst(V((tp.x, tp.y, 0.02)), DT * 0.4, 'astilla', 10, 0.8, up=0.9, seed=1)
    elif i == 4:
        cir_hang(2, 24, -26, plant=1.0, legs=0.06)
        tp = tail_pt()
        hero_pose(tp.x - 0.30, ('hero_walk', 1), hips_lean=-8, spine=-6, head=-2, hips_dz=0.14, hy=HYC, legs_planted=False,
                  airborne=tuck(hero, 18, 30, 40, 50))
        burst(V((tp.x, tp.y, 0.02)), DT * 1.4, 'polvo', 8, 0.6, up=0.3, seed=3)
        burst(V((tp.x, tp.y, 0.02)), DT * 1.4, 'astilla', 8, 0.8, up=0.9, seed=1)
        burst(V((tp.x, tp.y, 0.02)), DT * 1.4, 'sangre', 3, 0.3, up=0.5, seed=6)
    else:
        k = i - 5
        head = min(10 + 7 * k, 38) - 40 * max(0, 1 - k * 0.8) * 0
        cir_hang(0, 8 - 2 * k, 12 + 8 * k if k < 3 else 36, plant=1.0, legs=0.10, sway=-0.2 - 0.12 * min(k, 3))
        tp = tail_pt()
        # el heroe se levanta y retrocede hasta su sitio
        h0 = tp.x - 0.32
        hx = h0 + (hero_end_x() - h0) * min(1.0, (k + 1) / 4.0)
        hero_pose(hx, ('hero_walk', 1), hips_lean=24 - 5 * k, spine=14 - 3 * k, head=-6, hips_dz=-0.10 + 0.017 * k, hy=HYC)
        s = 0.6 ** k
        burst(V((tp.x, tp.y, 0.02)), DT * (2.4 + k), 'polvo', 8, 0.6, up=0.3, seed=3)
        burst(V((tp.x, tp.y, 0.02)), DT * (2.4 + k), 'astilla', max(2, 8 - k), 0.8, up=0.9, seed=1)


FRAMES['C'] = (frame_C, 12)
KEY['C'] = 3
