#!/usr/bin/env python3
"""Previsualizaciones de 3 alternativas de efectos de francotirador (boceto de decision).

Genera en ../assets:
  sniper_A_trace.gif  - trazo que se desvanece
  sniper_B_rings.gif  - anillos de choque
  sniper_C_beam.gif   - rayo irregular

Restricciones simuladas: imagen 256x192 en modo P con paleta fija de 16 colores,
sin alpha, sin antialiasing, sin dithering. Lineas por Bresenham, particulas en
punto fijo 8.8 con maximo 32 vivas. Se escala x3 con NEAREST al guardar.
Solo Pillow y la biblioteca estandar.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))

W, H, SCALE = 256, 192, 3
FRAME_MS, HOLD_MS = 40, 500      # 25 fps en el GIF, pausa final de 0,5 s
SIM_FRAMES = 75                  # 3,0 s de simulacion (1 paso por fotograma GIF)
MAX_PARTICLES = 32

# Paleta fija de 16 indices
(BG, FLOOR, FLOOR_EDGE, WALL_TOP, WALL_L, WALL_R, PLAYER, PLAYER_HI,
 RED, GREEN, WHITE, CYAN, CYAN_DIM, YELLOW, ORANGE, DARK_RED) = range(16)

PALETTE = [
    (13, 15, 24), (28, 32, 51), (45, 53, 83), (122, 130, 159),
    (74, 80, 112), (53, 59, 88), (58, 123, 255), (168, 208, 255),
    (232, 58, 58), (63, 214, 107), (255, 255, 255), (111, 240, 255),
    (42, 159, 184), (255, 224, 102), (255, 138, 42), (120, 36, 36),
]
PAL_FLAT = [c for rgb in PALETTE for c in rgb] + [0] * (768 - 3 * len(PALETTE))

# Geometria: boca del arma y linea de tiro (direccion isometrica 2:1 en pantalla)
MUZZLE = (72, 159)


def beam_pt(s):
    """Punto de la linea de tiro a distancia s (enteros) desde la boca."""
    return (MUZZLE[0] + 2 * s, MUZZLE[1] - s)


def feet_of(s):
    """Pies de un enemigo sobre la linea: el suelo queda 10 px bajo el rayo."""
    x, y = beam_pt(s)
    return (x, y + 10)


ENEMY_S = (22, 38, 54)
ENEMY_COL = (RED, GREEN, RED)
WALL_S = 72
IMPACT = beam_pt(WALL_S)          # (216, 87): cara izquierda del muro
WALL_C = (224, 94)                # centro del suelo del muro
PLAYER_FEET = (67, 169)
FLOOR_MUZZLE = (MUZZLE[0], MUZZLE[1] + 10)

AIM_START, READY, RELEASE = 10, 20, 35   # apuntado desde 0,4 s; listo en 0,8 s
DIE = RELEASE + 2                        # enemigos mueren 2 pasos tras el disparo

SPRITE = (
    ".bbb.",
    ".bhb.",
    ".bbb.",
    "bbbbb",
    "bbbbb",
    ".bbb.",
    ".bbb.",
    ".bbb.",
    ".b.b.",
    ".b.b.",
    ".b.b.",
    "bb.bb",
)

FONT = ImageFont.load_default()


def make_canvas():
    img = Image.new("P", (W, H), BG)
    img.putpalette(PAL_FLAT)
    return img


def make_floor():
    """Suelo isometrico: cuadricula de rombos 32x16."""
    img = make_canvas()
    d = ImageDraw.Draw(img)
    ox, oy = 128, 0
    for i in range(-12, 13):
        for j in range(-12, 25):
            cx = ox + (i - j) * 16
            cy = oy + (i + j) * 8
            d.polygon([(cx, cy - 8), (cx + 16, cy), (cx, cy + 8), (cx - 16, cy)],
                      fill=FLOOR, outline=FLOOR_EDGE)
    return img


def bres(p0, p1):
    """Bresenham entero entre dos puntos, incluidos extremos."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def line(d, p0, p1, col, dy=0):
    for x, y in bres(p0, p1):
        d.point((x, y + dy), fill=col)


def draw_sprite(d, fx, fy, body, hi):
    """Figura de 5x12 px con los pies en (fx, fy)."""
    x0, y0 = fx - 2, fy - 12
    for r, row in enumerate(SPRITE):
        for c, ch in enumerate(row):
            if ch != ".":
                d.point((x0 + c, y0 + r), fill=body if ch == "b" else hi)


def draw_player(d):
    draw_sprite(d, PLAYER_FEET[0], PLAYER_FEET[1], PLAYER, PLAYER_HI)
    line(d, (69, 160), MUZZLE, PLAYER_HI)   # cañon


