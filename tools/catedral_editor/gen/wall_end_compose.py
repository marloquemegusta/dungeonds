#!/usr/bin/env python3
"""Compone el remate de sala (256x152 px, 32x19 tiles) desde los renders del lab de wall_end_glb.py.

Una mitad izquierda (mundo x 128..256) hecha de: las 3 columnas interiores del muro lateral (render), un modulo del
fondo repetido byte a byte (para que los tiles se deduplican) y la mitad izquierda del modulo central; la derecha es
su espejo (igual que el muro derecho de la nave, que es el izquierdo con flip H). La base del muro cae en la ultima
fila de la imagen y la fase del lateral coincide con muro_izq_128.png (la linea de sala es multiplo de 128 px).

uso: python wall_end_compose.py <pkg_ciego> <pkg_pasante> <salida_dir>
     (cada pkg es la carpeta que escribe export_map_package_headless.cjs con width 928)
"""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image

W, H = 256, 152          # px de la imagen (32 x 19 tiles)
MOD = 48                 # ancho de modulo del fondo
THR = 40                 # suma RGB bajo la cual un pixel del render es vacio


def load(pkg):
    w = np.asarray(Image.open(Path(pkg) / "world.png").convert("RGB"))
    m = w.astype(int).sum(2) > THR
    return w, m


def geometry(w, m):
    """(columna del borde exterior del muro lateral, primera fila bajo el muro del fondo)."""
    cols = np.where(m[:, :].any(0))[0]
    x_back = cols.max()
    rows = np.where(m[:, x_back - 40:x_back].any(1))[0]      # solo el fondo (a la derecha del lateral)
    line = int(rows.max()) + 1
    x0 = int(np.where(m[line + 30:line + 200].any(0))[0].min())
    return x0, line


def compose(w, m, x0, line, centre_from_render):
    def cut(a, b):          # mundo x a..b, ultimas H filas sobre la linea
        return w[line - H:line, x0 + a - 128:x0 + b - 128], m[line - H:line, x0 + a - 128:x0 + b - 128]
    LAT_DY = int(os.environ.get('LAT_DY', '2'))   # fase del lateral: el render cae 2 px por debajo de muro_izq_128 (medido)
    lat = (w[line - H + LAT_DY:line + LAT_DY, x0:x0 + 24], m[line - H + LAT_DY:line + LAT_DY, x0:x0 + 24])
    mod = cut(184, 232)
    half = np.zeros((H, 128, 3), np.uint8); alpha = np.zeros((H, 128), bool)
    def put(x, part): half[:, x - 128:x - 128 + part[0].shape[1]] = part[0]; alpha[:, x - 128:x - 128 + part[1].shape[1]] = part[1]
    put(128, lat)
    put(152, (mod[0][:, 16:], mod[1][:, 16:]))
    put(184, mod)
    put(232, cut(232, 256) if centre_from_render else (mod[0][:, :24], mod[1][:, :24]))
    full = np.zeros((H, W, 4), np.uint8)
    full[:, :128, :3] = half; full[:, :128, 3] = alpha * 255
    full[:, 128:, :3] = half[:, ::-1]; full[:, 128:, 3] = (alpha[:, ::-1]) * 255
    return full


def main():
    ciego, pasante, out = sys.argv[1:4]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for name, pkg, centre in (("muro_fondo_ciego", ciego, False), ("muro_fondo_pasante", pasante, True)):
        w, m = load(pkg)
        x0, line = geometry(w, m)
        print(name, "x0", x0, "linea", line)
        Image.fromarray(compose(w, m, x0, line, centre), "RGBA").save(out / f"{name}.png")


if __name__ == "__main__":
    main()
