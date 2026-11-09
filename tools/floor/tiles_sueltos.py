#!/usr/bin/env python
"""Suelo 'tiles_sueltos' (opcion 3): biblioteca pequena de tiles 8x8 + volteos H/V.

Genera dos variantes en assets/environment/cathedral/floor/:
  tiles_sueltos    -> 16 tiles unicos de diseno
  tiles_sueltos_b  -> 24 tiles unicos de diseno

Metodo:
  1. Paleta: 32 colores de palette.json (BGR555), grises pardos, ordenados por luminancia.
     El dibujo trabaja en indices de paleta (rampa), asi que la textura ya esta cuantizada.
  2. Retícula de losas de 4x2 tiles (32x16 px = losa cuadrada de 1,8 m en la proyeccion 2:1).
     Aparejo alternado: las filas de losas impares se desplazan 2 tiles.
     Cada celda recibe un rol segun su posicion: C (cruce), T (junta horizontal arriba),
     L (junta vertical a la izquierda) o F (cara interior).
  3. Cada rol usa solo sus tiles de diseno. T admite volteo H (la junta sigue arriba),
     L admite volteo V (la junta sigue a la izquierda), C no volea, F vuelea libre.
  4. El bloque de 16x16 tiles se compone en pixeles y luego se trocea: cada bloque 8x8 se
     compara con sus 4 volteos y se agrupa por orbita. Asi el JSON sale de la textura
     real, no del diseno, y la reconstruccion se compara pixel a pixel.

Uso (desde la raiz del worktree):
    python tools/floor/tiles_sueltos.py
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAL_JSON = os.path.join(ROOT, "assets", "environment", "cathedral", "palette", "palette.json")
OUT_BASE = os.path.join(ROOT, "assets", "environment", "cathedral", "floor")

PERIOD = 16          # tiles por lado del bloque repetido
TILE = 8             # px
SLAB_W, SLAB_H = 4, 2
N_PAL = 32
SEED = 0x5EED
JOINT_OFF = 5       # indice de junta = base - 5
AO_OFF = 2          # sombra junto a la junta = base - 2
WIN_W, WIN_H = 33, 25

VARIANTS = {
    "tiles_sueltos": {
        "index": 0,
        "design": (
            [("T", "plain"), ("T", "crack"),
             ("L", "plain"), ("L", "pit"),
             ("C", "plain")]
            + [("F", "plain")] * 3 + [("F", "mottled")] * 2
            + [("F", "crack")] * 2 + [("F", "stain")] * 2
            + [("F", "wear"), ("F", "pit")]
        ),
    },
    "tiles_sueltos_b": {
        "index": 1,
        "design": (
            [("T", "plain"), ("T", "crack"), ("T", "mottled"),
             ("L", "plain"), ("L", "pit"), ("L", "crack"),
             ("C", "plain"), ("C", "mottled")]
            + [("F", "plain")] * 4 + [("F", "mottled")] * 3
            + [("F", "crack")] * 3 + [("F", "stain")] * 2
            + [("F", "wear")] * 2 + [("F", "pit")] * 2
        ),
    },
}


# ---------------------------------------------------------------- paleta

def bgr555_to_rgb8(v):
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    return ((r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2))


def build_palette(n=N_PAL):
    """32 colores de la paleta del proyecto: rampa de luminancia 20..120, con croma
    penalizada para que los niveles vecinos no cambien de tono (sin colores saturados)."""
    with open(PAL_JSON, encoding="utf-8") as fh:
        hexes = json.load(fh)["bgr555_hex"]["props"]
    cands, seen = [], set()
    for h in hexes:
        v = int(h, 16)
        if v in seen:
            continue
        seen.add(v)
        rgb = bgr555_to_rgb8(v)
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        chroma = max(rgb) - min(rgb)
        if 20 <= lum <= 120 and chroma <= 40:
            cands.append((lum, chroma, v))
    chosen, used = [], set()
    for target in np.linspace(20, 120, n):
        best = min((abs(c[0] - target) + 1.5 * c[1], j)
                   for j, c in enumerate(cands) if j not in used)
        used.add(best[1])
        chosen.append(cands[best[1]])
    chosen.sort()
    return [c[2] for c in chosen]


# ---------------------------------------------------------------- dibujo de tiles

def flip(block, h, v):
    if h:
        block = block[:, ::-1]
    if v:
        block = block[::-1, :]
    return block


def put(t, y, x, val):
    if 0 <= y < TILE and 0 <= x < TILE:
        t[y, x] = val


def grain(rng, t):
    m = rng.random((TILE, TILE))
    t[m < 0.12] -= 1
    t[m > 0.93] += 1


def draw_face(feat, rng, B):
    t = np.full((TILE, TILE), B, dtype=int)
    if feat == "plain":
        grain(rng, t)
    elif feat == "mottled":
        small = rng.integers(-1, 2, (4, 4))
        t += np.repeat(np.repeat(small, 2, 0), 2, 1)
        grain(rng, t)
    elif feat == "crack":
        grain(rng, t)
        length = int(rng.integers(4, 7))
        x0, y0 = (int(c) for c in rng.integers(1, 7, 2))
        dx = int(rng.choice([-1, 1]))
        dy = int(rng.choice([-1, 1]))
        x1, y1 = x0 + dx * length, y0 + dy * int(rng.integers(length - 2, length + 1))
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(n + 1):
            put(t, round(y0 + (y1 - y0) * k / n), round(x0 + (x1 - x0) * k / n), B - 3)
    elif feat == "stain":
        grain(rng, t)
        cx, cy = rng.uniform(2.0, 5.5, 2)
        r = rng.uniform(1.6, 2.6)
        for y in range(TILE):
            for x in range(TILE):
                d = np.hypot(x - cx, y - cy)
                if d < r * 0.7:
                    t[y, x] = B - 2
                elif d < r:
                    t[y, x] = B - 1
    elif feat == "wear":
        grain(rng, t)
        for _ in range(int(rng.integers(3, 6))):
            y, x = (int(c) for c in rng.integers(0, TILE, 2))
            t[y, x] = B + 2
    elif feat == "pit":
        grain(rng, t)
        y, x = (int(c) for c in rng.integers(1, 6, 2))
        t[y, x] = B - 3
        for dy, dx in ((0, 1), (1, 0), (1, 1)):
            t[y + dy, x + dx] = B - 2
    else:
        raise ValueError(feat)
    return t


def draw_tile(role, feat, rng, B):
    t = draw_face(feat, rng, B)
    J, A = B - JOINT_OFF, B - AO_OFF
    if role == "T":
        t[0, :] = J
        t[1, :] = np.minimum(t[1, :], A)
    elif role == "L":
        t[:, 0] = J
        t[:, 1] = np.minimum(t[:, 1], A)
    elif role == "C":
        t[0, :] = J
        t[:, 0] = J
        t[1, :] = np.minimum(t[1, :], A)
        t[:, 1] = np.minimum(t[:, 1], A)
    return t


# ---------------------------------------------------------------- composicion

def cell_role(x, y):
    row = y // SLAB_H
    off = 2 * (row % 2)                 # aparejo alternado
    left = (x - off) % SLAB_W == 0
    top = y % SLAB_H == 0
    if left and top:
        return "C"
    if top:
        return "T"
    if left:
        return "L"
    return "F"


def compose(lib, rng):
    """lib: lista de (role, tile 8x8). Devuelve textura 128x128 de indices de paleta."""
    by_role = {}
    for i, (role, _) in enumerate(lib):
        by_role.setdefault(role, []).append(i)
    tex = np.zeros((PERIOD * TILE, PERIOD * TILE), dtype=int)
    for y in range(PERIOD):
        for x in range(PERIOD):
            role = cell_role(x, y)
            i = by_role[role][int(rng.integers(len(by_role[role])))]
            if role == "T":
                h, v = int(rng.integers(2)), 0
            elif role == "L":
                h, v = 0, int(rng.integers(2))
            elif role == "C":
                h, v = 0, 0
            else:
                h, v = int(rng.integers(2)), int(rng.integers(2))
            tex[y * TILE:(y + 1) * TILE, x * TILE:(x + 1) * TILE] = flip(lib[i][1], h, v)
    return tex


def extract(tex):
    """Trocea la textura en tiles unicos por orbita de volteos. Devuelve (tiles, floor_map)."""
    keys, canon_of = {}, {}
    cells = {}
    for y in range(PERIOD):
        for x in range(PERIOD):
            b = tex[y * TILE:(y + 1) * TILE, x * TILE:(x + 1) * TILE]
            orbit = [flip(b, h, v) for h in (0, 1) for v in (0, 1)]
            key = min(tuple(o.flatten().tolist()) for o in orbit)
            cells[(x, y)] = (b, key)
            keys.setdefault(key, None)
    ordered = sorted(keys.keys())
    id_of = {k: i for i, k in enumerate(ordered)}
    tiles = [np.array(k, dtype=int).reshape(TILE, TILE) for k in ordered]
    floor_map = [[None] * PERIOD for _ in range(PERIOD)]
    for (x, y), (b, key) in cells.items():
        canon = tiles[id_of[key]]
        found = None
        for h in (0, 1):
            for v in (0, 1):
                if np.array_equal(flip(b, h, v), canon):
                    found = (h, v)
                    break
            if found:
                break
        assert found is not None, "orbita sin volteo valido"
        floor_map[y][x] = {"t": id_of[key], "h": found[0], "v": found[1]}
    return tiles, floor_map


def reconstruct(tiles, floor_map, cols, rows):
    """Reconstruye a pixeles SOLO desde tiles + floor_map (volteos incluidos)."""
    out = np.zeros((rows * TILE, cols * TILE), dtype=int)
    for ty in range(rows):
        for tx in range(cols):
            e = floor_map[ty % PERIOD][tx % PERIOD]
            out[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE] = flip(
                tiles[e["t"]], e["h"], e["v"])
    return out


def to_rgb(idx, pal_rgb):
    return np.array(pal_rgb, dtype=np.uint8)[idx]


def worst_window(floor_map):
    ids = np.array([[e["t"] for e in row] for row in floor_map])
    worst = 0
    for oy in range(PERIOD):
        for ox in range(PERIOD):
            ys = (oy + np.arange(WIN_H)) % PERIOD
            xs = (ox + np.arange(WIN_W)) % PERIOD
            worst = max(worst, len(np.unique(ids[np.ix_(ys, xs)])))
    return worst


def seam_metrics(rgb):
    d = lambda a, b: float(np.abs(a.astype(int) - b.astype(int)).mean())
    col_seam = d(rgb[:, -1], rgb[:, 0])
    row_seam = d(rgb[-1, :], rgb[0, :])
    col_in = np.mean([d(rgb[:, x], rgb[:, x + 1]) for x in range(rgb.shape[1] - 1)])
    row_in = np.mean([d(rgb[y, :], rgb[y + 1, :]) for y in range(rgb.shape[0] - 1)])
    return {
        "columna_diff_costura": round(col_seam, 2),
        "columna_diff_media_interna": round(float(col_in), 2),
        "fila_diff_costura": round(row_seam, 2),
        "fila_diff_media_interna": round(float(row_in), 2),
    }


def build_variant(name, spec, palette):
    pal_rgb = [bgr555_to_rgb8(v) for v in palette]
    B = len(palette) // 2 - 2               # base de la cara: medio-oscuro en la rampa
    design = spec["design"]
    lib = []
    for k, (role, feat) in enumerate(design):
        rng = np.random.default_rng([SEED, spec["index"], k])
        lib.append((role, draw_tile(role, feat, rng, B)))

    rng_map = np.random.default_rng([SEED, spec["index"], 999])
    tex = compose(lib, rng_map)
    # paleta recortada a los indices que de verdad usa el suelo (maximo 32)
    used = sorted(set(np.unique(tex).tolist()))
    lut = np.zeros(len(palette), dtype=int)
    for new_i, old_i in enumerate(used):
        lut[old_i] = new_i
    tex = lut[tex]
    palette = [palette[old_i] for old_i in used]
    pal_rgb = [bgr555_to_rgb8(v) for v in palette]
    tiles, floor_map = extract(tex)

    out_dir = os.path.join(OUT_BASE, name)
    os.makedirs(out_dir, exist_ok=True)

    # atlas de tiles unicos
    atlas = np.concatenate([np.array(t) for t in tiles], axis=1)
    Image.fromarray(to_rgb(atlas, pal_rgb), "RGB").save(os.path.join(out_dir, "tiles.png"))

    data = {
        "palette": [f"0x{v:04X}" for v in palette],
        "tiles": [t.flatten().tolist() for t in tiles],
        "floor_map": floor_map,
        "period_tiles": [PERIOD, PERIOD],
    }
    with open(os.path.join(out_dir, "floor.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(data, fh, separators=(",", ":"))

    # reconstruccion desde el JSON (solo tiles + volteos) y comparacion con la textura
    recon = reconstruct(tiles, floor_map, 64, 32)
    tiled_tex = np.tile(tex, (2, 4))  # filas x columnas: 256 x 512
    recon_ok = bool(np.array_equal(recon, tiled_tex))
    rgb512 = to_rgb(recon, pal_rgb)
    Image.fromarray(rgb512, "RGB").save(os.path.join(out_dir, "floor_512x256.png"))
    Image.fromarray(rgb512, "RGB").resize((512 * 3, 256 * 3), Image.NEAREST).save(
        os.path.join(out_dir, "floor_512x256_x3.png"))

    used_idx = set(np.unique(np.concatenate([t.flatten() for t in tiles])).tolist())
    stats = {
        "variante": name,
        "semilla": SEED,
        "disenio_tiles": len(design),
        "tiles_unicos_totales": len(tiles),
        "peor_ventana_33x25_tiles_distintos": worst_window(floor_map),
        "colores_paleta": len(palette),
        "colores_usados": len(used_idx),
        "costura_periodo": seam_metrics(to_rgb(tex, pal_rgb)),
        "reconstruccion_igual_a_textura": recon_ok,
        "celdas_por_rol": {r: sum(1 for y in range(PERIOD) for x in range(PERIOD)
                                   if cell_role(x, y) == r) for r in "TLCF"},
    }
    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(stats, fh, indent=2, ensure_ascii=False)
    return stats


def main():
    palette = build_palette()
    print(f"paleta: {len(palette)} colores")
    for name, spec in VARIANTS.items():
        s = build_variant(name, spec, palette)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        assert s["reconstruccion_igual_a_textura"], f"reconstruccion distinta en {name}"


if __name__ == "__main__":
    main()
