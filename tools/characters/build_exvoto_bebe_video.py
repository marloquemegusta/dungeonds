"""Clips del Bebe (exvoto_bebe) para los videos de lore (bestiario, 160x160, lab rapido). No van a la ROM.

  assets/sprites/bestiary/exvoto_bebe_walk/    andar con las manos juntas (exvoto_bebe_walk.fbx), 8 fotogramas
  assets/sprites/bestiary/exvoto_bebe_rezar/   bucle de rodillas (exvoto_bebe_pray_kneel.fbx), 16 fotogramas
  assets/sprites/bestiary/exvoto_bebe_gatear/  gateo (exvoto_bebe_crawl.fbx), 32 fotogramas

Los FBX salen de build_exvoto_tier.py (walk/pray; con --crawl-only, el gateo). Misma camara, luz y encuadre que
exvoto_walk; el tamano es el del juego: el Bebe mide lo que dice la proporcion de fitZoom de characters.json de
la rama del ARPG (0.479 el Bebe frente a 0.86 la monja de cera).

Uso: python tools/characters/build_exvoto_bebe_video.py [--only walk|rezar|gatear] [--frames N] [--dirs S,E,N] [--out <dir>]
"""
import argparse, json, os, shutil, subprocess, tempfile
from PIL import Image

from build_exvoto_pray import WALK_EXTENT, WALK_FIT, GROUND, norm_args

BEBE_RATIO = 0.479 / 0.86
FIT = WALK_FIT * BEBE_RATIO
CLIPS = {  # nombre: (fbx, fotogramas, ms por fotograma, ticksPerFrame)
    'walk': ('exvoto_bebe_walk.fbx', 8, 180, 11),
    'rezar': ('exvoto_bebe_pray_kneel.fbx', 16, 120, 5),
    'gatear': ('exvoto_bebe_crawl.fbx', 32, 60, 3),     # 32 x 57 ms = 1,82 s, el ciclo real (55 fotogramas a 30 fps)
}
DIR_FILES = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']


def align(out, dur):
    """Lleva el ancla de suelo de cada direccion a (80, 137), como exvoto_walk, recoloca la sombra y deja solo
    dirs/ + shadows/ + settings.json."""
    st = json.load(open(os.path.join(out, 'settings.json'), encoding='utf-8'))
    for k, d in enumerate(DIR_FILES):
        path = os.path.join(out, 'dirs', d + '.gif')
        if not os.path.exists(path):
            continue
        dx, dy = GROUND[0] - st['anchor'][0], GROUND[1] - st['dirGroundAnchors'][k]
        im = Image.open(path)
        frames = []
        for i in range(im.n_frames):
            im.seek(i)
            fr = im.convert('RGB')
            canvas = Image.new('RGB', fr.size, fr.getpixel((0, 0)))
            canvas.paste(fr, (dx, dy))
            frames.append(canvas.convert('P', palette=Image.ADAPTIVE, colors=256))
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=dur, loop=0, disposal=1)
        sp = os.path.join(out, 'shadows', d + '.png')
        if os.path.exists(sp):
            sh = Image.open(sp).convert('RGBA')
            canvas = Image.new('RGBA', sh.size, (0, 0, 0, 0))
            # la sombra del lab ya va referida a su propia ancla (cae en el centro del lienzo 320x320): en
            # horizontal no se mueve y en vertical solo lo que difiera esa ancla de la linea de suelo
            canvas.paste(sh, (0, st['anchor'][1] - st['dirGroundAnchors'][k]))
            canvas.save(sp)
    st['anchor'] = [GROUND[0], GROUND[1]]
    st['dirGroundAnchors'] = [GROUND[1]] * 8
    st.pop('dirBounds', None)
    st.pop('shadowBounds', None)
    with open(os.path.join(out, 'settings.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump(st, f, indent=2)
        f.write('\n')
    for extra in ('frames', 'spritesheet.png', 'shadow.png', 'collage.gif', 'nds_shadow_anchor.h', 'README.md'):
        p = os.path.join(out, extra)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.getcwd())
    ap.add_argument('--only', choices=list(CLIPS))
    ap.add_argument('--frames', type=int)
    ap.add_argument('--dirs')
    ap.add_argument('--out', help='carpeta de salida alternativa (pruebas)')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    tpl = json.load(open(os.path.join(root, 'assets/sprites/bestiary/exvoto_walk/settings.json'), encoding='utf-8'))
    for name, (fbx, nframes, ms, ticks) in CLIPS.items():
        if a.only and a.only != name:
            continue
        t = dict(tpl)
        t['ticksPerFrame'] = ticks
        t['fitZoom'] = FIT
        t.pop('animation', None)
        tmp = os.path.join(tempfile.gettempdir(), 'exvoto_bebe_%s_tpl.json' % name)
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            json.dump(t, f)
        out = os.path.join(a.out or os.path.join(root, 'assets/sprites/bestiary'), 'exvoto_bebe_%s' % name)
        cmd = ['node', os.path.join(root, 'tools/lab/fast/export_character_fast.cjs'),
               os.path.join(root, 'assets/models/characters/exvoto_bebe', fbx), out, '--template', tmp,
               '--resolution', '160', '--frames', str(a.frames or nframes), '--fitZoom', repr(FIT),
               '--fitExtent', repr(WALK_EXTENT), '--legibility', 'c2', '--noCHeader'] + norm_args(root)
        if a.dirs:
            cmd += ['--dirs', a.dirs]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(name, [l for l in (r.stdout + r.stderr).splitlines() if l.startswith(('FIT ', 'WARNING'))])
        if r.returncode:
            raise SystemExit(r.stderr)
        align(out, ms)


if __name__ == '__main__':
    main()
