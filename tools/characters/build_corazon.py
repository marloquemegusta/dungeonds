"""Construye los FBX animados del Corazon Abierto: corazon_{walk,disparo,agachado_andar}.fbx.

Uso:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/characters/build_corazon.py -- <raiz_worktree>

Entradas: modelo con esqueleto sin animar (corazon/source/corazon.fbx) y clips propios, solo armature + accion
(assets/models/animations/corazon/{walk,disparo,agachado_andar}.fbx; mismo esqueleto Mixamo de 65 huesos). La accion se asigna tal cual
al armature del modelo (mismos nombres de hueso, sin retarget); fps y tiempos de clave se conservan.
Salidas (derivadas, ignoradas por git): <raiz>/assets/models/characters/corazon/corazon_{walk,disparo,agachado_andar}.fbx
"""
import bpy, sys, os
from mathutils import Matrix, Quaternion, Vector

ROOT = sys.argv[sys.argv.index('--') + 1]
CHR = os.path.join(ROOT, 'assets/models/characters/corazon')
ANI = os.path.join(ROOT, 'assets/models/animations/corazon')
# (clip, accion final, fotograma en el que debe empezar el clip al importar el FBX final). Los clips de animations/
# empiezan en el 1; el andar original arrancaba en t = 1/30 s (fotograma 2) y el disparo en t = -1/24 s (fotograma 0).
# Blender no exporta tiempos negativos: el disparo se exporta desde el fotograma 1 y despues se desplaza el FBX.
CLIPS = [('walk', 'corazon_walk', 2), ('disparo', 'corazon_disparo', 0),
         ('agachado_andar', 'corazon_agachado_andar', 1),
         ('punch_a', 'corazon_punch_a', 1), ('punch_b', 'corazon_punch_b', 1),
         ('gancho', 'corazon_gancho', 1),
         ('pray', 'corazon_pray', 1)]
# Clips cuya fuente de Mixamo vive fuera de animations/corazon/ (ruta relativa a la raiz del worktree).
CLIP_SRC = {'pray': 'assets/models/animations/pray/pray_standing.fbx'}
# Rezar (DESIGN.md 7.7, Glifo): el clip de Mixamo «pray standing» es un bucle con las manos ya juntas, sin el gesto de
# juntarlas. Se construye un clip de 8 fotogramas que lleva al heroe de su pose de reposo (primer fotograma del andar) a la
# pose del rezo: la rotacion en mundo de cada hueso se interpola (slerp) con una rampa suave que cierra las manos en el
# fotograma PRAY_CLOSE_FRAME (0..7) y despues sigue el rezo de la fuente. (fotograma de la fuente, avance 0..1) por fotograma
PRAY_CLOSE_FRAME = 5
PRAY_PLAN = [(1, 0.0), (1, 0.104), (1, 0.352), (1, 0.648), (1, 0.896), (1, 1.0), (8, 1.0), (16, 1.0), (16, 1.0)]   # el 9.o fotograma duplica el ultimo: el lab muestrea i/8 de la duracion, asi cada muestra cae en su clave
# Recorte al tramo util del combo (DESIGN.md 7.2; walkthroughs/arpg-predemo/diseno_juego_final.md 10): fotogramas
# de la fuente a 30 fps, en coordenadas de clave del clip de Mixamo (F0 = clave 1). El clip exportado empieza en el
# primer fotograma del tramo, asi que el lab muestrea solo el golpe y no la pose de reposo de los extremos.
TRIM = {'punch_a': (1, 20),   # F0-F19
        'punch_b': (3, 21),   # F2-F20
        'gancho': (19, 43)}   # F18-F42
# Retoque del andar agachado (procedural, tras el retarget): se baja la pelvis `drop` unidades del esqueleto (el modelo
# mide ~82 u de alto), los pies se quedan donde estaban (IK analitica de pierna con el polo hacia delante, rodillas
# hacia delante) y la espalda/cabeza se enderezan o inclinan: la inclinacion de Spine*, Neck y Head se multiplica por
# `spine`/`head` (1 = la del clip, 0 = erguido). Nivel elegido por el usuario (DESIGN.md 6.9, ronda A/B/C del torso): A2,
# bajada 15, torso mas inclinado que el clip (spine 1,4), con la cabeza compensada para que siga mirando al frente.
# Altura media del sprite 20,8 px frente a 32,3 de pie (64 %). Descartados: a1 (spine 1,0), a3 (spine 1,8), el clip sin retocar (85 %).
CROUCH_LEVELS = {'a2': dict(drop=15.0, spine=1.4, head=-0.6)}
CROUCH_LEVEL = 'a2'      # nivel que sale como corazon_agachado_andar
CLIP_LEVEL = {'corazon_agachado_andar': CROUCH_LEVEL}
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


