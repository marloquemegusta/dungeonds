"""GIFs y hoja de contacto de la ronda de animacion de la Super Monja: ACTUAL | A | B | C, 4x NEAREST, fondo gris liso.
Uso: python tools/characters/super_monja_anim_gif.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "walkthroughs/arpg-exvoto-ramas/assets/anim"
SHEETS = [("ACTUAL", ROOT / "assets/sprites/characters/exvoto_super_monja/spritesheet.png")] + [
    (v, ROOT / f"assets/staging/super_monja_anim/{v}/exvoto_super_monja/spritesheet.png") for v in "ABC"]
C, Z, BG = 56, 4, (118, 115, 120, 255)
X0, X1 = 10, 46   # recorte horizontal solo para verlo mejor (la hoja vigente sigue en 56 px)
ROWS = {"S": 0, "SE": 7}


def cell(sheet, row, f):
    return sheet.crop((f * C + X0, row * C, f * C + X1, row * C + C))


def frame(sheets, row, f):
    W = X1 - X0
    im = Image.new("RGBA", (W * len(sheets), C), BG)
    for i, s in enumerate(sheets):
        im.alpha_composite(cell(s, row, f), (i * W, 0))
    return im.resize((im.width * Z, im.height * Z), Image.NEAREST).convert("RGB")


def gif(path, frames, ms):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=ms, loop=0, disposal=2)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    sheets = [Image.open(p).convert("RGBA") for _, p in SHEETS]
    for d, r in ROWS.items():
        fr = [frame(sheets, r, f) for f in range(8)]
        gif(OUT / f"sm_anim_{d}.gif", fr, 133)
        if d == "S":
            gif(OUT / "sm_anim_S_rapida.gif", fr, 65)
    # hoja: por version una fila S y una SE (8 frames), con la ACTUAL arriba
    Wc = X1 - X0
    W = Wc * 8 * Z
    sheet = Image.new("RGB", (W, C * Z * 8), BG[:3])
    y = 0
    for s in sheets:
        for r in ROWS.values():
            row = Image.new("RGBA", (Wc * 8, C), BG)
            for f in range(8):
                row.alpha_composite(cell(s, r, f), (f * Wc, 0))
            sheet.paste(row.resize((W, C * Z), Image.NEAREST).convert("RGB"), (0, y))
            y += C * Z
    sheet.save(OUT / "sm_anim_hoja.png")
