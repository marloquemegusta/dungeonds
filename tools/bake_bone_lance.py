#!/usr/bin/env python3
"""Bake a polished DS projectile sprite using the project's shared e30 look."""

import argparse
import math
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_look as look

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
CELL = 64
DIRS = [
    (0, 1), (-1, 1), (-1, 0), (-1, -1),
    (0, -1), (1, -1), (1, 0), (1, 1),
]

WORKER = r'''
import bpy, math, os
from mathutils import Vector

OUT = r"{out}"
CELL = {cell}
ELEV = {elev}
PX_PER_M = {pxm}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.render.resolution_x = CELL
scene.render.resolution_y = CELL
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1

# Project's shared gothic torch key, cool fill and spectral rim.
def sun(name, energy, color, rot, angle):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(angle)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.rotation_euler = tuple(math.radians(v) for v in rot)
    return obj

sun("AmberKey", 4.5, (1.0, 0.76, 0.46), (55, 0, 150), 6)
sun("SlateFill", 0.5, (0.30, 0.40, 0.65), (68, 0, -35), 45)
sun("SpectralRim", 0.85, (0.60, 0.80, 1.0), (72, 0, 55), 30)

world = bpy.data.worlds.new("DSWorld")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.015, 0.02, 0.035, 1)
bg.inputs[1].default_value = 0.18
scene.world = world

def principled(name, color, metallic=0.0, roughness=0.42):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

bone = principled("OldIvory", (0.72, 0.60, 0.40), roughness=0.32)
bone_light = principled("CutIvory", (0.92, 0.82, 0.63), roughness=0.26)
bone_shadow = principled("BoneSeam", (0.17, 0.12, 0.10), roughness=0.6)

def emission(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(em.outputs[0], out.inputs["Surface"])
    return mat

soul = emission("SoulCyan", (0.025, 0.55, 0.95), 2.0)
soul_dim = emission("SoulBlue", (0.015, 0.20, 0.55), 1.1)

# A tapered, irregular bone shaft with a sharp lance point and enlarged knuckle.
rings = [
    (-1.03, 0.015, 0.025), (-0.88, 0.075, 0.085),
    (-0.72, 0.11, 0.105), (-0.54, 0.068, 0.070),
    (-0.32, 0.050, 0.052), (-0.08, 0.048, 0.047),
    (0.18, 0.060, 0.055), (0.36, 0.080, 0.070),
    (0.50, 0.045, 0.042), (1.02, 0.002, 0.002),
]
segments = 10
verts = []
faces = []
for ri, (x, ry, rz) in enumerate(rings):
    for j in range(segments):
        a = (2 * math.pi * j / segments) + (0.10 if ri % 2 else 0.0)
        wobble = 1.0 + 0.06 * math.sin(j * 2.7 + ri * 1.9)
        verts.append((x, math.cos(a) * ry * wobble, math.sin(a) * rz * wobble))
for ri in range(len(rings) - 1):
    for j in range(segments):
        a = ri * segments + j
        b = ri * segments + (j + 1) % segments
        faces.append((a, b, b + segments, a + segments))
faces.append(tuple(range(segments - 1, -1, -1)))
faces.append(tuple((len(rings) - 1) * segments + j for j in range(segments)))
mesh = bpy.data.meshes.new("LanceBoneMesh")
mesh.from_pydata(verts, [], faces)
mesh.materials.append(bone)
mesh.materials.append(bone_light)
root = bpy.data.objects.new("BoneLanceRoot", None)
scene.collection.objects.link(root)
root.scale = (2.0, 2.0, 2.0)
obj = bpy.data.objects.new("BoneLance", mesh)
scene.collection.objects.link(obj)
obj.parent = root
for poly in mesh.polygons:
    poly.use_smooth = True
    # The forward half catches a pale, sharp highlight.
    if poly.index // segments >= 6:
        poly.material_index = 1

# Dark collars make the knuckled bone read clearly at native DS resolution.
for x, major, minor in [(-0.73, 0.085, 0.018), (0.34, 0.064, 0.012)]:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor, major_segments=10,
        minor_segments=4, location=(x, 0, 0))
    collar = bpy.context.object
    collar.name = "BoneJoint"
    collar.rotation_euler[1] = math.radians(90)
    collar.parent = root
    collar.data.materials.append(bone_shadow)

# Narrow spectral seams and three tapered afterimage wisps trail the shaft.
for idx, (x, z, length) in enumerate([(-0.55, 0.075, 0.34), (-0.28, -0.045, 0.25), (-0.04, 0.05, 0.18)]):
    curve = bpy.data.curves.new("SoulTrace", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = 0.018 if idx == 0 else 0.012
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    spline.points.add(2)
    spline.points[0].co = (x - length, -0.02, z - 0.10, 1)
    spline.points[1].co = (x - length * 0.45, 0.015, z, 1)
    spline.points[2].co = (x, 0.02, z + 0.015, 1)
    trace = bpy.data.objects.new("SoulAfterimage", curve)
    scene.collection.objects.link(trace)
    trace.parent = root
    curve.materials.append(soul if idx == 0 else soul_dim)

# Camera matches the character/environment orthographic scale and e30 elevation.
target = bpy.data.objects.new("Aim", None)
scene.collection.objects.link(target)
target.location = (0, 0, 0.0)
cam_data = bpy.data.cameras.new("IsoCam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = max(CELL, CELL) / PX_PER_M
cam = bpy.data.objects.new("IsoCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
track = cam.constraints.new(type="TRACK_TO")
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
el = math.radians(ELEV)
az = math.radians(45.0)
dist = 30.0
cam.location = (dist * math.cos(el) * math.cos(az),
                dist * math.cos(el) * math.sin(az),
                dist * math.sin(el))

# Aim each baked sprite along a projected screen octant in the dimetric world.
screen_dirs = [(0, 1), (-1, 1), (-1, 0), (-1, -1),
               (0, -1), (1, -1), (1, 0), (1, 1)]
for d, (sx, sy) in enumerate(screen_dirs):
    dc = sx + 2 * sy
    dr = 2 * sy - sx
    root.rotation_euler[2] = math.atan2(dr, dc)
    scene.render.filepath = os.path.join(OUT, "dir_%02d.png" % d)
    bpy.ops.render.render(write_still=True)
print("BONE_LANCE_BAKE_COMPLETE")
'''

