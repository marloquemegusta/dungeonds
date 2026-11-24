"""Sala 2: Nave III. Composicion de props del poster v3 (la lee poster_arpg_v3.py).
AMB: juego de luz de la sala ("techo" salvo los claustros, que usan dia/noche). LUZ: tono e intensidad preliminares (no tocar:
la luz se cierra sala a sala despues). DROP: piezas de la composicion de v2 (gen_ambientes_arpg.py) que se quitan.
ADD: (pieza, k, x, y) con x, y locales del bloque k (0 = tramo de entrada); pieza «nombre~» = la misma en espejo.
EXTRA: piezas que pueden ir sobre los pasos reservados (fuentes de luz dibujadas)."""
AMB = "techo"
LUZ = dict(L=0.45, tint=(0.86, 0.9, 1.0))   # nave
DROP = ['alambre', 'banco_roto', 'banco_volcado', 'banco_entero', 'sacos', 'sacos_b', 'sacos_remate_der', 'columna', 'santo', 'santo_der']

# Nave de iglesia: dos filas de bancos a cada lado del pasillo central (fuera de la franja de enemigos, y 70..228) que
# se rompen sala a sala. Azar con semilla fija: la composicion es estable.
import random
_ANCHO = {"banco_entero": 72, "banco_roto": 64, "banco_volcado": 80}


def _sala():
    rng = random.Random(27)
    suelto = list([('columna', 2, 0, 296), ('sacos', 1, 128, 248), ('sacos_b', 0, 80, 336)])
    out = list(suelto)
    for k in range(3):
        for y in (4, 38, 236, 270, 304, 340):
            for lado in (0, 1):
                if k == 0 and lado == 0 and y > 200:
                    continue                          # escalera de entrada
                r = rng.random()
                if r < 0.15:
                    continue
                pieza = "banco_volcado" if r < 0.15 + 0.12 else "banco_roto" if r < 0.15 + 0.12 + 0.4 else "banco_entero"
                bx = 8 if lado == 0 else 200 - _ANCHO[pieza]
                if any(e[1] == k and e[2] < bx + 80 and bx < e[2] + 72 and e[3] < y + 40 and y < e[3] + 80 for e in suelto):
                    continue                          # lo suelto pisa este banco
                out.append((pieza if lado == 0 else pieza + "~", k, 8 if lado == 0 else 200 - _ANCHO[pieza], y))
    return out


ADD = _sala()
