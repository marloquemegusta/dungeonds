"""Sala 9: Osario. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.34, tint=(0.8, 0.86, 1.0))   # penumbra fria
DROP = ['alambre', 'banco_roto', 'banco_volcado', 'sacos', 'sacos_b', 'sacos_remate_der']


# Una sala de verdad: los dos muros forrados de estanterias de nichos de perfil (osario_lado; «~» = espejo para el muro
# izquierdo) en tramos continuos que solo se abren donde salen los enemigos (filas de y 70..228 de cada tramo) y en las puertas;
# al fondo (k2) un muro de nichos de frente tras el cofre. Calaveras y huesos solo de remate, al pie de los estantes.
def _osario():
    out = [("osario_estante", 2, x, 0) for x in (4, 52, 100, 148)]   # muro de nichos tras el cofre: cada 48 px (los props no comparten tiles, sombra incluida)
    for k in range(3):
        # estantes pegados cada 48 px (los props no comparten tiles); su pie (y+34..y+48) queda fuera de las filas de enemigos
        for y in ((192, 240, 288, 336) if k == 2 else (0, 192, 240, 288, 336)):
            if not (k == 0 and y == 192):                  # puerta derecha del tramo 0
                out.append(("osario_lado", k, 160, y))
            if not (k == 1 and y == 192):                  # puerta izquierda del tramo 1
                out.append(("osario_lado~", k, 0, y))
    out += [("calaveras_pila", 2, 36, 30), ("calaveras_pila", 2, 132, 30),
            ("calaveras_pila", 1, 4, 96), ("huesos_monton", 1, 176, 160), ("calaveras_pila", 0, 172, 96),
            ("huesos_monton", 0, 40, 300), ("calaveras_pila", 0, 144, 344), ("huesos_monton", 2, 140, 330)]
    return out


ADD = _osario()
