#!/usr/bin/env python3
"""Hornea el arte de los fixtures de sala (cofre cerrado, cofre abierto, altar) para cada luz del ARPG.

Entrada: scratch/arpg_luz/<luz>/props/<pieza>/ (tools/arpg_light_props.py <luz> --only cofre_cerrado,cofre_abierto,altar).
Salida: nitrofiles/arpg_luz/<luz>_fix.bin, que source/room_light.c lee sobre los sprites de dia de include/enc_room_gfx.h.
No toca los paquetes <luz>.bin.

Formato (little endian): 'LFIX', u32 n (=3); n x { i16 left, u16 w, u16 h, u16 anchor_y }; despues los pixeles de los 3
sprites seguidos (w*h u16 cada uno, BGR555 con bit 15; 0 = transparente; 0x0001 = sombra: la ROM oscurece al 50 % el
pixel que hay debajo). Cada sprite va recortado a su caja: `left` es el desplazamiento X de su borde izquierdo respecto
al centro del fixture; `anchor_y` la Y local del punto de suelo.

uso: python tools/arpg_light_fix.py [luz ...]      (sin argumentos: las 12)
"""
import json, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DAY = ROOT / "assets/environment/cathedral/props/render"
PIECES = ("cofre_cerrado", "cofre_abierto", "altar")
DAY_W = {"cofre_cerrado": 48, "cofre_abierto": 48, "altar": 24}   # lienzo de include/enc_room_gfx.h
SHADOW = 0x0001


def bgr555(rgb):
    r, g, b = (rgb[..., i].astype(np.int32) >> 3 for i in range(3))
    return (r | (g << 5) | (b << 10) | 0x8000).astype(np.uint16)


def bake(folder, name):
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    art = np.asarray(Image.open(folder / "color.png").convert("RGBA"))
    sw, sh = meta["shadow_canvas_px"]; dx, dy = meta["shadow_offset_px"]; ox, oy = -dx, -dy
    px = np.zeros((sh, sw), np.uint16)
    body = art[:, :, 3] >= 128
    px[oy:oy + art.shape[0], ox:ox + art.shape[1]][body] = bgr555(art[:, :, :3])[body]
    sm = np.asarray(Image.open(folder / "shadow.png").convert("L")) > 127
    px[(sm) & (px == 0)] = SHADOW
    foot = np.asarray(Image.open(folder / "footprint.png").convert("L"))
    cells = (foot.reshape(foot.shape[0] // 4, 4, foot.shape[1] // 4, 4) >= 128).mean(axis=(1, 3)) > .40
    rows = [cy for cy in range(cells.shape[0]) if cells[cy].any()]
    anchor = max(rows) * 4 + 4 + oy
    # cuerpo del dia: su borde izquierdo respecto al centro del fixture (lienzo del dia centrado, color en -dx_dia)
    dmeta = json.loads((DAY / name / "meta.json").read_text(encoding="utf-8"))
    body_left = -DAY_W[name] // 2 - dmeta["shadow_offset_px"][0]
    ys, xs = np.nonzero(px)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    crop = px[y0:y1, x0:x1]
    return {"left": body_left - (ox - int(x0)), "w": crop.shape[1], "h": crop.shape[0], "anchor": anchor - int(y0), "px": crop}


def main():
    doc = json.loads((ROOT / "tools/arpg_light_rooms.json").read_text(encoding="utf-8"))
    ids = sys.argv[1:] or [l["id"] for l in doc["luces"]]
    out_dir = ROOT / "nitrofiles/arpg_luz"
    for lid in ids:
        sp = [bake(ROOT / "scratch/arpg_luz" / lid / "props" / n, n) for n in PIECES]
        blob = b"LFIX" + struct.pack("<I", len(sp))
        for s in sp:
            blob += struct.pack("<hHHH", s["left"], s["w"], s["h"], s["anchor"])
        for s in sp:
            blob += s["px"].astype("<u2").tobytes()
        (out_dir / f"{lid}_fix.bin").write_bytes(blob)
        print(lid, len(blob), "bytes", [(s["left"], s["w"], s["h"], s["anchor"]) for s in sp])


if __name__ == "__main__":
    main()
