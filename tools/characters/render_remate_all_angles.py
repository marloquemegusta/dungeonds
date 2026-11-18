"""Renderiza los 5 angulos unicos (az = 90, 45, 0, -45, -90) de Exvoto y Cireneo en Blender
y genera las carpetas de fotogramas 1x + angles.json para generate_remate_sprites.py.

Mapeo de direcciones (DIR_SOUTH=0 .. DIR_SOUTHEAST=7):
  dir 0 (South, hero viene de N):  az =  90, mirror = 0
  dir 1 (SW,    hero viene de NE): az =  45, mirror = 1
  dir 2 (West,  hero viene de E):  az =   0, mirror = 1
  dir 3 (NW,    hero viene de SE): az = -45, mirror = 1
  dir 4 (North, hero viene de S):  az = -90, mirror = 0
  dir 5 (NE,    hero viene de SW): az = -45, mirror = 0
  dir 6 (East,  hero viene de W):  az =   0, mirror = 0
  dir 7 (SE,    hero viene de NW): az =  45, mirror = 0
"""
import json
import math
import os
import shutil
import subprocess
import sys
from PIL import Image

WT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLENDER = r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
OUT_BASE = os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', 'angles')
SCRATCH = os.path.join(WT, 'walkthroughs', 'remate-exvoto', 'assets', '_tmp_angles')

UNIQUE_ANGLES = [
    (0, 90),
    (1, 135),
    (2, 180),
    (3, -135),
    (4, -90),
    (5, -45),
    (6, 0),
    (7, 45),
]

DIR_SOURCE = {
    0: (0, 90, False),
    1: (1, 135, False),
    2: (2, 180, False),
    3: (3, -135, False),
    4: (4, -90, False),
    5: (5, -45, False),
    6: (6, 0, False),
    7: (7, 45, False),
}


def proj(P, center, az_deg, elev_deg, ortho_scale, cw, ch):
    a, e = math.radians(az_deg), math.radians(elev_deg)
    dx, dy, dz = P[0] - center[0], P[1] - center[1], P[2] - center[2]
    u = dx * math.cos(a) + dy * math.sin(a)
    v = -dx * math.sin(a) * math.sin(e) + dy * math.cos(a) * math.sin(e) + dz * math.cos(e)
    return cw * (0.5 + u / ortho_scale), ch * (0.5 - v / (ortho_scale * ch / cw))


