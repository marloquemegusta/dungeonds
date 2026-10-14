import numpy as np
from PIL import Image
from pathlib import Path

def test():
    brain = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
    world_img_path = r"walkthroughs/scifi-dungeon-tripo/assets/00_spawn.png"

    im = Image.open(world_img_path).crop((0, 192, 256, 384)).convert("RGB")
    im_arr = np.array(im, dtype=np.uint8)

    # Load 3D BVH per-pixel vis_map (192, 256)
    vis_map = np.load(brain / "vis_map.npy")
    cam_x, cam_y = 233, 137
    px, py = 361, 233
    spx = px - cam_x # 128
    spy = py - cam_y # 96

    # Downsample vis_map to an 8x8 cell grid (24 x 32 cells)
    grid_h, grid_w = 192 // 8, 256 // 8 # 24, 32
    cell_grid = np.zeros((grid_h, grid_w), dtype=np.float32)

    for cy in range(grid_h):
        for cx in range(grid_w):
            cell_grid[cy, cx] = np.mean(vis_map[cy*8:(cy+1)*8, cx*8:(cx+1)*8])

    # Now bilinearly interpolate cell_grid back to 192x256
    from PIL import ImageFilter
    grid_img = Image.fromarray((cell_grid * 255.0).astype(np.uint8))
    smooth_mask = grid_img.resize((256, 192), Image.Resampling.BILINEAR)
    smooth_arr = np.array(smooth_mask, dtype=np.float32) / 255.0

    # Quantize to 16 integer levels (ARM9 fixed point)
    light_levels = np.clip(np.round(smooth_arr * 16.0), 0, 16).astype(np.int32)

    out_arr = np.zeros_like(im_arr)
    for c in range(3):
        comp_5 = im_arr[:, :, c].astype(np.int32) >> 3
        shaded = (comp_5 * light_levels) >> 4
        out_arr[:, :, c] = (shaded << 3) | (shaded >> 2)

    out_img = Image.fromarray(out_arr).resize((512, 384), Image.Resampling.NEAREST)
    out_path = brain / "bilinear_lightgrid_simulation.png"
    out_img.save(out_path)
    print("Saved bilinear lightgrid simulation to:", out_path)

if __name__ == "__main__":
    test()
