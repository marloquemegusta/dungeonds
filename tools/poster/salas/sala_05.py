"""Sala 5: Galeria del secreto. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.42, tint=(0.92, 0.88, 0.8))   # polvo
DROP = ['santo_der', 'columna_entera', 'santo', 'columna', 'alambre', 'sacos', 'sacos_b', 'banco_roto']
ADD = [
    ('capullo', 0, 4, 248),
    ('capullo', 0, 44, 248),
    ('sacos', 0, 0, 308),
    ('sacos_b', 0, 64, 312),
    ('cepo', 0, 164, 290),
    ('capullo', 0, 0, 0),
    ('sacos_remate', 0, 144, 352),
    ('sacos_b', 0, 0, 352),
]

