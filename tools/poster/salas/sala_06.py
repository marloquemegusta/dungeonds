"""Sala 6: Claustro bajo. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = None   # el claustro usa sus dos variantes (dia y noche)
LUZ = None
DROP = ['columna_entera']


# Galeria porticada: dos filas de columnas (arcada) pegadas a los muros, cada 128 px; el centro queda abierto.
def _arcada(nb, ys=(8, 168)):
    out = []
    for k in range(nb):
        for y in ys:
            out += [("columna_entera", k, 8, y), ("columna_entera", k, 128, y)]
    return out


def _claustro():
    out = _arcada(NB)
    out += [("banco_roto", 0, 72, 336), ("lapida_pie", 1, 88, 332), ("banco_roto", 2, 72, 336)]
    return out


NB = 3
ADD = _claustro()
