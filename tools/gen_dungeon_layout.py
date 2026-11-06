"""Designer script for the v0.3 dungeon: writes assets/arenas/arenas.json (DESIGN.md 6).

The layout is drawn on a 16 px cell grid (80x80 cells = the 1280x1280 image): rooms and
corridors carve open space out of solid rock; everything solid becomes `wall`/`rock` blocks whose
height depends on what is open to their north (a wall hides the floor 35 px per metre of
height NORTH of its own north edge, so the wall south of a corridor or room must stay low).
Cover (pillars, low walls) is listed per room. arenas.json stays the source of truth: edit
this script only to redesign the map, then run
    python.exe tools/gen_dungeon_layout.py
    python.exe tools/export_arenas.py && python.exe tools/bake_arena.py --spec assets/arenas/arenas.json
The script checks that every spawn has free floor and that the graph is connected.
"""
import json
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/arenas/arenas.json"
C = 16
N = 80
FLOOR = [16, 112, 1264, 1264]
FC = (1, 7, 79, 79)            # floor in cells (x0, y0, x1, y1)

# name: dict(rects (cells), notches (cells, solid inside), h = height of the walls south of it (m),
#            style = floor style, covers, pack)
# cover: (kind, [x0, y0, x1, y1] cells, height m)
ROOMS = {
    "start": dict(title="Antecamara", rects=[[31, 68, 49, 78]], h=1.0, style="plain", pack=None,
                  covers=[("wall", [34, 72, 38, 73], 1.0), ("wall", [42, 72, 46, 73], 1.0)]),
    "storage": dict(title="Almacen", rects=[[3, 60, 15, 78]], h=1.0, style="storage",
                    covers=[("wall", [4, 63, 7, 64], 0.9), ("wall", [11, 63, 14, 64], 0.9),
                            ("wall", [4, 67, 7, 68], 0.9), ("wall", [11, 67, 14, 68], 0.9),
                            ("wall", [4, 75, 7, 76], 0.9), ("wall", [11, 76, 14, 77], 0.9)],
                    pack=[("charger", 6, 65), ("charger", 9.5, 65.5), ("charger", 12.5, 61.5)]),
    "pit": dict(title="Foso", rects=[[65, 60, 77, 78]], notches=[[65, 60, 68, 63], [74, 60, 77, 63],
                                                                [65, 75, 68, 78], [74, 75, 77, 78]],
                h=1.4, style="pit",
                covers=[("wall", [69, 65, 73, 66], 1.4), ("wall", [70, 72, 72, 73], 1.4)],
                pack=[("shooter", 67, 70), ("shooter", 75, 66.5), ("charger", 71, 63)]),
    "guard": dict(title="Sala de guardia", rects=[[32, 48, 48, 60]], h=2.0, style="plain",
                  covers=[("pillar", [33, 49, 35, 50], 2.0), ("pillar", [45, 49, 47, 50], 2.0),
                          ("pillar", [33, 57, 35, 58], 2.0), ("pillar", [45, 57, 47, 58], 2.0)],
                  pack=[("charger", 36, 53), ("charger", 44, 53), ("shooter", 40, 51)]),
    "crypt": dict(title="Cripta de pilares", rects=[[3, 28, 25, 44]], h=2.0, style="crypt",
                  covers=[("pillar", [13, 31, 15, 32], 2.2), ("pillar", [19, 31, 21, 32], 2.2),
                          ("pillar", [13, 37, 15, 38], 2.2), ("pillar", [19, 37, 21, 38], 2.2),
                          ("pillar", [16, 34, 18, 35], 2.2), ("pillar", [4, 34, 6, 35], 2.2),
                          ("pillar", [4, 40, 6, 41], 2.2)],
                  pack=[("charger", 16.5, 30), ("charger", 20, 34), ("charger", 11.5, 34), ("charger", 22, 40)]),
    "niches": dict(title="Sala de nichos", rects=[[55, 30, 77, 42]],
                   notches=[], extra=[[57, 28, 61, 30], [63, 28, 67, 30], [57, 42, 61, 44], [63, 42, 67, 44]],
                   h=1.2, style="niches",
                   covers=[("wall", [60, 35, 66, 36], 1.0), ("wall", [72, 33, 75, 34], 1.0)],
                   pack=[("shooter", 59, 29), ("shooter", 65, 29), ("shooter", 59, 43), ("charger", 67, 38)]),
    "gallery": dict(title="Galeria de tiradores", rects=[[3, 8, 25, 16]], h=1.6, style="gallery",
                    covers=[("wall", [8, 11, 10, 12], 1.2), ("wall", [14, 12, 16, 13], 1.2),
                            ("wall", [19, 11, 21, 12], 1.2)],
                    pack=[("shooter", 5, 10), ("shooter", 13, 9.5), ("shooter", 18, 13.5),
                          ("shooter", 23, 10), ("charger", 16.5, 10.5)]),
    "hall": dict(title="Camara larga", rects=[[55, 8, 77, 17]], h=2.0, style="hall",
                 covers=[("pillar", [59, 11, 61, 12], 2.4), ("pillar", [65, 11, 67, 12], 2.4),
                         ("pillar", [71, 11, 73, 12], 2.4), ("pillar", [59, 14, 61, 15], 2.4),
                         ("pillar", [65, 14, 67, 15], 2.4)],
                 pack=[("charger", 57, 10), ("charger", 63, 9.5), ("charger", 69.5, 9.5),
                       ("shooter", 75, 12.5), ("shooter", 74.5, 9.5)]),
    "cross": dict(title="Cruce", rects=[[36, 26, 44, 40], [29, 30, 51, 36]], h=1.6, style="crypt",
                  covers=[("pillar", [39, 32, 41, 33], 1.8)],
                  pack=[("shooter", 31, 33), ("shooter", 49, 33), ("charger", 40, 28), ("charger", 40, 38)]),
    "sanctum": dict(title="Santuario", rects=[[29, 8, 51, 17]], h=2.0, style="sanctum",
                    covers=[("pillar", [34, 11, 36, 12], 2.0), ("pillar", [44, 11, 46, 12], 2.0),
                            ("pillar", [39, 13, 41, 14], 2.0), ("wall", [31, 14, 34, 15], 1.0),
                            ("wall", [46, 14, 49, 15], 1.0)],
                    pack=[("shooter", 32, 9.5), ("shooter", 40, 9.5), ("shooter", 48, 9.5),
                          ("charger", 37, 12.5), ("charger", 43, 12.5)]),
}
# corridors: name: (rect cells, height of the wall south of it)
CORRIDORS = {
    "c_w1": ([15, 69, 31, 74], 1.2), "c_e1": ([49, 69, 65, 74], 1.2),
    "c_w2": ([7, 44, 11, 60], 1.6), "c_w3": ([7, 16, 11, 28], 1.6),
    "c_e2": ([69, 42, 73, 60], 1.6), "c_e3": ([69, 17, 73, 30], 1.6),
    "c_c1": ([38, 60, 42, 68], 1.6), "c_c2": ([38, 40, 42, 48], 1.6), "c_c3": ([38, 17, 42, 26], 1.6),
}
PLAYER = (640, 1216)
STYLES = {   # sRGB tones the render should show (dark: floor luminance ~35-50)
    "plain": dict(pattern="checker", shade=1.0, tones=[[44, 47, 58], [38, 41, 52], [41, 44, 55]]),
    "storage": dict(pattern="scatter", shade=0.95, tones=[[50, 46, 48], [44, 40, 43], [47, 43, 45]]),
    "pit": dict(pattern="rows", shade=0.9, tones=[[40, 44, 54], [34, 38, 48], [37, 41, 51]]),
    "crypt": dict(pattern="checker", shade=1.0, tones=[[42, 46, 60], [35, 39, 53], [38, 42, 56]]),
    "niches": dict(pattern="scatter", shade=1.0, tones=[[46, 45, 54], [40, 39, 48], [43, 42, 51]]),
    "gallery": dict(pattern="rows", shade=1.0, tones=[[48, 49, 58], [42, 43, 52], [45, 46, 55]]),
    "hall": dict(pattern="checker", shade=0.95, tones=[[40, 43, 55], [34, 37, 49], [37, 40, 52]]),
    "sanctum": dict(pattern="rows", shade=1.05, tones=[[52, 48, 52], [45, 41, 45], [48, 44, 48]]),
    "corridor": dict(pattern="rows", shade=0.85, tones=[[36, 38, 48], [31, 33, 43], [34, 36, 46]]),
}
ROCK_H = 2.4
SCAN = 6            # cells north scanned for open floor when choosing a wall's height


