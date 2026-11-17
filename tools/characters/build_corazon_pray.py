"""Corazon Abierto (Elias) rezando y levantandose, para los videos de lore (bestiario, 8 direcciones, 160x160).

Genera, con el MISMO pipeline y ajustes que corazon_walk (plantilla assets/sprites/bestiary/corazon_walk/settings.json):
  assets/sprites/bestiary/corazon_rezar/dirs/      bucle de rodillas (pray_kneeling.fbx), 16 fotogramas
  assets/sprites/bestiary/corazon_levantarse/dirs/ de rodillas a de pie, una vez (pray_kneel_to_stand.fbx), 24 fotogramas

Uso (desde la raiz del worktree, Python normal; llama a Blender y a Node/Playwright headless):
  python tools/characters/build_corazon_pray.py [--root <raiz>] [--only rezar|levantarse] [--frames N]
Pasos: (1) Blender -b -P este mismo script -- <raiz> : retarget por delta de rotacion de las animaciones Mixamo
(Y-up, 65 huesos mixamorig) sobre el rig del Corazon (source/corazon.fbx), escalando la cadera por la altura de cadera
(como build_ojo.py), y exporta corazon_rezar.fbx / corazon_levantarse.fbx en assets/models/characters/corazon/;
(2) tools/lab/export_character_headless.cjs con la plantilla de corazon_walk (misma camara, escala, luz y
altura de pies) y la duracion por fotograma (animTicks, 26 ms por tick) acorde al clip.
Los FBX intermedios pesan ~6 MB cada uno y no hay que versionarlos.
"""
import os, sys

MS = {'rezar': 130, 'levantarse': 290}   # ms por fotograma del GIF (el bucle de rezar ~2,1 s; levantarse ~7 s)
WALK_EXTENT = 1.8619977081714065   # extent de encuadre de corazon_walk (lo imprime export_character_headless.cjs como FIT)

CLIPS = {
    # nombre: (fbx de animacion, fotogramas por direccion, ticks por fotograma, bucle)
    'rezar': ('pray_kneeling.fbx', 16, 5, True),
    'levantarse': ('pray_kneel_to_stand.fbx', 24, 11, False),
}

try:
    import bpy  # noqa
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False


def blender_main(root):
    import math
    from mathutils import Vector, Matrix
    P = 'mixamorig:'
    main = 'C:/codexlocal/dungeonds'

    def find(rel):
        p = os.path.join(root, rel)
        return p if os.path.exists(p) else os.path.join(main, rel)

    char_fbx = find('assets/models/characters/corazon/source/corazon.fbx')
    out_dir = os.path.join(root, 'assets/models/characters/corazon')
    only = os.environ.get('PRAY_ONLY')
    for name, (anim, nframes, _t, loop) in CLIPS.items():
        if only and only != name:
            continue
        nframes = int(os.environ.get('PRAY_FRAMES', nframes))
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=char_fbx)
        arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
        meshes = [o for o in bpy.data.objects if o.type == 'MESH']
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=find('assets/models/animations/pray/' + anim))
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
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
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
                    head = tb.head_local + MT3.inverted() @ (d_w * K * 100.0)
                else:
                    head = PB[P + n].matrix.translation.copy()
                PB[P + n].matrix = Matrix.Translation(head) @ R_des.to_4x4()
                update()
            return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in PB}

        poses = []
        for i in range(nframes + 1):
            if loop:
                t = i / nframes                            # el ultimo clave repite el primero (bucle)
            else:
                t = min(i, nframes - 1) / (nframes - 1)    # el fotograma N-1 es la pose final; el cierre la mantiene
            poses.append(sample(f0 + t * (f1 - f0)))
        if loop:
            poses[-1] = poses[0]
        action = bpy.data.actions.new(name)
        arm.animation_data.action = action
        for i, d in enumerate(poses):
            for pb in PB:
                l, q, s = d[pb.name]
                pb.location = l; pb.rotation_quaternion = q; pb.scale = s
                pb.keyframe_insert('location', frame=i)
                pb.keyframe_insert('rotation_quaternion', frame=i)
                pb.keyframe_insert('scale', frame=i)
        action.frame_range = (0, len(poses) - 1)
        scene.name = name; scene.render.fps = 24
        scene.frame_start = 0; scene.frame_end = len(poses) - 1
        bpy.data.objects.remove(src, do_unlink=True)
        bpy.ops.object.select_all(action='DESELECT')
        for o in [arm] + meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = arm
        path = os.path.join(out_dir, 'corazon_%s.fbx' % name)
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
    ap.add_argument('--only', choices=list(CLIPS))
    ap.add_argument('--frames', type=int)
    ap.add_argument('--skip-blender', action='store_true')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
    env = dict(os.environ)
    if a.only: env['PRAY_ONLY'] = a.only
    if a.frames: env['PRAY_FRAMES'] = str(a.frames)
    if not a.skip_blender:
        subprocess.run([blender, '-b', '-P', os.path.abspath(__file__), '--', root], check=True, env=env)
    tpl = json.load(open(os.path.join(root, 'assets/sprites/bestiary/corazon_walk/settings.json'), encoding='utf-8'))
    for name, (_a, nframes, ticks, _l) in CLIPS.items():
        if a.only and a.only != name:
            continue
        nframes = a.frames or nframes
        t = dict(tpl); t['ticksPerFrame'] = ticks; t['animation'] = name
        tmp = os.path.join(tempfile.gettempdir(), 'corazon_%s_tpl.json' % name)
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            json.dump(t, f)
        fbx = os.path.join(root, 'assets/models/characters/corazon/corazon_%s.fbx' % name)
        out = os.path.join(root, 'assets/sprites/bestiary/corazon_%s' % name)
        fit = 1.0
        for attempt in range(2):
            t['fitZoom'] = fit
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                json.dump(t, f)
            r = subprocess.run(['node', os.path.join(root, 'tools/lab/export_character_headless.cjs'), fbx, out,
                                '--template', tmp, '--resolution', '160', '--frames', str(nframes), '--fitZoom', str(fit),
                                '--anim', name, '--legibility', 'c2'], check=True, capture_output=True, text=True)
            extent = float([l for l in r.stdout.splitlines() if l.startswith('FIT ')][-1].split('"extent":')[1].split(',')[0])
            want = extent / WALK_EXTENT           # misma escala px/metro que corazon_walk (half = extent / fitZoom)
            print('%s: extent %.4f, fitZoom %.4f -> %.4f' % (name, extent, fit, want))
            if abs(want - fit) < 0.004:
                break
            fit = want
        align(out, MS[name])


def align(out, dur):
    """Mueve cada fotograma para que el ancla de suelo quede en (80, 142), como corazon_walk, y deja solo dirs/ + settings.json."""
    import glob, json, shutil
    from PIL import Image
    st = json.load(open(os.path.join(out, 'settings.json'), encoding='utf-8'))
    dirs = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']
    for k, d in enumerate(dirs):
        ax, ay = st['anchor'][0], st['dirGroundAnchors'][k]
        dx, dy = 80 - ax, 142 - ay
        path = os.path.join(out, 'dirs', d + '.gif')
        im = Image.open(path)
        frames = []
        for i in range(im.n_frames):
            im.seek(i); fr = im.convert('RGB')
            bg = fr.getpixel((0, 0))
            canvas = Image.new('RGB', fr.size, bg); canvas.paste(fr, (dx, dy))
            frames.append(canvas.convert('P', palette=Image.ADAPTIVE, colors=256))
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=dur, loop=im.info.get('loop', 0), disposal=1)
    st['anchor'] = [80, 142]; st['dirGroundAnchors'] = [142] * 8
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
