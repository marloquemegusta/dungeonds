"""Ronda de variantes de color/material de la Super Monja (solo walk), fuera de la ROM.
Post-proceso sobre los colores horneados (el lab rapido no expone material ni brillo por render):
  A actual | B cera negra pulida | C cera ahumada | D = C + brillos de B.
Entrada: assets/sprites/characters/exvoto_super_monja/spritesheet.png (56 px, 8x8).
Salida: assets/staging/super_monja_variantes/<A|B|C|D>/spritesheet.png
Uso: python tools/characters/super_monja_variantes.py
"""
import numpy as np
from pathlib import Path
from PIL import Image
from scipy.ndimage import gaussian_filter, binary_erosion

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets/sprites/characters/exvoto_super_monja/spritesheet.png"
OUT = ROOT / "assets/staging/super_monja_variantes"
C = 56


def lum(rgb):
    return (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114) / 255.0


def ramp(L, stops):
    xs = [s[0] for s in stops]
    return np.stack([np.interp(L, xs, [s[1][k] for s in stops]) for k in range(3)], -1)


def spec(rgb, a, strength):
    """Brillo de cera: lo que sobresale del entorno local (pliegues que cogen luz) -> marfil/ambar suave."""
    L = lum(rgb)
    m = a.astype(float)
    num = gaussian_filter(L * m, 3.0)
    den = np.maximum(gaussian_filter(m, 3.0), 1e-3)
    local = num / den
    h = np.clip((L - local - 0.012) * 9.0, 0, 1) ** 0.8
    h = h * np.clip((0.30 - L) / 0.10, 0, 1)      # solo el habito: cara, manos y pies no brillan
    h = gaussian_filter(h, 0.9) * 1.5           # suaviza el ruido del horneado: brillo en parches, no en motas
    h = np.minimum(h, 0.6) * (a > 0)
    amber = np.array([196, 160, 112], float)   # marfil-ambar, nunca blanco
    return h[..., None] * amber * strength, h


def rim(a, rgb, tone, amount):
    """Borde translucido falso: pixel de silueta y el siguiente, mas calidos y claros."""
    m = a > 0
    e1 = binary_erosion(m, iterations=1)
    e2 = binary_erosion(m, iterations=2)
    r1 = m & ~e1
    r2 = e1 & ~e2
    out = rgb.copy()
    tone = np.array(tone, float)
    out[r1] = out[r1] * (1 - amount) + tone * amount
    out[r2] = out[r2] * (1 - amount * 0.4) + tone * amount * 0.4
    return out


def variant(cell, v):
    a = cell[..., 3]
    rgb = cell[..., :3].astype(float)
    if v == "A":
        return cell
    L = lum(rgb)
    if v == "B":
        base = 0.075 * 255 + rgb * 0.93 + np.array([4, 2, 0])     # negro -> carbon profundo (sin tocar el tono)
        add, _ = spec(rgb, a, 0.8)
        out = base + add
    else:
        # C: ramp oxblood/pardo ahumado, el pelo claro (cara/pies) sube a marfil
        out = ramp(np.clip(L * 1.6, 0, 1), [(0, (26, 17, 16)), (0.18, (46, 29, 25)), (0.4, (78, 50, 38)),
                                             (0.7, (150, 112, 82)), (1.0, (200, 172, 130))])
        if v == "D":
            add, _ = spec(rgb, a, 0.7)
            out = out + add
        out = rim(a, out, (150, 98, 66), 0.40)
    out = np.clip(out, 0, 255)
    res = np.dstack([out, a]).astype(np.uint8)
    res[a == 0] = 0
    return res


if __name__ == "__main__":
    sheet = np.array(Image.open(SRC).convert("RGBA"))
    for v in "ABCD":
        out = sheet.copy()
        for r in range(8):
            for f in range(8):
                out[r * C:(r + 1) * C, f * C:(f + 1) * C] = variant(sheet[r * C:(r + 1) * C, f * C:(f + 1) * C], v)
        d = OUT / v
        d.mkdir(parents=True, exist_ok=True)
        Image.fromarray(out).save(d / "spritesheet.png")
        print(v, (d / "spritesheet.png").stat().st_size)
