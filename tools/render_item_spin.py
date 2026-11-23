"""Render 360-degree spinning 56x56 RGB15 item sprites for the ARPG inventory top screen.

Usage:
  blender --background --python tools/render_item_spin.py -- [--only SLUG] [--preview] [--icon24]

Outputs:
  nitrofiles/items/<slug>.bin  (8-byte header + 24 frames of 56x56 uint16_t RGB15)
"""

import math
import os
import struct
import sys

# Detect whether we are running inside Blender or as a standalone Python driver.
IN_BLENDER = False
try:
    import bpy
    import mathutils
    IN_BLENDER = True
except ImportError:
    pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(REPO_ROOT, "nitrofiles", "items")
TMP_DIR = os.path.join(REPO_ROOT, "build", "item_spin_tmp")

NUM_FRAMES = 24
RENDER_SZ = 112
OUT_SZ = 56
MAGIC = 0x4954  # 'IT'
# Fuente del icono de 24 px (--icon24): render grande que tools/bake_item_icon24.py reduce.
ICON_SRC_SZ = 192
ICON_ORTHO = 1.80
ICON_TILT_MUL = 2.0
ICON_YAW = -12.0

# (slug, relative_fbx_path, base_euler_deg (rx, ry, rz), tilt_deg)
ITEMS = [
    (
        "relic_lanza",
        "assets/models/items/relic_lanza/tripo_convert_0d52d8fc-15de-4d38-96f4-428d929ce548.fbx",
        (90.0, 45.0, 0.0),
        12.0,
    ),
    (
        "relic_nudillera",
        "assets/models/items/relic_nudillera/tripo_convert_bbb28601-f245-42a7-93b7-c5cc8f5208a7.fbx",
        (90.0, -90.0, 0.0),
        15.0,
    ),
    (
        "relic_calavera",
        "assets/models/items/relic_calavera/tripo_convert_c1f10f3e-f623-4806-9d9f-e33bd68769f8.fbx",
        (0.0, 0.0, 0.0),
        10.0,
    ),
    (
        "relic_corazon",
        "assets/models/hud/sacred_heart/tripo_convert_d96dac8c-dc43-495d-9495-f318e45fae13.fbx",
        (0.0, 0.0, 0.0),
        10.0,
    ),
    (
        # Hostia del Glifo: geometria generada por tools/make_relic_hostia.py (no hay FBX).
        "relic_hostia",
        "gen:make_relic_hostia",
        (90.0, 0.0, 0.0),
        15.0,
    ),
    (
        "tome_glifo",
        "assets/models/items/tome_glifo/tripo_convert_d5266d16-afb4-4b41-b70f-4489e4284835.fbx",
        (90.0, 90.0, 0.0),
        15.0,
    ),
    (
        "tome_levantar",
        "assets/models/items/tome_levantar/tripo_convert_6d103588-8b90-49d8-a6a3-c08fe9093cd3.fbx",
        (90.0, 90.0, 0.0),
        15.0,
    ),
    (
        "tome_rayo",
        "assets/models/items/tome_rayo/tripo_convert_3c8af05f-e6d7-48a1-bb2f-018926b464f0.fbx",
        (90.0, 90.0, 0.0),
        15.0,
    ),
]


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = argv[1:]
    only = None
    preview = False
    single = False
    icon = False
    i = 0
    while i < len(argv):
        if argv[i] == "--only" and i + 1 < len(argv):
            only = argv[i + 1]
            i += 2
        elif argv[i] == "--preview":
            preview = True
            i += 1
        elif argv[i] == "--single":
            single = True
            i += 1
        elif argv[i] == "--icon24":
            icon = True
            i += 1
        else:
            i += 1
    return only, preview, single, icon


