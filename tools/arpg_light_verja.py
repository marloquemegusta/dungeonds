#!/usr/bin/env python3
"""Hornea la reja (rastrillo) con la luz de cada sala del ARPG: color iluminado y sombra proyectada al suelo.

Entrada por luz: scratch/arpg_luz/<luz>/kit_props/verja/{color,shadow}.png (tools/arpg_light_props.py <luz> --kit --only verja;
con --render se lanza aqui). Para el arte de dia: assets/environment/cathedral/props/render/verja/color.png, sin sombra.
Salida: nitrofiles/arpg_luz/<luz>_verja.bin y nitrofiles/arpg_luz/dia_verja.bin, que source/room_light.c lee en la pantalla de
carga sobre g_verja_palette / g_verja_pixels (source/verja_gfx.c, mutables) y sobre la mascara de sombra de source/hwshadow.c.

Formato (little endian): 'LVJA'; u8 r0 (fila del lienzo 104x56 de la reja donde empieza la sombra), u8 rows (alto de la
sombra, 0 = sin sombra, max 40), u8 dir (0 = la sombra cae hacia la camara: al subir la reja se recorta por arriba; 1 = cae
hacia el fondo: se recorta por abajo), u8 0; paleta 16 x u16 BGR555 (indice 0 = transparente); pixeles 56 x 104 u8 (0..15);
mascara de sombra 1 bpp, LSB primero, filas continuas, partida en dos mitades: izquierda 56 px (rows x 7 B) y derecha 48 px
(rows x 6 B). La mitad izquierda y la derecha son las dos mascaras que hwshadow_add convierte a OBJ de ventana.

uso: python tools/arpg_light_verja.py [--render] [luz ...]      (sin luces: las 12 y la de dia)
"""
import json, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/props"))
import bake_verja_obj as bv                      # noqa: E402

DAY = ROOT / "assets/environment/cathedral/props/render/verja"
OUT = ROOT / "nitrofiles/arpg_luz"
MAX_ROWS = 40                                    # 5 tiles de alto: lo que reserva el cargador (source/hwshadow.c)
SPLIT = 56


def shadow_block(path):
    sm = np.asarray(Image.open(path).convert("L")) > 127
    if sm.shape[1] != bv.W:
        raise ValueError(f"{path}: ancho {sm.shape[1]}, se esperaba {bv.W}")
    ys = np.nonzero(sm.any(axis=1))[0]
    if len(ys) == 0:
        return 0, 0, 0, b"", b""
    r0, r1 = int(ys.min()), int(ys.max()) + 1
    below = (r0 + r1) / 2 > bv.H                 # la sombra cae por debajo de los pies: hacia la camara
    if r1 - r0 > MAX_ROWS:                       # recorta el extremo lejano (el que ya no se ve en la reja subida)
        if below: r1 = r0 + MAX_ROWS
        else: r0 = r1 - MAX_ROWS
    blk = sm[r0:r1]
    def pack(cols):
        return np.packbits(cols.reshape(-1), bitorder="little").tobytes()
    return r0, r1 - r0, 0 if below else 1, pack(blk[:, :SPLIT]), pack(blk[:, SPLIT:])


def bake(name, color_png, shadow_png):
    palette, pixels = bv.quantize(color_png, lit=shadow_png is not None)
    r0, rows, d, left, right = shadow_block(shadow_png) if shadow_png else (0, 0, 0, b"", b"")
    blob = b"LVJA" + struct.pack("<BBBB", r0, rows, d, 0)
    blob += struct.pack("<16H", *palette) + pixels.tobytes() + left + right
    (OUT / f"{name}_verja.bin").write_bytes(blob)
    print(f"{name}: {len(blob)} B, sombra filas {r0}..{r0 + rows} dir {d}")


def main():
    args = sys.argv[1:]
    render = "--render" in args
    ids = [a for a in args if not a.startswith("--")]
    doc = json.loads((ROOT / "tools/arpg_light_rooms.json").read_text(encoding="utf-8"))
    all_ids = [l["id"] for l in doc["luces"]]
    for lid in ids or all_ids:
        if render:
            subprocess.run([sys.executable, str(ROOT / "tools/arpg_light_props.py"), lid, "--kit", "--only", "verja"], check=True)
        d = ROOT / "scratch/arpg_luz" / lid / "kit_props/verja"
        bake(lid, d / "color.png", d / "shadow.png")
    if not ids:
        bake("dia", DAY / "color.png", None)


if __name__ == "__main__":
    main()
