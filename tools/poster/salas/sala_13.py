"""Sala 13: Capilla con llave. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.46, tint=(1.0, 0.82, 0.62))   # ambar de vela
DROP = ['vela', 'altar', 'relicario']
# Capilla de la llave: el relicario (retablo de 48 de ancho) centrado contra el muro del fondo, con un altar de servicio a cada
# lado; el cofre queda bajo el retablo. El relicario va en EXTRA porque su pie cae sobre el paso
# reservado del cofre. Reclinatorios en la nave, mirando al fondo; la puerta izquierda queda libre.
ADD = [("altar", 0, 40, 10), ("altar", 0, 148, 10)]
ADD += [("reclinatorio", 0, 164, y) for y in (252, 292)] + [("reclinatorio", 0, 56, y) for y in (252, 292)]
EXTRA = [("relicario", 0, 80, 0)]
