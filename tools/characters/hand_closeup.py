"""Render de cerca de la mano derecha del Ojo (frente, perfil y arriba) de un FBX de clip.
blender -b -P tools/characters/hand_closeup.py -- <fbx> <png_salida> [frame=0] [ortho_m=0.35]"""
import bpy, sys, os
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_util import *
a = sys.argv[sys.argv.index('--') + 1:]
fbx, out = a[0], a[1]
frame = int(a[2]) if len(a) > 2 else 0
ortho = float(a[3]) if len(a) > 3 else 0.35
RES = 360
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.context.scene.frame_set(frame)
bpy.context.view_layer.update()
hand = arm.matrix_world @ arm.pose.bones['mixamorig:RightHand'].head
c = hand + Vector((0, -0.04, -0.07))      # un poco hacia delante y abajo: mano y cabeza colgando
sc = setup_render((RES, RES))
imgs = []
for v in ('front', 'side', 'top'):
    cam = make_cam(c, ortho, v)
    p = os.path.join(os.path.dirname(out), '_h.png'); render_to(p)
    im = bpy.data.images.load(p); arr = np.array(im.pixels[:]).reshape(RES, RES, 4).copy(); bpy.data.images.remove(im)
    imgs.append(arr)
    bpy.data.objects.remove(cam)
sheet = np.concatenate(imgs, axis=1)
img = bpy.data.images.new('s', sheet.shape[1], sheet.shape[0], alpha=True)
img.pixels = sheet.flatten().tolist(); img.filepath_raw = out; img.file_format = 'PNG'; img.save()
os.remove(os.path.join(os.path.dirname(out), '_h.png'))
