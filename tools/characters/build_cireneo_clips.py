"""Clips del Cireneo SIN cruz (run, run_mirar, reaccion, triste) para el bestiario, 8 direcciones, 160x160.

Mismo pipeline que build_corazon_pray.py (retarget por delta de rotacion sobre el rig del Cireneo, cadera escalada
por altura, exportador headless, misma camara y escala que cireneo_sincruz_walk), pero el clip, el nombre de salida,
el numero de fotogramas, el tiempo por fotograma y el bucle son variables de entorno. Este archivo es nuevo: no
modifica build_corazon_pray.py ni build_cireneo_v2.py.

Variables (todas opcionales salvo CLIP_FBX y CLIP_NAME):
  CLIP_FBX      clip Mixamo, relativo a la raiz (p. ej. assets/models/animations/walk/fast_run.fbx)
  CLIP_NAME     nombre de salida: run | run_mirar | reaccion | triste  -> cireneo_sincruz_<CLIP_NAME>
  CLIP_FRAMES   fotogramas por direccion (default 16)
  CLIP_LOOP     1 = bucle (default), 0 = una vez (se queda en la ultima pose)
  CLIP_TICKS    ticksPerFrame del exportador (default 1; 26 ms por tick)
  CLIP_INPLACE  1 = anula el avance horizontal de la cadera (default 1); la altura se conserva
  CLIP_F0 / CLIP_F1  rango de fotogramas Mixamo a muestrear (default: el rango completo del clip)
  CLIP_SRC      FBX del rig (default cuerpo del Cireneo sin cruz)
  CLIP_FITZOOM  fitZoom (default 0.9), CLIP_EXTENT (default 1.872183561426501), CLIP_GROUND_Y (default 133)

Uso (desde la raiz del worktree, Python normal; llama a Blender y a Node/Playwright headless):
  CLIP_FBX=assets/models/animations/walk/fast_run.fbx CLIP_NAME=run CLIP_FRAMES=16 CLIP_TICKS=1 \
    python tools/characters/build_cireneo_clips.py --root <raiz>
Pasos: (1) Blender -b -P este mismo script -- <raiz> exporta assets/models/characters/cireneo/cireneo_sincruz_<NAME>.fbx;
(2) tools/lab/export_character_headless.cjs genera assets/sprites/bestiary/cireneo_sincruz_<NAME>/ con la plantilla de
cireneo_walk; (3) align deja el suelo en la fila GROUND_Y y limpia los archivos intermedios.
"""
import os, sys

CHAR_DEFAULT_SRC = 'assets/models/characters/cireneo/source/tripo_convert_cd715dbe-128f-4b59-b47f-5e36cc9cd8ac.fbx'
ENV = os.environ
CLIP_FBX = ENV.get('CLIP_FBX', '')
NAME = ENV.get('CLIP_NAME', '')
PREFIX = 'cireneo_sincruz'
FRAMES = int(ENV.get('CLIP_FRAMES', '16'))
LOOP = ENV.get('CLIP_LOOP', '1') == '1'
TICKS = int(ENV.get('CLIP_TICKS', '1'))
INPLACE = ENV.get('CLIP_INPLACE', '1') == '1'
F0_ENV = ENV.get('CLIP_F0')
F1_ENV = ENV.get('CLIP_F1')
SRC = ENV.get('CLIP_SRC', CHAR_DEFAULT_SRC)
FITZOOM = float(ENV.get('CLIP_FITZOOM', '0.9'))
EXTENT = float(ENV.get('CLIP_EXTENT', '1.872183561426501'))
GROUND_Y = int(ENV.get('CLIP_GROUND_Y', '133'))
TEMPLATE = 'assets/sprites/bestiary/cireneo_walk/settings.json'
MS_PER_TICK = 26   # duracion de cada tick del exportador (ver build_corazon_pray.py)

try:
    import bpy  # noqa
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False


