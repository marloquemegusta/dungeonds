import bpy
import math
import numpy as np
from mathutils import Vector
from pathlib import Path

def test_ds_3d():
    artifact_dir = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
    fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    
    obj = bpy.context.scene.objects[0]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    SCALE = 24.0
    for v in obj.data.vertices:
        v.co *= SCALE

    floor_samples = [v.co.z for p in obj.data.polygons if p.normal.z > 0.8 for v in [obj.data.vertices[i] for i in p.vertices]]
    floor_z = float(np.median(floor_samples))
    for v in obj.data.vertices:
        v.co.z -= floor_z

    bpy.context.view_layer.update()

    # Camera setup (Orthographic DS camera)
    ortho_scale = 38.0
    cam_data = bpy.data.cameras.new("DSCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_obj = bpy.data.objects.new("DSCam", cam_data)
    el = math.radians(30.0)
    az = math.radians(45.0)
    dist = 100.0
    cam_obj.location = (dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el))
    cam_obj.rotation_euler = (math.radians(60.0), 0.0, math.radians(45.0))
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    bpy.context.view_layer.update()

    world_w, world_h = 768, 512
    view_h = ortho_scale * (world_h / world_w)
    cam_rot_mat = cam_obj.matrix_world.to_3x3()
    cam_right = cam_rot_mat @ Vector((1, 0, 0))
    cam_up = cam_rot_mat @ Vector((0, 1, 0))
    cam_forward = cam_rot_mat @ Vector((0, 0, -1))
    cam_origin = cam_obj.matrix_world.translation

    # World background to pure black
    world = bpy.data.worlds.new("BlackWorld")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs["Strength"].default_value = 0.0
    bpy.context.scene.world = world

    # Position 1: Spawn (Center Room)
    px1, py1 = 361, 233
    u1 = ((px1 + 0.5) / world_w - 0.5) * ortho_scale
    v1 = (0.5 - (py1 + 0.5) / world_h) * view_h
    ray_start1 = cam_origin + cam_right * u1 + cam_up * v1
    t_g1 = -ray_start1.z / cam_forward.z
    pos1 = ray_start1 + cam_forward * t_g1

    # Position 2: Walking towards West Archway
    px2, py2 = 310, 240
    u2 = ((px2 + 0.5) / world_w - 0.5) * ortho_scale
    v2 = (0.5 - (py2 + 0.5) / world_h) * view_h
    ray_start2 = cam_origin + cam_right * u2 + cam_up * v2
    t_g2 = -ray_start2.z / cam_forward.z
    pos2 = ray_start2 + cam_forward * t_g2

    # Add Point Light
    light_data = bpy.data.lights.new(name="TorchLight", type="POINT")
    light_data.energy = 500.0 # Watts
    light_data.color = (1.0, 0.92, 0.75)
    light_data.shadow_soft_size = 0.05
    light_data.use_shadow = True
    light_obj = bpy.data.objects.new(name="TorchLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)

    scene = bpy.context.scene
    scene.render.resolution_x = world_w
    scene.render.resolution_y = world_h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    # Render Position 1 (Full 50k poly)
    light_obj.location = (pos1.x, pos1.y, 1.2)
    path_pos1 = str(artifact_dir / "ds3d_pos1_spawn_full.png")
    scene.render.filepath = path_pos1
    bpy.ops.render.render(write_still=True)

    # Render Position 2 (Moving into Archway)
    light_obj.location = (pos2.x, pos2.y, 1.2)
    path_pos2 = str(artifact_dir / "ds3d_pos2_arch_full.png")
    scene.render.filepath = path_pos2
    bpy.ops.render.render(write_still=True)

    # Now let's create the DS-hardware compliant Low-Poly mesh (Decimate to 400 polygons)
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = 0.015 # ~400 polygons!
    bpy.ops.object.modifier_apply(modifier="Decimate")
    poly_count = len(obj.data.polygons)
    print(f"Decimated mesh for DS hardware: {poly_count} polygons")

    # Render Low-Poly at Position 1 to compare
    light_obj.location = (pos1.x, pos1.y, 1.2)
    path_lowpoly1 = str(artifact_dir / "ds3d_pos1_lowpoly_ds.png")
    scene.render.filepath = path_lowpoly1
    bpy.ops.render.render(write_still=True)

    # Render Low-Poly at Position 2
    light_obj.location = (pos2.x, pos2.y, 1.2)
    path_lowpoly2 = str(artifact_dir / "ds3d_pos2_lowpoly_ds.png")
    scene.render.filepath = path_lowpoly2
    bpy.ops.render.render(write_still=True)

    print("Renderings complete!")

if __name__ == "__main__":
    test_ds_3d()
