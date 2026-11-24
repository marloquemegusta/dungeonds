"""Sala 10: Capilla del parroco. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.46, tint=(1.0, 0.82, 0.62))   # ambar de vela
DROP = ['banco_entero', 'vela']
# Capilla: altar al fondo entre dos candelabros de pie, relicarios y exvotos en los muros del fondo, y dos filas de
# reclinatorios (uno a cada lado del pasillo central) mirando al altar. Sin velas: con luz "techo" dejan la luz sin radio.
ADD = [("altar", 0, 96, 6), ("candelabro_pie", 0, 56, 6), ("candelabro_pie", 0, 120, 6),
       ("exvoto", 0, 4, 4), ("exvoto", 0, 164, 4)]
ADD += [("reclinatorio", 0, x, y) for y in (248, 306) for x in (8, 152)]
