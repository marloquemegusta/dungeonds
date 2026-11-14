"""GIF de aprobacion del Monaguillo (1 unidad): andar en las 8 direcciones.
4x NEAREST, 60 ms por frame (16,7 fps). Uso: python tools/characters/monaguillo_gif.py <raiz_worktree>"""
import sys, os
from PIL import Image, ImageDraw
root = sys.argv[1] if len(sys.argv) > 1 else '.'
SPR = os.path.join(root, 'assets/sprites/characters')
OUT = os.path.join(root, 'walkthroughs/abanderado-jefe/assets')
os.makedirs(OUT, exist_ok=True)
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
Z = 4; BG = (78, 74, 70); MS = 60


def cell(sheet, d, f):
    cs = sheet.width // 8
    return sheet.crop((f * cs, d * cs, (f + 1) * cs, (d + 1) * cs))


def frame(img, label):
    big = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
    bg = Image.new('RGBA', big.size, BG + (255,))
    bg.alpha_composite(big)
    ImageDraw.Draw(bg).text((6, 4), label, fill=(235, 235, 235, 255))
    return bg.convert('RGB')


walk = Image.open(os.path.join(SPR, 'monaguillo/spritesheet.png')).convert('RGBA')
frames = []
for d in range(8):
    for cyc in range(2):
        for f in range(8):
            frames.append(frame(cell(walk, d, f), 'monaguillo  %s' % DIRS[d]))
p = os.path.join(OUT, 'monaguillo_8dir.gif')
frames[0].save(p, save_all=True, append_images=frames[1:], duration=MS, loop=0, optimize=False, disposal=2)
print(p, len(frames), 'frames', frames[0].size, os.path.getsize(p) // 1024, 'KB')
big = walk.resize((walk.width * 2, walk.height * 2), Image.NEAREST)
bg = Image.new('RGBA', big.size, BG + (255,)); bg.alpha_composite(big)
bg.convert('RGB').save(os.path.join(OUT, 'monaguillo_hoja_andar.png'))
