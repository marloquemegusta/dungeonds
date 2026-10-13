import os
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ART = os.environ.get("WH40K_ART", r"C:\Users\malfonso\.gemini\antigravity\brain\295f906d-3c8b-4b9a-8a57-3b3f945e38a6")
WT = str(Path(__file__).resolve().parents[1])
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
COLLISION_TEST = os.environ.get("WH40K_COLLISION_TEST") == "1"
OUTPUT_ROOT = Path(os.environ.get("WH40K_OUTPUT_ROOT", WT))
MAP_SEGMENTS = 4
WORLD_W = 3200
WORLD_H = 1920
ORTHO_SCALE = 187.5  # Four connected 50 m sectors; preserve the original pixel density.
COLLISION_SCALE = 4
if COLLISION_TEST:
    MAP_SEGMENTS = 1
    WORLD_W = 1280
    WORLD_H = 768
    ORTHO_SCALE = 75.0  # Preserve the same 17 px/m scale as the full world.

blender_script = r'''
import os, math, bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree
import bmesh

ART = os.environ.get("WH40K_ART", r"C:\Users\malfonso\.gemini\antigravity\brain\295f906d-3c8b-4b9a-8a57-3b3f945e38a6")
MAP_SEGMENTS = int(os.environ["WH40K_MAP_SEGMENTS"])
WORLD_W = int(os.environ["WH40K_WORLD_W"])
WORLD_H = int(os.environ["WH40K_WORLD_H"])
ORTHO_SCALE = float(os.environ["WH40K_ORTHO_SCALE"])
COLLISION_SCALE = int(os.environ["WH40K_COLLISION_SCALE"])
TEST_ARENA = os.environ.get("WH40K_COLLISION_TEST") == "1"
OUT_3D = os.path.join(ART, "models_3d")
REC = os.path.join(ART, "received_fbx")

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Load 3D Floor Tiles
protos = {}
for kind, fname in [
    ("sidewalk", "wh40k_floor_sidewalk.glb"),
    ("straight", "wh40k_floor_road_straight.glb"),
    ("crossroad", "wh40k_floor_road_crossroad.glb"),
]:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.import_scene.gltf(filepath=os.path.join(OUT_3D, fname))
    obj = [o for o in bpy.context.selected_objects if o.type == "MESH"][0]
    obj.name = f"proto_{kind}"
    obj.hide_render = True
    protos[kind] = obj

TILE_SZ = 10.0
floor_objs = []
for gy in (range(5, 10) if TEST_ARENA else range(-2, -2 + MAP_SEGMENTS * 5)):
    for gx in range(-2, 3):
        local_gy = (gy + 2) % 5 - 2
        if gx == 0 and local_gy == 0:
            kind, rot = "crossroad", 0
        elif gx == 0:
            kind, rot = "straight", 0
        elif local_gy == 0:
            kind, rot = "straight", 90
        else:
            kind, rot = "sidewalk", 0
        proto = protos[kind]
        inst = proto.copy()
        inst.data = proto.data.copy()
        inst.hide_render = False
        inst.rotation_mode = "XYZ"
        inst.location = (gx * TILE_SZ, -gy * TILE_SZ + 75.0, 0.0)
        inst.rotation_euler = (0.0, 0.0, math.radians(rot))
        bpy.context.collection.objects.link(inst)
        floor_objs.append(inst)

# 2. Helper to import & place a Tripo3D FBX on the urban grid
def place_fbx(rel_folder, target_xy, target_z, scale_xy, rot_z_deg, tag):
    folder_matches = [
        os.path.join(REC, d) for d in os.listdir(REC)
        if rel_folder.lower() in d.lower() and os.path.isdir(os.path.join(REC, d))
    ]
    folder_path = folder_matches[0]
    fbx_file = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".fbx")][0]

    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx_file)
    new_objs = [o for o in (set(bpy.data.objects) - before) if o.type == "MESH"]
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    for o in new_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = new_objs[0]
    if len(new_objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    for mat in obj.data.materials:
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    if "Metallic" in node.inputs and not node.inputs["Metallic"].is_linked:
                        node.inputs["Metallic"].default_value = 0.1
                    for link in list(mat.node_tree.links):
                        if link.to_socket.name in ("Metallic", "Normal"):
                            mat.node_tree.links.remove(link)
                    node.inputs["Roughness"].default_value = 0.85

    verts = [v.co for v in obj.data.vertices]
    min_x = min(v.x for v in verts); max_x = max(v.x for v in verts)
    min_y = min(v.y for v in verts); max_y = max(v.y for v in verts)
    min_z = min(v.z for v in verts); max_z = max(v.z for v in verts)
    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    span = max(max_x - min_x, max_y - min_y)
    s = scale_xy / span

    for v in obj.data.vertices:
        v.co.x = (v.co.x - cx) * s
        v.co.y = (v.co.y - cy) * s
        v.co.z = (v.co.z - min_z) * s

    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0.0, 0.0, math.radians(rot_z_deg))
    obj.location = (target_xy[0], target_xy[1], target_z)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj["wh40k_tag"] = tag
    return obj

SIDEWALK_Z = 0.35
props = []
if TEST_ARENA:
    camera_rotation = Euler((math.radians(60.0), 0.0, math.radians(45.0)), "XYZ").to_matrix()
    basis_right = camera_rotation @ Vector((1.0, 0.0, 0.0))
    basis_up = camera_rotation @ Vector((0.0, 1.0, 0.0))
    determinant = basis_right.x * basis_up.y - basis_right.y * basis_up.x

    def screen_to_world(screen_x, screen_y):
        view_up = -screen_y
        return Vector(((screen_x * basis_up.y - basis_right.y * view_up) / determinant,
                       (basis_right.x * view_up - screen_x * basis_up.x) / determinant,
                       0.0))

    def make_wall(name, screen_center, length, height, angle, color, depth=0.35):
        center = screen_to_world(*screen_center)
        screen_dx = length * math.cos(math.radians(angle))
        screen_dy = length * math.sin(math.radians(angle))
        world_delta = screen_to_world(screen_dx, screen_dy)
        wall_length = math.hypot(world_delta.x, world_delta.y)
        world_angle = math.atan2(world_delta.y, world_delta.x)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center.x, center.y, SIDEWALK_Z + height / 2.0))
        wall = bpy.context.object
        wall.name = name
        wall.dimensions = (wall_length, depth, height)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        wall.rotation_euler[2] = world_angle
        mat = bpy.data.materials.new(name + "_material")
        mat.diffuse_color = (*color, 1.0)
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*color, 1.0)
        mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.82
        wall.data.materials.append(mat)
        wall["wh40k_tag"] = "test_wall"
        return wall

    # One clear approach from the spawn point to each wall; angle and height vary.
    props.extend([
        make_wall("test_north_0deg_h12", (0.0, -3.0), 4.5, 1.2, 0.0, (0.55, 0.16, 0.10)),
        make_wall("test_east_90deg_h24", (4.0, 0.0), 4.5, 2.4, 90.0, (0.14, 0.30, 0.58)),
        make_wall("test_north_45deg_h36", (0.0, 4.0), 4.5, 3.6, 45.0, (0.48, 0.38, 0.12)),
        make_wall("test_west_135deg_h18", (-4.0, 0.0), 4.5, 1.8, 135.0, (0.22, 0.46, 0.28)),
        make_wall("test_short_30deg_h12", (-4.3, -4.3), 2.4, 1.2, 30.0, (0.42, 0.25, 0.48)),
        make_wall("test_corner_60deg_h30_a", (4.3, 4.2), 2.8, 3.0, 60.0, (0.68, 0.30, 0.12)),
        make_wall("test_corner_150deg_h30_b", (5.3, 3.0), 2.8, 3.0, 150.0, (0.68, 0.30, 0.12)),
        make_wall("test_pillar_h30", (-4.5, 4.1), 0.9, 3.0, 0.0, (0.42, 0.42, 0.40), depth=0.9),
    ])
else:
    # North-West Lot (-8.5, +8.5): Large Ruined Cathedral Bastion
    props.append(place_fbx("fortaleza", (-8.8, 8.8), SIDEWALK_Z, 9.0, 0.0, "building"))
    # North-East Lot (+8.5, +8.5): Steampunk Manufactorum Wall
    props.append(place_fbx("steampunk", (7.8, 7.8), SIDEWALK_Z, 9.5, 0.0, "building"))
    # South-West Lot (-8.5, -7.8): Gothic Corner with Sandbag Barricade
    props.append(place_fbx("gothic+ruin", (-8.2, -7.8), SIDEWALK_Z, 8.6, 0.0, "building_with_cover"))
    # South-East Lot (+8.5, -8.5): Ruined L-Shaped Sanctum with Window Arch
    props.append(place_fbx("edificio", (8.2, -8.2), SIDEWALK_Z, 8.4, 0.0, "building"))
    # Street Sidewalk Curb Shelters
    props.append(place_fbx("oxidadas", (-4.2, 4.4), SIDEWALK_Z, 5.2, 0.0, "shelter"))
    props.append(place_fbx("oxidadas", (4.4, 4.2), SIDEWALK_Z, 5.2, -90.0, "shelter"))

# Repeat the complete sector along its north-south axis, then center the 200 m run.
sector_props = list(props)
bm_sector = bmesh.new()
for p in sector_props:
    before = len(bm_sector.verts)
    bm_sector.from_mesh(p.data)
    bm_sector.verts.ensure_lookup_table()
    new_verts = list(bm_sector.verts)[before:]
    bmesh.ops.transform(bm_sector, matrix=p.matrix_world, verts=new_verts)
sector_bvh = BVHTree.FromBMesh(bm_sector)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = WORLD_W
scene.render.resolution_y = WORLD_H
scene.world = bpy.data.worlds.new("World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.36, 0.33, 0.30, 1.0)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1.15

sun_data = bpy.data.lights.new("Sun", type="SUN")
sun_data.energy = 2.8
sun_data.color = (1.0, 0.96, 0.90)
sun_obj = bpy.data.objects.new("Sun", sun_data)
sun_obj.rotation_euler = (math.radians(48), math.radians(-22), math.radians(35))
bpy.context.collection.objects.link(sun_obj)

fill_data = bpy.data.lights.new("Fill", type="SUN")
fill_data.energy = 1.85
fill_data.color = (0.95, 0.93, 0.90)
fill_obj = bpy.data.objects.new("Fill", fill_data)
fill_obj.rotation_euler = (math.radians(-35), math.radians(40), math.radians(-120))
bpy.context.collection.objects.link(fill_obj)

# Keep the original world scale while extending the bake canvas.
cam_data = bpy.data.cameras.new("DSCam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = ORTHO_SCALE
cam_obj = bpy.data.objects.new("DSCam", cam_data)
el = math.radians(30.0)
az = math.radians(45.0)
dist = 60.0
cam_obj.location = (dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el))
cam_obj.rotation_euler = (math.radians(60.0), 0.0, math.radians(45.0))
bpy.context.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Render 0: Canonical sector props-only RGBA at world resolution for occlusion mask.
scene.render.film_transparent = True
for fo in floor_objs:
    fo.hide_render = True
sector_rgba = os.path.join(ART, "wh40k_sector_props_only.png")
scene.render.filepath = sector_rgba
bpy.ops.render.render(write_still=True)
for fo in floor_objs:
    fo.hide_render = False
scene.render.film_transparent = False

props = []
for segment in range(MAP_SEGMENTS):
    for source in sector_props:
        inst = source.copy()
        inst.data = source.data.copy()
        inst.location.y += (segment * 50.0 - (MAP_SEGMENTS - 1) * 25.0) if TEST_ARENA else segment * 50.0 - 75.0
        bpy.context.collection.objects.link(inst)
        props.append(inst)
for source in sector_props:
    bpy.data.objects.remove(source, do_unlink=True)

# Render 1: Full scene at original pixel scale on an expanded canvas.
full_world = os.path.join(ART, "wh40k_full_ds_world.png")
scene.render.filepath = full_world
bpy.ops.render.render(write_still=True)

# Render 2: Props-only RGBA at world resolution for exact pixel mask.
scene.render.film_transparent = True
for fo in floor_objs:
    fo.hide_render = True
props_rgba = os.path.join(ART, "wh40k_props_only_world.png")
scene.render.filepath = props_rgba
bpy.ops.render.render(write_still=True)

# 4. Compute the collision grid and occlusion depth map at world pixel scale.
bpy.context.view_layer.update()
cam_mat = cam_obj.matrix_world
cam_origin = cam_mat.translation
cam_right = cam_mat.to_3x3() @ Vector((1.0, 0.0, 0.0))
cam_up = cam_mat.to_3x3() @ Vector((0.0, 1.0, 0.0))
cam_forward = (cam_mat.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()

bm_collision = bmesh.new()
for p in props:
    verts_before = len(bm_collision.verts)
    bm_collision.from_mesh(p.data)
    bm_collision.verts.ensure_lookup_table()
    new_verts = list(bm_collision.verts)[verts_before:]
    bmesh.ops.transform(bm_collision, matrix=p.matrix_world, verts=new_verts)
collision_bvh = BVHTree.FromBMesh(bm_collision)

coll_w = WORLD_W // COLLISION_SCALE
coll_h = WORLD_H // COLLISION_SCALE
view_h = ORTHO_SCALE * WORLD_H / WORLD_W
coll_grid = np.zeros((coll_h, coll_w), dtype=np.uint8)
walk_samples = tuple((dx, dy) for dy in range(-2, 2) for dx in range(-2, 2))
for cy in range(coll_h):
    py = cy * COLLISION_SCALE + COLLISION_SCALE // 2
    v = (0.5 - (py + 0.5) / WORLD_H) * view_h
    for cx in range(coll_w):
        if cx < 4 or cx >= coll_w - 4 or cy < 4 or cy >= coll_h - 4:
            coll_grid[cy, cx] = 0x03  # outer world boundary blocks walk & bullet
            continue
        px = cx * COLLISION_SCALE + COLLISION_SCALE // 2
        u = ((px + 0.5) / WORLD_W - 0.5) * ORTHO_SCALE
        ray_start = cam_origin + cam_right * u + cam_up * v
        t_ground = (SIDEWALK_Z - ray_start.z) / cam_forward.z
        g_pt = ray_start + cam_forward * t_ground

        # Test every pixel in the 4x4 cell to avoid gaps around thin building geometry.
        hit_low = False
        for sample_dx, sample_dy in walk_samples:
            sample_px = px + sample_dx
            sample_py = py + sample_dy
            sample_v = (0.5 - (sample_py + 0.5) / WORLD_H) * view_h
            sample_u = ((sample_px + 0.5) / WORLD_W - 0.5) * ORTHO_SCALE
            sample_ray = cam_origin + cam_right * sample_u + cam_up * sample_v
            sample_t = (SIDEWALK_Z - sample_ray.z) / cam_forward.z
            sample_ground = sample_ray + cam_forward * sample_t
            hit_co, _, _, _ = collision_bvh.ray_cast(
                Vector((sample_ground.x, sample_ground.y, SIDEWALK_Z + 25.0)),
                Vector((0.0, 0.0, -1.0)), 24.95)
            if hit_co is not None and hit_co.z > SIDEWALK_Z + 0.05:
                hit_low = True
                break

        # Keep projectile height independent from the player's walkable body column.
        # Projectiles are blocked if geometry extends above cover height (SIDEWALK_Z + 1.25m).
        hit_hi_co, _, _, _ = collision_bvh.ray_cast(
            Vector((g_pt.x, g_pt.y, SIDEWALK_Z + 25.0)),
            Vector((0.0, 0.0, -1.0)), 24.95)
        hit_high = (hit_hi_co is not None and hit_hi_co.z > SIDEWALK_Z + 1.25)

        flags = 0
        if hit_low:
            flags |= 0x01  # COLL_WALK (blocks player/enemy movement)
        if hit_high:
            flags |= 0x02  # COLL_BULLET (blocks projectiles)
        coll_grid[cy, cx] = flags

bimg = bpy.data.images.load(sector_rgba)
pix = np.array(bimg.pixels[:], dtype=np.float32).reshape((WORLD_H, WORLD_W, 4))[::-1, :, :]
occ_depth = np.full((WORLD_H, WORLD_W), -1, dtype=np.int16)

for py in range(WORLD_H):
    v = (0.5 - (py + 0.5) / WORLD_H) * view_h
    for px in range(WORLD_W):
        if pix[py, px, 3] < 0.5:
            continue
        u = ((px + 0.5) / WORLD_W - 0.5) * ORTHO_SCALE
        ray_start = cam_origin + cam_right * u + cam_up * v
        hit_co, _, _, _ = sector_bvh.ray_cast(ray_start, cam_forward, 200.0)
        if hit_co is not None and hit_co.z > SIDEWALK_Z + 0.01:
            gp = Vector((hit_co.x, hit_co.y, SIDEWALK_Z)) - cam_origin
            v_ground = gp.dot(cam_up)
            py_ground = int(round((0.5 - v_ground / view_h) * WORLD_H - 0.5))
            occ_depth[py, px] = max(py, min(WORLD_H - 1, py_ground))

bm_collision.free()
bm_sector.free()
np.save(os.path.join(ART, "scratch", "wh40k_coll.npy"), coll_grid)
np.save(os.path.join(ART, "scratch", "wh40k_occ.npy"), occ_depth)
occ_offsets = []
for segment in range(MAP_SEGMENTS):
    delta = Vector((0.0, segment * 50.0 - (MAP_SEGMENTS - 1) * 25.0, 0.0))
    dx = int(round(delta.dot(cam_right) * WORLD_W / ORTHO_SCALE))
    dy = int(round(-delta.dot(cam_up) * WORLD_H / view_h))
    occ_offsets.append((dx, dy))
np.save(os.path.join(ART, "scratch", "wh40k_occ_offsets.npy"), np.array(occ_offsets, dtype=np.int16))
print("WALK_ONLY cells (cover):", int(np.sum(coll_grid == 1)), "SOLID_WALL cells:", int(np.sum(coll_grid == 3)))
'''

