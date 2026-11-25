"""Sala 10: Capilla del parroco. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.46, tint=(1.0, 0.82, 0.62))   # ambar de vela
DROP = ['banco_entero', 'vela']
# Capilla: altar al fondo entre dos candelabros de pie, relicarios y exvotos colgados del muro del fondo, y dos filas de
# reclinatorios (uno a cada lado del pasillo central) mirando al altar. Sin velas: con luz "techo" dejan la luz sin radio.
ADD = [("altar", 0, 96, 6), ("candelabro_pie", 0, 56, 6), ("candelabro_pie", 0, 120, 6)]
COLGADOS = [("exvoto", 24, 24), ("exvoto", 184, 24)]   # exvotos colgados del muro norte (antes de pie en el suelo)
ADD += [("reclinatorio", 0, x, y) for y in (248, 296) for x in (8, 164)]



# Encuentro especial «Parroquia» (DESIGN-ARPG.md §7, G_PARROQUIA: 7 Monjas, 4 Monaguillos, 1 Parroco), un solo grupo en un bloque.
# El altar (x104..119, y14..39) y el cofre (x90..125, y66..89) quedan al norte; relicarios en x24..63 y x152..191 (y20..71); reclinatorios al sur
# (entrada, y > 274, vacia). Las monjas rezan en dos corros a los lados del cofre; el Parroco, de pie ante el altar; la Muralla de 4 monaguillos
# cierra el centro dejando libres los dos flancos (x < 45 y x > 175): se llega a las monjas rodeando o con Glifo.
GRUPOS = [
    {"nombre": "Parroquia", "formacion": "muralla", "k": 0,   # pide: matar a las monjas que curan, rodeando la Muralla, y no usar el Rayo contra el Parroco
     "miembros": [("monja", 26, 106, "reza"), ("monja", 52, 90, "reza"), ("monja", 40, 130, "reza"), ("monja", 68, 112, "reza"),
                  ("monja", 144, 108, "reza"), ("monja", 168, 94, "reza"), ("monja", 150, 132, "reza"),
                  ("parroco", 108, 56, "quieto"),
                  ("monaguillo", 58, 164, "vaiven"), ("monaguillo", 94, 172, "vaiven"),
                  ("monaguillo", 128, 162, "vaiven"), ("monaguillo", 162, 170, "vaiven")],
     "ruta": None},
]
