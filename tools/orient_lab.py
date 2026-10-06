#!/usr/bin/env python3
"""
orient_lab.py - Orientation test bench for the DungeonDS assets.

Bakes each object at several Z rotations with the shared look, then composites
mini isometric scenes so a human can pick the rotation that reads correctly.
Nothing here touches the game; it only writes diagnostics to
artifacts/orient_lab/.

Usage:
    python tools/orient_lab.py
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_look as look

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
GLB_DIR = r"C:\codexlocal\dungeonds\assets\environment\dreadhollow\GLB"
OUT = r"C:\codexlocal\dungeonds\artifacts\orient_lab"
SPR = os.path.join(OUT, "sprites")

PRESET = "e30"
ELEV = look.elevation(PRESET)
FLOOR_W, FLOOR_H = look.FLOOR_TILE_W, look.tile_h(PRESET)
OBJ = look.OBJ_CANVAS
ROTS = [0, 45, 90, 135, 180, 225, 270, 315]

MODELS = {
    "wall": "021_crypt_wall.glb",
    "buttress": "022_buttressed_wall.glb",
    "ossuary": "023_ossuary_wall.glb",
    "arch": "078_ruined_lancet_arch.glb",
    "pillar": "068_soul_lantern_pillar.glb",
    "floor": "001_crypt_flagstone.glb",
}
ROT_MODELS = ["wall", "buttress", "ossuary", "arch"]


def blender_jobs():
    """One Blender process renders every lab sprite."""
    lines = []
    for key in ROT_MODELS:
        for rot in ROTS:
            lines.append((f"{key}_z{rot:03d}", MODELS[key], rot, "obj"))
    # floor: rotations matter for the texture, render a few
    for rot in (0, 45, 90, 135):
        lines.append((f"floor_z{rot:03d}", MODELS["floor"], rot, "floor"))
    lines.append(("pillar_z000", MODELS["pillar"], 0, "obj"))

    script = ["import bpy, math, os, mathutils"]
    script.append(f'OUT = r"{SPR}"')
    script.append("os.makedirs(OUT, exist_ok=True)")
    script.append("PX_PER_M = %r" % look.PIXELS_PER_METRE)
    script.append("ELEV = %r" % ELEV)
    script.append(
        "def build(glb, zrot, kind, rw, rh):\n"
        "    bpy.ops.wm.read_factory_settings(use_empty=True)\n"
        "    bpy.ops.import_scene.gltf(filepath=glb)\n"
        "    meshes = [o for o in bpy.data.objects if o.type == 'MESH']\n"
        "    pts = []\n"
        "    for o in meshes:\n"
        "        for c in o.bound_box:\n"
        "            pts.append(o.matrix_world @ mathutils.Vector(c))\n"
        "    zmax = max(p.z for p in pts)\n"
        "    if kind == 'floor':\n"
        "        for o in meshes:\n"
        "            o.location.z -= zmax\n"
        "    if zrot:\n"
        "        for o in meshes:\n"
        "            o.rotation_mode = 'XYZ'\n"
        "            o.rotation_euler.z += math.radians(zrot)\n"
        "    scene = bpy.context.scene\n"
        "    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'\n"
        "    scene.cycles.samples = 32; scene.cycles.use_denoising = True\n"
        "    scene.render.film_transparent = True\n"
        "    scene.render.image_settings.file_format = 'PNG'\n"
        "    scene.render.image_settings.color_mode = 'RGBA'\n"
        "    scene.render.resolution_x = rw; scene.render.resolution_y = rh\n"
        "    target = bpy.data.objects.new('T', None); target.location=(0,0,0)\n"
        "    scene.collection.objects.link(target)\n"
        + look.blender_world_snippet() + "\n"
        + look.blender_camera_snippet(0, 0, ELEV).replace("max(0, 0)", "max(rw, rh)") + "\n"
        + look.blender_lights_snippet()
    )
    script.append(
        "def render(name, glb, zrot, kind):\n"
        "    rw, rh = (%d, %d) if kind == 'floor' else (%d, %d)\n"
        "    build(glb, zrot, kind, rw, rh)\n"
        "    bpy.context.scene.render.filepath = os.path.join(OUT, name + '.png')\n"
        "    bpy.ops.render.render(write_still=True)\n"
        "    print('LAB', name)\n"
        % (FLOOR_W, FLOOR_H, OBJ, OBJ)
    )
    for name, glb, rot, kind in lines:
        script.append(f"render({name!r}, r'{os.path.join(GLB_DIR, glb)}', {rot}, {kind!r})")
    script.append("print('LAB_DONE')")

    tmp = os.path.join(OUT, "lab_bake.py")
    os.makedirs(OUT, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(script))
    return tmp, lines


def main():
    os.makedirs(SPR, exist_ok=True)
    tmp, jobs = blender_jobs()
    print(f"Rendering {len(jobs)} lab sprites with Blender...")
    p = subprocess.run([BLENDER_EXE, "-b", "-P", tmp], capture_output=True, text=True)
    if "LAB_DONE" not in p.stdout:
        print(p.stdout[-1500:])
        print(p.stderr[-1500:])
        raise RuntimeError("lab bake failed")

    from PIL import Image, ImageDraw

    FLOOR_SPR = os.path.join(SPR, "floor_z000.png")
    FLOOR = look.grade(Image.open(FLOOR_SPR).convert("RGBA"))

    def obj(name):
        return look.grade(Image.open(os.path.join(SPR, name + ".png")).convert("RGBA"))

    def scene(spr, run_axis, cells=6):
        """Floor patch plus a run of walls using `spr` along one axis."""
        pad = 90
        W = cells * 32 + 2 * pad
        H = cells * 16 + 2 * pad
        im = Image.new("RGBA", (W, H), (12, 12, 20, 255))
        ox, oy = pad + cells * 16, pad
        for r in range(cells):
            for c in range(cells):
                x = ox + (c - r) * 16 - 16
                y = oy + (c + r) * 8 - 8
                im.alpha_composite(FLOOR, (x, y))
        for k in range(1, cells - 1):
            if run_axis == "col":     # varies col -> down-right on screen
                c, r = 1 + k, 2
            else:                      # varies row -> down-left on screen
                c, r = 2, 1 + k
            x = ox + (c - r) * 16
            y = oy + (c + r) * 8
            im.alpha_composite(spr, (x - OBJ // 2, y - OBJ // 2))
        return im

    def sprite_row(name, key):
        im = Image.new("RGBA", (len(ROTS) * 72, 72), (30, 34, 44, 255))
        for i, rot in enumerate(ROTS):
            s = obj(f"{key}_z{rot:03d}")
            im.alpha_composite(s, (i * 72 + 4, 4))
        return im

    # --- sheet 1: wall rotations, raw sprites ---
    sheet = Image.new("RGB", (len(ROTS) * 72, 72 * 2 + 40), (18, 20, 28))
    d = ImageDraw.Draw(sheet)
    sheet.paste(sprite_row("wall", "wall").convert("RGB"), (0, 12))
    sheet.paste(sprite_row("buttress", "buttress").convert("RGB"), (0, 84 + 16))
    for i, rot in enumerate(ROTS):
        d.text((i * 72 + 22, 0), f"{rot}", fill=(255, 255, 0))
    sheet.save(os.path.join(OUT, "sheet_wall_sprite_rotations.png"))

    # --- sheet 2: wall used along the +col edge ---
    build_sheet("sheet_wall_run_along_col.png", "col", "wall")
    build_sheet("sheet_wall_run_along_row.png", "row", "wall")
    # --- sheet 3: arch ---
    build_sheet("sheet_arch_run_along_row.png", "row", "arch", scale_cells=6)

    # --- floor rotations tiled ---
    def floor_patch(spr, cells=5):
        pad = 20
        W = cells * 32 + 2 * pad
        H = cells * 16 + 2 * pad
        im = Image.new("RGBA", (W, H), (12, 12, 20, 255))
        ox, oy = pad + cells * 16, pad
        for r in range(cells):
            for c in range(cells):
                x = ox + (c - r) * 16 - 16
                y = oy + (c + r) * 8 - 8
                im.alpha_composite(spr, (x, y))
        return im

    fs = Image.new("RGB", (4 * 200 + 20, 140), (18, 20, 28))
    d = ImageDraw.Draw(fs)
    for i, rot in enumerate((0, 45, 90, 135)):
        s = look.grade(Image.open(os.path.join(SPR, f"floor_z{rot:03d}.png")).convert("RGBA"))
        p = floor_patch(s).convert("RGB")
        fs.paste(p, (10 + i * 200, 20))
        d.text((10 + i * 200, 6), f"floor z{rot}", fill=(255, 255, 0))
    fs.save(os.path.join(OUT, "sheet_floor_rotations.png"))

    # every floor tile tiled as used in game
    tiles = ["F0_crypt", "F1_obsidian", "F2_bone", "F3_crimson", "F4_worn"]
    ft = Image.new("RGB", (len(tiles) * 200 + 20, 140), (18, 20, 28))
    d = ImageDraw.Draw(ft)
    for i, t in enumerate(tiles):
        s = Image.open(os.path.join(r"C:\codexlocal\dungeonds\assets", f"dungeon_{PRESET}", t + ".png")).convert("RGBA")
        ft.paste(floor_patch(s).convert("RGB"), (10 + i * 200, 20))
        d.text((10 + i * 200, 6), t, fill=(255, 255, 0))
    ft.save(os.path.join(OUT, "sheet_floor_tiles.png"))

    print("Lab sheets written to", OUT)


def build_sheet(filename, axis, key, scale_cells=6):
    from PIL import Image, ImageDraw
    import os as _os
    OUT2 = OUT
    FLOOR = look.grade(Image.open(_os.path.join(SPR, "floor_z000.png")).convert("RGBA"))
    OBJ = look.OBJ_CANVAS

    def scene(spr, run_axis, cells):
        pad = 90
        W = cells * 32 + 2 * pad
        H = cells * 16 + 2 * pad
        im = Image.new("RGBA", (W, H), (12, 12, 20, 255))
        ox, oy = pad + cells * 16, pad
        for r in range(cells):
            for c in range(cells):
                im.alpha_composite(FLOOR, (ox + (c - r) * 16 - 16, oy + (c + r) * 8 - 8))
        for k in range(1, cells - 1):
            c, r = (1 + k, 2) if run_axis == "col" else (2, 1 + k)
            x = ox + (c - r) * 16
            y = oy + (c + r) * 8
            im.alpha_composite(spr, (x - OBJ // 2, y - OBJ // 2))
        return im

    cells = scale_cells
    W = cells * 32 + 180
    H = cells * 16 + 180
    sheet = Image.new("RGB", (4 * (W + 8) + 8, 2 * (H + 22) + 8), (18, 20, 28))
    d = ImageDraw.Draw(sheet)
    for i, rot in enumerate(ROTS):
        spr = look.grade(Image.open(_os.path.join(SPR, f"{key}_z{rot:03d}.png")).convert("RGBA"))
        sc = scene(spr, axis, cells).convert("RGB")
        col = i % 4
        row = i // 4
        x = 8 + col * (W + 8)
        y = 22 + row * (H + 22)
        sheet.paste(sc, (x, y))
        d.text((x, y - 12), f"{key} z{rot}  (run along {axis})", fill=(255, 255, 0))
    sheet.save(_os.path.join(OUT2, filename))
    print("wrote", filename)


if __name__ == "__main__":
    main()
