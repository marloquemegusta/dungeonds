"""Sala 11: Galeria de la Misa. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.46, tint=(1.0, 0.82, 0.62))   # ambar de vela
DROP = ['banco_entero', 'vela']
# Nave en miniatura: tres filas de reclinatorios a cada lado del pasillo en el tramo de entrada y, al fondo (k1),
# el altar entre candelabros con exvotos en los muros. La puerta derecha del tramo 0 (y 206..244) queda libre.
ADD = [("altar", 1, 96, 6), ("candelabro_pie", 1, 56, 6), ("candelabro_pie", 1, 120, 6),
       ("exvoto", 1, 4, 4), ("exvoto", 1, 164, 4)]
ADD += [("reclinatorio", 0, 8, y) for y in (60, 120, 180, 248, 308)]
ADD += [("reclinatorio", 0, 152, y) for y in (60, 120, 308)]
ADD += [("reclinatorio", 1, x, y) for y in (240, 300) for x in (8, 152)]


# La Misa (§7, especial en k1; k0 es el pasillo de entrada, sin enemigos): composicion de G_MISA = 4 Monjas, 3 Monaguillos,
# 2 Parrocos, 2 Super Monjas. Un solo grupo: todo despierta junto (radio de aviso comun a proposito).
GRUPOS = [
    {"nombre": "La Misa", "formacion": "puesto", "k": 1,   # ofician ante el altar, rezan los fieles; pide: matar a las que curan sin perder de vista a las acechantes
     "miembros": [("parroco", 90, 66, "quieto"), ("parroco", 131, 62, "quieto"),          # parrocos de pie ante el altar
                  ("monaguillo", 76, 124, "vaiven"), ("monaguillo", 142, 164, "vaiven"), ("monaguillo", 106, 204, "vaiven"),   # acolitos sueltos entre el altar y las monjas
                  ("monja", 29, 301, "reza"), ("monja", 178, 304, "reza"),                  # arrodilladas en los reclinatorios mas cercanos al altar (k1), dos filas irregulares
                  ("monja", 36, 366, "reza"), ("monja", 170, 364, "reza"),
                  # Super Monjas al acecho: la pista es el rastro de cera derretida junto a los relicarios; apenas asoman
                  ("smonja", 44, 47, "escondido"), ("smonja", 171, 46, "escondido")],
     "ruta": None},
]
