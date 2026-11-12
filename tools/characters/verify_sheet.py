"""Hoja de contacto (frente arriba, perfil abajo) de un FBX reimportado.
blender -b -P verify_sheet.py -- <fbx> <png_salida> [nframes] [res]"""
import bpy, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_util import *
args = sys.argv[sys.argv.index('--') + 1:]
fbx, out = args[0], args[1]
n = int(args[2]) if len(args) > 2 else 5
res = int(args[3]) if len(args) > 3 else 300
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
act = arm.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
print("ACTION", act.name, f0, f1, "meshes", [o.name for o in bpy.data.objects if o.type == 'MESH'])
frames = sorted(set(int(round(f0 + (f1 - f0) * i / (n - 1))) for i in range(n)))
setup_render((res, res))
tmp = os.path.dirname(out)
cams = {v: make_cam(Vector((0, 0, 0.45)), 1.5, v) for v in ('front', 'side', 'top')}
rows = []
hip = []
for v in ('front', 'side', 'top'):
    bpy.context.scene.camera = cams[v]
    imgs = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        p = os.path.join(tmp, '_t.png'); render_to(p)
        im = bpy.data.images.load(p); a = np.array(im.pixels[:]).reshape(res, res, 4).copy(); bpy.data.images.remove(im)
        imgs.append(a)
        if v == 'front':
            h = arm.pose.bones['mixamorig:Hips'].head
            hip.append((f, round(h.x, 2), round(h.y, 2), round(h.z, 2)))
    rows.append(np.concatenate(imgs, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)   # filas: arriba = frente (bloque imagen invertido en Y)
img = bpy.data.images.new('sheet', sheet.shape[1], sheet.shape[0], alpha=True)
img.pixels = sheet.flatten().tolist()
img.filepath_raw = out; img.file_format = 'PNG'; img.save()
os.remove(os.path.join(tmp, '_t.png'))
print("HIPS (frame,x,y,z):", hip)
