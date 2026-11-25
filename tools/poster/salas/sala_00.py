"""Sala 0: Nave I. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.55, tint=(0.86, 0.9, 1.0))   # nave: gris azulado de vidriera
DROP = ['alambre', 'banco_roto', 'banco_volcado', 'banco_entero', 'sacos', 'sacos_b', 'sacos_remate_der', 'columna', 'santo', 'santo_der']

# Nave de iglesia: dos filas de bancos a cada lado del pasillo central (fuera de la franja de enemigos, y 70..228) que
# se rompen sala a sala. Azar con semilla fija: la composicion es estable.
import random
_ANCHO = {"banco_entero": 72, "banco_roto": 64, "banco_volcado": 80}


def _sala():
    rng = random.Random(5)
    suelto = list([])
    out = list(suelto)
    for k in range(3):
        for y in (4, 38, 236, 270, 304, 340):
            for lado in (0, 1):
                if k == 0 and lado == 0 and y > 200:
                    continue                          # escalera de entrada
                r = rng.random()
                if r < 0:
                    continue
                pieza = "banco_volcado" if r < 0 + 0 else "banco_roto" if r < 0 + 0 + 0 else "banco_entero"
                bx = 8 if lado == 0 else 200 - _ANCHO[pieza]
                if any(e[1] == k and e[2] < bx + 80 and bx < e[2] + 72 and e[3] < y + 40 and y < e[3] + 80 for e in suelto):
                    continue                          # lo suelto pisa este banco
                out.append((pieza if lado == 0 else pieza + "~", k, 8 if lado == 0 else 200 - _ANCHO[pieza], y))
    return out


ADD = _sala()


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Rebano", "formacion": "enjambre", "k": 0,   # 6 bebes dan la cara entre los bancos; la monja reza al norte, tras ellos (mata primero a la que cura)
     "miembros": [("bebe", 62, 170, "gatea"), ("bebe", 88, 190, "gatea"), ("bebe", 118, 168, "gatea"),
                  ("bebe", 140, 196, "quieto"), ("bebe", 76, 214, "gatea"), ("bebe", 108, 222, "gatea"),
                  ("monja", 100, 100, "reza")],
     "ruta": None},
    {"nombre": "Corrillo", "formacion": "enjambre", "k": 1,   # primera monja con monaguillo cerca: el monaguillo se interpone; bebes de ruido
     "miembros": [("monja", 150, 96, "reza"), ("monaguillo", 118, 132, "vaiven"), ("bebe", 60, 152, "gatea"),
                  ("bebe", 84, 196, "gatea"), ("bebe", 132, 186, "quieto"), ("bebe", 165, 212, "gatea")],
     "ruta": None},
    {"nombre": "Procesion", "formacion": "puesto", "k": 2,   # 2 monaguillos al frente, bebes detras; ensena el golpe de remate contra monaguillos
     "miembros": [("monaguillo", 70, 128, "vaiven"), ("monaguillo", 138, 152, "vaiven"), ("bebe", 48, 180, "gatea"),
                  ("bebe", 96, 170, "gatea"), ("bebe", 118, 205, "quieto"), ("bebe", 160, 200, "gatea"),
                  ("bebe", 80, 226, "gatea")],
     "ruta": None},
]


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Rebano", "formacion": "enjambre", "k": 0,   # bebes entre los bancos y en el pasillo, la monja reza ante el banco del NO; mata primero a la que cura
     "miembros": [("bebe", 64, 160, "gatea"), ("bebe", 96, 190, "gatea"), ("bebe", 134, 168, "gatea"),
                  ("bebe", 152, 214, "quieto"), ("bebe", 80, 222, "gatea"), ("bebe", 104, 50, "gatea"),
                  ("monja", 46, 79, "reza")],
     "ruta": None},
    {"nombre": "Corrillo", "formacion": "enjambre", "k": 1,   # monja rezando ante el banco del NE con monaguillo cerca (se interpone); un bebe suelto en el pasillo sur
     "miembros": [("monja", 160, 79, "reza"), ("monaguillo", 118, 110, "vaiven"), ("bebe", 62, 150, "gatea"),
                  ("bebe", 112, 196, "gatea"), ("bebe", 150, 170, "quieto"), ("bebe", 104, 262, "gatea")],
     "ruta": None},
    {"nombre": "Procesion", "formacion": "procesion", "k": 2,   # columna irregular por el pasillo central: monaguillos delante rondan, bebes detras; ensena el remate
     "miembros": [("monaguillo", 98, 100, "patrulla"), ("monaguillo", 112, 128, "patrulla"), ("bebe", 92, 160, "gatea"),
                  ("bebe", 112, 184, "gatea"), ("bebe", 98, 208, "quieto"), ("bebe", 114, 232, "gatea"),
                  ("bebe", 102, 262, "gatea")],
     "ruta": [(96, 100), (112, 128), (98, 160), (112, 128)]},
]
