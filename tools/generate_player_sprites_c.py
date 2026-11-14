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


def crop_shadow_120_to_80(shb_body, mask_body, frame_indices=None):
    """Crop 120x120 shadow bounds and 4-bit packed masks to 80x80 centered at (60, 60)."""
    if frame_indices is None:
        frame_indices = list(range(8))
    rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', shb_body)
    assert len(rows) == 64, f'Expected 64 shadow_bounds, got {len(rows)}'
    shb_out = []
    for d in range(8):
        shb_out.append('    {\n')
        for f in frame_indices:
            x, y, w, h = [int(v) for v in rows[d * 8 + f]]
            nx = max(0, x - 20)
            ny = max(0, y - 20)
            shb_out.append(f'        {{ {nx}, {ny}, {w}, {h} }},\n')
        shb_out.append('    },\n')

    hex_bytes = [int(b, 16) for b in re.findall(r'0x[0-9A-Fa-f]{2}', mask_body)]
    frame_bytes = (120 * 120) // 2
    assert len(hex_bytes) == 64 * frame_bytes, f'Expected {64 * frame_bytes} mask bytes, got {len(hex_bytes)}'
    mask_out = []
    for d in range(8):
        mask_out.append('    {\n')
        for f in frame_indices:
            src = hex_bytes[(d * 8 + f) * frame_bytes:(d * 8 + f + 1) * frame_bytes]
            cropped = []
            for y in range(20, 100):
                row_off = y * 60
                cropped.extend(src[row_off + 10:row_off + 50])
            mask_out.append('        {\n')
            for i in range(0, len(cropped), 16):
                chunk = ', '.join(f'0x{b:02X}' for b in cropped[i:i + 16])
                mask_out.append(f'            {chunk},\n')
            mask_out.append('        },\n')
        mask_out.append('    },\n')
    return ''.join(shb_out).rstrip('\n'), ''.join(mask_out).rstrip('\n')

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


