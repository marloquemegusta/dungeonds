#!/usr/bin/env python3
"""
convert_iso_to_c.py - Converts the baked sprites and generates the dungeon map
into C for DungeonDS.

Usage:
    python tools/convert_iso_to_c.py --preset e30
    python tools/convert_iso_to_c.py --preset e60

Emits:
    include/dungeon_data.h / source/dungeon_data.c
    include/player_sprite.h / source/player_sprite.c

Sprite transparency is converted to the DS 1-bit BGR555 alpha. Ground shadows
remain separate 4-bit coverage masks, generated from Blender's Shadow Catcher
pass and composited over the rendered floor tiles at runtime.
"""

import os
import sys
import argparse
import warnings
import json

warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_look as look
from shadow_masks import coverage_bounds, read_shadow_coverage, shadow_coverage

from PIL import Image

ROOT = r"C:\codexlocal\dungeonds"

FLOOR_NAMES = ["F0_crypt", "F1_obsidian", "F2_bone", "F3_crimson", "F4_worn"]
OBJ_BASE_NAMES = [
    "WR_crypt", "WC_crypt",
    "WR_buttress", "WC_buttress",
    "WR_ossuary", "WC_ossuary",
    "P_soul", "P_broken",
    "AR_row", "AR_col",
]
OBJ_ROTATIONS = (0, 90, 180, 270)
OBJ_NAMES = [f"{name}_r{rot:03d}" for name in OBJ_BASE_NAMES for rot in OBJ_ROTATIONS]

FLOOR_CRYPT, FLOOR_OBSIDIAN, FLOOR_BONE, FLOOR_CRIMSON, FLOOR_WORN = range(5)

WR_CRYPT, WC_CRYPT = 0, 4
WR_BUTTRESS, WC_BUTTRESS = 8, 12
WR_OSSUARY, WC_OSSUARY = 16, 20
P_SOUL, P_BROKEN = 24, 28
AR_ROW, AR_COL = 32, 36

def sprite(base, rot):
    return base + OBJ_ROTATIONS.index(rot)

MAP_COLS, MAP_ROWS = 36, 36
VOID = 255

ALPHA_CUT = 110   # below this the pixel is discarded (clears catcher haze + faint penumbra)


