"""Exvoto (monja de cera) rezando y levantandose, para los videos de lore (bestiario, 8 direcciones, 160x160).

Mismo pipeline que build_corazon_pray.py, sin el paso de Blender: los FBX ya los dejo build_exvoto.py en
assets/models/characters/exvoto/ (solo en el repo principal, no versionados). Plantilla: exvoto_walk/settings.json.
  assets/sprites/bestiary/exvoto_rezar/dirs/       bucle de rodillas (exvoto_pray_kneel.fbx), 16 fotogramas
  assets/sprites/bestiary/exvoto_levantarse/dirs/  de rodillas a de pie, una vez (exvoto_stand_up.fbx), 24 fotogramas

Uso: python tools/characters/build_exvoto_pray.py [--root <raiz>] [--only rezar|levantarse] [--frames N]
"""
import os, sys

MS = {'rezar': 130, 'levantarse': 290}
WALK_EXTENT = 2.0391720399643707   # extent de encuadre de exvoto_walk (FIT del exportador)
WALK_FIT = 0.96                    # fitZoom de exvoto_walk: half = extent / fitZoom
SCALE_FIX = 0.84                   # medido: con la misma escala nominal, rezar/levantarse salian ~1,15x mas grandes que el andar (cabeza y altura de pie)
GROUND = (80, 137)                 # ancla de suelo de exvoto_walk

CLIPS = {
    'rezar': ('exvoto_pray_kneel.fbx', 16, 5, True),
    'levantarse': ('exvoto_stand_up.fbx', 24, 11, False),
}


def launcher():
    import argparse, json, subprocess, tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.getcwd())
    ap.add_argument('--only', choices=list(CLIPS))
    ap.add_argument('--frames', type=int)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    main = 'C:/codexlocal/dungeonds'
    tpl = json.load(open(os.path.join(root, 'assets/sprites/bestiary/exvoto_walk/settings.json'), encoding='utf-8'))
    for name, (fbxname, nframes, ticks, _l) in CLIPS.items():
        if a.only and a.only != name:
            continue
        nframes = a.frames or nframes
        t = dict(tpl); t['ticksPerFrame'] = ticks; t.pop('animation', None)
        tmp = os.path.join(tempfile.gettempdir(), 'exvoto_%s_tpl.json' % name)
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            json.dump(t, f)
        fbx = os.path.join(root, 'assets/models/characters/exvoto', fbxname)
        if not os.path.exists(fbx): fbx = os.path.join(main, 'assets/models/characters/exvoto', fbxname)
        out = os.path.join(root, 'assets/sprites/bestiary/exvoto_%s' % name)
        fit = 1.0
        for attempt in range(2):
            t['fitZoom'] = fit
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                json.dump(t, f)
            r = subprocess.run(['node', os.path.join(root, 'tools/lab/export_character_headless.cjs'), fbx, out,
                                '--template', tmp, '--resolution', '160', '--frames', str(nframes), '--fitZoom', str(fit),
                                '--legibility', 'c2'], check=True, capture_output=True, text=True)
            extent = float([l for l in r.stdout.splitlines() if l.startswith('FIT ')][-1].split('"extent":')[1].split(',')[0])
            want = extent / WALK_EXTENT * WALK_FIT * SCALE_FIX           # misma escala px/metro que exvoto_walk (half = extent / fitZoom)
            print('%s: extent %.4f, fitZoom %.4f -> %.4f' % (name, extent, fit, want))
            if abs(want - fit) < 0.004:
                break
            fit = want
        align(out, MS[name])


def align(out, dur):
    """Mueve cada fotograma para que el ancla de suelo quede en (80, 137), como exvoto_walk, y deja solo dirs/ + settings.json."""
    import glob, json, shutil
    from PIL import Image
    st = json.load(open(os.path.join(out, 'settings.json'), encoding='utf-8'))
    dirs = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']
    for k, d in enumerate(dirs):
        ax, ay = st['anchor'][0], st['dirGroundAnchors'][k]
        dx, dy = GROUND[0] - ax, GROUND[1] - ay
        path = os.path.join(out, 'dirs', d + '.gif')
        im = Image.open(path)
        frames = []
        for i in range(im.n_frames):
            im.seek(i); fr = im.convert('RGB')
            bg = fr.getpixel((0, 0))
            canvas = Image.new('RGB', fr.size, bg); canvas.paste(fr, (dx, dy))
            frames.append(canvas.convert('P', palette=Image.ADAPTIVE, colors=256))
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=dur, loop=im.info.get('loop', 0), disposal=1)
    st['anchor'] = [80, 137]; st['dirGroundAnchors'] = [137] * 8
    st.pop('dirBounds', None); st.pop('shadowBounds', None)
    with open(os.path.join(out, 'settings.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump(st, f, indent=2); f.write('\n')
    for extra in ('frames', 'shadows', 'spritesheet.png', 'shadow.png', 'collage.gif', 'nds_shadow_anchor.h', 'README.md'):
        p = os.path.join(out, extra)
        if os.path.isdir(p): shutil.rmtree(p)
        elif os.path.exists(p): os.remove(p)


if __name__ == '__main__':
    launcher()
