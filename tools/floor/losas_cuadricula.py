"""Generate two deterministic cathedral floor atlases of rectangular slabs."""
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
PALETTE_PATH = ROOT / "assets/environment/cathedral/palette/palette.json"
OUT_ROOT = ROOT / "assets/environment/cathedral/floor"
SEED = 20261108
PERIOD = 128


def rgb555(hex_color):
    value = int(hex_color, 16)
    return tuple(round(((value >> shift) & 31) * 255 / 31) for shift in (0, 5, 10))


def make_palette():
    source = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))["bgr555_hex"]["props"]
    colors = [(sum(c * w for c, w in zip(rgb555(h), (0.2126, 0.7152, 0.0722))), h, rgb555(h)) for h in source]
    # Keep the dark and middle stone range already present in the neutral prop palette.
    chosen = [item for item in sorted(colors) if 26 <= item[0] <= 102]
    chosen = chosen[::2]
    return [item[1] for item in chosen], np.asarray([item[2] for item in chosen], dtype=np.int16)


def make_slabs(variant, palette_rgb):
    rng = random.Random(SEED + variant * 7919)
    slab_w, slab_h = 32, 16
    slabs = []
    # Ten quiet stone faces, including worn edges, hairline cracks, a broken corner and a stain.
    for kind in range(10):
        face = np.zeros((slab_h, slab_w, 3), dtype=np.uint8)
        base = (74, 71, 64) if variant == 0 else (72, 69, 62)
        face[:] = base
        # Low contrast mottling in broad patches and sparse grains.
        for _ in range(11 if variant == 0 else 14):
            x, y = rng.randrange(3, 30), rng.randrange(2, 14)
            rw, rh = rng.randrange(2, 9), rng.randrange(1, 4)
            delta = rng.choice((-10, -7, -4, 4, 6))
            face[y:min(y + rh, 15), x:min(x + rw, 31)] = np.clip(
                face[y:min(y + rh, 15), x:min(x + rw, 31)].astype(np.int16) + delta, 0, 255)
        for _ in range(18):
            x, y = rng.randrange(2, 31), rng.randrange(2, 15)
            delta = rng.choice((-13, -9, 7))
            face[y, x] = np.clip(face[y, x].astype(np.int16) + delta, 0, 255)

        # Distinct but restrained imperfections, never directional lighting.
        if kind in (2, 7, 9):
            x, y = rng.randrange(8, 25), rng.randrange(5, 11)
            for dx, dy in ((0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3)):
                if y + dy < 15 and x + dx < 31:
                    face[y + dy, x + dx] = (43, 41, 38)
        if kind == 5:  # chipped, broken lower-right corner
            face[12:15, 27:31] = (46, 44, 41)
            face[13:15, 29:31] = (39, 37, 35)
        if kind == 8:  # subdued grime stain
            for y in range(6, 12):
                for x in range(11, 22):
                    if ((x - 16) ** 2) / 36 + ((y - 9) ** 2) / 7 < 1:
                        face[y, x] = np.clip(face[y, x].astype(np.int16) - 9, 0, 255)

        # Symmetric edge joints let any whole-slab H/V flip meet any neighbor cleanly.
        joint = (42, 40, 37) if variant == 0 else (31, 29, 27)
        face[0, :] = joint
        face[-1, :] = joint
        face[:, 0] = joint
        face[:, -1] = joint

        # Quantize each slab against the selected, source-derived BGR555 prop colors.
        flat = face.reshape(-1, 3).astype(np.int16)
        nearest = ((flat[:, None, :] - palette_rgb[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
        slabs.append(palette_rgb[nearest].astype(np.uint8).reshape(slab_h, slab_w, 3))
    return slabs


def orient(a, h, v):
    if h:
        a = a[:, ::-1]
    if v:
        a = a[::-1, :]
    return a


def canonical_tile(tile):
    options = [(tile, 0, 0), (tile[:, ::-1], 1, 0), (tile[::-1, :], 0, 1), (tile[::-1, ::-1], 1, 1)]
    return min(options, key=lambda item: item[0].tobytes())


def generate_one(name, variant, palette_hex, palette_rgb):
    rng = random.Random(SEED + variant * 7919 + 13)
    slabs = make_slabs(variant, palette_rgb)
    canvas = np.empty((PERIOD, PERIOD, 3), dtype=np.uint8)
    # 4 x 8 slab rows with alternating half-width offsets (128 px remains an exact period).
    for row in range(8):
        offset = 16 if row % 2 else 0
        pattern = [(rng.randrange(10), rng.randrange(2), rng.randrange(2)) for _ in range(4)]
        for col in range(-1, 5):
            origin_x = col * 32 + offset
            kind, h, v = pattern[col % 4]
            slab = orient(slabs[kind], h, v)
            left, right = max(0, origin_x), min(PERIOD, origin_x + 32)
            if left < right:
                canvas[row * 16:(row + 1) * 16, left:right] = slab[:, left - origin_x:right - origin_x]

    tiles, tile_ids, floor_map = [], {}, []
    for ty in range(16):
        map_row = []
        for tx in range(16):
            tile = canvas[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8]
            canonical, h, v = canonical_tile(tile)
            key = canonical.tobytes()
            if key not in tile_ids:
                tile_ids[key] = len(tiles)
                tiles.append(canonical.copy())
            map_row.append({"t": tile_ids[key], "h": h, "v": v})
        floor_map.append(map_row)

    # Rebuild solely from the serialized tile pixels and flip flags.
    restored = np.empty_like(canvas)
    json_tiles = []
    for tile in tiles:
        idx = ((tile[:, :, None, :] == palette_rgb[None, None, :, :]).all(axis=3)).argmax(axis=2)
        json_tiles.append(idx.reshape(-1).astype(int).tolist())
    for ty, row in enumerate(floor_map):
        for tx, cell in enumerate(row):
            tile = tiles[cell["t"]]
            restored[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8] = orient(tile, cell["h"], cell["v"])
    if not np.array_equal(canvas, restored):
        raise RuntimeError("JSON tile reconstruction differs from quantized source")

    expanded = np.tile(restored, (2, 4, 1))  # 512 x 256 px
    out = OUT_ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.concatenate(tiles, axis=1), "RGB").save(out / "tiles.png")
    Image.fromarray(expanded, "RGB").save(out / "floor_512x256.png")
    Image.fromarray(expanded, "RGB").resize((1536, 768), Image.Resampling.NEAREST).save(out / "floor_512x256_x3.png")
    doc = {"palette": palette_hex, "tiles": json_tiles, "floor_map": floor_map, "period_tiles": [16, 16]}
    (out / "floor.json").write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8", newline="")

    worst = 0
    for y in range(16):
        for x in range(16):
            ids = {floor_map[(y + dy) % 16][(x + dx) % 16]["t"] for dy in range(25) for dx in range(33)}
            worst = max(worst, len(ids))
    # Exact periodicity is checked by construction against the 128x128 reconstructed period.
    wrap_check = np.array_equal(expanded[:, :128], np.tile(restored, (2, 1, 1))) and np.array_equal(expanded[:128], np.tile(restored, (1, 4, 1)))
    stats = {"unique_tiles": len(tiles), "worst_window_33x25_unique_tiles": worst,
             "palette_colors_used": len(set(int(i) for row in json_tiles for i in row)),
             "period_seam_exact": bool(wrap_check), "json_reconstruction_pixel_exact": True,
             "period_tiles": [16, 16], "slab_variants": 10}
    (out / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8", newline="")
    return stats


def main():
    palette_hex, palette_rgb = make_palette()
    results = {
        "losas_cuadricula": generate_one("losas_cuadricula", 0, palette_hex, palette_rgb),
        "losas_cuadricula_b": generate_one("losas_cuadricula_b", 1, palette_hex, palette_rgb),
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