def build_mask():
    label = np.full((N, N), -1, dtype=int)
    names = []
    heights = []
    styles = []

    def carve(name, rect, h, style):
        if name not in names:
            names.append(name)
            heights.append(h)
            styles.append(style)
        i = names.index(name)
        x0, y0, x1, y1 = rect
        label[y0:y1, x0:x1] = i

    for name, r in ROOMS.items():
        for rect in r["rects"] + r.get("extra", []):
            carve(name, rect, r["h"], r["style"])
        for x0, y0, x1, y1 in r.get("notches", []):
            label[y0:y1, x0:x1] = -1
    for name, (rect, h) in CORRIDORS.items():
        carve(name, rect, h, "corridor")
    return label, names, heights, styles


def wall_heights(label, heights):
    """Per-cell height of the solid cells."""
    hmap = np.zeros((N, N))
    for y in range(N):
        for x in range(N):
            if label[y, x] >= 0:
                continue
            h = None
            for d in range(1, SCAN + 1):          # open floor to the north decides
                if y - d >= 0 and label[y - d, x] >= 0:
                    h = heights[label[y - d, x]]
                    break
            if h is None:                          # side walls: any open floor beside or below
                best = None
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < N and 0 <= xx < N and label[yy, xx] >= 0:
                            dist = max(abs(dx), abs(dy))
                            if best is None or dist < best[0]:
                                best = (dist, heights[label[yy, xx]])
                h = best[1] if best else ROCK_H
            hmap[y, x] = h
    return hmap


