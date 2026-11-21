"""Compone los pases crudos del remate del Ojo (ds_remate_ojo.py) en fotogramas 1x RGBA, GIF 4x y hoja de contacto.

Misma iluminacion que los remates del Exvoto (proto_remate_exvoto_post.py): el pase plano aporta el color y el de
estudio el relieve: rgb = plano * GAIN * (estudio/plano / R0)^0.9. Bordes duros al 110 de alfa y sombra al 45 %.

Uso: python tools/characters/ds_remate_ojo_post.py <carpeta_raw> <carpeta_salida> [celda]
  <carpeta_raw>    = <salida>/ds_ojo/raw  (fNN_lit.png, fNN_flat.png, sNN.png)
  <carpeta_salida> = walkthroughs/remate-ojo/assets
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageFilter

RAW, OUTD = sys.argv[1], sys.argv[2]
CELL = int(sys.argv[3]) if len(sys.argv) > 3 else 96
ONLY = None
if '--test' in sys.argv:
    ONLY = int(sys.argv[sys.argv.index('--test') + 1])
SS = 4
GAIN, R0 = 1.38, 0.55
BG = (0x3d, 0x3b, 0x38)


def lum(a):
    return a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11


def compose(i):
    lit = np.array(Image.open(os.path.join(RAW, 'f%02d_lit.png' % i)).convert('RGBA')).astype(np.float32)
    flat = np.array(Image.open(os.path.join(RAW, 'f%02d_flat.png' % i)).convert('RGBA')).astype(np.float32)
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
    s = Image.open(os.path.join(RAW, 's%02d.png' % i)).convert('RGBA').getchannel('A')
    s = s.filter(ImageFilter.GaussianBlur(2.2 * SS)).resize((CELL, CELL), Image.BOX)
    sa = np.array(s).astype(np.float32) * 0.45
    sh = np.zeros((CELL, CELL, 4), np.uint8)
    sh[..., 3] = np.clip(sa, 0, 255).astype(np.uint8)
    fr = Image.fromarray(sh, 'RGBA')
    fr.alpha_composite(img)
    return fr


idx = sorted(int(os.path.basename(p)[1:3]) for p in glob.glob(os.path.join(RAW, 'f??_lit.png')))
if ONLY is not None:
    idx = [ONLY]
fdir = os.path.join(OUTD, 'frames')
os.makedirs(fdir, exist_ok=True)
frames = []
for i in idx:
    fr = compose(i)
    fr.save(os.path.join(fdir, 'f%02d.png' % i))
    frames.append(fr)
Z = 4
big = []
for fr in frames:
    bg = Image.new('RGBA', (CELL * Z, CELL * Z), BG + (255,))
    bg.alpha_composite(fr.resize((CELL * Z, CELL * Z), Image.NEAREST))
    big.append(bg.convert('RGB'))
n = len(big)
col = Image.new('RGB', (CELL * Z * n, CELL * Z))
for k, b in enumerate(big):
    col.paste(b, (k * CELL * Z, 0))
pal = col.quantize(colors=160, method=Image.MEDIANCUT, dither=Image.NONE)
gifs = [b.quantize(palette=pal, dither=Image.NONE) for b in big]
dur = [60] * n
if ONLY is None:
    dur[-1] = 700
    gifs[0].save(os.path.join(OUTD, 'ojo_remate_4x.gif'), save_all=True, append_images=gifs[1:], duration=dur,
                 loop=0, disposal=1, optimize=False)
    rows = (n + 3) // 4
    sheet = Image.new('RGB', (4 * CELL * 3, rows * CELL * 3), BG)
    for k, b in enumerate(big):
        sheet.paste(b.resize((CELL * 3, CELL * 3), Image.NEAREST), ((k % 4) * CELL * 3, (k // 4) * CELL * 3))
    sheet.save(os.path.join(OUTD, 'ojo_remate_sheet.png'))
else:
    big[0].save(os.path.join(OUTD, 'test_%02d_4x.png' % ONLY))
print('POST OK', idx)
