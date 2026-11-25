"""Sala 1: Nave II. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.5, tint=(0.86, 0.9, 1.0))   # nave
DROP = ['alambre', 'banco_roto', 'banco_volcado', 'banco_entero', 'sacos', 'sacos_b', 'sacos_remate_der', 'columna', 'santo', 'santo_der']

# Nave de iglesia: dos filas de bancos a cada lado del pasillo central (fuera de la franja de enemigos, y 70..228) que
# se rompen sala a sala. Azar con semilla fija: la composicion es estable.
import random
_ANCHO = {"banco_entero": 72, "banco_roto": 64, "banco_volcado": 80}


def _sala():
    rng = random.Random(16)
    suelto = list([('sacos_b', 0, 72, 352)])
    out = list(suelto)
    for k in range(3):
        for y in (4, 38, 236, 270, 304, 340):
            for lado in (0, 1):
                if k == 0 and lado == 0 and y > 200:
                    continue                          # escalera de entrada
                r = rng.random()
                if r < 0.05:
                    continue
                pieza = "banco_volcado" if r < 0.05 + 0 else "banco_roto" if r < 0.05 + 0 + 0.25 else "banco_entero"
                bx = 8 if lado == 0 else 200 - _ANCHO[pieza]
                if any(e[1] == k and e[2] < bx + 80 and bx < e[2] + 72 and e[3] < y + 40 and y < e[3] + 80 for e in suelto):
                    continue                          # lo suelto pisa este banco
                out.append((pieza if lado == 0 else pieza + "~", k, 8 if lado == 0 else 200 - _ANCHO[pieza], y))
    return out


ADD = _sala()


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Puesto", "formacion": "puesto", "k": 0,   # primer Ojo al fondo a la derecha dominando el pasillo; monaguillos y bebes obligan a acercarse bajo fuego
     "miembros": [("ojo", 150, 92, "quieto"), ("monaguillo", 80, 140, "vaiven"), ("monaguillo", 130, 152, "vaiven"),
                  ("bebe", 60, 190, "gatea"), ("bebe", 100, 200, "gatea"), ("bebe", 150, 205, "quieto"),
                  ("bebe", 120, 172, "gatea")],
     "ruta": None},
    {"nombre": "Carga", "formacion": "embestida", "k": 1,   # primer Cireneo con linea libre por el pasillo; la monja reza al norte; esquivar la embestida
     "miembros": [("cireneo", 104, 102, "pasea"), ("monja", 45, 90, "reza"), ("monaguillo", 80, 150, "vaiven"),
                  ("monaguillo", 132, 160, "vaiven"), ("bebe", 60, 192, "gatea"), ("bebe", 96, 208, "gatea"),
                  ("bebe", 140, 198, "quieto"), ("bebe", 172, 172, "gatea")],
     "ruta": None},
    {"nombre": "Guardia de la monja", "formacion": "muralla", "k": 2,   # dos monjas rezando tras dos monaguillos: el Rayo no pasa, rodear o Glifo
     "miembros": [("monja", 70, 90, "reza"), ("monja", 135, 92, "reza"), ("monaguillo", 78, 138, "vaiven"),
                  ("monaguillo", 128, 146, "vaiven"), ("bebe", 50, 190, "gatea"), ("bebe", 94, 200, "gatea"),
                  ("bebe", 150, 192, "quieto"), ("bebe", 112, 224, "gatea")],
     "ruta": None},
]


# Encuentros colocados a mano (DESIGN-ARPG.md 12). Banda libre entre bancos: y 72..235 de cada bloque.
GRUPOS = [
    {"nombre": "Puesto", "formacion": "puesto", "k": 0,   # primer Ojo al fondo a la derecha dominando el pasillo; un bebe gatea entre los bancos del norte
     "miembros": [("ojo", 150, 92, "quieto"), ("monaguillo", 80, 140, "vaiven"), ("monaguillo", 130, 152, "vaiven"),
                  ("bebe", 62, 186, "gatea"), ("bebe", 104, 208, "gatea"), ("bebe", 150, 200, "quieto"),
                  ("bebe", 104, 50, "gatea")],
     "ruta": None},
    {"nombre": "Carga", "formacion": "embestida", "k": 1,   # primer Cireneo con linea libre; la monja reza en el hueco de la fila del NO; esquivar la embestida
     "miembros": [("cireneo", 104, 102, "pasea"), ("monja", 46, 34, "reza"), ("monaguillo", 80, 150, "vaiven"),
                  ("monaguillo", 132, 160, "vaiven"), ("bebe", 60, 192, "gatea"), ("bebe", 140, 198, "quieto"),
                  ("bebe", 172, 172, "gatea"), ("bebe", 104, 258, "gatea")],
     "ruta": None},
    {"nombre": "Guardia de la monja", "formacion": "muralla", "k": 2,   # monjas rezando en la fila (hueco NO y banco NE) tras dos monaguillos: el Rayo no pasa, rodear o Glifo
     "miembros": [("monja", 46, 34, "reza"), ("monja", 160, 79, "reza"), ("monaguillo", 78, 138, "vaiven"),
                  ("monaguillo", 128, 146, "vaiven"), ("bebe", 50, 190, "gatea"), ("bebe", 94, 204, "gatea"),
                  ("bebe", 150, 192, "quieto"), ("bebe", 104, 52, "gatea")],
     "ruta": None},
]