def rock_blocks(label, hmap):
    todo = (label < 0)
    todo[:FC[1], :] = False          # above the floor rect
    todo[:, :FC[0]] = False
    todo[:, FC[2]:] = False
    done = np.zeros_like(todo)
    out = []
    for y in range(FC[1], FC[3]):
        for x in range(FC[0], FC[2]):
            if not todo[y, x] or done[y, x]:
                continue
            h = hmap[y, x]
            x1 = x
            while x1 < FC[2] and todo[y, x1] and not done[y, x1] and hmap[y, x1] == h:
                x1 += 1
            y1 = y + 1
            while y1 < FC[3] and all(todo[y1, x:x1]) and not any(done[y1, x:x1]) and all(hmap[y1, x:x1] == h):
                y1 += 1
            done[y:y1, x:x1] = True
            out.append({"kind": "rock", "rect": [x * C, y * C, x1 * C, y1 * C], "height_m": round(float(h), 2)})
    return out


def zones_for(label, styles):
    xs = sorted({1, 27, 53, 79})
    ys = sorted({7, 17, 26, 28, 40, 44, 48, 60, 68, 79})
    zones = []
    for yi in range(len(ys) - 1):
        for xi in range(len(xs) - 1):
            x0, x1, y0, y1 = xs[xi], xs[xi + 1], ys[yi], ys[yi + 1]
            cnt = {}
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if label[y, x] >= 0:
                        cnt[styles[label[y, x]]] = cnt.get(styles[label[y, x]], 0) + 1
            style = max(cnt, key=lambda k: (cnt[k] if k != "corridor" else cnt[k] * 0.9)) if cnt else "corridor"
            zones.append({"name": f"z{xi}{yi}", "rect": [x0 * C, y0 * C, x1 * C, y1 * C], "style": style,
                          "accent": "amber"})
    return zones


