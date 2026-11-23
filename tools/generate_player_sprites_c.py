import os, re, json, argparse
from PIL import Image

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parser = argparse.ArgumentParser()
parser.add_argument('--src', default=os.path.join(WT, 'assets/sprites/characters'))
parser.add_argument('--legibility', choices=['auto', 'anterior', 'c2'], default='auto',
                    help='DS conversion mode: auto (from settings.json), anterior (a<40, shift), or c2 (a<77, rounded)')
ARGS = parser.parse_args()
SRC_ROOT = os.path.abspath(ARGS.src)
SPRITE_W = 40
SPRITE_H = 40
SHADOW_W = 80
SHADOW_H = 80
MASK_BYTES = (SHADOW_W * SHADOW_H) // 2

def parse_header(h_path, mask_bytes=MASK_BYTES):
    with open(h_path, 'r', encoding='utf-8') as f:
        text = f.read()
    m_anc = re.search(r'g_\w+_ground_anchors\[8\]\s*=\s*\{([^}]+)\};', text)
    anchors = [int(x.strip()) for x in m_anc.group(1).split(',') if x.strip()]
    m_sb = re.search(r'g_\w+_sprite_bounds\[8\]\[4\]\s*=\s*\{([^;]+)\};', text)
    sb_rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', m_sb.group(1))
    sprite_bounds = [[int(x) for x in r] for r in sb_rows]
    m_shb = re.search(r'g_\w+_shadow_bounds\[8\]\[8\]\[4\]\s*=\s*\{([\s\S]+?)\n\};', text)
    shb_body = m_shb.group(1)
    m_mask = re.search(rf'g_\w+_shadow_masks\[8\]\[8\]\[{mask_bytes}\][^{{]+\{{([\s\S]+?)\n\}};', text)
    mask_body = m_mask.group(1)
    return anchors, sprite_bounds, shb_body, mask_body


def crop_shadow_to_80(shb_body, mask_body, src_w=120, src_h=120, frame_indices=None):
    """Crop src_w x src_h shadow bounds and 4-bit packed masks to 80x80 centered."""
    if frame_indices is None:
        frame_indices = list(range(8))
    off_x = (src_w - 80) // 2
    off_y = (src_h - 80) // 2
    assert off_x % 2 == 0, f'Expected even x offset, got {off_x}'
    rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', shb_body)
    assert len(rows) == 64, f'Expected 64 shadow_bounds, got {len(rows)}'
    shb_out = []
    for d in range(8):
        shb_out.append('    {\n')
        for f in frame_indices:
            x, y, w, h = [int(v) for v in rows[d * 8 + f]]
            nx = max(0, x - off_x)
            ny = max(0, y - off_y)
            shb_out.append(f'        {{ {nx}, {ny}, {w}, {h} }},\n')
        shb_out.append('    },\n')

    hex_bytes = [int(b, 16) for b in re.findall(r'0x[0-9A-Fa-f]{2}', mask_body)]
    frame_bytes = (src_w * src_h) // 2
    src_row_bytes = src_w // 2
    byte_off = off_x // 2
    assert len(hex_bytes) == 64 * frame_bytes, f'Expected {64 * frame_bytes} mask bytes, got {len(hex_bytes)}'
    mask_out = []
    for d in range(8):
        mask_out.append('    {\n')
        for f in frame_indices:
            src = hex_bytes[(d * 8 + f) * frame_bytes:(d * 8 + f + 1) * frame_bytes]
            cropped = []
            for y in range(off_y, off_y + 80):
                row_off = y * src_row_bytes
                cropped.extend(src[row_off + byte_off:row_off + byte_off + 40])
            mask_out.append('        {\n')
            for i in range(0, len(cropped), 16):
                chunk = ', '.join(f'0x{b:02X}' for b in cropped[i:i + 16])
                mask_out.append(f'            {chunk},\n')
            mask_out.append('        },\n')
        mask_out.append('    },\n')
    return ''.join(shb_out).rstrip('\n'), ''.join(mask_out).rstrip('\n')


def crop_shadow_120_to_80(shb_body, mask_body, frame_indices=None):
    return crop_shadow_to_80(shb_body, mask_body, 120, 120, frame_indices)

def crop_shadow_masks(shb_body, mask_body, shw=SHADOW_W, shh=SHADOW_H, frame_indices=None):
    """Pack 4-bit shadow masks tightly to each frame's [x, y, w, h] bounding box."""
    if frame_indices is None:
        frame_indices = list(range(8))
    rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', shb_body)
    assert len(rows) == 8 * len(frame_indices), f'Expected {8 * len(frame_indices)} shadow_bounds, got {len(rows)}'
    hex_bytes = [int(b, 16) for b in re.findall(r'0x[0-9A-Fa-f]{2}', mask_body)]
    frame_bytes = (shw * shh) // 2
    assert len(hex_bytes) == 8 * len(frame_indices) * frame_bytes, (
        f'Expected {8 * len(frame_indices) * frame_bytes} mask bytes, got {len(hex_bytes)}'
    )

    packed_all = []
    offsets = []
    for d in range(8):
        dir_offs = []
        for idx in range(len(frame_indices)):
            fi = d * len(frame_indices) + idx
            bx, by, bw, bh = [int(v) for v in rows[fi]]
            src = hex_bytes[fi * frame_bytes:(fi + 1) * frame_bytes]
            dir_offs.append(len(packed_all))
            nibbles = []
            for y in range(by, by + bh):
                row_off = y * shw
                for x in range(bx, bx + bw):
                    px = row_off + x
                    b = src[px >> 1]
                    nibbles.append((b >> 4) if (px & 1) else (b & 0x0F))
            for i in range(0, len(nibbles), 2):
                lo = nibbles[i]
                hi = nibbles[i + 1] if (i + 1) < len(nibbles) else 0
                packed_all.append(lo | (hi << 4))
        offsets.append(dir_offs)

    off_lines = ['{\n']
    for d in range(8):
        off_lines.append('    { ' + ', '.join(str(v) for v in offsets[d]) + ' },\n')
    off_lines.append('};\n')

    data_lines = ['{\n']
    if not packed_all:
        data_lines.append('    0x00,\n')
    else:
        for i in range(0, len(packed_all), 16):
            chunk = ', '.join(f'0x{b:02X}' for b in packed_all[i:i + 16])
            data_lines.append(f'    {chunk},\n')
    data_lines.append('};\n')
    return ''.join(off_lines), ''.join(data_lines)