def px_bgr555(r, g, b, a, x, y):
    """BGR555 with a 1-bit alpha. A hard cut-off keeps baked shadows crisp;
    dithering them only turned into static on the DS panel."""
    if a < ALPHA_CUT:
        return 0
    return ((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10) | 0x8000


def write_pixels(c, path, w, h, indent):
    im = Image.open(path).convert("RGBA")
    assert im.size == (w, h), f"{path}: {im.size} != {(w, h)}"
    data = list(im.getdata())
    c.write(indent)
    for i, (r, g, b, a) in enumerate(data):
        x = i % w
        y = i // w
        c.write(f"0x{px_bgr555(r, g, b, a, x, y):04X},")
        if (i + 1) % 16 == 0:
            c.write("\n" + (indent if i + 1 < len(data) else ""))
        else:
            c.write(" ")
    c.write("\n")


def write_shadow_mask(c, path, w, h, indent):
    source_w = 128
    source_h = 128
    coverage = read_shadow_coverage(path, (source_w, source_h))
    offset_x = (source_w - w) // 2
    offset_y = (source_h - h) // 2
    cropped = [
        coverage[(offset_y + y) * source_w + offset_x + x]
        for y in range(h) for x in range(w)
    ]
    c.write(indent)
    for i in range(0, len(cropped), 2):
        packed = (cropped[i] >> 4) | ((cropped[i + 1] >> 4) << 4)
        c.write(f"0x{packed:02X},")
        if (i // 2 + 1) % 32 == 0:
            c.write("\n" + (indent if i + 2 < len(cropped) else ""))
        else:
            c.write(" ")
    c.write("\n")
    return coverage_bounds(cropped, w, h)


def build_map(layout="dungeon"):
    floor = [[VOID] * MAP_COLS for _ in range(MAP_ROWS)]
    obj = [[0] * MAP_COLS for _ in range(MAP_ROWS)]

    lo, hi = 2, MAP_COLS - 3
    cx, cy = 17, 17
    aisles = (8, 14, 20, 26)   # colonnade lines, kept aligned with the pillars

    seam_y = (WR_CRYPT, WR_BUTTRESS, WR_OSSUARY)
    seam_x = (WC_CRYPT, WC_BUTTRESS, WC_OSSUARY)
    for r in range(lo, hi + 1):
        for c in range(lo, hi + 1):
            d = max(abs(c - cx), abs(r - cy))
            if d <= 1:
                floor[r][c] = FLOOR_CRIMSON
            elif d == 2:
                floor[r][c] = FLOOR_BONE
            elif d == 3:
                floor[r][c] = FLOOR_OBSIDIAN
            elif (c in aisles) or (r in aisles):
                floor[r][c] = FLOOR_OBSIDIAN
            elif (c * 7 + r * 5) % 23 == 0:
                floor[r][c] = FLOOR_WORN   # sparse worn accents, breaks up repetition
            else:
                floor[r][c] = FLOOR_CRYPT

    for r in range(lo, hi + 1):
        # Fixed column, varying row: the wall runs along world Y. In the
        # baked kit the WR family is the Y-running wall; WC is its X-running
        # counterpart (the names describe the source kit, not map axes).
        base = seam_y[(r - lo) % len(seam_y)] if layout in ("modular-seam", "integration-showcase") else (WR_BUTTRESS if r % 5 == 0 else WR_CRYPT)
        obj[r][lo] = sprite(base, 180) + 1
        obj[r][hi] = sprite(base, 0) + 1
    for c in range(lo + 1, hi):
        # Fixed row, varying column: the wall runs along world X.
        base = seam_x[(c - lo) % len(seam_x)] if layout in ("modular-seam", "integration-showcase") else (WC_BUTTRESS if c % 5 == 0 else WC_CRYPT)
        # WR's authored zero rotation already runs along world X. The two
        # opposite perimeter sides only need the 180-degree facing variant.
        obj[lo][c] = sprite(base, 180) + 1
        obj[hi][c] = sprite(base, 0) + 1

    if layout == "integration-showcase":
        # Replace full 2 m structural bays with their matching arch modules;
        # source trims may overhang, but their native pivots share the bay centre.
        for c in (7, 12, 17, 22, 27):
            obj[lo][c] = sprite(AR_COL, 180) + 1
            obj[hi][c] = sprite(AR_COL, 0) + 1
        for r in (7, 12, 17, 22, 27):
            obj[r][lo] = sprite(AR_ROW, 180) + 1
            obj[r][hi] = sprite(AR_ROW, 0) + 1
        for c in (9, 14, 20, 25):
            for r in (9, 14, 20, 25):
                soul_rot = 180 if (c + r) % 2 == 0 else 90
                obj[r][c] = (sprite(P_BROKEN, soul_rot) if (c + r) % 3 == 0 else sprite(P_SOUL, soul_rot)) + 1
    elif layout != "modular-seam":
        for c in (9, 18, 26):
            obj[lo][c] = sprite(WC_OSSUARY, 180) + 1
            obj[hi][c] = sprite(WC_OSSUARY, 0) + 1
        for r in (9, 18, 26):
            obj[r][lo] = sprite(WR_OSSUARY, 180) + 1
            obj[r][hi] = sprite(WR_OSSUARY, 0) + 1
        for c in (13, 22):
            obj[lo][c] = sprite(AR_COL, 180) + 1
            obj[hi][c] = sprite(AR_COL, 0) + 1

        for c in (8, 14, 20, 26):
            for r in (8, 14, 20, 26):
                soul_rot = 180 if (c + r) % 2 == 0 else 90
                obj[r][c] = (sprite(P_BROKEN, soul_rot) if (c + r) % 3 == 0 else sprite(P_SOUL, soul_rot)) + 1

        for k in (7, 27):
            obj[k][cx] = sprite(AR_ROW, 180) + 1
            obj[cy][k] = sprite(AR_COL, 180) + 1

    return floor, obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(look.PRESETS), default="e30")
    ap.add_argument("--layout", choices=("dungeon", "modular-seam", "integration-showcase"), default="dungeon")
    args = ap.parse_args()

    tile_h = look.tile_h(args.preset)
    obj_shadow_canvas = 96
    sprite_dir = os.path.join(ROOT, "assets", f"dungeon_{args.preset}")
    player_sheet = os.path.join(ROOT, "assets", "characters", "monster", f"player_{args.preset}.png")
    player_shadow_sheet = os.path.join(ROOT, "assets", "characters", "monster", f"player_{args.preset}_shadow.png")
    player_anchor_path = os.path.join(ROOT, "assets", "characters", "monster", f"player_{args.preset}_anchor.json")
    charger_sheet = os.path.join(ROOT, "assets", "characters", "charger", f"charger_{args.preset}.png")
    charger_shadow_sheet = os.path.join(ROOT, "assets", "characters", "charger", f"charger_{args.preset}_shadow.png")
    if os.path.isfile(player_anchor_path):
        with open(player_anchor_path, encoding="utf-8") as f:
            player_anchor = json.load(f)["anchor_pixel"]
        if len(player_anchor) != 2 or any(not 0 <= int(v) < look.CHAR_CANVAS for v in player_anchor):
            raise ValueError(f"invalid player anchor in {player_anchor_path}: {player_anchor}")
        player_anchor_x, player_anchor_y = map(int, player_anchor)
    else:
        player_anchor_x, player_anchor_y = look.CHAR_CANVAS // 2, look.CHAR_ANCHOR_Y

    floor, obj = build_map(args.layout)

    with open(os.path.join(ROOT, "include", "dungeon_data.h"), "w", encoding="utf-8") as h:
        h.write(f"""#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

// Baked view preset: {args.preset} (elevation {look.elevation(args.preset):.0f} deg)
#define FLOOR_TILE_W {look.FLOOR_TILE_W}
#define FLOOR_TILE_H {tile_h}
#define NUM_FLOOR_TILES {len(FLOOR_NAMES)}

#define OBJ_SPRITE_W {look.OBJ_CANVAS}
#define OBJ_SPRITE_H {look.OBJ_CANVAS}
#define OBJ_SHADOW_W {obj_shadow_canvas}
#define OBJ_SHADOW_H {obj_shadow_canvas}
#define OBJ_ANCHOR_Y {look.GROUND_ANCHOR_Y}
#define NUM_OBJ_SPRITES {len(OBJ_NAMES)}

#define MAP_COLS {MAP_COLS}
#define MAP_ROWS {MAP_ROWS}
#define MAP_VOID {VOID}

enum {{
    FLOOR_CRYPT = 0,
    FLOOR_OBSIDIAN = 1,
    FLOOR_BONE = 2,
    FLOOR_CRIMSON = 3,
    FLOOR_WORN = 4
}};

enum {{
    OBJ_WR_CRYPT = 0,
    OBJ_WC_CRYPT = 4,
    OBJ_WR_BUTTRESS = 8,
    OBJ_WC_BUTTRESS = 12,
    OBJ_WR_OSSUARY = 16,
    OBJ_WC_OSSUARY = 20,
    OBJ_P_SOUL = 24,
    OBJ_P_BROKEN = 28,
    OBJ_AR_ROW = 32,
    OBJ_AR_COL = 36
}};

extern const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_W * FLOOR_TILE_H];
extern const uint16_t g_obj_sprites[NUM_OBJ_SPRITES][OBJ_SPRITE_W * OBJ_SPRITE_H];
extern const uint8_t g_obj_shadow_masks[NUM_OBJ_SPRITES][OBJ_SHADOW_W * OBJ_SHADOW_H / 2];
extern const uint8_t g_obj_shadow_bounds[NUM_OBJ_SPRITES][4];
extern const uint8_t g_floor_map[MAP_ROWS][MAP_COLS];
extern const uint8_t g_obj_map[MAP_ROWS][MAP_COLS];

#endif // DUNGEON_DATA_H
""")

    with open(os.path.join(ROOT, "source", "dungeon_data.c"), "w", encoding="utf-8") as c:
        c.write('#include "dungeon_data.h"\n\n')
        c.write(f"// {look.FLOOR_TILE_W}x{tile_h} dimetric floor diamonds (BGR555, bit15 = opaque)\n")
        c.write(f"const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_W * FLOOR_TILE_H] __attribute__((aligned(4))) = {{\n")
        for fn in FLOOR_NAMES:
            c.write(f"    // {fn}\n    {{\n        ")
            write_pixels(c, os.path.join(sprite_dir, fn + ".png"), look.FLOOR_TILE_W, tile_h, "        ")
            c.write("    },\n")
        c.write("};\n\n")

        c.write(f"// {look.OBJ_CANVAS}x{look.OBJ_CANVAS} upright walls, pillars and arches with baked shadows\n")
        c.write(f"const uint16_t g_obj_sprites[NUM_OBJ_SPRITES][OBJ_SPRITE_W * OBJ_SPRITE_H] __attribute__((aligned(4))) = {{\n")
        for on in OBJ_NAMES:
            c.write(f"    // {on}\n    {{\n        ")
            write_pixels(c, os.path.join(sprite_dir, on + ".png"), look.OBJ_CANVAS, look.OBJ_CANVAS, "        ")
            c.write("    },\n")
        c.write("};\n\n")

        c.write("// Pre-rendered 3D shadow-catcher coverage, one 8-bit mask per object orientation\n")
        c.write("const uint8_t g_obj_shadow_masks[NUM_OBJ_SPRITES][OBJ_SHADOW_W * OBJ_SHADOW_H / 2] = {\n")
        object_bounds = []
        for on in OBJ_NAMES:
            c.write(f"    // {on}_shadow\n    {{\n")
            object_bounds.append(write_shadow_mask(
                c, os.path.join(sprite_dir, on + "_shadow.png"),
                obj_shadow_canvas, obj_shadow_canvas, "        "))
            c.write("    },\n")
        c.write("};\n\n")
        c.write("const uint8_t g_obj_shadow_bounds[NUM_OBJ_SPRITES][4] = {\n")
        for bounds in object_bounds:
            c.write("    { " + ", ".join(map(str, bounds)) + " },\n")
        c.write("};\n\n")

        c.write(f"// Floor map ({MAP_ROWS} rows x {MAP_COLS} cols), {VOID} = void\n")
        c.write(f"const uint8_t g_floor_map[{MAP_ROWS}][{MAP_COLS}] = {{\n")
        for r in range(MAP_ROWS):
            c.write("    { " + ", ".join(f"{v:3d}" for v in floor[r]) + " },\n")
        c.write("};\n\n")

        c.write(f"// Object map ({MAP_ROWS} rows x {MAP_COLS} cols), 0 = none\n")
        c.write(f"const uint8_t g_obj_map[{MAP_ROWS}][{MAP_COLS}] = {{\n")
        for r in range(MAP_ROWS):
            c.write("    { " + ", ".join(f"{v:2d}" for v in obj[r]) + " },\n")
        c.write("};\n")

    # --- character spritesheets (hero player and charger enemy) ---
    cell = look.CHAR_CANVAS
    shadow_cell = cell * 3 // 2
    n_dirs, n_frames = 8, 8

    player_im = Image.open(player_sheet).convert("RGBA")
    assert player_im.size == (n_frames * cell, n_dirs * cell), player_im.size
    player_sh = Image.open(player_shadow_sheet).convert("RGBA")
    assert player_sh.size == (n_dirs * shadow_cell, shadow_cell), player_sh.size

    charger_im = Image.open(charger_sheet).convert("RGBA")
    assert charger_im.size == (n_frames * cell, n_dirs * cell), charger_im.size
    charger_sh = Image.open(charger_shadow_sheet).convert("RGBA")
    assert charger_sh.size == (n_dirs * shadow_cell, shadow_cell), charger_sh.size

    char_w = 48
    char_h = 40
    crop_x0 = 8
    crop_y0 = 4
    char_anchor_x = player_anchor_x - crop_x0
    char_anchor_y = player_anchor_y - crop_y0

    with open(os.path.join(ROOT, "include", "player_sprite.h"), "w", encoding="utf-8") as h:
        h.write(f"""#ifndef PLAYER_SPRITE_INCLUDED
#define PLAYER_SPRITE_INCLUDED

#include <nds.h>

#define PLAYER_SPRITE_W {char_w}
#define PLAYER_SPRITE_H {char_h}
#define PLAYER_SHADOW_W {shadow_cell}
#define PLAYER_SHADOW_H {shadow_cell}
#define PLAYER_NUM_DIRS {n_dirs}
#define PLAYER_NUM_FRAMES {n_frames}

 // The ground origin is the shared lower anchor of every sprite canvas.
#define PLAYER_ANCHOR_X {char_anchor_x}
#define PLAYER_ANCHOR_Y {char_anchor_y}

#define NUM_CHARACTERS 2

enum {{
    CHAR_HERO = 0,
    CHAR_CHARGER = 1
}};

typedef struct {{
    const char *name;
    int speed;        // 8.8 fixed point speed (px/frame)
    int anim_period;  // ticks per frame
}} CharacterConfig;

extern const CharacterConfig g_characters[NUM_CHARACTERS];

// Hero frames & shadows (Walking)
extern const uint16_t g_player_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_player_shadow_masks[PLAYER_NUM_DIRS][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_player_shadow_bounds[PLAYER_NUM_DIRS][4];

// Charger enemy frames & shadows (Run / Charge)
extern const uint16_t g_charger_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_charger_shadow_masks[PLAYER_NUM_DIRS][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_charger_shadow_bounds[PLAYER_NUM_DIRS][4];

// Fast indexed lookups:
extern const uint16_t (* const g_character_frames[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t (* const g_character_shadow_masks[NUM_CHARACTERS])[PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[4];

#endif // PLAYER_SPRITE_INCLUDED
""")

    def write_char_arrays(c, var_prefix, label, sheet, shadow_sheet):
        c.write(f"// {char_w}x{char_h} BGR555 {label} frames, {n_dirs} directions x {n_frames} frames\n")
        c.write(f"const uint16_t {var_prefix}_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES]"
                f"[PLAYER_SPRITE_W * PLAYER_SPRITE_H] __attribute__((aligned(4))) = {{\n")
        for d in range(n_dirs):
            c.write(f"    // Direction {d}\n    {{\n")
            for f in range(n_frames):
                crop = sheet.crop((f * cell + crop_x0, d * cell + crop_y0,
                                   f * cell + crop_x0 + char_w, d * cell + crop_y0 + char_h))
                c.write(f"        // Frame {f}\n        {{\n            ")
                data = list(crop.getdata())
                for i, (r, g, b, a) in enumerate(data):
                    x = i % char_w
                    y = i // char_w
                    c.write(f"0x{px_bgr555(r, g, b, a, x, y):04X},")
                    if (i + 1) % 16 == 0:
                        c.write("\n            " if i + 1 < len(data) else "\n")
                    else:
                        c.write(" ")
                c.write("\n        },\n")
            c.write("    },\n")
        c.write("};\n\n")

        c.write(f"// Pre-rendered {label} shadow coverage masks, one per facing\n")
        c.write(f"const uint8_t {var_prefix}_shadow_masks[PLAYER_NUM_DIRS][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] = {{\n")
        bounds_list = []
        for d in range(n_dirs):
            crop = shadow_sheet.crop((d * shadow_cell, 0, (d + 1) * shadow_cell, shadow_cell))
            coverage = shadow_coverage(crop, f"{label} shadow direction {d}")
            bounds_list.append(coverage_bounds(coverage, shadow_cell, shadow_cell))
            c.write(f"    // Direction {d}\n    {{\n")
            for i in range(0, len(coverage), 2):
                packed = (coverage[i] >> 4) | ((coverage[i + 1] >> 4) << 4)
                c.write(f"0x{packed:02X},")
                if (i // 2 + 1) % 32 == 0:
                    c.write("\n        " if i + 2 < len(coverage) else "\n")
                else:
                    c.write(" ")
            c.write("\n    },\n")
        c.write("};\n\n")
        c.write(f"const uint8_t {var_prefix}_shadow_bounds[PLAYER_NUM_DIRS][4] = {{\n")
        for bounds in bounds_list:
            c.write("    { " + ", ".join(map(str, bounds)) + " },\n")
        c.write("};\n\n")

    with open(os.path.join(ROOT, "source", "player_sprite.c"), "w", encoding="utf-8") as c:
        c.write('#include "player_sprite.h"\n\n')
        c.write('const CharacterConfig g_characters[NUM_CHARACTERS] = {\n')
        c.write('    { "Hero (Monster)", 181, 3 },\n')
        c.write('    { "Enemy Charger",  362, 2 },\n')
        c.write('};\n\n')

        write_char_arrays(c, "g_player", "hero", player_im, player_sh)
        write_char_arrays(c, "g_charger", "charger", charger_im, charger_sh)

        c.write('const uint16_t (* const g_character_frames[NUM_CHARACTERS])[PLAYER_NUM_FRAMES]'
                '[PLAYER_SPRITE_W * PLAYER_SPRITE_H] = {\n'
                '    g_player_frames,\n'
                '    g_charger_frames\n'
                '};\n\n')
        c.write('const uint8_t (* const g_character_shadow_masks[NUM_CHARACTERS])'
                '[PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] = {\n'
                '    g_player_shadow_masks,\n'
                '    g_charger_shadow_masks\n'
                '};\n\n')
        c.write('const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[4] = {\n'
                '    g_player_shadow_bounds,\n'
                '    g_charger_shadow_bounds\n'
                '};\n')

    print(f"[OK] preset {args.preset}: 32x{tile_h} floors, {look.OBJ_CANVAS}x{look.OBJ_CANVAS} objects, "
          f"{cell}x{cell} characters (hero + charger).")


if __name__ == "__main__":
    main()
