"""Maquetas A/B/C del modo jefe sobre capturas reales de la ROM (solo para elegir, no evidencia de juego)."""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

WT = r"C:\codexlocal\dungeonds\.worktrees\modo-jefe"
SRC = WT + r"\artifacts\modo_jefe"
OUT = sys.argv[1]
FB = r"C:\Windows\Fonts\BOOKOSB.TTF"
FR = r"C:\Windows\Fonts\BOOKOS.TTF"
FI = r"C:\Windows\Fonts\BOOKOSI.TTF"

CREAM = (226, 210, 170)
BONE_DIM = (140, 125, 100)
RED = (150, 36, 34)
RED_DK = (70, 18, 18)
BACK = (28, 20, 20)
GOLD = (216, 160, 88)
INK = (12, 8, 8)

base_c = Image.open(SRC + r"\jefe_c_3s.png").convert("RGB")
base_d = Image.open(SRC + r"\jefe_d_arriba.png").convert("RGB")
codex = Image.open(r"C:\codexlocal\dungeonds\walkthroughs\abanderado-codice\assets\05_abanderado.png").convert("RGB")


def font(path, size):
    return ImageFont.truetype(path, size)


def hide_float_bar(img, box):
    """Tapa la barra flotante actual copiando el suelo de justo encima."""
    x0, y0, x1, y1 = box
    patch = img.crop((x0, y0 - (y1 - y0), x1, y0))
    img.paste(patch, (x0, y0))


def ctext(d, cx, y, s, f, fill, shadow=INK):
    w = d.textlength(s, font=f)
    x = int(cx - w / 2)
    if shadow:
        d.text((x + 1, y + 1), s, font=f, fill=shadow)
    d.text((x, y), s, font=f, fill=fill)


def darken(img, k):
    return ImageEnhance.Brightness(img).enhance(k)


def boss_crop(img):
    return img.crop((104, 24, 150, 84))  # Abanderado en jefe_c_3s


# Barra común (A) para reutilizar en fases y victoria
def bar_a(img, hp=1.0, broken=None):
    d = ImageDraw.Draw(img)
    f = font(FB, 9)
    ctext(d, 128, 2, "EL ABANDERADO", f, CREAM)
    x0, x1, y0, y1 = 24, 232, 15, 21
    d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=BONE_DIM)
    d.rectangle((x0, y0, x1, y1), fill=BACK)
    fill_x = x0 + int((x1 - x0) * hp)
    d.rectangle((x0, y0, fill_x, y1), fill=RED)
    d.line((x0, y0, fill_x, y0), fill=(190, 70, 60))
    for t in (1 / 3, 2 / 3):
        nx = x0 + int((x1 - x0) * t)
        d.rectangle((nx, y0 - 2, nx, y1 + 2), fill=CREAM if broken != t else GOLD)
    if broken:
        nx = x0 + int((x1 - x0) * broken)
        for dx, dy in ((-3, -4), (3, -4), (-3, 9), (3, 9), (-5, 3), (5, 3)):
            d.line((nx, y0 + 3, nx + dx, y0 + 3 + dy - 3), fill=GOLD)
    return img


def scene(base=base_c):
    img = base.copy()
    hide_float_bar(img, (112, 14, 146, 22))
    return img


# ---------------- INTRO ----------------
def intro_a():
    img = darken(scene(), 0.35)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 255, 191), fill=(0, 0, 0))
    por = codex.crop((70, 28, 190, 172))
    img.paste(por, (68, 14))
    d.rectangle((60, 8, 196, 166), outline=BONE_DIM)
    ctext(d, 128, 172, "CÓDICE · V", font(FR, 9), BONE_DIM, None)
    ctext(d, 128, 192 + 62, "EL ABANDERADO", font(FB, 20), CREAM)
    ctext(d, 128, 192 + 88, "Capitán Íñigo Albar", font(FI, 11), BONE_DIM)
    ctext(d, 128, 192 + 170, "START: saltar", font(FR, 8), BONE_DIM, None)
    return img


def intro_b():
    img = scene()
    dark = darken(img, 0.22)
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((127 - 46, 54 - 40, 127 + 46, 54 + 40), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    img = Image.composite(img, dark, mask)
    d = ImageDraw.Draw(img)
    # cartela bajo el jefe
    d.rectangle((40, 104, 216, 134), fill=RED_DK, outline=RED)
    d.polygon([(40, 104), (30, 119), (40, 134)], fill=RED_DK)
    d.polygon([(216, 104), (226, 119), (216, 134)], fill=RED_DK)
    ctext(d, 128, 106, "EL ABANDERADO", font(FB, 14), CREAM)
    ctext(d, 128, 123, "Capitán Íñigo Albar", font(FI, 8), BONE_DIM, None)
    return img


def intro_c():
    img = darken(scene(), 0.45)
    big = boss_crop(base_c).resize((46 * 3, 60 * 3), Image.NEAREST)
    # fondo detrás del jefe ampliado para que se lea
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 255, 191), fill=(18, 14, 14))
    img.paste(big, (128 - 69, 6))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 255, 22), fill=(0, 0, 0))
    d.rectangle((0, 192 + 120, 255, 383), fill=(0, 0, 0))
    d.rectangle((0, 170, 255, 191), fill=(0, 0, 0))
    ctext(d, 128, 192 + 126, "EL ABANDERADO", font(FB, 18), CREAM)
    ctext(d, 128, 192 + 150, "«Mientras el asta siga en pie,", font(FI, 9), BONE_DIM, None)
    ctext(d, 128, 192 + 162, "nadie se retira.»", font(FI, 9), BONE_DIM, None)
    return img


