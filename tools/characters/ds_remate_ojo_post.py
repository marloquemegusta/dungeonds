"""Compone los pases crudos del remate del Ojo en las 8 direcciones (ds_remate_ojo.py).

Misma iluminacion que los remates del Exvoto: rgb = plano * GAIN * (estudio/plano / R0)^0.9, bordes duros al 110 de
alfa y sombra al 45 %. Escribe un GIF 4x por direccion, una hoja comparativa del fotograma de contacto y un HTML con
las 8 direcciones para revisarlo desde el movil.

Uso: python tools/characters/ds_remate_ojo_post.py <carpeta_raw_base> <carpeta_salida> [celda]
  <carpeta_raw_base> = <salida>/ds_ojo/raw   (contiene raw_d0 .. raw_d7)
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageFilter

RAW, OUTD = sys.argv[1], sys.argv[2]
CELL = int(sys.argv[3]) if len(sys.argv) > 3 else 96
SS = 4
GAIN, R0 = 1.38, 0.55
BG = (0x3d, 0x3b, 0x38)
ONLY = None
if '--test' in sys.argv:
    ONLY = int(sys.argv[sys.argv.index('--test') + 1])
DIRS = [int(x) for x in os.environ.get('DIRS', '0,1,2,3,4,5,6,7').split(',')]
DIR_NAMES = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
CONTACT_F = int(os.environ.get('CONTACT_F', '18'))


def lum(a):
    return a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11


def compose(raw, i):
    lit = np.array(Image.open(os.path.join(raw, 'f%02d_lit.png' % i)).convert('RGBA')).astype(np.float32)
    flat = np.array(Image.open(os.path.join(raw, 'f%02d_flat.png' % i)).convert('RGBA')).astype(np.float32)
    al = lit[..., 3]
    lf, ll = lum(flat[..., :3]), lum(lit[..., :3])
    ratio = np.where(lf > 6, ll / np.maximum(lf, 1), R0)
    shade = np.clip(ratio / R0, 0.55, 1.5) ** 0.9
    rgb = np.clip(flat[..., :3] * GAIN * shade[..., None], 0, 255)
    out = np.dstack([rgb, al]).astype(np.uint8)
    img = Image.fromarray(out, 'RGBA').resize((CELL, CELL), Image.BOX)
    a = np.array(img)
    a[..., 3] = np.where(a[..., 3] >= 110, 255, 0)
    img = Image.fromarray(a, 'RGBA')
    s = Image.open(os.path.join(raw, 's%02d.png' % i)).convert('RGBA').getchannel('A')
    s = s.filter(ImageFilter.GaussianBlur(2.2 * SS)).resize((CELL, CELL), Image.BOX)
    sa = np.array(s).astype(np.float32) * 0.45
    sh = np.zeros((CELL, CELL, 4), np.uint8)
    sh[..., 3] = np.clip(sa, 0, 255).astype(np.uint8)
    fr = Image.fromarray(sh, 'RGBA')
    fr.alpha_composite(img)
    return fr


def gif_of(frames, path, dur):
    big = []
    for fr in frames:
        bg = Image.new('RGBA', (CELL * 4, CELL * 4), BG + (255,))
        bg.alpha_composite(fr.resize((CELL * 4, CELL * 4), Image.NEAREST))
        big.append(bg.convert('RGB'))
    col = Image.new('RGB', (CELL * 4 * len(big), CELL * 4))
    for k, b in enumerate(big):
        col.paste(b, (k * CELL * 4, 0))
    pal = col.quantize(colors=160, method=Image.MEDIANCUT, dither=Image.NONE)
    q = [b.quantize(palette=pal, dither=Image.NONE) for b in big]
    q[0].save(path, save_all=True, append_images=q[1:], duration=dur, loop=0, disposal=1, optimize=False)


made = []
for d in DIRS:
    raw = os.path.join(RAW, 'raw_d%d' % d)
    if not os.path.isdir(raw):
        print('FALTA', raw)
        continue
    idx = sorted(int(os.path.basename(p)[1:3]) for p in glob.glob(os.path.join(raw, 'f??_lit.png')))
    if ONLY is not None:
        idx = [ONLY]
    fdir = os.path.join(OUTD, 'dir_%d' % d)
    os.makedirs(fdir, exist_ok=True)
    frames = []
    for i in idx:
        fr = compose(raw, i)
        fr.save(os.path.join(fdir, 'f%02d.png' % i))
        frames.append(fr)
    dur = [60] * len(frames)
    if ONLY is None:
        dur[-1] = 700
    gif_of(frames, os.path.join(OUTD, 'ojo_remate_d%d_4x.gif' % d), dur)
    made.append((d, frames))
    print('DIR', d, len(frames))

# hoja comparativa: el fotograma de contacto en las 8 direcciones (3x)
if ONLY is None and len(made) == 8:
    Z = 3
    sheet = Image.new('RGB', (4 * CELL * Z, 2 * CELL * Z), BG)
    for k, (d, frames) in enumerate(made):
        if CONTACT_F < len(frames):
            b = Image.new('RGBA', (CELL * Z, CELL * Z), BG + (255,))
            b.alpha_composite(frames[CONTACT_F].resize((CELL * Z, CELL * Z), Image.NEAREST))
            sheet.paste(b.convert('RGB'), ((k % 4) * CELL * Z, (k // 4) * CELL * Z))
    sheet.save(os.path.join(OUTD, 'ojo_remate_contacto_8dirs.png'))

    # HTML para revisar las 8 a la vez
    rows = []
    for d, _ in made:
        rows.append('<figure><img src="ojo_remate_d%d_4x.gif" width="384" height="384" alt="dir %d">'
                    '<figcaption>dir %d · %s</figcaption></figure>' % (d, d, d, DIR_NAMES[d]))
    html = ('<!doctype html><meta charset="utf-8"><title>Remate del Ojo - 8 direcciones</title>'
            '<style>body{background:#1e1d1c;color:#d8d3c8;font:14px system-ui;margin:0;padding:16px}'
            'h1{font-size:16px;font-weight:600;margin:0 0 12px}'
            '.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}'
            'figure{margin:0;background:#2b2a28;border-radius:8px;overflow:hidden}'
            'img{display:block;width:100%;height:auto;image-rendering:pixelated}'
            'figcaption{padding:6px 10px;font-size:13px;color:#b9b2a4}</style>'
            '<h1>Remate del Ojo &mdash; 8 direcciones (4x, 60 ms/fotograma)</h1><div class="g">'
            + ''.join(rows) + '</div>')
    with open(os.path.join(OUTD, 'ojo_remate_8dirs.html'), 'w', encoding='utf-8') as f:
        f.write(html)
print('POST OK', [d for d, _ in made])
