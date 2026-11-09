"""Prototipo de lapidas de suelo sobre rombos_tripo con cluster de un solo tono y junta oscura.

Cada lapida se escala sin deformar a un numero entero de rombos: las horizontales a 2 rombos
de ancho (64 px) y las verticales a 3 rombos de alto (48 px). Bajo la lapida, los rombos del
cluster se rellenan con el tono mediano de la piedra A, sin alternar el damero.
La junta es de 1 px y de 2 px en los lados izquierdo y superior (luz key desde arriba-izquierda;
las sombras de las piezas caen a la derecha-abajo).

Dos variantes por lapida: V1, cluster de un solo tono; V2, el mismo cluster con una variacion
de tono por rombo de +-5 niveles por canal.

usage: python tools/catalogo/cat_lapidas_cluster.py
Salida: walkthroughs/v032-escenario/assets/cat_lapidas_cluster.png (A1..H2).
"""
import json
import os

import numpy as np
from PIL import Image

import cat_common as C

NAMES = [
    "lapida_cruz_h", "lapida_cruz_v",
    "lapida_caballero_h", "lapida_caballero_v",
    "lapida_cruz2_h", "lapida_cruz2_v",
    "lapida_caballero2_h", "lapida_caballero2_v",
]

CELL_W, CELL_H = 180, 120
BOX = (0, 0, CELL_W, CELL_H)
GROUND = 86
RH_W, RH_H = 32, 16
CLUSTER_MARGIN = 20
JOINT = (26, 22, 18, 255)
VARIANT_DELTAS = (-5.0, 0.0, 5.0)


def content_image(name):
    meta = json.load(open(os.path.join(C.RENDER, name, "meta.json"), encoding="utf-8"))
    image = Image.open(os.path.join(C.RENDER, name, "color.png")).convert("RGBA")
    cw, ch = image.size
    nw, nh = meta["content_px"]
    ox, oy = (cw - nw) // 2, ch - nh
    return image.crop((ox, oy, ox + nw, oy + nh)), meta


def scale_slab(name, content, meta):
    nw, nh = content.size
    factor = (2 * RH_W / nw) if name.endswith("_h") else (3 * RH_H / nh)
    size = (max(1, round(nw * factor)), max(1, round(nh * factor)))
    return content.resize(size, Image.LANCZOS), factor, round(meta["target_width"] * factor)


def diamond_mask(cx, cy):
    ys, xs = np.mgrid[0:CELL_H, 0:CELL_W]
    return np.abs(xs - cx) / 16.0 + np.abs(ys - cy) / 8.0 < 1.0


def stone_tone(arr):
    tones = []
    for cy in range(8, CELL_H, 16):
        for cx in range(16, CELL_W, 32):
            mask = diamond_mask(cx, cy)
            tones.append(arr[mask].mean(axis=0))
    return np.median(np.array(tones), axis=0)


def draw_cluster(cell, bbox, variant):
    arr = np.asarray(cell.convert("RGB")).copy()
    tone = stone_tone(arr)
    x0, y0, x1, y1 = bbox
    for cy in range(0, CELL_H + RH_H, RH_H):
        for cx in range(0, CELL_W + RH_W, RH_W):
            for center in ((cx, cy), (cx + 16, cy + 8)):
                ccx, ccy = center
                if not (x0 - CLUSTER_MARGIN <= ccx <= x1 + CLUSTER_MARGIN and
                        y0 - CLUSTER_MARGIN <= ccy <= y1 + CLUSTER_MARGIN):
                    continue
                delta = 0.0
                if variant == 2:
                    key = (ccx * 73856093) ^ (ccy * 19349663)
                    delta = VARIANT_DELTAS[key % 3]
                arr[diamond_mask(ccx, ccy)] = np.clip(tone + delta, 0, 255).astype(np.uint8)
    cell.paste(Image.fromarray(arr).convert("RGBA"), (0, 0))
    return cell


