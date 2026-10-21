import os, re, json
from PIL import Image

WT = '.worktrees/asset-refresh'

def parse_header(h_path):
    with open(h_path) as f:
        text = f.read()
    m_anc = re.search(r'g_\w+_ground_anchors\[8\]\s*=\s*\{([^}]+)\};', text)
    anchors = [int(x.strip()) for x in m_anc.group(1).split(',') if x.strip()]
    m_sb = re.search(r'g_\w+_sprite_bounds\[8\]\[4\]\s*=\s*\{([^;]+)\};', text)
    sb_rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', m_sb.group(1))
    sprite_bounds = [[int(x) for x in r] for r in sb_rows]
    m_shb = re.search(r'g_\w+_shadow_bounds\[8\]\[4\]\s*=\s*\{([^;]+)\};', text)
    shb_rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}', m_shb.group(1))
    shadow_bounds = [[int(x) for x in r] for r in shb_rows]
    m_mask = re.search(r'g_\w+_shadow_masks\[8\]\[4608\][^{]+\{([\s\S]+?)\n\};', text)
    mask_body = m_mask.group(1)
    return anchors, sprite_bounds, shadow_bounds, mask_body

def convert_sheet(png_path, w=48, h=48):
    im = Image.open(png_path).convert('RGBA')
    lines = []
    lines.append('{\n')
    for d in range(8):
        lines.append(f'    // Direction {d}\n    {{\n')
        for f in range(8):
            lines.append(f'        // Frame {f}\n        {{\n')
            cell = im.crop((f * w, d * h, (f + 1) * w, (d + 1) * h))
            row_data = []
            for y in range(h):
                for x in range(w):
                    r, g, b, a = cell.getpixel((x, y))
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

# Characters config: (var_name, folder, disp_name, spd, ticks)
chars = [
    ('player', 'marine', 'Space Marine Hero', 406, 4),
    ('charger', 'charger', 'Enemy Charger (Knocker)', 373, 5),
    ('necron', 'necron', 'Necron Shooter Enemy', 461, 4),
]

out_lines = []
out_lines.append('#include "player_sprite.h"\n\n')
out_lines.append('const CharacterConfig g_characters[NUM_CHARACTERS] = {\n')
for var_name, folder, disp_name, spd, ticks in chars:
    out_lines.append(f'    {{ "{disp_name}", {spd}, {ticks} }},\n')
out_lines.append('};\n\n')

# Convert each character
for var_name, folder, disp_name, spd, ticks in chars:
    char_dir = os.path.join(WT, 'assets/sprites/characters', folder)
    png_path = os.path.join(char_dir, 'spritesheet.png')
    h_path = os.path.join(char_dir, 'nds_shadow_anchor.h')
    
    anchors, sb, shb, mask_body = parse_header(h_path)
    
    # Frames
    out_lines.append(f'// 48x48 BGR555 frames for {disp_name}, 8 directions x 8 frames\n')
    out_lines.append(f'const uint16_t g_{var_name}_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H] __attribute__((aligned(4))) = ')
    out_lines.append(convert_sheet(png_path, 48, 48))
    out_lines.append('\n')
    
    # Shadows
    out_lines.append(f'// 4-bit packed shadow masks for {disp_name}\n')
    out_lines.append(f'const uint8_t g_{var_name}_shadow_masks[PLAYER_NUM_DIRS][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] __attribute__((aligned(4))) = {{\n')
    out_lines.append(mask_body)
    out_lines.append('\n};\n\n')
    
    # Shadow bounds
    out_lines.append(f'const uint8_t g_{var_name}_shadow_bounds[PLAYER_NUM_DIRS][4] = {{\n')
    for row in shb:
        out_lines.append(f'    {{ {row[0]}, {row[1]}, {row[2]}, {row[3]} }},\n')
    out_lines.append('};\n\n')

# Arrays table
out_lines.append('const uint16_t (* const g_character_frames[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H] = {\n')
out_lines.append('    g_player_frames,\n')
out_lines.append('    g_charger_frames,\n')
out_lines.append('    g_necron_frames\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t (* const g_character_shadow_masks[NUM_CHARACTERS])[PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2] = {\n')
out_lines.append('    g_player_shadow_masks,\n')
out_lines.append('    g_charger_shadow_masks,\n')
out_lines.append('    g_necron_shadow_masks\n')
out_lines.append('};\n\n')

out_lines.append('const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[4] = {\n')
out_lines.append('    g_player_shadow_bounds,\n')
out_lines.append('    g_charger_shadow_bounds,\n')
out_lines.append('    g_necron_shadow_bounds\n')
out_lines.append('};\n')

out_path = os.path.join(WT, 'source/player_sprite.c')
with open(out_path, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print('Generated source/player_sprite.c successfully! Size:', os.path.getsize(out_path), 'bytes')
