"""Genera nitrofiles/remate/<kind>_d<dir>.bin, source/remate_sprites.c e include/remate_sprites.h.

Tipos de remate (REMATE_NUM_KINDS): Exvoto (12 fotogramas), Cireneo (12) y Ojo del Tribunal (38). Los tres comparten
el formato de paquete binario, pero cada tipo decide su numero de fotogramas y de ticks de juego via `RemateKindInfo`
(no hay un REMATE_NUM_FRAMES global). El lab exporta las escenas como paquetes 1x + sombras; ver `walkthroughs/remate-ojo`.

Los paquetes del lab de Exvoto y Cireneo nunca se versionaron: sus bins y sus tablas quedan congelados en
`tools/remate_legacy.json` (extraido de `source/remate_sprites.c`) y este script no los reescribe. Solo el Ojo se
re-empaqueta aqui, desde su paquete del lab (`OJO_LAB_OUT`, por defecto walkthroughs/remate-ojo/assets/lab_out).

Uso: python tools/generate_remate_sprites.py
     python tools/generate_remate_sprites.py --migrate-masks   (convierte los bins 'RMAT' existentes, sombras de 4 bpp, al
     formato 'RMT1' de 1 bpp sin necesitar el lab)
"""
import json
import math
import os
import re
import struct
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_minmax

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_JSON = os.path.join(WT, 'tools', 'remate_legacy.json')
# Paquete del lab del Ojo y GLB de la escena (para calcular donde caen los pies del heroe en cada fotograma).
OJO_LAB_OUT = os.environ.get('OJO_LAB_OUT', os.path.join(WT, 'walkthroughs', 'remate-ojo', 'assets', 'lab_out'))
OJO_GLB_DIR = os.environ.get('OJO_GLB', os.path.join(WT, 'scratch_lab', 'glb_ojo'))
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
        'frames': 12,
        'ticks': 6,
        'legacy': True,
    },
    {
        'name': 'cireneo',
        'ppm': 56.4,
        'has_remnant': 1,
        'reuse_pix_from': {10: 9, 11: 9},
        'frames': 12,
        'ticks': 6,
        'legacy': True,
    },
    {
        'name': 'ojo',
        'ppm': 35.0,          # lab rapido: 96 px / 2,742857 m de fitExtent
        'has_remnant': 1,     # fotograma 38 = el Ojo tendido sin el heroe
        'reuse_pix_from': None,
        'frames': 38,
        'ticks': 4,           # 38*4 = 152 frames de juego (~2,5 s): el ritmo del GIF aprobado (60 ms/fotograma)
        'legacy': False,
        'single_layer': True, # la escena no se parte en heroe/restos: una sola capa a la profundidad de los pies
        'dup_frame0': False,  # el lab rapido renderiza el fotograma 0 bien (el hack era del lab web)
        'shadow_share': True, # las mascaras de sombra se comparten cada 2 fotogramas (mismo criterio que el Exvoto)
        'shadow_canvas': 128,
        'shadow_max': 80,
        'lab_out': OJO_LAB_OUT,
        'glb_dir': OJO_GLB_DIR,
    },
]

N_DIRS = 8
SH_CANVAS = 80
MAGIC = 0x31544D52  # 'RMT1': mascaras de sombra a 1 bpp (el 'RMAT' = 0x54414D52 anterior las llevaba en nibbles de 4 bits)
MAGIC_4BPP = 0x54414D52
DIR_NAMES = ['0_S', '1_SW', '2_W', '3_NW', '4_N', '5_NE', '6_E', '7_SE']
MAX_FRAMES = max(k['frames'] for k in KINDS)


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


