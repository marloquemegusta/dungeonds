"""Tamano de registro de streaming por fotograma (pixeles + runs, como tools/generate_player_sprites_c.py; sin sombra) y comprobacion de bbox (cortes de celda).
Uso: python tools/characters/arana_puente_stats.py <hoja.png> <celda>"""
import sys
from PIL import Image
png, c = sys.argv[1], int(sys.argv[2])
im = Image.open(png).convert("RGBA"); worst = (0, None); cut = []
for d in range(8):
    for f in range(8):
        cell = im.crop((f * c, d * c, (f + 1) * c, (d + 1) * c)); a = cell.getchannel("A").point(lambda v: 255 if v >= 77 else 0)
        bb = a.getbbox()
        if not bb: continue
        x0, y0, x1, y1 = bb; bw, bh = x1 - x0, y1 - y0
        pix = bh * (bw + (bw & 1)) * 2
        n = 0
        for y in range(y0, y1):
            x = x0; r = 0
            while x < x1:
                if a.getpixel((x, y)): 
                    while x < x1 and a.getpixel((x, y)): x += 1
                    r += 1
                else: x += 1
            n += r
        runs = (bh + 1 + n + ((bh + 1 + n) & 1)) * 2
        rec = pix + runs
        if rec > worst[0]: worst = (rec, (d, f, bw, bh))
        if x0 == 0 or y0 == 0 or x1 == c or y1 == c: cut.append((d, f, bb))
print(png, "mayor registro pix+runs", worst, "| tocan borde de celda:", cut)
