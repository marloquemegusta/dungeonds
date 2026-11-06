"""Mockup (NOT a ROM capture): lightning-bolt auras (Killua / SSJ2 references) over the real hero sprite."""
import math, random
from PIL import Image, ImageDraw
exec(open('walkthroughs/weapon-previews/scripts/aura_mockups.py').read().split('def put(')[0])   # base, is_body, colours, FX, FY

def line(p0, p1):
    (x0, y0), (x1, y1) = [(int(round(a)), int(round(b))) for a, b in (p0, p1)]
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n) for i in range(n + 1)]

def bolt(r, x, y, ang, length, jag=3, step=3, fork=0.0, thick=False, depth=1, out=None, col=LB):
    """Angular zigzag polyline from (x,y) heading `ang`; optional forks."""
    pts = [(x, y)]; cx, cy = x, y; n = max(2, length // step)
    for i in range(n):
        a = ang + r.uniform(-.55, .55)
        cx += math.cos(a) * step + r.uniform(-jag, jag) * .5
        cy += math.sin(a) * step + r.uniform(-jag, jag) * .5
        pts.append((cx, cy))
        if fork and r.random() < fork and i > 0:
            bolt(r, cx, cy, ang + r.choice((-1, 1)) * r.uniform(.6, 1.1), length // 2, jag, step, 0, thick, depth, out, col)
    for a, b in zip(pts, pts[1:]):
        for (px_, py_) in line(a, b):
            out.append((px_, py_, WHITE if thick else col, depth))
            if thick:
                out.append((px_ + 1, py_, col, depth)); out.append((px_, py_ + 1, MB, depth))

def render(fn, seed):
    r = random.Random(seed); out = []; fn(r, out)
    im = base.copy(); px = im.load(); W, H = im.size
    for x, y, c, d in out:           # back first, then front
        if d < 0 and 0 <= x < W and 0 <= y < H and not is_body(px[x, y]): px[x, y] = c
    for x, y, c, d in out:
        if d >= 0 and 0 <= x < W and 0 <= y < H: px[x, y] = c
    return im

def ring(phase, hgt, rx):
    a = phase * 2 * math.pi
    return FX + math.cos(a) * rx, FY + math.sin(a) * rx / 2 - hgt, (1 if math.sin(a) >= 0 else -1)

# A  Killua: bolts that wrap around the body (start on ring, climb tangentially, forking)
def A(r, out):
    for k in range(6):
        ph = k / 6 + .04; hh = 4 + (k * 7) % 28
        x, y, d = ring(ph, hh, 10)
        tang = (ph + .25) * 2 * math.pi
        bolt(r, x, y - 0, -math.pi / 2 + math.cos(tang) * .9, 16, 3, 3, .22, False, d, out)
# B  SSJ2: short thin bolts jutting radially outward from the body at several heights
def B(r, out):
    for k in range(9):
        ph = k / 9 + .03; hh = 5 + (k * 11) % 30
        x, y, d = ring(ph, hh, 6); ang = ph * 2 * math.pi
        bolt(r, x, y, math.atan2(math.sin(ang) * .5 - .25, math.cos(ang)), 11, 2, 3, 0, False, d, out, WHITE if k % 2 else LB)
# C  Crown at the feet (figure 1): spiky bolts bursting up/out of the ground ring + a few hugging bolts
def C(r, out):
    for k in range(8):
        ph = k / 8 + .02; x, y, d = ring(ph, 0, 11); ang = ph * 2 * math.pi
        bolt(r, x, y, math.atan2(math.sin(ang) * .4 - 1.1, math.cos(ang) * .9), 14, 3, 3, .2, True, d, out)
    for k in range(2):
        x, y, d = ring(.1 + k * .5, 12, 9); bolt(r, x, y, -math.pi / 2, 16, 3, 3, .2, False, d, out)
# D  Thick glowing bolts (like the figure statues): few, fat, 2-px with white core
def D(r, out):
    for k in range(5):
        ph = k / 5 + .07; hh = 3 + (k * 9) % 26; x, y, d = ring(ph, hh, 9)
        bolt(r, x, y, ((ph * 2 * math.pi + math.pi / 2) % (2 * math.pi)) - math.pi / 2 * 0 - math.pi / 2 + .3, 15, 3, 3, .2, True, d, out)
# E  Dense crackle: many thin white bolts all around (anime still, picture 2)
def E(r, out):
    for k in range(14):
        ph = r.random(); hh = r.uniform(3, 32); x, y, d = ring(ph, hh, r.uniform(6, 12))
        bolt(r, x, y, r.uniform(0, 2 * math.pi), r.randint(7, 14), 2, 2, .25, False, d, out, WHITE if r.random() < .5 else LB)
# F  Mix: crown at feet + wrapping bolts + some radial spikes + loose sparks
def F(r, out):
    C(r, out); A(random.Random(5), out); B(random.Random(9), out)

opts = [("A  Killua: rayos que envuelven el cuerpo", A, 4), ("B  SSJ2: rayitos finos hacia fuera", B, 7),
        ("C  Corona de rayos desde el suelo", C, 11), ("D  Rayos gordos con nucleo blanco", D, 2),
        ("E  Crepitar denso fino", E, 13), ("F  Mezcla de todo", F, 21)]
S = 5; W, H = base.size
sheet = Image.new('RGB', (3 * W * S, 2 * (H * S + 24)), (20, 20, 28)); d = ImageDraw.Draw(sheet)
for i, (name, fn, seed) in enumerate(opts):
    im = render(fn, seed).resize((W * S, H * S), Image.NEAREST)
    x, y = (i % 3) * W * S, (i // 3) * (H * S + 24)
    sheet.paste(im, (x, y + 24)); d.text((x + 6, y + 6), name, fill=(255, 255, 255))
sheet.save('walkthroughs/weapon-previews/assets/sniper_aura_rayos.png'); print(sheet.size)