bpath = os.path.join(ART, "scratch", "_blender_assemble_wh40k.py")
with open(bpath, "w", encoding="utf-8") as f:
    f.write(blender_script)

blender_env = os.environ.copy()
blender_env.update({
    "WH40K_MAP_SEGMENTS": str(MAP_SEGMENTS),
    "WH40K_WORLD_W": str(WORLD_W),
    "WH40K_WORLD_H": str(WORLD_H),
    "WH40K_ORTHO_SCALE": str(ORTHO_SCALE),
    "WH40K_COLLISION_SCALE": str(COLLISION_SCALE),
    "WH40K_COLLISION_TEST": "1" if COLLISION_TEST else "0",
})
subprocess.run([BLENDER, "-b", "-P", bpath], check=True, env=blender_env)

# 5. Generate C sources for the DS engine & visual collision overlay
img = Image.open(os.path.join(ART, "wh40k_full_ds_world.png")).convert("RGB")
if img.size != (WORLD_W, WORLD_H):
    raise SystemExit(f"expected Blender bake {(WORLD_W, WORLD_H)}, found {img.size}")
rgb = np.asarray(img, dtype=np.uint16)
r5 = (rgb[:, :, 0] >> 3) & 31
g5 = (rgb[:, :, 1] >> 3) & 31
b5 = (rgb[:, :, 2] >> 3) & 31
bgr555 = (0x8000 | r5 | (g5 << 5) | (b5 << 10)).flatten()
raw_world = os.path.join(ART, "scratch", "wh40k_world_bgr555.raw")
bgr555.astype("<u2", copy=False).tofile(raw_world)

