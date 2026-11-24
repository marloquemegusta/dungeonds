"""Sala 12: Galeria del prisionero. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.36, tint=(0.72, 0.9, 0.74))   # verde de celda
DROP = ['santo_der', 'columna_entera', 'santo', 'columna', 'alambre', 'sacos', 'sacos_b', 'banco_roto']
ADD = [
    ('capullo', 0, 20, 8),
    ('capullo', 0, 150, 8),
    ('cepo', 0, 0, 290),
    ('alambre', 0, 0, 346),
    ('alambre', 0, 32, 346),
    ('cepo', 0, 144, 290),
    ('alambre', 0, 144, 346),
    ('alambre', 0, 176, 346),
    ('capullo', 1, 20, 296),
    ('alambre', 1, 0, 346),
    ('alambre', 1, 32, 346),
    ('capullo', 1, 168, 296),
    ('alambre', 1, 144, 346),
    ('alambre', 1, 176, 346),
    ('cepo', 1, 4, 10),
    ('cepo', 1, 140, 10),
]

