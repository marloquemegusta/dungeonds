"""Sala 3: Nave IV. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.4, tint=(0.86, 0.9, 1.0))   # nave
DROP = ['alambre', 'banco_roto', 'banco_volcado', 'banco_entero', 'sacos', 'sacos_b', 'sacos_remate_der', 'columna', 'santo', 'santo_der']

# Nave de iglesia: dos filas de bancos a cada lado del pasillo central (fuera de la franja de enemigos, y 70..228) que
# se rompen sala a sala. Azar con semilla fija: la composicion es estable.
import random
_ANCHO = {"banco_entero": 72, "banco_roto": 64, "banco_volcado": 80}


def _sala():
    rng = random.Random(38)
    suelto = list([('columna', 1, 0, 232), ('sacos', 1, 72, 232), ('sacos', 0, 96, 336), ('sacos_b', 2, 128, 232), ('alambre', 2, 96, 344), ('alambre', 0, 104, 232)])
    out = list(suelto)
    for k in range(3):
        for y in (4, 38, 236, 270, 304, 340):
            for lado in (0, 1):
                if k == 0 and lado == 0 and y > 200:
                    continue                          # escalera de entrada
                r = rng.random()
                if r < 0.2:
                    continue
                pieza = "banco_volcado" if r < 0.2 + 0.3 else "banco_roto" if r < 0.2 + 0.3 + 0.4 else "banco_entero"
                bx = 8 if lado == 0 else 200 - _ANCHO[pieza]
                if any(e[1] == k and e[2] < bx + 80 and bx < e[2] + 72 and e[3] < y + 40 and y < e[3] + 80 for e in suelto):
                    continue                          # lo suelto pisa este banco
                out.append((pieza if lado == 0 else pieza + "~", k, 8 if lado == 0 else 200 - _ANCHO[pieza], y))
    return out


ADD = _sala()


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Guardia", "formacion": "puesto", "k": 0,   # de todo un poco: Ojo al norte, Cireneo en el flanco, monjas rezando; no hay respiro
     "miembros": [("ojo", 104, 86, "quieto"), ("monja", 58, 92, "reza"), ("monja", 150, 90, "reza"),
                  ("cireneo", 52, 150, "pasea"), ("monaguillo", 90, 140, "vaiven"), ("monaguillo", 120, 150, "vaiven"),
                  ("monaguillo", 152, 136, "vaiven"), ("bebe", 60, 204, "gatea"), ("bebe", 100, 210, "gatea"),
                  ("bebe", 140, 202, "quieto"), ("bebe", 170, 178, "gatea")],
     "ruta": None},
    {"nombre": "Cortejo", "formacion": "cruzado", "k": 1,   # dos Ojos cruzados con monaguillos de escudo; sin respiro
     "miembros": [("ojo", 28, 122, "quieto"), ("ojo", 180, 128, "quieto"), ("monja", 60, 90, "reza"),
                  ("monja", 148, 92, "reza"), ("monaguillo", 80, 150, "vaiven"), ("monaguillo", 110, 142, "vaiven"),
                  ("monaguillo", 136, 156, "vaiven"), ("bebe", 50, 196, "gatea"), ("bebe", 90, 206, "gatea"),
                  ("bebe", 130, 200, "quieto"), ("bebe", 160, 212, "gatea"), ("bebe", 170, 178, "gatea")],
     "ruta": None},
    {"nombre": "Asalto", "formacion": "embestida", "k": 2,   # dos Cireneos y un Ojo, monjas al norte y monaguillos de escudo; un bebe emboscado tras el banco roto del NO (pista: cera que cruje)
     "miembros": [("ojo", 182, 112, "quieto"), ("monja", 84, 86, "reza"), ("monja", 128, 84, "reza"),
                  ("cireneo", 50, 132, "pasea"), ("cireneo", 156, 152, "pasea"), ("monaguillo", 88, 168, "vaiven"),
                  ("monaguillo", 118, 160, "vaiven"), ("monaguillo", 138, 188, "vaiven"), ("bebe", 60, 204, "gatea"),
                  ("bebe", 104, 216, "gatea"), ("bebe", 150, 224, "quieto"), ("bebe", 46, 61, "escondido")],
     "ruta": None},
]


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Guardia", "formacion": "puesto", "k": 0,   # Ojo al norte, Cireneo en el flanco; monjas rezando en el hueco de la fila NE y ante el banco NO; sin respiro
     "miembros": [("ojo", 104, 88, "quieto"), ("monja", 160, 64, "reza"), ("monja", 46, 79, "reza"),
                  ("cireneo", 52, 150, "pasea"), ("monaguillo", 90, 140, "vaiven"), ("monaguillo", 120, 150, "vaiven"),
                  ("monaguillo", 152, 136, "vaiven"), ("bebe", 60, 204, "gatea"), ("bebe", 140, 202, "quieto"),
                  ("bebe", 170, 178, "gatea"), ("bebe", 104, 46, "gatea")],
     "ruta": None},
    {"nombre": "Cortejo", "formacion": "cruzado", "k": 1,   # dos Ojos cruzados con monaguillos de escudo; monjas en el hueco de la fila NO y ante el banco NE; sin respiro
     "miembros": [("ojo", 28, 122, "quieto"), ("ojo", 180, 128, "quieto"), ("monja", 46, 64, "reza"),
                  ("monja", 160, 79, "reza"), ("monaguillo", 80, 150, "vaiven"), ("monaguillo", 110, 142, "vaiven"),
                  ("monaguillo", 136, 156, "vaiven"), ("bebe", 50, 196, "gatea"), ("bebe", 130, 200, "quieto"),
                  ("bebe", 160, 212, "gatea"), ("bebe", 170, 178, "gatea"), ("bebe", 104, 270, "gatea")],
     "ruta": None},
    {"nombre": "Asalto", "formacion": "embestida", "k": 2,   # 2 Cireneos y 1 Ojo, monjas rezando al norte; un bebe emboscado tras el banco roto del NO (pista: cera que cruje; se prefiere a la del banco del sur porque despierta al grupo cuando el heroe esta ya cerca)
     "miembros": [("ojo", 182, 112, "quieto"), ("monja", 46, 34, "reza"), ("monja", 150, 79, "reza"),
                  ("cireneo", 50, 132, "pasea"), ("cireneo", 156, 152, "pasea"), ("monaguillo", 88, 168, "vaiven"),
                  ("monaguillo", 118, 160, "vaiven"), ("monaguillo", 138, 188, "vaiven"), ("bebe", 60, 204, "gatea"),
                  ("bebe", 104, 216, "gatea"), ("bebe", 150, 224, "quieto"), ("bebe", 46, 61, "escondido")],
     "ruta": None},
]
