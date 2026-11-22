"""Genera include/inv_item_floor_art.h (iconos de suelo 24x24) desde include/inv_item_art.h.
Mismo tamano que el inventario, pero con mas contraste y algo mas de saturacion (objeto magico, no comparte la luz apagada de la escena).
El inventario conserva su arte: include/inv_item_art.h no se toca."""
import re, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, "include", "inv_item_art.h"), encoding="utf-8").read()
arrs = re.findall(r"static const uint16_t (s_\w+)_24\[24 \* 24\] = \{(.*?)\};", src, re.S)
S = 24
# Parametros de contraste/saturacion (se aplican aqui, nunca en ejecucion).
PCT_LO, PCT_HI = 2, 98          # percentiles de luminancia de los pixeles opacos
GAIN_MIN, GAIN_MAX = 1.35, 1.5  # ganancia de contraste alrededor del punto medio (limitada)
TARGET_MID = 15.0               # luminancia a la que cae el punto medio del icono
SAT_BOOST = 1.18                # +18 % de saturacion
AURA_N, AURA_OFF, AURA_R = 30, 3, 3   # mapa 30x30, icono en (3,3), halo hasta 3 px
SH_W, SH_H, SH_OX, SH_OY = 36, 10, -24, 0  # igual que INV_FLOOR_SH_* en include/inventory.h
out = ["#ifndef INV_ITEM_FLOOR_ART_H", "#define INV_ITEM_FLOOR_ART_H", "",
       "#include <stdint.h>", "",
       "// Generado por tools/bake_inv_floor_art.py: iconos de suelo 24x24 RGB15 con contraste (0x0000 = transparente).", ""]

def rgb(c): return c & 31, (c >> 5) & 31, (c >> 10) & 31
def lum(r, g, b): return 0.30 * r + 0.59 * g + 0.11 * b

for name, body in arrs:
    px = [int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]+", body)]
    assert len(px) == S * S
    ls = sorted(lum(*rgb(c)) for c in px if c)
    lo = ls[int(len(ls) * PCT_LO / 100)]
    hi = ls[min(len(ls) - 1, int(len(ls) * PCT_HI / 100))]
    mid = (lo + hi) / 2
    gain = min(GAIN_MAX, max(GAIN_MIN, 31.0 / max(1.0, hi - lo) * 0.9))
    res = []
    for c in px:
        if not c:
            res.append(0); continue
        r, g, b = rgb(c)
        ch = [TARGET_MID + (v - mid) * gain for v in (r, g, b)]
        l = lum(*ch)
        ch = [l + (v - l) * SAT_BOOST for v in ch]
        r, g, b = (max(0, min(31, int(v + 0.5))) for v in ch)
        v = r | (g << 5) | (b << 10) | 0x8000
        res.append(v)
    out.append("static const uint16_t %s_fl24[24 * 24] = {" % name)
    for i in range(0, S * S, S):
        out.append("    " + ", ".join("0x%04X" % v for v in res[i:i + S]) + ",")
    out += ["};", ""]
    # Aura: mapa 30x30 (icono en 3,3): 0 = opaco, 1..3 = distancia euclidea redondeada a la silueta, 255 = nada.
    opaque = [(x, y) for y in range(S) for x in range(S) if res[y * S + x]]
    aura = []
    for ay in range(AURA_N):
        for ax in range(AURA_N):
            ix, iy = ax - AURA_OFF, ay - AURA_OFF
            if 0 <= ix < S and 0 <= iy < S and res[iy * S + ix]:
                aura.append(0); continue
            e2 = min((x - ix) ** 2 + (y - iy) ** 2 for x, y in opaque if abs(x - ix) <= 4 and abs(y - iy) <= 4) \
                if any(abs(x - ix) <= 4 and abs(y - iy) <= 4 for x, y in opaque) else 999
            d = int(e2 ** 0.5 + 0.5)
            aura.append(d if 1 <= d <= AURA_R else 255)
    out.append("static const uint8_t %s_aura[%d * %d] = {" % (name, AURA_N, AURA_N))
    for i in range(0, AURA_N * AURA_N, AURA_N):
        out.append("    " + ", ".join("%d" % v for v in aura[i:i + AURA_N]) + ",")
    out += ["};", ""]
    # Sombra: silueta proyectada al suelo; h = altura sobre la base; cae a la izquierda y algo abajo.
    sh = [0] * (SH_W * SH_H)
    low = max(y for x, y in opaque)
    for x, y in opaque:
        h = low - y
        mx = (x - 12) - int(h * 0.5 + 0.5) - SH_OX
        my = int(h * 0.4 + 0.5) - SH_OY
        if 0 <= mx < SH_W and 0 <= my < SH_H: sh[my * SH_W + mx] = 1
    out.append("static const uint8_t %s_sh[%d * %d] = {" % (name, SH_W, SH_H))
    for i in range(0, SH_W * SH_H, SH_W):
        out.append("    " + ", ".join("%d" % v for v in sh[i:i + SH_W]) + ",")
    out += ["};", ""]
    print("%s: lo=%.1f hi=%.1f gain=%.2f" % (name, lo, hi, gain))
out.append("#endif // INV_ITEM_FLOOR_ART_H")
open(os.path.join(root, "include", "inv_item_floor_art.h"), "w", newline="\n").write("\n".join(out) + "\n")
print(len(arrs), "icons")
