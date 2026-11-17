"""Separa el Corazon Abierto original en modelo + clips (convencion de assets/models/README: modelo en
characters/<p>/source/, clips en animations/<grupo>/). Script historico de una sola vez: los dos FBX de partida
(corazon.fbx con el clip de disparo y corazon_walk_normal.fbx con el de andar) ya no estan en el arbol; viven en el
historial de git.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/extract_corazon.py -- <raiz> <fbx_disparo> <fbx_walk>

Salidas:
  <raiz>/assets/models/characters/corazon/source/corazon.fbx   malla + armature, sin accion (reposo)
  <raiz>/assets/models/animations/corazon/walk.fbx             armature + accion (andar, 30 fps, frames 2-33)
  <raiz>/assets/models/animations/corazon/disparo.fbx          armature + accion (disparo, 24 fps, frames 0-23)
Cada clip queda normalizado (primera clave en el fotograma 1 al importar). El andar original empezaba en el fotograma 2
(t = 1/30 s) y el disparo en el 0 (clave a t = -1/24 s, que Blender no sabe exportar). build_corazon.py restituye esos
desfases para que el lab vea las mismas duraciones (1,07 s y 0,92 s).
"""
import bpy, sys, os

ROOT, DISPARO_FBX, WALK_FBX = sys.argv[sys.argv.index('--') + 1:][:3]
CHR = os.path.join(ROOT, 'assets/models/characters/corazon/source')
ANI = os.path.join(ROOT, 'assets/models/animations/corazon')
os.makedirs(CHR, exist_ok=True)
os.makedirs(ANI, exist_ok=True)


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    return arm, meshes


def mesh_signature(meshes):
    import numpy as np
    out = []
    for m in meshes:
        co = np.empty(len(m.data.vertices) * 3)
        m.data.vertices.foreach_get('co', co)
        out.append((m.name, len(m.data.vertices), len(m.data.polygons), co))
    return out


# ---- comprobar que las dos mallas originales son la misma
arm, meshes = load(WALK_FBX)
sig_walk = mesh_signature(meshes)
rest_walk = {b.name: tuple(round(x, 6) for r in b.matrix_local for x in r) for b in arm.data.bones}
arm, meshes = load(DISPARO_FBX)
sig_disp = mesh_signature(meshes)
rest_disp = {b.name: tuple(round(x, 6) for r in b.matrix_local for x in r) for b in arm.data.bones}
import numpy as np
for (n0, v0, p0, c0), (n1, v1, p1, c1) in zip(sig_walk, sig_disp):
    print('MESH', n0, n1, v0, v1, p0, p1, 'max |dv| = %.3e' % (np.abs(c0 - c1).max() if v0 == v1 else -1))
    assert v0 == v1 and p0 == p1
rest_diff = max(abs(a - b) for k in rest_disp for a, b in zip(rest_disp[k], rest_walk[k]))
print('REST max diff entre los dos armatures: %.3e' % rest_diff)


def export_arm_only(clip, out):
    arm, meshes = load(clip[0])
    act = arm.animation_data.action
    print('CLIP', clip[0], act.name, tuple(act.frame_range), 'fps', bpy.context.scene.render.fps,
          'fcurves no pose:', sorted({fc.data_path for l in act.layers for s in l.strips for cb in s.channelbags
                                      for fc in cb.fcurves if not fc.data_path.startswith('pose.bones')}))
    for o in meshes:
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    for i in list(bpy.data.images):
        bpy.data.images.remove(i)
    act.name = clip[1]
    act.use_fake_user = True
    arm.animation_data.action = None    # sin accion activa y con la pose a cero el exportador escribe el reposo real
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True, object_types={'ARMATURE'},
        add_leaf_bones=False, path_mode='STRIP', embed_textures=False,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0)
    print('EXPORTED', out)


export_arm_only((WALK_FBX, 'walk'), os.path.join(ANI, 'walk.fbx'))
export_arm_only((DISPARO_FBX, 'disparo'), os.path.join(ANI, 'disparo.fbx'))

# ---- modelo sin animacion (malla + armature en reposo)
arm, meshes = load(DISPARO_FBX)
for a in list(bpy.data.actions):
    a.use_fake_user = False
arm.animation_data.action = None
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for pb in arm.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for o in [arm] + meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
out = os.path.join(CHR, 'corazon.fbx')
bpy.ops.export_scene.fbx(
    filepath=out, use_selection=True, object_types={'ARMATURE', 'MESH'},
    use_mesh_modifiers=False, add_leaf_bones=False, path_mode='COPY', embed_textures=True,
    bake_anim=False, mesh_smooth_type='FACE')
print('EXPORTED', out)
