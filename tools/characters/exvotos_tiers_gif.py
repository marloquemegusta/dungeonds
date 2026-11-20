"""GIF de revision: Exvoto + los tres tiers andando, uno al lado del otro.

Cada sprite usa la MISMA escala (4x NEAREST sobre su celda) y se alinea por su ancla de suelo
(dirGroundAnchors de su settings.json), asi la diferencia de altura es la del modelo, no la de la celda.

Uso: python tools/characters/exvotos_tiers_gif.py <raiz_worktree>
"""
import sys, os, json
from PIL import Image, ImageDraw

root = sys.argv[1] if len(sys.argv) > 1 else '.'
SPR = os.path.join(root, 'assets/sprites/characters')
OUT = os.path.join(root, 'walkthroughs/arpg-predemo/assets')
os.makedirs(OUT, exist_ok=True)

Z = 4
BG = (78, 74, 70)
LABEL_H = 22
GAP = 10
DIR = 0               # S: de frente al observador
CYCLES = 2
CELLS = [
    ('exvoto', 'Exvoto x1,00'),
    ('exvoto_bebe', 'Bebe x0,60'),
    ('exvoto_parroco', 'Parroco x1,15'),
    ('exvoto_monja', 'Monja x1,15'),
]


def load(name, label):
    d = os.path.join(SPR, name)
    s = json.load(open(os.path.join(d, 'settings.json'), encoding='utf-8'))
    sheet = Image.open(os.path.join(d, 'spritesheet.png')).convert('RGBA')
    fw = sheet.width // s['spritesheet']['columns']
    anchor = s['dirGroundAnchors'][DIR]
    return name, label, sheet, fw, anchor


loaded = [load(n, l) for n, l in CELLS]
cw = max(fw for _, _, _, fw, _ in loaded) * Z
anchor_px = max(a for _, _, _, _, a in loaded) * Z
GROUND = LABEL_H + GAP + anchor_px + 4 * Z          # linea de suelo comun
top = {n: GROUND - a * Z for n, _, _, _, a in loaded}
H = GROUND + (cw - anchor_px) + GAP
W = len(loaded) * cw + (len(loaded) + 1) * GAP


def build(f):
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for i, (name, label, sheet, fw, anchor) in enumerate(loaded):
        cell = sheet.crop((f * fw, DIR * fw, (f + 1) * fw, (DIR + 1) * fw))
        big = cell.resize((fw * Z, fw * Z), Image.NEAREST)
        x = GAP + i * (cw + GAP) + (cw - fw * Z) // 2
        y = top[name] + (anchor - anchor) * Z
        im.paste(big, (x, y), big)
        dr.text((GAP + i * (cw + GAP) + 4, 4), label, fill=(235, 235, 235))
        dr.line([(GAP + i * (cw + GAP), GROUND), (GAP + i * (cw + GAP) + cw, GROUND)], fill=(120, 114, 108))
    return im


frames = [build(f) for _ in range(CYCLES) for f in range(8)]
p = os.path.join(OUT, 'exvotos_tiers.gif')
frames[0].save(p, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=False, disposal=2)
print(p, len(frames), 'frames', frames[0].size, os.path.getsize(p) // 1024, 'KB')
frames[0].save(os.path.join(OUT, 'exvotos_tiers_frames.png'))
print('still', os.path.join(OUT, 'exvotos_tiers_frames.png'), frames[0].size)
