"""Genera source/remate_sprites.c y include/remate_sprites.h: las animaciones combinadas
del remate (glory kill) del Corazon Abierto sobre el Exvoto y sobre el Cireneo.

Entradas:
  - Exvoto A: walkthroughs/remate-exvoto/assets/ronda2/exvoto_A/f00.png ... f11.png (64x64)
  - Cireneo A: walkthroughs/remate-exvoto/assets/ronda2/cireneo_A/f00.png ... f11.png (80x80)

Optimizacion de memoria EWRAM para encajar holgadamente en el limite estricto de 3.5 MB de la DS:
  - Sombras: las mascaras de 4 bpp se comparten cada 2 fotogramas (la sombra varia suavemente a 4 ticks/frame).
  - Cireneo: los fotogramas finales 10 y 11 (cruz ya clavada) reutilizan los pixeles del fotograma 9.
"""
import os
import sys
from PIL import Image

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KINDS = [
    {
        'name': 'exvoto',
        'dir': os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', 'ronda2', 'exvoto_A'),
        'cell_w': 64,
        'cell_h': 64,
        'anchor_x': 32,
        'anchor_y': 42,
        'enemy_dx': 6,
        'enemy_dy': 4,
        'shadow_cx': 32,
        'shadow_cy': 42,
        'has_remnant': 1,
        'opaque_a': 96,
        'shadow_min_a': 4,
        'shadow_max_a': 95,
        'reuse_pix_from': None,
    },
    {
        'name': 'cireneo',
        'dir': os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', 'ronda2', 'cireneo_A'),
        'cell_w': 80,
        'cell_h': 80,
        'anchor_x': 19,
        'anchor_y': 46,
        'enemy_dx': 26,
        'enemy_dy': 8,
        'shadow_cx': 40,
        'shadow_cy': 45,
        'has_remnant': 0,
        'opaque_a': 180,
        'shadow_min_a': 4,
        'shadow_max_a': 150,
        'reuse_pix_from': {10: 9, 11: 9},
    },
]

N_FRAMES = 12
SH_CANVAS = 80


def load_frame(k_dir, i, cw, ch):
    p = os.path.join(k_dir, 'f%02d.png' % i)
    im = Image.open(p).convert('RGBA')
    assert im.size == (cw, ch), (im.size, (cw, ch))
    return im


def split_frame(im, mirror, cfg):
    cw, ch = cfg['cell_w'], cfg['cell_h']
    opa_a = cfg['opaque_a']
    sh_min = cfg['shadow_min_a']
    sh_max = cfg['shadow_max_a']
    spr = [[0] * (cw + 1) for _ in range(ch)]
    sh = set()

    for y in range(ch):
        for x in range(cw):
            r, g, b, a = im.getpixel((x, y))
            xx = (cw - x) if mirror else x
            if a >= opa_a:
                spr[y][xx] = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) | 0x8000
            elif sh_min <= a <= sh_max:
                sh.add((xx, y))
    return spr, sh


def components(spr, cw, ch):
    w = cw + 1
    seen = set()
    out = []
    for y in range(ch):
        for x in range(w):
            if not spr[y][x] or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            comp = []
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < ch and spr[ny][nx] and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
            out.append(comp)
    return out


def encode_sprite(spr, cw, ch, pix, runs):
    w = cw + 1
    xs = [x for y in range(ch) for x in range(w) if spr[y][x]]
    ys = [y for y in range(ch) for x in range(w) if spr[y][x]]
    pix_off, run_off = len(pix), len(runs)
    if not xs:
        return (0, 0, 0, 0), pix_off, run_off
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    for y in range(y0, y1 + 1):
        row = spr[y][x0:x1 + 1]
        pix.extend(row)
        if bw & 1:
            pix.append(0)
    rr_all = []
    for y in range(y0, y1 + 1):
        rr, x = [], x0
        while x <= x1:
            if spr[y][x]:
                s = x
                while x <= x1 and spr[y][x]:
                    x += 1
                rr.append((s - x0) | ((x - s) << 8))
            else:
                x += 1
        rr_all.append(rr)
    block, pos = [], bh + 1
    for rr in rr_all:
        block.append(pos)
        pos += len(rr)
    block.append(pos)
    for rr in rr_all:
        block.extend(rr)
    if len(block) & 1:
        block.append(0)
    runs.extend(block)
    return (x0, y0, bw, bh), pix_off, run_off


