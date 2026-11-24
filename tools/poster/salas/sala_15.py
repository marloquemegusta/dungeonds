"""Sala 15: Cripta. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.4, tint=(1.0, 0.7, 0.55))   # rojo de brasa
DROP = ['columna_entera', 'santo', 'santo_der']
EXTRA = []   # sin hoguera: no encaja en una cripta (la luz la dan los braseros; no hay pieza de antorcha de pared)


# Cripta: arena libre en el centro; sarcofagos de lado alineados contra los dos muros (sarcofago_lado, «~» = espejo),
# lapidas de pie entre ellos, braseros en las esquinas de la entrada y flanqueandola la entrada (hacen de antorchas),
# y un sarcofago grande al fondo, entre los escoltas, tras el jefe.
def _cripta():
    out = [("sarcofago", 0, 68, 0)]
    for y in (80, 112, 192, 224, 304):
        out += [("sarcofago_lado~", 0, 0, y), ("sarcofago_lado", 0, 160, y)]
    for y in (144, 256):
        out += [("lapida_pie", 0, 4, y), ("lapida_pie", 0, 172, y)]
    out += [ ("brasero", 0, 14, 336), ("brasero", 0, 154, 336),
           
            ("calaveras_pila", 0, 44, 120), ("huesos_monton", 0, 142, 300)]
    return out


ADD = _cripta()
