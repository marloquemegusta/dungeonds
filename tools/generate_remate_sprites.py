"""Genera nitrofiles/remate/<kind>_d<dir>.bin, source/remate_sprites.c y include/remate_sprites.h
a partir de los paquetes exportados por el lab headless (walkthroughs/remate-exvoto/assets/lab_out/).
"""
import json
import math
import os
import struct
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_minmax

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB_OUT = os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', 'lab_out')
GLB_DIR = os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', 'glb')
HERO_NODE = 'tripo_node_f25681c0'   # malla del heroe (Corazon) dentro de los GLB de la escena
HERO_MESH = 'f25681c0'
CAM_COS = math.cos(math.radians(30.0))   # elevacion del lab: 1 m de altura = ppm*cos(30) px
NITRO_DIR = os.path.join(WT, 'nitrofiles', 'remate')

KINDS = [
    {
        'name': 'exvoto',
        'ppm': 38.0,
        'has_remnant': 1,
        'reuse_pix_from': None,
    },
    {
        'name': 'cireneo',
        'ppm': 56.4,
        'has_remnant': 1,
        'reuse_pix_from': {10: 9, 11: 9},
    },
]

N_FRAMES = 12
N_DIRS = 8
SH_CANVAS = 80
MAGIC = 0x54414D52  # 'RMAT'
DIR_NAMES = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']


def load_lab_frame(kind_dir, d, i, cw, ch):
    p = os.path.join(kind_dir, 'frames', DIR_NAMES[d], '%d.png' % i)
    im = Image.open(p).convert('RGBA')
    assert im.size == (cw, ch), (p, im.size, (cw, ch))
    spr = [[0] * (cw + 1) for _ in range(ch)]
    for y in range(ch):
        for x in range(cw):
            r, g, b, a = im.getpixel((x, y))
            if a >= 96:
                spr[y][x] = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) | 0x8000
    return spr


def load_lab_shadow(shadow_atlas, sh_size, d, i):
    """Celda (i, d) del atlas de sombras: el atlas tiene framesPerDirection columnas y 8 filas de sh_size px."""
    cell = shadow_atlas.crop((i * sh_size, d * sh_size, (i + 1) * sh_size, (d + 1) * sh_size))
    pts = set()
    for y in range(sh_size):
        for x in range(sh_size):
            if cell.getpixel((x, y))[3] >= 96:
                pts.add((x, y))
    return pts, sh_size, sh_size


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


def encode_shadow(sh, scx, scy, masks):
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


def hero_end_pose(cfg):
    """Pies del heroe en el ultimo fotograma de la animacion, leidos de la escena exportada (GLB f11):
    dist = metros por delante hacia el enemigo (el enemigo esta en el origen de mundo), lat = lateral y
    lift_px = elevacion del dibujo respecto al suelo del ancla. El lab renderiza los remates con suelo comun
    (--fixedGround: y = 0 de la escena en todos los fotogramas), asi que el ancla del lab ya esta en el suelo
    de la escena y la elevacion es 0."""
    p = os.path.join(GLB_DIR, cfg['name'], 'f%02d.glb' % (N_FRAMES - 1))
    tx, _, tz = glb_minmax.node_translation(p, HERO_NODE)
    return -tx, -tz, 0.0


def hero_feet_by_frame(cfg):
    """Pies del heroe en cada fotograma (escena de Blender): centroide de sus vertices a menos de 3 cm de su punto
    mas bajo, en coordenadas de mundo del GLB (x, z) y altura sobre el suelo comun (y)."""
    res = []
    for f in range(N_FRAMES):
        h = glb_minmax.world_points(os.path.join(GLB_DIR, cfg['name'], 'f%02d.glb' % f), HERO_MESH)
        m = float(h[:, 1].min())
        c = h[h[:, 1] < m + 0.03]
        res.append((float(c[:, 0].mean()), float(c[:, 2].mean()), m))
    return res


def hero_feet_cell(cfg, settings, d, feet):
    """Donde caen los pies del heroe dentro de la celda del lab (px), con el mismo suelo comun que el render."""
    lab_ax, lab_ay = settings['anchor']
    ang = d * math.pi / 4.0
    ux, uy = -math.sin(ang), math.cos(ang)
    rx, ry = -uy, ux
    fx, fz, yh = feet
    edx = (-fx * ux + -fz * rx) * cfg['ppm']
    edy = (-fx * uy + -fz * ry) * cfg['ppm'] * 0.5
    return lab_ax - edx, lab_ay - edy - yh * cfg['ppm'] * CAM_COS


