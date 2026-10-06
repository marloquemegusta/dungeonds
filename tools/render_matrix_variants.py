#!/usr/bin/env python3
"""
tools/render_matrix_variants.py
Genera una matriz homogénea de renders en 8 direcciones para los 3 personajes:
1. Mismo ángulo isométrico (30° elevación, 45° azimuth)
2. Misma luz direccional principal (Key Sun coincidente con la sombra proyectada del juego)
3. 4 variantes de iluminación, normales y grading sistemáticas para CADA modelo:
   - V1: Baseline Direccional Limpio (Key 4.5 + Fill 0.85 + Normal 100% + Textura PBR limpia)
   - V2: Normales Suavizadas (Key 4.5 + Fill 0.85 + Normal 35% + Textura PBR limpia)
   - V3: Chiaroscuro Equilibrado (Key 4.5 + Fill 0.65 + Normal 35% + Contraste moderado)
   - V4: Contraste Tonal NDS (Key 4.5 + Fill 0.65 + Normal 35% + Grading NDS 1.24C)
"""

import os
import sys
import math
import subprocess
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageChops

ROOT = r"C:\codexlocal\dungeonds"
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
OUT_ROOT = os.path.join(ROOT, "assets", "matrix_runs")
ARTIFACT_DIR = r"C:\Users\malfonso\.gemini\antigravity\brain\ad7a0809-368b-48fc-b06d-5b8a08c83a95"
WALKTHROUGH_ASSETS = os.path.join(ROOT, "walkthroughs", "08-standardize-character-shaders", "assets")

CELL = 64
NUM_DIRS = 8
NUM_FRAMES = 8
SAMPLES = 16  # Rápido y limpio con Cycles CPU denoising
ELEV = 30.0
PIXELS_PER_METRE = 32.0 / (2.0 * math.sqrt(2.0))  # 11.3137 px/m

# Definición de personajes y escalas ajustadas para caja 48x40 en EWRAM
CHARACTERS = {
    "hero": {
        "title": "Héroe Nigromante",
        "fbx": os.path.join(ROOT, "assets", "characters", "monster", "Walking.fbx"),
        "scale": 1.40,  # 1.40x llena la caja de 48x40 en pantalla con gran resolución
        "stride_3d_m": 1.5017,
        "anim_period": 3,
        "neck_pitch": 0.0,
        "armature_scale": 1.0,
        "displace": 0.0,
        "is_skeleton": False,
    },
    "charger": {
        "title": "Cargador (Maw)",
        "fbx": os.path.join(ROOT, "assets", "characters", "charger", "Run.fbx"),
        "scale": 1.35,  # 1.35x llena la caja de 48x40
        "stride_3d_m": 2.0000,
        "anim_period": 2,
        "neck_pitch": 20.0,
        "armature_scale": 1.0,
        "displace": 0.0,
        "is_skeleton": False,
    },
    "skeleton": {
        "title": "Esqueleto",
        "fbx": os.path.join(ROOT, "assets", "characters", "skeleton", "skeleton.fbx"),
        "scale": 1.35,  # 1.35x para llenar la caja
        "stride_3d_m": 1.2500,
        "anim_period": 3,
        "neck_pitch": 0.0,
        "armature_scale": 0.027,
        "displace": 0.12,  # Evita huesos rotos a baja resolución
        "is_skeleton": True,
    }
}

# 4 Variantes Homogéneas
VARIANTS = {
    "V1_baseline_clean": {
        "label": "V1: Baseline Direccional Limpio",
        "desc": "Luz direccional antorcha (Key 4.5) + Fill 0.85 + Normal 100% + Sin masses negras",
        "key_energy": 4.5,
        "fill_energy": 0.85,
        "world_strength": 0.35,
        "normal_strength": 1.0,
        "grade_contrast": 1.05,
        "grade_brightness": 1.02,
        "grade_saturation": 1.05,
    },
    "V2_normal_smooth": {
        "label": "V2: Normales Suavizadas (35%)",
        "desc": "Misma luz direccional limpia, pero Normal Map atenuado al 35% (anti-shimmering NDS)",
        "key_energy": 4.5,
        "fill_energy": 0.85,
        "world_strength": 0.35,
        "normal_strength": 0.35,
        "grade_contrast": 1.05,
        "grade_brightness": 1.02,
        "grade_saturation": 1.05,
    },
    "V3_balanced_chiaroscuro": {
        "label": "V3: Chiaroscuro Equilibrado",
        "desc": "Luz antorcha viva + Fill 0.65 + Normal 35% (volumen gótico legible)",
        "key_energy": 4.5,
        "fill_energy": 0.65,
        "world_strength": 0.25,
        "normal_strength": 0.35,
        "grade_contrast": 1.15,
        "grade_brightness": 1.00,
        "grade_saturation": 1.15,
    },
    "V4_tonal_contrast": {
        "label": "V4: Contraste Tonal NDS",
        "desc": "Grading con contraste reforzado (1.24) para dar pop en pantalla de Nintendo DS",
        "key_energy": 4.5,
        "fill_energy": 0.65,
        "world_strength": 0.25,
        "normal_strength": 0.35,
        "grade_contrast": 1.24,
        "grade_brightness": 0.98,
        "grade_saturation": 1.24,
    }
}

