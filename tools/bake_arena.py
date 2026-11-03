#!/usr/bin/env python3
"""Bakes lab map packages into Nintendo DS arena sources (DESIGN.md 4.6, TECHNICAL.md 3).

For every arena it reads a package directory (world.png, collision.png, occlusion_depth.png,
exported by tools/lab/export_map_package_headless.cjs) and writes source/arena_<name>.c with:
  - the floor as 8bpp tiles and a tilemap (256-colour palette, 255 colours + void),
  - the 2-bit collision grid (4 px cells),
  - the occlusion runs sorted by (y, x) with a per-row index,
  - the player start and the enemy spawn points,
and a `const Arena g_arena_<name>`. `source/arenas.c` lists them in order.

usage:
  python.exe tools/bake_arena.py --spec assets/arenas/arenas.json     # the v0.1 arenas
  python.exe tools/bake_arena.py --package DIR --name NAME --player X,Y [--enemy charger:X,Y ...]
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILE = 8
COLLISION_SCALE = 4
OCC_DEPTH_TOLERANCE = 1          # px of ground-Y spread merged into one run

# The upper screen has 128 KiB of VRAM: a 16 bpp actor page leaves 28 KiB of tile slots, i.e.
# 448 tiles including the blank one. Every screen window (33x25 tiles) must need fewer distinct
# tiles than that; near-identical tiles are merged (lossy) until it does (TECHNICAL.md 3.3).
TILE_SLOTS = 448
WINDOW_BUDGET = TILE_SLOTS - 8
VIEW_W, VIEW_H = 33, 25

ENEMY_TYPES = {"charger": "ARENA_ENEMY_CHARGER", "shooter": "ARENA_ENEMY_SHOOTER"}


def max_window_distinct(tmap):
    best = 0
    for y in range(0, max(1, tmap.shape[0] - VIEW_H + 1)):
        for x in range(0, max(1, tmap.shape[1] - VIEW_W + 1)):
            best = max(best, len(np.unique(tmap[y:y + VIEW_H, x:x + VIEW_W])))
    return best


def merge_tiles(tiles_list, tmap, pal_rgb, threshold, max_pixel_error):
    """Greedy merge by usage: a tile joins the nearest kept tile when it is close enough."""
    arr = np.array([np.frombuffer(t, dtype=np.uint8) for t in tiles_list])
    rgb = pal_rgb[arr].reshape(len(tiles_list), -1)
    void = (arr == 0)
    counts = np.bincount(tmap.flatten(), minlength=len(tiles_list))
    order = [0] + [int(t) for t in np.argsort(-counts, kind='stable') if t != 0]   # blank stays tile 0
    kept = []
    kept_rgb = np.zeros((len(tiles_list), rgb.shape[1]), dtype=np.float32)
    kept_void = np.zeros((len(tiles_list), arr.shape[1]), dtype=bool)
    remap = np.zeros(len(tiles_list), dtype=np.int64)
    for t in order:
        k = len(kept)
        if k:
            diff = np.abs(kept_rgb[:k] - rgb[t])
            mean = diff.mean(axis=1)
            ok = (mean <= threshold) & (diff.max(axis=1) <= max_pixel_error) & (kept_void[:k] == void[t]).all(axis=1)
            if ok.any():
                remap[t] = int(np.argmin(np.where(ok, mean, 1e9)))
                continue
        kept_rgb[k] = rgb[t]
        kept_void[k] = void[t]
        remap[t] = k
        kept.append(t)
    return remap, kept


def bake_floor(world_png, world_w, world_h):
    im = Image.open(world_png).convert('RGB')
    padded = Image.new('RGB', (world_w, world_h), (0, 0, 0))
    padded.paste(im, (0, 0))
    im_p = padded.quantize(colors=255, method=Image.MEDIANCUT)       # index 0 reserved for the void
    pal_raw = im_p.getpalette()[:255 * 3]
    pal_bgr = [0x0000]
    pal_rgb = np.zeros((256, 3), dtype=np.float32)
    for i in range(len(pal_raw) // 3):               # flat renders use far fewer than 255 colours
        r, g, b = pal_raw[i * 3:i * 3 + 3]
        pal_rgb[i + 1] = (r, g, b)
        pal_bgr.append((r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) | 0x8000)
    pal_bgr += [0x0000] * (256 - len(pal_bgr))

    indexed = np.array(im_p, dtype=np.uint8) + 1
    arr = np.array(padded)
    indexed[(arr[:, :, 0] < 5) & (arr[:, :, 1] < 5) & (arr[:, :, 2] < 5)] = 0     # black void

    map_w, map_h = world_w // TILE, world_h // TILE
    ids = {bytes([0] * 64): 0}
    tiles = [bytes([0] * 64)]
    tmap = np.zeros((map_h, map_w), dtype=np.int64)
    for ty in range(map_h):
        for tx in range(map_w):
            t_bytes = bytes(indexed[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE].flatten())
            if t_bytes not in ids:
                ids[t_bytes] = len(tiles)
                tiles.append(t_bytes)
            tmap[ty, tx] = ids[t_bytes]

    worst = max_window_distinct(tmap)
    note = f"worst window {worst} tiles (budget {WINDOW_BUDGET})"
    if worst > WINDOW_BUDGET:
        for threshold in (1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0):
            remap, kept = merge_tiles(tiles, tmap, pal_rgb, threshold, 96)
            new_map = remap[tmap]
            worst = max_window_distinct(new_map)
            if worst <= WINDOW_BUDGET:
                tiles = [tiles[t] for t in kept]
                tmap = new_map
                note = f"merged at threshold {threshold}: {len(tiles)} tiles, worst window {worst}"
                break
        else:
            sys.exit("could not fit the floor into the upper screen tile budget")
    return pal_bgr, tiles, tmap, note


def bake_collision(coll_png, world_w, world_h):
    cw, ch = world_w // COLLISION_SCALE, world_h // COLLISION_SCALE
    arr = np.array(Image.open(coll_png).convert('L'))
    padded = np.zeros((world_h, world_w), dtype=np.uint8)
    padded[:arr.shape[0], :arr.shape[1]] = arr[:world_h, :world_w]
    grid = np.zeros((ch, cw), dtype=np.uint8)
    for cy in range(ch):
        for cx in range(cw):
            cell = padded[cy * COLLISION_SCALE:(cy + 1) * COLLISION_SCALE, cx * COLLISION_SCALE:(cx + 1) * COLLISION_SCALE]
            grid[cy, cx] = 0 if np.mean(cell >= 128) > 0.40 else 3        # white = walkable
    flat = grid.flatten().astype(np.uint8)
    if flat.size % 4:
        flat = np.pad(flat, (0, 4 - flat.size % 4))
    packed = flat[0::4] | (flat[1::4] << 2) | (flat[2::4] << 4) | (flat[3::4] << 6)
    return grid, packed


def bake_occlusion(depth_png, world_w, world_h):
    rgb = np.array(Image.open(depth_png).convert('RGB'), dtype=np.int32)
    ground_y = np.full((world_h, world_w), -1, dtype=np.int32)
    h, w = min(world_h, rgb.shape[0]), min(world_w, rgb.shape[1])
    ground_y[:h, :w] = np.where(rgb[:h, :w, 2] >= 128, rgb[:h, :w, 0] * 256 + rgb[:h, :w, 1], -1)
    runs = []
    for y in range(world_h):
        row = ground_y[y]
        x = 0
        while x < world_w:
            if row[x] < 0:
                x += 1
                continue
            x0 = x
            min_d = max_d = row[x]
            while x < world_w and row[x] >= 0:
                d = row[x]
                if max(max_d, d) - min(min_d, d) > OCC_DEPTH_TOLERANCE:
                    break
                min_d, max_d = min(min_d, d), max(max_d, d)
                x += 1
            runs.append((x0, y, x - x0, int(max_d)))
    row_start = [0] * (world_h + 1)
    for _, y, _, _ in runs:
        row_start[y + 1] += 1
    for y in range(world_h):
        row_start[y + 1] += row_start[y]
    return runs, row_start


# Body footprint (ground circle of radius 6 = ellipse 6x3 on screen) sampled like the tests do.
FOOTPRINT = ((0, 0), (-6, 0), (6, 0), (0, -3), (0, 3), (-5, -2), (-5, 2), (5, -2), (5, 2))


def check_walkable(grid, x, y, what):
    for dx, dy in FOOTPRINT:
        cx, cy = (x + dx) // COLLISION_SCALE, (y + dy) // COLLISION_SCALE
        if not (0 <= cx < grid.shape[1] and 0 <= cy < grid.shape[0]) or grid[cy, cx] != 0:
            sys.exit(f"{what} at ({x},{y}) does not have free floor for the body footprint")


def write_arena(name, title, package_dir, player, enemies):
    world_png = os.path.join(package_dir, 'world.png')
    w0, h0 = Image.open(world_png).size
    world_w = (w0 + TILE - 1) // TILE * TILE
    world_h = (h0 + TILE - 1) // TILE * TILE
    print(f"== {name}: {title} ({world_w}x{world_h})")

    pal, tiles, tmap, note = bake_floor(world_png, world_w, world_h)
    grid, packed = bake_collision(os.path.join(package_dir, 'collision.png'), world_w, world_h)
    runs, row_start = bake_occlusion(os.path.join(package_dir, 'occlusion_depth.png'), world_w, world_h)
    walk = int(np.sum(grid == 0))
    print(f"   floor: {len(tiles)} tiles, {note}\n   collision: {walk} walkable cells ({walk * 100 // grid.size}%)\n   occlusion: {len(runs)} runs")

    if not enemies:
        sys.exit(f"{name}: an arena without enemies would never be cleared")
    check_walkable(grid, player[0], player[1], "player start")
    for t, x, y in enemies:
        check_walkable(grid, x, y, f"{t} spawn")

    ident = name.replace('-', '_')
    if ident.startswith('arena_'):
        ident = ident[len('arena_'):]               # arena_01 -> source/arena_01.c, g_arena_01
    out = []
    out.append(f'// Generated by tools/bake_arena.py from {os.path.relpath(package_dir, ROOT).replace(os.sep, "/")}. Do not edit.\n')
    out.append('#include "arena.h"\n\n')
    out.append(f'static const uint16_t s_palette[256] __attribute__((aligned(4))) = {{\n')
    for i in range(0, 256, 16):
        out.append("    " + ", ".join(f"0x{v:04X}" for v in pal[i:i + 16]) + ",\n")
    out.append('};\n\n')
    out.append(f'static const uint8_t s_tiles[{len(tiles)}][64] __attribute__((aligned(4))) = {{\n')
    for t in tiles:
        out.append("    { " + ", ".join(str(b) for b in t) + " },\n")
    out.append('};\n\n')
    out.append(f'static const uint16_t s_map[{tmap.shape[0] * tmap.shape[1]}] __attribute__((aligned(4))) = {{\n')
    for row in tmap:
        out.append("    " + ", ".join(str(int(v)) for v in row) + ",\n")
    out.append('};\n\n')
    out.append(f'static const uint8_t s_collision[{len(packed)}] = {{\n')
    for i in range(0, len(packed), 32):
        out.append("    " + ", ".join(f"0x{int(v):02X}" for v in packed[i:i + 32]) + ",\n")
    out.append('};\n\n')
    out.append('static const DungeonOcclusionRun s_occlusion_runs[] __attribute__((aligned(4))) = {\n')
    for x0, y, length, d in runs:
        out.append(f"    {{{x0}, {y}, {length}, {d}}},\n")
    if not runs:
        out.append("    {0, 0, 0, -1},\n")
    out.append('};\n\n')
    out.append(f'static const uint32_t s_occlusion_row_start[{world_h + 1}] __attribute__((aligned(4))) = {{\n')
    for i in range(0, len(row_start), 16):
        out.append("    " + ", ".join(str(v) for v in row_start[i:i + 16]) + ",\n")
    out.append('};\n\n')
    out.append('static const ArenaEnemy s_enemies[] = {\n')
    for t, x, y in enemies:
        out.append(f"    {{ {ENEMY_TYPES[t]}, {x}, {y} }},\n")
    if not enemies:
        out.append("    { 0, 0, 0 },\n")
    out.append('};\n\n')
    out.append(f'const Arena g_arena_{ident} = {{\n')
    out.append(f'    .name = "{title}",\n')
    out.append(f'    .world_w = {world_w}, .world_h = {world_h},\n')
    out.append(f'    .collision_w = {world_w // COLLISION_SCALE}, .collision_h = {world_h // COLLISION_SCALE},\n')
    out.append(f'    .map_w = {tmap.shape[1]}, .map_h = {tmap.shape[0]}, .num_tiles = {len(tiles)},\n')
    out.append(f'    .player_x = {player[0]}, .player_y = {player[1]},\n')
    out.append(f'    .num_enemies = {len(enemies)},\n')
    out.append('    .collision = s_collision,\n    .palette = s_palette,\n    .tiles = s_tiles,\n    .map = s_map,\n')
    out.append('    .occlusion_runs = s_occlusion_runs,\n    .occlusion_row_start = s_occlusion_row_start,\n    .enemies = s_enemies,\n};\n')
    with open(os.path.join(ROOT, 'source', f'arena_{ident}.c'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(''.join(out))
    return ident


def write_arena_list(idents):
    out = ['// Generated by tools/bake_arena.py. Do not edit.\n#include "arena.h"\n\n']
    for i in idents:
        out.append(f'extern const Arena g_arena_{i};\n')
    out.append('\nconst Arena *const g_arenas[] = {\n')
    for i in idents:
        out.append(f'    &g_arena_{i},\n')
    out.append('};\n')
    out.append(f'const int g_num_arenas = {len(idents)};\n')
    with open(os.path.join(ROOT, 'source', 'arenas.c'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(''.join(out))


def parse_xy(text):
    x, y = text.split(',')
    return int(x), int(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', help='arenas.json; packages are read from assets/sprites/arenas/<name>/')
    ap.add_argument('--package')
    ap.add_argument('--name')
    ap.add_argument('--title')
    ap.add_argument('--player')
    ap.add_argument('--enemy', action='append', default=[], help='type:X,Y')
    args = ap.parse_args()

    idents = []
    if args.spec:
        spec = json.load(open(args.spec, encoding='utf-8'))
        for a in spec['arenas']:
            package = os.path.join(ROOT, 'assets', 'sprites', 'arenas', a['name'])
            enemies = [(e['type'], e['at'][0], e['at'][1]) for e in a['enemies']]
            idents.append(write_arena(a['name'], a['title'], package, tuple(a['player_start']), enemies))
    else:
        enemies = []
        for e in args.enemy:
            t, xy = e.split(':')
            enemies.append((t,) + parse_xy(xy))
        idents.append(write_arena(args.name, args.title or args.name, os.path.abspath(args.package), parse_xy(args.player), enemies))
    write_arena_list(idents)
    print("arenas:", ", ".join(idents))


if __name__ == '__main__':
    main()
