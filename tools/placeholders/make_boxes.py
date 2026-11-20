"""Builds the placeholder GLBs (one box per prop) with Blender, headless.

  "<blender>" -b -P tools/placeholders/make_boxes.py

Writes assets/models/placeholders/<name>.glb. Each is a plain box with one flat material
(muted colors, never pure primaries). Temporary: replaced by the real Tripo models later.
"""
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models" / "placeholders"

# name: (dimensions in m (x, y, z), base RGB, emission strength, rotation in degrees (x, y, z))
SPECS = {
    "runa_xp":      ((0.25, 0.08, 0.40), (0.70, 0.52, 0.22), 0.15, (0, 0, 0)),
    "orbe_vida":    ((0.25, 0.25, 0.25), (0.55, 0.13, 0.12), 0.0, (0, 0, 0)),
    "orbe_mana":    ((0.25, 0.25, 0.25), (0.18, 0.27, 0.55), 0.0, (0, 0, 0)),
    "maldicion":    ((0.20, 0.20, 0.20), (0.40, 0.28, 0.45), 0.0, (45, 0, 45)),
    "aliado_marca": ((0.20, 0.20, 0.05), (0.55, 0.60, 0.48), 0.0, (0, 0, 0)),
}


def make_material(name, rgb, emission):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    if emission > 0.0:
        bsdf.inputs["Emission Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (dims, rgb, emission, rot) in SPECS.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, dims[2] / 2))
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (dims[0], dims[1], dims[2])
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if any(rot):
            obj.rotation_euler = tuple(math.radians(a) for a in rot)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.data.materials.append(make_material(name + "_mat", rgb, emission))
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(
            filepath=str(OUT / (name + ".glb")),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
        )
        print("GLB", name, dims, rgb)


if __name__ == "__main__":
    main()
