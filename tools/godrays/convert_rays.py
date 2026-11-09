#!/usr/bin/env python3
"""Convert additive RGB ray PNGs to compact 4bpp Nintendo DS OBJ graphics."""
import argparse
from pathlib import Path

from PIL import Image

MAX_SUB_BYTES = 16 * 1024
MAX_RAY_DIM = (256, 128)
CHUNK = 16
MAX_PIECES_PER_RAY = 64


def rgb15(rgb):
    r, g, b = (max(0, min(31, round(c * 31 / 255))) for c in rgb)
    return r | (g << 5) | (b << 10)


def c_array(name, ctype, values, per_line=12):
    lines = [f"const {ctype} {name}[] = {{"]
    for i in range(0, len(values), per_line):
        lines.append("    " + ", ".join(str(x) for x in values[i:i + per_line]) + ",")
    lines.append("};")
    return "\n".join(lines)


def quantize(image, dither=False):
    rgba = image.convert("RGBA")
    colors = {}
    samples = []
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = rgba.getpixel((x, y))
            if a < 16 or max(r, g, b) <= 5:
                samples.append(None)
                continue
            if dither:
                delta = ((x & 3) * 2 + (y & 3) * 2 - 6)
                r, g, b = (max(0, min(255, c + delta)) for c in (r, g, b))
            key = ((r >> 3), (g >> 3), (b >> 3))
            colors[key] = colors.get(key, 0) + 1
            samples.append(key)
    ranked = sorted(colors, key=lambda c: (colors[c], sum(c)), reverse=True)[:15]
    palette = [0] + [rgb15(tuple(c * 255 // 31 for c in color)) for color in ranked]
    indices = []
    for key in samples:
        if key is None or not ranked:
            indices.append(0)
            continue
        nearest = min(range(len(ranked)), key=lambda i: sum((key[j] - ranked[i][j]) ** 2 for j in range(3)))
        indices.append(nearest + 1)
    return indices, palette


def encode_chunk(indices, image_w, x0, y0, w, h):
    # SpriteMapping_1D_32: 32x32 4bpp sprites are 4x4 tiles in row-major order.
    pixels = []
    for ty in range(0, CHUNK, 8):
        for tx in range(0, CHUNK, 8):
            for py in range(8):
                for px in range(8):
                    x, y = x0 + tx + px, y0 + ty + py
                    pixels.append(indices[y * image_w + x] if x < x0 + w and y < y0 + h else 0)
    out = bytearray()
    for i in range(0, len(pixels), 2):
        out.append(pixels[i] | (pixels[i + 1] << 4))
    return bytes(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("png", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("source/godrays_gfx.c"))
    parser.add_argument("--dither", action="store_true", help="apply a subtle ordered 4x4 color dither")
    args = parser.parse_args()

    tiles = bytearray()
    palettes = []
    pieces = []
    ray_ranges = []
    ray_stats = []
    for ray_index, path in enumerate(args.png):
        if ray_index >= 15:
            raise SystemExit("at most 15 ray PNGs fit alongside the dust palette in OBJ palette RAM")
        image = Image.open(path)
        if image.format != "PNG" or image.mode not in ("RGB", "RGBA"):
            raise SystemExit(f"{path}: expected an RGB or RGBA PNG (got {image.format}/{image.mode})")
        if image.width % CHUNK or image.height % CHUNK or image.width > MAX_RAY_DIM[0] or image.height > MAX_RAY_DIM[1]:
            raise SystemExit(f"{path}: dimensions must be multiples of {CHUNK}, at most 256x128 (got {image.size})")
        indices, palette = quantize(image, args.dither)
        palette += [0] * (16 - len(palette))
        palettes.extend(palette)
        first_piece = len(pieces)
        ray_bytes = 0
        for y in range(0, image.height, CHUNK):
            for x in range(0, image.width, CHUNK):
                block = encode_chunk(indices, image.width, x, y, image.width, image.height)
                if not any(block):
                    continue
                if len(pieces) - first_piece >= MAX_PIECES_PER_RAY:
                    raise SystemExit(f"{path}: visible light needs more than {MAX_PIECES_PER_RAY} OAM pieces")
                if len(tiles) + len(block) > MAX_SUB_BYTES:
                    raise SystemExit(f"sprite tiles exceed sub OBJ bank ({MAX_SUB_BYTES} bytes)")
                offset = len(tiles)
                tiles.extend(block)
                pieces.append((ray_index, x, y, CHUNK, CHUNK, offset))
                ray_bytes += len(block)
        if len(pieces) == first_piece:
            raise SystemExit(f"{path}: no visible light pixels to convert")
        ray_ranges.append((first_piece, len(pieces) - first_piece))
        ray_stats.append((path.name, len(pieces) - first_piece, ray_bytes))
        print(f"{path.name}: {len(pieces) - first_piece} piezas, {ray_bytes} bytes")

    # Two 8x8 dust animation frames, soft circles in their own final palette.
    dust_palette = [0, rgb15((255, 202, 112))] + [0] * 14
    palettes.extend(dust_palette)
    dust_first = len(tiles)
    for frame in range(2):
        for y in range(8):
            for x in range(8):
                dx, dy = x * 2 - 7, y * 2 - 7
                radius = dx * dx + dy * dy
                on = radius <= (20 if frame == 0 else 28)
                if (y & 1) and frame:
                    on = on and x not in (0, 7)
                # One 8x8 4bpp tile, packed low nibble first.
                if x == 0:
                    row = []
                row.append(1 if on else 0)
                if x == 7:
                    for px in range(0, 8, 2):
                        tiles.append(row[px] | (row[px + 1] << 4))
    if len(tiles) > MAX_SUB_BYTES:
        raise SystemExit(f"ray and dust tiles exceed sub OBJ bank ({MAX_SUB_BYTES} bytes)")
    header = [
        "#ifndef GODRAYS_GFX_H", "#define GODRAYS_GFX_H", "#include <stdint.h>",
        "typedef struct { uint8_t ray, width, height; int16_t x, y; uint16_t tile_offset; } GodrayPiece;",
        "typedef struct { uint16_t first_piece, piece_count; } GodrayRange;",
        f"#define GODRAY_RAY_COUNT {len(ray_ranges)}", f"#define GODRAY_PIECE_COUNT {len(pieces)}",
        f"#define GODRAY_TILE_BYTES {len(tiles)}", f"#define GODRAY_DUST_OFFSET {dust_first}",
        "extern const uint8_t g_godray_tiles[GODRAY_TILE_BYTES];",
        f"extern const uint16_t g_godray_palettes[{len(palettes)}];",
        "extern const GodrayPiece g_godray_pieces[GODRAY_PIECE_COUNT];",
        "extern const GodrayRange g_godray_ranges[GODRAY_RAY_COUNT];", "#endif", ""
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        f.write("#include \"godrays_gfx.h\"\n\n")
        for name, piece_count, ray_bytes in ray_stats:
            f.write(f"/* {name}: {piece_count} piezas, {ray_bytes} bytes */\n")
        f.write(f"/* total: {len(pieces)} piezas, {len(tiles)} bytes incluyendo motas */\n\n")
        f.write(c_array("g_godray_tiles", "uint8_t", list(tiles), 16) + "\n\n")
        f.write(c_array("g_godray_palettes", "uint16_t", palettes, 8) + "\n\n")
        f.write("const GodrayPiece g_godray_pieces[GODRAY_PIECE_COUNT] = {\n")
        for ray, x, y, width, height, offset in pieces:
            f.write(f"    {{{ray}, {width}, {height}, {x}, {y}, {offset}}},\n")
        f.write("};\n\nconst GodrayRange g_godray_ranges[GODRAY_RAY_COUNT] = {\n")
        for first, count in ray_ranges:
            f.write(f"    {{{first}, {count}}},\n")
        f.write("};\n")
    header_path = Path("include/godrays_gfx.h")
    with header_path.open("w", newline="") as f:
        f.write("\n".join(header) + "\n")
    print(f"Total: {len(pieces)} piezas, {len(tiles)} bytes (incluye motas), {len(ray_ranges)} haces + polvo")


if __name__ == "__main__":
    main()