def encode_shadow(sh, scx, scy, masks, canvas=SH_CANVAS, max_dim=64):
    raw_pts = [(x - scx + canvas // 2, y - scy + canvas // 2) for (x, y) in sh]
    valid_pts = [(px, py) for (px, py) in raw_pts if 0 <= px < canvas and 0 <= py < canvas]

    off = len(masks)
    if not valid_pts:
        return (0, 0, 0, 0), off

    xs = [p[0] for p in valid_pts]
    ys = [p[1] for p in valid_pts]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bw, bh = max_x - min_x + 1, max_y - min_y + 1

    if bw > max_dim:
        mid_x = int(round(sum(xs) / len(xs)))
        min_x = max(0, min(canvas - max_dim, mid_x - max_dim // 2))
        max_x = min_x + max_dim - 1
        bw = max_dim
    if bh > max_dim:
        mid_y = int(round(sum(ys) / len(ys)))
        min_y = max(0, min(canvas - max_dim, mid_y - max_dim // 2))
        max_y = min_y + max_dim - 1
        bh = max_dim

    pset = set((px, py) for (px, py) in valid_pts if min_x <= px <= max_x and min_y <= py <= max_y)
    bits = []
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            bits.append(1 if (x, y) in pset else 0)
    # 1 bpp, flujo continuo de filas, LSB primero, relleno a byte por fotograma
    for i in range(0, len(bits), 8):
        v = 0
        for k, bit in enumerate(bits[i:i + 8]):
            v |= bit << k
        masks.append(v)
    return (min_x, min_y, bw, bh), off


def hero_end_pose(cfg):
    """Pies del heroe en el ultimo fotograma de la animacion, leidos de la escena exportada (GLB): dist = metros por
    delante hacia el enemigo (el enemigo esta en el origen de mundo), lat = lateral y lift_px = elevacion del dibujo
    respecto al suelo del ancla. El lab renderiza con suelo comun (--fixedGround), asi que la elevacion es 0."""
    p = os.path.join(cfg['glb_dir'], 'f%02d.glb' % (cfg['frames'] - 1))
    tx, _, tz = glb_minmax.node_translation(p, HERO_NODE)
    return -tx, -tz, 0.0


def hero_feet_by_frame(cfg):
    """Pies del heroe en cada fotograma (escena del lab): centroide de sus vertices a menos de 3 cm de su punto mas
    bajo, en coordenadas de mundo del GLB (x, z) y altura sobre el suelo comun (y)."""
    res = []
    for f in range(cfg['frames']):
        h = glb_minmax.world_points(os.path.join(cfg['glb_dir'], 'f%02d.glb' % f), HERO_MESH)
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


def bin_header_bytes(frames):
    """Tamano de la cabecera de un bin de `frames` fotogramas (mismo orden que pack_dir_bin)."""
    return 16 + (frames + 1) * 4 * 3 + frames * 4 * 2 + (frames + 1) * 4 * 3


def bin_chunks(path, frames):
    """Maximos por fotograma del bin (bytes): capa A+B de pixeles, capa A+B de runs y mascara de sombra.
    remate.c carga un fotograma cada vez desde NitroFS a buffers de ese tamano, en vez de todo el bin."""
    with open(path, 'rb') as f:
        b = f.read()
    magic, pix_bytes, runs_bytes, mask_bytes = struct.unpack_from('<4I', b, 0)
    assert magic == MAGIC, path
    off = 16
    off += (frames + 1) * 4                                   # f_bounds
    fp = struct.unpack_from('<%dI' % (frames + 1), b, off); off += (frames + 1) * 4
    fr = struct.unpack_from('<%dI' % (frames + 1), b, off); off += (frames + 1) * 4
    off += frames * 4                                         # s_bounds
    so = struct.unpack_from('<%dI' % frames, b, off); off += frames * 4
    off += (frames + 1) * 4                                   # d_bounds
    dp = struct.unpack_from('<%dI' % (frames + 1), b, off); off += (frames + 1) * 4
    dr = struct.unpack_from('<%dI' % (frames + 1), b, off)
    pix = runs = mask = 0
    for f in range(frames):
        pix = max(pix, (fp[f + 1] - fp[f] + dp[f + 1] - dp[f]) * 2)
        runs = max(runs, (fr[f + 1] - fr[f] + dr[f + 1] - dr[f]) * 2)
        end = mask_bytes
        for j in range(f + 1, frames):
            if so[j] > so[f]:
                end = so[j]
                break
        mask = max(mask, end - so[f])
    # Fotograma de restos (ultimo del bin, solo capa A y sin sombra): tambien tiene que caber.
    pix = max(pix, pix_bytes - fp[frames] * 2)
    runs = max(runs, runs_bytes - fr[frames] * 2)
    return pix, runs, mask, bin_header_bytes(frames)


def chunk_limits():
    """Buffers estaticos de remate.c: el peor fotograma de cualquier tipo/direccion, redondeado a 1 KiB."""
    pix = runs = mask = hdr = 0
    for cfg in KINDS:
        for d in range(N_DIRS):
            p = os.path.join(NITRO_DIR, '%s_d%d.bin' % (cfg['name'], d))
            a, b, c, h = bin_chunks(p, cfg['frames'])
            pix, runs, mask, hdr = max(pix, a), max(runs, b), max(mask, c), max(hdr, h)
    round_k = lambda v: (v + 1023) & ~1023
    return round_k(hdr), round_k(pix), round_k(runs), round_k(mask)


def pack_dir_bin(cfg, settings, shadow_atlas, d, feet):
    F = cfg['frames']
    sh_size = int(settings['shadowSize'][0])
    kind_dir = cfg['lab_out']
    cw, ch, ax, ay, edx, edy, lab_ax, lab_ay = dir_geometry(cfg, settings, d)
    reuse_map = cfg.get('reuse_pix_from') or {}
    pix, runs, masks = [], [], []
    fb, fp, fr, sb, so = [], [], [], [], []
    db, dp, dr, depth = [], [], [], []
    frames = [load_lab_frame(kind_dir, d, i, cw, ch) for i in range(F)]
    if cfg.get('dup_frame0'):   # hack del lab web: su fotograma 0 no coincide con la escena (GLB f00)
        frames[0] = frames[1]
        feet = [feet[1]] + list(feet[1:])
    hero_off = []
    for i in range(F):
        gx, gy = hero_feet_cell(cfg, settings, d, (feet[i][0], feet[i][1], 0.0))
        hero_off.append((max(-127, min(127, int(round(gx - ax)))), max(-127, min(127, int(round(gy - ay))))))

    prev_sb, prev_so = None, None
    for i, spr in enumerate(frames):
        if i in reuse_map:
            ref_idx = reuse_map[i]
            b, po, ro = fb[ref_idx], fp[ref_idx], fr[ref_idx]
        else:
            if cfg.get('single_layer'):
                la, lb = spr, [[0] * (cw + 1) for _ in range(ch)]
            else:
                la, lb = split_layers(spr, cw, ch, hero_feet_cell(cfg, settings, d, feet[i]))
            b, po, ro = encode_sprite(la, cw, ch, pix, runs)
            if cfg.get('single_layer'):
                b2_, po2_, ro2_ = (0, 0, 0, 0), len(pix), len(runs)
            else:
                b2_, po2_, ro2_ = encode_sprite(lb, cw, ch, pix, runs)
            hy = hero_feet_cell(cfg, settings, d, feet[i])[1]
            rb = bottom_row(lb, ch, cw + 1)
            clamp = lambda v: max(-127, min(127, v))
            depth.append((clamp(int(round(max(hy, settings['anchor'][1]))) - ay),
                          clamp((rb if rb is not None else ay) - ay)))
        fb.append(b); fp.append(po); fr.append(ro)
        db.append(b2_); dp.append(po2_); dr.append(ro2_)

        if cfg.get('shadow_share') and (i & 1) and i != 1 and prev_sb is not None:
            sb.append(prev_sb); so.append(prev_so)
        else:
            sh, sw, sh_h = load_lab_shadow(shadow_atlas, sh_size, d, i)
            b2, o2 = encode_shadow(sh, sw // 2, sh_h // 2, masks,
                                   canvas=cfg.get('shadow_canvas', SH_CANVAS),
                                   max_dim=cfg.get('shadow_max', 64))
            prev_sb, prev_so = b2, o2
            sb.append(b2); so.append(o2)

    if cfg['has_remnant']:
        rem = load_lab_frame(kind_dir, d, F, cw, ch)
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
    buf += struct.pack('<%dI' % (F + 1), *fp)
    buf += struct.pack('<%dI' % (F + 1), *fr)
    for b in sb:
        buf += struct.pack('<4B', *b)
    buf += struct.pack('<%dI' % F, *so)
    for b in db:
        buf += struct.pack('<4B', *b)
    buf += struct.pack('<%dI' % (F + 1), *dp)
    buf += struct.pack('<%dI' % (F + 1), *dr)
    buf += struct.pack('<%dH' % len(pix), *pix)
    buf += struct.pack('<%dH' % len(runs), *runs)
    buf += bytes(masks)
    return bytes(buf), depth, hero_off


def pad_rows(rows, width, n):
    """Completa cada fila de longitud `width` hasta `n` con ceros (frames que el tipo corto no usa)."""
    return [list(r) + [0] * (n - width) for r in rows]


def main():
    os.makedirs(NITRO_DIR, exist_ok=True)
    with open(LEGACY_JSON, encoding='utf-8') as f:
        legacy = json.load(f)

    kind_infos = []      # (cell_w, cell_h, has_remnant, remnant_frame, frames, ticks)
    dir_infos = []       # per kind: 8 rows of 6
    depth_infos = []     # per kind: 8 rows of MAX_FRAMES*2
    off_infos = []       # idem
    max_bin = 0

    for cfg in KINDS:
        F = cfg['frames']
        if cfg.get('legacy'):
            old = legacy[cfg['name']]
            cw, ch, hr, rf = old['kind']
            kind_infos.append((cw, ch, hr, rf, F, cfg['ticks']))
            dir_infos.append(old['dir'])
            depth_infos.append([pad_rows([r], F * 2, MAX_FRAMES * 2)[0] for r in old['depth']])
            off_infos.append([pad_rows([r], F * 2, MAX_FRAMES * 2)[0] for r in old['hero_off']])
            for d in range(N_DIRS):
                p = os.path.join(NITRO_DIR, '%s_d%d.bin' % (cfg['name'], d))
                assert os.path.exists(p), 'falta el bin congelado %s' % p
                max_bin = max(max_bin, os.path.getsize(p))
            continue

        settings_path = os.path.join(cfg['lab_out'], 'settings.json')
        with open(settings_path) as f:
            settings = json.load(f)
        shadow_atlas = Image.open(os.path.join(cfg['lab_out'], 'shadow.png')).convert('RGBA')
        cw, ch = map(int, settings['frameSize'].split('x'))
        sh_size = int(settings['shadowSize'][0])
        n_lab = int(settings['framesPerDirection'])
        assert n_lab == F + (1 if cfg['has_remnant'] else 0), (cfg['name'], n_lab)
        assert shadow_atlas.size == (n_lab * sh_size, N_DIRS * sh_size), (cfg['name'], shadow_atlas.size)
        kind_infos.append((cw, ch, cfg['has_remnant'], F, F, cfg['ticks']))
        d_list, depth_list, off_list = [], [], []
        feet = hero_feet_by_frame(cfg)
        bias_shift = (cfg.get('shadow_canvas', SH_CANVAS) - SH_CANVAS) // 2
        for d in range(N_DIRS):
            data, depth, hero_off = pack_dir_bin(cfg, settings, shadow_atlas, d, feet)
            with open(os.path.join(NITRO_DIR, '%s_d%d.bin' % (cfg['name'], d)), 'wb') as f:
                f.write(data)
            max_bin = max(max_bin, len(data))
            _, _, ax, ay, edx, edy, lab_ax, lab_ay = dir_geometry(cfg, settings, d)
            d_list.append((ax, ay, edx, edy, (lab_ax - ax) - bias_shift, (lab_ay - ay) - bias_shift))
            depth_list.append([v for pair in depth for v in pair])
            off_list.append([v for pair in hero_off for v in pair])
        dir_infos.append(d_list)
        depth_infos.append(depth_list)
        off_infos.append(off_list)

    max_bin_aligned = (max_bin + 15) & ~15
    hdr_k, pix_k, runs_k, mask_k = chunk_limits()

    c = [
        '// Generado por tools/generate_remate_sprites.py: no editar a mano.\n',
        '#include "remate_sprites.h"\n\n',
        'const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS] = {\n',
    ]
    for cw, ch, hr, rf, nf, tk in kind_infos:
        c.append('    { %d, %d, %d, %d, %d, %d },\n' % (cw, ch, hr, rf, nf, tk))
    c.append('};\n\n')
    c.append('const RemateDirInfo g_remate_dir_info[REMATE_NUM_KINDS][REMATE_NUM_DIRS] = {\n')
    for d_list in dir_infos:
        c.append('    {\n')
        for ax, ay, edx, edy, sox, soy in d_list:
            c.append('        { %d, %d, %d, %d, %d, %d },\n' % (ax, ay, edx, edy, sox, soy))
        c.append('    },\n')
    c.append('};\n\n')
    c.append('const int8_t g_remate_depth[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_MAX_FRAMES][2] = {\n')
    for depth_list in depth_infos:
        c.append('    {\n')
        for row in depth_list:
            c.append('        { %s },\n' % ', '.join('{%d, %d}' % (row[i], row[i + 1])
                                                    for i in range(0, MAX_FRAMES * 2, 2)))
        c.append('    },\n')
    c.append('};\n\n')
    c.append('const int8_t g_remate_hero_off[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_MAX_FRAMES][2] = {\n')
    for off_list in off_infos:
        c.append('    {\n')
        for row in off_list:
            c.append('        { %s },\n' % ', '.join('{%d, %d}' % (row[i], row[i + 1])
                                                    for i in range(0, MAX_FRAMES * 2, 2)))
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
#define REMATE_KIND_OJO      2
#define REMATE_NUM_KINDS     3
#define REMATE_NUM_DIRS      8

// Mayor numero de fotogramas de animacion de cualquier tipo (el Ojo, 38). Cada tipo declara los suyos en
// `RemateKindInfo.frames`; Exvoto y Cireneo usan 12. El bin de cada tipo lleva cabecera del tamano de sus frames.
#define REMATE_MAX_FRAMES    %d
#define REMATE_SHADOW_CANVAS 80
#define REMATE_BIN_MAGIC     0x31544D52u
// Streaming desde NitroFS (remate.c): la celda lee el fotograma que toca a estos buffers estaticos en vez de cargar
// el bin entero. Son el peor fotograma de cualquier tipo/direccion (cuadrados a 1 KiB por el generador).
#define REMATE_HEADER_BYTES  %d
#define REMATE_PIX_BYTES     %d
#define REMATE_RUN_BYTES     %d
#define REMATE_MASK_BYTES    %d

typedef struct {
    uint8_t cell_w;
    uint8_t cell_h;
    uint8_t has_remnant;
    uint8_t remnant_frame;   // indice del fotograma de restos dentro del bin
    uint8_t frames;          // fotogramas de animacion (sin el de restos)
    uint8_t ticks;           // frames de juego por fotograma de animacion
} RemateKindInfo;

typedef struct {
    uint8_t anchor_x;
    uint8_t anchor_y;
    int8_t  enemy_dx;
    int8_t  enemy_dy;
    int8_t  shadow_ox;
    int8_t  shadow_oy;
} RemateDirInfo;

extern const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS];
extern const RemateDirInfo g_remate_dir_info[REMATE_NUM_KINDS][REMATE_NUM_DIRS];
// Profundidad de cada capa de la celda por fotograma ([0] = heroe y enemigo en el agarre, [1] = restos sueltos), en px de mundo
// respecto a los pies finales del heroe. Solo se usan los primeros `frames` valores de cada fila.
extern const int8_t g_remate_depth[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_MAX_FRAMES][2];
// Pies del heroe en el suelo (x, y) por fotograma, en px de mundo respecto al ancla (sus pies finales): el fotograma 0 es
// donde debe estar para empezar sin salto y el ultimo es (0,0). Lo usan la embestida previa y la camara (remate.c).
extern const int8_t g_remate_hero_off[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_MAX_FRAMES][2];

#endif
''' % (MAX_FRAMES, hdr_k, pix_k, runs_k, mask_k)
    with open(os.path.join(WT, 'include', 'remate_sprites.h'), 'w', newline='\n') as f:
        f.write(h)

    print('OK: %d tipos, max bin=%d B; buffers header=%d pix=%d runs=%d mask=%d' % (len(KINDS), max_bin, hdr_k, pix_k, runs_k, mask_k))


SLUG_FRAMES = {'exvoto': 12, 'cireneo': 12, 'ojo': 38}


def migrate_bin_masks(path, frames):
    """Reescribe un bin 'RMAT' (mascaras de sombra en nibbles) como 'RMT1' (1 bpp, LSB primero, region por fotograma
    redondeada a byte). Devuelve (regiones, mayor region en bytes) o None si ya estaba migrado."""
    with open(path, 'rb') as f:
        b = f.read()
    magic, pix_bytes, runs_bytes, mask_bytes = struct.unpack_from('<4I', b, 0)
    if magic == MAGIC:
        return None
    assert magic == MAGIC_4BPP, path
    F = frames
    off = 16 + (F + 1) * 4 + (F + 1) * 4 * 2          # f_bounds, fp, fr
    sb = [struct.unpack_from('<4B', b, off + i * 4) for i in range(F)]
    so_at = off + F * 4
    so = list(struct.unpack_from('<%dI' % F, b, so_at))
    hdr_end = so_at + F * 4 + (F + 1) * 4 * 3
    assert hdr_end == bin_header_bytes(F), (path, hdr_end)
    mask0 = hdr_end + pix_bytes + runs_bytes
    old = b[mask0:mask0 + mask_bytes]
    assert len(old) == mask_bytes
    npx = {}                                           # offset viejo -> pixeles de la region
    for i in range(F):
        npx[so[i]] = max(npx.get(so[i], 0), sb[i][2] * sb[i][3])
    new_off, new_mask = {}, bytearray()
    for o in sorted(npx):
        new_off[o] = len(new_mask)
        n = npx[o]
        bits = []
        for k in range(n):
            nib = (old[o + (k >> 1)] >> 4) if (k & 1) else (old[o + (k >> 1)] & 0x0F)
            assert nib in (0, 15), (path, 'mascara no binaria')
            bits.append(1 if nib else 0)
        for k in range(0, n, 8):
            v = 0
            for j, bit in enumerate(bits[k:k + 8]):
                v |= bit << j
            new_mask.append(v)
    largest = max(((len(new_mask) if o == max(npx) else new_off[nxt]) - new_off[o])
                  for o, nxt in zip(sorted(npx), sorted(npx)[1:] + [max(npx)])) if npx else 0
    while len(new_mask) & 3:
        new_mask.append(0)
    out = bytearray(b[:hdr_end + pix_bytes + runs_bytes])
    struct.pack_into('<II', out, 0, MAGIC, pix_bytes)
    struct.pack_into('<II', out, 8, runs_bytes, len(new_mask))
    struct.pack_into('<%dI' % F, out, so_at, *[new_off[o] for o in so])
    out += new_mask
    with open(path, 'wb') as f:
        f.write(out)
    return len(npx), largest


def migrate_masks():
    biggest = 0
    for slug, F in SLUG_FRAMES.items():
        for d in range(N_DIRS):
            p = os.path.join(NITRO_DIR, '%s_d%d.bin' % (slug, d))
            r = migrate_bin_masks(p, F)
            if r:
                biggest = max(biggest, r[1])
    hdr_k, pix_k, runs_k, mask_k = chunk_limits_all()
    print('OK: bins migrados; REMATE_MASK_BYTES necesario = %d' % mask_k)
    hp = os.path.join(WT, 'include', 'remate_sprites.h')
    with open(hp, encoding='utf-8', newline='') as f:
        t = f.read()
    t2 = re.sub(r'(#define REMATE_BIN_MAGIC\s+)0x[0-9A-Fa-f]+u', r'\g<1>0x31544D52u', t)
    t2 = re.sub(r'(#define REMATE_MASK_BYTES\s+)\d+', lambda m: m.group(1) + str(mask_k), t2)
    with open(hp, 'w', encoding='utf-8', newline='') as f:
        f.write(t2)


def chunk_limits_all():
    hdr = pix = runs = mask = 0
    for slug, F in SLUG_FRAMES.items():
        for d in range(N_DIRS):
            a, b, c, h = bin_chunks(os.path.join(NITRO_DIR, '%s_d%d.bin' % (slug, d)), F)
            pix, runs, mask, hdr = max(pix, a), max(runs, b), max(mask, c), max(hdr, h)
    round_k = lambda v: (v + 1023) & ~1023
    return round_k(hdr), round_k(pix), round_k(runs), round_k(mask)


if __name__ == '__main__':
    if '--migrate-masks' in sys.argv:
        migrate_masks()
    else:
        main()

