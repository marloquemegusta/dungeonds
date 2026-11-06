"""Mockup (NOT a ROM capture): candidate sniper charge auras drawn over the real hero sprite."""
import math, random
from PIL import Image, ImageDraw, ImageFont
SRC = 'test_output/aura_v4/aimline_0000.png'
im0 = Image.open(SRC).convert('RGB'); w, h = im0.size
base = im0.crop((0, h // 2, w, h // 2 + 170)).crop((14, 44, 94, 104))   # 80x60 around the hero
FX, FY = 24, 54          # feet in the crop
W, H = base.size
WHITE, LB, MB, DB = (255, 255, 255), (150, 215, 255), (70, 150, 255), (30, 70, 200)
YEL, ORA = (255, 225, 80), (255, 140, 30)

def is_body(p):
    r, g, b = p
    return b >= r - 6 or (r + g + b) < 110       # hero is blue-grey or dark outline; floor is brown

def render(draw_fn, seed=3):
    rnd = random.Random(seed)
    back, front = [], []          # (x, y, color)
    draw_fn(rnd, back, front)
    im = base.copy(); px = im.load()
    for x, y, c in back:
        if 0 <= x < W and 0 <= y < H and not is_body(px[x, y]): px[x, y] = c
    for x, y, c in front:
        if 0 <= x < W and 0 <= y < H: px[x, y] = c
    return im

def put(back, front, x, y, c, depth):
    (back if depth < 0 else front).append((int(round(x)), int(round(y)), c))

def pt(phase, hgt, rx=11):
    a = phase * 2 * math.pi
    return FX + math.cos(a) * rx, FY + math.sin(a) * rx / 2 - hgt, math.sin(a)

# 1. single helix of discrete sparks (dots with gaps)
def o1(r, back, front):
    for k in range(26):
        t = k / 25; ph = t * 1.6 + 0.1
        if k % 3 == 2: continue
        x, y, d = pt(ph, t * 32); put(back, front, x, y, WHITE if k % 2 else LB, d)
        if k % 3 == 0: put(back, front, x + 1, y, MB, d)
# 2. double helix of dashed sparks
def o2(r, back, front):
    for s in (0, .5):
        for k in range(30):
            if k % 4 == 3: continue
            t = k / 29; x, y, d = pt(s + t * 1.7, t * 34)
            put(back, front, x, y, WHITE, d); put(back, front, x, y + 1, MB, d)
# 3. comet sparks: bright head with fading tail along the spiral
def o3(r, back, front):
    for s in (0.0, 0.33, 0.66):
        head = s
        for j in range(7):
            t = (head * 1.0 + 0.15) ; ph = s + j * -0.035 + 0.0
            hh = 6 + s * 20 + (6 - j) * 2.2
            x, y, d = pt(s * 1.9 + 0.25 - j * 0.045, hh)
            put(back, front, x, y, [WHITE, LB, LB, MB, MB, DB, DB][j], d)
# 4. arcs: short curved bolts orbiting at different heights (broken ring segments)
def o4(r, back, front):
    for lvl in range(5):
        hh = 4 + lvl * 7; start = lvl * 0.23
        for k in range(9):
            if (k + lvl) % 5 == 4: continue
            x, y, d = pt(start + k * 0.045, hh + math.sin(k) * 1.5, 12 - lvl)
            put(back, front, x, y, WHITE if k % 3 == 0 else LB, d)
# 5. loose sparks only, rising on spiral paths (lots of isolated pixels, some 2-px)
def o5(r, back, front):
    for k in range(40):
        t = r.random(); ph = r.random() + t * 1.2; x, y, d = pt(ph, t * 34, 9 + r.random() * 4)
        c = WHITE if r.random() < .3 else (LB if r.random() < .6 else MB)
        put(back, front, x, y, c, d)
        if r.random() < .3: put(back, front, x, y + 1, c, d)
# 6. mix: faint dotted double helix + loose sparks + zigzag bolt at the crossings
def o6(r, back, front):
    for s in (0, .5):
        for k in range(28):
            if k % 2: continue
            t = k / 27; x, y, d = pt(s + t * 1.7, t * 34)
            put(back, front, x, y, LB if k % 4 else WHITE, d)
    for k in range(18):
        t = r.random(); x, y, d = pt(r.random() + t, t * 34, 13); put(back, front, x, y, WHITE, d)
    for cx in (0.25, 0.75):
        x, y, d = pt(cx + 0.0, 17)
        for j in range(5):
            put(back, front, x - 6 + j * 3 + r.randint(-1, 1), y + r.randint(-3, 3), WHITE, 1)

opts = [("1  Helice simple de chispas", o1), ("2  Doble helice punteada", o2), ("3  Cometas (cabeza + estela)", o3),
        ("4  Arcos rotos orbitando", o4), ("5  Chispas sueltas en espiral", o5), ("6  Mezcla + relampagos", o6)]
S = 5
sheet = Image.new('RGB', (3 * W * S, 2 * (H * S + 24)), (20, 20, 28)); d = ImageDraw.Draw(sheet)
for i, (name, fn) in enumerate(opts):
    im = render(fn).resize((W * S, H * S), Image.NEAREST)
    x, y = (i % 3) * W * S, (i // 3) * (H * S + 24)
    sheet.paste(im, (x, y + 24)); d.text((x + 6, y + 6), name, fill=(255, 255, 255))
sheet.save('walkthroughs/weapon-previews/assets/sniper_aura_opciones.png'); print(sheet.size)