def shift(mask, dx, dy):
    out = np.zeros_like(mask)
    ys_src = slice(max(0, -dy), mask.shape[0] - max(0, dy))
    ys_dst = slice(max(0, dy), mask.shape[0] - max(0, -dy))
    xs_src = slice(max(0, -dx), mask.shape[1] - max(0, dx))
    xs_dst = slice(max(0, dx), mask.shape[1] - max(0, -dx))
    out[ys_dst, xs_dst] = mask[ys_src, xs_src]
    return out


def draw_joint(cell, alpha, origin):
    solid = alpha > 127
    ring = solid.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                ring |= shift(solid, dx, dy)
    ring |= shift(solid, -1, 0) | shift(solid, -2, 0)
    ring |= shift(solid, 0, -1) | shift(solid, 0, -2)
    ring &= ~solid
    ys, xs = np.nonzero(ring)
    if not len(xs):
        return
    layer = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    px = layer.load()
    ox, oy = origin
    for x, y in zip(xs, ys):
        px[int(x + ox), int(y + oy)] = JOINT
    cell.alpha_composite(layer)


def marine_pair():
    frame = C.char_frame("characters_neutral", "marine", 0, 0)
    sheet = Image.open(os.path.join(C.ROOT, "assets/sprites/characters_neutral/marine/shadow.png"))
    arr = np.asarray(sheet.convert("RGBA").crop((0, 0, 80, 80))).copy()
    arr[:, :, :3] = 0
    arr[:, :, 3] = (arr[:, :, 3] * 0.35).astype(np.uint8)
    return frame, Image.fromarray(arr)


def main():
    marine, marine_shadow = marine_pair()
    anchor = C.char_anchor("characters_neutral", "marine")
    floor = C.floor_crop("rombos_tripo", (CELL_W, CELL_H), BOX)

    cells = []
    proposals = []
    for index, name in enumerate(NAMES):
        letter = chr(ord("A") + index)
        content, meta = content_image(name)
        slab, factor, proposed = scale_slab(name, content, meta)
        proposals.append((name, meta["target_width"], proposed, factor))
        for variant in (1, 2):
            cell = Image.new("RGBA", (CELL_W, CELL_H), C.BG)
            cell.paste(floor, (0, 0))

            padded = Image.new("RGBA", (slab.width + 4, slab.height + 4), (0, 0, 0, 0))
            padded.alpha_composite(slab, (2, 2))
            sx = (CELL_W - slab.width) // 2 + 18 - 2
            sy = GROUND - slab.height - 2
            alpha = np.asarray(padded)[:, :, 3]
            ys, xs = np.nonzero(alpha > 127)
            bbox = (sx + xs.min(), sy + ys.min(), sx + xs.max(), sy + ys.max())
            draw_cluster(cell, bbox, variant)
            draw_joint(cell, alpha, (sx, sy))

            cell.alpha_composite(padded, (sx, sy))
            cell.alpha_composite(marine_shadow, (6, GROUND - 33))
            cell.alpha_composite(marine, (6, GROUND - anchor[1]))
            label = f"{name[len('lapida_'):]} \u00b7 {'V1 un tono' if variant == 1 else 'V2 tono sutil'}"
            cells.append((cell, f"{letter}{variant}", label))

    C.build_grid(cells, 4, CELL_W, CELL_H, "cat_lapidas_cluster.png",
                 "Lapidas de suelo sobre rombos_tripo: cluster de un tono y junta oscura",
                 scale=2,
                 footer="V1: cluster de un solo tono con junta; V2: variacion de tono de +-5 niveles por canal y rombo. "
                        "Escala: h = 2 rombos de 32 px de ancho, v = 3 rombos de 16 px de alto. "
                        "Junta 1 px; 2 px en los lados izquierdo y superior (luz key desde arriba-izquierda).")

    for name, before, after, factor in proposals:
        print(f"{name}: target_width {before} -> {after} (x{factor:.4f})")


if __name__ == "__main__":
    main()
