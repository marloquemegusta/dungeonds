import numpy as np
from PIL import Image
from pathlib import Path

def test_exact():
    brain = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
    world_img_path = r"walkthroughs/scifi-dungeon-tripo/assets/00_spawn.png"

    im = Image.open(world_img_path).crop((0, 192, 256, 384)).convert("RGB")
    im_arr = np.array(im, dtype=np.uint8)

    # Load the 3D baked vis_map which has full 3D wall occlusions and continuous falloff
    vis_map = np.load(brain / "vis_map.npy") # (192, 256), range 0.0 to 1.0

    # Quantize to 16 integer light levels (0..16) as done in ARM9 fixed-point integer math
    light_levels = np.clip(np.round(vis_map * 16.0), 0, 16).astype(np.int32)

    # Simulate the exact ARM9 C code:
    # static inline uint16_t shade_rgb15(uint16_t c, int light)
    #   r = (r * light) >> 4; g = (g * light) >> 4; b = (b * light) >> 4;
    out_arr = np.zeros_like(im_arr)
    for c in range(3):
        # 5-bit color precision matching NDS RGB15
        comp_5bit = im_arr[:, :, c] >> 3
        shaded_5bit = (comp_5bit * light_levels) >> 4
        out_arr[:, :, c] = (shaded_5bit << 3) | (shaded_5bit >> 2) # Expand back to 8bpp for display

    out_img = Image.fromarray(out_arr).resize((512, 384), Image.Resampling.NEAREST)
    out_path = brain / "nds_exact_proportional_shading_simulation.png"
    out_img.save(out_path)
    print("Saved exact NDS simulation to:", out_path)

if __name__ == "__main__":
    test_exact()