def blender_main(root):
    import math
    from mathutils import Vector, Matrix
    P = 'mixamorig:'
    char_fbx = os.path.join(root, SRC)
    anim_fbx = os.path.join(root, CLIP_FBX)
    out_dir = os.path.join(root, 'assets/models/characters/cireneo')
    scene = None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=char_fbx)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=anim_fbx)
    new = [o for o in bpy.data.objects if o not in before]
    src = [o for o in new if o.type == 'ARMATURE'][0]
    for o in new:                      # el cuerpo (Beta) del FBX de Mixamo sobra
        if o.type == 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    scene = bpy.context.scene
    PB, SPB = arm.pose.bones, src.pose.bones
    MS3 = src.matrix_world.to_3x3().normalized()
    MT3 = arm.matrix_world.to_3x3().normalized()
    act = src.animation_data.action
    f0 = int(round(act.frame_range[0])) if F0_ENV is None else int(F0_ENV)
    f1 = int(round(act.frame_range[1])) if F1_ENV is None else int(F1_ENV)
    print('CLIP range %d..%d frames %d' % (f0, f1, FRAMES))
    arm.animation_data_create(); arm.animation_data.action = None

    def update():
        bpy.context.view_layer.update()

    scene.frame_set(f0); update()
    K = (arm.matrix_world @ arm.data.bones[P + 'Hips'].head_local).z / (src.matrix_world @ src.data.bones[P + 'Hips'].head_local).z
    ORDER = [b.name[len(P):] for b in arm.data.bones]   # padres antes que hijos

    def sample(x):
        fi = int(math.floor(x)); scene.frame_set(fi, subframe=x - fi); update()
        for pb in PB:
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        update()
        for n in ORDER:
            sp = SPB.get(P + n); sb = src.data.bones.get(P + n); tb = arm.data.bones[P + n]
            if sp is None:
                continue
            rest3 = tb.matrix_local.to_3x3().normalized()
            R_delta = sp.matrix.to_3x3().normalized() @ sb.matrix_local.to_3x3().normalized().inverted()
            R_world = MS3 @ R_delta @ MS3.inverted()
            R_des = (MT3.inverted() @ R_world @ MT3) @ rest3
            if n == 'Hips':
                # desplazamiento de la cadera respecto a su reposo, en mundo (m), escalado a la altura del destino
                d_w = (src.matrix_world @ sp.head) - (src.matrix_world @ sb.head_local)
                if INPLACE:
                    d_w = Vector((0.0, 0.0, d_w.z))    # sin avance de raiz: solo sube y baja
                head = tb.head_local + MT3.inverted() @ (d_w * K * 100.0)
            else:
                head = PB[P + n].matrix.translation.copy()
            PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
            update()
        return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}

    poses = []
    for i in range(FRAMES + 1):
        if LOOP:
            t = i / FRAMES                              # el ultimo clave repite el primero (bucle)
        else:
            t = min(i, FRAMES - 1) / (FRAMES - 1)       # el fotograma N-1 es la pose final; el cierre la mantiene
        poses.append(sample(f0 + t * (f1 - f0)))
    if LOOP:
        poses[-1] = poses[0]
    # diagnostico de cierre del bucle: diferencia maxima de rotacion entre la primera y la ultima muestra reales
    if LOOP:
        worst = 0.0
        for n in poses[0]:
            q0 = poses[0][n][1]; q1 = poses[FRAMES - 1][n][1]
            worst = max(worst, q0.rotation_difference(q1).angle)
        print('CLOSE max rotation gap first vs last-real (deg) %.1f' % math.degrees(worst))
    action = bpy.data.actions.new(NAME)
    arm.animation_data.action = action
    for i, d in enumerate(poses):
        for pb in PB:
            l, q, s = d[pb.name]
            pb.location = l; pb.rotation_quaternion = q; pb.scale = s
            pb.keyframe_insert('location', frame=i)
            pb.keyframe_insert('rotation_quaternion', frame=i)
            pb.keyframe_insert('scale', frame=i)
    action.frame_range = (0, len(poses) - 1)
    scene.name = NAME; scene.render.fps = 24
    scene.frame_start = 0; scene.frame_end = len(poses) - 1
    bpy.data.objects.remove(src, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [arm] + meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(out_dir, '%s_%s.fbx' % (PREFIX, NAME))
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'}, use_mesh_modifiers=False,
        add_leaf_bones=False, path_mode='COPY', embed_textures=True, bake_anim=True, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0, mesh_smooth_type='FACE')
    print('EXPORTED', path, 'K=%.4f' % K)