def resolve_legibility(char_dir, cli_mode):
    if cli_mode in ('anterior', 'c2'):
        return cli_mode
    settings_path = os.path.join(char_dir, 'settings.json')
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as sf:
                sdata = json.load(sf)
                if sdata.get('legibility') == 'c2':
                    return 'c2'
        except Exception:
            pass
    return 'anterior'


RUN_STATS = []


def convert_sheet_cropped(png_path, w=SPRITE_W, h=SPRITE_H, dir_shift=None, frame_indices=None, legibility='anterior'):
    im = Image.open(png_path).convert('RGBA')
    if frame_indices is None:
        frame_indices = list(range(8))
    use_c2 = (legibility == 'c2')
    alpha_thresh = 77 if use_c2 else 40
    pixels_all = []
    offsets = []
    bounds = []
    runs_all = []      # uint16 halfwords: per frame block = (bh+1) row offsets, then one (x | len << 8) per opaque run
    run_offsets = []
    for d in range(8):
        dir_offs = []
        dir_bnds = []
        dir_run_offs = []
        shift = dir_shift[d] if dir_shift else 0
        for f in frame_indices:
            cell = im.crop((f * w, d * h, (f + 1) * w, (d + 1) * h))
            buf = [0] * (w * h)
            min_x, max_x = w, -1
            min_y, max_y = h, -1
            for y in range(h):
                sy = y - shift      # content moves by `shift` rows: new row y shows old row y - shift
                for x in range(w):
                    if sy < 0 or sy >= h:
                        r, g, b, a = 0, 0, 0, 0
                    else:
                        r, g, b, a = cell.getpixel((x, sy))
                    if a < alpha_thresh:
                        val = 0
                    else:
                        if use_c2:
                            r5 = (r * 31 + 127) // 255
                            g5 = (g * 31 + 127) // 255
                            b5 = (b * 31 + 127) // 255
                        else:
                            r5 = (r >> 3) & 0x1F
                            g5 = (g >> 3) & 0x1F
                            b5 = (b >> 3) & 0x1F
                        val = r5 | (g5 << 5) | (b5 << 10) | 0x8000
                        if x < min_x: min_x = x
                        if x > max_x: max_x = x
                        if y < min_y: min_y = y
                        if y > max_y: max_y = y
                    buf[y * w + x] = val
            dir_offs.append(len(pixels_all))
            dir_run_offs.append(len(runs_all))
            if max_x < min_x:
                dir_bnds.append((0, 0, 0, 0))
            else:
                bw = max_x - min_x + 1
                bh = max_y - min_y + 1
                dir_bnds.append((min_x, min_y, bw, bh))
                for y in range(min_y, max_y + 1):
                    pixels_all.extend(buf[y * w + min_x:y * w + max_x + 1])
                    if bw & 1:
                        pixels_all.append(0)    # even row pitch: every row starts on a 32-bit boundary
                assert bw <= 255
                # Opaque runs (bit 15 set) per row, x relative to the cropped frame.
                row_runs = []
                for y in range(min_y, max_y + 1):
                    rr = []
                    x = min_x
                    while x <= max_x:
                        if buf[y * w + x] & 0x8000:
                            x0 = x
                            while x <= max_x and (buf[y * w + x] & 0x8000):
                                x += 1
                            rr.append((x0 - min_x) | ((x - x0) << 8))
                        else:
                            x += 1
                    row_runs.append(rr)
                block = []
                pos = bh + 1
                for rr in row_runs:
                    block.append(pos)
                    pos += len(rr)
                block.append(pos)
                for rr in row_runs:
                    block.extend(rr)
                if len(block) & 1:
                    block.append(0)     # keep every block 4-byte aligned
                assert len(block) < 65536
                runs_all.extend(block)
        offsets.append(dir_offs)
        bounds.append(dir_bnds)
        run_offsets.append(dir_run_offs)

    off_lines = ['{\n']
    for d in range(8):
        off_lines.append('    { ' + ', '.join(str(v) for v in offsets[d]) + ' },\n')
    off_lines.append('};\n')

    bnd_lines = ['{\n']
    for d in range(8):
        bnd_lines.append('    { ' + ', '.join('{ %d, %d, %d, %d }' % b for b in bounds[d]) + ' },\n')
    bnd_lines.append('};\n')

    pix_lines = ['{\n']
    if not pixels_all:
        pix_lines.append('    0x0000,\n')
    else:
        for i in range(0, len(pixels_all), 16):
            chunk = ', '.join(f'0x{v:04X}' for v in pixels_all[i:i + 16])
            pix_lines.append(f'    {chunk},\n')
    pix_lines.append('};\n')

    run_off_lines = ['{\n']
    for d in range(8):
        run_off_lines.append('    { ' + ', '.join(str(v) for v in run_offsets[d]) + ' },\n')
    run_off_lines.append('};\n')
    run_lines = ['{\n']
    if not runs_all:
        runs_all = [0]
    for i in range(0, len(runs_all), 16):
        run_lines.append('    ' + ', '.join(str(v) for v in runs_all[i:i + 16]) + ',\n')
    run_lines.append('};\n')
    RUN_STATS.append(len(runs_all) * 2 + 4 * 8 * len(frame_indices))
    return (''.join(off_lines), ''.join(bnd_lines), ''.join(pix_lines),
            ''.join(run_off_lines), ''.join(run_lines))

def emit_runs(out_lines, name, run_offs, run_data, frames_const, comment):
    out_lines.append(f'// {comment}\n')
    out_lines.append(f'const uint16_t g_{name}_runs[] __attribute__((aligned(4))) = ')
    out_lines.append(run_data)
    out_lines.append('\n')
    out_lines.append(f'const uint32_t g_{name}_run_offsets[PLAYER_NUM_DIRS][{frames_const}] = ')
    out_lines.append(run_offs)
    out_lines.append('\n')



STREAM_MAGIC = 0x4E555250   # 'PRUN'


