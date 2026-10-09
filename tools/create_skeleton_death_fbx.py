#!/usr/bin/env python3
"""Create a hand-choreographed bone-pile FBX from the existing skeleton.

The source mesh is divided into rigid-looking anatomical pieces. Their motion
is deliberately keyed to a composed final pile instead of relying on free
rigid-body collisions, which scattered the previous prototype.
"""

import bpy
import math
import os
from mathutils import Quaternion, Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "assets", "characters", "skeleton", "skeleton.fbx")
OUTPUT = os.path.join(ROOT, "assets", "characters", "skeleton", "skeleton_death.fbx")
START_FRAME = 1
END_FRAME = 37
PILE_FRAME = 29

GROUP_TO_BONE = {
    "mixamorig:Head": "mixamorig:Head",
    "mixamorig:Neck": "mixamorig:Neck",
    "mixamorig:Spine": "mixamorig:Spine",
    "mixamorig:Spine1": "mixamorig:Spine1",
    "mixamorig:Spine2": "mixamorig:Spine2",
    "mixamorig:Hips": "mixamorig:Hips",
    "mixamorig:LeftShoulder": "mixamorig:LeftArm",
    "mixamorig:LeftArm": "mixamorig:LeftArm",
    "mixamorig:LeftForeArm": "mixamorig:LeftForeArm",
    "mixamorig:LeftHand": "mixamorig:LeftHand",
    "mixamorig:LeftHandIndex1": "mixamorig:LeftHand",
    "mixamorig:LeftHandIndex2": "mixamorig:LeftHand",
    "mixamorig:LeftHandIndex3": "mixamorig:LeftHand",
    "mixamorig:RightShoulder": "mixamorig:RightArm",
    "mixamorig:RightArm": "mixamorig:RightArm",
    "mixamorig:RightForeArm": "mixamorig:RightForeArm",
    "mixamorig:RightHand": "mixamorig:RightHand",
    "mixamorig:RightHandIndex1": "mixamorig:RightHand",
    "mixamorig:RightHandIndex2": "mixamorig:RightHand",
    "mixamorig:RightHandIndex3": "mixamorig:RightHand",
    "mixamorig:LeftUpLeg": "mixamorig:LeftUpLeg",
    "mixamorig:LeftLeg": "mixamorig:LeftLeg",
    "mixamorig:LeftFoot": "mixamorig:LeftFoot",
    "mixamorig:LeftToeBase": "mixamorig:LeftFoot",
    "mixamorig:RightUpLeg": "mixamorig:RightUpLeg",
    "mixamorig:RightLeg": "mixamorig:RightLeg",
    "mixamorig:RightFoot": "mixamorig:RightFoot",
    "mixamorig:RightToeBase": "mixamorig:RightFoot",
}

# Hand-placed centers around the pelvis: torso and skull make the upper mound;
# long bones overlap across the base instead of shooting away from the body.
PILE_OFFSETS = {
    "mixamorig:Hips": (0.00, 0.00, 0.015),
    "mixamorig:Spine": (-0.005, 0.00, 0.035),
    "mixamorig:Spine1": (0.005, 0.01, 0.055),
    "mixamorig:Spine2": (0.00, 0.00, 0.075),
    "mixamorig:Neck": (0.025, 0.01, 0.095),
    "mixamorig:Head": (0.05, 0.005, 0.12),
    "mixamorig:LeftArm": (-0.025, 0.025, 0.015),
    "mixamorig:LeftForeArm": (-0.06, 0.015, 0.025),
    "mixamorig:LeftHand": (-0.04, 0.00, 0.02),
    "mixamorig:RightArm": (0.025, -0.025, 0.015),
    "mixamorig:RightForeArm": (0.06, -0.015, 0.025),
    "mixamorig:RightHand": (0.04, 0.00, 0.02),
    "mixamorig:LeftUpLeg": (-0.025, -0.02, 0.01),
    "mixamorig:LeftLeg": (-0.055, -0.035, 0.02),
    "mixamorig:LeftFoot": (-0.08, -0.02, 0.005),
    "mixamorig:RightUpLeg": (0.025, -0.02, 0.01),
    "mixamorig:RightLeg": (0.055, -0.035, 0.02),
    "mixamorig:RightFoot": (0.08, -0.02, 0.005),
}

PILE_ANGLES = {
    "mixamorig:LeftArm": -0.35,
    "mixamorig:LeftForeArm": 0.25,
    "mixamorig:RightArm": 0.35,
    "mixamorig:RightForeArm": -0.25,
    "mixamorig:LeftUpLeg": 0.20,
    "mixamorig:LeftLeg": -0.30,
    "mixamorig:RightUpLeg": -0.20,
    "mixamorig:RightLeg": 0.30,
    "mixamorig:LeftFoot": -0.50,
    "mixamorig:RightFoot": 0.50,
    "mixamorig:LeftHand": 0.45,
    "mixamorig:RightHand": -0.45,
}


