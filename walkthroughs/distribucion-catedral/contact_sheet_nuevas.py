"""Hoja de contactos (1x + 4x NEAREST) de las piezas nuevas junto al marine (escala 31 px)."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RENDER = os.path.join(ROOT, "assets/environment/cathedral/props/render")
OUT = os.path.join(ROOT, "walkthroughs/distribucion-catedral/assets/piezas_nuevas.png")
BG = (0x2a, 0x26, 0x22, 255)

PIECES = ["banco_entero", "sacos", "columna_entera", "vela", "columna", "banco_volcado"]


def main():
    sheet = Image.open(os.path.join(ROOT, "assets/sprites/characters/marine/spritesheet.png")).convert("RGBA")
    marine = sheet.crop((0, 0, 40, 40))

    items = [("marine (31px)", marine, 20, 32)]
    for n in PIECES:
        im = Image.open(os.path.join(RENDER, n, "color.png")).convert("RGBA")
        items.append((n, im, im.width // 2, im.height))

    pad, labh = 10, 22
    maxabove = max(ay for _, _, _, ay in items)
    f = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    cols = []
    for name, im, ax, ay in items:
        tw = max(probe.textlength(name, font=f), probe.textlength("%dx%d" % im.size, font=f))
        cols.append((name, im, ax, ay, max(im.width, int(tw) + 4)))
    W = pad + sum(c[4] + pad for c in cols)
    H1 = labh + maxabove + 14
    x, base = pad, labh + maxabove
    s1 = Image.new("RGBA", (W, H1), BG)
    d = ImageDraw.Draw(s1)
    for name, im, ax, ay, colw in cols:
        s1.alpha_composite(im, (x + (colw - im.width) // 2, base - ay))
        d.text((x, 2), name, fill=(230, 220, 200, 255), font=f)
        d.text((x, base + 2), "%dx%d" % im.size, fill=(160, 150, 135, 255), font=f)
        x += colw + pad
    d.line([(0, base), (W, base)], fill=(90, 80, 70, 255))

    s4 = s1.resize((W * 4, H1 * 4), Image.NEAREST)
    d4 = ImageDraw.Draw(s4)
    for gx in range(0, s4.width, 32):
        d4.line([(gx, 0), (gx, s4.height)], fill=(255, 255, 255, 14))
    for gy in range(0, s4.height, 32):
        d4.line([(0, gy), (s4.width, gy)], fill=(255, 255, 255, 14))
    out = Image.new("RGBA", (s4.width, H1 + 8 + s4.height), BG)
    out.alpha_composite(s1, (0, 0))
    out.alpha_composite(s4, (0, H1 + 8))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.convert("RGB").save(OUT)
    print(OUT, out.size)


if __name__ == "__main__":
    main()
