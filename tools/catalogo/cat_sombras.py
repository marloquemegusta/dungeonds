"""Hoja 3: seis piezas del lote 1 con y sin su sombra horneada, sobre rombos.

usage: python tools/catalogo/cat_sombras.py
Salida: walkthroughs/v032-escenario/assets/cat_sombras.png (numeros 1..12).
"""
from PIL import Image

import cat_common as C

PIECES = ["banco_roto", "banco_volcado", "columna", "relicario", "santo", "vela"]
CELL_W, CELL_H = 124, 100
BOX = (48, 40, 48 + CELL_W, 40 + CELL_H)
GROUND = 72


def main():
    cells = []
    number = 1
    for name in PIECES:
        image = C.prop_image(name)
        mask, offset = C.prop_shadow(name)
        shadow = C.shadow_rgba(mask)
        x = (CELL_W - image.width) // 2
        origin_y = GROUND - image.height
        for with_shadow in (False, True):
            cell = Image.new("RGBA", (CELL_W, CELL_H), C.BG)
            cell.paste(C.floor_crop("rombos", (CELL_W, CELL_H), BOX), (0, 0))
            if with_shadow:
                cell.alpha_composite(shadow, (x + offset[0], origin_y + offset[1]))
            cell.alpha_composite(image, (x, origin_y))
            suffix = "con sombra" if with_shadow else "sin sombra"
            cells.append((cell, number, f"{name} \u00b7 {suffix}"))
            number += 1

    C.build_grid(cells, 4, CELL_W, CELL_H, "cat_sombras.png",
                 "Piezas del lote 1 sobre rombos: sin sombra (impar) y con su shadow.png (par)",
                 scale=3,
                 footer="La sombra usa shadow.png y shadow_offset_px de meta.json (luz alineada con la del marine).")


if __name__ == "__main__":
    main()
