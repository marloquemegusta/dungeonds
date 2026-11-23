"""Evidencia de arana_puente: hoja de contacto 8x8 por variante y GIF (de pie -> pino puente -> andar arana -> puente al reves -> de pie) sobre el suelo de la
catedral, 4x NEAREST, 60 ms/fotograma, con la transicion actual (la que rueda) al lado. Cada clip se coloca con su propia ancla de suelo (settings.json).
Uso: python tools/characters/arana_puente_gif.py [exvoto|monaguillo ...]"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / "assets/staging/arana_exvotos_puente"; OLD = ROOT / "assets/staging/arana_exvotos"
OUT = ROOT / "walkthroughs/arpg-exvoto-ramas/assets/arana_exvotos_puente"; OUT.mkdir(parents=True, exist_ok=True)
Z = 4
ia = Image.open(ROOT / "walkthroughs/arpg-exvoto-ramas/assets/arana/arana_ia.gif"); ia.seek(0)
FLOOR = ia.convert("RGB").crop((575, 20, 845, 300))
FLOOR = FLOOR.resize((round(FLOOR.width * Z / 3.594), round(FLOOR.height * Z / 3.594)), Image.NEAREST)
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
STEP = {"S": (0, 1), "SE": (2, 1)}


class Sheet:
    def __init__(self, d, c):
        self.im = Image.open(d / "spritesheet.png").convert("RGBA"); self.c = c
        self.anchor = json.load(open(d / "settings.json"))["anchor"]

    def put(self, canvas, row, f, gx, gy):
        cell = self.im.crop((f * self.c, row * self.c, (f + 1) * self.c, (row + 1) * self.c)).resize((self.c * Z, self.c * Z), Image.NEAREST)
        canvas.alpha_composite(cell, (int(gx - self.anchor[0] * Z), int(gy - self.anchor[1] * Z)))


def floor_canvas(w, h):
    bg = Image.new("RGBA", (w, h))
    for y in range(0, h, FLOOR.height):
        for x in range(0, w, FLOOR.width):
            bg.paste(FLOOR.convert("RGBA"), (x, y))
    return bg


for pers, c in (("exvoto", 40), ("monaguillo", 48)):
    if len(sys.argv) > 1 and pers not in sys.argv[1:]:
        continue
    wk = Sheet(OLD / pers / "walk" / pers, c); old = Sheet(OLD / pers / "trans" / pers, c)
    for var in ("A", "B"):
        tr = Sheet(NEW / pers / var / "trans" / pers, c)
        sheet = Image.new("RGBA", (8 * c * Z, 8 * c * Z), (128, 128, 128, 255))
        dr = ImageDraw.Draw(sheet)
        for d in range(8):
            for f in range(8):
                sheet.alpha_composite(tr.im.crop((f * c, d * c, (f + 1) * c, (d + 1) * c)).resize((c * Z, c * Z), Image.NEAREST), (f * c * Z, d * c * Z))
                dr.rectangle((f * c * Z, d * c * Z, (f + 1) * c * Z - 1, (d + 1) * c * Z - 1), outline=(90, 90, 90, 255))
        sheet.convert("RGB").save(OUT / f"{pers}_{var}_hoja_8dir.png")
        for dn in ("S", "SE"):
            d = DIRS.index(dn); sx, sy = STEP[dn]
            seq = [("tr", 0)] * 6 + [("tr", f) for f in range(8)] + [("wk", f % 8) for f in range(16)] + [("tr", f) for f in range(7, -1, -1)] + [("tr", 0)] * 6
            W, H = 380, 300; frames = []; pos = 0
            for n_, (k, f) in enumerate(seq):
                if k == "wk":
                    pos += 1 if f < 6 else 0
                can = floor_canvas(W * 2, H)
                for ox, sh_tr, label in ((0, old, "actual (rueda)"), (W, tr, f"nueva {var}")):
                    sub = Image.new("RGBA", (W, H)); sub.alpha_composite(can.crop((ox, 0, ox + W, H)))
                    (sh_tr if k == "tr" else wk).put(sub, d, f, 160 + sx * pos * Z, 170 + sy * pos * Z)
                    ImageDraw.Draw(sub).text((8, 8), f"{pers} {dn}  |  {label}", fill=(255, 255, 255, 255))
                    can.alpha_composite(sub, (ox, 0))
                ImageDraw.Draw(can).line((W, 0, W, H), fill=(255, 255, 255, 255))
                can.putpixel((W * 2 - 1, H - 1), (255 * (n_ % 2),) * 3 + (255,))   # evita que el GIF funda fotogramas repetidos (duracion > 65 ms)
                frames.append(can.convert("RGB"))
            frames[0].save(OUT / f"{pers}_{var}_{dn}.gif", save_all=True, append_images=frames[1:], duration=60, loop=0)
            print(OUT / f"{pers}_{var}_{dn}.gif")