def split_layers(spr, cw, ch, feet_xy):
    """Parte un fotograma en dos actores: A = la pieza conexa que toca los pies del heroe (heroe + enemigo en
    el agarre, cruz que lleva) y B = el resto (mitades, trozos, polvo sueltos). Cada capa se dibuja con su propia
    profundidad. Devuelve (A, B) con la misma forma que `spr`; B puede quedar vacia."""
    comps = components(spr, cw, ch)
    a = [[0] * (cw + 1) for _ in range(ch)]
    b = [[0] * (cw + 1) for _ in range(ch)]
    if not comps:
        return a, b
    fx, fy = feet_xy
    owner = min(range(len(comps)), key=lambda k: min((x - fx) ** 2 + (y - fy) ** 2 for x, y in comps[k]))
    for k, comp in enumerate(comps):
        dst = a if k == owner else b
        for x, y in comp:
            dst[y][x] = spr[y][x]
    return a, b


def bottom_row(spr, ch, w):
    for y in range(ch - 1, -1, -1):
        if any(spr[y][:w]):
            return y
    return None


def dir_geometry(cfg, settings, d):
    cw, ch = map(int, settings['frameSize'].split('x'))
    lab_ax, lab_ay = settings['anchor']
    ang = d * math.pi / 4.0
    ux = -math.sin(ang)
    uy = math.cos(ang)
    rx = -uy
    ry = ux
    dist, lat, lift_px = hero_end_pose(cfg)
    edx = int(round((dist * ux + lat * rx) * cfg['ppm']))
    edy = int(round((dist * uy + lat * ry) * cfg['ppm'] * 0.5 + lift_px))
    ax = max(0, min(cw - 1, lab_ax - edx))
    ay = max(0, min(ch - 1, lab_ay - edy))
    return cw, ch, ax, ay, edx, edy, lab_ax, lab_ay