RETARGET = ('agachado_andar', 'punch_a', 'punch_b', 'gancho', 'pray')   # clips Mixamo con otra orientacion de ejes de hueso: se retargetean por orientacion en mundo


def _rot3(m):
    return m.to_3x3().normalized()


def retarget_action(arm, sa, aname, level=None, pray=None):
    """Copia al esqueleto del modelo (arm) la animacion del esqueleto Mixamo sa, sin tocar ninguno de los dos.

    Los dos tienen los mismos 65 huesos pero otros ejes locales, asi que no se copian las rotaciones locales: por cada
    hueso se toma el giro en mundo respecto a su reposo y se aplica al reposo del modelo. La cadera se escala a la
    altura del modelo y se le quita el avance horizontal (in-place, como walk.fbx)."""
    scene = bpy.context.scene
    act = sa.animation_data.action
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    plan = [pf[0] for pf in PRAY_PLAN] if pray else list(range(f0, f1 + 1))
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
    for f in plan:
        scene.frame_set(f)
        drift.append(Rw @ (sa.pose.bones['mixamorig:Hips'].head - hs.head_local))
    net = drift[-1] - drift[0]
    net.z = 0
    fwd = net.normalized() if net.length > 1e-3 else None
    rest = {b.name: _rot3(b.matrix_local) for b in arm.data.bones}
    rh = {b.name: b.head_local.copy() for b in arm.data.bones}
    P = 'mixamorig:'

    def fk(basis, hips_pos):
        T, pos = {}, {}
        for b in order:
            n = b.name
            if b.parent is None:
                T[n] = rest[n] @ basis[n]
                pos[n] = hips_pos.copy()
            else:
                pn = b.parent.name
                T[n] = T[pn] @ rest[pn].inverted() @ rest[n] @ basis[n]
                pos[n] = pos[pn] + T[pn] @ rest[pn].inverted() @ (rh[n] - rh[pn])
        return T, pos

    def retouch(T0, hips0, cfg):
        """Baja la pelvis, endereza el torso y recoloca las piernas (IK de dos huesos) con los pies en su sitio."""
        basis = {}
        for b in order:
            n = b.name
            basis[n] = (rest[n].inverted() @ T0[n]) if b.parent is None else (
                rest[n].inverted() @ rest[b.parent.name] @ T0[b.parent.name].inverted() @ T0[n])
        _, pos0 = fk(basis, hips0)
        for n, k in (('Spine', cfg['spine']), ('Spine1', cfg['spine']), ('Spine2', cfg['spine']),
                     ('Neck', cfg['head']), ('Head', cfg['head'])):
            ax, ang = basis[P + n].to_quaternion().to_axis_angle()      # k puede pasar de 1 (mas inclinado) o ser < 0
            basis[P + n] = Quaternion(ax, ang * k).to_matrix()
        hips1 = hips0 + Vector((0.0, 0.0, -cfg['drop']))
        T1, pos1 = fk(basis, hips1)
        yax = Vector((0.0, 1.0, 0.0))
        for side in ('Left', 'Right'):
            up, leg, foot = P + side + 'UpLeg', P + side + 'Leg', P + side + 'Foot'
            H, target = pos1[up], pos0[foot]
            l1, l2 = (rh[leg] - rh[up]).length, (rh[foot] - rh[leg]).length
            dv = target - H
            d = min(max(dv.length, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
            u = dv.normalized()
            a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
            h = max(l1 * l1 - a * a, 0.0) ** 0.5
            toe = rh[P + side + 'ToeBase'] - rh[foot]
            toe.z = 0.0
            fwd_now = (T1[P + 'Hips'] @ rest[P + 'Hips'].inverted()) @ toe.normalized()
            pole = fwd_now - u * fwd_now.dot(u)
            pole.normalize()
            K = H + u * a + pole * h
            diff = (T1[up] @ yax).rotation_difference((K - H).normalized()).to_matrix()
            T1[up] = diff @ T1[up]
            T1[leg] = diff @ T1[leg]
            diff2 = (T1[leg] @ yax).rotation_difference((target - K).normalized()).to_matrix()
            T1[leg] = diff2 @ T1[leg]
            for b in order:                       # pie y dedos conservan su orientacion original (suela plana)
                n = b.name
                if n == foot or (b.parent is not None and n.startswith(P + side + 'Toe')) or n == P + side + 'ToeBase':
                    T1[n] = T0[n]
                if n.startswith(P + side + 'Toe_End'):
                    T1[n] = T0[n]
        return T1, hips1

    arm.animation_data_create()
    new_act = bpy.data.actions.new(aname)
    arm.animation_data.action = new_act
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for i, f in enumerate(plan):
        scene.frame_set(f)
        T = {}
        for b in order:
            sb = sa.data.bones[b.name]
            Ps = Rw @ _rot3(sa.pose.bones[b.name].matrix)
            Rs = Rw @ _rot3(sb.matrix_local)
            T[b.name] = (Ps @ Rs.inverted()) @ rest[b.name]
        d = drift[i].copy()
        if fwd is not None:
            d -= fwd * (d.dot(fwd) - drift[0].dot(fwd))
        hips_pos = rh[P + 'Hips'] + d * ratio
        if pray:
            k = PRAY_PLAN[i][1]
            for b in order:
                q0, q1 = pray['T'][b.name].to_quaternion(), T[b.name].to_quaternion()
                if q0.dot(q1) < 0:
                    q1.negate()
                T[b.name] = q0.slerp(q1, k).to_matrix()
            hips_pos = pray['hips'].lerp(hips_pos, k)
        if level:
            T, hips_pos = retouch(T, hips_pos, CROUCH_LEVELS[level])
        for b in order:
            n = b.name
            if b.parent is None:
                basis = rest[n].inverted() @ T[n]
            else:
                basis = rest[n].inverted() @ rest[b.parent.name] @ T[b.parent.name].inverted() @ T[n]
            pb = arm.pose.bones[n]
            kf = i + 1 if pray else f
            pb.rotation_quaternion = basis.to_quaternion()
            pb.keyframe_insert('rotation_quaternion', frame=kf)
            if b.parent is None:
                pb.location = rest[n].inverted() @ (hips_pos - rh[n])
                pb.keyframe_insert('location', frame=kf)
    arm.animation_data.action = None
    new_act.name = aname
    return new_act


def trim_action(act, ta, tb):
    """Borra las claves fuera de [ta, tb] y desplaza las que quedan para que la primera caiga en el fotograma 1."""
    for l in act.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    pts = fc.keyframe_points
                    for i in range(len(pts) - 1, -1, -1):
                        if pts[i].co.x < ta - 0.5 or pts[i].co.x > tb + 0.5:
                            pts.remove(pts[i], fast=True)
                    for kp in fc.keyframe_points:
                        kp.co.x += 1 - ta; kp.handle_left.x += 1 - ta; kp.handle_right.x += 1 - ta
                    fc.update()


ONLY = os.environ.get('BUILD_ONLY')   # p. ej. BUILD_ONLY=pray: solo ese clip
for clip, name, start in CLIPS:
    if ONLY and clip != ONLY:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHR, 'source/corazon.fbx'))
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, CLIP_SRC[clip]) if clip in CLIP_SRC else os.path.join(ANI, clip + '.fbx'))   # fija el fps de la escena al del clip
    fps = scene.render.fps
    new = [o for o in bpy.data.objects if o not in before]
    src_arm = [o for o in new if o.type == 'ARMATURE'][0]
    assert {b.name for b in src_arm.data.bones} == {b.name for b in arm.data.bones}, 'esqueletos distintos'
    pray = None
    if clip == 'pray':
        # pose de reposo del heroe: primer fotograma del andar (mismos huesos y ejes que el modelo: se evalua tal cual)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(ANI, 'walk.fbx'))
        wk = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE'][0]
        scene.frame_set(int(round(wk.animation_data.action.frame_range[0])))
        bpy.context.view_layer.update()
        Rk = _rot3(wk.matrix_world)
        hk = wk.data.bones['mixamorig:Hips']
        pray = {'T': {pb.name: Rk @ _rot3(pb.matrix) for pb in wk.pose.bones},
                'hips': arm.data.bones['mixamorig:Hips'].head_local
                        + (Rk @ (wk.pose.bones['mixamorig:Hips'].head - hk.head_local))
                        * (arm.data.bones['mixamorig:Hips'].head_local.z / (Rk @ hk.head_local).z)}
        for o in [o for o in bpy.data.objects if o not in before]:
            bpy.data.objects.remove(o, do_unlink=True)
        new = [o for o in new if o.name in bpy.data.objects]
    act = retarget_action(arm, src_arm, clip, CLIP_LEVEL.get(name), pray) if clip in RETARGET else src_arm.animation_data.action
    if clip in TRIM:
        trim_action(act, *TRIM[clip])
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    print('TRIM', name, '->', f0, f1)
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

