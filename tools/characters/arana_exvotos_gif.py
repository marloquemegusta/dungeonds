"""Evidencia de arana_exvotos: GIF por personaje (de pie -> transicion -> andar arana -> transicion inversa -> de pie) sobre el suelo
de la catedral (tesela recortada de walkthroughs/arpg-exvoto-ramas/assets/arana/arana_ia.gif) junto a la Super Monja arana, 4x NEAREST,
60 ms/fotograma; y hoja de contacto de la transicion en 8 direcciones.  Uso: python tools/characters/arana_exvotos_gif.py"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ST = ROOT / "assets/staging/arana_exvotos"
OUT = ROOT / "walkthroughs/arpg-exvoto-ramas/assets/arana_exvotos"
OUT.mkdir(parents=True, exist_ok=True)
Z = 4
ia = Image.open(ROOT / "walkthroughs/arpg-exvoto-ramas/assets/arana/arana_ia.gif"); ia.seek(0)
FLOOR = ia.convert("RGB").crop((575, 20, 845, 300))
FLOOR = FLOOR.resize((round(FLOOR.width * Z / 3.594), round(FLOOR.height * Z / 3.594)), Image.NEAREST)
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
STEP = {"S": (0, 1), "SE": (2, 1), "E": (2, 0), "NE": (2, -1), "N": (0, -1), "NW": (-2, -1), "W": (-2, 0), "SW": (-2, 1)}


class Sheet:
    def __init__(self, d, c):
        self.im = Image.open(d / "spritesheet.png").convert("RGBA"); self.c = c
        self.anchor = json.load(open(d / "settings.json"))["anchor"]

    def cell(self, row, f):
        return self.im.crop((f * self.c, row * self.c, (f + 1) * self.c, (row + 1) * self.c))


def put(canvas, sh, row, f, gx, gy):
    cell = sh.cell(row, f).resize((sh.c * Z, sh.c * Z), Image.NEAREST)
    canvas.alpha_composite(cell, (int(gx - sh.anchor[0] * Z), int(gy - sh.anchor[1] * Z)))


def floor_canvas(w, h):
    bg = Image.new("RGBA", (w, h))
    for y in range(0, h, FLOOR.height):
        for x in range(0, w, FLOOR.width):
            bg.paste(FLOOR.convert("RGBA"), (x, y))
    return bg


sm = Sheet(ROOT / "assets/sprites/characters/exvoto_super_monja", 64)
for pers, c in (("exvoto", 40), ("monaguillo", 48)):
    tr = Sheet(ST / pers / "trans" / pers, c); wk = Sheet(ST / pers / "walk" / pers, c)
    sheet = Image.new("RGBA", (8 * c * Z, 8 * c * Z), (128, 128, 128, 255))
    for d in range(8):
        for f in range(8):
            sheet.alpha_composite(tr.cell(d, f).resize((c * Z, c * Z), Image.NEAREST), (f * c * Z, d * c * Z))
    sheet.convert("RGB").save(OUT / f"{pers}_transicion_hoja_8dir.png")
    for dn in ("S", "SE"):
        d = DIRS.index(dn); sx, sy = STEP[dn]
        # secuencia: (hoja, fila, fotograma, avance)
        seq = [("tr", 0)] * 6 + [("tr", f) for f in range(8)] + [("wk", f % 8) for f in range(16)] + [("tr", f) for f in range(7, -1, -1)] + [("tr", 0)] * 6
        W, H = 760, 520
        frames = []
        pos = 0
        for i, (k, f) in enumerate(seq):
            if k == "wk":
                pos += 1 if f < 6 else 0   # arrancadas: avanza en la racha, quieto en la pausa
            can = floor_canvas(W, H)
            g1 = (230 - sx * 6 * Z * 0 + sx * pos * Z, 300 + sy * pos * Z)
            put(can, tr if k == "tr" else wk, d, f, *g1)
            # Super Monja arana a su escala, en sincronia, siempre andando
            wf = (i % 8)
            put(can, sm, d, wf, 560 + sx * (i % 16) * Z * 0.5, 300 + sy * (i % 16) * Z * 0.5)
            ImageDraw.Draw(can).text((10, 8), f"{pers} ({dn})   |   Super Monja arana", fill=(255, 255, 255, 255))
            frames.append(can.convert("RGB"))
        frames[0].save(OUT / f"{pers}_arana_{dn}.gif", save_all=True, append_images=frames[1:], duration=60, loop=0)
print("ok")
