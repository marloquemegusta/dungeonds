"""Monta la hoja de contacto (4x NEAREST) y el GIF (>=15 fps) del prototipo del remate a partir de los f??.png / s??.png
que escribe proto_remate_exvoto.py.

Uso: python tools/characters/proto_remate_sheet.py <carpeta_render> <carpeta_salida> <nombre> [n_columnas]
"""
import sys, os, glob
from PIL import Image, ImageDraw

src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 6
os.makedirs(dst, exist_ok=True)
CELL = 64
FLOOR = (74, 68, 72, 255)
fs = sorted(glob.glob(os.path.join(src, 'f??.png')))
frames = []
for f in fs:
    ch = Image.open(f).convert('RGBA').resize((CELL, CELL), Image.BOX)
    r, g, b, a_ = ch.split()
    gain = lambda v: min(255, int(v * 1.4))      # los sprites reales llevan su propia iluminacion: aqui solo se aclara
    ch = Image.merge('RGBA', (r.point(gain), g.point(gain), b.point(gain), a_))
    sh = Image.open(f.replace('f', 's', 1) if False else os.path.join(src, 's' + os.path.basename(f)[1:])).convert('RGBA')
    sh = sh.resize((CELL, CELL), Image.BOX)
    a = sh.getchannel('A').point(lambda v: int(v * 0.5))
    shadow = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    shadow.putalpha(a)
    # el sprite final es RGBA transparente: se guarda tambien sin suelo
    fr = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    fr.alpha_composite(shadow)
    fr.alpha_composite(ch)
    frames.append(fr)

Z = 4
# hoja de contacto
rows = (len(frames) + cols - 1) // cols
sheet = Image.new('RGBA', (cols * CELL * Z, rows * CELL * Z), FLOOR)
d = ImageDraw.Draw(sheet)
for i, fr in enumerate(frames):
    x, y = (i % cols) * CELL * Z, (i // cols) * CELL * Z
    big = fr.resize((CELL * Z, CELL * Z), Image.NEAREST)
    sheet.alpha_composite(big, (x, y))
    d.rectangle([x, y, x + CELL * Z - 1, y + CELL * Z - 1], outline=(30, 28, 32, 255))
    d.text((x + 4, y + 3), str(i), fill=(235, 235, 235, 255))
sheet.convert('RGB').save(os.path.join(dst, name + '_hoja.png'))

# GIF: 4x NEAREST, 60 ms por fotograma (16,7 fps); pausa en el golpe y al final
gif = []
durs = []
for i, fr in enumerate(frames):
    bg = Image.new('RGBA', (CELL * Z, CELL * Z), FLOOR)
    bg.alpha_composite(fr.resize((CELL * Z, CELL * Z), Image.NEAREST))
    gif.append(bg.convert('P', palette=Image.ADAPTIVE, colors=64))
    durs.append(60)
durs[-1] = 600
gif[0].save(os.path.join(dst, name + '.gif'), save_all=True, append_images=gif[1:], duration=durs, loop=0, disposal=2)
# tira sin suelo (lo que iria a la ROM, 1x) para medir
strip = Image.new('RGBA', (CELL * len(frames), CELL), (0, 0, 0, 0))
for i, fr in enumerate(frames):
    strip.paste(fr, (i * CELL, 0))
strip.save(os.path.join(dst, name + '_tira_1x.png'))
print('OK', len(frames))
