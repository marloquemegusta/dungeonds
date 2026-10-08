#!/usr/bin/env python3
"""
tools/lab/shader_lab_server.py
Servidor interactivo y GUI Web local para tuning de modelos, shaders, iluminación y bakes en tiempo real con Blender.
Puerto por defecto: 8088.
"""

import os
import sys
import json
import math
import subprocess
import threading
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageChops

PORT = 8088
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
RUNS_DIR = os.path.join(ROOT, "assets", "lab_runs")
os.makedirs(RUNS_DIR, exist_ok=True)

# Parámetros canónicos
PIXELS_PER_METRE = 32.0 / (2.0 * math.sqrt(2.0))  # 11.3137 px/m

CHARACTERS_CONFIG = {
    "hero": {
        "name": "Héroe Nigromante",
        "fbx": os.path.join(ROOT, "assets", "characters", "monster", "Walking.fbx"),
        "default_scale": 1.40,
        "default_elevation": 30.0,
        "armature_scale": 1.0,
        "neck_pitch": 0.0,
        "displace": 0.0,
        "is_skeleton": False,
        "stride_3d_m": 1.5017,
        "anim_period": 3
    },
    "charger": {
        "name": "Cargador (Maw)",
        "fbx": os.path.join(ROOT, "assets", "characters", "charger", "Run.fbx"),
        "default_scale": 1.35,
        "default_elevation": 30.0,
        "armature_scale": 1.0,
        "neck_pitch": 20.0,
        "displace": 0.0,
        "is_skeleton": False,
        "stride_3d_m": 2.0000,
        "anim_period": 2
    },
    "skeleton": {
        "name": "Esqueleto",
        "fbx": os.path.join(ROOT, "assets", "characters", "skeleton", "skeleton.fbx"),
        "default_scale": 1.35,
        "default_elevation": 30.0,
        "armature_scale": 0.027,
        "neck_pitch": 0.0,
        "displace": 0.12,
        "is_skeleton": True,
        "stride_3d_m": 1.2500,
        "anim_period": 3
    }
}

