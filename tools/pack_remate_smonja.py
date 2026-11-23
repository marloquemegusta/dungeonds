"""Empaqueta el remate de la Super Monja (arana) desde su paquete del lab rapido.

Escribe nitrofiles/remate/smonja_d0..d7.bin y AÑADE (o actualiza) el tipo REMATE_KIND_SMONJA en
source/remate_sprites.c e include/remate_sprites.h sin tocar los otros tipos: tools/generate_remate_sprites.py solo
conoce 3 de los 5 tipos consolidados, asi que no se puede usar para regenerar las tablas completas.

Uso: python tools/pack_remate_smonja.py
Entrada: SMONJA_LAB_OUT (por defecto walkthroughs/remate-smonja/assets/lab_out) y SMONJA_GLB (scratch_lab/glb_smonja).
"""
import glob
import json
import os
import re
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_remate_sprites as G

WT = G.WT
LAB = os.environ.get('SMONJA_LAB_OUT', os.path.join(WT, 'walkthroughs', 'remate-smonja', 'assets', 'lab_out'))
GLB = os.environ.get('SMONJA_GLB', os.path.join(WT, 'scratch_lab', 'glb_smonja'))
FRAMES = 36
TICKS = 4
NAME = 'smonja'
CFG = {
    'name': NAME, 'ppm': 38.0, 'has_remnant': 1, 'reuse_pix_from': None, 'frames': FRAMES, 'ticks': TICKS,
    'legacy': False, 'single_layer': True, 'dup_frame0': False, 'shadow_share': True,
    'shadow_canvas': 128, 'shadow_max': 80, 'lab_out': LAB, 'glb_dir': GLB,
}
C_PATH = os.path.join(WT, 'source', 'remate_sprites.c')
H_PATH = os.path.join(WT, 'include', 'remate_sprites.h')


def read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def write(p, t):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(t)


def split_blocks(txt, start_marker):
    """Devuelve (indice inicio del cuerpo, indice del '};' final) del array que empieza en start_marker."""
    i = txt.index(start_marker)
    j = txt.index('{\n', i) + 2
    k = txt.index('\n};', j)
    return j, k + 1


def main():
    with open(os.path.join(LAB, 'settings.json')) as f:
        settings = json.load(f)
    atlas = Image.open(os.path.join(LAB, 'shadow.png')).convert('RGBA')
    cw, ch = map(int, settings['frameSize'].split('x'))
    assert int(settings['framesPerDirection']) == FRAMES + 1
    feet = G.hero_feet_by_frame(CFG)
    bias = (CFG['shadow_canvas'] - G.SH_CANVAS) // 2
    d_list, depth_list, off_list = [], [], []
    for d in range(G.N_DIRS):
        data, depth, hero_off = G.pack_dir_bin(CFG, settings, atlas, d, feet)
        with open(os.path.join(G.NITRO_DIR, '%s_d%d.bin' % (NAME, d)), 'wb') as f:
            f.write(data)
        _, _, ax, ay, edx, edy, lab_ax, lab_ay = G.dir_geometry(CFG, settings, d)
        d_list.append((ax, ay, edx, edy, (lab_ax - ax) - bias, (lab_ay - ay) - bias))
        depth_list.append([v for pair in depth for v in pair])
        off_list.append([v for pair in hero_off for v in pair])
        print('d%d bin=%d B anchor=(%d,%d) enemy=(%d,%d)' % (d, len(data), ax, ay, edx, edy))

    mf = G.MAX_FRAMES = 38

    def rows_depth(lst):
        out = ['    {\n']
        for row in lst:
            row = list(row) + [0] * (mf * 2 - len(row))
            out.append('        { %s },\n' % ', '.join('{%d, %d}' % (row[i], row[i + 1]) for i in range(0, mf * 2, 2)))
        out.append('    }, /* %s */\n' % NAME)
        return ''.join(out)

    c = read(C_PATH)
    # fila de RemateKindInfo
    if NAME in c:
        raise SystemExit('el tipo %s ya esta en remate_sprites.c: revertir antes de re-empaquetar' % NAME)
    j, k = split_blocks(c, 'g_remate_kind_info')
    c = c[:k] + '    { %d, %d, 1, %d, %d, %d }, /* %s */\n' % (cw, ch, FRAMES, FRAMES, TICKS, NAME) + c[k:]
    j, k = split_blocks(c, 'g_remate_dir_info')
    blk = '    {\n' + ''.join('        { %d, %d, %d, %d, %d, %d },\n' % t for t in d_list) + '    }, /* %s */\n' % NAME
    c = c[:k] + blk + c[k:]
    j, k = split_blocks(c, 'g_remate_depth')
    c = c[:k] + rows_depth(depth_list) + c[k:]
    j, k = split_blocks(c, 'g_remate_hero_off')
    c = c[:k] + rows_depth(off_list) + c[k:]
    write(C_PATH, c)

    # cabecera: nuevo tipo y buffers de streaming recalculados sobre todos los bins existentes
    h = read(H_PATH)
    n = int(re.search(r'#define REMATE_NUM_KINDS\s+(\d+)', h).group(1))
    h = re.sub(r'(#define REMATE_NUM_KINDS\s+)\d+', lambda m: m.group(1) + str(n + 1), h)
    h = h.replace('#define REMATE_NUM_KINDS', '#define REMATE_KIND_SMONJA    %d\n#define REMATE_NUM_KINDS' % n, 1)
    frames_by_kind = {'exvoto': 12, 'cireneo': 12, 'ojo': 38, 'monaguillo': 12, 'exvoto_bebe': 12, NAME: FRAMES}
    pix = runs = mask = hdr = 0
    for kind, nf in frames_by_kind.items():
        for d in range(G.N_DIRS):
            a, b, m_, hh = G.bin_chunks(os.path.join(G.NITRO_DIR, '%s_d%d.bin' % (kind, d)), nf)
            pix, runs, mask, hdr = max(pix, a), max(runs, b), max(mask, m_), max(hdr, hh)
    rk = lambda v: (v + 1023) & ~1023
    for key, val in (('HEADER', hdr), ('PIX', pix), ('RUN', runs), ('MASK', mask)):
        h = re.sub(r'(#define REMATE_%s_BYTES\s+)\d+' % key, lambda m: m.group(1) + str(rk(val)), h)
    write(H_PATH, h)
    print('buffers hdr=%d pix=%d runs=%d mask=%d  (raw %d %d %d %d)' % (rk(hdr), rk(pix), rk(runs), rk(mask), hdr, pix, runs, mask))


if __name__ == '__main__':
    main()