def write_streamed_bin(var_name, fr_pix, fr_offs, fr_bnds, fr_runs, fr_run_offs, sh_data, sh_offs, shb_body):
    """Packs the sheet of a streamed slot (8 dirs x 8 frames) for source/stream_char.c, one record per frame so that
    a single read fetches everything a frame needs. Little endian. Layout:
    header (8 u32: magic, frames, max_record_bytes, 5 spare) | records[64] { u32 file_offset, u16 pix_bytes,
    u16 runs_bytes, u16 shadow_bytes, u16 spare } | frame_bounds u8[256] | shadow_bounds u8[256] | the records' data.
    A record is its pixels (u16, even row pitch), its opaque-run block (u16) and its shadow mask (u8), each padded to
    4 bytes, so every part starts word-aligned in the RAM slot."""
    import struct

    def ints(text):
        return [int(x) for x in re.findall(r'[0-9]+', text)]

    def pad4(b):
        return b + bytes(1) * (-len(b) % 4)

    fo = ints(fr_offs); ro = ints(fr_run_offs); so = ints(sh_offs)
    frame_bounds = ints(fr_bnds); shadow_bounds = ints(shb_body)
    assert len(fo) == len(ro) == len(so) == 64 and len(frame_bounds) == len(shadow_bounds) == 256
    pix = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', fr_pix)]
    runs = ints(fr_runs)
    shadow = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', sh_data)]

    def part(arr, offs, i, fmt):
        end = offs[i + 1] if i < 63 else len(arr)
        chunk = arr[offs[i]:end]
        return pad4(struct.pack('<%d%s' % (len(chunk), fmt), *chunk)), len(chunk) * struct.calcsize(fmt)

    head_bytes = 32 + 64 * 12 + 256 + 256
    recs, data, off, max_rec = [], b'', head_bytes, 0
    for i in range(64):
        pb, pn = part(pix, fo, i, 'H')
        rb, rn = part(runs, ro, i, 'H')
        sb, sn = part(shadow, so, i, 'B')
        rec = pb + rb + sb
        recs.append(struct.pack('<IHHHH', off, pn, rn, sn, 0))
        data += rec
        off += len(rec)
        max_rec = max(max_rec, len(rec))
    rel = STREAMED[var_name]
    path = os.path.join(WT, 'nitrofiles', *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(struct.pack('<8I', STREAM_MAGIC, 64, max_rec, 0, 0, 0, 0, 0) + b''.join(recs)
                + bytes(frame_bounds) + bytes(shadow_bounds) + data)
    print('streamed %s -> %s: %d bytes, largest record %d bytes (STREAM_SLOT_BYTES must be >= this)' % (
        var_name, path, os.path.getsize(path), max_rec))


chars_meta = [
    ('player', 'corazon', 'Corazon Abierto Hero', 340, 4),
    ('charger', 'cireneo', 'Enemy Charger (Knocker)', 310, 5),
    ('ojo', 'ojo', 'El Ojo del Tribunal', 110, 9),
    ('exvoto', 'exvoto', 'Exvoto Walker Enemy', 130, 8),
    # Exvoto clips (DESIGN.md 6.10): each one is a character slot of its own, so the enemy swaps char_id
    # when its pose changes and the renderer needs no special case. Same 40x40 cell as the walk (and the
    # same world scale: characters.json scaleRef + normScale).
    ('exvoto_pray_stand', 'exvoto_pray_stand', 'Exvoto praying standing', 11, 24),
    ('exvoto_pray_kneel', 'exvoto_pray_kneel', 'Exvoto praying kneeling', 27, 14),
    ('exvoto_stand_up', 'exvoto_stand_up', 'Exvoto standing up', 0, 9),
    ('abanderado', 'abanderado', 'El Abanderado', 50, 14),
    ('monaguillo', 'monaguillo', 'Exvoto Monaguillo', 39, 22),
    # Hero crouched walk (DESIGN.md 6.9): a slot of its own like the Exvoto clips; the still pose is one fixed frame of it.
    ('hero_crouch_walk', 'corazon_agachado_andar', 'Hero crouched walking', 0, 8),
    # Exvoto tier "Bebe" (v3 tiers, walkthroughs/arpg-predemo §10): a slot of its own like the Exvoto clips.
    ('exvoto_bebe', 'exvoto_bebe', 'Exvoto Bebe walking', 53, 8),
    # El Campanero de Animas (jefe ARPG): sus 5 clips (80x80) van en NitroFS (tools/generate_campanero_bin.py, source/campanero_sprite.c);
    # este slot solo aporta configuracion, ancla de suelo y municion (ceros), sin pixeles en la EWRAM fija.
    ('campanero', 'campanero', 'El Campanero de Animas', 80, 8),
    # Exvoto tier "Parroco" running (48x48 cell, Mixamo Running): too big for the fixed RAM, so its pixels, runs and
    # shadow masks are not emitted as C: they go to nitrofiles/parroco/run.bin and parroco_run.c loads them once.
    ('exvoto_parroco_run', 'exvoto_parroco_run', 'Exvoto Parroco running', 0, 10),
    # Super Monja (Tripo 9713149f, 56x56 cell, tools/characters/bake_exvoto_super_monja.py): her four clips, streamed too.
    ('exvoto_super_monja', 'exvoto_super_monja', 'Super Monja walking', 39, 8),
    ('exvoto_super_monja_pray_stand', 'exvoto_super_monja_pray_stand', 'Super Monja praying standing', 39, 24),
    ('exvoto_super_monja_pray_kneel', 'exvoto_super_monja_pray_kneel', 'Super Monja praying kneeling', 39, 14),
    ('exvoto_super_monja_stand_up', 'exvoto_super_monja_stand_up', 'Super Monja standing up', 39, 9),
    # Possession by the Super Monja's aura (DESIGN-ARPG s5): the Exvoto and the Monaguillo lie down into the spider form
    # (trans: standing -> spider, played backwards to get up) and scuttle (walk: frames 0-5 burst, 6-7 pause). Streamed too.
    ('exvoto_arana_walk', 'exvoto_arana_walk', 'Exvoto spider walking', 39, 6),
    ('exvoto_arana_trans', 'exvoto_arana_trans', 'Exvoto lying down into the spider', 0, 3),
    ('monaguillo_arana_walk', 'monaguillo_arana_walk', 'Monaguillo spider walking', 39, 6),
    ('monaguillo_arana_trans', 'monaguillo_arana_trans', 'Monaguillo lying down into the spider', 0, 3),
]
STREAMED = {   # slot -> file in nitrofiles/ (read by source/stream_char.c; the slot order of player_sprite.h)
    'exvoto_parroco_run': 'parroco/run.bin',
    'exvoto_super_monja': 'smonja/walk.bin',
    'exvoto_super_monja_pray_stand': 'smonja/pray_stand.bin',
    'exvoto_super_monja_pray_kneel': 'smonja/pray_kneel.bin',
    'exvoto_super_monja_stand_up': 'smonja/stand_up.bin',
    'exvoto_arana_walk': 'arana/exvoto_walk.bin',
    'exvoto_arana_trans': 'arana/exvoto_trans.bin',
    'monaguillo_arana_walk': 'arana/monaguillo_walk.bin',
    'monaguillo_arana_trans': 'arana/monaguillo_trans.bin',
}
SINGLE_FRAME = set()
STUB_NO_PIXELS = {'campanero'}

# Ticks per frame of the Exvoto clips come from the manifest (the lab settings carry the template's).
with open(os.path.join(SRC_ROOT, 'characters.json'), 'r', encoding='utf-8') as _mf:
    MANIFEST = json.load(_mf)['characters']

out_lines = []
out_lines.append('#include "player_sprite.h"\n\n')

char_configs = []
all_anchors = []
all_muzzles = []
for var_name, folder, disp_name, def_spd, def_ticks in chars_meta:
    char_dir = os.path.join(SRC_ROOT, folder)
    settings_path = os.path.join(char_dir, 'settings.json')
    spd, ticks = def_spd, def_ticks
    sw, sh = SPRITE_W, SPRITE_H
    shw, shh = SHADOW_W, SHADOW_H
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as sf:
            sdata = json.load(sf)
            spd = int(sdata.get('speedFixed8_8', def_spd))
            ticks = int(sdata.get('ticksPerFrame', def_ticks))
            if 'frameSize' in sdata:
                parts = str(sdata['frameSize']).split('x')
                sw, sh = int(parts[0]), int(parts[1])
            if 'shadowSize' in sdata:
                shw, shh = int(sdata['shadowSize'][0]), int(sdata['shadowSize'][1])
    if folder.startswith('exvoto') and 'ticksPerFrame' in MANIFEST.get(folder, {}):
        ticks = int(MANIFEST[folder]['ticksPerFrame'])
    if var_name.endswith('_arana_walk') or var_name.endswith('_arana_trans'):
        spd, ticks = def_spd, def_ticks    # the staged settings carry the lab's duration, not the game's
    if var_name == 'charger':
        ticks = 8  # match 37.86 px stride at ENEMY_CHARGER_APPROACH_SPEED (150)
    if var_name == 'ojo':
        spd = 110   # ENEMY_TYPE_SHOOTER speed (gameplay.c), 8.8 fixed = 0.43 px/frame
        ticks = 9   # 8 frames x 9 = 72 game frames per cycle x 0.43 px = 30.9 px, the lab's 31.3 px stride (no magic carpet)
    out_shw = SHADOW_W if shw > SHADOW_W else shw
    out_shh = SHADOW_H if shh > SHADOW_H else shh
    if var_name == 'campanero':
        out_shw = out_shh = 112   # lienzo de sombra propio del jefe (tools/generate_campanero_bin.py SHW)
    char_configs.append((var_name, folder, disp_name, spd, ticks, sw, sh, shw, shh, out_shw, out_shh))

out_lines.append('const CharacterConfig g_characters[NUM_CHARACTERS] = {\n')
for var_name, folder, disp_name, spd, ticks, sw, sh, shw, shh, out_shw, out_shh in char_configs:
    out_lines.append(f'    {{ "{disp_name}", {spd}, {ticks}, {sw}, {sh}, {out_shw}, {out_shh} }},\n')
out_lines.append('};\n\n')

for var_name, folder, disp_name, spd, ticks, sw, sh, shw, shh, out_shw, out_shh in char_configs:
    char_dir = os.path.join(SRC_ROOT, folder)
    png_path = os.path.join(char_dir, 'spritesheet.png')
    h_path = os.path.join(char_dir, 'nds_shadow_anchor.h')

    mask_bytes = (shw * shh) // 2
    anchors, sb, shb_body, mask_body = parse_header(h_path, mask_bytes)
    frame_idx = [0] if var_name in SINGLE_FRAME else None
    if shw > SHADOW_W or frame_idx:
        shb_body, mask_body = crop_shadow_to_80(shb_body, mask_body, shw, shh, frame_idx)
    all_anchors.append(anchors)
    muzzle = [[[0, 0, 0] for _ in range(8)] for _ in range(8)]
    settings_path = os.path.join(char_dir, 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as sf:
            dm = json.load(sf).get('dirMuzzle')
        if dm:
            muzzle = [[[int(v) for v in dm[d][f]] for f in range(8)] for d in range(8)]
    all_muzzles.append(muzzle)

    if var_name in STUB_NO_PIXELS:
        zero_tbl = '{' + chr(10) + ''.join('    { ' + ', '.join('0' for _ in range(8)) + ' },' + chr(10) for _ in range(8)) + '};' + chr(10)
        zero_bnds = '{' + chr(10) + ''.join('    { ' + ', '.join('{ 0, 0, 0, 0 }' for _ in range(8)) + ' },' + chr(10) for _ in range(8)) + '};' + chr(10)
        out_lines.append(f'// {disp_name}: slot sin pixeles en la EWRAM (los fotogramas se leen de NitroFS, source/campanero_sprite.c)\n')
        out_lines.append(f'const uint16_t g_{var_name}_frames[] __attribute__((aligned(4))) = {{ 0 }};\n')
        out_lines.append(f'const uint32_t g_{var_name}_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ' + zero_tbl)
        out_lines.append(f'const uint8_t g_{var_name}_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = ' + zero_bnds)
        out_lines.append(f'const uint16_t g_{var_name}_runs[] __attribute__((aligned(4))) = {{ 0 }};\n')
        out_lines.append(f'const uint32_t g_{var_name}_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ' + zero_tbl)
        out_lines.append(f'const uint8_t g_{var_name}_shadow_masks[] __attribute__((aligned(4))) = {{ 0 }};\n')
        out_lines.append(f'const uint32_t g_{var_name}_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ' + zero_tbl)
        out_lines.append(f'const uint8_t g_{var_name}_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = ' + zero_bnds + '\n')
        continue

    char_mode = resolve_legibility(char_dir, ARGS.legibility)
    fr_offs, fr_bnds, fr_pix, fr_run_offs, fr_runs = convert_sheet_cropped(png_path, sw, sh, frame_indices=frame_idx, legibility=char_mode)
    sheet_mark = len(out_lines)
    out_lines.append(f'// {sw}x{sh} BGR555 frames for {disp_name}, 8 directions x 8 frames (cropped to bounds)\n')
    out_lines.append(f'const uint16_t g_{var_name}_frames[] __attribute__((aligned(4))) = ')
    out_lines.append(fr_pix)
    out_lines.append('\n')
    out_lines.append(f'const uint32_t g_{var_name}_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ')
    out_lines.append(fr_offs)
    out_lines.append('\n')
    out_lines.append(f'const uint8_t g_{var_name}_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = ')
    out_lines.append(fr_bnds)
    out_lines.append('\n')
    if var_name in STREAMED:
        sh_offs, sh_data = crop_shadow_masks(shb_body, mask_body, out_shw, out_shh, frame_idx)
        write_streamed_bin(var_name, fr_pix, fr_offs, fr_bnds, fr_runs, fr_run_offs, sh_data, sh_offs, shb_body)
        del out_lines[sheet_mark:]      # this slot has no C arrays: only the config row, anchors and muzzle tables
        continue
    emit_runs(out_lines, var_name, fr_run_offs, fr_runs, 'PLAYER_NUM_FRAMES',
              f'Opaque runs per row of {disp_name} frames (blit_stride): block = (bh+1) row offsets in halfwords, then x | len << 8')

    sh_offs, sh_data = crop_shadow_masks(shb_body, mask_body, out_shw, out_shh, frame_idx)
    out_lines.append(f'// 4-bit packed animated crisp 3D shadow masks for {disp_name} (8 dirs x 8 frames, cropped to bounds)\n')
    out_lines.append(f'const uint8_t g_{var_name}_shadow_masks[] __attribute__((aligned(4))) = ')
    out_lines.append(sh_data)
    out_lines.append('\n')
    out_lines.append(f'const uint32_t g_{var_name}_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ')
    out_lines.append(sh_offs)
    out_lines.append('\n')

    out_lines.append(f'const uint8_t g_{var_name}_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = {{\n')
    out_lines.append(shb_body)
    out_lines.append('\n};\n\n')

# Charger charge clip (Cireneo bent nearly parallel to the ground): 4 frames (0, 2, 4, 6) at 60x60.
CHARGE_DIR = os.path.join(SRC_ROOT, 'cireneo_charge')
walk_c_anchors, _, _, _ = parse_header(os.path.join(SRC_ROOT, 'cireneo', 'nds_shadow_anchor.h'), (120 * 120) // 2)
chg_anchors, _, chg_shb_body, chg_mask_body = parse_header(os.path.join(CHARGE_DIR, 'nds_shadow_anchor.h'), (120 * 120) // 2)
chg_shift = [walk_c_anchors[d] - chg_anchors[d] for d in range(8)]
chg_frames = [0, 2, 4, 6]
chg_shb_body, chg_mask_body = crop_shadow_120_to_80(chg_shb_body, chg_mask_body, chg_frames)
print('charger charge anchors: walk', walk_c_anchors, 'charge', chg_anchors, 'shift', chg_shift)

chg_mode = resolve_legibility(CHARGE_DIR, ARGS.legibility)
chg_fr_offs, chg_fr_bnds, chg_fr_pix, chg_run_offs, chg_runs = convert_sheet_cropped(os.path.join(CHARGE_DIR, 'spritesheet.png'), 60, 60, chg_shift, chg_frames, legibility=chg_mode)
out_lines.append('// 60x60 BGR555 charge clip of the charger (CHAR_CHARGER), 8 directions x 4 frames (cropped to bounds)\n')
out_lines.append('const uint16_t g_charger_charge_frames[] __attribute__((aligned(4))) = ')
out_lines.append(chg_fr_pix)
out_lines.append('\n')
out_lines.append('const uint32_t g_charger_charge_frame_offsets[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES] = ')
out_lines.append(chg_fr_offs)
out_lines.append('\n')
out_lines.append('const uint8_t g_charger_charge_frame_bounds[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][4] = ')
out_lines.append(chg_fr_bnds)
out_lines.append('\n')
emit_runs(out_lines, 'charger_charge', chg_run_offs, chg_runs, 'CHARGER_CHARGE_NUM_FRAMES', 'Opaque runs of the charger charge clip')

chg_sh_offs, chg_sh_data = crop_shadow_masks(chg_shb_body, chg_mask_body, 80, 80, chg_frames)
out_lines.append('// 4-bit packed shadow masks of the charger charge clip (8 dirs x 4 frames, cropped to bounds)\n')
out_lines.append('const uint8_t g_charger_charge_shadow_masks[] __attribute__((aligned(4))) = ')
out_lines.append(chg_sh_data)
out_lines.append('\n')
out_lines.append('const uint32_t g_charger_charge_shadow_offsets[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES] = ')
out_lines.append(chg_sh_offs)
out_lines.append('\n')

out_lines.append('const uint8_t g_charger_charge_shadow_bounds[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][4] = {\n')
out_lines.append(chg_shb_body)
out_lines.append('\n};\n\n')

# Charger telegraph keyframe (Cireneo crouched with feet planted, frame 6): 1 frame at 60x60.
# Shadow reuses g_charger_charge_shadow_masks[d][0] to stay within the 3.5 MiB EWRAM budget.
TELE_DIR = os.path.join(SRC_ROOT, 'cireneo_telegraph')
tg_anchors, _, _, _ = parse_header(os.path.join(TELE_DIR, 'nds_shadow_anchor.h'), (120 * 120) // 2)
tg_shift = [walk_c_anchors[d] - tg_anchors[d] for d in range(8)]
tg_frames = [6]
print('charger telegraph anchors: walk', walk_c_anchors, 'telegraph', tg_anchors, 'shift', tg_shift)

tg_mode = resolve_legibility(TELE_DIR, ARGS.legibility)
tg_fr_offs, tg_fr_bnds, tg_fr_pix, tg_run_offs, tg_runs = convert_sheet_cropped(os.path.join(TELE_DIR, 'spritesheet.png'), 60, 60, tg_shift, tg_frames, legibility=tg_mode)
out_lines.append('// 60x60 BGR555 telegraph keyframe of the charger (CHAR_CHARGER), 8 directions x 1 frame (cropped to bounds)\n')
out_lines.append('const uint16_t g_charger_telegraph_frames[] __attribute__((aligned(4))) = ')
out_lines.append(tg_fr_pix)
out_lines.append('\n')
out_lines.append('const uint32_t g_charger_telegraph_frame_offsets[PLAYER_NUM_DIRS][CHARGER_TELEGRAPH_NUM_FRAMES] = ')
out_lines.append(tg_fr_offs)
out_lines.append('\n')
out_lines.append('const uint8_t g_charger_telegraph_frame_bounds[PLAYER_NUM_DIRS][CHARGER_TELEGRAPH_NUM_FRAMES][4] = ')
out_lines.append(tg_fr_bnds)
out_lines.append('\n')
emit_runs(out_lines, 'charger_telegraph', tg_run_offs, tg_runs, 'CHARGER_TELEGRAPH_NUM_FRAMES', 'Opaque runs of the charger telegraph keyframe')

# Ojo del Tribunal clips (DESIGN.md 6.10): look (4 frames of the breathing loop) and sentence (6 frames of the
# gesture) at 40x40, with their own muzzle table. The walk is the CHAR_OJO slot (8 frames). Each clip is shifted so
# its feet sit on the walk's ground row (walk_anchor - clip_anchor), like the charger clips.
def filter_shadow_80(shb_body, mask_body, frame_indices):
    rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', shb_body)
    assert len(rows) == 64
    hex_bytes = re.findall(r'0x[0-9A-Fa-f]{2}', mask_body)
    fb = (SHADOW_W * SHADOW_H) // 2
    assert len(hex_bytes) == 64 * fb
    shb, msk = [], []
    for d in range(8):
        shb.append('    {\n')
        for f in frame_indices:
            shb.append('        { %s, %s, %s, %s },\n' % tuple(rows[d * 8 + f]))
            msk.extend(hex_bytes[(d * 8 + f) * fb:(d * 8 + f + 1) * fb])
        shb.append('    },\n')
    return ''.join(shb).rstrip('\n'), ' '.join(msk)


OJO_WALK_ANCHORS, _, _, _ = parse_header(os.path.join(SRC_ROOT, 'ojo', 'nds_shadow_anchor.h'), (112 * 112) // 2)


def sole_row(png_path, frames, w=56, h=56):
    """90th percentile over directions/frames of the lowest opaque row of each cell: the row where the soles touch the floor.
    The lab's ground anchor is estimated per clip and can differ by 1-2 rows between clips of a standing pose and
    a walk, so the clips are aligned on the soles instead (no pop when the Ojo stops walking to look)."""
    im = Image.open(png_path).convert('RGBA')
    rows = []
    for d in range(8):
        for f in frames:
            ys = [y for y in range(h) for x in range(w) if im.getpixel((f * w + x, d * h + y))[3] > 0]
            rows.append(max(ys))
    rows.sort()
    return rows[(len(rows) * 9) // 10]


OJO_WALK_SOLE = sole_row(os.path.join(SRC_ROOT, 'ojo', 'spritesheet.png'), range(8))
OJO_CLIPS = [('ojo_look', 'ojo_look', [0, 2, 4, 6], 'OJO_LOOK_NUM_FRAMES', 'Ojo look (breathing loop)'),
             ('ojo_sentence', 'ojo_sentence', [0, 2, 3, 4, 5, 7], 'OJO_SENTENCE_NUM_FRAMES', 'Ojo sentence (gesture)')]
for cvar, cfolder, cframes, cconst, cdesc in OJO_CLIPS:
    cdir = os.path.join(SRC_ROOT, cfolder)
    c_anchors, _, c_shb, c_mask = parse_header(os.path.join(cdir, 'nds_shadow_anchor.h'), (112 * 112) // 2)
    c_sole = sole_row(os.path.join(cdir, 'spritesheet.png'), cframes)
    c_shift = [OJO_WALK_SOLE - c_sole] * 8
    print(cvar, 'soles: walk', OJO_WALK_SOLE, 'clip', c_sole, 'shift', c_shift, '(lab anchors: walk', OJO_WALK_ANCHORS[0], 'clip', c_anchors[0], ')')
    c_shb, c_mask = crop_shadow_to_80(c_shb, c_mask, 112, 112, cframes)
    c_offs, c_bnds, c_pix, c_roffs, c_runs = convert_sheet_cropped(os.path.join(cdir, 'spritesheet.png'), 56, 56, c_shift, cframes)
    out_lines.append(f'// 56x56 BGR555 {cdesc} clip of the Ojo (CHAR_OJO), 8 directions x {len(cframes)} frames (cropped to bounds)\n')
    out_lines.append(f'const uint16_t g_{cvar}_frames[] __attribute__((aligned(4))) = ')
    out_lines.append(c_pix)
    out_lines.append('\n')
    out_lines.append(f'const uint32_t g_{cvar}_frame_offsets[PLAYER_NUM_DIRS][{cconst}] = ')
    out_lines.append(c_offs)
    out_lines.append('\n')
    out_lines.append(f'const uint8_t g_{cvar}_frame_bounds[PLAYER_NUM_DIRS][{cconst}][4] = ')
    out_lines.append(c_bnds)
    out_lines.append('\n')
    emit_runs(out_lines, cvar, c_roffs, c_runs, cconst, f'Opaque runs of the {cdesc} clip')
    c_so, c_sd = crop_shadow_masks(c_shb, c_mask, SHADOW_W, SHADOW_H, cframes)
    out_lines.append(f'// 4-bit packed shadow masks of the {cdesc} clip (8 dirs x {len(cframes)} frames, cropped to bounds)\n')
    out_lines.append(f'const uint8_t g_{cvar}_shadow_masks[] __attribute__((aligned(4))) = ')
    out_lines.append(c_sd)
    out_lines.append('\n')
    out_lines.append(f'const uint32_t g_{cvar}_shadow_offsets[PLAYER_NUM_DIRS][{cconst}] = ')
    out_lines.append(c_so)
    out_lines.append('\n')
    out_lines.append(f'const uint8_t g_{cvar}_shadow_bounds[PLAYER_NUM_DIRS][{cconst}][4] = {{\n')
    out_lines.append(c_shb)
    out_lines.append('\n};\n\n')
    with open(os.path.join(cdir, 'settings.json'), 'r', encoding='utf-8') as sf:
        c_dm = json.load(sf)['dirMuzzle']
    out_lines.append(f'// {cdesc} muzzle per direction/frame: gx, gy, h (same meaning as g_character_muzzle)\n')
    out_lines.append(f'const int8_t g_{cvar}_muzzle[PLAYER_NUM_DIRS][{cconst}][3] = {{\n')
    for d in range(8):
        out_lines.append('    { ' + ', '.join('{ %d, %d, %d }' % tuple(int(v) for v in c_dm[d][f]) for f in cframes) + ' },\n')
    out_lines.append('};\n\n')

# Hero shot clip (Corazon Abierto, DESIGN.md "Carga y disparo"): a second set for CHAR_HERO only.
# It is the clip rendered by the lab at the walk's world scale (scaleRef + normScale) but in a bigger cell
# (characters.json resolution, e.g. 48x48 vs 40x40) so the arms spread in a cross are not cut. The cell is
# not shifted: the clip has its own ground-anchor table (g_player_shot_ground_anchors) and the engine draws
# it at (feet.x - w/2, feet.y - anchor), so the feet and the horizontal centre stay where the walk has them.
# The lab's shadow canvas is 2x the cell (96x96 here); it is cropped centred to the 80x80 the engine uses.
SHOT_DIR = os.path.join(SRC_ROOT, 'corazon_disparo')
with open(os.path.join(SHOT_DIR, 'settings.json'), 'r', encoding='utf-8') as sf:
    shot_settings = json.load(sf)
shot_w, shot_h = [int(v) for v in str(shot_settings['frameSize']).split('x')]
shot_shw, shot_shh = [int(v) for v in shot_settings['shadowSize']]
with open(os.path.join(WT, 'include', 'player_sprite.h'), 'r', encoding='utf-8') as hf:
    hdr = hf.read()
hdr_w = int(re.search(r'#define HERO_SHOT_SPRITE_W (\d+)', hdr).group(1))
hdr_h = int(re.search(r'#define HERO_SHOT_SPRITE_H (\d+)', hdr).group(1))
assert (hdr_w, hdr_h) == (shot_w, shot_h), (
    f'include/player_sprite.h says HERO_SHOT_SPRITE {hdr_w}x{hdr_h} but the lab rendered {shot_w}x{shot_h}')
assert shot_w % 2 == 0, 'the engine centres the cell with w / 2: use an even width'
shot_anchors, _, shot_shb_body, shot_mask_body = parse_header(os.path.join(SHOT_DIR, 'nds_shadow_anchor.h'), (shot_shw * shot_shh) // 2)
walk_anchors, _, _, _ = parse_header(os.path.join(SRC_ROOT, 'corazon', 'nds_shadow_anchor.h'))
print('hero shot cell %dx%d, anchors: walk' % (shot_w, shot_h), walk_anchors, 'shot', shot_anchors)
assert shot_settings['anchor'][0] == shot_w // 2, 'the shot clip must be centred on the feet horizontally'
if shot_shw > SHADOW_W:
    shot_shb_body, shot_mask_body = crop_shadow_to_80(shot_shb_body, shot_mask_body, shot_shw, shot_shh)
    # Nothing of the shadow may fall outside the 80x80 window (the crop clamps silently otherwise).
    _off = (shot_shw - SHADOW_W) // 2
    for _x, _y, _w, _h in [tuple(int(v) for v in r) for r in re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', ''.join(
            open(os.path.join(SHOT_DIR, 'nds_shadow_anchor.h'), 'r', encoding='utf-8').read().split('shadow_bounds[8][8][4]')[1].split('};')[0]))]:
        if _w and _h:
            assert _off <= _x and _x + _w <= _off + SHADOW_W and _off <= _y and _y + _h <= _off + SHADOW_H, (
                f'hero shot shadow {_x},{_y} {_w}x{_h} is cut by the {SHADOW_W}x{SHADOW_H} crop')
shot_dm = shot_settings['dirMuzzle']
shot_muzzle = [[[int(v) for v in shot_dm[d][f]] for f in range(8)] for d in range(8)]

shot_mode = resolve_legibility(SHOT_DIR, ARGS.legibility)
shot_fr_offs, shot_fr_bnds, shot_fr_pix, shot_run_offs, shot_runs = convert_sheet_cropped(os.path.join(SHOT_DIR, 'spritesheet.png'), shot_w, shot_h, None, legibility=shot_mode)
out_lines.append('// %dx%d BGR555 shot clip of the hero (CHAR_HERO only), 8 directions x 8 frames: f0 arms crossed, f7 collapsed (cropped to bounds)\n' % (shot_w, shot_h))
out_lines.append('const uint16_t g_player_shot_frames[] __attribute__((aligned(4))) = ')
out_lines.append(shot_fr_pix)
out_lines.append('\n')
out_lines.append('const uint32_t g_player_shot_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ')
out_lines.append(shot_fr_offs)
out_lines.append('\n')
out_lines.append('const uint8_t g_player_shot_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = ')
out_lines.append(shot_fr_bnds)
out_lines.append('\n')
out_lines.append('// Ground anchor row (feet) of the shot clip inside its own cell, per direction\n')
out_lines.append('const uint8_t g_player_shot_ground_anchors[PLAYER_NUM_DIRS] = { ' + ', '.join(str(a) for a in shot_anchors) + ' };\n\n')
emit_runs(out_lines, 'player_shot', shot_run_offs, shot_runs, 'PLAYER_NUM_FRAMES', 'Opaque runs of the hero shot clip')

shot_sh_offs, shot_sh_data = crop_shadow_masks(shot_shb_body, shot_mask_body, SHADOW_W, SHADOW_H)
out_lines.append('// 4-bit packed shadow masks of the hero shot clip (8 dirs x 8 frames, cropped to bounds)\n')
out_lines.append('const uint8_t g_player_shot_shadow_masks[] __attribute__((aligned(4))) = ')
out_lines.append(shot_sh_data)
out_lines.append('\n')
out_lines.append('const uint32_t g_player_shot_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ')
out_lines.append(shot_sh_offs)
out_lines.append('\n')

out_lines.append('const uint8_t g_player_shot_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = {\n')
out_lines.append(shot_shb_body)
out_lines.append('\n};\n\n')

out_lines.append('// Hero shot clip muzzle per direction/frame: gx, gy, h (same meaning as g_character_muzzle)\n')
out_lines.append('const int8_t g_hero_shot_muzzle[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3] = {\n')
for d in range(8):
    out_lines.append('    { ' + ', '.join('{ %d, %d, %d }' % tuple(shot_muzzle[d][f]) for f in range(8)) + ' },\n')
out_lines.append('};\n\n')

# Abanderado point clip (CHAR_ABANDERADO): 8 directions x 8 frames at 60x60 (head raised, staff tilted forward).
AB_PT_DIR = os.path.join(SRC_ROOT, 'abanderado_point')
ab_walk_anc, _, _, _ = parse_header(os.path.join(SRC_ROOT, 'abanderado', 'nds_shadow_anchor.h'), (120 * 120) // 2)
ab_pt_anc, _, ab_pt_shb, ab_pt_mask = parse_header(os.path.join(AB_PT_DIR, 'nds_shadow_anchor.h'), (120 * 120) // 2)
ab_pt_shift = [ab_walk_anc[d] - ab_pt_anc[d] for d in range(8)]
ab_pt_shb, ab_pt_mask = crop_shadow_to_80(ab_pt_shb, ab_pt_mask, 120, 120)
ab_pt_mode = resolve_legibility(AB_PT_DIR, ARGS.legibility)
ab_pt_offs, ab_pt_bnds, ab_pt_pix, ab_pt_roffs, ab_pt_runs = convert_sheet_cropped(
    os.path.join(AB_PT_DIR, 'spritesheet.png'), 60, 60, ab_pt_shift, legibility=ab_pt_mode)
out_lines.append('// 60x60 BGR555 point clip of El Abanderado (CHAR_ABANDERADO), 8 directions x 8 frames (cropped to bounds)\n')
out_lines.append('const uint16_t g_abanderado_point_frames[] __attribute__((aligned(4))) = ')
out_lines.append(ab_pt_pix)
out_lines.append('\n')
out_lines.append('const uint32_t g_abanderado_point_frame_offsets[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES] = ')
out_lines.append(ab_pt_offs)
out_lines.append('\n')
out_lines.append('const uint8_t g_abanderado_point_frame_bounds[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES][4] = ')
out_lines.append(ab_pt_bnds)
out_lines.append('\n')
emit_runs(out_lines, 'abanderado_point', ab_pt_roffs, ab_pt_runs, 'ABANDERADO_POINT_NUM_FRAMES',
          'Opaque runs of the Abanderado point clip')
ab_pt_so, ab_pt_sd = crop_shadow_masks(ab_pt_shb, ab_pt_mask, SHADOW_W, SHADOW_H)
out_lines.append('// 4-bit packed shadow masks of the Abanderado point clip (8 dirs x 8 frames, cropped to bounds)\n')
out_lines.append('const uint8_t g_abanderado_point_shadow_masks[] __attribute__((aligned(4))) = ')
out_lines.append(ab_pt_sd)
out_lines.append('\n')
out_lines.append('const uint32_t g_abanderado_point_shadow_offsets[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES] = ')
out_lines.append(ab_pt_so)
out_lines.append('\n')
out_lines.append('const uint8_t g_abanderado_point_shadow_bounds[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES][4] = {\n')
out_lines.append(ab_pt_shb)
out_lines.append('\n};\n\n')

out_lines.append('const uint8_t g_character_ground_anchors[NUM_CHARACTERS][PLAYER_NUM_DIRS] = {\n')
for anc in all_anchors:
    out_lines.append('    { ' + ', '.join(str(x) for x in anc) + ' },\n')
out_lines.append('};\n\n')

out_lines.append('// Weapon muzzle per character/direction/frame: gx, gy, h in sprite pixels relative to the ground anchor (zeros = no weapon)\n')
out_lines.append('const int8_t g_character_muzzle[NUM_CHARACTERS][PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3] = {\n')
for muzzle in all_muzzles:
    out_lines.append('    {\n')
    for d in range(8):
        out_lines.append('        { ' + ', '.join('{ %d, %d, %d }' % tuple(muzzle[d][f]) for f in range(8)) + ' },\n')
    out_lines.append('    },\n')
out_lines.append('};\n\n')

for tbl, suffix in (
    ('const uint16_t * g_character_frames[NUM_CHARACTERS]', 'frames'),
    ('const uint32_t (* g_character_frame_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES]', 'frame_offsets'),
    ('const uint8_t (* g_character_frame_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4]', 'frame_bounds'),
    ('const uint16_t * g_character_runs[NUM_CHARACTERS]', 'runs'),
    ('const uint32_t (* g_character_run_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES]', 'run_offsets'),
    ('const uint8_t * g_character_shadow_masks[NUM_CHARACTERS]', 'shadow_masks'),
    ('const uint32_t (* g_character_shadow_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES]', 'shadow_offsets'),
    ('const uint8_t (* g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4]', 'shadow_bounds'),
):
    out_lines.append(f'{tbl} = {{\n')
    out_lines.append(',\n'.join(('    0' if c[0] in STREAMED else f'    g_{c[0]}_{suffix}') for c in char_configs) + '\n')
    out_lines.append('};\n\n')

out_path = os.path.join(WT, 'source/player_sprite.c')
with open(out_path, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print('Opaque-run tables: %d bytes (runs + offsets)' % sum(RUN_STATS))
print('Generated source/player_sprite.c successfully! Size:', os.path.getsize(out_path), 'bytes')
