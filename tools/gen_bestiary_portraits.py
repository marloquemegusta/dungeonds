#!/usr/bin/env python3
"""
tools/gen_bestiary_portraits.py - Packs high-res 160x160 character portraits into NitroFS binaries.
Generates nitrofiles/bestiary/<id>.bin for corazon, exvoto, cireneo, and ojo.
Each binary contains an 8-direction index table, shared 256-color BGR555 palette,
and per-direction cropped frames with animation bounding box union for zero-jitter centering.
"""

import os
import struct
import sys
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
SPRITES_BASE = os.path.join(PROJECT_ROOT, 'assets', 'sprites', 'bestiary')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'nitrofiles', 'bestiary')

MAGIC = 0x4251
CANVAS_W = 160
CANVAS_H = 160
NUM_DIRS = 8
ALPHA_THRESHOLD = 77

CHARACTERS = [
    {
        'id': 'corazon',
        'clips': [
            ('corazon_disparo', list(range(8)))
        ]
    },
    {
        'id': 'exvoto',
        'clips': [
            ('exvoto_walk', list(range(8)))
        ]
    },
    {
        'id': 'cireneo',
        'clips': [
            ('cireneo_walk', list(range(8)))
        ]
    },
    {
        'id': 'ojo',
        'clips': [
            ('ojo_look', list(range(4)))
        ]
    }
]

def load_clip_frames(clip_name, frame_indices):
    path = os.path.join(SPRITES_BASE, clip_name, 'spritesheet.png')
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing spritesheet: {path}")
    sheet = Image.open(path)
    dirs = {d: [] for d in range(NUM_DIRS)}
    for d in range(NUM_DIRS):
        for f in frame_indices:
            box = (f * CANVAS_W, d * CANVAS_H, (f + 1) * CANVAS_W, (d + 1) * CANVAS_H)
            dirs[d].append(sheet.crop(box))
    return dirs

