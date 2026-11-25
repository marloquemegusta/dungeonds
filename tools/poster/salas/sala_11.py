"""Sala 11: Galeria de la Misa. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.46, tint=(1.0, 0.82, 0.62))   # ambar de vela
DROP = ['banco_entero', 'vela', 'relicario']   # relicario (v2) ocupaba las esquinas y vetaba exvotos y candelabros
# Nave en miniatura: dos columnas de reclinatorios contra los muros (paso de 40 px) con pasillo central y, al fondo (k1), el altar
# entre candelabros con dos exvotos colgados del muro norte. La puerta derecha del tramo 0 (y 206..244) queda libre.
ADD = [("altar", 1, 96, 6), ("candelabro_pie", 1, 56, 6), ("candelabro_pie", 1, 120, 6)]
COLGADOS = [("exvoto", 81, 24), ("exvoto", 176, 24)]
ADD += [("reclinatorio", 0, x, y) for y in (44, 84, 124, 164, 256, 296, 336) for x in (8, 164) if not (x > 100 and 190 < y < 250)]
ADD += [("reclinatorio", 1, x, y) for y in (240, 290) for x in (8, 164)]
