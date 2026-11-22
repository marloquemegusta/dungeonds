#!/usr/bin/env python
"""Mockups A/B/C del hechizo de suelo «Glifo» (grieta de luz). Reproducible:
    python tools/glifo_mockup/glifo_mockup.py [sello|redil|zarza]
Genera 3 GIF (filas Sello / Redil / Zarza) con columnas A|B|C y hojas de contacto.
Todo a 128x96 nativos (pantalla DS recortada), suelo y sprites reales de la ROM."""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "walkthroughs", "glifo-diseno", "assets", "mockup")
CAP = os.path.join(ROOT, "walkthroughs", "arpg-predemo", "assets", "combate_glifo.png")
SPR = os.path.join(ROOT, "assets", "sprites", "characters")


def c15(r, g, b):
    return (round(r * 255 / 31), round(g * 255 / 31), round(b * 255 / 31))


IVORY = c15(29, 25, 19); GOLD = c15(27, 20, 11); AMBER = c15(24, 15, 7)
EMBER = c15(20, 9, 5); CRIMSON = c15(15, 5, 4); DEEP = c15(9, 3, 3)
ASH_A = c15(15, 13, 12); ASH_B = c15(10, 9, 8); ASH_C = c15(6, 5, 5)
SMOKE_L = c15(22, 20, 18); SMOKE_M = c15(18, 16, 14)
COLD = c15(17, 18, 21)  # acento frio apagado (ceniza azulada)

W, H = 128, 96
CX, CY = 64, 54
RX, RY = 40, 20
T = 189                 # frames de juego del bucle (60 fps)
STEP = 3                # exporta cada 3 -> 20 fps (50 ms)
OPEN_END, DET0, DET1, CLOSE1 = 36, 126, 141, 171


def hsh(x, y, t, s=0):
    v = (int(x) * 73856093) ^ (int(y) * 19349663) ^ (int(t) * 83492791) ^ (int(s) * 2654435761)
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return (v ^ (v >> 16)) / 4294967296.0


# ------------------------------------------------------------------ suelo
def make_floor():
    src = np.array(Image.open(CAP).convert("RGB"))
    tile = src[190:222, 40:72]
    reps = np.tile(tile, (4, 5, 1))
    return reps[:H, :W].copy()


FLOOR = make_floor()


# ------------------------------------------------------------------ sprites
class Sheet:
    def __init__(self, name):
        arr = np.array(Image.open(os.path.join(SPR, name, "spritesheet.png")).convert("RGBA"))
        self.cells = [[arr[r * 40:(r + 1) * 40, c * 40:(c + 1) * 40] for c in range(8)] for r in range(8)]
        bot = 0
        for r in range(8):
            for c in range(8):
                ys = np.where(self.cells[r][c][:, :, 3] > 0)[0]
                if len(ys):
                    bot = max(bot, ys.max())
        self.foot = int(bot)


SHEETS = {}


def sheet(name):
    if name not in SHEETS:
        SHEETS[name] = Sheet(name)
    return SHEETS[name]


