"""Boceto de decision: 3 GIFs con alternativas de efectos de escopeta.

Lienzo logico 256x192 a 1x, escalado x3 con NEAREST al guardar.
Sin alpha, paleta fija de 16 colores, sin antialiasing.
Solo previsualizacion: no es codigo del juego.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

W, H = 256, 192
SCALE = 3
FRAME_MS = 40
N_FRAMES = 63          # 0.00 .. 2.48 s en pasos de 0.04 s (~2.5 s)
HOLD_FRAMES = 12       # ~0.5 s de pausa final (repite el ultimo fotograma)

SPD = 320.0            # px/s de los perdigones
RANGE = 110.0          # alcance maximo de un perdigon (px)
PELLET_LIFE_FADE = 0.36
T_SHOT = (0.20, 1.20)  # instantes de los dos disparos
OFFSETS_DEG = [-14.0, -9.3, -4.7, 0.0, 4.7, 9.3, 14.0]

# Paleta fija de 16 colores (indices usados en todo el script)
PAL = [
    (16, 14, 22),     # 0 negro fondo / sombra
    (34, 30, 44),     # 1 suelo oscuro
    (52, 46, 66),     # 2 lineas de rombo
    (96, 88, 110),    # 3 muro cara derecha
    (70, 64, 84),     # 4 muro cara izquierda
    (130, 122, 144),  # 5 muro tapa
    (60, 120, 230),   # 6 jugador azul
    (150, 200, 255),  # 7 jugador claro
    (210, 60, 60),    # 8 enemigo rojo
    (80, 200, 90),    # 9 enemigo verde
    (255, 255, 255),  # 10 blanco
    (255, 230, 90),   # 11 amarillo
    (255, 140, 40),   # 12 naranja
    (150, 150, 160),  # 13 gris humo
    (150, 30, 30),    # 14 rojo oscuro
    (220, 220, 225),  # 15 claro / texto
]

PAL_IMG = Image.new("P", (1, 1))
_flat = []
for _c in PAL:
    _flat += list(_c)
PAL_IMG.putpalette(_flat + [0] * (768 - len(_flat)))

# Geometria de escena (pantalla)
X0, Y0 = 128, 18              # esquina superior del tile (0,0)
P0 = (30, 60)                 # pies del jugador
M0 = (36, 50)                 # boca del arma (10 px sobre el suelo)
A0 = math.atan2(8, 16)        # direccion iso (1,0) -> (16,8)
U = (math.cos(A0), math.sin(A0))
E1_FEET = (71, 81)            # enemigo cercano (rojo)
E1_C = (71, 75)               # centro del cuerpo para colision
E2_FEET = (164, 127)          # enemigo lejano (verde)
E2_C = (164, 121)
WALL = (88, 70, 128, 110)     # bbox del bloque de muro
SHAKE = [(2, 0), (-2, 1), (1, -2), (-1, 1)]

FONT = None


def get_font():
    global FONT
    if FONT is None:
        try:
            FONT = ImageFont.load_default(size=8)
        except Exception:
            FONT = ImageFont.load_default()
    return FONT


def iso_corner(i, j):
    return (X0 + (i - j) * 16, Y0 + (i + j) * 8)


def build_bg():
    bg = Image.new("RGB", (W, H), PAL[0])
    d = ImageDraw.Draw(bg)
    for i in range(10):
        for j in range(10):
            pts = [iso_corner(i, j), iso_corner(i + 1, j),
                   iso_corner(i + 1, j + 1), iso_corner(i, j + 1)]
            d.polygon(pts, fill=PAL[1 if (i + j) % 2 == 0 else 0], outline=PAL[2])
    # Bloque de muro: footprint centrado en (108,100), altura 20 px
    L, R, B, T = (88, 100), (128, 100), (108, 110), (108, 90)
    Lu, Ru, Bu, Tu = (88, 80), (128, 80), (108, 90), (108, 70)
    d.polygon([L, B, Bu, Lu], fill=PAL[4], outline=PAL[0])
    d.polygon([B, R, Ru, Bu], fill=PAL[3], outline=PAL[0])
    d.polygon([Tu, Ru, Bu, Lu], fill=PAL[5], outline=PAL[0])
    return bg


def figure(d, x, y, body, head, legs=0):
    x, y = round(x), round(y)
    d.rectangle([x - 3, y - 9, x + 2, y - 3], fill=PAL[body])
    d.rectangle([x - 2, y - 13, x + 1, y - 10], fill=PAL[head])
    d.rectangle([x - 3, y - 2, x - 1, y], fill=PAL[legs])
    d.rectangle([x + 1, y - 2, x + 2, y], fill=PAL[legs])


def trace(origin, ang, targets):
    """Avanza un perdigon hasta impacto (enemigo/muro) o alcance."""
    ux, uy = math.cos(ang), math.sin(ang)
    s = 0.0
    while s <= RANGE:
        px = origin[0] + ux * s
        py = origin[1] + uy * s
        for (cx, cy, rad, tid) in targets:
            if (px - cx) ** 2 + (py - cy) ** 2 <= rad * rad:
                return s, "enemy", (px, py), (-ux, -uy), tid
        if WALL[0] <= px <= WALL[2] and WALL[1] <= py <= WALL[3]:
            return s, "wall", (px, py), (-ux, -uy), None
        s += 0.5
    return RANGE, "range", (origin[0] + ux * RANGE, origin[1] + uy * RANGE), None, None


def fire(ts, rng, targets):
    pellets = []
    for off in OFFSETS_DEG:
        ang = A0 + math.radians(off + rng.uniform(-1.5, 1.5))
        s, kind, hit, nrm, tid = trace(M0, ang, targets)
        life = s / SPD + 0.06 if kind != "range" else RANGE / SPD + 0.02
        pellets.append({"t0": ts, "ang": ang, "stop": s, "kind": kind,
                        "hit": hit, "nrm": nrm, "tid": tid,
                        "t_imp": ts + s / SPD, "life": life})
    return pellets


def spark_dirs(n, count, rng):
    base = math.atan2(n[1], n[0])
    out = []
    for k in range(count):
        off = math.radians(-40 + 80 * k / (count - 1)) if count > 1 else 0.0
        a = base + off + rng.uniform(-0.1, 0.1)
        out.append((math.cos(a), math.sin(a)))
    return out


def shell_traj(x, y, vx, vy, ground, rng, dur=2.6):
    out = []
    t, dt, g = 0.0, 0.01, 500.0
    resting = False
    while t <= dur + 1e-9:
        out.append((t, x, y))
        if not resting:
            vy += g * dt
            x += vx * dt
            y += vy * dt
            if y >= ground:
                y = ground
                vy = -vy * 0.35
                vx *= 0.6
                if abs(vy) < 20:
                    vy = 0.0
                    resting = True
        else:
            x += vx * dt
            vx *= 0.97
        t += dt
    return out


def cone(origin, base, L, hw_deg):
    hw = math.radians(hw_deg)
    ox, oy = origin
    pts = [(ox, oy),
           (ox + math.cos(base - hw) * L, oy + math.sin(base - hw) * L),
           (ox + math.cos(base) * L, oy + math.sin(base) * L),
           (ox + math.cos(base + hw) * L, oy + math.sin(base + hw) * L)]
    return [(round(x), round(y)) for x, y in pts]


def ramp(seq, frac):
    i = min(len(seq) - 1, max(0, int(frac * len(seq))))
    return seq[i]


# ---------- Dibujo de efectos ----------

def draw_pellet(d, e, t, alt):
    p = e["p"]
    age = t - p["t0"]
    if age < 0 or age > p["life"]:
        return 0
    ux, uy = math.cos(p["ang"]), math.sin(p["ang"])
    hs = min(SPD * age, p["stop"])
    hx = M0[0] + ux * hs
    hy = M0[1] + uy * hs
    f = min(0.999, age / PELLET_LIFE_FADE)
    x, y = round(hx), round(hy)
    if alt == "A":
        col = ramp([10, 11, 12, 14, 13], f)
        d.line([(x, y), (round(hx - ux * 4), round(hy - uy * 4))], fill=PAL[col])
        d.point((x, y), fill=PAL[10 if f < 0.15 else col])
    elif alt == "B":
        col = ramp([10, 11, 12, 13], f)
        d.rectangle([x, y, x + 1, y + 1], fill=PAL[col])
        if f < 0.7:
            for k in (3, 6, 9):
                d.point((round(hx - ux * k), round(hy - uy * k)), fill=PAL[13])
    else:
        length = max(2, round(16 * (1 - 0.5 * f)))
        for k in range(length):
            c = 10 if k < 4 else (11 if k < 9 else 12)
            d.point((round(hx - ux * k), round(hy - uy * k)), fill=PAL[c])
        d.rectangle([x, y, x + 1, y + 1], fill=PAL[10])
    return 1


def draw_muzzle(d, e, t):
    age = t - e["t0"]
    if age < 0 or age >= 0.12:
        return 0
    fi = int(age / 0.04)
    alt = e["alt"]
    if alt == "A":
        if fi == 0:
            x, y = M0
            for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4), (2, 2), (-2, -2)):
                d.line([(x, y), (x + dx, y + dy)], fill=PAL[10])
        elif fi == 1:
            d.polygon(cone(M0, A0, 5, 20), fill=PAL[11])
        else:
            d.rectangle([M0[0], M0[1], M0[0] + 1, M0[1] + 1], fill=PAL[12])
        return 1
    if alt == "B":
        lengths, widths = [16, 14, 9], [25, 22, 18]
    else:
        lengths, widths = [22, 19, 13], [30, 26, 20]
    d.polygon(cone(M0, A0, lengths[fi], widths[fi]), fill=PAL[[10, 11, 12][fi]])
    return 1


def draw_spark(d, e, t):
    age = t - e["t0"]
    if age < 0 or age > e["life"]:
        return 0
    f = age / e["life"]
    col = ramp([10, 11, 12, 14], f)
    grow = min(1.0, age / 0.06)
    x, y = e["pos"]
    for dx, dy in e["dirs"]:
        d.line([(round(x), round(y)),
                (round(x + dx * e["len"] * grow), round(y + dy * e["len"] * grow))],
               fill=PAL[col])
    return len(e["dirs"])


def draw_dust(d, e, t):
    age = t - e["t0"]
    if age < 0 or age > e["life"]:
        return 0
    f = age / e["life"]
    col = 15 if f < 0.4 else 13
    dither = f > 0.7
    k = min(age, 0.5)
    for vx, vy in e["dots"]:
        xi = round(e["pos"][0] + vx * k)
        yi = round(e["pos"][1] + vy * k)
        if dither and (xi + yi) % 2:
            continue
        d.rectangle([xi, yi, xi + 1, yi + 1], fill=PAL[col])
    return len(e["dots"])


def draw_smoke(d, e, t):
    age = t - e["t0"]
    if age < 0 or age > e["life"]:
        return 0
    f = age / e["life"]
    cx = e["pos"][0] + e["v"][0] * age
    cy = e["pos"][1] + e["v"][1] * age
    r = round(e["r0"] + 4 * f)
    cx, cy = round(cx), round(cy)
    if f < 0.4:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAL[15])
    elif f < 0.75:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAL[13])
    else:
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r and (xx + yy) % 2 == 0:
                    d.point((xx, yy), fill=PAL[13])
    return 1


def draw_shell(d, e, t):
    age = t - e["t0"]
    if age < 0:
        return 0
    idx = min(len(e["traj"]) - 1, int(age / 0.01 + 1e-9))
    _, x, y = e["traj"][idx]
    xi, yi = round(x), round(y)
    d.rectangle([xi, yi, xi + 1, yi], fill=PAL[e["col"]])
    return 1


def draw_arc(d, e, t):
    age = t - e["t0"]
    if age < 0 or age > e["life"]:
        return 0
    f = age / e["life"]
    r = 0.6 + 3.0 * min(1.0, age / 0.4)
    col = ramp([10, 11, 12, 13], f)
    px, py = e["P"]
    k = 0
    phi = -e["fan"]
    while phi <= e["fan"] + 1e-9:
        if not (f > 0.5 and k % 2):
            for rr in (r, r - 0.2):
                wx = rr * math.cos(phi)
                wy = rr * math.sin(phi)
                sx = px + 16 * (wx - wy)
                sy = py + 8 * (wx + wy)
                d.point((round(sx), round(sy)), fill=PAL[col])
        phi += 0.05
        k += 1
    return 1


def draw_frag(d, e, t):
    age = t - e["t0"]
    if age < 0 or age > 0.5:
        return 0
    for x0, y0, vx, vy, c in e["pieces"]:
        x = x0 + vx * age
        y = y0 + vy * age + 0.5 * 160 * age * age
        d.point((round(x), round(y)), fill=PAL[c])
    return len(e["pieces"])


# ---------- Construccion de la linea temporal ----------

def impact_effects(alt, p, rng):
    out = []
    n = p["nrm"]
    if alt == "A":
        cnt = 3 if p["kind"] == "enemy" else 2
        out.append({"type": "spark", "t0": p["t_imp"], "pos": p["hit"], "life": 0.16,
                    "len": 4, "dirs": spark_dirs(n, cnt, rng)})
    elif alt == "B":
        dots = [(rng.uniform(-10, 10), rng.uniform(-14, 2)) for _ in range(2)]
        out.append({"type": "dust", "t0": p["t_imp"], "pos": p["hit"], "life": 0.45,
                    "dots": dots})
    else:
        out.append({"type": "spark", "t0": p["t_imp"], "pos": p["hit"], "life": 0.2,
                    "len": 6, "dirs": spark_dirs(n, 3, rng)})
    return out


def build_effects(alt, rng):
    fx, phys = [], []
    for si, ts in enumerate(T_SHOT):
        targets = [(E1_C[0], E1_C[1], 8, "E1")] if si == 0 else [(E2_C[0], E2_C[1], 8, "E2")]
        ps = fire(ts, rng, targets)
        phys.append(ps)
        fx.append({"type": "muzzle", "t0": ts, "alt": alt})
        for p in ps:
            fx.append({"type": "pellet", "p": p, "alt": alt})
        for p in ps:
            if p["kind"] in ("enemy", "wall"):
                fx.extend(impact_effects(alt, p, rng))
        if alt in ("B", "C"):
            vx = rng.uniform(40, 60)
            vy = -rng.uniform(70, 100)
            fx.append({"type": "shell", "t0": ts + 0.03, "col": 12 if alt == "B" else 11,
                       "traj": shell_traj(P0[0] + 4, P0[1] - 6, vx, vy, 62, rng)})
        if alt == "B":
            for _ in range(3):
                fx.append({"type": "smoke", "t0": ts + 0.02, "pos": M0,
                           "v": (rng.uniform(4, 10), rng.uniform(-14, -6)),
                           "life": 1.0, "r0": 2})
        if alt == "C":
            fx.append({"type": "arc", "t0": ts, "life": 0.5, "P": P0, "fan": 0.6})
            dots = [(rng.uniform(-30, 30), rng.uniform(-40, -5)) for _ in range(5)]
            fx.append({"type": "dust", "t0": ts, "pos": P0, "life": 0.6, "dots": dots})

    e1_hits = [p["t_imp"] for p in phys[0] if p["kind"] == "enemy" and p["tid"] == "E1"]
    t_hit = min(e1_hits)
    t_death = t_hit + 0.15
    push = 8.0
    e1_final = (E1_FEET[0] + U[0] * push, E1_FEET[1] + U[1] * push)
    if alt == "C":
        pieces = []
        for _ in range(5):
            pieces.append((e1_final[0], e1_final[1] - 6, rng.uniform(-40, 40),
                           rng.uniform(-60, -20), rng.choice([8, 14])))
        fx.append({"type": "frag", "t0": t_death, "pieces": pieces})
    return fx, phys, t_hit, t_death, e1_final


def recoil(t, alt):
    amp = 4.0 if alt == "C" else 2.0
    r = 0.0
    for ts in T_SHOT:
        if t >= ts:
            r = max(r, amp * max(0.0, 1 - (t - ts) / 0.2))
    return r


def shake(t, alt):
    if alt != "C":
        return 0, 0
    for ts in T_SHOT:
        age = t - ts + 1e-9
        if 0 <= age < 0.16:
            k = min(3, int(age / 0.04))
            return SHAKE[k]
    return 0, 0


def label(d, text):
    font = get_font()
    bbox = d.textbbox((0, 0), text, font=font)
    d.rectangle([0, 0, bbox[2] + 4, bbox[3] + 3], fill=PAL[0])
    d.text((2, 1), text, fill=PAL[15], font=font)


def render(alt, t, bg, fx, t_hit, t_death, e1_final, text):
    img = bg.copy()
    d = ImageDraw.Draw(img)
    rec = recoil(t, alt)
    px = P0[0] - U[0] * rec
    py = P0[1] - U[1] * rec
    d.line([(round(px + 1), round(py - 7)), (round(px + 6), round(py - 10))], fill=PAL[13])
    figure(d, px, py, 6, 7)
    figure(d, E2_FEET[0], E2_FEET[1], 9, 9)

    if t < t_hit:
        figure(d, E1_FEET[0], E1_FEET[1], 8, 14)
    elif t < t_death:
        if t - t_hit < 0.08:
            figure(d, e1_final[0], e1_final[1], 10, 10)
        else:
            figure(d, e1_final[0], e1_final[1], 8, 14)
    else:
        ex, ey = round(e1_final[0]), round(e1_final[1])
        d.rectangle([ex - 3, ey - 1, ex + 3, ey + 1], fill=PAL[14])
        d.point((ex - 2, ey - 2), fill=PAL[8])

    count = 0
    for e in fx:
        ty = e["type"]
        if ty == "pellet":
            count += draw_pellet(d, e, t, e["alt"])
        elif ty == "muzzle":
            count += draw_muzzle(d, e, t)
        elif ty == "spark":
            count += draw_spark(d, e, t)
        elif ty == "dust":
            count += draw_dust(d, e, t)
        elif ty == "smoke":
            count += draw_smoke(d, e, t)
        elif ty == "shell":
            count += draw_shell(d, e, t)
        elif ty == "arc":
            count += draw_arc(d, e, t)
        elif ty == "frag":
            count += draw_frag(d, e, t)

    sx, sy = shake(t, alt)
    if sx or sy:
        out = Image.new("RGB", (W, H), PAL[0])
        out.paste(img, (sx, sy))
        img = out
        d = ImageDraw.Draw(img)
    label(d, text)
    return img, count


def make_gif(alt, text, filename, seed, bg, out_dir):
    rng = random.Random(seed)
    fx, phys, t_hit, t_death, e1_final = build_effects(alt, rng)
    frames, max_count = [], 0
    for i in range(N_FRAMES):
        t = round(i * 0.04, 4)
        img, cnt = render(alt, t, bg, fx, t_hit, t_death, e1_final, text)
        max_count = max(max_count, cnt)
        frames.append(img)
    frames += [frames[-1]] * HOLD_FRAMES
    out = []
    for im in frames:
        p = im.quantize(palette=PAL_IMG, dither=Image.Dither.NONE)
        out.append(p.resize((W * SCALE, H * SCALE), Image.NEAREST))
    path = os.path.join(out_dir, filename)
    out[0].save(path, save_all=True, append_images=out[1:],
                duration=FRAME_MS, loop=0, optimize=False)
    hits = sum(1 for ps in phys for p in ps if p["kind"] == "enemy")
    walls = sum(1 for ps in phys for p in ps if p["kind"] == "wall")
    print(f"{filename}: {len(out)} frames, {os.path.getsize(path) / 1024:.1f} KB, "
          f"max particulas simultaneas={max_count}, impactos enemigo={hits}, muro={walls}")
    return path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.normpath(os.path.join(here, "..", "assets"))
    os.makedirs(out_dir, exist_ok=True)
    bg = build_bg()
    make_gif("A", "A: estelas cortas", "shotgun_A_tracers.gif", 11, bg, out_dir)
    make_gif("B", "B: estallido en cono", "shotgun_B_blast.gif", 22, bg, out_dir)
    make_gif("C", "C: pesada con onda", "shotgun_C_heavy.gif", 33, bg, out_dir)