coll = np.load(os.path.join(ART, "scratch", "wh40k_coll.npy"))
occ = np.load(os.path.join(ART, "scratch", "wh40k_occ.npy"))
occ_offsets = np.load(os.path.join(ART, "scratch", "wh40k_occ_offsets.npy"))

# Create visual overlay of Walkable vs Low Cover (Bullets Pass) vs Solid Wall
overlay = img.copy().convert("RGBA")
ov_layer = Image.new("RGBA", (WORLD_W, WORLD_H), (0, 0, 0, 0))
ov_draw = ImageDraw.Draw(ov_layer)
for cy in range(4, coll.shape[0] - 4):
    for cx in range(4, coll.shape[1] - 4):
        val = int(coll[cy, cx])
        x0, y0 = cx * COLLISION_SCALE, cy * COLLISION_SCALE
        if val == 1:
            # Low cover / barricade: blocks walk, bullets pass (Yellow-Amber)
            ov_draw.rectangle([x0, y0, x0 + COLLISION_SCALE - 1, y0 + COLLISION_SCALE - 1], fill=(255, 210, 0, 150))
        elif val & 2:
            # Solid wall / pillar: blocks walk and bullets (Red)
            ov_draw.rectangle([x0, y0, x0 + COLLISION_SCALE - 1, y0 + COLLISION_SCALE - 1], fill=(235, 45, 45, 145))