chars_meta = [
    ('player', 'corazon', 'Corazon Abierto Hero', 340, 4),
    ('charger', 'cireneo', 'Enemy Charger (Knocker)', 310, 5),
    ('necron', 'necron', 'Necron Shooter Enemy', 385, 4),
    ('skeleton', 'skeleton', 'Skeleton Walker Enemy', 39, 22),
]

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
    if var_name == 'charger':
        ticks = 8  # match 37.86 px stride at ENEMY_CHARGER_APPROACH_SPEED (150)
    out_shw = SHADOW_W if shw == 120 else shw
    out_shh = SHADOW_H if shh == 120 else shh
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
    if shw == 120:
        shb_body, mask_body = crop_shadow_120_to_80(shb_body, mask_body)
    all_anchors.append(anchors)
    muzzle = [[[0, 0, 0] for _ in range(8)] for _ in range(8)]
    settings_path = os.path.join(char_dir, 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as sf:
            dm = json.load(sf).get('dirMuzzle')
        if dm:
            muzzle = [[[int(v) for v in dm[d][f]] for f in range(8)] for d in range(8)]
    all_muzzles.append(muzzle)

    char_mode = resolve_legibility(char_dir, ARGS.legibility)
    fr_offs, fr_bnds, fr_pix, fr_run_offs, fr_runs = convert_sheet_cropped(png_path, sw, sh, legibility=char_mode)
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
    emit_runs(out_lines, var_name, fr_run_offs, fr_runs, 'PLAYER_NUM_FRAMES',
              f'Opaque runs per row of {disp_name} frames (blit_stride): block = (bh+1) row offsets in halfwords, then x | len << 8')

    sh_offs, sh_data = crop_shadow_masks(shb_body, mask_body, out_shw, out_shh)
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

# Hero shot clip (Corazon Abierto, DESIGN.md "Carga y disparo"): a second set for CHAR_HERO only.
# It is the clip rendered by the lab with the walk's settings. Its ground line was 1 px lower
# (anchor 34 vs 33 in the walk), so each direction is shifted up by walk_anchor - shot_anchor rows:
# the feet then sit on the same row as in the walk and the walk's ground anchor table serves both.
SHOT_DIR = os.path.join(SRC_ROOT, 'corazon_disparo')
walk_anchors, _, _, _ = parse_header(os.path.join(SRC_ROOT, 'corazon', 'nds_shadow_anchor.h'))
shot_anchors, _, shot_shb_body, shot_mask_body = parse_header(os.path.join(SHOT_DIR, 'nds_shadow_anchor.h'))
shot_shift = [walk_anchors[d] - shot_anchors[d] for d in range(8)]
print('hero shot anchors: walk', walk_anchors, 'shot', shot_anchors, 'shift', shot_shift)
with open(os.path.join(SHOT_DIR, 'settings.json'), 'r', encoding='utf-8') as sf:
    shot_dm = json.load(sf)['dirMuzzle']
shot_muzzle = [[[int(v) for v in shot_dm[d][f]] for f in range(8)] for d in range(8)]

shot_mode = resolve_legibility(SHOT_DIR, ARGS.legibility)
shot_fr_offs, shot_fr_bnds, shot_fr_pix, shot_run_offs, shot_runs = convert_sheet_cropped(os.path.join(SHOT_DIR, 'spritesheet.png'), SPRITE_W, SPRITE_H, shot_shift, legibility=shot_mode)
out_lines.append('// 40x40 BGR555 shot clip of the hero (CHAR_HERO only), 8 directions x 8 frames: f0 arms crossed, f7 collapsed (cropped to bounds)\n')
out_lines.append('const uint16_t g_player_shot_frames[] __attribute__((aligned(4))) = ')
out_lines.append(shot_fr_pix)
out_lines.append('\n')
out_lines.append('const uint32_t g_player_shot_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES] = ')
out_lines.append(shot_fr_offs)
out_lines.append('\n')
out_lines.append('const uint8_t g_player_shot_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = ')
out_lines.append(shot_fr_bnds)
out_lines.append('\n')
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

out_lines.append('const uint16_t * const g_character_frames[NUM_CHARACTERS] = {\n')
out_lines.append('    g_player_frames,\n')
out_lines.append('    g_charger_frames,\n')
out_lines.append('    g_necron_frames,\n    g_skeleton_frames\n')
out_lines.append('};\n\n')

out_lines.append('const uint32_t (* const g_character_frame_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES] = {\n')
out_lines.append('    g_player_frame_offsets,\n')
out_lines.append('    g_charger_frame_offsets,\n')
out_lines.append('    g_necron_frame_offsets,\n    g_skeleton_frame_offsets\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t (* const g_character_frame_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4] = {\n')
out_lines.append('    g_player_frame_bounds,\n')
out_lines.append('    g_charger_frame_bounds,\n')
out_lines.append('    g_necron_frame_bounds,\n    g_skeleton_frame_bounds\n')
out_lines.append('};\n\n')

out_lines.append('const uint16_t * const g_character_runs[NUM_CHARACTERS] = {\n')
out_lines.append('    g_player_runs,\n')
out_lines.append('    g_charger_runs,\n')
out_lines.append('    g_necron_runs,\n    g_skeleton_runs\n')
out_lines.append('};\n\n')

out_lines.append('const uint32_t (* const g_character_run_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES] = {\n')
out_lines.append('    g_player_run_offsets,\n')
out_lines.append('    g_charger_run_offsets,\n')
out_lines.append('    g_necron_run_offsets,\n    g_skeleton_run_offsets\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t * const g_character_shadow_masks[NUM_CHARACTERS] = {\n')
out_lines.append('    g_player_shadow_masks,\n')
out_lines.append('    g_charger_shadow_masks,\n')
out_lines.append('    g_necron_shadow_masks,\n    g_skeleton_shadow_masks\n')
out_lines.append('};\n\n')

out_lines.append('const uint32_t (* const g_character_shadow_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES] = {\n')
out_lines.append('    g_player_shadow_offsets,\n')
out_lines.append('    g_charger_shadow_offsets,\n')
out_lines.append('    g_necron_shadow_offsets,\n    g_skeleton_shadow_offsets\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4] = {\n')
out_lines.append('    g_player_shadow_bounds,\n')
out_lines.append('    g_charger_shadow_bounds,\n')
out_lines.append('    g_necron_shadow_bounds,\n    g_skeleton_shadow_bounds\n')
out_lines.append('};\n')

out_path = os.path.join(WT, 'source/player_sprite.c')
with open(out_path, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print('Opaque-run tables: %d bytes (runs + offsets)' % sum(RUN_STATS))
print('Generated source/player_sprite.c successfully! Size:', os.path.getsize(out_path), 'bytes')
