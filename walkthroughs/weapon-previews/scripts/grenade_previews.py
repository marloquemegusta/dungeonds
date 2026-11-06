"""Boceto de decision: 3 alternativas visuales de granada (isometrico, Nintendo DS).

Solo Pillow. Paleta indexada de 16 colores, sin alpha ni antialiasing.
Escena logica 256x192, escalada x3 con NEAREST al guardar.
Timeline: 75 fotogramas de GIF; cada fotograma = 2 frames de juego a 60 fps.
Mecha de 90 frames de juego = 45 fotogramas de GIF (FUSE_F).
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "assets"))

W, H, SCALE = 256, 192, 3
N_FRAMES = 75
DUR_MS = 40
LAST_HOLD_MS = 500
FUSE_F = 45      # 90 frames de juego
FLIGHT_F = 20    # 40 frames de juego
ENTER_F = 30     # proyectil de mortero entra 1 s despues de marcar

# Paleta (16 colores)
BG, FLOOR_A, FLOOR_B, GRID = 0, 1, 2, 3
WALL_SIDE, WALL_TOP = 4, 5
PLAY, RED, GREEN = 6, 7, 8
WHITE, YEL, ORG, HOT, SMOKE, DARK, CYAN = 9, 10, 11, 12, 13, 14, 15
PAL = [
    (0x14, 0x12, 0x1C), (0x24, 0x22, 0x30), (0x2C, 0x2A, 0x38), (0x3E, 0x3A, 0x50),
    (0x5A, 0x52, 0x6A), (0x77, 0x6E, 0x88), (0x3A, 0x7B, 0xE0), (0xE0, 0x3A, 0x3A),
    (0x3A, 0xC0, 0x4A), (0xFF, 0xFF, 0xFF), (0xFF, 0xE0, 0x40), (0xFF, 0x88, 0x20),
    (0xD8, 0x30, 0x20), (0x88, 0x88, 0x90), (0x40, 0x40, 0x48), (0x60, 0xD8, 0xE8),
]
PAL_FLAT = []
for _c in PAL:
    PAL_FLAT.extend(_c)
PAL_FLAT.extend([0] * (3 * (256 - len(PAL))))

# Rampa de desvanecimiento (sin transparencia): blanco -> amarillo -> naranja -> rojo -> gris -> oscuro
RAMP = [WHITE, YEL, ORG, HOT, SMOKE, DARK]

try:
    FONT = ImageFont.load_default(size=10)
except TypeError:
    FONT = ImageFont.load_default()


def iso(wx, wy):
    """Proyeccion isometrica 2:1 (tile 32x16). Origen del mundo en la pantalla (128, 88)."""
    return int(round(128 + 16 * (wx - wy))), int(round(88 + 8 * (wx + wy)))


TX, TY = iso(0, 0)
PLAYER_W = (-2.0, 2.0)
WALL_T = (2, -1)
R_X, R_Y = 68, 34  # radio de explosion (3 tiles) proyectado: rx = 16*sqrt2*R, ry = 8*sqrt2*R
ENEMIES = [        # (tile, color, dentro del radio)
    ((1, 0), RED, True),
    ((0, 1), GREEN, True),
    ((-1, -1), RED, True),
    ((3, -3), GREEN, False),  # fuera del radio: no sufre dano
]

PLAYER_SPR = [
    "..##..",
    "..##..",
    ".####.",
    "######",
    ".####.",
    "..##..",
    ".#..#.",
    ".#..#.",
]
ENEMY_SPR = [
    "#.##.#",
    ".####.",
    "######",
    "#.##.#",
    ".#..#.",
]

_rng = random.Random(7)
SPARKS = [(_rng.uniform(0, 2 * math.pi), _rng.uniform(2.0, 5.0)) for _ in range(12)]
SMOKE_PUFFS = [(-12, 0), (6, 2), (-2, 4)]
_rng = random.Random(11)
FRAGS = [(_rng.uniform(-2.5, 2.5), _rng.uniform(-4.0, -1.0)) for _ in range(16)]
ZONE_PIX = []
for _x in range(TX - R_X, TX + R_X + 1):
    for _y in range(TY - R_Y, TY + R_Y + 1):
        if ((_x - TX) / R_X) ** 2 + ((_y - TY) / R_Y) ** 2 <= 1.0 and (_x - _y) % 6 < 2:
            ZONE_PIX.append((_x, _y))


def ell(d, cx, cy, rx, ry, **kw):
    d.ellipse([int(round(cx - rx)), int(round(cy - ry)), int(round(cx + rx)), int(round(cy + ry))], **kw)


def rect(d, x0, y0, x1, y1, **kw):
    d.rectangle([int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))], **kw)


def draw_spr(d, spr, x, y, color):
    """x, y = ancla en los pies (centro inferior del sprite)."""
    h, w = len(spr), len(spr[0])
    x0, y0 = x - w // 2, y - h
    for r, row in enumerate(spr):
        for c, ch in enumerate(row):
            if ch == "#":
                px, py = x0 + c, y0 + r
                if 0 <= px < W and 0 <= py < H:
                    d.point((px, py), fill=color)


def put_text(img, xy, text, col):
    """Texto binario (sin antialiasing) sobre imagen de paleta."""
    m = Image.new("1", (W, H), 0)
    ImageDraw.Draw(m).text(xy, text, fill=1, font=FONT)
    box = m.getbbox()
    if not box:
        return
    mp, ip = m.load(), img.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            if mp[x, y]:
                ip[x, y] = col


def make_base():
    img = Image.new("P", (W, H), BG)
    img.putpalette(PAL_FLAT)
    d = ImageDraw.Draw(img)
    for i in range(-8, 9):
        for j in range(-8, 9):
            cx, cy = iso(i, j)
            fill = FLOOR_A if (i + j) % 2 == 0 else FLOOR_B
            d.polygon([(cx, cy - 8), (cx + 16, cy), (cx, cy + 8), (cx - 16, cy)], fill=fill, outline=GRID)
    # bloque de muro
    cx, cy = iso(*WALL_T)
    top = cy - 18
    d.polygon([(cx, top - 8), (cx + 16, top), (cx, top + 8), (cx - 16, top)], fill=WALL_TOP, outline=BG)
    d.polygon([(cx - 16, top), (cx, top + 8), (cx, cy + 8), (cx - 16, cy)], fill=WALL_SIDE, outline=BG)
    d.polygon([(cx, top + 8), (cx + 16, top), (cx + 16, cy), (cx, cy + 8)], fill=DARK, outline=BG)
    return img


BASE = make_base()


def arc(s, z_peak):
    """Vuelo en arco del jugador a TARGET. Devuelve (x_suelo, y_suelo, altura)."""
    wx = PLAYER_W[0] + (0.0 - PLAYER_W[0]) * s
    wy = PLAYER_W[1] + (0.0 - PLAYER_W[1]) * s
    gx, gy = iso(wx, wy)
    z = 4.0 * z_peak * s * (1.0 - s)
    return gx, gy, int(round(z))


def draw_actors(img, f, e):
    """Enemigos, jugador. e = fotograma de explosion."""
    d = ImageDraw.Draw(img)
    for (wx, wy), col, inside in ENEMIES:
        sx, sy = iso(wx, wy)
        c = col
        if inside and f >= e:
            t = f - e
            if t >= 18:
                continue
            c = RAMP[t // 3]
            dx, dy = sx - TX, sy - TY
            n = math.hypot(dx, dy) or 1.0
            push = min(t, 8) * 1.2
            sx = int(round(sx + dx / n * push))
            sy = int(round(sy + dy / n * push))
        bob = 1 if (not inside and (f // 6) % 2 == 1) else 0
        draw_spr(d, ENEMY_SPR, sx, sy + 4 - bob, c)
    px, py = iso(*PLAYER_W)
    flash = e <= f < e + 8 and (f // 2) % 2 == 0
    draw_spr(d, PLAYER_SPR, px, py + 4, WHITE if flash else PLAY)
    if e <= f < e + 20:
        put_text(img, (px + 6, py - 22 - int((f - e) * 0.4)), "-2", HOT)


# ---------------------------------------------------------------- A: anillo que se cierra
def frame_A(f):
    img = BASE.copy()
    d = ImageDraw.Draw(img)
    put_text(img, (4, 4), "A: anillo que se cierra", WHITE)
    g = 2 * f
    if f < FUSE_F:
        frac = max(0.0, 1.0 - g / 90.0)
        col = CYAN if frac > 0.5 else (YEL if frac > 0.2 else HOT)
        if frac * R_X >= 2:
            ell(d, TX, TY, R_X * frac, R_Y * frac, outline=col, width=2)
        if g < 40:
            gx, gy, z = arc(g / 40.0, 28)
            d.point((gx, gy), fill=DARK)               # sombra en el suelo
            rect(d, gx - 1, gy - z - 1, gx, gy - z, fill=WHITE)
        elif (f // 3) % 2 == 0:
            rect(d, TX - 1, TY - 1, TX, TY, fill=WHITE)  # punto brillante que parpadea
    draw_actors(img, f, FUSE_F)
    if f >= FUSE_F:
        fx_A(img, f - FUSE_F)
    return img


def fx_A(img, t):
    d = ImageDraw.Draw(img)
    if t < 2:
        ell(d, TX, TY, 14, 7, fill=WHITE)
    if t < 12:
        k = min(1.0, (t + 1) / 8.0)
        ring = [WHITE, WHITE, YEL, YEL, ORG, ORG, HOT, HOT, SMOKE, SMOKE, SMOKE, SMOKE][t]
        ell(d, TX, TY, R_X * 1.1 * k, R_Y * 1.1 * k, outline=ring, width=3)
        for ang, spd in SPARKS:  # chispas en lineas
            p0 = (TX + math.cos(ang) * spd * (t - 1) * 2.0, TY + math.sin(ang) * spd * (t - 1))
            p1 = (TX + math.cos(ang) * spd * t * 2.0, TY + math.sin(ang) * spd * t)
            col = [WHITE, YEL, ORG, HOT][min(3, t // 3)]
            if t >= 1:
                d.line([p0, p1], fill=col)
    for off_x, delay in SMOKE_PUFFS:  # volutas de humo que suben
        u = t - 2 - delay
        if u < 0 or t >= 30:
            continue
        cy = TY - 6 - u * 0.9
        r = 3 + u * 0.3
        ell(d, TX + off_x, cy, r, r, fill=SMOKE if u < 14 else DARK, outline=DARK)


# ---------------------------------------------------------------- B: granada rebotando
def grenade_b(g):
    if g < 40:
        return arc(g / 40.0, 28)
    if g < 58:
        s = (g - 40) / 18.0
        z = 4.0 * 12 * s * (1.0 - s)
    elif g < 72:
        s = (g - 58) / 14.0
        z = 4.0 * 5 * s * (1.0 - s)
    else:
        z = 0.0
    return TX, TY, int(round(z))


def frame_B(f):
    img = BASE.copy()
    d = ImageDraw.Draw(img)
    put_text(img, (4, 4), "B: granada rebotando", WHITE)
    g = 2 * f
    if f < FUSE_F:
        for a in range(0, 360, 5):  # circulo punteado tenue del radio
            x = TX + R_X * math.cos(math.radians(a))
            y = TY + R_Y * math.sin(math.radians(a))
            d.point((int(round(x)), int(round(y))), fill=DARK)
        gx, gy, z = grenade_b(g)
        rr = max(1, 3 - z // 8)
        ell(d, gx, gy, rr, 1, fill=DARK)               # sombra en el suelo
        bx, by = gx, gy - z
        period = 16.0 if g < 40 else max(2.0, 16.0 - 14.0 * (g - 40) / 50.0)
        on = math.floor(g / period) % 2 == 0           # luz roja que parpadea cada vez mas rapido
        rect(d, bx - 1, by - 1, bx + 1, by + 1, fill=DARK)
        d.point((bx - 1, by - 1), fill=WHITE)
        if on:
            rect(d, bx - 1, by - 3, bx + 1, by - 3, fill=HOT)
        else:
            d.point((bx, by - 3), fill=SMOKE)
    draw_actors(img, f, FUSE_F)
    if f >= FUSE_F:
        fx_B(img, f - FUSE_F)
    return img


def fx_B(img, t):
    d = ImageDraw.Draw(img)
    if t < 2:
        ell(d, TX, TY, R_X * 0.9, R_Y * 0.9, fill=WHITE)  # fogonazo blanco de 2 frames
    if 2 <= t < 26:
        u = t - 2
        r = 6 + 26 * u / 8.0 if u < 8 else 32 - (u - 8) * 0.6  # crece y luego se encoge
        cx, cy = TX, TY - 8
        ell(d, cx, cy, r, r, fill=HOT if u < 14 else SMOKE)
        ell(d, cx, cy, r * 0.65, r * 0.65, fill=ORG if u < 14 else HOT)
        ell(d, cx, cy, r * 0.35, r * 0.35, fill=YEL if u < 10 else ORG)
    for i, (vx, vy) in enumerate(FRAGS):  # escombros con gravedad
        if t < 26:
            x = TX + vx * t
            y = TY - 8 + vy * t + 0.175 * t * t
            if 0 <= x < W - 1 and 0 <= y < H - 1:
                rect(d, x, y, x + 1, y + 1, fill=[YEL, ORG, RED, SMOKE][i % 4])


# ---------------------------------------------------------------- C: mortero desde arriba
def frame_C(f):
    img = BASE.copy()
    d = ImageDraw.Draw(img)
    put_text(img, (4, 4), "C: mortero desde arriba", WHITE)
    t = f - FUSE_F
    # Suelo bajo el impacto (zona de peligro, cráter y onda plana) antes de los actores
    if f < FUSE_F:
        ell(d, TX, TY, R_X, R_Y, outline=HOT)
        col = HOT if (f // 3) % 2 == 0 else DARK      # tramado de rayas diagonales parpadeante
        for (x, y) in ZONE_PIX:
            d.point((x, y), fill=col)
    if t >= 0:
        ell(d, TX, TY, 36, 18, fill=BG, outline=DARK)  # cráter oscuro que queda
    if 0 <= t < 12:
        k = min(1.0, (t + 1) / 8.0)
        ring = [WHITE, WHITE, WHITE, YEL, YEL, YEL, ORG, ORG, ORG, HOT, HOT, HOT][t]
        ell(d, TX, TY, R_X * 1.1 * k, R_Y * 1.1 * k, outline=ring, width=2)  # onda plana en el suelo
    if ENTER_F <= f < FUSE_F:  # proyectil cayendo desde arriba con estela
        s = (f - ENTER_F) / float(FUSE_F - ENTER_F)
        py = TY - 120 * (1.0 - s) ** 2
        for k in range(4, 22, 2):
            d.point((TX, int(py) - k), fill=SMOKE)
        rect(d, TX - 1, py - 4, TX, py, fill=WHITE)
        d.point((TX, int(py) - 5), fill=YEL)
    draw_actors(img, f, FUSE_F)
    if t >= 0:
        fx_C_air(img, t)
    return img


def fx_C_air(img, t):
    d = ImageDraw.Draw(img)
    if t < 20:
        h = 96 * min(1.0, (t + 1) / 4.0) * max(0.25, 1.0 - t / 20.0)  # columna de fuego vertical
        wd = 16 * max(0.4, 1.0 - t / 14.0)
        top = TY + 2 - h
        rect(d, TX - wd / 2, top, TX + wd / 2, TY + 2, fill=HOT if t < 12 else SMOKE)
        rect(d, TX - wd * 0.3, top + 3, TX + wd * 0.3, TY + 2, fill=ORG if t < 12 else HOT)
        rect(d, TX - wd * 0.15, top + 5, TX + wd * 0.15, TY + 2, fill=WHITE if t < 3 else YEL)
    for off_x, delay in SMOKE_PUFFS:
        u = t - 6 - delay
        if u < 0 or t >= 28:
            continue
        r = 3 + u * 0.4
        ell(d, TX + off_x, TY - 50 - u * 1.0, r, r, fill=SMOKE if u < 12 else DARK, outline=DARK)


# ---------------------------------------------------------------- render
def render(name, fn):
    frames = []
    for f in range(N_FRAMES):
        img = fn(f)
        frames.append(img.resize((W * SCALE, H * SCALE), Image.NEAREST))
    path = os.path.join(OUT_DIR, name)
    durations = [DUR_MS] * (N_FRAMES - 1) + [LAST_HOLD_MS]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=1)
    size_kb = os.path.getsize(path) / 1024.0
    print("%s  frames=%d  size=%.1f KB" % (path, N_FRAMES, size_kb))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    render("grenade_A_ring.gif", frame_A)
    render("grenade_B_bounce.gif", frame_B)
    render("grenade_C_mortar.gif", frame_C)


if __name__ == "__main__":
    main()
