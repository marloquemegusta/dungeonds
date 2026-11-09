"""Hoja 4: personajes con contorno (characters) vs neutra sin contorno (characters_neutral).

usage: python tools/catalogo/cat_personajes.py
Salida: walkthroughs/v032-escenario/assets/cat_personajes.png
"""
from PIL import Image, ImageDraw

import cat_common as C

CHARS = ["marine", "charger", "necron", "skeleton"]
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
FRAMES = [0, 4]
VARIANTS = [("characters", "actual"), ("characters_neutral", "neutra")]
LBL_W, CELL, GAPX, ROWH, HEADER = 86, 40, 2, 42, 18
SCALE = 3


def main():
    base_w = LBL_W + len(DIRS) * (CELL + GAPX) - GAPX
    block_h = HEADER + len(FRAMES) * len(VARIANTS) * ROWH
    base_h = len(CHARS) * block_h + 24
    base = Image.new("RGBA", (base_w, base_h), C.BG)

    rows = []  # (etiqueta de fila, y_base, kind)
    for ci, char in enumerate(CHARS):
        top = 24 + ci * block_h
        for fi, frame in enumerate(FRAMES):
            for vi, (kind, label) in enumerate(VARIANTS):
                row = fi * len(VARIANTS) + vi
                rows.append((f"{char}", ci, frame, label, top + HEADER + row * ROWH, kind))
                anchor = C.char_anchor(kind, char)
                for di in range(len(DIRS)):
                    sprite = C.char_frame(kind, char, di, frame)
                    x = LBL_W + di * (CELL + GAPX)
                    y = top + HEADER + row * ROWH
                    base.alpha_composite(sprite, (x, y + 38 - anchor[1]))

    big = base.resize((base_w * SCALE, base_h * SCALE), Image.NEAREST)
    title_h = 22 * SCALE
    width, height = big.width + 4, big.height + title_h + 4
    out = Image.new("RGBA", (width, height), C.BG)
    out.alpha_composite(big, (2, 2 + title_h))
    draw = ImageDraw.Draw(out)
    title = "Personajes: con contorno vs neutra sin contorno (mismos fotogramas 0 y 4)"
    title_size = C.fit_font_size(draw, title, 14 * SCALE, width - 8)
    draw.text((5, 4), title, font=C.font(title_size), fill=C.INK)

    small = C.font(7 * SCALE)
    header = C.font(8 * SCALE)
    name_font = C.font(9 * SCALE)
    for char in CHARS:
        ci = CHARS.index(char)
        y0 = 2 + title_h + (24 + ci * block_h) * SCALE
        draw.text((5, y0), char.upper(), font=name_font, fill=C.ACCENT)
        for di, dname in enumerate(DIRS):
            x = 2 + (LBL_W + di * (CELL + GAPX)) * SCALE
            draw.text((x + 2, y0 - 2), f"{dname} ({di})", font=small, fill=C.DIM)

    for char, ci, frame, label, y, kind in rows:
        top = 2 + title_h + y * SCALE
        draw.text((5, top + 10), f"f{frame} {label}", font=small, fill=C.INK)
        for di in range(len(DIRS)):
            x = 2 + (LBL_W + di * (CELL + GAPX)) * SCALE
            draw.rectangle((x, top, x + CELL * SCALE - 1, top + CELL * SCALE - 1),
                           outline=(255, 255, 255, 26))

    if width > C.MAX_WIDTH:
        raise SystemExit(f"cat_personajes.png: {width} px de ancho > {C.MAX_WIDTH}")
    out.convert("RGB").save(C.out_path("cat_personajes.png"))
    print(C.out_path("cat_personajes.png"), out.size)


if __name__ == "__main__":
    main()
