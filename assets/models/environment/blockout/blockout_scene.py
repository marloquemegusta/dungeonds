import bpy
import math
import os
from mathutils import Vector


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = ROOT_DIR


def mat(name, color, roughness=0.9, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    return m


def box(name, loc, size, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new("soft blockout edges", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        obj.modifiers.new("weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def text_obj(body, loc, size, material, rotation=(0, 0, 0), align="CENTER"):
    curve = bpy.data.curves.new(body, "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.extrude = 0
    obj = bpy.data.objects.new(body, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    return obj


def wall(name, x1, y1, x2, y2, height, material, thickness=0.55):
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    obj = box(name, ((x1+x2)/2, (y1+y2)/2, height/2),
              (length if abs(dx) >= abs(dy) else thickness,
               thickness if abs(dx) >= abs(dy) else length, height), material, 0.06)
    return obj


def cylinder(name, loc, radius, depth, material, vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def cone(name, loc, radius1, radius2, depth, material, vertices=8, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2,
                                    depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def ring(name, x, y, radius, material, z=0.10, thickness=0.045):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thickness,
                                    major_segments=64, minor_segments=6, location=(x,y,z))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def aim_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Clear, functional blockout palette.
floor_mat = mat("01 | concrete floor", (0.30, 0.34, 0.39))
grid_mat = mat("02 | floor grid", (0.38, 0.43, 0.48))
wall_mat = mat("03 | perimeter walls", (0.18, 0.22, 0.28))
cover_mat = mat("04 | waist-high cover", (0.38, 0.43, 0.49))
player_mat = mat("05 | player blue", (0.12, 0.55, 0.95), emission=0.12)
enemy_mat = mat("06 | enemy red", (0.90, 0.14, 0.12), emission=0.08)
shot_mat = mat("07 | shotgun amber", (1.0, 0.55, 0.08), emission=0.25)
rifle_mat = mat("08 | long-range cyan", (0.10, 0.85, 0.92), emission=0.22)
gatling_mat = mat("09 | gatling magenta", (0.92, 0.22, 0.62), emission=0.18)
label_mat = mat("10 | white labels", (0.94, 0.97, 1.0), emission=0.6)
dark_mat = mat("11 | label backing", (0.06, 0.08, 0.11))

# Main combat room: 24 x 18 m, connected to a short entry and exit run.
box("main combat room floor (24 x 18 m)", (0, 0, -0.28), (24, 18, 0.56), floor_mat)
box("entry corridor floor", (-4, -12, -0.28), (5, 6, 0.56), floor_mat)
box("exit corridor floor", (5, 12, -0.28), (5, 6, 0.56), floor_mat)

# Two openings align diagonally so moving through the room keeps crossing the firing lanes.
wall("south-west wall", -12, -9, -6.5, -9, 2.2, wall_mat)
wall("south-east wall", -1.5, -9, 12, -9, 2.2, wall_mat)
wall("north-west wall", -12, 9, 2.5, 9, 2.2, wall_mat)
wall("north-east wall", 7.5, 9, 12, 9, 2.2, wall_mat)
wall("west wall", -12, -9, -12, 9, 2.2, wall_mat)
wall("east wall", 12, -9, 12, 9, 2.2, wall_mat)

# Corridor edges and short door cheeks; low cutaway walls keep the whole layout readable.
wall("entry left cheek", -6.5, -15, -6.5, -9, 1.5, wall_mat)
wall("entry right cheek", -1.5, -15, -1.5, -9, 1.5, wall_mat)
wall("exit left cheek", 2.5, 9, 2.5, 15, 1.5, wall_mat)
wall("exit right cheek", 7.5, 9, 7.5, 15, 1.5, wall_mat)

# Sparse floor grid provides scale without turning the render into a diagram.
for x in range(-10, 11, 2):
    box(f"grid x={x}", (x, 0, 0.012), (0.025, 17.6, 0.024), grid_mat)
for y in range(-8, 9, 2):
    box(f"grid y={y}", (0, y, 0.014), (23.6, 0.025, 0.024), grid_mat)

# Cover is offset: every obstruction protects one angle while leaving another exposed.
box("central long cover", (-0.6, 0.2, 0.68), (2.4, 6.4, 1.3), cover_mat, 0.12)
box("west low cover", (-7.7, 2.2, 0.55), (3.2, 1.4, 1.0), cover_mat, 0.10)
box("east low cover", (7.0, -3.8, 0.55), (3.0, 1.5, 1.0), cover_mat, 0.10)
box("north offset cover", (-8.6, 5.6, 0.62), (2.1, 2.0, 1.15), cover_mat, 0.10)
box("south offset cover", (-4.0, -4.8, 0.62), (2.0, 2.3, 1.15), cover_mat, 0.10)

# Player marker and a small arrow showing stylus aim direction.
cylinder("player base", (-4, -7.2, 0.25), 0.62, 0.26, player_mat)
cone("player marker", (-4, -7.2, 0.92), 0.48, 0.0, 1.05, player_mat, vertices=4,
     rotation=(0, 0, math.radians(40)))
text_obj("START", (-4, -8.25, 0.06), 0.58, label_mat)

# Three simple enemy markers illustrate sightline and pressure positions, not final enemy designs.
enemies = [
    ("GUNNER / lane pressure", 9.0, 6.4),
    ("CHARGER / close pressure", 8.6, -6.0),
    ("GROUP / sustained fire", -8.3, -2.2),
]
for label, x, y in enemies:
    cylinder(label + " base", (x, y, 0.22), 0.58, 0.20, enemy_mat)
    cone(label + " marker", (x, y, 0.83), 0.46, 0.0, 1.0, enemy_mat)
    text_obj(label, (x, y+0.9, 0.08), 0.40, label_mat)

# Weapon range cues: close shotgun radius, firing lane, and a broad sustained-fire loop.
ring("shotgun close range (3.2 m)", 8.0, -5.3, 3.2, shot_mat, z=0.08)
text_obj("SHOTGUN / CLOSE", (5.2, -1.3, 0.08), 0.42, shot_mat)
# Long-range firing lane is a narrow floor stripe along the diagonal approach.
lane = box("long-range sightline", (5.1, 6.4, 0.055), (10.0, 0.20, 0.045), rifle_mat)
text_obj("LONG SIGHTLINE", (4.4, 7.35, 0.08), 0.42, rifle_mat)
# Dashed outer loop around the central cover gives the gatling user a moving route.
for i in range(16):
    angle = 2 * math.pi * i / 16
    x, y = 5.1 * math.cos(angle), 5.0 * math.sin(angle)
    box(f"gatling movement dash {i+1}", (x, y, 0.07), (0.62, 0.10, 0.05), gatling_mat)
    bpy.context.object.rotation_euler[2] = angle + math.pi / 2
text_obj("GATLING / KEEP MOVING", (0, -6.2, 0.08), 0.42, gatling_mat)

# Label plaque, floating just outside the room footprint.
box("title backing", (0, 17.25, 0.0), (25, 1.6, 0.18), dark_mat, 0.04)
text_obj("BLOCKOUT 01  |  STRAFE + SHOOT ARENA  |  24 x 18 m",
         (0, 17.05, 0.13), 0.68, label_mat)

# Ground, world, camera and soft studio lighting (backdrop omitted so arena is not shrunk)
# box("ground", (0, 0, -0.68), (200, 200, 0.20), mat("ground", (0.055, 0.07, 0.09)))
world = bpy.context.scene.world
world.color = (0.06, 0.07, 0.09)
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.045, 0.065, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

for name, loc, power, size in [
    ("key", (0, -5, 30), 5000, 18),
    ("fill", (-18, 3, 18), 2600, 14),
    ("rim", (14, 12, 18), 3200, 12),
]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.shape = "DISK"
    light.data.size = size
    aim_camera(light, (0, 0, 0))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1700
scene.render.resolution_y = 1350
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.render.image_settings.color_mode = "RGBA"

camera_data = bpy.data.cameras.new("isometric camera")
camera = bpy.data.objects.new("isometric camera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera.location = (27, -34, 34)
camera.data.type = "ORTHO"
camera.data.ortho_scale = 42
aim_camera(camera, (0, 0, 1.1))
scene.render.filepath = os.path.join(ASSET_DIR, "arena_isometric.png")
bpy.ops.render.render(write_still=True)

# Save a top-down companion render for checking lanes and routes.
top_data = bpy.data.cameras.new("top-down camera")
top = bpy.data.objects.new("top-down camera", top_data)
bpy.context.collection.objects.link(top)
top.location = (0, 0, 55)
top.rotation_euler = (0, 0, 0)
top.data.type = "ORTHO"
top.data.ortho_scale = 40
scene.camera = top
scene.render.resolution_x = 1700
scene.render.resolution_y = 1250
scene.render.filepath = os.path.join(ASSET_DIR, "arena_topdown.png")
bpy.ops.render.render(write_still=True)

# Leave the editable project opening on the isometric view.
scene.camera = camera
scene.render.filepath = os.path.join(ASSET_DIR, "arena_isometric.png")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSET_DIR, "isometric_shooter_blockout.blend"))

# Export clean FBX and GLB
fbx_path = os.path.join(ASSET_DIR, "isometric_shooter_blockout.fbx")
glb_path = os.path.join(ASSET_DIR, "isometric_shooter_blockout.glb")
bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=False, object_types={'MESH'}, mesh_smooth_type='FACE')
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=False)
print(f"Exported clean {fbx_path} and {glb_path}")

