"""Compone los pases crudos del remate (ds_remate_exvoto.py) en los fotogramas 1x RGBA y en el GIF de control.

Uso: python tools/characters/ds_remate_exvoto_post.py <carpeta_raw> <directorio_ronda2> <X>
  <carpeta_raw>       = <salida_blender>/ds_exvoto_<X>/raw
  <directorio_ronda2> = walkthroughs/remate-exvoto/assets/ronda2

Escribe <directorio_ronda2>/ds_exvoto_<X>/fNN.png (1x RGBA, fondo transparente) y <directorio_ronda2>/ds_exvoto_<X>.gif.
GIF: 4x NEAREST, 60 ms por fotograma, fondo #3d3b38 y UNA PALETA GLOBAL para todos los fotogramas.
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageFilter

RAW, OUTD, X = sys.argv[1], sys.argv[2], sys.argv[3]
CELL_RAW = None
CELL = 64                      # la celda de salida del GIF (4x = 256); 1x se recorta a la celda comun
GAIN, R0 = 1.30, 0.55
BG = (0x3d, 0x3b, 0x38)
HEAT_COL = np.array([212, 168, 104], np.float32)      # FX_SH_GOLD apagado
HEAT_HOT = np.array([176, 116, 62], np.float32)       # FX_SH_AMBER apagado


def lum(a):
    return a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11


def compose(i, W, H):
    lit = np.array(Image.open(os.path.join(RAW, 'f%02d_lit.png' % i)).convert('RGBA')).astype(np.float32)
    flat = np.array(Image.open(os.path.join(RAW, 'f%02d_flat.png' % i)).convert('RGBA')).astype(np.float32)
    al = lit[..., 3]
    lf, ll = lum(flat[..., :3]), lum(lit[..., :3])
    ratio = np.where(lf > 6, ll / np.maximum(lf, 1), R0)
    shade = np.clip(ratio / R0, 0.62, 1.45) ** 0.85
    rgb = np.clip(flat[..., :3] * GAIN * shade[..., None], 0, 255)
    hp = os.path.join(RAW, 'h%02d.png' % i)
    if os.path.exists(hp):
        h = np.array(Image.open(hp).convert('RGBA')).astype(np.float32)
        m = (h[..., 0] / 255.0 * (h[..., 3] / 255.0))[..., None]
        tint = HEAT_COL * (1 - m) + HEAT_HOT * m
        rgb = rgb * (1 - 0.6 * m) + tint * 0.6 * m
        rgb = np.clip(rgb, 0, 255)
    out = np.dstack([rgb, al]).astype(np.uint8)
    img = Image.fromarray(out, 'RGBA').resize((W, H), Image.BOX)
    a = np.array(img)
    a[..., 3] = np.where(a[..., 3] >= 108, 255, 0)       # borde duro: en la DS no hay alfa parcial
    img = Image.fromarray(a, 'RGBA')
    s = Image.open(os.path.join(RAW, 's%02d.png' % i)).convert('RGBA').getchannel('A')
    s = s.filter(ImageFilter.GaussianBlur(2.0 * (W / float(CELL)))).resize((W, H), Image.BOX)
    sa = np.clip(np.array(s).astype(np.float32) * 0.45, 0, 255).astype(np.uint8)
    sh = np.zeros((H, W, 4), np.uint8)
    sh[..., 3] = sa
    fr = Image.fromarray(sh, 'RGBA')
    fr.alpha_composite(img)
    return fr


idx = sorted(int(os.path.basename(p)[1:3]) for p in glob.glob(os.path.join(RAW, 'f??_lit.png')))
probe = Image.open(os.path.join(RAW, 'f%02d_lit.png' % idx[0])).size
W = CELL
H = int(round(CELL * probe[1] / float(probe[0])))
fdir = os.path.join(OUTD, 'ds_exvoto_' + X)
os.makedirs(fdir, exist_ok=True)
frames = []
for i in idx:
    fr = compose(i, W, H)
    fr.save(os.path.join(fdir, 'f%02d.png' % i))
    frames.append(fr)
Z = 4
big = []
for fr in frames:
    bg = Image.new('RGBA', (W * Z, H * Z), BG + (255,))
    bg.alpha_composite(fr.resize((W * Z, H * Z), Image.NEAREST))
    big.append(bg.convert('RGB'))
# una sola paleta para todos los fotogramas: se cuantiza el collage y se aplica igual a cada uno
col = Image.new('RGB', (W * Z * len(big), H * Z))
for k, b in enumerate(big):
    col.paste(b, (k * W * Z, 0))
pal = col.quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE)
gifs = [b.quantize(palette=pal, dither=Image.NONE) for b in big]
dur = [60] * len(gifs)
dur[-1] = 420
gifs[0].save(os.path.join(OUTD, 'ds_exvoto_%s.gif' % X), save_all=True, append_images=gifs[1:], duration=dur, loop=0,
             disposal=1, optimize=False)
rows = (len(big) + 5) // 6
sheet = Image.new('RGB', (6 * W * Z, rows * H * Z), BG)
for k, b in enumerate(big):
    sheet.paste(b, ((k % 6) * W * Z, (k // 6) * H * Z))
sheet.save(os.path.join(OUTD, 'ds_exvoto_%s_hoja.png' % X))
print('POST OK', X, idx, 'size', (W, H))
