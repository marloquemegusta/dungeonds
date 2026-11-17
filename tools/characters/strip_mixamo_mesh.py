"""Quita el maniqui (malla Beta_Joints/Beta_Surface) de los clips Mixamo de assets/models/animations/, dejando solo
armature + accion en el mismo archivo. Script de una sola vez (los FBX ya limpios estan versionados).

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/strip_mixamo_mesh.py -- <fbx>...
"""
import bpy, sys

for path in sys.argv[sys.argv.index('--') + 1:]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    act = arm.animation_data.action
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    for i in list(bpy.data.images):
        bpy.data.images.remove(i)
    act.name = 'mixamo.com'   # el exportador antepone el nombre del armature; asi la accion no acumula prefijos
    act.use_fake_user = True
    # sin accion activa y con la pose a cero el exportador escribe el reposo real
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE'},
        add_leaf_bones=False, path_mode='STRIP', embed_textures=False,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0)
    print('STRIPPED', path, tuple(act.frame_range), 'fps', bpy.context.scene.render.fps)
