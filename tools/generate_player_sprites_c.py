import os, re, json, argparse
from PIL import Image

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parser = argparse.ArgumentParser()
parser.add_argument('--src', default=os.path.join(WT, 'assets/sprites/characters'))
ARGS = parser.parse_args()
SRC_ROOT = os.path.abspath(ARGS.src)
SPRITE_W = 40
SPRITE_H = 40
SHADOW_W = 80
SHADOW_H = 80
MASK_BYTES = (SHADOW_W * SHADOW_H) // 2

def parse_header(h_path):
    with open(h_path, 'r', encoding='utf-8') as f:
        text = f.read()
    m_anc = re.search(r'g_\w+_ground_anchors\[8\]\s*=\s*\{([^}]+)\};', text)
    anchors = [int(x.strip()) for x in m_anc.group(1).split(',') if x.strip()]
    m_sb = re.search(r'g_\w+_sprite_bounds\[8\]\[4\]\s*=\s*\{([^;]+)\};', text)
    sb_rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', m_sb.group(1))
    sprite_bounds = [[int(x) for x in r] for r in sb_rows]
    m_shb = re.search(r'g_\w+_shadow_bounds\[8\]\[8\]\[4\]\s*=\s*\{([\s\S]+?)\n\};', text)
    shb_body = m_shb.group(1)
    m_mask = re.search(rf'g_\w+_shadow_masks\[8\]\[8\]\[{MASK_BYTES}\][^{{]+\{{([\s\S]+?)\n\}};', text)
    mask_body = m_mask.group(1)
    return anchors, sprite_bounds, shb_body, mask_body

def convert_sheet(png_path, w=SPRITE_W, h=SPRITE_H, dir_shift=None):
    im = Image.open(png_path).convert('RGBA')
    lines = []
    lines.append('{\n')
    for d in range(8):
        lines.append(f'    // Direction {d}\n    {{\n')
        for f in range(8):
            lines.append(f'        // Frame {f}\n        {{\n')
            cell = im.crop((f * w, d * h, (f + 1) * w, (d + 1) * h))
            shift = dir_shift[d] if dir_shift else 0
            row_data = []
            for y in range(h):
                sy = y - shift      # content moves by `shift` rows: new row y shows old row y - shift
                for x in range(w):
                    if sy < 0 or sy >= h:
                        r, g, b, a = 0, 0, 0, 0
                    else:
                        r, g, b, a = cell.getpixel((x, sy))
                    if a < 40:
                        val = 0
                    else:
                        r5 = (r >> 3) & 0x1F
                        g5 = (g >> 3) & 0x1F
                        b5 = (b >> 3) & 0x1F
                        val = r5 | (g5 << 5) | (b5 << 10) | 0x8000
                    row_data.append(f'0x{val:04X}')
            for i in range(0, len(row_data), 16):
                chunk = ', '.join(row_data[i:i+16])
                lines.append(f'            {chunk},\n')
            lines.append('        },\n')
        lines.append('    },\n')
    lines.append('};\n')
    return ''.join(lines)

chars_meta = [
    ('player', 'corazon', 'Corazon Abierto Hero', 340, 4),
    ('charger', 'charger', 'Enemy Charger (Knocker)', 310, 5),
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
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as sf:
            sdata = json.load(sf)
            spd = int(sdata.get('speedFixed8_8', def_spd))
            ticks = int(sdata.get('ticksPerFrame', def_ticks))
    char_configs.append((var_name, folder, disp_name, spd, ticks))

out_lines.append('const CharacterConfig g_characters[NUM_CHARACTERS] = {\n')
for var_name, folder, disp_name, spd, ticks in char_configs:
    out_lines.append(f'    {{ "{disp_name}", {spd}, {ticks} }},\n')
out_lines.append('};\n\n')

for var_name, folder, disp_name, spd, ticks in char_configs:
    char_dir = os.path.join(SRC_ROOT, folder)
    png_path = os.path.join(char_dir, 'spritesheet.png')
    h_path = os.path.join(char_dir, 'nds_shadow_anchor.h')

    anchors, sb, shb_body, mask_body = parse_header(h_path)
    all_anchors.append(anchors)
    muzzle = [[[0, 0, 0] for _ in range(8)] for _ in range(8)]
    settings_path = os.path.join(char_dir, 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as sf:
            dm = json.load(sf).get('dirMuzzle')
        if dm:
            muzzle = [[[int(v) for v in dm[d][f]] for f in range(8)] for d in range(8)]
    all_muzzles.append(muzzle)

    out_lines.append(f'// {SPRITE_W}x{SPRITE_H} BGR555 frames for {disp_name}, 8 directions x 8 frames\n')
    out_lines.append(f'const uint16_t g_{var_name}_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H] __attribute__((aligned(4))) = ')
    out_lines.append(convert_sheet(png_path, SPRITE_W, SPRITE_H))
    out_lines.append('\n')

    out_lines.append(f'// 4-bit packed animated crisp 3D shadow masks for {disp_name} (8 dirs x 8 frames)\n')
    out_lines.append(f'const uint8_t g_{var_name}_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] __attribute__((aligned(4))) = {{\n')
    out_lines.append(mask_body)
    out_lines.append('\n};\n\n')

    out_lines.append(f'const uint8_t g_{var_name}_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4] = {{\n')
    out_lines.append(shb_body)
    out_lines.append('\n};\n\n')

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

out_lines.append('// 40x40 BGR555 shot clip of the hero (CHAR_HERO only), 8 directions x 8 frames: f0 arms crossed, f7 collapsed\n')
out_lines.append('const uint16_t g_player_shot_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H] __attribute__((aligned(4))) = ')
out_lines.append(convert_sheet(os.path.join(SHOT_DIR, 'spritesheet.png'), SPRITE_W, SPRITE_H, shot_shift))
out_lines.append('\n')

out_lines.append('// 4-bit packed shadow masks of the hero shot clip (8 dirs x 8 frames)\n')
out_lines.append('const uint8_t g_player_shot_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] __attribute__((aligned(4))) = {\n')
out_lines.append(shot_mask_body)
out_lines.append('\n};\n\n')

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

out_lines.append('const uint16_t (* const g_character_frames[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H] = {\n')
out_lines.append('    g_player_frames,\n')
out_lines.append('    g_charger_frames,\n')
out_lines.append('    g_necron_frames,\n    g_skeleton_frames\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t (* const g_character_shadow_masks[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] = {\n')
out_lines.append('    g_player_shadow_masks,\n')
out_lines.append('    g_charger_shadow_masks,\n')
out_lines.append('    g_necron_shadow_masks,\n    g_skeleton_shadow_masks\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4] = {\n')
out_lines.append('    g_player_shadow_bounds,\n')
out_lines.append('    g_charger_shadow_bounds,\n')
out_lines.append('    g_necron_shadow_bounds,\n    g_skeleton_shadow_bounds\n')
out_lines.append('};\n')

out_path = os.path.join(WT, 'source/player_sprite.c')
with open(out_path, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print('Generated source/player_sprite.c successfully! Size:', os.path.getsize(out_path), 'bytes')
