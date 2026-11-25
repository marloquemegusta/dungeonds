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
    out = [("osario_estante", 2, x, 0) for x in (0, 40, 80, 120, 160)]   # muro de nichos de lado a lado tras el cofre
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


# Nave 3 junta dos amenazas por grupo (DESIGN-ARPG.md §10, §12). Sin luz: el miedo es no ver, pero cada escondite tiene su pista.
# Franja libre entre estantes: y 56..190 de cada bloque (pasillo central x 48..160). Piezas altas para esconder: pila de calaveras
# (k0 x168..207, y98..135; k1 x8..47, y98..135); un bebe con los pies ~18 px al norte de su base queda tapado entero.
# Cofre de k2 (x72..136, y44..100) y entrada de k0 (y > 274) sin enemigos.
GRUPOS = [
    {"nombre": "Coro", "formacion": "muralla", "k": 0,   # 3 monaguillos en fila tapan a 3 monjas rezando; 2 bebes emboscados tras la pila de calaveras
     # Emboscada: los dos bebes tras la pila de la derecha; pista = un craneo rueda y repiquetean huesos al pasar cerca.
     "miembros": [("monja", 28, 70, "reza"), ("monja", 66, 62, "reza"), ("monja", 102, 72, "reza"),
                  ("monaguillo", 34, 120, "vaiven"), ("monaguillo", 80, 126, "vaiven"), ("monaguillo", 126, 118, "vaiven"),
                  ("bebe", 180, 113, "escondido"), ("bebe", 195, 116, "escondido"),
                  ("bebe", 100, 168, "gatea"), ("bebe", 52, 178, "quieto")],
     "ruta": None},
    {"nombre": "Tiradores", "formacion": "cruzado", "k": 1,   # dos Ojos en lados opuestos del paso (la pila solo tapa a uno); bebes y monaguillos entre los huesos
     # Emboscada: un bebe tras la pila de la izquierda; pista = su sombra asoma bajo la pila cuando el Ojo barre con la mirada.
     "miembros": [("ojo", 30, 76, "barre"), ("ojo", 180, 150, "barre"),
                  ("monja", 98, 66, "reza"),
                  ("monaguillo", 72, 118, "vaiven"), ("monaguillo", 134, 104, "vaiven"),
                  ("bebe", 27, 118, "escondido"), ("bebe", 138, 182, "quieto"),
                  ("bebe", 62, 172, "gatea"), ("bebe", 112, 160, "gatea")],
     "ruta": None},
    {"nombre": "Carga doble", "formacion": "embestida", "k": 2,   # dos Cireneos pasean ante el cofre con linea recta libre hacia los estantes; monja y monaguillos al norte
     "miembros": [("monja", 28, 90, "reza"),
                  ("monaguillo", 52, 122, "vaiven"), ("monaguillo", 160, 112, "vaiven"),
                  ("cireneo", 68, 164, "pasea"), ("cireneo", 142, 176, "pasea"),
                  ("bebe", 100, 130, "quieto"), ("bebe", 120, 152, "gatea"), ("bebe", 178, 150, "gatea")],
     "ruta": None},
]
