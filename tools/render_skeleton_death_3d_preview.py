#!/usr/bin/env python3
"""Render the death FBX directly in Blender, before sprite baking."""

import bpy
import math
import os
import sys
from mathutils import Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FBX = os.path.join(ROOT, "assets", "characters", "skeleton", "skeleton_death.fbx")
OUT = os.path.join(ROOT, "walkthroughs", "skeleton-death-fbx", "assets")
BLEND = os.path.join(OUT, "skeleton-death-3d-preview.blend")
FRAME_DIR = os.path.join(OUT, "_skeleton_death_3d_frames")
RESOLUTION = 640


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX)
    scene = bpy.context.scene
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("FBX import did not produce mesh chunks")

    actions = list(bpy.data.actions)
    if not actions:
        raise RuntimeError("FBX import did not produce animation actions")
    print("IMPORTED_ACTIONS=" + ",".join(f"{a.name}:{int(a.frame_range[0])}-{int(a.frame_range[1])}" for a in actions))
    for arm in arms:
        arm.animation_data_create()
        arm.animation_data.action = actions[0]
    start = min(int(a.frame_range[0]) for a in actions)
    end = max(int(a.frame_range[1]) for a in actions)
    scene.frame_start, scene.frame_end = start, end

    # A single bone material makes the physical pieces readable in a normal 3D render.
    bone = bpy.data.materials.new("PreviewBoneIvory")
    bone.diffuse_color = (0.58, 0.43, 0.27, 1.0)
    bone.use_nodes = True
    shader = bone.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.58, 0.43, 0.27, 1.0)
    shader.inputs["Roughness"].default_value = 0.8
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(bone)

    # Bound the camera against the animated mesh at representative times.
    bbox_points = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for frame in sorted({start, start + (end-start)//2, end}):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in meshes:
            evaluated = obj.evaluated_get(depsgraph)
            bbox_points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not bbox_points:
        raise RuntimeError("Could not determine animated mesh bounds")
    minimum = Vector(tuple(min(p[i] for p in bbox_points) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in bbox_points) for i in range(3)))
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    span = max(extent.x, extent.y, extent.z, 0.5)
    print("ANIMATED_BOUNDS", tuple(round(v, 3) for v in minimum), tuple(round(v, 3) for v in maximum))

    floor_mat = bpy.data.materials.new("PreviewFloor")
    floor_mat.diffuse_color = (0.08, 0.09, 0.11, 1.0)
    floor_mat.use_nodes = True
    floor_mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.08, 0.09, 0.11, 1.0)
    bpy.ops.mesh.primitive_plane_add(size=span * 8.0, location=(center.x, center.y, minimum.z - 0.015))
    floor = bpy.context.object
    floor.name = "PreviewGround"
    floor.data.materials.append(floor_mat)

    cam_data = bpy.data.cameras.new("PreviewCamera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = span * 1.42
    camera = bpy.data.objects.new("PreviewCamera", cam_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((span * 2.2, -span * 3.0, span * 1.8))
    look_at(camera, center)
    scene.camera = camera

    def area_light(name, offset, energy, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(offset)
        look_at(obj, center)

    area_light("Key", (span * 0.25, -span * 0.25, span * 4.0), 90, span * 1.4, (1.0, 0.83, 0.62))
    area_light("Fill", (-span * 2.3, -span * 0.5, span * 1.8), 28, span * 1.8, (0.62, 0.75, 1.0))
    area_light("Rim", (0.0, span * 2.0, span * 2.6), 60, span * 1.2, (1.0, 0.93, 0.78))

    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world = bpy.data.worlds.new("PreviewWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.018, 0.021, 0.025, 1.0)
    scene.render.fps = 12
    scene.frame_set(start)
    scene.render.filepath = os.path.join(FRAME_DIR, "frame_")
    os.makedirs(FRAME_DIR, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_location = center
                area.spaces.active.region_3d.view_distance = span * 3.2
                area.spaces.active.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)

    for frame in range(start, end + 1):
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(FRAME_DIR, f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    scene.frame_set(end)
    bpy.context.view_layer.update()
    final_points = []
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        final_points.extend(evaluated.matrix_world @ Vector(c) for c in evaluated.bound_box)
    print("END_BOUNDS", tuple(round(min(p[i] for p in final_points), 3) for i in range(3)),
          "FLOOR_Z", round(minimum.z - 0.015, 3))
    print(f"PREVIEW_BLEND={BLEND}")
    print(f"PREVIEW_FRAMES={start}-{end} DIR={FRAME_DIR}")


if __name__ == "__main__":
    main()
