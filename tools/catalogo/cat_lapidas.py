"""Hoja 2: las 8 lapidas (h y v) sobre el suelo de rombos con el marine para escala.

usage: python tools/catalogo/cat_lapidas.py
Salida: walkthroughs/v032-escenario/assets/cat_lapidas.png (letras A..H).
"""
from PIL import Image

import cat_common as C

NAMES = [
    "lapida_cruz_h", "lapida_cruz_v",
    "lapida_caballero_h", "lapida_caballero_v",
    "lapida_cruz2_h", "lapida_cruz2_v",
    "lapida_caballero2_h", "lapida_caballero2_v",
]
CELL_W, CELL_H = 124, 96
BOX = (48, 40, 48 + CELL_W, 40 + CELL_H)
GROUND = 70


def main():
    marine = C.char_frame("characters_neutral", "marine", 0, 0)
    marine_anchor = C.char_anchor("characters_neutral", "marine")

    cells = []
    for index, name in enumerate(NAMES):
        lapida = C.prop_image(name)
        cell = Image.new("RGBA", (CELL_W, CELL_H), C.BG)
        cell.paste(C.floor_crop("rombos", (CELL_W, CELL_H), BOX), (0, 0))
        cell.alpha_composite(marine, (2, GROUND - marine_anchor[1]))
        cell.alpha_composite(lapida, (CELL_W - lapida.width - 2, GROUND - lapida.height))
        label = name[len("lapida_"):]
        cells.append((cell, chr(ord("A") + index), label))

    C.build_grid(cells, 4, CELL_W, CELL_H, "cat_lapidas.png",
                 "Lapidas (top_only) sobre rombos; marine a la izquierda para escala",
                 scale=3,
                 footer="A-H segun el orden pedido: cruz, caballero, cruz2, caballero2; h = horizontal, v = vertical.")


if __name__ == "__main__":
    main()