# ------------------------------------------------------------------ runas
def arc(r, a0, a1, n=None):
    n = n or max(8, int(abs(a1 - a0) / (2 * math.pi) * 96))
    return [(r * math.cos(a0 + (a1 - a0) * i / n), r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def ln(p, q):
    return [p, q]


def cross(cu, cv, hu, hv):
    return [[(cu, cv - hv), (cu, cv + hv)], [(cu - hu, cv - hv * 0.35), (cu + hu, cv - hv * 0.35)]]


def polar(r, a):
    return (r * math.cos(a), r * math.sin(a))


TOP = -math.pi / 2
FULL = 2 * math.pi


def strokes_for(variant, aura):
    """Lista de (puntos en circulo unidad, grupo, temblor px, prob. rama, brillo)."""
    S = []

    def add(pts, g, j, pb, br=1.0):
        S.append((pts, g, j, pb, br))

    rnd = random.Random(7 + ord(variant))
    redil = aura == "redil"
    if variant == "A":
        add(arc(1.0, TOP, TOP + FULL), "ring", 0.45, 0.03)
        add(arc(0.82, TOP, TOP + FULL), "ring", 0.45, 0.03)
        for k in range(32):                      # inscripcion tallada
            a = TOP + FULL * (k + 0.5) / 32
            add(ln(polar(0.86, a), polar(0.96, a)), "inner", 0.2, 0.0)
            m = rnd.random()
            if m < 0.35:
                p = polar(0.91, a); t = (-math.sin(a) * 0.045, math.cos(a) * 0.045)
                add(ln((p[0] - t[0], p[1] - t[1]), (p[0] + t[0], p[1] + t[1])), "inner", 0.15, 0.0)
            elif m < 0.55:
                add(ln(polar(0.96, a), polar(0.96, a + 0.07)), "inner", 0.15, 0.0)
        add(arc(0.42, TOP, TOP + FULL), "inner", 0.4, 0.03)
        if not redil:
            for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                p = polar(0.62, a)
                for s in cross(p[0], p[1], 0.075, 0.17):
                    add(s, "inner", 0.15, 0.0)
            # crismon (Chi-Rho)
            add(ln((0, -0.34), (0, 0.34)), "center", 0.3, 0.02)
            add([(0.13 * math.cos(t), -0.22 + 0.13 * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 12)],
                "center", 0.3, 0.0)
            add(ln((-0.3, -0.3), (0.3, 0.3)), "center", 0.3, 0.02)
            add(ln((0.3, -0.3), (-0.3, 0.3)), "center", 0.3, 0.02)
        else:
            for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                p = polar(0.62, a)
                for s in cross(p[0], p[1], 0.075, 0.17):
                    add(s, "inner", 0.15, 0.0)
    elif variant == "B":
        add(arc(1.0, TOP, TOP + FULL), "ring", 0.6, 0.05)
        add(arc(0.82, TOP, TOP + FULL), "ring", 0.6, 0.04)
        for k in range(12):                      # doce apostoles
            a = TOP + FULL * (k + 0.5) / 12
            p = polar(0.91, a)
            for s in cross(p[0], p[1], 0.05, 0.075):
                add(s, "inner", 0.1, 0.0)
        if not redil:
            add(arc(0.15, TOP, TOP + FULL, 24), "center", 0.25, 0.0)
            add(arc(0.24, TOP, TOP + FULL, 30), "center", 0.3, 0.02)
            for k in range(16):
                a = TOP + FULL * k / 16
                r1 = 0.76 if k % 2 == 0 else 0.5
                if k % 4 == 3:                    # rayo ondulado (llama de custodia)
                    pts = []
                    for i in range(9):
                        r = 0.3 + (r1 - 0.3) * i / 8
                        pts.append(polar(r, a + 0.045 * (1 if i % 2 else -1)))
                    add(pts, "inner", 0.3, 0.05, 1.12)
                else:
                    add(ln(polar(0.3, a), polar(r1, a)), "inner", 0.45, 0.06, 1.12)
        else:
            add(arc(0.5, TOP, TOP + FULL), "inner", 0.5, 0.04)
    else:  # C
        add(arc(1.0, TOP, TOP + FULL), "ring", 1.0, 0.07)
        for k in range(22):                      # corona de espinas
            a = TOP + FULL * (k + 0.3 * rnd.random()) / 22
            if k % 2 == 0:
                add(ln(polar(0.99, a), polar(1.12, a + 0.03)), "inner", 0.35, 0.0)
            else:
                add(ln(polar(1.0, a), polar(0.9, a - 0.03)), "inner", 0.35, 0.0)
        for k in range(8):                       # huesos / muescas
            a = TOP + FULL * (k + 0.5) / 8
            p0, p1 = polar(0.80, a), polar(0.90, a)
            add(ln(p0, p1), "inner", 0.4, 0.0)
            t = (-math.sin(a), math.cos(a))
            for p in (p0, p1):
                add(ln((p[0] - t[0] * 0.04, p[1] - t[1] * 0.04), (p[0] + t[0] * 0.04, p[1] + t[1] * 0.04)), "inner", 0.2, 0.0)
        radii = [0.28, 0.42, 0.56, 0.70]
        gaps = [math.pi / 2, 3 * math.pi / 2, math.pi / 2, 3 * math.pi / 2]
        gw = 0.42
        for i, (r, g) in enumerate(zip(radii, gaps)):
            if redil and i < 2:
                continue
            add(arc(r, g + gw, g - gw + FULL), "center" if i < 2 else "inner", 0.9, 0.09)
            if i < len(radii) - 1 and not (redil and i < 2):
                ge = g + gw
                add(ln(polar(r, ge), polar(radii[i + 1], ge)), "inner", 0.6, 0.0)
        if not redil:
            add(ln((0, -0.1), (0, 0.1)), "center", 0.4, 0.0)
    if redil:                                    # brazos en espiral hacia el centro
        for arm in range(3):
            th0 = TOP + arm * FULL / 3
            pts = [polar(0.95 - 0.8 * t, th0 + 1.9 * t) for t in np.linspace(0, 1, 42)]
            add(pts, "inner", 0.55 if variant != "C" else 0.9, 0.05, 1.05)
    return S


def bres(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy
    return pts


class Rune:
    def __init__(self, variant, aura):
        rnd = random.Random(1000 + ord(variant) * 7 + (3 if aura == "redil" else 0))
        pix = {}   # (x,y) -> [kind, grupo, frac, brillo]
        for pts, grp, jit, pb, br in strokes_for(variant, aura):
            sc = [(CX + u * RX, CY + v * RY) for u, v in pts]
            lens = [0.0]
            for i in range(len(sc) - 1):
                lens.append(lens[-1] + math.hypot(sc[i + 1][0] - sc[i][0], sc[i + 1][1] - sc[i][1]))
            total = max(lens[-1], 1e-6)
            n = max(1, int(total / 2.0))
            res = []
            j = 0
            for k in range(n + 1):
                d = total * k / n
                while j < len(sc) - 2 and lens[j + 1] < d:
                    j += 1
                seg = max(lens[j + 1] - lens[j], 1e-6)
                t = (d - lens[j]) / seg
                x = sc[j][0] + (sc[j + 1][0] - sc[j][0]) * t
                y = sc[j][1] + (sc[j + 1][1] - sc[j][1]) * t
                tx, ty = (sc[j + 1][0] - sc[j][0]) / seg, (sc[j + 1][1] - sc[j][1]) / seg
                o = rnd.gauss(0, jit) if 0 < k < n else 0
                res.append((x - ty * o, y + tx * o, d / total, (tx, ty)))
            for i in range(len(res) - 1):
                a, b = res[i], res[i + 1]
                for (px, py) in bres(round(a[0]), round(a[1]), round(b[0]), round(b[1])):
                    if 0 <= px < W and 0 <= py < H and ((px, py) not in pix or pix[(px, py)][0] == 1):
                        pix[(px, py)] = [0, grp, a[2], br if hsh(px, py, 9) > 0.06 else br * 0.5]
            for i, r in enumerate(res):          # astillas / ramificaciones cortas
                if 0 < i < len(res) - 1 and rnd.random() < pb:
                    ang = math.atan2(r[3][1], r[3][0]) + rnd.choice((-1, 1)) * rnd.uniform(0.7, 1.4)
                    L = rnd.randint(2, 5 if variant != "C" else 6)
                    x1, y1 = r[0] + math.cos(ang) * L, r[1] + math.sin(ang) * L
                    for (px, py) in bres(round(r[0]), round(r[1]), round(x1), round(y1)):
                        if 0 <= px < W and 0 <= py < H and (px, py) not in pix:
                            pix[(px, py)] = [1, grp, r[2], 0.8]
        xs, ys, kind, order, br, rn = [], [], [], [], [], []
        for (x, y), (k, g, fr, b) in pix.items():
            r_ = math.hypot((x - CX) / RX, (y - CY) / RY)
            if g == "ring":
                o = 0.42 * fr
            else:
                o = 0.4 + 0.6 * (0.75 * (1 - min(r_, 1.0)) + 0.25 * fr)
            xs.append(x); ys.append(y); kind.append(k); order.append(min(o, 1.0)); br.append(b); rn.append(r_)
        self.x = np.array(xs); self.y = np.array(ys); self.kind = np.array(kind)
        self.order = np.array(order); self.br = np.array(br); self.rn = np.array(rn)
        self.te = DET1 + (1.1 - np.minimum(self.rn, 1.1)) / 1.1 * (CLOSE1 - DET1)
        self.n = len(xs)
        self.set = set(zip(xs, ys))
        # esquirlas de piedra levantada (pixeles fijos junto a la grieta)
        self.shards = [i for i in range(self.n)
                       if self.kind[i] == 0 and hsh(self.x[i], self.y[i], 5, ord(variant)) < 0.09]


# ------------------------------------------------------------------ utilidades de dibujo
def put(img, x, y, col):
    if 0 <= x < W and 0 <= y < H:
        img[y, x] = col


def blend(img, x, y, col, a):
    if 0 <= x < W and 0 <= y < H:
        img[y, x] = img[y, x] * (1 - a) + np.array(col, np.float32) * a


def dil(mask, n):
    m = mask.copy()
    for _ in range(n):
        p = m.copy()
        p[1:, :] |= m[:-1, :]; p[:-1, :] |= m[1:, :]
        p[:, 1:] |= m[:, :-1]; p[:, :-1] |= m[:, 1:]
        p[1:, 1:] |= m[:-1, :-1]; p[:-1, :-1] |= m[1:, 1:]
        p[1:, :-1] |= m[:-1, 1:]; p[:-1, 1:] |= m[1:, :-1]
        m = p
    return m


def tint(img, mask, col, a):
    img[mask] = img[mask] * (1 - a) + np.array(col, dtype=np.float32) * a


# ------------------------------------------------------------------ simulacion
class Enemy:
    def __init__(self, name, pos, speed, theta, slot, div, phase):
        self.sh = sheet(name); self.g = list(pos); self.speed = speed
        self.theta = theta; self.slot = slot; self.div = div; self.phase = phase
        self.fast = speed > 0.4; self.face = theta

    def update(self, f, row):
        gx, gy = self.g
        r = math.hypot(gx, gy)
        pulling = row == "redil" and OPEN_END <= f < DET1
        if pulling:
            if r > 1:
                self.theta = math.atan2(gy, gx)
        else:
            self.theta += 0.035 * math.sin(f * 0.045 + self.phase)
            if r > 30:
                d = math.atan2(-gy, -gx) - self.theta
                d = (d + math.pi) % (2 * math.pi) - math.pi
                self.theta += 0.1 * d
        vx, vy = self.speed * math.cos(self.theta), self.speed * math.sin(self.theta)
        if pulling:
            sx, sy = self.slot
            d = math.hypot(sx - gx, sy - gy)
            if d > 0.8:
                vx += 0.47 * (sx - gx) / d; vy += 0.47 * (sy - gy) / d
            elif not self.fast:
                vx = vy = 0; self.g = [sx, sy]
        if not pulling:
            for o in self.others:
                dx, dy = self.g[0] - o.g[0], self.g[1] - o.g[1]
                dd = math.hypot(dx, dy)
                if 0.01 < dd < 22:
                    vx += 0.25 * dx / dd; vy += 0.25 * dy / dd
        gx, gy = self.g[0] + vx, self.g[1] + vy
        r = math.hypot(gx, gy)
        if r > 37:
            gx, gy = gx * 37 / r, gy * 37 / r
        self.g = [gx, gy]
        self.face = self.theta

    def screen(self):
        return CX + self.g[0], CY + self.g[1] * 0.5

    def dir_idx(self):
        a = math.degrees(math.atan2(math.sin(self.face) * 0.5, math.cos(self.face)))
        return int(round((a - 90) / 45.0)) % 8


def new_enemies():
    L = [
        Enemy("exvoto_monja", (-24, 6), 0.25, 0.3, (-4, 2), 4, 0.0),
        Enemy("exvoto_parroco", (22, -12), 0.18, 2.4, (4, -3), 6, 1.7),
        Enemy("exvoto_bebe", (2, 26), 0.55, -0.9, (0, 0), 3, 3.1),
    ]
    for e in L:
        e.others = [o for o in L if o is not e]
    return L


def tongue_pixels(x, y, age, life, Hh, f, seed):
    t = min(age / life, 1.0)
    hh = Hh * (math.sin(math.pi * t) ** 0.8)
    n = int(round(hh))
    px = []
    for i in range(n):
        wob = int(round(math.sin(f * 0.8 + seed + i * 1.1) * 0.7 * (i / max(1, n))))
        fr = i / max(1, n - 1)
        col = EMBER if fr < 0.34 else (AMBER if fr < 0.7 else GOLD)
        if i == n - 1 and n >= 3:
            col = IVORY
        px.append((x + wob, y - 1 - i, col))
    if n >= 3:
        px.append((x + 1, y - 1, EMBER)); px.append((x - 1, y - 1, EMBER))
    return px


def mote_color(t):
    return IVORY if t < 0.18 else GOLD if t < 0.45 else AMBER if t < 0.75 else EMBER


class Scene:
    def __init__(self, variant, row):
        self.v, self.row = variant, row
        self.rune = Rune(variant, "redil" if row == "redil" else "x")
        self.rnd = random.Random(500 + ord(variant) + len(row) * 31)
        self.en = new_enemies()
        self.motes, self.tongues, self.smoke, self.spir, self.eflames = [], [], [], [], []

    # -- estado de brillo de la grieta
    def crack_state(self, f):
        R = self.rune
        if f < OPEN_END:
            p = f / OPEN_END
            vis = R.order <= p
            head = np.maximum(0, 1 - (p - R.order) / 0.07)
            b = 0.75 + 0.65 * head
        else:
            vis = np.ones(R.n, bool)
            if f < DET0:
                b0 = 0.85 + 0.22 * math.sin(2 * math.pi * (f - OPEN_END) / 40.0 + 0.5)
            elif f < DET1:
                b0 = 1.45 - 0.5 * (f - DET0) / (DET1 - DET0)
            else:
                b0 = 0.9
            b = np.full(R.n, b0)
        b = b * R.br
        noise = np.array([hsh(R.x[i], R.y[i], f // 4) for i in range(R.n)])
        b = b + 0.12 * (noise - 0.5)
        scar = np.zeros(R.n)
        if f >= DET1:
            ext = R.te <= f
            scar = np.where(ext, 0.8 * np.clip(1 - (f - R.te) / 18.0, 0, 1), 0)
            vis = vis & ~ext
            b = np.where((R.te - f) < 5, b * 0.55, b)
        return vis, b, scar

    def spawn(self, f, vis):
        R, rnd, row = self.rune, self.rnd, self.row
        idx_vis = np.where(vis)[0]
        if len(idx_vis) == 0:
            return
        if f < CLOSE1 - 6:
            rate = (0.9 if f < DET0 else 3.0) * (0.55 if row == "zarza" else 1.0)
            k = int(rate) + (1 if rnd.random() < rate - int(rate) else 0)
            for _ in range(k):
                i = int(idx_vis[rnd.randrange(len(idx_vis))])
                self.motes.append([R.x[i], R.y[i], 0.0, rnd.uniform(0.15, 0.4), rnd.uniform(0, 6.28), 0, rnd.randint(14, 30)])
        if row == "zarza" and OPEN_END + 6 <= f < DET1:
            if f < DET0:
                rate = 0.6
                k = int(rate) + (1 if rnd.random() < rate - int(rate) else 0)
                for _ in range(k):
                    i = int(idx_vis[rnd.randrange(len(idx_vis))])
                    self.tongues.append([R.x[i], R.y[i], 0, rnd.randint(12, 20), rnd.uniform(3, 6), rnd.uniform(0, 6.28), R.y[i]])
            elif f < DET0 + 8:
                for i in idx_vis:
                    if rnd.random() < 0.07:
                        self.tongues.append([R.x[i], R.y[i], 0, rnd.randint(10, 16), rnd.uniform(7, 11), rnd.uniform(0, 6.28), R.y[i]])
            for e in self.en:                     # enemigos ardiendo
                ex, ey = e.screen()
                if math.hypot(e.g[0], e.g[1]) < 40:
                    kk = 1.1 if f < DET0 else 2.0
                    k = int(kk) + (1 if rnd.random() < kk - int(kk) else 0)
                    for _ in range(k):
                        bx = ex + rnd.randint(-6, 6)
                        by = ey - rnd.randint(4, 26)
                        self.eflames.append([bx, by, 0, rnd.randint(7, 12), rnd.uniform(3, 5), rnd.uniform(0, 6.28), ey + 0.5])
        if row == "redil" and OPEN_END - 6 <= f < DET0 and rnd.random() < 0.55:
            self.spir.append([0.97, rnd.uniform(0, 6.28), 0, rnd.randint(45, 70), rnd.random() < 0.3])
        if row == "redil" and DET0 <= f < DET0 + 6:
            for _ in range(2):
                self.spir.append([0.97, rnd.uniform(0, 6.28), 0, rnd.randint(25, 40), False])

    def step_particles(self, f):
        rnd = self.rnd
        for m in self.motes:
            m[5] += 1; m[2] += m[3]
        self.motes = [m for m in self.motes if m[5] < m[6]]
        for tg in self.tongues + self.eflames:
            tg[2] += 1
            if self.row == "zarza" and tg[2] == int(tg[3] * 0.7) and tg[4] > 3.5 and rnd.random() < 0.7:
                self.smoke.append([tg[0], tg[1] - tg[4], 0.0, 0, rnd.randint(10, 16), tg[6]])
        self.tongues = [t for t in self.tongues if t[2] < t[3]]
        self.eflames = [t for t in self.eflames if t[2] < t[3]]
        for s in self.smoke:
            s[3] += 1; s[2] += 0.3; s[0] += rnd.uniform(-0.15, 0.15)
        self.smoke = [s for s in self.smoke if s[3] < s[4]]
        for p in self.spir:
            p[2] += 1
            p[0] -= 0.97 / p[3]
            p[1] += 0.07 / (p[0] + 0.25) + 0.03
        self.spir = [p for p in self.spir if p[2] < p[3] and p[0] > 0.04]

    # -- render de un fotograma
    def render(self, f):
        R = self.rune
        row = self.row
        vis, b, scar = self.crack_state(f)
        img = FLOOR.astype(np.float32).copy()
        yy, xx = np.mgrid[0:H, 0:W]
        inside = ((xx - CX) / RX) ** 2 + ((yy - CY) / RY) ** 2 <= 1.0
        if OPEN_END <= f < DET1:
            tint(img, inside, AMBER, 0.05 if f < DET0 else 0.08)
        # cicatriz oscura
        if (scar > 0).any():
            sm = np.zeros((H, W), np.float32)
            for i in np.where(scar > 0)[0]:
                sm[R.y[i], R.x[i]] = max(sm[R.y[i], R.x[i]], scar[i])
            neigh = dil(sm > 0, 1) & (sm == 0)
            img = img * (1 - sm[..., None]) + np.array(DEEP, np.float32) * sm[..., None]
            tint(img, neigh, DEEP, 0.18)
        # halos
        lit = vis
        M = np.zeros((H, W), bool); M2 = M.copy(); M3 = M.copy(); core = M.copy()
        for i in np.where(lit)[0]:
            y, x = R.y[i], R.x[i]
            core[y, x] = True
            if b[i] >= 0.4: M[y, x] = True
            if b[i] >= 0.72: M2[y, x] = True
            if b[i] >= 1.2: M3[y, x] = True
        warm = EMBER if row == "zarza" else AMBER
        tint(img, dil(M3, 3) & ~core, IVORY, 0.12)
        tint(img, dil(M2, 2) & ~core, warm, 0.12)
        tint(img, dil(M, 1) & ~core, GOLD, 0.30)
        # bordes que tiemblan (piedra oscura junto a la fisura) y esquirlas
        for i in np.where(lit)[0]:
            x, y = int(R.x[i]), int(R.y[i])
            for k, (dx, dy) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
                if (x + dx, y + dy) in R.set:
                    continue
                if hsh(x, y, f // 5, k) < 0.28:
                    blend(img, x + dx, y + dy, DEEP, 0.6)
        det_pop = DET0 <= f < DET0 + 9
        for i in R.shards:
            if lit[i]:
                x, y = int(R.x[i]), int(R.y[i])
                up = 1 + (2 if det_pop and hsh(x, y, f // 3) < 0.6 else 0)
                put(img, x + 1, y, ASH_C)
                put(img, x + 1, y - up, SMOKE_M)
                if up == 1:
                    put(img, x + 2, y - 1, ASH_A)
        # nucleo de la grieta
        for i in np.where(lit)[0]:
            bi = b[i]
            if R.kind[i] == 1:
                col = GOLD if bi >= 0.55 else AMBER
            else:
                col = IVORY if bi >= 0.55 else GOLD if bi >= 0.4 else AMBER if bi >= 0.28 else EMBER
            put(img, int(R.x[i]), int(R.y[i]), col)
        # barrido de la detonacion
        if DET0 <= f < DET1:
            t = (f - DET0) / (DET1 - DET0)
            rr = min(1.05, t * 1.3)
            ring = np.zeros((H, W), bool)
            for a in np.linspace(0, 2 * math.pi, 220):
                x = round(CX + rr * RX * math.cos(a)); y = round(CY + rr * RY * math.sin(a))
                if 0 <= x < W and 0 <= y < H:
                    ring[y, x] = True
            fade = 1 - t * 0.6
            tint(img, dil(ring, 1) & ~ring, GOLD, 0.35 * fade)
            tint(img, ring, IVORY, 0.9 * fade)
            tint(img, inside & ~ring, IVORY, 0.10 * (1 - t))
        # vortice central (Redil)
        if row == "redil":
            s = 0.0
            if f >= OPEN_END - 16:
                s = min(1.0, (f - (OPEN_END - 16)) / 16.0)
            if f >= DET1:
                s = max(0.0, 1 - (f - DET1) / 20.0)
            if DET0 <= f < DET1:
                s = 1.25
            if s > 0:
                self.draw_vortex(img, f, s)
        # sombras de enemigos
        for e in self.en:
            ex, ey = e.screen()
            for yy_ in range(-5, 6):
                for xx_ in range(-12, 13):
                    if (xx_ / 11.0) ** 2 + (yy_ / 4.5) ** 2 <= 1.0:
                        blend(img, int(round(ex)) + xx_, int(round(ey)) + yy_, (0, 0, 0), 0.38)
        # entidades ordenadas por profundidad (suelo y)
        ents = []
        for e in self.en:
            ents.append((e.screen()[1], 0, ("enemy", e)))
        for m in self.motes:
            t = m[5] / m[6]
            x = m[0] + math.sin(m[5] * 0.3 + m[4]) * 0.9
            y = m[1] - m[2]
            px = [(int(round(x)), int(round(y)), mote_color(t))]
            if t < 0.5:
                px.append((int(round(x)), int(round(y)) + 1, GOLD if t < 0.25 else AMBER))
            ents.append((m[1] + 0.2, 1, ("px", px)))
        for tg in self.tongues + self.eflames:
            ents.append((tg[6], 1, ("px", tongue_pixels(int(tg[0]), int(tg[1]), tg[2], tg[3], tg[4], f, tg[5]))))
        for s_ in self.smoke:
            t = s_[3] / s_[4]
            ents.append((s_[5], 1, ("px", [(int(round(s_[0])), int(round(s_[1] - s_[2])), SMOKE_M if t < 0.6 else ASH_A)])))
        for p in self.spir:
            px = []
            for k, col in ((0, GOLD if not p[4] else COLD), (1, AMBER if not p[4] else ASH_A), (2, EMBER)):
                rr = p[0] + 0.035 * k
                th = p[1] - (0.07 / (rr + 0.25) + 0.03) * 2.2 * k
                px.append((int(round(CX + rr * RX * math.cos(th))), int(round(CY + rr * RY * math.sin(th))) - 1, col))
            ents.append((CY + p[0] * RY * math.sin(p[1]), 1, ("px", px)))
        ents.sort(key=lambda e: (e[0], e[1]))
        out = np.clip(img, 0, 255)
        for _, _, (kind, data) in ents:
            if kind == "px":
                for (x, y, col) in data:
                    put(out, x, y, col)
            else:
                self.draw_enemy(out, data, f)
        return out.astype(np.uint8)

    def draw_vortex(self, img, f, s):
        rx, ry = 7.5 * s, 3.9 * s
        yy, xx = np.mgrid[0:H, 0:W]
        v = ((xx - CX) / max(rx, 0.1)) ** 2 + ((yy - CY) / max(ry, 0.1)) ** 2
        img[v <= 1.0] = DEEP
        tint(img, (v > 0.72) & (v <= 1.0), ASH_C, 0.6)
        tint(img, (v > 1.0) & (v <= 1.5) & (yy >= CY), AMBER, 0.35)
        ang0 = f * 0.17
        for arm in range(3):
            for t in np.linspace(0.04, 1.0, 26):
                th = ang0 + arm * 2 * math.pi / 3 + 3.2 * t
                x = round(CX + rx * 0.92 * t * math.cos(th)); y = round(CY + ry * 0.92 * t * math.sin(th))
                put(img, x, y, IVORY if t < 0.35 else GOLD if t < 0.7 else AMBER)
        put(img, CX, CY, IVORY)

    def draw_enemy(self, out, e, f):
        ex, ey = e.screen()
        col = (f // e.div + int(e.phase * 2)) % 8
        cell = e.sh.cells[e.dir_idx()][col]
        fade = min(1.0, (f + 1) / 10.0, (T - f) / 10.0)
        fl = 0.0
        if DET0 <= f < DET0 + 9:
            fl = (0.7, 0.45, 0.22)[(f - DET0) // 3]
        x0 = int(round(ex)) - 20
        y0 = int(round(ey)) - e.sh.foot
        a = cell[:, :, 3].astype(np.float32) / 255.0 * fade
        rgb = cell[:, :, :3].astype(np.float32)
        if fl:
            rgb = rgb * (1 - fl) + np.array(IVORY, np.float32) * fl
        for yy in range(40):
            for xx in range(40):
                aa = a[yy, xx]
                if aa > 0.01:
                    X, Y = x0 + xx, y0 + yy
                    if 0 <= X < W and 0 <= Y < H:
                        out[Y, X] = out[Y, X] * (1 - aa) + rgb[yy, xx] * aa

    def run(self):
        frames = []
        for f in range(T):
            for e in self.en:
                e.update(f, self.row)
            vis, _, _ = self.crack_state(f)
            self.spawn(f, vis)
            self.step_particles(f)
            if f % STEP == 0:
                frames.append(self.render(f))
        return frames


# ------------------------------------------------------------------ composicion
FONT = None


def font():
    global FONT
    if FONT is None:
        try:
            FONT = ImageFont.truetype("arial.ttf", 15)
        except Exception:
            FONT = ImageFont.load_default()
    return FONT


SC = 4; GAP = 8; LAB = 20


def compose(cols):
    n = len(cols)
    w = n * W * SC + (n - 1) * GAP; h = H * SC + LAB
    im = Image.new("RGB", (w, h), (12, 10, 10))
    d = ImageDraw.Draw(im)
    for i, (name, arr) in enumerate(zip("ABC", cols)):
        x = i * (W * SC + GAP)
        im.paste(Image.fromarray(arr).resize((W * SC, H * SC), Image.NEAREST), (x, LAB))
        d.text((x + 6, 2), name, fill=GOLD, font=font())
    return im


def save_gif(frames, path):
    fh = frames[0].height
    pal_src = Image.new("RGB", (frames[0].width, fh * 8))
    for k in range(8):
        pal_src.paste(frames[(k * 8 + 4) % len(frames)], (0, k * fh))
    pal = pal_src.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    qs = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    qs[0].save(path, save_all=True, append_images=qs[1:], duration=50, loop=0, optimize=False, disposal=1)


KEYS = [12, 30, 60, 99, 129, 135, 150, 171]


def contact(frames, path):
    cells = [frames[k // STEP] for k in KEYS]
    cw, chh = cells[0].size
    sh = Image.new("RGB", (cw * 2 + 8, (chh + 6) * 4), (12, 10, 10))
    d = ImageDraw.Draw(sh)
    for i, c in enumerate(cells):
        x = (i % 2) * (cw + 8); y = (i // 2) * (chh + 6)
        sh.paste(c, (x, y))
        d.text((x + cw - 60, y + 2), "f=%d" % KEYS[i], fill=GOLD, font=font())
    sh.save(path)


ROWS = [("fila1_sello", "sello"), ("fila2_redil", "redil"), ("fila3_zarza", "zarza")]


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for stem, row in ROWS:
        if only and only != row:
            continue
        cols = [Scene(v, row).run() for v in "ABC"]
        comp = [compose([cols[0][i], cols[1][i], cols[2][i]]) for i in range(len(cols[0]))]
        gif = os.path.join(OUT, stem + "_abc.gif")
        save_gif(comp, gif)
        contact(comp, os.path.join(OUT, stem + "_abc_contacto.png"))
        print(stem, len(comp), "frames", os.path.getsize(gif) // 1024, "KB")


if __name__ == "__main__":
    main()
