"""Tira a tamano de juego: personaje a ~40 px de alto, ampliada 4x NEAREST, en 3 direcciones.
blender -b -P tools/characters/strip_40px.py -- <fbx> <png_salida> [nframes=6] [alto_px=40] [alto_m=0.92]"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_util import *
args = sys.argv[sys.argv.index('--') + 1:]
fbx, out = args[0], args[1]
n = int(args[2]) if len(args) > 2 else 6
H = int(args[3]) if len(args) > 3 else 40
height_m = float(args[4]) if len(args) > 4 else 0.92
RES = 64
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
act = arm.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
frames = [int(round(f0 + (f1 - f0) * i / n)) for i in range(n)]   # sin repetir el cierre
sc = setup_render((RES, RES))
sc.render.filter_size = 0.0                      # bordes duros, como un sprite
sc.world.color = (0.30, 0.30, 0.33)              # suelo gris medio-oscuro
center = Vector((0, 0, height_m / 2))
ortho = RES / H * height_m
cam_d = bpy.data.cameras.new('c'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
cam = bpy.data.objects.new('c', cam_d); sc.collection.objects.link(cam); sc.camera = cam
elev = math.radians(30)
rows = []
for az in (0, 45, 90):   # 0 = de frente (cam en -Y), 90 = perfil (cam en +X)
    a = math.radians(az)
    d = Vector((math.sin(a) * math.cos(elev), -math.cos(a) * math.cos(elev), math.sin(elev))) * 4
    cam.location = center + d
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    imgs = []
    for f in frames:
        sc.frame_set(f)
        p = os.path.join(os.path.dirname(out), '_t.png'); render_to(p)
        im = bpy.data.images.load(p); arr = np.array(im.pixels[:]).reshape(RES, RES, 4).copy(); bpy.data.images.remove(im)
        imgs.append(arr)
    rows.append(np.concatenate(imgs, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)       # imagen de Blender invertida en Y: frente arriba
sheet = sheet.repeat(4, axis=0).repeat(4, axis=1)  # 4x NEAREST
img = bpy.data.images.new('s', sheet.shape[1], sheet.shape[0], alpha=True)
img.pixels = sheet.flatten().tolist()
img.filepath_raw = out; img.file_format = 'PNG'; img.save()
os.remove(os.path.join(os.path.dirname(out), '_t.png'))
print('STRIP', sheet.shape)
