"""Mide la deriva vertical de los pies del heroe entre fotogramas del remate, tal como los coloca la ROM
(la celda se dibuja en un origen fijo), y dibuja tiras de control.
  python tools/remate_feet_check.py <antes|despues> [carpeta_lab_out]
Pies = centroide de los vertices del heroe a menos de 3 cm de su punto mas bajo, en cada GLB (escena de Blender).
Suelo del lab: 'antes' apoya cada fotograma en su punto mas bajo (y = -minY); 'despues' usa el suelo comun (y = 0).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_minmax as g

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS = os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets')
HERO = 'f25681c0'
PPM = {'exvoto': 38.0, 'cireneo': 56.4}
K = math.cos(math.radians(30))
DIRN = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']


def feet(kind, f):
    p = os.path.join(AS, 'glb', kind, 'f%02d.glb' % f)
    h = g.world_points(p, HERO)
    a = g.world_points(p)
    m = h[:, 1].min()
    c = h[h[:, 1] < m + 0.03]
    return c[:, 0].mean(), c[:, 2].mean(), m, a[:, 1].min()


def screen(kind, st, d, f, fx, fz, yh, ymin, lab):
    ang = d * math.pi / 4
    ux, uy = -math.sin(ang), math.cos(ang)
    rx, ry = -uy, ux
    dist, lat = -fx, -fz
    ppm = PPM[kind]
    edx = (dist * ux + lat * rx) * ppm
    edy = (dist * uy + lat * ry) * ppm * 0.5
    base = ymin if st == 'antes' else 0.0
    return lab[0] - edx, lab[1] - edy - (yh - base) * ppm * K


def main():
    st = sys.argv[1]
    out = {}
    tiles = {}
    for kind in PPM:
        lo = os.path.join(AS, 'lab_out', kind)
        s = json.load(open(os.path.join(lo, 'settings.json')))
        lab = s['anchor']
        F = [feet(kind, f) for f in range(12)]
        print('==', kind, st)
        for d in range(8):
            ys = []
            for f in range(12):
                fx, fz, yh, ymin = F[f]
                ys.append(screen(kind, st, d, f, fx, fz, yh, ymin, lab))
            ys = np.array(ys)
            grip = ys[2:12]
            print('dir %d  grip y: %s  drift(max-min)=%.1f px  x drift=%.1f' % (
                d, ' '.join('%.1f' % v for v in grip[:, 1]), grip[:, 1].max() - grip[:, 1].min(), grip[:, 0].max() - grip[:, 0].min()))
            out[(kind, d)] = ys
    # tiras: filas = direcciones, columnas = fotogramas 2..11 (agarre); recorte de 72x64 px alrededor de los pies
    # del fotograma 3 (fijo para toda la fila, como la ROM), a 3x. Linea roja = suelo de referencia (pies del fotograma 3),
    # circulo cian = pies medidos en cada fotograma.
    sc, W, H = 3, 72, 64
    for kind in PPM:
        lo = os.path.join(AS, 'lab_out', kind)
        cols = list(range(2, 12))
        img = Image.new('RGBA', (len(cols) * W * sc, 8 * H * sc), (60, 60, 70, 255))
        dr = ImageDraw.Draw(img)
        for d in range(8):
            ys = out[(kind, d)]
            rx, ry = ys[3]
            x0, y0 = int(round(rx)) - W // 2, int(round(ry)) - 48
            for ci, f in enumerate(cols):
                im = Image.open(os.path.join(lo, 'frames', DIRN[d], '%d.png' % f)).convert('RGBA')
                big = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                big.paste(im.crop((x0, y0, x0 + W, y0 + H)), (0, 0))
                big = big.resize((W * sc, H * sc), Image.NEAREST)
                ox, oy = ci * W * sc, d * H * sc
                img.alpha_composite(big, (ox, oy))
                ly = oy + (ry - y0) * sc
                dr.line([(ox, ly), (ox + W * sc, ly)], fill=(255, 0, 0, 255), width=1)
                px, py = ox + (ys[f][0] - x0) * sc, oy + (ys[f][1] - y0) * sc
                dr.ellipse([px - 4, py - 4, px + 4, py + 4], outline=(0, 255, 255, 255))
        o = os.path.join(AS, 'revision', 'remate_pies_%s_%s.png' % (st, kind))
        img.save(o)
        print('->', o)


main()