def bgr555(r, g, b, a):
    if a < 110:
        return 0
    return 0x8000 | ((r >> 3) & 31) | (((g >> 3) & 31) << 5) | (((b >> 3) & 31) << 10)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=("e30",), default="e30")
    args = ap.parse_args()

    from PIL import Image
    out_dir = os.path.join(ROOT, "assets", "effects", "bone_lance")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bone_lance_") as temp:
        worker_path = os.path.join(temp, "worker.py")
        script = WORKER.replace("{out}", temp.replace("\\\\", "/"))
        script = script.replace("{cell}", str(CELL))
        script = script.replace("{elev}", str(look.elevation(args.preset)))
        script = script.replace("{pxm}", str(look.PIXELS_PER_METRE))
        with open(worker_path, "w", encoding="utf-8") as f:
            f.write(script)
        proc = subprocess.run([BLENDER_EXE, "-b", "-P", worker_path],
                              capture_output=True, text=True)
        if proc.returncode != 0 or "BONE_LANCE_BAKE_COMPLETE" not in proc.stdout:
            raise RuntimeError((proc.stdout[-2000:] + "\n" + proc.stderr[-2000:]).strip())

        sheet = Image.new("RGBA", (CELL, CELL * len(DIRS)), (0, 0, 0, 0))
        for d in range(len(DIRS)):
            with Image.open(os.path.join(temp, "dir_%02d.png" % d)) as im:
                frame = look.apply_outline(im.convert("RGBA"))
                sheet.paste(frame, (0, d * CELL))
        sheet = look.grade(sheet)
        sheet.save(os.path.join(out_dir, "bone_lance_e30.png"))

        header_path = os.path.join(ROOT, "include", "bone_lance_sprite.h")
        source_path = os.path.join(ROOT, "source", "bone_lance_sprite.c")
        with open(header_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("""#ifndef BONE_LANCE_SPRITE_INCLUDE_H
#define BONE_LANCE_SPRITE_INCLUDE_H

#include <stdint.h>

#define BONE_LANCE_SPRITE_W 64
#define BONE_LANCE_SPRITE_HEIGHT 64
#define BONE_LANCE_NUM_DIRS 8

extern const uint16_t g_bone_lance_frames[BONE_LANCE_NUM_DIRS]
    [BONE_LANCE_SPRITE_W * BONE_LANCE_SPRITE_HEIGHT];

#endif
""")
        with open(source_path, "w", encoding="utf-8", newline="\n") as f:
            f.write('#include "bone_lance_sprite.h"\n\n')
            f.write("const uint16_t g_bone_lance_frames[BONE_LANCE_NUM_DIRS]"
                    "[BONE_LANCE_SPRITE_W * BONE_LANCE_SPRITE_HEIGHT] = {\n")
            for d in range(len(DIRS)):
                f.write("    {\n")
                with Image.open(os.path.join(out_dir, "bone_lance_e30.png")) as baked:
                    frame = baked.crop((0, d * CELL, CELL, (d + 1) * CELL)).convert("RGBA")
                    vals = [bgr555(*frame.getpixel((x, y))) for y in range(CELL) for x in range(CELL)]
                for i in range(0, len(vals), 12):
                    f.write("        " + ", ".join("0x%04X" % v for v in vals[i:i + 12]) + ",\n")
                f.write("    },\n")
            f.write("};\n")
    print(f"[OK] assets/effects/bone_lance/bone_lance_e30.png")
    print(f"[OK] include/bone_lance_sprite.h + source/bone_lance_sprite.c")

if __name__ == "__main__":
    main()
