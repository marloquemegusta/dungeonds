"""Hoja de contacto del Campanero: una fila por clip, 8 fotogramas, para una direccion (0..7). 3x NEAREST.
Uso: python tools/characters/campanero_sheet.py <dir> <salida.png>"""
import sys
from PIL import Image
D = int(sys.argv[1]); OUT = sys.argv[2]
CLIPS = ['campanero', 'campanero_walk', 'campanero_toque', 'campanero_tanido', 'campanero_death']
W = 60; Z = 3
sheet = Image.new('RGBA', (W * Z * 8, W * Z * len(CLIPS)), (70, 70, 80, 255))
for r, c in enumerate(CLIPS):
    im = Image.open('assets/sprites/characters/%s/spritesheet.png' % c).convert('RGBA')
    for f in range(8):
        t = im.crop((f * W, D * W, (f + 1) * W, (D + 1) * W)).resize((W * Z, W * Z), Image.NEAREST)
        sheet.alpha_composite(t, (f * W * Z, r * W * Z))
sheet.save(OUT)
