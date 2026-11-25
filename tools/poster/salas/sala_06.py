"""Sala 6: Claustro bajo. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas).
GRUPOS: encuentros colocados a mano (formato en el docstring de poster_arpg_juego.py; revision: poster_arpg.py --sala 6 --revision)."""
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


# Nave 1 presenta cada pieza sola (DESIGN-ARPG.md §10, §12). Columnas de la arcada: visibles en x=18..52 y x=138..172 (centros 35 y 155),
# base en y=127 e y=287 de cada bloque. Una columna tapa entera a quien tenga los pies a ~20 px al norte de su base (p. ej. (35, 108)).
# La puerta izquierda (y 206..244 del bloque 0) es la entrada: el grupo 0 queda al norte y a la derecha de ella.
GRUPOS = [
    {"nombre": "Rebano", "formacion": "enjambre", "k": 0,      # enseña a matar primero a la monja: reza arrodillada ante la lapida con cruz (al norte); racimo de bebes junto a la columna derecha, dos avanzan al centro, uno rezagado a la izquierda
     "miembros": [("bebe", 150, 142, "gatea"), ("bebe", 164, 154, "quieto"), ("bebe", 144, 158, "gatea"), ("bebe", 157, 168, "gatea"),
                  ("bebe", 112, 112, "gatea"), ("bebe", 98, 130, "gatea"), ("bebe", 70, 140, "quieto"),
                  ("monja", 96, 16, "reza")],
     "ruta": None},
    {"nombre": "Procesion", "formacion": "patrulla", "k": 1,   # la unica patrulla de la zona: 2 monaguillos rondan con 3 bebes; 2 bebes emboscados
     # pista: la sombra de las dos columnas del norte tiene un bulto de mas y se oye arrastrar pies; pide pasar por el centro, lejos de ellas
     "miembros": [("monaguillo", 70, 150, "patrulla"), ("monaguillo", 125, 262, "patrulla"),
                  ("bebe", 35, 108, "escondido"), ("bebe", 155, 108, "escondido"),
                  ("bebe", 62, 198, "gatea"), ("bebe", 104, 214, "gatea"), ("bebe", 88, 246, "gatea")],
     "ruta": [(70, 150), (130, 170), (125, 262), (78, 244)]},
    {"nombre": "Corrillo", "formacion": "enjambre", "k": 2,    # junto a la columna derecha: monja rezando, un monaguillo que la cubre y bebes en el hueco entre filas de columnas
     "miembros": [("monja", 118, 122, "reza"), ("monaguillo", 94, 110, "vaiven"),
                  ("bebe", 74, 176, "gatea"), ("bebe", 100, 198, "gatea"),
                  ("bebe", 118, 160, "quieto"), ("bebe", 86, 142, "gatea")],
     "ruta": None},
]