def dominant_group(obj, vertex, group_names):
    weighted = ((g.weight, group_names.get(g.group, "")) for g in vertex.groups)
    return max(weighted, default=(0.0, ""))[1]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SOURCE)
    scene = bpy.context.scene
    scene.frame_set(START_FRAME)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    source_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]
    if not source_meshes:
        raise RuntimeError("Source FBX has no weighted skeleton meshes")

    group_names = {o.name: {g.index: g.name for g in o.vertex_groups} for o in source_meshes}
    regions = {}
    materials = []
    material_indices = {}
    floor_z = float("inf")

    for obj in source_meshes:
        for slot in obj.material_slots:
            mat = slot.material
            key = mat.name if mat else "BoneDefault"
            if key not in material_indices:
                material_indices[key] = len(materials)
                materials.append(mat)

        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        world_vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        floor_z = min(floor_z, *(v.z for v in world_vertices))
        vertex_bones = [GROUP_TO_BONE.get(dominant_group(obj, v, group_names[obj.name]), "mixamorig:Spine2")
                        for v in obj.data.vertices]
        for poly in mesh.polygons:
            counts = {}
            for index in poly.vertices:
                bone = vertex_bones[index]
                counts[bone] = counts.get(bone, 0) + 1
            bone = max(counts, key=counts.get)
            part = regions.setdefault(bone, {"verts": [], "faces": [], "material_ids": []})
            base = len(part["verts"])
            part["verts"].extend(world_vertices[i].copy() for i in poly.vertices)
            part["faces"].append(tuple(range(base, base + len(poly.vertices))))
            mat = obj.material_slots[poly.material_index].material if poly.material_index < len(obj.material_slots) else None
            part["material_ids"].append(material_indices.get(mat.name if mat else "BoneDefault", 0))
        evaluated.to_mesh_clear()

    if not math.isfinite(floor_z):
        raise RuntimeError("Could not determine the skeleton's floor height")
    center = sum(regions["mixamorig:Hips"]["verts"], Vector()) / len(regions["mixamorig:Hips"]["verts"])
    scene.frame_start, scene.frame_end = START_FRAME, END_FRAME

    # Remove the source rig after capturing its evaluated, connected pose.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)

    chunks = {}
    for bone, part in regions.items():
        if not part["faces"]:
            continue
        origin = sum(part["verts"], Vector()) / len(part["verts"])
        mesh = bpy.data.meshes.new(f"Bone_{bone}_mesh")
        mesh.from_pydata([v - origin for v in part["verts"]], [], part["faces"])
        mesh.update()
        for mat in materials:
            if mat:
                mesh.materials.append(mat)
        for poly, material_id in zip(mesh.polygons, part["material_ids"]):
            if materials:
                poly.material_index = material_id
        obj = bpy.data.objects.new(f"Bone_{bone}", mesh)
        scene.collection.objects.link(obj)
        obj.location = origin
        obj.rotation_mode = "QUATERNION"
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
        obj["bone_region"] = bone
        chunks[bone] = {"object": obj, "origin": origin, "verts": part["verts"]}

    # Align the longest pieces across the floor; keep the skull/core stacked up.
    final_transforms = {}
    for bone, chunk in chunks.items():
        obj, origin = chunk["object"], chunk["origin"]
        offset = PILE_OFFSETS.get(bone, (0.0, 0.0, 0.08))
        target = Vector((center.x + offset[0], center.y + offset[1], floor_z + offset[2]))
        local = [v - origin for v in chunk["verts"]]
        if bone in PILE_ANGLES and len(local) > 1:
            a = max(local, key=lambda v: v.length_squared)
            b = max(local, key=lambda v: (v - a).length_squared)
            axis = (b - a).normalized()
            angle = PILE_ANGLES[bone]
            horizontal = Vector((math.cos(angle), math.sin(angle), 0.0))
            rotation = axis.rotation_difference(horizontal)
        elif bone.startswith("mixamorig:Spine"):
            rotation = Vector((0.0, 0.0, 1.0)).rotation_difference(Vector((1.0, 0.0, 0.0)))
        else:
            rotation = Quaternion((0.0, 0.0, 1.0), PILE_ANGLES.get(bone, 0.0))
        ground_clearance = -min((rotation @ v).z for v in local)
        target.z = floor_z + ground_clearance + offset[2]
        final_transforms[bone] = (target, rotation)

    # Every segment follows a delayed, inward/downward arc and settles into its
    # authored slot. The tiny damped bounce sells impact without scattering.
    ordered = sorted(chunks)
    for order, bone in enumerate(ordered):
        obj = chunks[bone]["object"]
        start = chunks[bone]["origin"].copy()
        target, final_rotation = final_transforms[bone]
        delay = (order % 5) * 1.1
        for frame in range(START_FRAME, END_FRAME + 1):
            progress = smooth((frame - START_FRAME - delay) / (PILE_FRAME - START_FRAME - delay))
            pos = start.lerp(target, progress)
            bounce = math.sin(progress * math.pi * 3.0) * 0.035 * (1.0 - progress)
            pos.z += bounce
            spin = 0.22 * math.sin(progress * math.pi) * (1.0 - progress)
            spin_q = Quaternion((1.0, 0.0, 0.0), spin)
            obj.location = pos
            obj.rotation_quaternion = spin_q.slerp(final_rotation, progress)
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)

    bpy.context.view_layer.update()
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in chunks.values():
        obj["object"].select_set(True)
    bpy.context.view_layer.objects.active = chunks["mixamorig:Hips"]["object"]
    bpy.ops.export_scene.fbx(
        filepath=OUTPUT,
        use_selection=True,
        object_types={"MESH"},
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0,
        axis_forward="-Z",
        axis_up="Y",
    )
    print(f"DEATH_FBX_COMPLETE={OUTPUT}")
    print(f"PIECES={len(chunks)} FRAMES={START_FRAME}-{END_FRAME} PILE_FRAME={PILE_FRAME}")
    print(f"SOURCE_FLOOR_Z={floor_z:.4f}")


if __name__ == "__main__":
    main()