# ---------------- BARRA ----------------
def barra_a():
    return bar_a(scene(), 0.72)


def barra_b():
    img = scene()
    d = ImageDraw.Draw(img)
    y = 383 - 22
    d.text((96, y), "EL ABANDERADO", font=font(FB, 8), fill=CREAM)
    x0, x1, y0, y1 = 96, 248, y + 12, y + 16
    d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=BONE_DIM)
    d.rectangle((x0, y0, x1, y1), fill=BACK)
    d.rectangle((x0, y0, x0 + int((x1 - x0) * 0.72), y1), fill=RED)
    for t in (1 / 3, 2 / 3):
        nx = x0 + int((x1 - x0) * t)
        d.line((nx, y0 - 2, nx, y1 + 2), fill=CREAM)
    return img


def barra_c():
    img = scene()
    d = ImageDraw.Draw(img)
    ctext(d, 128, 2, "EL ABANDERADO", font(FB, 9), CREAM)
    n = 21
    lit = int(n * 0.72)
    x = 26
    y = 19
    for i in range(n):
        if i in (7, 14):  # cruz que separa fases
            d.line((x + 2, y - 4, x + 2, y + 4), fill=GOLD)
            d.line((x - 1, y - 2, x + 5, y - 2), fill=GOLD)
            x += 10
        col = CREAM if i < lit else (55, 45, 40)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col, outline=INK)
        x += 9
    return img


# ---------------- FASE ----------------
def fase_a():
    img = scene()
    flash = Image.new("RGB", img.size, (235, 220, 185))
    img = Image.blend(img, flash, 0.45)
    shaken = Image.new("RGB", img.size, (0, 0, 0))
    shaken.paste(img, (3, -2))
    return bar_a(shaken, 0.66)


def fase_b():
    img = scene()
    d = ImageDraw.Draw(img)
    cx, cy = 127, 80
    for r, col in ((30, CREAM), (52, (190, 175, 140)), (74, (130, 118, 95))):
        d.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), outline=col, width=2)
    return bar_a(img, 0.66)


def fase_c():
    img = scene()
    d = ImageDraw.Draw(img)
    ctext(d, 128, 88, "II", font(FB, 26), RED, INK)
    return bar_a(img, 0.66, broken=2 / 3)


# ---------------- VICTORIA ----------------
def victoria_a():
    img = scene()
    img = ImageEnhance.Color(img).enhance(0.4)
    d = ImageDraw.Draw(img)
    # el jefe se hunde en un charco de cera: la mitad de arriba baja y los pies desaparecen en el charco
    boss = base_c.crop((104, 24, 150, 70))
    floor = img.crop((104, 90, 150, 150))
    img.paste(ImageEnhance.Color(floor).enhance(0.4), (104, 24))
    img.paste(ImageEnhance.Color(boss).enhance(0.6), (104, 38))
    d = ImageDraw.Draw(img)
    d.ellipse((98, 72, 156, 90), fill=(214, 196, 150), outline=(170, 150, 110))
    for x, y, h in ((114, 60, 12), (126, 56, 16), (138, 62, 10)):
        d.line((x, y, x, y + h), fill=(214, 196, 150), width=2)
    ctext(d, 128, 192 + 150, "(cámara lenta 1 s)", font(FI, 9), BONE_DIM)
    return img


def victoria_b():
    img = darken(scene(), 0.5)
    d = ImageDraw.Draw(img)
    d.rectangle((24, 100, 232, 148), fill=RED_DK, outline=GOLD)
    ctext(d, 128, 104, "EL ABANDERADO", font(FB, 12), BONE_DIM, None)
    ctext(d, 128, 120, "VENCIDO", font(FB, 20), CREAM)
    return img


def victoria_c():
    img = scene()
    img = ImageEnhance.Color(img).enhance(0.0)
    img = Image.blend(img, Image.new("RGB", img.size, (238, 230, 214)), 0.7)
    d = ImageDraw.Draw(img)
    ctext(d, 128, 70, "EL ABANDERADO", font(FB, 16), (60, 40, 35), None)
    d.line((40, 80, 216, 80), fill=RED, width=2)
    ctext(d, 128, 96, "Vencido en la nave", font(FI, 10), (90, 70, 60), None)
    return img


GROUPS = {
    "intro": (intro_a, intro_b, intro_c),
    "barra": (barra_a, barra_b, barra_c),
    "fase": (fase_a, fase_b, fase_c),
    "victoria": (victoria_a, victoria_b, victoria_c),
}

S = 2
GAP = 8
for name, fns in GROUPS.items():
    cols = [fn() for fn in fns]
    W = 3 * 256 * S + 2 * GAP
    H = 384 * S + 30
    sheet = Image.new("RGB", (W, H), (20, 18, 18))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cols):
        c = c.copy()
        cd = ImageDraw.Draw(c)
        cd.line((0, 191, 255, 191), fill=(0, 0, 0))
        cd.line((0, 192, 255, 192), fill=(0, 0, 0))
        x = i * (256 * S + GAP)
        sheet.paste(c.resize((256 * S, 384 * S), Image.NEAREST), (x, 30))
        d.text((x + 8, 4), "ABC"[i], font=font(FB, 20), fill=GOLD)
    sheet.save(f"{OUT}\\mock_{name}.png")
    print(name)
