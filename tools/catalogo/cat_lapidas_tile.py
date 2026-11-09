"""Hoja de lapidas tileadas sobre rombos_tripo, alineadas a la rejilla de 8 px.

Cada celda es un recorte 384x192 de floor_512x256.png de rombos_tripo (el floor completo
512x256 a x3 supera el limite de 1600 px de ancho). Las lapidas se colocan con origen
multiplo de 8 px; no llevan sombra para que las costuras y solapes se vean sin ruido.

Disposiciones:
  1: fila de lapida_cruz2_h seguidas, en bandas alternas con losas del damero.
  2: columna de lapida_cruz2_v seguidas, en columnas alternas con losas del damero.
  3: mosaico alterno h/v con lapida_cruz2_h y lapida_cruz2_v.
  4 (franja): mosaico alterno h/v con lapida_caballero2_h y lapida_caballero2_v.

usage: python tools/catalogo/cat_lapidas_tile.py
Salida: walkthroughs/v032-escenario/assets/cat_lapidas_tile.png
"""
from PIL import Image

import cat_common as C

CANVAS_W, CANVAS_H = 384, 192
BOX = (0, 0, CANVAS_W, CANVAS_H)
BLOCK_W, BLOCK_H = 96, 48


def base():
    cell = Image.new("RGBA", (CANVAS_W, CANVAS_H), C.BG)
    cell.paste(C.floor_crop("rombos_tripo", (CANVAS_W, CANVAS_H), BOX), (0, 0))
    return cell


def place(cell, sprite, x, y):
    assert x >= 0 and y >= 0 and x + sprite.width <= CANVAS_W and y + sprite.height <= CANVAS_H, (x, y)
    assert x % 8 == 0 and y % 8 == 0, (x, y)
    cell.alpha_composite(sprite, (x, y))


def arr_fila(cell, h):
    # Bandas en y = 8, 56, 104, 152; las bandas impares desplazadas 40 px.
    for band, y in enumerate((8, 56, 104, 152)):
        x0 = 40 if band % 2 else 0
        for k in range(5):
            x = x0 + 72 * k
            if x + h.width <= CANVAS_W:
                place(cell, h, x, y)


def arr_columna(cell, v):
    # Columnas en x = 0, 96, 192, 288; las impares desplazadas 40 px en y.
    for col, x in enumerate((0, 96, 192, 288)):
        y0 = 40 if col % 2 else 0
        for k in range(4):
            y = y0 + 40 * k
            if y + v.height <= CANVAS_H:
                place(cell, v, x, y)


def arr_mosaico(cell, h, v, h_off, v_off):
    # Cada bloque de 96x48 lleva una h o una v, alternando en damero.
    for by in range(CANVAS_H // BLOCK_H):
        for bx in range(CANVAS_W // BLOCK_W):
            x0, y0 = bx * BLOCK_W, by * BLOCK_H
            if (bx + by) % 2 == 0:
                place(cell, h, x0 + h_off[0], y0 + h_off[1])
            else:
                place(cell, v, x0 + v_off[0], y0 + v_off[1])


def main():
    cruz_h = C.prop_image("lapida_cruz2_h")
    cruz_v = C.prop_image("lapida_cruz2_v")
    cab_h = C.prop_image("lapida_caballero2_h")
    cab_v = C.prop_image("lapida_caballero2_v")

    cells = []

    cell = base()
    arr_fila(cell, cruz_h)
    cells.append((cell, "1", "fila de lapida_cruz2_h"))

    cell = base()
    arr_columna(cell, cruz_v)
    cells.append((cell, "2", "columna de lapida_cruz2_v"))

    cell = base()
    arr_mosaico(cell, cruz_h, cruz_v, (16, 8), (24, 8))
    cells.append((cell, "3", "mosaico h/v cruz2"))

    cell = base()
    arr_mosaico(cell, cab_h, cab_v, (16, 8), (24, 0))
    cells.append((cell, "4", "franja: mosaico h/v caballero2"))

    C.build_grid(cells, 2, CANVAS_W, CANVAS_H, "cat_lapidas_tile.png",
                 "Lapidas tileadas sobre rombos_tripo, rejilla de 8 px",
                 scale=2,
                 footer="Recorte 384x192 de rombos_tripo a x2 NEAREST; origenes multiplo de 8 px; sin sombras.")


if __name__ == "__main__":
    main()
