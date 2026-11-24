"""Sala 8: Enfermeria. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.48, tint=(0.96, 0.92, 0.8))   # amarillo enfermo
DROP = ['banco_roto', 'banco_volcado', 'alambre', 'sacos', 'sacos_b', 'sacos_remate', 'sacos_remate_der']


# Enfermeria de hospital: filas de catres con la cabecera contra cada muro (catre a la izquierda, «catre~» en espejo a la
# derecha), pegados cada 48 px y fuera de la franja de enemigos (y 70..228); pasillo central libre. Biombos que separan
# camas, palanganas y candelabros de pie junto a las camas; exvotos colgados tras el fondo. Sin velas (la luz de techo
# no admite fuentes puntuales).
def _enfermeria():
    out = []
    for k in range(3):
        izq = [16, 232, 280]      # camas del muro izquierdo
        der = [16, 232, 280]
        if k == 0:
            der = [16, 248, 296]   # puerta derecha del tramo 0 (y 206..244)
        if k == 2:
            izq = [16, 248, 296]   # puerta izquierda del tramo 2
        out += [("catre", k, -8, y) for y in izq] + [("catre~", k, 144, y) for y in der]
        # ultimo hueco de cada muro: biombo (alterna lados) o cama
        if k != 2:
            out.append(("biombo", k, -8, 328) if k == 0 else ("biombo~", k, 152, 328))
            out.append(("catre~", k, 144, 328) if k == 0 else ("catre", k, -8, 328))
        # a los pies de las camas
        out += [("palangana", k, 72, izq[1] + 4), ("candelabro_pie", k, 96, 236)]
    out += [("candelabro_pie", 0, 64, 20), ("candelabro_pie", 1, 104, 12)]
    out += [("exvoto", 2, x, 4) for x in (64, 112)]
    return out


ADD = _enfermeria()
