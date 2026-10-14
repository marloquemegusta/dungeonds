import bpy
import math
import numpy as np
from mathutils import Vector
from pathlib import Path
import os

def render():
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
    cam_data = bpy.data.cameras.new("DSCam")
    cam_data.type = "ORTHO"
    ortho_scale = 38.0
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

    cam_rot_mat = cam_obj.matrix_world.to_3x3()
    cam_right = cam_rot_mat @ Vector((1, 0, 0))
    cam_up = cam_rot_mat @ Vector((0, 1, 0))
    cam_forward = cam_rot_mat @ Vector((0, 0, -1))
    cam_origin = cam_obj.matrix_world.translation

    world_w, world_h = 768, 512
    view_h = ortho_scale * (world_h / world_w)

    # Player position at spawn
    px, py = 361, 233
    u = ((px + 0.5) / world_w - 0.5) * ortho_scale
    v = (0.5 - (py + 0.5) / world_h) * view_h
    ray_start = cam_origin + cam_right * u + cam_up * v

    # Ground intersection for player position
    t_ground = -ray_start.z / cam_forward.z
    ground_pos = ray_start + cam_forward * t_ground
    print(f"Player 3D Ground Position: {ground_pos}")

    # Set World background to pure black
    world = bpy.data.worlds.new("BlackWorld")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs["Strength"].default_value = 0.0
    bpy.context.scene.world = world

    # Add Point Light (Torch) at player position
    light_data = bpy.data.lights.new(name="TorchLight", type="POINT")
    light_data.energy = 500.0 # Watts
    light_data.color = (1.0, 0.92, 0.75) # Warm torch light
    light_data.shadow_soft_size = 0.1 # Crisp shadow
    light_data.use_shadow = True
    
    # Place torch at chest height (Z = 1.2m above floor)
    light_obj = bpy.data.objects.new(name="TorchLight", object_data=light_data)
    light_obj.location = (ground_pos.x, ground_pos.y, 1.2)
    bpy.context.collection.objects.link(light_obj)

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = world_w
    scene.render.resolution_y = world_h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    full_render_path = str(artifact_dir / "blender_real_lighting_full.png")
    scene.render.filepath = full_render_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered full view to {full_render_path}")

    # Also crop/render the DS bottom screen viewport (cam_x=233, cam_y=137, 256x192)
    from PIL import Image
    im = Image.open(full_render_path)
    ds_crop = im.crop((233, 137, 233 + 256, 137 + 192))
    ds_crop_2x = ds_crop.resize((512, 384), Image.Resampling.NEAREST)
    crop_path = str(artifact_dir / "blender_real_lighting_ds_view.png")
    ds_crop_2x.save(crop_path)
    print(f"Saved DS view to {crop_path}")

if __name__ == "__main__":
    render()