def build_portrait_binary(char_info):
    char_id = char_info['id']
    clips = char_info['clips']

    # 1. Load all frames for all 8 directions
    dirs = {d: [] for d in range(NUM_DIRS)}
    for clip_name, f_indices in clips:
        clip_dirs = load_clip_frames(clip_name, f_indices)
        for d in range(NUM_DIRS):
            dirs[d].extend(clip_dirs[d])

    num_frames = len(dirs[0])
    for d in range(1, NUM_DIRS):
        assert len(dirs[d]) == num_frames, f"Dir {d} has {len(dirs[d])} frames, expected {num_frames}"

    # 2. Collect opaque pixels across all frames and directions for palette generation
    opaque_pixels = []
    for d in range(NUM_DIRS):
        for frame in dirs[d]:
            arr = np.array(frame)
            mask = arr[:, :, 3] >= ALPHA_THRESHOLD
            rgb = arr[mask, :3]
            if len(rgb) > 0:
                opaque_pixels.append(rgb)

    if not opaque_pixels:
        raise ValueError(f"No opaque pixels found for {char_id}")

    all_rgb = np.vstack(opaque_pixels)

    # 3. Quantize with Pillow to at most 255 colors (color 0 is transparent)
    flat_img = Image.fromarray(all_rgb.reshape(-1, 1, 3))
    quantized = flat_img.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    raw_pal = quantized.getpalette()[:255 * 3]

    # Palette table for Pillow mapping: index 0 = (0,0,0) (transparent), 1..255 = colors
    pal_256_rgb = [0, 0, 0] + raw_pal
    while len(pal_256_rgb) < 256 * 3:
        pal_256_rgb.extend([0, 0, 0])

    # Convert 1..255 to NDS BGR555 | 0x8000
    nds_palette = [0] * 256
    nds_palette[0] = 0x0000  # Transparent
    for i in range(1, 256):
        r = pal_256_rgb[i * 3] >> 3
        g = pal_256_rgb[i * 3 + 1] >> 3
        b = pal_256_rgb[i * 3 + 2] >> 3
        nds_palette[i] = (r & 0x1F) | ((g & 0x1F) << 5) | ((b & 0x1F) << 10) | 0x8000

    pal_img = Image.new('P', (1, 1))
    pal_img.putpalette(pal_256_rgb)

    # 4. Map frames to 8-bit palette and crop
    dir_data_blocks = []
    dir_sizes = []

    for d in range(NUM_DIRS):
        frame_records = []
        cropped_pixels_list = []
        u_min_x, u_min_y = CANVAS_W, CANVAS_H
        u_max_x, u_max_y = 0, 0

        current_offset = 0
        for frame in dirs[d]:
            arr = np.array(frame)
            alpha_mask = arr[:, :, 3] >= ALPHA_THRESHOLD

            rgb_frame = frame.convert('RGB')
            mapped = rgb_frame.quantize(palette=pal_img, dither=Image.Dither.NONE)
            mapped_arr = np.array(mapped, dtype=np.uint8)

            # Mask out transparent pixels
            mapped_arr[~alpha_mask] = 0
            # Ensure opaque pixels do not use index 0
            mapped_arr[alpha_mask & (mapped_arr == 0)] = 1

            if np.any(alpha_mask):
                y_idx, x_idx = np.where(alpha_mask)
                bx = int(x_idx.min())
                by = int(y_idx.min())
                bw = int(x_idx.max() - bx + 1)
                bh = int(y_idx.max() - by + 1)
                cropped = mapped_arr[by : by + bh, bx : bx + bw].tobytes()

                if bx < u_min_x: u_min_x = bx
                if by < u_min_y: u_min_y = by
                if bx + bw > u_max_x: u_max_x = bx + bw
                if by + bh > u_max_y: u_max_y = by + bh
            else:
                bx, by, bw, bh = 0, 0, 0, 0
                cropped = b''

            frame_records.append((bx, by, bw, bh, current_offset))
            cropped_pixels_list.append(cropped)
            current_offset += len(cropped)

        if u_min_x > u_max_x:
            u_min_x, u_min_y, u_max_x, u_max_y = 0, 0, CANVAS_W, CANVAS_H

        # Pack direction block
        # Header: u_min_x, u_min_y, u_max_x, u_max_y (4 bytes)
        dir_header = struct.pack('<4B', u_min_x, u_min_y, u_max_x, u_max_y)

        # Frames: bx, by, bw, bh, offset (8 bytes each)
        frames_bytes = b''
        for rec in frame_records:
            frames_bytes += struct.pack('<4BI', rec[0], rec[1], rec[2], rec[3], rec[4])

        pixels_bytes = b''.join(cropped_pixels_list)

        dir_block = dir_header + frames_bytes + pixels_bytes
        dir_data_blocks.append(dir_block)
        dir_sizes.append(len(dir_block))

    # 5. Pack complete file
    # Header format:
    # uint16 magic (0x4251)
    # uint8  num_dirs (8)
    # uint8  num_frames
    # uint8  canvas_w (160)
    # uint8  canvas_h (160)
    # uint8  pad[2]
    # uint16 palette[256] (512 bytes)
    # uint32 dir_offsets[8] (32 bytes)
    # uint32 dir_sizes[8] (32 bytes)
    # Total header size = 2 + 1 + 1 + 1 + 1 + 2 + 512 + 32 + 32 = 584 bytes

    header_size = 584
    dir_offsets = []
    current_file_offset = header_size
    for sz in dir_sizes:
        dir_offsets.append(current_file_offset)
        current_file_offset += sz

    header_bytes = struct.pack('<H4B2x', MAGIC, NUM_DIRS, num_frames, CANVAS_W, CANVAS_H)
    header_bytes += struct.pack('<256H', *nds_palette)
    header_bytes += struct.pack('<8I', *dir_offsets)
    header_bytes += struct.pack('<8I', *dir_sizes)
    assert len(header_bytes) == header_size, f"Header size mismatch: {len(header_bytes)} != {header_size}"

    full_binary = header_bytes + b''.join(dir_data_blocks)
    return full_binary, dir_sizes

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating bestiary portrait binaries in {OUTPUT_DIR}...")
    max_single_dir_size = 0

    for char_info in CHARACTERS:
        char_id = char_info['id']
        binary, dir_sizes = build_portrait_binary(char_info)
        out_path = os.path.join(OUTPUT_DIR, f"{char_id}.bin")
        with open(out_path, 'wb') as f:
            f.write(binary)

        max_dir = max(dir_sizes)
        if max_dir > max_single_dir_size:
            max_single_dir_size = max_dir

        print(f"  {char_id}.bin: total={len(binary)} bytes ({len(binary)/1024:.1f} KB), max_dir={max_dir} bytes ({max_dir/1024:.1f} KB)")

    print(f"\nCompleted successfully! Maximum single-direction buffer required: {max_single_dir_size} bytes ({max_single_dir_size/1024:.1f} KB).")

if __name__ == '__main__':
    main()