def run(cmd, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    print('RUN:', ' '.join(cmd), flush=True)
    subprocess.check_call(cmd, env=e)


def render_exvoto():
    ex_script = os.path.join(WT, 'tools', 'characters', 'ds_remate_exvoto.py')
    post_script = os.path.join(WT, 'tools', 'characters', 'ds_remate_exvoto_post.py')
    for d, az in UNIQUE_ANGLES:
        tag = f'exvoto_d{d}'
        raw_out = os.path.join(SCRATCH, tag)
        post_out = os.path.join(SCRATCH, tag + '_post')
        dst_dir = os.path.join(OUT_BASE, tag)
        if os.path.exists(raw_out):
            shutil.rmtree(raw_out)
        os.makedirs(raw_out, exist_ok=True)
        os.makedirs(post_out, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)
        run([BLENDER, '-b', '--factory-startup', '-P', ex_script, '--', WT, raw_out, 'A', 'all'],
            env={'DBG_AZ': str(az), 'DBG_ZOOM': '0.70175'})
        run([sys.executable, post_script, os.path.join(raw_out, 'ds_exvoto_A', 'raw'), post_out, 'A'])
        src_frames = os.path.join(post_out, 'ds_exvoto_A')
        for i in range(12):
            im = Image.open(os.path.join(src_frames, f'f{i:02d}.png')).convert('RGBA')
            if im.size == (64, 64):
                im.save(os.path.join(dst_dir, f'f{i:02d}.png'))
            else:
                canvas = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                pad_y = (64 - im.height) // 2
                canvas.paste(im, (0, pad_y))
                canvas.save(os.path.join(dst_dir, f'f{i:02d}.png'))


def render_cireneo():
    cir_script = os.path.join(WT, 'tools', 'characters', 'ds_remate_cireneo.py')
    sheet_script = os.path.join(WT, 'tools', 'characters', 'ds_remate_cireneo_sheet.py')
    for d, az in UNIQUE_ANGLES:
        tag = f'cireneo_d{d}'
        raw_out = os.path.join(SCRATCH, tag)
        dst_dir = os.path.join(OUT_BASE, tag)
        if os.path.exists(raw_out):
            shutil.rmtree(raw_out)
        os.makedirs(raw_out, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)
        cx = '-0.10' if d in (1, 2, 3) else '-0.20'
        run([BLENDER, '-b', '--factory-startup', '-P', cir_script, '--', WT, raw_out, 'A', 'all'],
            env={'REMATE_AZ': str(az), 'REMATE_CX': cx, 'REMATE_CY': '0.0', 'REMATE_PPM': '56.4'})
        run([sys.executable, sheet_script, raw_out, dst_dir, '-', '-'])


def write_meta():
    meta = {'exvoto': [], 'cireneo': []}
    for d in range(8):
        src_d, az, mirror = DIR_SOURCE[d]
        # Exvoto: 64x50 padded +7 vertically into 64x64 at 38.0 px/m
        ex_ortho = 64.0 / 38.0
        hx, hy = proj((-0.30, 0, 0), (0.01, 0, 0.46), az, 30.0, ex_ortho, 64, 50)
        ex, ey = proj((0.0, 0, 0), (0.01, 0, 0.46), az, 30.0, ex_ortho, 64, 50)
        hy += 7
        ey += 7
        if mirror:
            hx = 64 - hx
            ex = 64 - ex
        ax, ay = int(round(hx)), int(round(hy))
        edx, edy = int(round(ex - hx)), int(round(ey - hy))
        sx, sy = int(round((hx + ex) * 0.5)), int(round((hy + ey) * 0.5))
        meta['exvoto'].append({
            'dir': d, 'src_dir': src_d, 'mirror': mirror,
            'anchor_x': ax, 'anchor_y': ay,
            'enemy_dx': edx, 'enemy_dy': edy,
            'shadow_cx': sx, 'shadow_cy': sy,
        })

        # Cireneo: 80x80 at 56.4 px/m
        cir_cx = -0.10 if d in (1, 2, 3) else -0.20
        cir_ortho = 80.0 / 56.4
        hx, hy = proj((-0.62, 0, 0), (cir_cx, 0.0, 0.30), az, 30.0, cir_ortho, 80, 80)
        ex, ey = proj((0.0, 0, 0), (cir_cx, 0.0, 0.30), az, 30.0, cir_ortho, 80, 80)
        if mirror:
            hx = 80 - hx
            ex = 80 - ex
        ax, ay = int(round(hx)), int(round(hy))
        edx, edy = int(round(ex - hx)), int(round(ey - hy))
        sx, sy = int(round((hx + ex) * 0.5)), int(round((hy + ey) * 0.5))
        meta['cireneo'].append({
            'dir': d, 'src_dir': src_d, 'mirror': mirror,
            'anchor_x': ax, 'anchor_y': ay,
            'enemy_dx': edx, 'enemy_dy': edy,
            'shadow_cx': sx, 'shadow_cy': sy,
        })

    os.makedirs(OUT_BASE, exist_ok=True)
    with open(os.path.join(OUT_BASE, 'angles.json'), 'w') as f:
        json.dump(meta, f, indent=2)
    print('WROTE angles.json')


if __name__ == '__main__':
    os.makedirs(OUT_BASE, exist_ok=True)
    render_exvoto()
    render_cireneo()
    write_meta()
    if os.path.exists(SCRATCH):
        shutil.rmtree(SCRATCH)
    print('ALL ANGLES DONE')
