"""Sala 2: Nave III. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.45, tint=(0.86, 0.9, 1.0))   # nave
DROP = ['alambre', 'banco_roto', 'banco_volcado', 'banco_entero', 'sacos', 'sacos_b', 'sacos_remate_der', 'columna', 'santo', 'santo_der']

# Nave de iglesia: dos filas de bancos a cada lado del pasillo central (fuera de la franja de enemigos, y 70..228) que
# se rompen sala a sala. Azar con semilla fija: la composicion es estable.
import random
_ANCHO = {"banco_entero": 72, "banco_roto": 64, "banco_volcado": 80}


def _sala():
    rng = random.Random(27)
    suelto = list([('columna', 2, 0, 296), ('sacos', 1, 128, 248), ('sacos_b', 0, 80, 336)])
    out = list(suelto)
    for k in range(3):
        for y in (4, 38, 236, 270, 304, 340):
            for lado in (0, 1):
                if k == 0 and lado == 0 and y > 200:
                    continue                          # escalera de entrada
                r = rng.random()
                if r < 0.15:
                    continue
                pieza = "banco_volcado" if r < 0.15 + 0.12 else "banco_roto" if r < 0.15 + 0.12 + 0.4 else "banco_entero"
                bx = 8 if lado == 0 else 200 - _ANCHO[pieza]
                if any(e[1] == k and e[2] < bx + 80 and bx < e[2] + 72 and e[3] < y + 40 and y < e[3] + 80 for e in suelto):
                    continue                          # lo suelto pisa este banco
                out.append((pieza if lado == 0 else pieza + "~", k, 8 if lado == 0 else 200 - _ANCHO[pieza], y))
    return out


ADD = _sala()


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Coro", "formacion": "muralla", "k": 0,   # tres monjas tras tres monaguillos y bebes; prioriza a las que curan
     "miembros": [("monja", 60, 88, "reza"), ("monja", 104, 84, "reza"), ("monja", 148, 92, "reza"),
                  ("monaguillo", 70, 136, "vaiven"), ("monaguillo", 110, 128, "vaiven"), ("monaguillo", 146, 140, "vaiven"),
                  ("bebe", 48, 185, "gatea"), ("bebe", 90, 200, "gatea"), ("bebe", 128, 190, "quieto"),
                  ("bebe", 160, 215, "gatea")],
     "ruta": None},
    {"nombre": "Tiradores", "formacion": "cruzado", "k": 1,   # dos Ojos en lados opuestos: ningun banco tapa de los dos; los bebes distraen
     "miembros": [("ojo", 30, 104, "quieto"), ("ojo", 178, 108, "quieto"), ("monja", 104, 82, "reza"),
                  ("monaguillo", 82, 150, "vaiven"), ("monaguillo", 130, 160, "vaiven"), ("bebe", 60, 200, "gatea"),
                  ("bebe", 100, 186, "gatea"), ("bebe", 150, 206, "quieto"), ("bebe", 118, 226, "gatea")],
     "ruta": None},
    {"nombre": "Carga doble", "formacion": "embestida", "k": 2,   # dos Cireneos a los lados del pasillo: llevarlos a un lado y que choquen
     "miembros": [("cireneo", 58, 112, "pasea"), ("cireneo", 150, 122, "pasea"), ("monja", 104, 84, "reza"),
                  ("monaguillo", 92, 160, "vaiven"), ("monaguillo", 122, 172, "vaiven"), ("bebe", 70, 200, "gatea"),
                  ("bebe", 110, 216, "gatea"), ("bebe", 160, 196, "quieto")],
     "ruta": None},
]


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Coro", "formacion": "muralla", "k": 0,   # tres monjas rezando ante los bancos del norte y el pasillo, tras tres monaguillos; prioriza a las que curan
     "miembros": [("monja", 46, 79, "reza"), ("monja", 104, 34, "reza"), ("monja", 160, 79, "reza"),
                  ("monaguillo", 70, 136, "vaiven"), ("monaguillo", 110, 128, "vaiven"), ("monaguillo", 146, 140, "vaiven"),
                  ("bebe", 32, 176, "gatea"), ("bebe", 90, 200, "gatea"), ("bebe", 132, 190, "quieto"),
                  ("bebe", 160, 215, "gatea")],
     "ruta": None},
    {"nombre": "Tiradores", "formacion": "cruzado", "k": 1,   # dos Ojos en lados opuestos: ningun banco tapa de los dos; la monja reza en el pasillo norte; un bebe suelto al sur
     "miembros": [("ojo", 30, 104, "quieto"), ("ojo", 178, 108, "quieto"), ("monja", 104, 36, "reza"),
                  ("monaguillo", 82, 150, "vaiven"), ("monaguillo", 130, 160, "vaiven"), ("bebe", 60, 200, "gatea"),
                  ("bebe", 150, 206, "quieto"), ("bebe", 118, 226, "gatea"), ("bebe", 104, 264, "gatea")],
     "ruta": None},
    {"nombre": "Carga doble", "formacion": "embestida", "k": 2,   # dos Cireneos a los lados del pasillo: llevarlos a un lado y que choquen; monja en el hueco de la fila del NE
     "miembros": [("cireneo", 58, 112, "pasea"), ("cireneo", 150, 122, "pasea"), ("monja", 160, 34, "reza"),
                  ("monaguillo", 92, 160, "vaiven"), ("monaguillo", 122, 172, "vaiven"), ("bebe", 70, 200, "gatea"),
                  ("bebe", 160, 196, "quieto"), ("bebe", 106, 266, "gatea")],
     "ruta": None},
]
