"""Sala 4: Galeria del cofre. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.45, tint=(0.92, 0.88, 0.8))   # polvo
DROP = ['santo_der', 'columna_entera', 'santo', 'columna', 'alambre', 'sacos', 'sacos_b', 'banco_roto']


# Almacen del Tribunal: los cepos en fila contra el muro izquierdo (pegados, 48 px de paso), los sacos apilados en tramos
# continuos contra el derecho (salvo la puerta), el cofre al fondo entre la pila de sacos y el primer cepo; centro y franja de
# enemigos (y 70..228) libres.
def _almacen():
    out = [("cepo", 0, 0, y) for y in (0, 228, 276, 324)]
    out += [("sacos_b", 0, 144, 0), ("sacos", 0, 144, 16)]            # pila del fondo, sobre la puerta
    y = 248                                                            # bajo la puerta derecha (y 206..244)
    for p in ("sacos", "sacos_b", "sacos", "sacos_b", "sacos", "sacos_b"):
        out.append((p, 0, 144, y))
        y += 24 if p == "sacos" else 16
    return out


ADD = _almacen()


# La puerta (derecha, y 206..244) es la entrada; el cofre esta al fondo (x 90..125, y 66..89), reservado x 72..136, y 44..100.
GRUPOS = [
    {"nombre": "Rebano", "formacion": "enjambre", "k": 0,      # la monja reza ante el cofre, racimo de 3 bebes al oeste, dos que avanzan al cofre y uno rezagado a la derecha: matar primero a la que cura
     "miembros": [("monja", 60, 84, "reza"),
                  ("bebe", 40, 140, "gatea"), ("bebe", 56, 154, "quieto"), ("bebe", 36, 166, "gatea"),
                  ("bebe", 98, 122, "gatea"), ("bebe", 124, 144, "gatea"), ("bebe", 152, 126, "quieto")],
     "ruta": None},
]