def main():
    label, names, heights, styles = build_mask()
    hmap = wall_heights(label, heights)
    blocks = rock_blocks(label, hmap)
    covers = []
    for name, r in ROOMS.items():
        for kind, (x0, y0, x1, y1), h in r["covers"]:
            covers.append({"kind": kind, "rect": [x0 * C, y0 * C, x1 * C, y1 * C], "height_m": h})
    enemies = []
    packs = [n for n, r in ROOMS.items() if r["pack"]]
    # pack numbers by path distance from the start (ground metric), nearest first
    dist = ground_distance(label, (PLAYER[0] // C, PLAYER[1] // C))
    order = sorted(packs, key=lambda n: min(dist[int(y // 1), int(x // 1)] for _, x, y in ROOMS[n]["pack"]))
    for pack, n in enumerate(order):
        for t, x, y in ROOMS[n]["pack"]:
            enemies.append({"pack": pack, "type": t, "at": [int(x * C), int(y * C)], "room": n})
    # validation
    solid_cover = np.zeros((N * C, N * C), dtype=bool)
    for b in covers + blocks:
        x0, y0, x1, y1 = b["rect"]
        solid_cover[y0:y1, x0:x1] = True
    foot = ((0, 0), (-6, 0), (6, 0), (0, -3), (0, 3), (-5, -2), (-5, 2), (5, -2), (5, 2))
    for e in enemies + [{"type": "player", "at": list(PLAYER)}]:
        x, y = e["at"]
        for dx, dy in foot:
            if label[(y + dy) // C, (x + dx) // C] < 0 or solid_cover[y + dy, x + dx]:
                raise SystemExit(f"{e['type']} at {e['at']} is not on free floor")
    for r in ROOMS.values():
        for kind, (x0, y0, x1, y1), h in r["covers"]:
            if (label[y0:y1, x0:x1] < 0).any():
                raise SystemExit(f"cover {x0, y0, x1, y1} is outside its room")
    reach = ground_distance(label, (PLAYER[0] // C, PLAYER[1] // C))
    if (reach[label >= 0] >= 10 ** 8).any():
        raise SystemExit("unreachable open cells")
    spec = {
        "comment": "Source of truth for the v0.3 dungeon (DESIGN.md 6), generated by tools/gen_dungeon_layout.py "
                   "(rooms/corridors drawn on a 16 px cell grid, solid rock as 'rock' blocks whose height follows "
                   "what is open to the north). All positions are pixels of the final image (the lab render), screen "
                   "aligned: x right, y down; footprints are ground projections (a 32x16 footprint is a 32x32 ground-px "
                   "square). Heights are in metres, 40.42 px per metre. Zones only drive the floor look (style = tones and "
                   "pattern, see floor_styles); every accent is the same warm amber. Enemies carry a 'pack' (0..8, nearest "
                   "to the start first) that groups them for encounters.",
        "image": [1280, 1280],
        "pixels_per_metre": 40.42,
        "camera_elevation_degrees": 30,
        "floor": {"rect": FLOOR},
        "boundary_wall_height_m": 2.4,
        "shadows": True,
        "shadowExtent": 60,
        "shadowMapSize": 4096,
        "baked_shadows": False,
        "baked_glow": True,
        "floor_styles": STYLES,
        "arenas": [{
            "name": "dungeon_01",
            "title": "Mazmorra",
            "zones": zones_for(label, styles),
            "doors": [],
            "blocks": blocks + covers,
            "player_start": list(PLAYER),
            "enemies": enemies,
            "rooms": {n: {"title": r["title"], "rects": [[a * C for a in rc] for rc in r["rects"] + r.get("extra", [])],
                          "wall_height_m": r["h"]} for n, r in ROOMS.items()},
        }],
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print(f"rock blocks {len(blocks)}, covers {len(covers)}, enemies {len(enemies)}, packs {len(order)}")
    for pack, n in enumerate(order):
        d = min(dist[int(y), int(x)] for _, x, y in ROOMS[n]["pack"])
        print(f"  pack {pack}: {n:8s} {len(ROOMS[n]['pack'])} enemies, ground distance {d * C} px ({d * C / 256:.1f} screens)")


def ground_distance(label, start):
    """BFS over open cells, step cost 1 horizontally and 2 vertically (the floor is 2:1 on screen)."""
    import heapq
    INF = 10 ** 9
    d = np.full((N, N), INF, dtype=np.int64)
    sx, sy = start
    d[sy, sx] = 0
    pq = [(0, sx, sy)]
    while pq:
        cur, x, y = heapq.heappop(pq)
        if cur > d[y, x]:
            continue
        for dx, dy, cost in ((1, 0, 1), (-1, 0, 1), (0, 1, 2), (0, -1, 2)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < N and 0 <= ny < N and label[ny, nx] >= 0 and cur + cost < d[ny, nx]:
                d[ny, nx] = cur + cost
                heapq.heappush(pq, (cur + cost, nx, ny))
    return d


if __name__ == "__main__":
    main()