def draw_wall(d, cols):
    top, left, right = cols
    cx, cy = WALL_C
    hw, hh, h = 8, 4, 26
    L, T, R, B = (cx - hw, cy), (cx, cy - hh), (cx + hw, cy), (cx, cy + hh)

    def up(p):
        return (p[0], p[1] - h)

    d.polygon([L, B, up(B), up(L)], fill=left)
    d.polygon([B, R, up(R), up(B)], fill=right)
    d.polygon([up(L), up(T), up(R), up(B)], fill=top)


def draw_world(d, t, wall_cols):
    """Muro (lejano), enemigos (de lejos a cerca) y jugador."""
    draw_wall(d, wall_cols)
    for k in (2, 1, 0):
        if t >= DIE:
            continue
        if t >= RELEASE:
            body, hi = WHITE, WHITE
        else:
            body, hi = ENEMY_COL[k], YELLOW
        fx, fy = feet_of(ENEMY_S[k])
        draw_sprite(d, fx, fy, body, hi)
    draw_player(d)


class Particles:
    """Particulas en punto fijo 8.8, maximo MAX_PARTICLES vivas."""

    def __init__(self, rng):
        self.rng = rng
        self.items = []

    def spawn(self, x, y, n, speed, life, ramp, grav=24):
        for _ in range(n):
            if len(self.items) >= MAX_PARTICLES:
                return
            vx = self.rng.randint(-speed, speed)
            vy = self.rng.randint(-speed, speed // 2)
            # [x, y, vx, vy, edad, vida, rampa, gravedad]
            self.items.append([x << 8, y << 8, vx, vy, 0, life, ramp, grav])

    def update_and_draw(self, d):
        keep = []
        for p in self.items:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += p[7]
            p[4] += 1
            if p[4] >= p[5]:
                continue
            ramp = p[6]
            d.point((p[0] >> 8, p[1] >> 8), fill=ramp[p[4] * len(ramp) // p[5]])
            keep.append(p)
        self.items = keep


# ---------------------------------------------------------------- A: trazo
def frame_A(t, c):
    img = c["base"].copy()
    d = ImageDraw.Draw(img)
    a = t - RELEASE
    wall = (YELLOW, WHITE, YELLOW) if a in (0, 1) else (WALL_TOP, WALL_L, WALL_R)
    draw_world(d, t, wall)

    if AIM_START <= t < RELEASE:
        line(d, MUZZLE, IMPACT, RED if t < READY else GREEN)

    if 0 <= a < 6:
        core = (WHITE, WHITE, CYAN, CYAN, CYAN_DIM, FLOOR_EDGE)[a]
        edge = (CYAN, CYAN, CYAN_DIM, FLOOR_EDGE, FLOOR_EDGE, FLOOR)[a]
        if a < 2:
            line(d, MUZZLE, IMPACT, edge, dy=-1)
            line(d, MUZZLE, IMPACT, edge, dy=1)
        line(d, MUZZLE, IMPACT, core)
        if a < 2:
            r = 4 - 2 * a
            mx, my = MUZZLE
            d.ellipse([mx - r, my - r, mx + r, my + r],
                      fill=YELLOW if a == 0 else ORANGE)

    if t == DIE:
        for s in ENEMY_S:
            fx, fy = feet_of(s)
            c["parts"].spawn(fx, fy - 6, 8, 384, 10, (WHITE, YELLOW, ORANGE, DARK_RED))
    c["parts"].update_and_draw(d)
    return img


# ---------------------------------------------------------------- B: anillos
RING_RAMP = (WHITE, CYAN, CYAN, CYAN_DIM, CYAN_DIM, FLOOR_EDGE, FLOOR_EDGE)


def frame_B(t, c):
    img = c["base"].copy()
    d = ImageDraw.Draw(img)
    a = t - RELEASE
    draw_world(d, t, (WALL_TOP, WALL_L, WALL_R))

    if AIM_START <= t < RELEASE:
        pts = bres(MUZZLE, IMPACT)
        if t < READY:
            for i, p in enumerate(pts):
                if i % 3 == 0:
                    d.point(p, fill=RED)
        elif (t // 2) % 2 == 0:          # parpadeo al estar lista
            for i, p in enumerate(pts):
                if i % 3 == 0:
                    d.point(p, fill=GREEN)

    if 0 <= a < 8:
        col = WHITE if a < 3 else (CYAN if a < 6 else CYAN_DIM)
        line(d, MUZZLE, IMPACT, col)
        if a == 0:
            mx, my = MUZZLE
            d.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=WHITE)

    if t == RELEASE:
        # (x, y, suelo?) : anillos isometricos en el suelo y uno en el muro
        c["rings"] = ([(FLOOR_MUZZLE[0], FLOOR_MUZZLE[1], True)]
                      + [(feet_of(s)[0], feet_of(s)[1], True) for s in ENEMY_S]
                      + [(IMPACT[0], IMPACT[1], False)])
    if c.get("rings") and 0 <= a < len(RING_RAMP):
        for cx, cy, flat in c["rings"]:
            rx = 2 + 2 * a
            ry = rx // 2 if flat else rx
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=RING_RAMP[a])

    if t >= RELEASE + 3:                  # marca oscura en el muro
        d.ellipse([216, 85, 221, 89], fill=BG, outline=WALL_L)

    if t == DIE:
        for k, s in enumerate(ENEMY_S):
            fx, fy = feet_of(s)
            c["parts"].spawn(fx, fy - 6, 6, 320, 12, (WHITE, ENEMY_COL[k], DARK_RED), grav=20)
    c["parts"].update_and_draw(d)
    return img


# ---------------------------------------------------------------- C: rayo
SHAKE = ((2, 0), (-2, 1), (1, -2))


def frame_C(t, c):
    img = c["base"].copy()
    d = ImageDraw.Draw(img)

    if t == RELEASE:                      # destello de pantalla, 1 fotograma
        d.rectangle([0, 0, W - 1, H - 1], fill=WHITE)
        c["flash"] = True
        return img

    wall = (WHITE, CYAN_DIM, WHITE) if t == RELEASE + 1 else (WALL_TOP, WALL_L, WALL_R)
    draw_world(d, t, wall)

    if AIM_START <= t < RELEASE:
        col = RED if t < READY else GREEN
        cx, cy = beam_pt(ENEMY_S[0])     # reticula sobre el primer enemigo
        line(d, MUZZLE, IMPACT, col)
        if t < READY:
            r = 11 - (6 * (t - AIM_START)) // (READY - AIM_START)
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                x, y = cx + sx * r, cy + sy * r
                line(d, (x, y), (x - sx * 3, y), col)
                line(d, (x, y), (x, y - sy * 3), col)
        else:                             # se cierra al estar lista
            d.rectangle([cx - 5, cy - 5, cx + 5, cy + 5], outline=col)
        d.point((cx, cy), fill=col)

    if RELEASE + 1 <= t <= RELEASE + 3:
        rng = random.Random(1000 + t)
        pts = [MUZZLE]
        for i in range(1, 8):
            bx, by = beam_pt((WALL_S * i) // 8)
            pts.append((bx + rng.randint(-1, 1), by + rng.randint(-2, 2)))
        pts.append(IMPACT)
        for dy, col in ((-1, CYAN), (1, CYAN), (0, WHITE)):   # borde cian, nucleo blanco
            for p0, p1 in zip(pts, pts[1:]):
                line(d, p0, p1, col, dy)
        k = t - (RELEASE + 1)
        L = (5, 4, 2)[k]
        col = (WHITE, CYAN, CYAN_DIM)[k]
        centres = [(feet_of(s)[0], feet_of(s)[1] - 6) for s in ENEMY_S] + [IMPACT]
        for x, y in centres:             # destello en cruz
            line(d, (x - L, y), (x + L, y), col)
            line(d, (x, y - L), (x, y + L), col)

    if t in (RELEASE + 4, RELEASE + 5):
        line(d, MUZZLE, IMPACT, CYAN if t == RELEASE + 4 else CYAN_DIM)

    if RELEASE + 1 <= t <= RELEASE + 3:  # temblor de 2 px durante 3 fotogramas
        dx, dy = SHAKE[t - (RELEASE + 1)]
        out = make_canvas()
        out.paste(img, (dx, dy))
        img = out
    return img


def render(frame_fn, label, seed):
    rng = random.Random(seed)
    ctx = {"base": make_floor(), "rng": rng, "parts": Particles(rng),
           "rings": [], "flash": False}
    frames = []
    for t in range(SIM_FRAMES):
        ctx["flash"] = False
        img = frame_fn(t, ctx)
        d = ImageDraw.Draw(img)
        d.text((3, 3), label, fill=BG if ctx["flash"] else WHITE, font=FONT)
        frames.append(img)
    frames.append(frames[-1].copy())     # pausa final
    durations = [FRAME_MS] * SIM_FRAMES + [HOLD_MS]
    return frames, durations


def main():
    os.makedirs(ASSETS, exist_ok=True)
    jobs = [
        ("A: trazo que se desvanece", frame_A, "sniper_A_trace.gif", 11),
        ("B: anillos de choque", frame_B, "sniper_B_rings.gif", 22),
        ("C: rayo irregular", frame_C, "sniper_C_beam.gif", 33),
    ]
    for label, fn, name, seed in jobs:
        frames, durations = render(fn, label, seed)
        big = [f.resize((W * SCALE, H * SCALE), Image.NEAREST) for f in frames]
        path = os.path.join(ASSETS, name)
        big[0].save(path, save_all=True, append_images=big[1:],
                    duration=durations, loop=0, disposal=1)
        print(f"{path} frames={len(big)} size={os.path.getsize(path) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
