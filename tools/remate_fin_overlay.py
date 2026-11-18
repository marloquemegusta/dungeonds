"""Superpone, por direccion, el ultimo fotograma del remate (lab_out/<kind>/frames/<dir>/11.png)
y la silueta del heroe normal (corazon, frame 0) colocada donde la ROM la hace reaparecer
(ancla de la celda = pies del heroe).  Uso: remate_fin_overlay.py <salida.png> [kind ...]
Lee las anclas de source/remate_sprites.c (lo que realmente usa la ROM)."""
import os, re, sys
from PIL import Image, ImageDraw
WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', 'lab_out')
HERO = os.path.join(WT, 'assets', 'sprites', 'characters', 'corazon', 'frames')
DIRS = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']
HERO_ANCHOR = (20, 33)


def dir_info():
    txt = open(os.path.join(WT, 'source', 'remate_sprites.c')).read()
    out = {}
    for name, body in re.findall(r'\{ /\* (\w+) \*/\n(.*?)\n    \},', txt, re.S):
        out[name] = [tuple(map(int, m)) for m in re.findall(r'\{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+) \}', body)]
    return out


def main():
    outp = sys.argv[1]
    kinds = sys.argv[2:] or ['exvoto', 'cireneo']
    info = dir_info()
    S = 3
    cells = []
    for k in kinds:
        for d in range(8):
            fr = Image.open(os.path.join(LAB, k, 'frames', DIRS[d], '11.png')).convert('RGBA')
            ax, ay = info[k][d][0], info[k][d][1]
            base = Image.new('RGBA', fr.size, (0x3d, 0x3b, 0x38, 255))
            base.alpha_composite(fr)
            hero = Image.open(os.path.join(HERO, DIRS[d], '0.png')).convert('RGBA')
            hs = Image.new('RGBA', fr.size, (0, 0, 0, 0))
            hs.paste(hero, (ax - HERO_ANCHOR[0], ay - HERO_ANCHOR[1]))
            # silueta del heroe normal: contorno cian sobre el ultimo fotograma
            a = hs.split()[3].point(lambda v: 255 if v >= 96 else 0)
            from PIL import ImageFilter
            edge = Image.composite(Image.new('RGBA', fr.size, (0, 255, 255, 255)), Image.new('RGBA', fr.size, (0, 0, 0, 0)),
                                   ImageChops_sub(a.filter(ImageFilter.MaxFilter(3)), a))
            base.alpha_composite(edge)
            big = base.resize((fr.size[0] * S, fr.size[1] * S), Image.NEAREST)
            dr = ImageDraw.Draw(big)
            cx, cy = ax * S + S // 2, ay * S + S // 2
            dr.line((cx - 6, cy, cx + 6, cy), fill=(255, 0, 255, 255)); dr.line((cx, cy - 6, cx, cy + 6), fill=(255, 0, 255, 255))
            dr.text((3, 3), '%s %s' % (k, DIRS[d]), fill=(255, 255, 255, 255))
            cells.append(big)
    w = max(c.size[0] for c in cells)
    h = max(c.size[1] for c in cells)
    cols = 4
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * w, rows * h), (0x3d, 0x3b, 0x38, 255))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % cols) * w, (i // cols) * h))
    sheet.save(outp)
    print(outp, sheet.size)


def ImageChops_sub(a, b):
    from PIL import ImageChops
    return ImageChops.subtract(a, b)


main()
