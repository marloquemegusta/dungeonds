"""Compone los pases crudos del remate (proto_remate_exvoto_v2.py) en fotogramas 1x RGBA y en el GIF de control.

Uso: python tools/characters/proto_remate_exvoto_post.py <carpeta_raw> <carpeta_salida> <X> [--test N]
  <carpeta_raw>   = <salida_blender>/exvoto_<X>/raw   (fNN_lit.png, fNN_flat.png, sNN.png, hNN.png opcional)
  <carpeta_salida>= walkthroughs/remate-exvoto/assets/ronda2   (escribe exvoto_<X>/fNN.png y exvoto_<X>.gif)

Iluminacion: el Workbench sale oscuro frente al render del juego, asi que se combina el pase plano (color de la textura)
con el relieve del pase de estudio:  rgb = plano * GAIN * (estudio/plano / R0)^0.9  (GAIN y R0 calibrados contra los
sprites reales: medias hero (115,82,62), Exvoto (156,142,109)).
GIF: 4x NEAREST, 60 ms por fotograma, fondo #3d3b38 y UNA paleta global para todos los fotogramas.
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageFilter

RAW, OUTD, X = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = None
if '--test' in sys.argv:
    ONLY = int(sys.argv[sys.argv.index('--test') + 1])
CELL, SS = 64, 4
GAIN, R0 = 1.38, 0.55
BG = (0x3d, 0x3b, 0x38)
# colores de efecto apagados (FX_SH_* de source/weapons.c, RGB15 x8)
HEAT_COL = np.array([216, 160, 88], np.float32)      # FX_SH_GOLD
HEAT_HOT = np.array([192, 120, 56], np.float32)      # FX_SH_AMBER


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
    hp = os.path.join(RAW, 'h%02d.png' % i)
    if os.path.exists(hp):
        h = np.array(Image.open(hp).convert('RGBA')).astype(np.float32)
        m = (h[..., 0] / 255.0 * (h[..., 3] / 255.0))[..., None]
        tint = HEAT_COL * (1 - m) + HEAT_HOT * m
        rgb = rgb * (1 - 0.65 * m) + tint * 0.65 * m
        rgb = np.clip(rgb, 0, 255)
    out = np.dstack([rgb, al]).astype(np.uint8)
    img = Image.fromarray(out, 'RGBA').resize((CELL, CELL), Image.BOX)
    a = np.array(img)
    a[..., 3] = np.where(a[..., 3] >= 110, 255, 0)      # borde duro, como los sprites de la DS
    img = Image.fromarray(a, 'RGBA')
    # sombra: pase negro, suavizado en alta resolucion, 45 % de opacidad
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
fdir = os.path.join(OUTD, 'exvoto_' + X)
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
# paleta global: se cuantiza un collage con todos los fotogramas y se aplica la misma paleta a cada uno (sin tramado)
n = len(big)
cols = n
col = Image.new('RGB', (CELL * Z * cols, CELL * Z))
for k, b in enumerate(big):
    col.paste(b, (k * CELL * Z, 0))
pal = col.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
gifs = [b.quantize(palette=pal, dither=Image.NONE) for b in big]
dur = [60] * n
if ONLY is None:
    dur[-1] = 600
    gifs[0].save(os.path.join(OUTD, 'exvoto_%s.gif' % X), save_all=True, append_images=gifs[1:], duration=dur, loop=0,
                 disposal=1, optimize=False)
    # hoja de contacto 4x para revisar (no es entregable)
    rows = (n + 5) // 6
    sheet = Image.new('RGB', (6 * CELL * 3, rows * CELL * 3), BG)
    for k, b in enumerate(big):
        sheet.paste(b.resize((CELL * 3, CELL * 3), Image.NEAREST), ((k % 6) * CELL * 3, (k // 6) * CELL * 3))
    sheet.save(os.path.join(RAW, '..', 'hoja.png'))
else:
    big[0].save(os.path.join(RAW, '..', 'test_%02d_4x.png' % ONLY))
print('POST OK', X, idx)
