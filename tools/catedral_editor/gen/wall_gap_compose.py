#!/usr/bin/env python3
"""Recorta el hueco lateral (dos modulos quitados) del render de wall_gap_glb.py: hueco_izq.png, 24 x 264 px (33 filas de tiles).

uso: python wall_gap_compose.py <pkg_gap> <salida.png>
El pkg sale de export_map_package_headless.cjs con width 1586 (escala de 17,9 px/m con la caja de la escena vieja; ver
ghost.py). Filas R de la imagen, relativas a la fila G0 = 96 donde empieza el vacio en el juego: R = -24..239. Contiene
el canto del modulo norte (su cara 3D real, 112 px de alto), el vacio (144 filas) y 4 filas de arte de los modulos a ambos
lados con la misma fase que muro_izq_128.png. Las 24 columnas son las interiores (lado de la nave).
"""
import sys
import numpy as np
from PIL import Image

G0, R0, R1, FACE = 96, -24, 240, 112
pkg, out = sys.argv[1:3]
w = np.asarray(Image.open(f"{pkg}/world.png").convert("RGB"))
m = w.astype(int).sum(2) > 40
x1 = int(np.where(m.any(0))[0].max()) + 1                      # borde interior (nave) del muro
c = m[:, x1 - 12:x1 - 2].mean(1) > 0.5
d = np.diff(np.r_[0, c.astype(int), 0]); st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
(n0, n1), (s0, s1) = list(zip(st, en))[:2]
print("norte", n0, n1, "vacio", n1, s0, "sur", s0, s1, "-> vacio", s0 - n1, "filas (esperado 144)")
assert abs((s0 - n1) - 144) <= 2, "escala del lab fuera de 17,9 px/m: ajustar width"
rho0 = n1 - (G0 - R0)                                           # fila del render de R = R0
img = w[rho0:rho0 + (R1 - R0), x1 - 24:x1]
alpha = (m[rho0:rho0 + (R1 - R0), x1 - 24:x1]) * 255
Image.fromarray(np.dstack([img, alpha]).astype(np.uint8), "RGBA").save(out)
print("x1", x1, "rho0", rho0, "fase (rho0-R0-34) mod 128 =", (rho0 - R0 - 34) % 128, "(esperado 0)", "->", out)