overlay_comp = Image.alpha_composite(overlay, ov_layer).convert("RGB")
overlay_comp.save(os.path.join(ART, "wh40k_collision_overlay.png"))

# Write world dimensions before the generated C arrays.
(OUTPUT_ROOT / "include" / "diablo_dungeon.h").write_text(
    "#ifndef DIABLO_DUNGEON_H\n#define DIABLO_DUNGEON_H\n\n"
    "#include <nds.h>\n\n"
    f"#define WORLD_W {WORLD_W}\n#define WORLD_H {WORLD_H}\n"
    f"#define COLLISION_W {coll.shape[1]}\n#define COLLISION_H {coll.shape[0]}\n"
    f"#define COLLISION_SCALE {COLLISION_SCALE}\n"
    f"#define DUNGEON_OCCLUSION_SEGMENTS {MAP_SEGMENTS}\n"
    f"#define COLLISION_BYTES ((COLLISION_W * COLLISION_H + 3) / 4)\n\n"
    f"#define SPAWN_PIXEL_X {WORLD_W // 2}\n#define SPAWN_PIXEL_Y {WORLD_H // 2}\n\n"
    "extern const uint8_t g_dungeon_collision[COLLISION_BYTES];\n\n"
    "#endif // DIABLO_DUNGEON_H\n",
    encoding="utf-8",
)

