"""Blender worker: make textured displaced tile variants and a 4x3 preview grid."""
import json
import math
import sys
from pathlib import Path

import os

import bpy

GAP = float(os.environ.get("FLOOR_TILE_GAP", ".015"))


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def make_tile(spec, color_path, height_path):
    nx = max(32, int(spec["tile_w"] * 96))
    ny = max(32, int(spec["tile_h"] * 96))
    verts, faces, uvs = [], [], []
    for j in range(ny + 1):
        v = j / ny
        for i in range(nx + 1):
            u = i / nx
            verts.append(((u - .5) * spec["tile_w"], (v - .5) * spec["tile_h"], 0))
            uvs.append((spec["u0"] + u * spec["uv_w"], spec["v0"] + v * spec["uv_h"]))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    mesh = bpy.data.meshes.new("ReliefGrid")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uv_layer.data[li].uv = uvs[mesh.loops[li].vertex_index]
    obj = bpy.data.objects.new("DisplacedFloor", mesh)
    bpy.context.collection.objects.link(obj)

    mat = bpy.data.materials.new("MudPlanksPuddles")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    color = bpy.data.images.load(str(color_path), check_existing=True)
    color.pack()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = color
    tex.interpolation = "Linear"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = .92
    obj.data.materials.append(mat)

    hmap = bpy.data.images.load(str(height_path), check_existing=True)
    pixels = list(hmap.pixels)
    hw, hh = hmap.size
    # Sample pixels per vertex; edge fade forces every border to z=0 for clean
    # repeated tiles while leaving interior relief intact.
    for j in range(ny + 1):
        v = j / ny
        for i in range(nx + 1):
            u = i / nx
            su = spec["u0"] + u * spec["uv_w"]
            sv = spec["v0"] + v * spec["uv_h"]
            x = min(hw - 1, max(0, int(su * (hw - 1))))
            y = min(hh - 1, max(0, int((1 - sv) * (hh - 1))))
            value = pixels[(y * hw + x) * 4]
            edge = min(u, 1 - u, v, 1 - v)
            fade = min(1.0, edge / .045)
            mesh.vertices[j * (nx + 1) + i].co.z = spec["relief"] * .55 + (value - .5) * spec["relief"] * fade
    for p in mesh.polygons:
        p.use_smooth = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    return obj


def export(path, selected):
    bpy.ops.object.select_all(action="DESELECT")
    for o in selected:
        o.select_set(True)
    bpy.context.view_layer.objects.active = selected[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                              export_apply=True)


def main():
    task = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
    color_path, height_path = Path(task["color"]), Path(task["height"])
    clear()
    tiles = []
    for spec in task["tiles"]:
        clear()
        obj = make_tile(spec, color_path, height_path)
        export(Path(spec["out"]), [obj])
        tiles.append((spec, obj))
    clear()
    grid_objects = []
    for idx, (spec, _) in enumerate(tiles):
        obj = make_tile(spec, color_path, height_path)
        col, row = idx % 4, idx // 4
        obj.location.x = col * (spec["tile_w"] + GAP)
        obj.location.y = -row * (spec["tile_h"] + GAP)
        if grid_objects:  # the lab textures a GLB reliably only with one shared material
            obj.data.materials[0] = grid_objects[0].data.materials[0]
        grid_objects.append(obj)
    export(Path(task["grid_out"]), grid_objects)
    print("created", len(tiles), "tiles and", task["grid_out"])


if __name__ == "__main__":
    main()