def launcher():
    import argparse, json, subprocess, tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.getcwd())
    ap.add_argument('--skip-blender', action='store_true')
    a = ap.parse_args()
    if not NAME or not CLIP_FBX:
        raise SystemExit('faltan CLIP_FBX y CLIP_NAME')
    root = os.path.abspath(a.root)
    blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
    if not a.skip_blender:
        subprocess.run([blender, '-b', '-P', os.path.abspath(__file__), '--', root], check=True, env=dict(os.environ))
    tpl = json.load(open(os.path.join(root, TEMPLATE), encoding='utf-8'))
    ns_path = os.path.join(root, 'assets/sprites/characters/cireneo/settings.json')
    ns = json.load(open(ns_path, encoding='utf-8')).get('normScale')
    if not ns:
        raise SystemExit('falta normScale en %s' % ns_path)
    t = dict(tpl); t['ticksPerFrame'] = TICKS; t['animation'] = NAME; t['fitZoom'] = FITZOOM
    tmp = os.path.join(tempfile.gettempdir(), '%s_%s_tpl.json' % (PREFIX, NAME))
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        json.dump(t, f)
    fbx = os.path.join(root, 'assets/models/characters/cireneo', '%s_%s.fbx' % (PREFIX, NAME))
    out = os.path.join(root, 'assets/sprites/bestiary/%s_%s' % (PREFIX, NAME))
    r = subprocess.run(['node', os.path.join(root, 'tools/lab/export_character_headless.cjs'), fbx, out,
                        '--template', tmp, '--resolution', '160', '--frames', str(FRAMES), '--fitZoom', repr(FITZOOM),
                        '--fitExtent', repr(EXTENT), '--anim', NAME, '--legibility', 'c2',
                        '--normScale', repr(ns)], check=True, capture_output=True, text=True)
    print(NAME, [l for l in r.stdout.splitlines() if l.startswith(('FIT ', 'WARNING', 'animations'))])
    align(out, MS_PER_TICK * TICKS)


def align(out, dur):
    """Mueve cada fotograma para que el ancla de suelo quede en (80, GROUND_Y), como cireneo_sincruz_walk, y deja solo dirs/ + settings.json."""
    import json, shutil
    from PIL import Image
    st = json.load(open(os.path.join(out, 'settings.json'), encoding='utf-8'))
    dirs = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']
    for k, d in enumerate(dirs):
        ax, ay = st['anchor'][0], st['dirGroundAnchors'][k]
        dx, dy = 80 - ax, GROUND_Y - ay
        path = os.path.join(out, 'dirs', d + '.gif')
        im = Image.open(path)
        frames = []
        for i in range(im.n_frames):
            im.seek(i); fr = im.convert('RGB')
            bg = fr.getpixel((0, 0))
            canvas = Image.new('RGB', fr.size, bg); canvas.paste(fr, (dx, dy))
            frames.append(canvas.convert('P', palette=Image.ADAPTIVE, colors=256))
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=dur, loop=im.info.get('loop', 0), disposal=1)
    st['anchor'] = [80, GROUND_Y]; st['dirGroundAnchors'] = [GROUND_Y] * 8
    st.pop('dirBounds', None); st.pop('shadowBounds', None)
    with open(os.path.join(out, 'settings.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump(st, f, indent=2); f.write('\n')
    for extra in ('frames', 'shadows', 'spritesheet.png', 'shadow.png', 'collage.gif', 'nds_shadow_anchor.h', 'README.md'):
        p = os.path.join(out, extra)
        if os.path.isdir(p): shutil.rmtree(p)
        elif os.path.exists(p): os.remove(p)


if __name__ == '__main__':
    if IN_BLENDER:
        blender_main(sys.argv[sys.argv.index('--') + 1])
    else:
        launcher()