def rgba_to_rgb15_bytes(img_rgba):
    """Convert a 56x56 RGBA PIL Image to packed uint16_t RGB15 bytes."""
    px = img_rgba.load()
    out = bytearray(OUT_SZ * OUT_SZ * 2)
    idx = 0
    for y in range(OUT_SZ):
        for x in range(OUT_SZ):
            r, g, b, a = px[x, y]
            if a < 96:
                val = 0
            else:
                r5 = min(31, (r + 4) >> 3)
                g5 = min(31, (g + 4) >> 3)
                b5 = min(31, (b + 4) >> 3)
                val = 0x8000 | (b5 << 10) | (g5 << 5) | r5
            struct.pack_into("<H", out, idx, val)
            idx += 2
    return bytes(out)


def pack_frames_to_bin(slug, frame_pngs):
    from PIL import Image, ImageEnhance, ImageFilter

    os.makedirs(OUT_DIR, exist_ok=True)
    bin_path = os.path.join(OUT_DIR, f"{slug}.bin")
    with open(bin_path, "wb") as f:
        f.write(struct.pack("<HHHH", MAGIC, len(frame_pngs), OUT_SZ, OUT_SZ))
        for p in frame_pngs:
            im = Image.open(p).convert("RGBA")
            # Downsample with Lanczos, then apply mild C2 legibility boost (sharpen + contrast)
            im = im.resize((OUT_SZ, OUT_SZ), Image.Resampling.LANCZOS)
            r, g, b, a = im.split()
            rgb = Image.merge("RGB", (r, g, b))
            rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.8, percent=90, threshold=3))
            rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
            rgb = ImageEnhance.Brightness(rgb).enhance(1.08)
            r2, g2, b2 = rgb.split()
            im2 = Image.merge("RGBA", (r2, g2, b2, a))
            f.write(rgba_to_rgb15_bytes(im2))
    print(f"[pack] wrote {bin_path} ({os.path.getsize(bin_path)} bytes)")


