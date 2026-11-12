"""Hoja de contactos y GIF de las 8 pantallas del ciclo de la catedral (assets/catedral_ciclo).

Cada captura del runner son las dos pantallas (256x384). Para 'pantallas seguidas' se usa la
pantalla inferior (192 px) de cada una, que es la que centra la banda capturada.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets", "catedral_ciclo")
OUT_SHEET = os.path.join(HERE, "assets", "catedral_ciclo_contact.png")
OUT_GIF = os.path.join(HERE, "assets", "catedral_ciclo.gif")
NAMES = ["01_nave_inicio", "02_nave_inicio_alta", "03_barricada", "04_bancadas_a",
         "05_bancadas_b", "06_bancadas_c", "07_bancadas_d", "08_crucero"]


def bottom_screen(name):
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGB")
    w, h = im.size
    return im.crop((0, h - 192, w, h)) if h >= 192 else im


def main():
    screens = [bottom_screen(n) for n in NAMES]
    w, h = screens[0].size
    label_h = 14
    sheet = Image.new("RGB", (w, (h + label_h) * len(screens)), (12, 10, 9))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (name, im) in enumerate(zip(NAMES, screens)):
        y = i * (h + label_h)
        draw.text((3, y + 2), name, fill=(210, 200, 180), font=font)
        sheet.paste(im, (0, y + label_h))
    sheet.save(OUT_SHEET)
    sheet.resize((w * 2, sheet.height * 2), Image.NEAREST).save(
        OUT_SHEET.replace(".png", "_2x.png"))
    screens[0].save(OUT_GIF, save_all=True, append_images=screens[1:], duration=420, loop=0)
    print(OUT_SHEET, sheet.size)
    print(OUT_GIF, (w, h))


if __name__ == "__main__":
    main()
