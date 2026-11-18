"""Construye los FBX animados del Corazon Abierto: corazon_{walk,disparo,agachado_andar}.fbx.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/build_corazon.py -- <raiz_worktree>

Entradas: modelo con esqueleto sin animar (corazon/source/corazon.fbx) y clips propios, solo armature + accion
(assets/models/animations/corazon/{walk,disparo,agachado_andar}.fbx; mismo esqueleto Mixamo de 65 huesos). La accion se asigna tal cual
al armature del modelo (mismos nombres de hueso, sin retarget); fps y tiempos de clave se conservan.
Salidas (derivadas, ignoradas por git): <raiz>/assets/models/characters/corazon/corazon_{walk,disparo,agachado_andar}.fbx
"""
import bpy, sys, os
from mathutils import Matrix

ROOT = sys.argv[sys.argv.index('--') + 1]
CHR = os.path.join(ROOT, 'assets/models/characters/corazon')
ANI = os.path.join(ROOT, 'assets/models/animations/corazon')
# (clip, accion final, fotograma en el que debe empezar el clip al importar el FBX final). Los clips de animations/
# empiezan en el 1; el andar original arrancaba en t = 1/30 s (fotograma 2) y el disparo en t = -1/24 s (fotograma 0).
# Blender no exporta tiempos negativos: el disparo se exporta desde el fotograma 1 y despues se desplaza el FBX.
CLIPS = [('walk', 'corazon_walk', 2), ('disparo', 'corazon_disparo', 0),
         ('agachado_andar', 'corazon_agachado_andar', 1)]
KTIME = 46186158000   # tics de tiempo FBX por segundo

def shift_fbx_times(path, dt):
    """Suma dt (tics FBX) a todas las claves y a los limites de la pila de animacion de un FBX binario."""
    from io_scene_fbx import parse_fbx, encode_bin
    root, version = parse_fbx.parse(path)

    def conv(e):
        n = encode_bin.FBXElem(e.id)
        for v, ty in zip(e.props, e.props_type):
            ty = chr(ty)
            if e.id == b'KeyTime' and ty == 'l':
                for i in range(len(v)):
                    v[i] += dt
            if ty == 'S':
                n.add_string(v)
            elif ty == 'L':
                if e.id == b'P' and e.props[0] in (b'LocalStart', b'LocalStop', b'ReferenceStart', b'ReferenceStop'):
                    v += dt
                n.add_int64(v)
            else:
                getattr(n, {'Z': 'add_int8', 'Y': 'add_int16', 'B': 'add_bool', 'C': 'add_char', 'I': 'add_int32',
                            'F': 'add_float32', 'D': 'add_float64', 'R': 'add_bytes', 'i': 'add_int32_array',
                            'l': 'add_int64_array', 'f': 'add_float32_array', 'd': 'add_float64_array',
                            'b': 'add_bool_array', 'c': 'add_byte_array'}[ty])(v)
        n.elems = [conv(c) for c in e.elems]
        return n

    out = conv(root)
    encode_bin.write(path, out, version)
    print('SHIFT', path, dt)


RETARGET = ('agachado_andar',)   # clips Mixamo con otra orientacion de ejes de hueso: se retargetean por orientacion en mundo


def _rot3(m):
    return m.to_3x3().normalized()


def retarget_action(arm, sa, aname):
    """Copia al esqueleto del modelo (arm) la animacion del esqueleto Mixamo sa, sin tocar ninguno de los dos.

    Los dos tienen los mismos 65 huesos pero otros ejes locales, asi que no se copian las rotaciones locales: por cada
    hueso se toma el giro en mundo respecto a su reposo y se aplica al reposo del modelo. La cadera se escala a la
    altura del modelo y se le quita el avance horizontal (in-place, como walk.fbx)."""
    scene = bpy.context.scene
    act = sa.animation_data.action
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    Rw = _rot3(sa.matrix_world)
    assert _rot3(arm.matrix_world).to_quaternion().angle < 1e-3, 'el modelo no esta alineado con el mundo'
    order = []

    def walk(b):
        order.append(b)
        for c in b.children:
            walk(c)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b)
    hs, ht = sa.data.bones['mixamorig:Hips'], arm.data.bones['mixamorig:Hips']
    ratio = ht.head_local.z / (Rw @ hs.head_local).z
    drift = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        drift.append(Rw @ (sa.pose.bones['mixamorig:Hips'].head - hs.head_local))
    net = drift[-1] - drift[0]
    net.z = 0
    fwd = net.normalized() if net.length > 1e-3 else None
    arm.animation_data_create()
    new_act = bpy.data.actions.new(aname)
    arm.animation_data.action = new_act
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for i, f in enumerate(range(f0, f1 + 1)):
        scene.frame_set(f)
        T = {}
        for b in order:
            s = sa.data.bones[b.name]
            Ps = Rw @ _rot3(sa.pose.bones[b.name].matrix)
            Rs = Rw @ _rot3(s.matrix_local)
            T[b.name] = (Ps @ Rs.inverted()) @ _rot3(b.matrix_local)
            rest = _rot3(b.matrix_local)
            if b.parent is None:
                basis = rest.inverted() @ T[b.name]
            else:
                basis = rest.inverted() @ _rot3(b.parent.matrix_local) @ T[b.parent.name].inverted() @ T[b.name]
            pb = arm.pose.bones[b.name]
            pb.rotation_quaternion = basis.to_quaternion()
            pb.keyframe_insert('rotation_quaternion', frame=f)
            if b.parent is None:
                d = drift[i].copy()
                if fwd is not None:
                    d -= fwd * (d.dot(fwd) - drift[0].dot(fwd))
                pb.location = rest.inverted() @ (d * ratio)
                pb.keyframe_insert('location', frame=f)
    arm.animation_data.action = None
    new_act.name = aname
    return new_act


for clip, name, start in CLIPS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHR, 'source/corazon.fbx'))
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ANI, clip + '.fbx'))   # fija el fps de la escena al del clip
    fps = scene.render.fps
    new = [o for o in bpy.data.objects if o not in before]
    src_arm = [o for o in new if o.type == 'ARMATURE'][0]
    assert {b.name for b in src_arm.data.bones} == {b.name for b in arm.data.bones}, 'esqueletos distintos'
    act = retarget_action(arm, src_arm, clip) if clip in RETARGET else src_arm.animation_data.action
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    act.use_fake_user = True
    if src_arm.animation_data:
        src_arm.animation_data.action = None
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    act.name = name
    arm.animation_data_create()
    arm.animation_data.action = act
    arm.animation_data.action_slot = act.slots[0]   # el slot del clip se llamaba como el armature de origen
    # el exportador escribe el tiempo de la clave como f/fps y el importador lo devuelve en f+1: las claves se llevan al
    # fotograma start-1 y la escena se limita a ese rango
    export_start = max(start, 1)
    post_shift = export_start - start   # fotogramas que se retrasan las claves en el FBX ya escrito
    dx = (export_start - 1) - f0
    for l in act.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    for kp in fc.keyframe_points:
                        kp.co.x += dx; kp.handle_left.x += dx; kp.handle_right.x += dx
                    fc.update()
    scene.name = name
    scene.frame_start, scene.frame_end = f0 + dx, f1 + dx
    scene.frame_set(f0 + dx)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in [arm] + meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(CHR, name + '.fbx')
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=False, add_leaf_bones=False, path_mode='COPY', embed_textures=True,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0, mesh_smooth_type='FACE')
    print('EXPORTED', path, 'fps', fps, 'frames', f0, f1)
    if post_shift:
        shift_fbx_times(path, -post_shift * KTIME // fps)