def pack_dir_bin(cfg, settings, shadow_atlas, d, feet):
    sh_size = int(settings['shadowSize'][0])
    kind_dir = os.path.join(LAB_OUT, cfg['name'])
    cw, ch, ax, ay, edx, edy, lab_ax, lab_ay = dir_geometry(cfg, settings, d)
    reuse_map = cfg.get('reuse_pix_from') or {}
    pix, runs, masks = [], [], []
    fb, fp, fr, sb, so = [], [], [], [], []
    db, dp, dr, depth = [], [], [], []
    frames = [load_lab_frame(kind_dir, d, i, cw, ch) for i in range(N_FRAMES)]
    # El render del lab del fotograma 0 no coincide con la escena (GLB f00): heroe ~20 px desplazado y enemigo en otra
    # pose (bug del renderer pendiente). El hueco 0 es copia del 1 (pixeles, capas, profundidad, sombra y pies).
    frames[0] = frames[1]
    feet = [feet[1]] + list(feet[1:])
    # Pies del heroe en el suelo (altura 0) por fotograma, relativos al ancla (px de mundo).
    hero_off = []
    for i in range(N_FRAMES):
        gx, gy = hero_feet_cell(cfg, settings, d, (feet[i][0], feet[i][1], 0.0))
        hero_off.append((max(-127, min(127, int(round(gx - ax)))), max(-127, min(127, int(round(gy - ay))))))

    prev_sb, prev_so = None, None
    for i, spr in enumerate(frames):
        if i in reuse_map:
            ref_idx = reuse_map[i]
            b, po, ro = fb[ref_idx], fp[ref_idx], fr[ref_idx]
            b2_, po2_, ro2_ = db[ref_idx], dp[ref_idx], dr[ref_idx]
            depth.append(depth[ref_idx])
        else:
            la, lb = split_layers(spr, cw, ch, hero_feet_cell(cfg, settings, d, feet[i]))
            b, po, ro = encode_sprite(la, cw, ch, pix, runs)
            b2_, po2_, ro2_ = encode_sprite(lb, cw, ch, pix, runs)
            # Capa A (heroe + enemigo en el agarre): la del mas cercano a la camara entre los pies del heroe en ese
            # fotograma y el punto de suelo del enemigo (el origen de mundo, la y del ancla del lab). Capa B (restos):
            # su fila mas baja, que para un trozo tumbado es su borde mas cercano al suelo.
            hy = hero_feet_cell(cfg, settings, d, feet[i])[1]
            rb = bottom_row(lb, ch, cw + 1)
            clamp = lambda v: max(-127, min(127, v))
            depth.append((clamp(int(round(max(hy, settings['anchor'][1]))) - ay), clamp((rb if rb is not None else ay) - ay)))
        fb.append(b); fp.append(po); fr.append(ro)
        db.append(b2_); dp.append(po2_); dr.append(ro2_)

        if (i & 1) and i != 1 and prev_sb is not None:
            b2, o2 = prev_sb, prev_so
        else:
            sh, sw, sh_h = load_lab_shadow(shadow_atlas, sh_size, d, 1 if i == 0 else i)
            b2, o2 = encode_shadow(sh, sw // 2, sh_h // 2, masks)
            prev_sb, prev_so = b2, o2
        sb.append(b2); so.append(o2)

    if cfg['has_remnant']:
        rem = load_lab_frame(kind_dir, d, N_FRAMES, cw, ch)
        b, po, ro = encode_sprite(rem, cw, ch, pix, runs)
    else:
        b, po, ro = (0, 0, 0, 0), len(pix), len(runs)
    fb.append(b); fp.append(po); fr.append(ro)
    db.append((0, 0, 0, 0)); dp.append(len(pix)); dr.append(len(runs))   # restos: una sola capa

    if len(pix) & 1:
        pix.append(0)
    if len(runs) & 1:
        runs.append(0)
    while len(masks) & 3:
        masks.append(0)

    pix_bytes = len(pix) * 2
    runs_bytes = len(runs) * 2
    mask_bytes = len(masks)

    buf = bytearray()
    buf += struct.pack('<4I', MAGIC, pix_bytes, runs_bytes, mask_bytes)
    for b in fb:
        buf += struct.pack('<4B', *b)
    buf += struct.pack('<%dI' % (N_FRAMES + 1), *fp)
    buf += struct.pack('<%dI' % (N_FRAMES + 1), *fr)
    for b in sb:
        buf += struct.pack('<4B', *b)
    buf += struct.pack('<%dI' % N_FRAMES, *so)
    for b in db:
        buf += struct.pack('<4B', *b)
    buf += struct.pack('<%dI' % (N_FRAMES + 1), *dp)
    buf += struct.pack('<%dI' % (N_FRAMES + 1), *dr)
    buf += struct.pack('<%dH' % len(pix), *pix)
    buf += struct.pack('<%dH' % len(runs), *runs)
    buf += bytes(masks)
    return bytes(buf), depth, hero_off


def main():
    os.makedirs(NITRO_DIR, exist_ok=True)
    max_bin = 0
    total_disk = 0
    kind_infos = []
    dir_infos = []
    depth_infos = []
    off_infos = []

    for cfg in KINDS:
        settings_path = os.path.join(LAB_OUT, cfg['name'], 'settings.json')
        with open(settings_path) as f:
            settings = json.load(f)
        shadow_atlas = Image.open(os.path.join(LAB_OUT, cfg['name'], 'shadow.png')).convert('RGBA')
        cw, ch = map(int, settings['frameSize'].split('x'))
        sh_size = int(settings['shadowSize'][0])
        n_lab = int(settings['framesPerDirection'])
        assert n_lab == N_FRAMES + (1 if cfg['has_remnant'] else 0), (cfg['name'], n_lab)
        assert shadow_atlas.size == (n_lab * sh_size, N_DIRS * sh_size), (cfg['name'], shadow_atlas.size)
        kind_infos.append((cw, ch, cfg['has_remnant'], N_FRAMES, cfg['name']))
        d_list = []
        depth_list = []
        off_list = []
        feet = hero_feet_by_frame(cfg)
        for d in range(N_DIRS):
            data, depth, hero_off = pack_dir_bin(cfg, settings, shadow_atlas, d, feet)
            out_path = os.path.join(NITRO_DIR, '%s_d%d.bin' % (cfg['name'], d))
            with open(out_path, 'wb') as f:
                f.write(data)
            max_bin = max(max_bin, len(data))
            total_disk += len(data)
            _, _, ax, ay, edx, edy, lab_ax, lab_ay = dir_geometry(cfg, settings, d)
            sox = lab_ax - ax
            soy = lab_ay - ay
            d_list.append((ax, ay, edx, edy, sox, soy, d))
            depth_list.append(depth)
            off_list.append(hero_off)
        dir_infos.append((cfg['name'], d_list))
        depth_infos.append((cfg['name'], depth_list))
        off_infos.append((cfg['name'], off_list))

    max_bin_aligned = (max_bin + 15) & ~15

    c = [
        '// Generado por tools/generate_remate_sprites.py: no editar a mano.\n',
        '#include "remate_sprites.h"\n\n',
        'const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS] = {\n',
    ]
    for cw, ch, hr, rf, name in kind_infos:
        c.append('    { %d, %d, %d, %d }, /* %s */\n' % (cw, ch, hr, rf, name))
    c.append('};\n\n')
    c.append('const RemateDirInfo g_remate_dir_info[REMATE_NUM_KINDS][REMATE_NUM_DIRS] = {\n')
    for name, d_list in dir_infos:
        c.append('    { /* %s */\n' % name)
        for ax, ay, edx, edy, sox, soy, d in d_list:
            c.append('        { %d, %d, %d, %d, %d, %d }, /* dir %d */\n' % (ax, ay, edx, edy, sox, soy, d))
        c.append('    },\n')
    c.append('};\n\n')
    c.append('const int8_t g_remate_depth[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_NUM_FRAMES][2] = {\n')
    for name, depth_list in depth_infos:
        c.append('    { /* %s */\n' % name)
        for d, offs in enumerate(depth_list):
            c.append('        { %s }, /* dir %d */\n' % (', '.join('{%d, %d}' % v for v in offs), d))
        c.append('    },\n')
    c.append('};\n\n')
    c.append('const int8_t g_remate_hero_off[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_NUM_FRAMES][2] = {\n')
    for name, off_list in off_infos:
        c.append('    { /* %s */\n' % name)
        for d, offs in enumerate(off_list):
            c.append('        { %s }, /* dir %d */\n' % (', '.join('{%d, %d}' % v for v in offs), d))
        c.append('    },\n')
    c.append('};\n')

    with open(os.path.join(WT, 'source', 'remate_sprites.c'), 'w', newline='\n') as f:
        f.write(''.join(c))

    h = '''#ifndef REMATE_SPRITES_H
#define REMATE_SPRITES_H
// Generado por tools/generate_remate_sprites.py: no editar a mano.
#include <stdint.h>

#define REMATE_KIND_EXVOTO   0
#define REMATE_KIND_CIRENEO  1
#define REMATE_NUM_KINDS     2
#define REMATE_NUM_DIRS      8

#define REMATE_NUM_FRAMES    12
#define REMATE_SHADOW_CANVAS 80
#define REMATE_BIN_MAGIC     0x54414D52u
#define REMATE_MAX_BIN_BYTES %d

typedef struct {
    uint8_t cell_w;
    uint8_t cell_h;
    uint8_t has_remnant;
    uint8_t remnant_frame;
} RemateKindInfo;

typedef struct {
    uint8_t anchor_x;
    uint8_t anchor_y;
    int8_t  enemy_dx;
    int8_t  enemy_dy;
    int8_t  shadow_ox;
    int8_t  shadow_oy;
} RemateDirInfo;

typedef struct {
    uint32_t magic;
    uint32_t pix_bytes;
    uint32_t runs_bytes;
    uint32_t mask_bytes;
    uint8_t  f_bounds[REMATE_NUM_FRAMES + 1][4];
    uint32_t f_pix_off[REMATE_NUM_FRAMES + 1];
    uint32_t f_run_off[REMATE_NUM_FRAMES + 1];
    uint8_t  s_bounds[REMATE_NUM_FRAMES][4];
    uint32_t s_mask_off[REMATE_NUM_FRAMES];
    uint8_t  d_bounds[REMATE_NUM_FRAMES + 1][4];     // capa B: restos sueltos del fotograma (0 = ninguno)
    uint32_t d_pix_off[REMATE_NUM_FRAMES + 1];
    uint32_t d_run_off[REMATE_NUM_FRAMES + 1];
} RemateBinHeader;

extern const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS];
extern const RemateDirInfo g_remate_dir_info[REMATE_NUM_KINDS][REMATE_NUM_DIRS];
// Profundidad de cada capa de la celda por fotograma ([0] = heroe y enemigo en el agarre, [1] = restos sueltos), en px de mundo
// respecto a los pies finales del heroe: [0] la mas cercana entre los pies del heroe y el enemigo, [1] la fila mas baja de los restos (pack_dir_bin en el generador).
extern const int8_t g_remate_depth[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_NUM_FRAMES][2];
// Pies del heroe en el suelo (x, y) por fotograma, en px de mundo respecto al ancla (sus pies finales): el fotograma 0 es
// donde debe estar para empezar sin salto y el 11 es (0,0). Lo usan la embestida previa y la camara (remate.c).
extern const int8_t g_remate_hero_off[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_NUM_FRAMES][2];

#endif
''' % max_bin_aligned
    with open(os.path.join(WT, 'include', 'remate_sprites.h'), 'w', newline='\n') as f:
        f.write(h)

    print('OK: 16 nitro bins, max=%d B (buf=%d B), total_nitro=%d B' % (
        max_bin, max_bin_aligned, total_disk
    ))


if __name__ == '__main__':
    main()
