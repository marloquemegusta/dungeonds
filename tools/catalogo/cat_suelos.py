"""Hoja 1: cada suelo de la catedral con la misma escena (marine + 3 piezas).

usage: python tools/catalogo/cat_suelos.py
Salida: walkthroughs/v032-escenario/assets/cat_suelos.png (numeros 1..N).
"""
import os

from PIL import Image

import cat_common as C

FLOORS = [
    "rombos", "rombos_b", "rombos_h", "rombos_h_b",
    "losas_3d", "losas_3d_b", "losas_3d_h", "losas_3d_h_b",
]
CELL_W, CELL_H = 216, 136
BOX = (48, 40, 48 + CELL_W, 40 + CELL_H)
GROUND = 108
PIECES = ["banco_volcado", "columna", "vela"]


def main():
    floors = [f for f in FLOORS if os.path.isdir(os.path.join(C.FLOOR, f))]
    for extra in sorted(os.listdir(C.FLOOR)):
        if extra.startswith("rombos_tripo") and extra not in floors:
            floors.append(extra)
    missing = [f for f in FLOORS if f not in floors]
    if missing:
        print("aviso: no existen", missing)

    marine = C.char_frame("characters_neutral", "marine", 0, 0)
    marine_anchor = C.char_anchor("characters_neutral", "marine")
    items = [("marine", marine, marine_anchor[1])]
    for name in PIECES:
        image = C.prop_image(name)
        items.append((name, image, image.height))

    total = sum(i[1].width for i in items)
    gap = (CELL_W - total) / (len(items) + 1)
    starts, x = [], gap
    for _, image, _ in items:
        starts.append(round(x))
        x += image.width + gap

    cells = []
    for number, floor in enumerate(floors, 1):
        cell = Image.new("RGBA", (CELL_W, CELL_H), C.BG)
        cell.paste(C.floor_crop(floor, (CELL_W, CELL_H), BOX), (0, 0))
        for (name, image, ground_offset), sx in zip(items, starts):
            if name != "marine":
                mask, off = C.prop_shadow(name)
                sh = C.shadow_rgba(mask)
                cell.alpha_composite(sh, (sx + off[0], GROUND - ground_offset + off[1]))
            cell.alpha_composite(image, (sx, GROUND - ground_offset))
        cells.append((cell, number, floor))

    C.build_grid(cells, 2, CELL_W, CELL_H, "cat_suelos.png",
                 "Suelos de la catedral: misma escena (marine + banco, columna y vela)",
                 scale=3,
                 footer="Cada opcion es un recorte de floor_512x256.png a escala 1x, ampliado x3 con NEAREST.")


if __name__ == "__main__":
    main()
