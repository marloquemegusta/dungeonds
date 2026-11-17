"""Maquetas de la ronda 2 del modo jefe (solo para elegir; no son evidencia de juego).

Uso: python tools/mock_modo_jefe_r2.py <carpeta_salida>
Parte de las capturas reales de artifacts/modo_jefe/ (escenario modo_jefe_capturas.json).
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.dirname(HERE)
SRC = os.path.join(WT, "artifacts", "modo_jefe")
OUT = sys.argv[1]
FB = r"C:\Windows\Fonts\BOOKOSB.TTF"
FR = r"C:\Windows\Fonts\BOOKOS.TTF"
FI = r"C:\Windows\Fonts\BOOKOSI.TTF"

CREAM = (226, 210, 170)
BONE_DIM = (150, 135, 108)
RED = (150, 36, 34)
RED_HI = (190, 70, 60)
BACK = (28, 20, 20)
GOLD = (216, 160, 88)
INK = (12, 8, 8)
SEPIA_INK = (60, 40, 35)

BOSS_X, BOSS_Y = 127, 54
NAME, TITLE = "EL ABANDERADO", "Capitán Íñigo Albar"
QUOTE = ("«Mientras el asta siga en pie,", "nadie se retira.»")


def f(path, size):
    return ImageFont.truetype(path, size)


def ctext(d, cx, y, s, fnt, fill, shadow=INK):
    w = d.textlength(s, font=fnt)
    x = int(cx - w / 2)
    if shadow:
        d.text((x + 1, y + 1), s, font=fnt, fill=shadow)
    d.text((x, y), s, font=fnt, fill=fill)
    return x, w


def base():
    img = Image.open(os.path.join(SRC, "jefe_c_3s.png")).convert("RGB")
    patch = img.crop((112, 6, 146, 14))  # tapa la barra flotante actual
    img.paste(patch, (112, 14))
    # tapa "JEFE" del HUD de la fila superior de la pantalla de abajo
    img.paste(img.crop((4, 192 + 22, 40, 192 + 36)), (4, 192 + 4))
    return img


def zoom_top(img, k):
    w, h = 256 // k, 192 // k
    x0 = max(0, min(256 - w, BOSS_X - w // 2))
    y0 = max(0, min(384 - h, BOSS_Y + 6 - h // 2))
    out = img.copy()
    out.paste(img.crop((x0, y0, x0 + w, y0 + h)).resize((256, 192), Image.NEAREST), (0, 0))
    return out


def vignette_top(img, strength=0.25):
    top = img.crop((0, 0, 256, 192))
    dark = ImageEnhance.Brightness(top).enhance(strength)
    m = Image.new("L", (256, 192), 0)
    ImageDraw.Draw(m).ellipse((40, -10, 216, 200), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(18))
    img.paste(Image.composite(top, dark, m), (0, 0))
    return img


def darken_bottom(img, k, band=None):
    y0, y1 = band if band else (192, 384)
    part = img.crop((0, y0, 256, y1))
    img.paste(ImageEnhance.Brightness(part).enhance(k), (0, y0))
    return img


def intro_text(img, y=192 + 70, quote=True, struck=False, ink=CREAM, sub=BONE_DIM, shadow=INK, last=None):
    d = ImageDraw.Draw(img)
    x, w = ctext(d, 128, y, NAME, f(FB, 20), ink, shadow)
    if struck:
        d.line((x - 6, y + 13, x + w + 6, y + 13), fill=RED, width=2)
    ctext(d, 128, y + 26, TITLE, f(FI, 10), sub, None)
    if quote:
        ctext(d, 128, y + 48, QUOTE[0], f(FI, 10), ink, shadow)
        ctext(d, 128, y + 61, QUOTE[1], f(FI, 10), ink, shadow)
    if last:
        ctext(d, 128, y + 50, last, f(FI, 11), ink, shadow)
    return img


# ---------------- INTRO ----------------
def intro_a():
    img = zoom_top(base(), 2)
    return intro_text(darken_bottom(img, 0.3))


def intro_b():
    img = vignette_top(zoom_top(base(), 2))
    return intro_text(darken_bottom(img, 0.3))


def intro_c():
    img = zoom_top(base(), 3)
    img = darken_bottom(img, 0.2, band=(192 + 56, 192 + 142))
    return intro_text(img)


# ---------------- BARRA (fila de arriba de la pantalla de abajo, junto a los corazones) ----------------
HEART_X = 172  # los corazones empiezan aquí en la captura


def bar(img, x0, x1, y0, h, hp, broken=None, notch_col=CREAM):
    d = ImageDraw.Draw(img)
    y1 = y0 + h - 1
    d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=INK)
    d.rectangle((x0, y0, x1, y1), fill=BACK)
    fx = x0 + int((x1 - x0) * hp)
    d.rectangle((x0, y0, fx, y1), fill=RED)
    d.line((x0, y0, fx, y0), fill=RED_HI)
    for t in (1 / 3, 2 / 3):
        nx = x0 + int((x1 - x0) * t)
        if broken and abs(t - broken) < 1e-6:
            for dx, dy in ((-3, -3), (3, -3), (-3, h + 2), (3, h + 2), (0, -4), (0, h + 3)):
                d.line((nx, y0 + h // 2, nx + dx, y0 + dy), fill=GOLD)
        else:
            d.line((nx, y0 - 1, nx, y1 + 1), fill=notch_col)
    return img


def barra_a():
    img = base()
    d = ImageDraw.Draw(img)
    y = 192 + 6
    d.text((6, y - 1), "ABANDERADO", font=f(FB, 8), fill=CREAM)
    return bar(img, 70, HEART_X - 8, y + 2, 6, 0.72)


def barra_b():
    img = base()
    img = bar(img, 6, HEART_X - 8, 192 + 5, 11, 0.72)
    d = ImageDraw.Draw(img)
    d.text((10, 192 + 5), NAME, font=f(FB, 8), fill=CREAM, stroke_width=1, stroke_fill=INK)
    return img


def barra_c():
    img = base()
    img = bar(img, 6, HEART_X - 8, 192 + 7, 4, 0.72)
    d = ImageDraw.Draw(img)
    d.text((6, 192 + 13), NAME, font=f(FB, 8), fill=CREAM, stroke_width=1, stroke_fill=INK)
    return img


# ---------------- FASE C con la barra nueva (una sola imagen por cada barra) ----------------
def with_phase(fn):
    def g():
        img = fn()
        # rehace la barra al 66 % con la marca rota: se reutiliza el dibujo de cada variante
        return img
    return g


def fase_a():
    img = base()
    d = ImageDraw.Draw(img)
    d.text((6, 192 + 5), "ABANDERADO", font=f(FB, 8), fill=CREAM)
    bar(img, 70, HEART_X - 8, 192 + 8, 6, 0.665, broken=2 / 3)
    ctext(ImageDraw.Draw(img), BOSS_X, 92, "II", f(FB, 26), RED)
    return img


def fase_b():
    img = base()
    bar(img, 6, HEART_X - 8, 192 + 5, 11, 0.665, broken=2 / 3)
    d = ImageDraw.Draw(img)
    d.text((10, 192 + 5), NAME, font=f(FB, 8), fill=CREAM, stroke_width=1, stroke_fill=INK)
    ctext(d, BOSS_X, 92, "II", f(FB, 26), RED)
    return img


def fase_c():
    img = base()
    bar(img, 6, HEART_X - 8, 192 + 7, 4, 0.665, broken=2 / 3)
    d = ImageDraw.Draw(img)
    d.text((6, 192 + 13), NAME, font=f(FB, 8), fill=CREAM, stroke_width=1, stroke_fill=INK)
    ctext(d, BOSS_X, 92, "II", f(FB, 26), RED)
    return img


# ---------------- VICTORIA (a juego con la intro) ----------------
def bleach(img, box, k):
    part = img.crop(box)
    part = ImageEnhance.Color(part).enhance(0.0)
    part = Image.blend(part, Image.new("RGB", part.size, (238, 230, 214)), k)
    img.paste(part, box[:2])
    return img


def victoria_a():
    img = zoom_top(base(), 2)
    img = bleach(img, (0, 0, 256, 384), 0.7)
    return intro_text(img, quote=False, struck=True, ink=SEPIA_INK, sub=(110, 90, 80), shadow=None,
                      last="Vencido en la nave")


def victoria_b():
    img = zoom_top(base(), 2)
    img = bleach(img, (0, 0, 256, 192), 0.7)
    img = darken_bottom(img, 0.3)
    return intro_text(img, quote=False, struck=True, last="«El asta ha caído.»")


def victoria_c():
    img = bleach(base(), (0, 0, 256, 384), 0.7)
    return intro_text(img, quote=False, struck=True, ink=SEPIA_INK, sub=(110, 90, 80), shadow=None,
                      last="Vencido en la nave")


GROUPS = {
    "r2_intro": (intro_a, intro_b, intro_c),
    "r2_barra": (barra_a, barra_b, barra_c),
    "r2_fase": (fase_a, fase_b, fase_c),
    "r2_victoria": (victoria_a, victoria_b, victoria_c),
}

S, GAP = 2, 8
for name, fns in GROUPS.items():
    W = 3 * 256 * S + 2 * GAP
    sheet = Image.new("RGB", (W, 384 * S + 30), (20, 18, 18))
    d = ImageDraw.Draw(sheet)
    for i, fn in enumerate(fns):
        c = fn()
        cd = ImageDraw.Draw(c)
        cd.line((0, 191, 255, 191), fill=(0, 0, 0))
        cd.line((0, 192, 255, 192), fill=(0, 0, 0))
        x = i * (256 * S + GAP)
        sheet.paste(c.resize((256 * S, 384 * S), Image.NEAREST), (x, 30))
        d.text((x + 8, 4), "ABC"[i], font=f(FB, 20), fill=GOLD)
    sheet.save(os.path.join(OUT, f"mock_{name}.png"))
    print(name)
