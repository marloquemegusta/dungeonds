"""Sala 14: Galeria de la Monjarana. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.34, tint=(0.7, 0.92, 0.66))   # verde enfermizo
DROP = ['santo', 'santo_der', 'columna_entera']


# Salon de estatuas: santos en hilera regular contra los dos muros, columna entre ellos; el nido de la Monjarana al fondo (k1):
# capullos cada vez mas apretados, colgados del techo del fondo y apoyados en los muros.
def _galeria():
    out = []
    for y in (8, 72, 136, 264, 328):              # k0: hilera de santos pegada a los dos muros (la izquierda libre en la puerta)
        out += [("santo", 0, 4, y), ("santo_der", 0, 164, y)]
    out += [("santo_der", 0, 164, 200)]
    for y in (0, 238, 302):                        # k1: mismos santos de cada lado, fuera de las filas de enemigos
        if y:                                      # arriba a la izquierda esta la Super Monja (su capa pisaba el pedestal)
            out += [("santo", 1, 4, y)]
        out += [("santo_der", 1, 164, y)]
    out += [("columna_entera", 0, 56, 0), ("columna_entera", 0, 112, 0),
            ("columna_entera", 0, 56, 264), ("columna_entera", 0, 112, 264)]
    # nido de la Monjarana: capullos apretados al fondo y mas sueltos hacia la entrada
    out += [("capullo", 1, x, 0) for x in (48, 80, 112)]
    out += [("capullo", 1, 52, 238), ("capullo", 1, 84, 242), ("capullo", 1, 116, 238), ("capullo", 1, 68, 300), ("capullo", 1, 100, 304)]
    out += [("capullo", 1, 56, 60), ("capullo", 1, 112, 60)]
    out += [("capullo", 0, 80, 150), ("capullo", 0, 56, 140)]
    out += [("huesos_monton", 1, 88, 180), ("calaveras_pila", 0, 90, 200)]
    return out


ADD = _galeria()