def blender_render_item(slug, fbx_rel, base_euler_deg, tilt_deg, single=False, icon=False):
    fbx_path = os.path.join(REPO_ROOT, fbx_rel)
    generated = fbx_rel.startswith("gen:")
    if not generated and not os.path.exists(fbx_path):
        print(f"[ERROR] Missing FBX: {fbx_path}")
        return []

    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Scene & render settings
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    ] else "BLENDER_EEVEE"
    # --icon24: un fotograma fuente para el icono de 24 px (mas inclinado y mas lleno).
    scene.render.resolution_x = ICON_SRC_SZ if icon else RENDER_SZ
    scene.render.resolution_y = ICON_SRC_SZ if icon else RENDER_SZ
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    # Bright, crisp exposure (Option B style)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.75

    # World ambient light
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.38, 0.35, 0.32, 1.0)
        bg.inputs["Strength"].default_value = 1.1

    # Import FBX (o genera la geometria con su script de tools/)
    if generated:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        __import__(fbx_rel[4:]).build()
    else:
        bpy.ops.import_scene.fbx(filepath=fbx_path)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        print(f"[ERROR] No meshes in {fbx_path}")
        return []

    # Parent all imported objects to a pivot empty
    pivot = bpy.data.objects.new("Pivot", None)
    scene.collection.objects.link(pivot)

    # Apply base_euler_deg to each root imported object first, or compute bounds after
    root_objs = [o for o in bpy.context.scene.objects if o != pivot and o.parent is None]
    for o in root_objs:
        o.parent = pivot

    # Apply base orientation
    pivot.rotation_euler = tuple(math.radians(a) for a in base_euler_deg)
    bpy.context.view_layer.update()

    # Compute world-space bounding box of all meshes
    min_v = mathutils.Vector((1e9, 1e9, 1e9))
    max_v = mathutils.Vector((-1e9, -1e9, -1e9))
    for m in meshes:
        for corner in m.bound_box:
            wc = m.matrix_world @ mathutils.Vector(corner)
            min_v.x = min(min_v.x, wc.x)
            min_v.y = min(min_v.y, wc.y)
            min_v.z = min(min_v.z, wc.z)
            max_v.x = max(max_v.x, wc.x)
            max_v.y = max(max_v.y, wc.y)
            max_v.z = max(max_v.z, wc.z)

    center = (min_v + max_v) * 0.5
    size = max_v - min_v
    max_dim = max(size.x, size.y, size.z, 1e-5)
    scale_f = 1.65 / max_dim

    # Create an outer spin empty so we can center+scale inside, then tilt & spin cleanly
    spin_pivot = bpy.data.objects.new("SpinPivot", None)
    scene.collection.objects.link(spin_pivot)

    # Re-parent pivot under a norm_pivot that centers and scales
    norm_pivot = bpy.data.objects.new("NormPivot", None)
    scene.collection.objects.link(norm_pivot)
    norm_pivot.parent = spin_pivot

    pivot.parent = norm_pivot
    pivot.location = -center
    norm_pivot.scale = (scale_f, scale_f, scale_f)

    # Camera looking along +Y (from -Y towards origin)
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ICON_ORTHO if icon else 2.15
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -4.0, 0.0)
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.camera = cam

    # 3-point studio lighting (Option B bright)
    def add_light(name, kind, loc, rot_deg, energy, color=(1.0, 0.97, 0.92), size=2.0):
        ldata = bpy.data.lights.new(name, type=kind)
        ldata.energy = energy
        ldata.color = color
        if kind == "AREA":
            ldata.size = size
        lobj = bpy.data.objects.new(name, ldata)
        scene.collection.objects.link(lobj)
        lobj.location = loc
        lobj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        return lobj

    add_light("Key", "AREA", (2.5, -3.5, 2.5), (55.0, 0.0, 35.0), 180.0, (1.0, 0.96, 0.88), 3.0)
    add_light("Fill", "AREA", (-3.0, -2.5, -0.5), (95.0, 0.0, -45.0), 90.0, (0.85, 0.90, 1.0), 3.5)
    add_light("Rim", "AREA", (0.0, 3.0, 2.0), (-60.0, 0.0, 0.0), 140.0, (1.0, 0.88, 0.72), 2.5)

    item_tmp = os.path.join(TMP_DIR, slug)
    os.makedirs(item_tmp, exist_ok=True)
    pngs = []
    if icon:
        spin_pivot.rotation_euler = (math.radians(tilt_deg * ICON_TILT_MUL), 0.0, math.radians(ICON_YAW))
        out_png = os.path.join(item_tmp, "icon24_src.png")
        scene.render.filepath = out_png
        bpy.ops.render.render(write_still=True)
        print(f"[icon24] {out_png}; hornear con: python tools/bake_item_icon24.py {slug}")
        return []
    n_frames = 1 if single else NUM_FRAMES
    for fidx in range(n_frames):
        yaw = (360.0 * fidx) / NUM_FRAMES
        # Slight forward tilt + Z spin so 3D depth is visible while spinning
        spin_pivot.rotation_euler = (math.radians(tilt_deg), 0.0, math.radians(yaw))
        out_png = os.path.join(item_tmp, f"f_{fidx:02d}.png")
        scene.render.filepath = out_png
        bpy.ops.render.render(write_still=True)
        pngs.append(out_png)
    return pngs


def main():
    only, preview, single, icon = parse_args()
    if not IN_BLENDER:
        # Pack already-rendered PNGs into nitrofiles/items/*.bin using system Python + PIL
        for slug, _, _, _ in ITEMS:
            if only and slug != only:
                continue
            item_tmp = os.path.join(TMP_DIR, slug)
            pngs = [os.path.join(item_tmp, f"f_{i:02d}.png") for i in range(NUM_FRAMES)]
            if all(os.path.exists(p) for p in pngs):
                pack_frames_to_bin(slug, pngs)
            else:
                print(f"[SKIP] {slug}: missing rendered frames in {item_tmp}")
        return

    for slug, fbx_rel, euler_deg, tilt_deg in ITEMS:
        if only and slug != only:
            continue
        print(f"=== Rendering {slug} ===")
        pngs = blender_render_item(slug, fbx_rel, euler_deg, tilt_deg, single=single, icon=icon)
        if pngs and not preview and not single:
            try:
                pack_frames_to_bin(slug, pngs)
            except ImportError:
                print(f"[INFO] PIL not in Blender Python; run python tools/render_item_spin.py to pack {slug}")


if __name__ == "__main__":
    main()
