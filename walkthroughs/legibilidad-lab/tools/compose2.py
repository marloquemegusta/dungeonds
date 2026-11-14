"""Segunda tanda A/B sobre la variante C: bordes intermedios y enfoque tras reducir."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from compose import soft_contrast, ds_convert

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = 'C:/codexlocal/dungeonds/walkthroughs/hw-shadows/assets/stress_hw_frame.png'


def blur3(x):
    k = np.array([1, 2, 1], float) / 4
    p = np.pad(x, ((1, 1), (1, 1)) + ((0, 0),) * (x.ndim - 2), mode='edge')
    h = k[0] * p[:, :-2] + k[1] * p[:, 1:-1] + k[2] * p[:, 2:]
    return k[0] * h[:-2] + k[1] * h[1:-1] + k[2] * h[2:]


def sharpen(rgba, amount):
    """Enfoque que solo mira píxeles del propio personaje (sin halo contra el fondo transparente)."""
    rgb = rgba[..., :3].astype(float)
    m = (rgba[..., 3] >= 77).astype(float)
    bl = blur3(rgb * m[..., None]) / np.maximum(blur3(m), 1e-3)[..., None]
    out = rgba.copy()
    out[..., :3] = np.clip(rgb + amount * (rgb - bl), 0, 255).astype(np.uint8)
    return out


ROWS = [  # etiqueta, umbral de borde, enfoque
    ('C  elegida (bordes 50%)', 128, 0.0),
    ('C1 bordes 30%', 77, 0.0),
    ('C2 bordes 30% + enfoque suave', 77, 0.5),
    ('C3 bordes 30% + enfoque medio', 77, 1.0),
]


def main(char, frame=0):
    sheet = np.asarray(Image.open(f'{HERE}/out/{char}/E_neutral/spritesheet.png').convert('RGBA')).copy()
    cell = sheet.shape[0] // 8
    m = sheet[..., 3] > 0
    sheet[..., :3][m] = soft_contrast(sheet[..., :3][m].astype(float)[None], 1.45)[0].astype(np.uint8)
    patch = Image.open(ROM).convert('RGBA').crop((20, 240, 20 + cell, 240 + cell))
    S, W = 4, 8 * cell
    canvas = Image.new('RGBA', (W * S, (cell * S + 22) * len(ROWS)), (20, 20, 20, 255))
    dr = ImageDraw.Draw(canvas)
    for i, (label, th, amt) in enumerate(ROWS):
        sh = sharpen(sheet, amt) if amt else sheet
        sh = ds_convert(sh, th, True)
        bg = Image.new('RGBA', (W, cell))
        for d in range(8):
            bg.paste(patch, (d * cell, 0))
            bg.alpha_composite(Image.fromarray(sh[d * cell:(d + 1) * cell, frame * cell:(frame + 1) * cell]), (d * cell, 0))
        y = i * (cell * S + 22)
        dr.text((6, y + 5), f'{label}   ({int((sh[..., 3] > 0).sum())} px)', fill=(255, 255, 255, 255))
        canvas.paste(bg.resize((W * S, cell * S), Image.NEAREST), (0, y + 22))
    p = f'{HERE}/ab2_{char}.png'
    canvas.save(p)
    print(p)


if __name__ == '__main__':
    main(sys.argv[1])