BLENDER_WORKER_TEMPLATE = r'''
import bpy, math, os, mathutils

FBX = r"{fbx}"
OUT_DIR = r"{out_dir}"
CELL = {cell}
NUM_DIRS = {dirs}
NUM_FRAMES = {frames}
SAMPLES = {samples}
PX_PER_M = {pxm}
SCALE = {scale}
ELEV = {elev}
AZIMUTH = {azimuth}
NECK_PITCH = {neck_pitch}
ARMATURE_SCALE = {armature_scale}
DISPLACE = {displace}
IS_SKELETON = {is_skeleton}
NORMAL_STRENGTH = {normal_strength}
KEY_ENERGY = {key_energy}
KEY_ROT_X = {key_rot_x}
KEY_ROT_Y = {key_rot_y}
KEY_ROT_Z = {key_rot_z}
FILL_ENERGY = {fill_energy}
WORLD_STRENGTH = {world_strength}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)

actions = list(bpy.data.actions)
act = actions[0] if actions else None
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if act:
    for arm in armatures:
        if not arm.animation_data:
            arm.animation_data_create()
        arm.animation_data.action = act
    start_f = int(act.frame_range[0]); end_f = int(act.frame_range[1])
else:
    start_f = bpy.context.scene.frame_start; end_f = bpy.context.scene.frame_end

if ARMATURE_SCALE != 1.0:
    for arm in armatures:
        arm.scale = (ARMATURE_SCALE, ARMATURE_SCALE, ARMATURE_SCALE)

# In-place lock
bpy.context.scene.frame_set(start_f)
for arm in armatures:
    for bone_name in ["mixamorig:Hips", "Hips", "root", "Root"]:
        if bone_name in arm.pose.bones:
            bone = arm.pose.bones[bone_name]
            c = bone.constraints.new(type='LIMIT_LOCATION')
            c.owner_space = 'LOCAL'
            c.use_min_x = c.use_max_x = True
            c.min_x = c.max_x = bone.location.x
            c.use_min_z = c.use_max_z = True
            c.min_z = c.max_z = bone.location.z
            break

if NECK_PITCH != 0.0:
    for arm in armatures:
        for b_name in ["mixamorig:Neck", "mixamorig:Head"]:
            if b_name in arm.pose.bones:
                b = arm.pose.bones[b_name]
                b.rotation_mode = 'XYZ'
                b.rotation_euler.x += math.radians(NECK_PITCH)

if DISPLACE > 0.0:
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        fat = obj.modifiers.new('Fatten', 'DISPLACE')
        fat.strength = DISPLACE
        fat.mid_level = 0.0

if IS_SKELETON:
    bone_mat = bpy.data.materials.new('BoneClean')
    bone_mat.use_nodes = True
    bsdf = bone_mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.92, 0.88, 0.80, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.50
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        obj.data.materials.clear()
        obj.data.materials.append(bone_mat)
else:
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'NORMAL_MAP':
                    node.inputs['Strength'].default_value = NORMAL_STRENGTH

bpy.context.view_layer.update()
root_anchor = armatures[0].matrix_world.translation.copy() if armatures else mathutils.Vector((0.0, 0.0, 0.0))

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = CELL
scene.render.resolution_y = CELL

# Evaluate character bounding height to vertically center the camera
dg = bpy.context.evaluated_depsgraph_get()
_all_z = []
for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
    ev = obj.evaluated_get(dg)
    for corner in ev.bound_box:
        _all_z.append((ev.matrix_world @ mathutils.Vector(corner)).z)
_char_height = (max(_all_z) - min(_all_z)) if _all_z else 1.835
_target_z = _char_height * 0.50

target = bpy.data.objects.new('CamTarget', None)
target.location = (root_anchor.x, root_anchor.y, _target_z)
scene.collection.objects.link(target)

rig = bpy.data.objects.new('CameraRig', None)
rig.location = root_anchor
scene.collection.objects.link(rig)

for obj in [o for o in bpy.data.objects if o.type in {{'MESH', 'ARMATURE'}}]:
    world_matrix = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_world = world_matrix

cam_data = bpy.data.cameras.new('IsoCam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = CELL / (PX_PER_M * SCALE)
cam = bpy.data.objects.new('IsoCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

_el = math.radians(ELEV)
_dist = 30.0
_az = math.radians(AZIMUTH)
cam.location = (root_anchor.x + _dist * math.cos(_el) * math.cos(_az),
               root_anchor.y + _dist * math.cos(_el) * math.sin(_az),
               _target_z + _dist * math.sin(_el))
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

# World
w = bpy.data.worlds.new('DSWorld')
w.use_nodes = True
bg = w.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value = (0.04, 0.05, 0.07, 1.0)
    bg.inputs[1].default_value = WORLD_STRENGTH
scene.world = w

# Key light
key_data = bpy.data.lights.new('Key', 'SUN')
key_data.energy = KEY_ENERGY
key_data.color = (1.0, 0.76, 0.46)
key_data.angle = math.radians(6.0)
key_data.use_shadow = True
key_obj = bpy.data.objects.new('Key', key_data)
key_obj.rotation_euler = (math.radians(KEY_ROT_X), math.radians(KEY_ROT_Y), math.radians(KEY_ROT_Z))
scene.collection.objects.link(key_obj)

# Fill light
fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = FILL_ENERGY
fill_data.color = (0.45, 0.55, 0.75)
fill_data.angle = math.radians(45.0)
fill_data.use_shadow = False
fill_obj = bpy.data.objects.new('Fill', fill_data)
fill_obj.rotation_euler = (math.radians(68.0), math.radians(0.0), math.radians(-35.0))
scene.collection.objects.link(fill_obj)

# Rim light
rim_data = bpy.data.lights.new('Rim', 'SUN')
rim_data.energy = 0.85
rim_data.color = (0.60, 0.80, 1.00)
rim_data.angle = math.radians(30.0)
rim_data.use_shadow = False
rim_obj = bpy.data.objects.new('Rim', rim_data)
rim_obj.rotation_euler = (math.radians(72.0), math.radians(0.0), math.radians(55.0))
scene.collection.objects.link(rim_obj)

os.makedirs(OUT_DIR, exist_ok=True)
total = max(1, end_f - start_f)
frame_indices = [int(start_f + (i * total) / NUM_FRAMES) for i in range(NUM_FRAMES)]

for d in range(NUM_DIRS):
    rig.rotation_euler.z = math.radians(135.0 - d * 360.0 / NUM_DIRS)
    bpy.context.view_layer.update()
    for fi, fnum in enumerate(frame_indices):
        scene.frame_set(fnum)
        rig.location.z = root_anchor.z
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        lowest_z = 1e9
        for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
            ev = obj.evaluated_get(dg)
            for corner in ev.bound_box:
                lowest_z = min(lowest_z, (ev.matrix_world @ mathutils.Vector(corner)).z)
        rig.location.z = root_anchor.z - lowest_z
        bpy.context.view_layer.update()
        scene.render.filepath = os.path.join(OUT_DIR, "d%02d_f%03d.png" % (d, fi))
        bpy.ops.render.render(write_still=True)

print("LAB_RENDER_DONE")
'''