# Write source/diablo_dungeon.c
coll_flat = coll.flatten().astype(np.uint8)
if coll_flat.size % 4:
    coll_flat = np.pad(coll_flat, (0, 4 - coll_flat.size % 4))
coll_packed = (coll_flat[0::4] | (coll_flat[1::4] << 2) |
               (coll_flat[2::4] << 4) | (coll_flat[3::4] << 6))
lines = [
    '#include "diablo_dungeon.h"\n\n',
]
lines.append("const uint8_t g_dungeon_collision[COLLISION_BYTES] = {\n")
for i in range(0, len(coll_packed), 32):
    chunk = ", ".join(f"0x{int(v):02X}" for v in coll_packed[i : i + 32])
    lines.append(f"    {chunk},\n")
lines.append("};\n")

with open(OUTPUT_ROOT / "source" / "diablo_dungeon.c", "w", encoding="utf-8") as f:
    f.writelines(lines)

# Encode RLE runs for source/dungeon_occlusion.c
runs = []
for y in range(WORLD_H):
    x = 0
    while x < WORLD_W:
        if occ[y, x] < 0:
            x += 1
            continue
        x0 = x
        min_d = occ[y, x]
        max_d = occ[y, x]
        while x < WORLD_W and occ[y, x] >= 0:
            d = occ[y, x]
            if max(max_d, d) - min(min_d, d) > 8:
                break
            min_d = min(min_d, d)
            max_d = max(max_d, d)
            x += 1
        runs.append((x0, y, x - x0, int(max_d)))