BLENDER_SCRIPT_TEMPLATE = r'''
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
NECK_PITCH = {neck_pitch}
ARMATURE_SCALE = {armature_scale}
DISPLACE = {displace}
IS_SKELETON = {is_skeleton}
NORMAL_STRENGTH = {normal_strength}
KEY_ENERGY = {key_energy}
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

# Escala física del armature
if ARMATURE_SCALE != 1.0:
    for arm in armatures:
        arm.scale = (ARMATURE_SCALE, ARMATURE_SCALE, ARMATURE_SCALE)

# Bloqueo de desplazamiento de raíz (in-place)
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

# Ajuste ergonómico de cuello/cabeza si aplica
if NECK_PITCH != 0.0:
    for arm in armatures:
        for b_name in ["mixamorig:Neck", "mixamorig:Head"]:
            if b_name in arm.pose.bones:
                b = arm.pose.bones[b_name]
                b.rotation_mode = 'XYZ'
                b.rotation_euler.x += math.radians(NECK_PITCH)

# Modificador Displace (Fattening para huesos finos)
if DISPLACE > 0.0:
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        fat = obj.modifiers.new('Fatten', 'DISPLACE')
        fat.strength = DISPLACE
        fat.mid_level = 0.0

# Materiales y Normal Maps
if IS_SKELETON:
    bone_mat = bpy.data.materials.new('BoneGothicClean')
    bone_mat.use_nodes = True
    bsdf = bone_mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.92, 0.88, 0.80, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.50
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        obj.data.materials.clear()
        obj.data.materials.append(bone_mat)
else:
    # Atenuación de Normal Map si existe en los materiales PBR
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

target = bpy.data.objects.new('CamTarget', None)
target.location = (root_anchor.x, root_anchor.y, 0.0)
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
_az = math.radians(45.0)
cam.location = (root_anchor.x + _dist * math.cos(_el) * math.cos(_az),
               root_anchor.y + _dist * math.cos(_el) * math.sin(_az),
               _dist * math.sin(_el))
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

# World Environment
w = bpy.data.worlds.new('DSWorld')
w.use_nodes = True
bg = w.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value = (0.04, 0.05, 0.07, 1.0)
    bg.inputs[1].default_value = WORLD_STRENGTH
scene.world = w

# Luz Direccional Principal (Key - Antorcha coincidente con sombras proyectadas del juego)
key_data = bpy.data.lights.new('Key', 'SUN')
key_data.energy = KEY_ENERGY
key_data.color = (1.0, 0.76, 0.46)
key_data.angle = math.radians(6.0)
key_data.use_shadow = True
key_obj = bpy.data.objects.new('Key', key_data)
key_obj.rotation_euler = (math.radians(55.0), math.radians(0.0), math.radians(150.0))
scene.collection.objects.link(key_obj)

# Luz de Relleno Opcional / Sombras (Fill)
fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = FILL_ENERGY
fill_data.color = (0.45, 0.55, 0.75)
fill_data.angle = math.radians(45.0)
fill_data.use_shadow = False
fill_obj = bpy.data.objects.new('Fill', fill_data)
fill_obj.rotation_euler = (math.radians(68.0), math.radians(0.0), math.radians(-35.0))
scene.collection.objects.link(fill_obj)

# Luz Rim Espectral
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

print("MATRIX_RENDER_DONE")
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

def build_8dir_collage(frames_dir, out_gif_path, title, subtitle, duration=100, zoom=2):
    cols = 4
    rows = 2
    pad = 12
    header_h = 44
    cell_pad_bottom = 22
    cell_w = CELL * zoom
    cell_h = CELL * zoom
    total_w = pad * (cols + 1) + cols * cell_w
    total_h = header_h + pad * (rows + 1) + rows * (cell_h + cell_pad_bottom)

    gif_frames = []
    for fi in range(NUM_FRAMES):
        canvas = Image.new('RGBA', (total_w, total_h), (16, 14, 20, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, total_w, header_h], fill=(24, 21, 30, 255))
        draw.text((pad, 8), title, fill=(245, 240, 250, 255))
        draw.text((pad, 25), subtitle, fill=(175, 170, 195, 255))

        for d in range(NUM_DIRS):
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
    print(f"  [GIF GENERADO] {out_gif_path}")

def main():
    os.makedirs(OUT_ROOT, exist_ok=True)
    os.makedirs(WALKTHROUGH_ASSETS, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    print("=================================================================")
    print("EJECUTANDO MATRIZ DE RENDERS HOMOGÉNEOS CON LUZ DIRECCIONAL CANÓNICA")
    print("=================================================================")

    manifest_kinematics = {}

    for char_key, char_cfg in CHARACTERS.items():
        print(f"\n>>> PROCESANDO PERSONAJE: {char_cfg['title']} ({char_key})")

        # Cálculo cinemático acoplado a la zancada
        stride_px = char_cfg["stride_3d_m"] * PIXELS_PER_METRE * char_cfg["scale"]
        frames_per_cycle = NUM_FRAMES * char_cfg["anim_period"]
        speed_fixed_8_8 = int(round((stride_px * 256.0) / frames_per_cycle))
        speed_px_frame = speed_fixed_8_8 / 256.0

        manifest_kinematics[char_key] = {
            "title": char_cfg["title"],
            "scale": char_cfg["scale"],
            "stride_3d_m": char_cfg["stride_3d_m"],
            "anim_period": char_cfg["anim_period"],
            "stride_px_screen": round(stride_px, 3),
            "speed_fixed_8_8": speed_fixed_8_8,
            "speed_px_frame": round(speed_px_frame, 3)
        }

        print(f"  Cinemática: Zancada 3D={char_cfg['stride_3d_m']:.3f}m -> {stride_px:.2f}px pantalla")
        print(f"  Velocidad acoplada: speed={speed_fixed_8_8} (8.8 fixed, ~{speed_px_frame:.3f} px/frame) periodo={char_cfg['anim_period']}")

        for var_key, var_cfg in VARIANTS.items():
            run_id = f"{char_key}_{var_key}"
            run_dir = os.path.join(OUT_ROOT, run_id)
            os.makedirs(run_dir, exist_ok=True)

            print(f"\n  * Variante: {var_cfg['label']}")

            # Render de fotogramas con Blender
            blender_script = BLENDER_SCRIPT_TEMPLATE.format(
                fbx=char_cfg["fbx"],
                out_dir=run_dir,
                cell=CELL,
                dirs=NUM_DIRS,
                frames=NUM_FRAMES,
                samples=SAMPLES,
                pxm=PIXELS_PER_METRE,
                scale=char_cfg["scale"],
                elev=ELEV,
                neck_pitch=char_cfg["neck_pitch"],
                armature_scale=char_cfg["armature_scale"],
                displace=char_cfg["displace"],
                is_skeleton=char_cfg["is_skeleton"],
                normal_strength=var_cfg["normal_strength"],
                key_energy=var_cfg["key_energy"],
                fill_energy=var_cfg["fill_energy"],
                world_strength=var_cfg["world_strength"]
            )

            tmp_py = os.path.join(run_dir, "render_worker.py")
            with open(tmp_py, "w", encoding="utf-8") as f:
                f.write(blender_script)

            p = subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, text=True)
            if "MATRIX_RENDER_DONE" not in p.stdout:
                print(p.stdout[-1500:])
                print(p.stderr[-1500:])
                raise RuntimeError(f"Error renderizando {run_id}")
            if os.path.exists(tmp_py):
                os.remove(tmp_py)

            # Post-proceso: Outline 1px anti-erosión y grading en PIL
            processed_dir = os.path.join(run_dir, "processed")
            os.makedirs(processed_dir, exist_ok=True)

            for d in range(NUM_DIRS):
                for fi in range(NUM_FRAMES):
                    raw_file = os.path.join(run_dir, f"d{d:02d}_f{fi:03d}.png")
                    with Image.open(raw_file) as im:
                        outlined = apply_outline(im)
                        graded = grade_image(
                            outlined,
                            var_cfg["grade_contrast"],
                            var_cfg["grade_brightness"],
                            var_cfg["grade_saturation"]
                        )
                        graded.save(os.path.join(processed_dir, f"d{d:02d}_f{fi:03d}.png"))

            # Crear collage GIF de 8 direcciones
            gif_name = f"{char_key}_{var_key}.gif"
            out_gif_walkthrough = os.path.join(WALKTHROUGH_ASSETS, gif_name)
            out_gif_artifact = os.path.join(ARTIFACT_DIR, gif_name)

            title = f"{char_cfg['title']} — {var_cfg['label']}"
            subtitle = f"Zancada: {stride_px:.1f}px | Speed C: {speed_fixed_8_8} (8.8) | {var_cfg['desc'][:70]}"

            build_8dir_collage(processed_dir, out_gif_walkthrough, title, subtitle)
            # Copiar también al artifact dir para visor de usuario
            import shutil
            shutil.copy2(out_gif_walkthrough, out_gif_artifact)

    # Guardar manifiesto cinemático
    kin_path = os.path.join(OUT_ROOT, "kinematics_manifest.json")
    with open(kin_path, "w", encoding="utf-8") as f:
        json.dump(manifest_kinematics, f, indent=2)
    print(f"\n[OK] Manifiesto cinemático guardado en {kin_path}")
    print("[MATRIZ DE 12 COLLAGES GENERADA EXITOSAMENTE]")

if __name__ == "__main__":
    main()
