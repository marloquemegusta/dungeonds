"""Compone la comparativa A/B simulando la conversión a DS y sobre suelo real."""
import sys, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = 'C:/codexlocal/dungeonds/assets/sprites/arenas'
CELL = 40


def soft_contrast(rgb, gain):
    """Curva S en luminancia con pivote en la mediana: sube contraste medio sin recortar extremos."""
    f = rgb / 255.0
    L = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    p = float(np.median(L))
    d = L - p
    m = np.where(d < 0, p, 1 - p)
    out = p + d * gain / (1 + (gain - 1) * np.abs(d) / np.maximum(m, 1e-4))
    scale = np.where(L > 1e-4, out / np.maximum(L, 1e-4), 1)
    return np.clip(f * scale[..., None], 0, 1) * 255


def ds_convert(rgba, thresh, rounding):
    rgb = rgba[..., :3].astype(float)
    q = np.clip(np.round(rgb / 255 * 31), 0, 31) if rounding else (rgb.astype(int) >> 3)
    out = np.zeros_like(rgba)
    out[..., :3] = (q * 255 / 31).astype(np.uint8)
    out[..., 3] = np.where(rgba[..., 3] >= thresh, 255, 0)
    return out


VARIANTS = [  # (carpeta, etiqueta, umbral, redondeo, ganancia curva)
    ('A_base', 'A  actual', 40, False, None),
    ('B_ss4', 'B  supersampling x4 + bordes 50%', 128, True, None),
    ('E_neutral', 'C  B + tono neutro + curva S', 128, True, 1.45),
    ('F_fres_soft', 'D  C + brillo de borde suave', 128, True, 1.45),
    ('G_fres_strong', 'E  C + brillo de borde fuerte', 128, True, 1.45),
]


def floor(name, w, h, origin):
    if name == 'rom':  # suelo real de la ROM: misma baldosa de 40x40 bajo cada celda
        patch = Image.open('C:/codexlocal/dungeonds/walkthroughs/hw-shadows/assets/stress_hw_frame.png').convert('RGBA').crop((20, 250, 60, 290))
        im = Image.new('RGBA', (w, h))
        for x in range(0, w, CELL): im.paste(patch, (x, 0))
        return im
    im = Image.open(f'{ROOT}/{name}/world.png').convert('RGBA')
    return im.crop((origin[0], origin[1], origin[0] + w, origin[1] + h))


def main(char, frame=0):
    rows = []
    for folder, label, th, rnd, gain in VARIANTS:
        sheet = np.asarray(Image.open(f'{HERE}/out/{char}/{folder}/spritesheet.png').convert('RGBA')).copy()
        if gain:
            m = sheet[..., 3] > 0
            sheet[..., :3][m] = soft_contrast(sheet[..., :3][m].astype(float)[None], gain)[0].astype(np.uint8)
        rows.append((label, ds_convert(sheet, th, rnd)))
    scale = 4
    lab_w = 0
    out_imgs = []
    for fl, org in (('rom', None), ('dungeon_01', (300, 200))):
        W, H = 8 * CELL, CELL
        canvas = Image.new('RGBA', (W * scale, (H * scale + 22) * len(rows)), (20, 20, 20, 255))
        dr = ImageDraw.Draw(canvas)
        for i, (label, sh) in enumerate(rows):
            bg = floor(fl, W, H, org)
            for d in range(8):
                cell = Image.fromarray(sh[d * CELL:(d + 1) * CELL, frame * CELL:(frame + 1) * CELL])
                bg.alpha_composite(cell, (d * CELL, 0))
            y = i * (H * scale + 22)
            dr.text((6, y + 5), label, fill=(255, 255, 255, 255))
            canvas.paste(bg.resize((W * scale, H * scale), Image.NEAREST), (0, y + 22))
        p = f'{HERE}/cmp_{char}_{fl}.png'
        canvas.save(p)
        out_imgs.append(p)
    print('\n'.join(out_imgs))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0)