def apply_outline(im, color=(16, 16, 24), alpha_thresh=40):
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    w, h = im.size
    r, g, b, a = im.split()
    solid = a.point(lambda p: 255 if p > alpha_thresh else 0, mode='L')
    left = ImageChops.offset(solid, -1, 0)
    right = ImageChops.offset(solid, 1, 0)
    up = ImageChops.offset(solid, 0, -1)
    down = ImageChops.offset(solid, 0, 1)
    dilated = ImageChops.lighter(solid, left)
    dilated = ImageChops.lighter(dilated, right)
    dilated = ImageChops.lighter(dilated, up)
    dilated = ImageChops.lighter(dilated, down)
    outline_mask = ImageChops.subtract(dilated, solid)
    opaque_a = ImageChops.lighter(a, solid)
    opaque_im = Image.merge("RGBA", (r, g, b, opaque_a))
    outline_img = Image.new("RGBA", (w, h), (color[0], color[1], color[2], 255))
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base.paste(outline_img, (0, 0), outline_mask)
    base.alpha_composite(opaque_im)
    return base

def grade_image(img, contrast, brightness, saturation):
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)
    return img

DIR_NAMES = [
    "0: S (Sur)", "1: SW (Suroeste)", "2: W (Oeste)", "3: NW (Noroeste)",
    "4: N (Norte)", "5: NE (Noreste)", "6: E (Este)", "7: SE (Sureste)"
]

def build_8dir_collage(frames_dir, out_gif_path, title, subtitle, duration=100, zoom=2, cell=64):
    cols = 4
    rows = 2
    pad = 12
    header_h = 44
    cell_pad_bottom = 22
    cell_w = cell * zoom
    cell_h = cell * zoom
    total_w = pad * (cols + 1) + cols * cell_w
    total_h = header_h + pad * (rows + 1) + rows * (cell_h + cell_pad_bottom)

    gif_frames = []
    for fi in range(8):
        canvas = Image.new('RGBA', (total_w, total_h), (16, 14, 20, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, total_w, header_h], fill=(24, 21, 30, 255))
        draw.text((pad, 8), title, fill=(245, 240, 250, 255))
        draw.text((pad, 25), subtitle, fill=(175, 170, 195, 255))

        for d in range(8):
            col = d % cols
            row = d // cols
            x0 = pad + col * (cell_w + pad)
            y0 = header_h + pad + row * (cell_h + cell_pad_bottom + pad)

            draw.rectangle([x0 - 2, y0 - 2, x0 + cell_w + 1, y0 + cell_h + 1],
                           fill=(28, 25, 34, 255), outline=(50, 45, 62, 255))

            fpath = os.path.join(frames_dir, f"d{d:02d}_f{fi:03d}.png")
            if os.path.exists(fpath):
                im = Image.open(fpath).convert('RGBA')
                im_scaled = im.resize((cell_w, cell_h), Image.Resampling.NEAREST)
                canvas.paste(im_scaled, (x0, y0), im_scaled)

            draw.text((x0 + 4, y0 + cell_h + 4), DIR_NAMES[d], fill=(180, 175, 195, 255))

        gif_frames.append(canvas.convert('P', palette=Image.Palette.ADAPTIVE))

    os.makedirs(os.path.dirname(out_gif_path), exist_ok=True)
    gif_frames[0].save(out_gif_path, save_all=True, append_images=gif_frames[1:], duration=duration, loop=0)
    return out_gif_path

