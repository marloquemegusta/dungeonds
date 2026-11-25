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


# Nave 3 junta dos amenazas (DESIGN-ARPG.md §10, §12). La puerta izquierda (y 206..244 del bloque 0) es la entrada; cepos y alambre
# son el contexto del Cireneo (se aturde al chocar). El cofre esta al fondo del bloque 1 (x 90..125, y 66..89).
GRUPOS = [
    {"nombre": "Carga doble", "formacion": "embestida", "k": 0,   # dos Cireneos con linea recta libre hacia los cepos del sur: esquivar para que choquen
     "miembros": [("monja", 104, 40, "reza"), ("monaguillo", 84, 80, "vaiven"), ("monaguillo", 128, 76, "vaiven"),
                  ("cireneo", 140, 222, "pasea"), ("cireneo", 100, 148, "pasea"),
                  ("bebe", 70, 118, "gatea"), ("bebe", 118, 106, "gatea"), ("bebe", 90, 170, "quieto")],
     "ruta": None},
    {"nombre": "Tiradores", "formacion": "cruzado", "k": 1,      # dos Ojos en las esquinas de los cepos cruzan fuego sobre el pasillo del cofre; la monja reza tras el cofre
     "miembros": [("ojo", 30, 88, "barre"), ("ojo", 178, 92, "barre"), ("monja", 104, 30, "reza"),
                  ("monaguillo", 68, 76, "vaiven"), ("monaguillo", 146, 70, "vaiven"),
                  ("bebe", 80, 170, "gatea"), ("bebe", 112, 150, "gatea"), ("bebe", 142, 186, "quieto"), ("bebe", 70, 216, "gatea")],
     "ruta": None},
]