occ_lines = [
    '#include "dungeon_occlusion.h"\n\n',
    'const DungeonOcclusionRun g_dungeon_occlusion_runs[] __attribute__((aligned(4))) = {\n',
]
for x0, y, length, d in runs:
    occ_lines.append(f"    {{{x0}, {y}, {length}, {d}}},\n")
if not runs:
    occ_lines.append("    {0, 0, 0, -1},\n")
occ_lines.append("};\n\n")
occ_lines.append(f"const uint32_t g_dungeon_occlusion_run_count = {len(runs)}u;\n")
occ_lines.append("\nconst DungeonOcclusionSegmentOffset g_dungeon_occlusion_segments[DUNGEON_OCCLUSION_SEGMENTS] = {\n")
for dx, dy in occ_offsets:
    occ_lines.append(f"    {{{int(dx)}, {int(dy)}}},\n")
occ_lines.append("};\n")

with open(OUTPUT_ROOT / "source" / "dungeon_occlusion.c", "w", encoding="utf-8") as f:
    f.writelines(occ_lines)

subprocess.run([sys.executable, str(OUTPUT_ROOT / "tools" / "generate_fbx_bg_tiles.py"), raw_world], check=True)
print(f"Generated {len(runs)} occlusion runs and hardware BG tiles!")