def execute_render_job(params):
    char_key = params.get("character", "hero")
    char_cfg = CHARACTERS_CONFIG[char_key]
    
    scale = float(params.get("scale", char_cfg["default_scale"]))
    elev = float(params.get("elevation", char_cfg["default_elevation"]))
    azimuth = float(params.get("azimuth", 45.0))
    samples = int(params.get("samples", 12))
    
    key_energy = float(params.get("key_energy", 4.5))
    key_rot_x = float(params.get("key_rot_x", 55.0))
    key_rot_y = float(params.get("key_rot_y", 0.0))
    key_rot_z = float(params.get("key_rot_z", 150.0))
    fill_energy = float(params.get("fill_energy", 0.85))
    world_strength = float(params.get("world_strength", 0.35))
    normal_strength = float(params.get("normal_strength", 0.35))
    
    contrast = float(params.get("contrast", 1.15))
    brightness = float(params.get("brightness", 1.00))
    saturation = float(params.get("saturation", 1.15))
    outline_enabled = bool(params.get("outline", True))
    
    job_id = f"{char_key}_{int(scale*100)}_{int(elev)}_{int(key_energy*10)}_{int(fill_energy*10)}_{int(normal_strength*100)}_{int(contrast*100)}"
    job_dir = os.path.join(RUNS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # 1. Blender Render
    worker_script = BLENDER_WORKER_TEMPLATE.format(
        fbx=char_cfg["fbx"],
        out_dir=job_dir,
        cell=64,
        dirs=8,
        frames=8,
        samples=samples,
        pxm=PIXELS_PER_METRE,
        scale=scale,
        elev=elev,
        azimuth=azimuth,
        neck_pitch=char_cfg["neck_pitch"],
        armature_scale=char_cfg["armature_scale"],
        displace=char_cfg["displace"],
        is_skeleton=char_cfg["is_skeleton"],
        normal_strength=normal_strength,
        key_energy=key_energy,
        key_rot_x=key_rot_x,
        key_rot_y=key_rot_y,
        key_rot_z=key_rot_z,
        fill_energy=fill_energy,
        world_strength=world_strength
    )
    
    tmp_py = os.path.join(job_dir, "worker.py")
    with open(tmp_py, "w", encoding="utf-8") as f:
        f.write(worker_script)
        
    p = subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, text=True)
    if "LAB_RENDER_DONE" not in p.stdout:
        print(p.stdout[-1200:])
        print(p.stderr[-1200:])
        raise RuntimeError(f"Blender render falló para job {job_id}")
    if os.path.exists(tmp_py):
        os.remove(tmp_py)

    # 2. Post-process PIL
    proc_dir = os.path.join(job_dir, "processed")
    os.makedirs(proc_dir, exist_ok=True)
    for d in range(8):
        for fi in range(8):
            src_f = os.path.join(job_dir, f"d{d:02d}_f{fi:03d}.png")
            if os.path.exists(src_f):
                with Image.open(src_f) as im:
                    out_im = apply_outline(im) if outline_enabled else im.convert("RGBA")
                    out_im = grade_image(out_im, contrast, brightness, saturation)
                    out_im.save(os.path.join(proc_dir, f"d{d:02d}_f{fi:03d}.png"))
                    
    # 3. Cálculo cinemático acoplado
    stride_px = char_cfg["stride_3d_m"] * PIXELS_PER_METRE * scale
    frames_per_cycle = 8 * char_cfg["anim_period"]
    speed_fixed_8_8 = int(round((stride_px * 256.0) / frames_per_cycle))
    speed_px_frame = speed_fixed_8_8 / 256.0
    
    # 4. GIF Collage
    gif_path = os.path.join(job_dir, "collage_8dirs.gif")
    title = f"{char_cfg['name']} — Escala {scale:.2f}x | Elev {elev:.0f}° | Normales {int(normal_strength*100)}%"
    subtitle = f"Zancada: {stride_px:.1f}px | Speed C: {speed_fixed_8_8} (8.8) | Fill: {fill_energy} | Contr: {contrast}"
    build_8dir_collage(proc_dir, gif_path, title, subtitle)
    
    return {
        "job_id": job_id,
        "gif_url": f"/runs/{job_id}/collage_8dirs.gif",
        "stride_px": round(stride_px, 2),
        "speed_fixed_8_8": speed_fixed_8_8,
        "speed_px_frame": round(speed_px_frame, 3),
        "anim_period": char_cfg["anim_period"]
    }

class LabHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shader_lab_ui.html")
            with open(html_path, "rb") as f:
                self.wfile.write(f.read())
            return
        elif url.path.startswith("/runs/"):
            rel_path = url.path[len("/runs/"):]
            file_path = os.path.join(RUNS_DIR, rel_path)
            if os.path.exists(file_path):
                self.send_response(200)
                if file_path.endswith(".gif"):
                    self.send_header("Content-Type", "image/gif")
                elif file_path.endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
        elif url.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(CHARACTERS_CONFIG).encode())
            return
        self.send_error(404, "File not found")

    def do_POST(self):
        if self.path == "/api/render":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            params = json.loads(body)
            try:
                res = execute_render_job(params)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return
        self.send_error(404, "Endpoint not found")

def main():
    print(f"Iniciando DS Shader Lab Web en http://localhost:{PORT}")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), LabHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")

if __name__ == "__main__":
    main()
