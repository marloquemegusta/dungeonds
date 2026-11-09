"""Hoja A/B: rombos_tripo frente a rombos_tripo_b con la misma escena.

Cada suelo es el mismo recorte grande (256x128 de floor_512x256.png), ampliado x3 con NEAREST.
Escena: marine, banco_roto, columna y vela, cada uno con su sombra sobre el suelo.

usage: python tools/catalogo/cat_tripo_ab.py
Salida: walkthroughs/v032-escenario/assets/cat_tripo_ab.png (etiquetas A y B).
"""
from PIL import Image

import cat_common as C

FLOORS = [("A", "rombos_tripo"), ("B", "rombos_tripo_b")]
CELL_W, CELL_H = 256, 128
BOX = (0, 0, CELL_W, CELL_H)
GROUND = 112
PIECES = ["banco_roto", "columna", "vela"]


def main():
    marine = C.char_frame("characters_neutral", "marine", 0, 0)
    marine_anchor = C.char_anchor("characters_neutral", "marine")
    items = [("marine", marine, marine_anchor[1])]
    for name in PIECES:
        image = C.prop_image(name)
        items.append((name, image, image.height))

    total = sum(item[1].width for item in items)
    gap = (CELL_W - total) / (len(items) + 1)
    starts, x = [], gap
    for _, image, _ in items:
        starts.append(round(x))
        x += image.width + gap

    cells = []
    for badge, floor in FLOORS:
        cell = Image.new("RGBA", (CELL_W, CELL_H), C.BG)
        cell.paste(C.floor_crop(floor, (CELL_W, CELL_H), BOX), (0, 0))
        for (name, image, ground_offset), sx in zip(items, starts):
            if name != "marine":
                mask, off = C.prop_shadow(name)
                sh = C.shadow_rgba(mask)
                cell.alpha_composite(sh, (sx + off[0], GROUND - ground_offset + off[1]))
            cell.alpha_composite(image, (sx, GROUND - ground_offset))
        cells.append((cell, badge, floor))

    C.build_grid(cells, 2, CELL_W, CELL_H, "cat_tripo_ab.png",
                 "rombos_tripo (A) frente a rombos_tripo_b (B): misma escena",
                 scale=3,
                 footer="Recorte 256x128 de floor_512x256.png ampliado x3 con NEAREST; marine, banco_roto, columna y vela con sombra.")


if __name__ == "__main__":
    main()
