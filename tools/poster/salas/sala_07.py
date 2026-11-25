"""Sala 7: Claustro alto. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
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
    out += [("banco_roto", 0, 72, 336), ("lapida_pie", 1, 88, 332)]
    return out


NB = 3
ADD = _claustro()


# Nave 2 presenta al Ojo y al Cireneo (DESIGN-ARPG.md §10, §12). Columnas: visibles en x=18..52 y x=138..172, base en y=127 e y=287.
# Solo hay una puerta (izquierda, y 206..244 del bloque 0): la entrada. El cofre esta al fondo del bloque 2 (x 82..117, y 66..89).
GRUPOS = [
    {"nombre": "Puesto", "formacion": "puesto", "k": 0,       # un Ojo al fondo barre el claustro: hay que cruzar bajo su mirada a por los bebes
     "miembros": [("ojo", 98, 66, "barre"), ("monaguillo", 64, 104, "vaiven"), ("monaguillo", 122, 98, "vaiven"),
                  ("bebe", 90, 140, "gatea"), ("bebe", 116, 153, "gatea"), ("bebe", 76, 126, "quieto"), ("bebe", 124, 144, "gatea")],
     "ruta": None},
    {"nombre": "Carga", "formacion": "embestida", "k": 1,     # el Cireneo anda con linea recta libre hacia la columna baja derecha: llevarlo contra ella; la monja reza al fondo
     "miembros": [("monja", 96, 52, "reza"), ("monaguillo", 68, 92, "vaiven"), ("monaguillo", 126, 84, "vaiven"),
                  ("cireneo", 112, 232, "pasea"), ("bebe", 70, 205, "gatea"), ("bebe", 96, 188, "gatea"),
                  ("bebe", 84, 228, "gatea"), ("bebe", 100, 160, "quieto")],
     "ruta": None},
    {"nombre": "Guardia de la monja", "formacion": "emboscada", "k": 2,   # dos monjas rezan ante el cofre; 2 bebes emboscados tras la columna norte derecha
     # pista: la vela de la monja titila y se oye cera cuando se pasa junto a la columna; ir por el centro los despierta, ir por el borde izquierdo no
     "miembros": [("monja", 60, 58, "reza"), ("monja", 62, 104, "reza"),
                  ("monaguillo", 70, 150, "vaiven"), ("monaguillo", 122, 146, "vaiven"),
                  ("bebe", 150, 106, "escondido"), ("bebe", 160, 111, "escondido"),
                  ("bebe", 82, 192, "gatea"), ("bebe", 112, 208, "gatea")],
     "ruta": None},
]
