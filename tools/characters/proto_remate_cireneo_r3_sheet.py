"""Monta los fotogramas 1x RGBA (sombra incluida), la hoja de contacto 4x y el GIF de control de una opcion del remate del
Cireneo a partir de los f??.png / s??.png a 4x que escribe proto_remate_cireneo.py.

Uso: python tools/characters/proto_remate_cireneo_sheet.py <raw_dir> <carpeta_fotogramas> [gif_salida] [hoja_salida] [columnas]
  - <carpeta_fotogramas>/f00.png... : 1x, fondo transparente, sombra incluida.
  - gif_salida: 4x NEAREST, 60 ms por fotograma, fondo #3d3b38, UNA paleta global para todos los fotogramas.
  - hoja_salida: hoja de contacto 4x (solo para revisar).
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageDraw

raw, dst = sys.argv[1], sys.argv[2]
gif_out = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
sheet_out = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 6
os.makedirs(dst, exist_ok=True)
BG = (0x3d, 0x3b, 0x38)
SHADOW_A = 0.42
Z = 4

fs = sorted(glob.glob(os.path.join(raw, 'f??.png')))
frames = []
for i, f in enumerate(fs):
    col = Image.open(f).convert('RGBA')
    n = col.size[0] // 4
    col = col.resize((n, n), Image.BOX)
    sh = Image.open(os.path.join(raw, 's' + os.path.basename(f)[1:])).convert('RGBA').resize((n, n), Image.BOX)
    a = sh.getchannel('A').point(lambda v: int(v * SHADOW_A))
    shadow = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    shadow.putalpha(a)
    fr = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    fr.alpha_composite(shadow)
    fr.alpha_composite(col)
    frames.append(fr)
    fr.save(os.path.join(dst, 'f%02d.png' % i))
N = frames[0].size[0]

if sheet_out:
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * N * Z, rows * N * Z), BG)
    d = ImageDraw.Draw(sheet)
    for i, fr in enumerate(frames):
        x, y = (i % cols) * N * Z, (i // cols) * N * Z
        big = fr.resize((N * Z, N * Z), Image.NEAREST)
        sheet.paste(big, (x, y), big)
        d.rectangle([x, y, x + N * Z - 1, y + N * Z - 1], outline=(30, 28, 32))
        d.text((x + 4, y + 3), str(i), fill=(235, 235, 235))
    sheet.save(sheet_out)

if gif_out:
    comp = []
    for fr in frames:
        bg = Image.new('RGBA', (N, N), BG + (255,))
        bg.alpha_composite(fr)
        comp.append(bg.convert('RGB').resize((N * Z, N * Z), Image.NEAREST))
    # una paleta GLOBAL: se cuantiza una imagen que contiene todos los fotogramas y todos usan esa misma paleta
    mosaic = Image.new('RGB', (N * Z, N * Z * len(comp)))
    for i, c in enumerate(comp):
        mosaic.paste(c, (0, i * N * Z))
    pal_img = mosaic.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
    out = [c.quantize(palette=pal_img, dither=Image.NONE) for c in comp]
    durs = [60] * len(out)
    durs[-1] = 600
    out[0].save(gif_out, save_all=True, append_images=out[1:], duration=durs, loop=0, disposal=1, optimize=False)
import numpy as np
for i, fr in enumerate(frames):
    a = np.array(fr.getchannel('A'))
    sp = np.array(Image.open(fs[i]).convert('RGBA').resize((N, N), Image.BOX).getchannel('A'))
    ys, xs = np.where(sp > 20)
    edge = (sp[0, :] > 20).any() or (sp[-1, :] > 20).any() or (sp[:, 0] > 20).any() or (sp[:, -1] > 20).any()
    print('f%02d sprite bbox x%d-%d y%d-%d%s' % (i, xs.min(), xs.max(), ys.min(), ys.max(), '  <<< TOCA EL BORDE' if edge else ''))
print('OK', len(frames), 'celda', N)