def encode_shadow(sh, mirror, cfg, masks):
    cw, ch = cfg['cell_w'], cfg['cell_h']
    scx = (cw - cfg['shadow_cx']) if mirror else cfg['shadow_cx']
    scy = cfg['shadow_cy']

    raw_pts = [(x - scx + SH_CANVAS // 2, y - scy + SH_CANVAS // 2) for (x, y) in sh]
    valid_pts = [(px, py) for (px, py) in raw_pts if 0 <= px < SH_CANVAS and 0 <= py < SH_CANVAS]

    off = len(masks)
    if not valid_pts:
        return (0, 0, 0, 0), off

    xs = [p[0] for p in valid_pts]
    ys = [p[1] for p in valid_pts]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bw, bh = max_x - min_x + 1, max_y - min_y + 1

    if bw > 64:
        mid_x = int(round(sum(xs) / len(xs)))
        min_x = max(0, min(SH_CANVAS - 64, mid_x - 32))
        max_x = min_x + 63
        bw = 64
    if bh > 64:
        mid_y = int(round(sum(ys) / len(ys)))
        min_y = max(0, min(SH_CANVAS - 64, mid_y - 32))
        max_y = min_y + 63
        bh = 64

    pset = set((px, py) for (px, py) in valid_pts if min_x <= px <= max_x and min_y <= py <= max_y)
    nib = []
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            nib.append(15 if (x, y) in pset else 0)
    for i in range(0, len(nib), 2):
        lo = nib[i]
        hi = nib[i + 1] if i + 1 < len(nib) else 0
        masks.append(lo | (hi << 4))
    return (min_x, min_y, bw, bh), off


def main():
    pix, runs, masks = [], [], []

    all_f_bounds = []
    all_f_poff = []
    all_f_roff = []
    all_s_bounds = []
    all_s_off = []

    for k_idx, cfg in enumerate(KINDS):
        k_fb, k_fp, k_fr, k_sb, k_so = [], [], [], [], []
        cw, ch = cfg['cell_w'], cfg['cell_h']
        reuse_map = cfg.get('reuse_pix_from') or {}

        for mirror in (0, 1):
            fb, fp, fr, sb, so = [], [], [], [], []
            frames = [split_frame(load_frame(cfg['dir'], i, cw, ch), mirror, cfg) for i in range(N_FRAMES)]

            prev_sb, prev_so = None, None
            for i, (spr, sh) in enumerate(frames):
                if i in reuse_map:
                    ref_idx = reuse_map[i]
                    b = fb[ref_idx]
                    po = fp[ref_idx]
                    ro = fr[ref_idx]
                else:
                    b, po, ro = encode_sprite(spr, cw, ch, pix, runs)
                fb.append(b); fp.append(po); fr.append(ro)

                # Shadow optimization: share shadow mask every 2 frames (i and i-1)
                if (i & 1) and prev_sb is not None:
                    b2, o2 = prev_sb, prev_so
                else:
                    b2, o2 = encode_shadow(sh, mirror, cfg, masks)
                    prev_sb, prev_so = b2, o2
                sb.append(b2); so.append(o2)

            # Frame 12: remnant
            if cfg['has_remnant']:
                last = frames[N_FRAMES - 1][0]
                comps = components(last, cw, ch)
                ax = (cw - cfg['anchor_x']) if mirror else cfg['anchor_x']
                ay = cfg['anchor_y']
                hero = min(comps, key=lambda c: min(abs(x - ax) + abs(y - (ay - 8)) for x, y in c))
                rem = [[0] * (cw + 1) for _ in range(ch)]
                for c in comps:
                    if c is hero or len(c) < 6:
                        continue
                    for x, y in c:
                        rem[y][x] = last[y][x]
                b, po, ro = encode_sprite(rem, cw, ch, pix, runs)
            else:
                b, po, ro = (0, 0, 0, 0), len(pix), len(runs)

            fb.append(b); fp.append(po); fr.append(ro)

            k_fb.append(fb); k_fp.append(fp); k_fr.append(fr)
            k_sb.append(sb); k_so.append(so)

        all_f_bounds.append(k_fb)
        all_f_poff.append(k_fp)
        all_f_roff.append(k_fr)
        all_s_bounds.append(k_sb)
        all_s_off.append(k_so)

    def arr_bounds(name, data):
        out = ['const uint8_t %s[%d][2][%d][4] = {' % (name, len(data), len(data[0][0]))]
        for k_idx, k_data in enumerate(data):
            out.append('    { /* kind %d: %s */' % (k_idx, KINDS[k_idx]['name']))
            for m_data in k_data:
                out.append('        {')
                for b in m_data:
                    out.append('            { %d, %d, %d, %d },' % tuple(b))
                out.append('        },')
            out.append('    },')
        out.append('};\n')
        return '\n'.join(out)

    def arr_offsets(name, data):
        out = ['const uint32_t %s[%d][2][%d] = {' % (name, len(data), len(data[0][0]))]
        for k_idx, k_data in enumerate(data):
            out.append('    { /* kind %d: %s */' % (k_idx, KINDS[k_idx]['name']))
            for m_data in k_data:
                out.append('        { ' + ', '.join(str(v) for v in m_data) + ' },')
            out.append('    },')
        out.append('};\n')
        return '\n'.join(out)

    def flat(name, ctype, data, fmt, per=16):
        lines = []
        for i in range(0, len(data), per):
            lines.append('    ' + ', '.join(fmt(x) for x in data[i:i + per]) + ',')
        return 'const %s %s[] __attribute__((aligned(4))) = {\n%s\n};\n' % (ctype, name, '\n'.join(lines))

    # C code output
    c = [
        '// Generado por tools/generate_remate_sprites.py: no editar a mano.\n',
        '#include "remate_sprites.h"\n\n',
        'const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS] = {\n'
    ]
    for k in KINDS:
        sox = k['shadow_cx'] - k['anchor_x']
        soy = k['shadow_cy'] - k['anchor_y']
        c.append('    { %d, %d, %d, %d, %d, %d, %d, %d, %d, %d }, /* %s */\n' % (
            k['cell_w'], k['cell_h'], k['anchor_x'], k['anchor_y'],
            k['enemy_dx'], k['enemy_dy'], sox, soy,
            k['has_remnant'], N_FRAMES, k['name']
        ))
    c.append('};\n\n')

    c.append(arr_bounds('g_remate_frame_bounds', all_f_bounds))
    c.append('\n' + arr_offsets('g_remate_frame_offsets', all_f_poff))
    c.append('\n' + arr_offsets('g_remate_run_offsets', all_f_roff))
    c.append('\n' + arr_bounds('g_remate_shadow_bounds', all_s_bounds))
    c.append('\n' + arr_offsets('g_remate_shadow_offsets', all_s_off))

    c.append('\n' + flat('g_remate_pixels', 'uint16_t', pix, lambda v: '0x%04X' % v))
    c.append('\n' + flat('g_remate_runs', 'uint16_t', runs, str))
    c.append('\n' + flat('g_remate_shadow_masks', 'uint8_t', masks or [0], lambda v: '0x%02X' % v, 24))

    with open(os.path.join(WT, 'source', 'remate_sprites.c'), 'w', newline='\n') as f:
        f.write(''.join(c))

    # Header output
    h = '''#ifndef REMATE_SPRITES_H
#define REMATE_SPRITES_H
// Generado por tools/generate_remate_sprites.py: no editar a mano.
#include <stdint.h>

#define REMATE_KIND_EXVOTO   0
#define REMATE_KIND_CIRENEO  1
#define REMATE_NUM_KINDS     2

#define REMATE_NUM_FRAMES    12
#define REMATE_SHADOW_CANVAS 80

typedef struct {
    uint8_t cell_w;
    uint8_t cell_h;
    uint8_t anchor_x;
    uint8_t anchor_y;
    int8_t  enemy_dx;
    int8_t  enemy_dy;
    int8_t  shadow_ox;
    int8_t  shadow_oy;
    uint8_t has_remnant;
    uint8_t remnant_frame;
} RemateKindInfo;

extern const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS];

extern const uint8_t g_remate_frame_bounds[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES + 1][4];
extern const uint32_t g_remate_frame_offsets[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES + 1];
extern const uint32_t g_remate_run_offsets[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES + 1];

extern const uint8_t g_remate_shadow_bounds[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES][4];
extern const uint32_t g_remate_shadow_offsets[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES];

extern const uint16_t g_remate_pixels[];
extern const uint16_t g_remate_runs[];
extern const uint8_t g_remate_shadow_masks[];

#endif
'''
    with open(os.path.join(WT, 'include', 'remate_sprites.h'), 'w', newline='\n') as f:
        f.write(h)

    print('OK: pixels %d B, runs %d B, shadow %d B (total: %d B)' % (
        len(pix) * 2, len(runs) * 2, len(masks),
        len(pix) * 2 + len(runs) * 2 + len(masks)
    ))


if __name__ == '__main__':
    main()
