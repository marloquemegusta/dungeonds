"""Build the first paired-lancet cathedral wall module in Blender and export GLB."""
import bpy
import math
import os
import sys
from mathutils import Vector


def material(name, color, metallic=0.0, roughness=0.82):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def prism(name, points, y0, y1, mat):
    # points use Blender's screen plane (X horizontal, Y vertical); y0/y1 are depth Z.
    verts = [(x, y, z) for z in (y0, y1) for x, y in points]
    n = len(points)
    # Local front faces point +Z; the whole module is turned toward the lab camera below.
    faces = [tuple(range(n)), tuple(range(n, 2*n))]
    faces += [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def box(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def lancet(cx, bottom, width, height, depth, glass, lead, stone):
    half = width / 2
    shoulder = bottom + height * 0.72
    tip = bottom + height
    # Dark pointed opening with a two-color glass field and a central mullion.
    points = [(cx-half, bottom), (cx+half, bottom), (cx+half, shoulder), (cx, tip), (cx-half, shoulder)]
    prism("LancetShadow", points, depth, depth+0.10, lead)
    inner = width * 0.76
    ih = height * 0.82
    ib = bottom + height * 0.08
    it = ib + ih
    ish = ib + ih * 0.72
    left = [(cx-inner/2, ib), (cx, ib), (cx, it), (cx-inner/2, ish)]
    right = [(cx, ib), (cx+inner/2, ib), (cx+inner/2, ish), (cx, it)]
    prism("GlassBurgundy", left, depth-0.025, depth+0.015, glass[0])
    prism("GlassBlueViolet", right, depth-0.026, depth+0.014, glass[1])
    # Lead rails and a gold crosspiece are kept broad enough to survive DS reduction.
    box("CentralMullion", (cx, (ib+it)/2, depth-0.05), (0.055, ih, 0.075), lead)
    box("Crossbar", (cx, ib+ih*0.43, depth-0.055), (inner, 0.045, 0.08), glass[2])
    # Stone archivolt follows the lancet silhouette in four coarse voussoirs.
    for side in (-1, 1):
        box("StoneJamb", (cx+side*(half+0.10), bottom+height*0.40, depth-0.08),
            (0.20, height*0.80, 0.22), stone)
    prism("PointedArchKeystone", [(cx-0.13, shoulder), (cx, tip+0.16), (cx+0.13, shoulder)],
          depth-0.10, depth+0.12, stone)


def main():
    out = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    stone = material("LimestoneWarmGray", (0.29, 0.27, 0.24))
    stone_lit = material("LimestoneEdge", (0.40, 0.37, 0.32))
    lead = material("DarkLead", (0.075, 0.065, 0.075), metallic=0.45)
    ruby = material("DeepBurgundyGlass", (0.32, 0.045, 0.10), metallic=0.08, roughness=0.24)
    violet = material("BlueVioletGlass", (0.08, 0.11, 0.32), metallic=0.08, roughness=0.24)
    gold = material("OldGold", (0.58, 0.34, 0.08), metallic=0.6, roughness=0.48)
    # A framed pair of lancets on a shallow wall panel; openings remain readable at game scale.
    box("WallBacking", (0, 2.3, 0), (3.2, 4.6, 0.28), stone)
    box("LowerPlinth", (0, 0.18, -0.14), (3.3, 0.36, 0.32), stone_lit)
    box("UpperStringCourse", (0, 4.25, -0.14), (3.3, 0.12, 0.30), stone_lit)
    for x in (-1.48, 1.48):
        box("Pilaster", (x, 2.28, -0.13), (0.22, 4.08, 0.30), stone_lit)
    lancet(-0.48, 0.78, 0.76, 2.65, 0.22, (ruby, violet, gold), lead, stone_lit)
    lancet(0.48, 0.78, 0.76, 2.65, 0.22, (violet, ruby, gold), lead, stone_lit)
    box("CentralPier", (0, 1.98, 0.28), (0.10, 2.40, 0.16), stone_lit)
    # The lab's fixed 45-degree azimuth views along local +Z; turn the façade to face it.
    parts = list(bpy.context.scene.objects)
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    root = bpy.context.object
    root.name = "LancetWallRoot"
    root.rotation_euler[1] = math.radians(135)
    for obj in parts:
        obj.parent = root
    # Set a useful viewport preview in the .blend, while the game render remains lab-driven.
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 512
    bpy.context.scene.render.resolution_y = 768
    bpy.context.scene.render.resolution_percentage = 100
    bpy.ops.wm.save_as_mainfile(filepath=out[:-4] + ".blend")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=False, export_materials="EXPORT")


main()
