"""Construye monaguillo_walk.fbx transfiriendo el andar rezando de assets/models/animations/monaguillo/walk_pray.fbx al modelo monje zombi.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_monaguillo.py -- <raiz_worktree>

Salida: <raiz>/assets/models/characters/monaguillo/monaguillo_walk.fbx
"""
import bpy, sys, os, math, glob
from mathutils import Vector, Matrix

ROOT = sys.argv[sys.argv.index('--') + 1]
OUT = os.path.join(ROOT, 'assets/models/characters/monaguillo')
CHAR_FBX = glob.glob(os.path.join(OUT, 'source/tripo_convert_9a55a12b-*.fbx'))[0]
SRC_FBX = os.path.join(ROOT, 'assets/models/animations/monaguillo/walk_pray.fbx')

WALK_FRAMES = 48        # multiplo de 8 para el lab, +1 de cierre
P = 'mixamorig:'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=SRC_FBX)
src_arm = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE'][0]
src_act = src_arm.animation_data.action
scene = bpy.context.scene
PB = arm.pose.bones
MS3 = src_arm.matrix_world.to_3x3().normalized()
MT3 = arm.matrix_world.to_3x3().normalized()
SPB = src_arm.pose.bones


def update():
    bpy.context.view_layer.update()


def world_z(o, n):
    update()
    return (o.matrix_world @ o.data.bones[P + n].head_local).z


K = world_z(arm, 'Hips') / world_z(src_arm, 'Hips')
f0, f1 = int(round(src_act.frame_range[0])), int(round(src_act.frame_range[1]))
src_arm.animation_data_create()
src_arm.animation_data.action = src_act
if hasattr(src_arm.animation_data, 'action_slot') and src_act.slots:
    src_arm.animation_data.action_slot = src_act.slots[0]
arm.animation_data_create()
arm.animation_data.action = None
ORDER = [b.name[len(P):] for b in arm.data.bones]


def src_rot(n, rest3):
    sp = SPB.get(P + n); sb = src_arm.data.bones.get(P + n)
    R_delta = sp.matrix.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
    R_world = MS3 @ R_delta @ MS3.inverted()
    return (MT3.inverted() @ R_world @ MT3) @ rest3


act = bpy.data.actions.new('monaguillo_walk')
arm.animation_data.action = act
for i in range(WALK_FRAMES + 1):
    x = f0 + (f1 - f0) * (i % WALK_FRAMES) / float(WALK_FRAMES)
    fi = int(math.floor(x)); sub = x - fi
    scene.frame_set(fi, subframe=sub)
    update()
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    update()
    for n in ORDER:
        tb = arm.data.bones[P + n]
        if SPB.get(P + n) is None:
            continue
        rest3 = tb.matrix_local.to_3x3().normalized()
        R_des = src_rot(n, rest3)
        if n == 'Hips':
            sp = SPB[P + n]; sb = src_arm.data.bones[P + n]
            dz = ((src_arm.matrix_world @ sp.matrix).translation.z - (src_arm.matrix_world @ sb.matrix_local).translation.z) * K
            d = MT3.inverted() @ Vector((0, 0, dz * 100.0))
            head = tb.head_local + d
        else:
            head = PB[P + n].matrix.translation.copy()
        PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
        update()
    f = i + 1
    for pb in PB:
        pb.keyframe_insert('location', frame=f)
        pb.keyframe_insert('rotation_quaternion', frame=f)
        pb.keyframe_insert('scale', frame=f)

scene.frame_start = 1
scene.frame_end = WALK_FRAMES + 1

for o in list(bpy.data.objects):
    if o != arm and o not in meshes:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = arm

out_fbx = os.path.join(OUT, 'monaguillo_walk.fbx')
bpy.ops.export_scene.fbx(
    filepath=out_fbx,
    use_selection=True,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,
    path_mode='COPY',
    embed_textures=True,
)
print('Exported', out_fbx)
