"""Extrae del Cireneo v1 (Tripo) SOLO el armature con las acciones walk y charge.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/extract_cireneo_v1_clips.py -- <raiz> [<fbx_v1>]

Lee <raiz>/assets/models/characters/cireneo/source/tripo_convert_172f5fef-dd4a-431e-99f9-1ab308e5dd5f.fbx
(o <fbx_v1> si se indica) y escribe <raiz>/assets/models/animations/cireneo/v1_clips.fbx
(armature + acciones, sin mesh, materiales ni texturas). build_cireneo_v2.py lo usa como OLD_FBX.
Historico: el FBX v1 de entrada ya no esta en el arbol (vive en el historial de git); el resultado esta versionado.
"""
import bpy, sys, os

args = sys.argv[sys.argv.index('--') + 1:]
ROOT = args[0]
CIR = os.path.join(ROOT, 'assets/models/characters/cireneo')
SRC = args[1] if len(args) > 1 else os.path.join(CIR, 'source/tripo_convert_172f5fef-dd4a-431e-99f9-1ab308e5dd5f.fbx')
OUT = os.path.join(ROOT, 'assets/models/animations/cireneo/v1_clips.fbx')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
for o in [o for o in bpy.data.objects if o.type != 'ARMATURE']:
    bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    bpy.data.meshes.remove(m)
for m in list(bpy.data.materials):
    bpy.data.materials.remove(m)
for i in list(bpy.data.images):
    bpy.data.images.remove(i)
keep = [a for a in bpy.data.actions if 'walk' in a.name or 'charge' in a.name]
for a in list(bpy.data.actions):
    if a not in keep:
        bpy.data.actions.remove(a)
for a in keep:
    a.use_fake_user = True
print('CLIPS', [(a.name, tuple(a.frame_range)) for a in keep])

# el exportador escribe como reposo la pose evaluada: dejar el rig en reposo (sin accion activa)
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, object_types={'ARMATURE'},
    add_leaf_bones=False, path_mode='STRIP', embed_textures=False,
    bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0, bake_anim_step=1.0)
print('EXPORTED', OUT)
