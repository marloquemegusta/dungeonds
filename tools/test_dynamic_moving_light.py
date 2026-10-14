import numpy as np
from PIL import Image
from pathlib import Path
import math

def test():
    brain = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
    world_img_path = r"walkthroughs/scifi-dungeon-tripo/assets/00_spawn.png"

    # Load background image
    im = Image.open(world_img_path).crop((0, 192, 256, 384)).convert("RGB")
    im_arr = np.array(im, dtype=np.uint8)

    # Load 3D baked multi positions: pos1_spawn, pos2_arch, pos3_corridor
    data = np.load(brain / "baked_multi_positions.npz")
    
    # Let's test pos1_spawn (361, 233), pos2_arch (318, 238), pos3_corridor (275, 245)
    cam_x, cam_y = 233, 137

    positions = [
        ("Spawn Centro", "pos1_spawn", 361, 233),
        ("Cruce Arco", "pos2_arch", 318, 238),
        ("Pasillo Oeste", "pos3_corridor", 275, 245)
    ]

    frames = []

    for label, key, px, py in positions:
        vis_map = data[key] # (192, 256) float array directly from 3D BVH raycast
        
        # 16-level fixed-point integer quantization matching NDS ARM9
        light_levels = np.clip(np.round(vis_map * 16.0), 0, 16).astype(np.int32)

        out_arr = np.zeros_like(im_arr)
        for c in range(3):
            comp_5 = im_arr[:, :, c].astype(np.int32) >> 3
            shaded = (comp_5 * light_levels) >> 4
            out_arr[:, :, c] = (shaded << 3) | (shaded >> 2)

        frame = Image.fromarray(out_arr)
        
        # Draw player indicator
        from PIL import ImageDraw
        draw = ImageDraw.Draw(frame)
        spx = px - cam_x
        spy = py - cam_y
        draw.ellipse([(spx-3, spy-3), (spx+3, spy+3)], fill=(255, 240, 180), outline=(255, 100, 50))
        draw.text((8, 8), label, fill=(100, 255, 140))
        
        frames.append(frame.resize((512, 384), Image.Resampling.NEAREST))

    # Save animated GIF
    gif_path = brain / "true_3d_dynamic_moving_light.gif"
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=800, loop=0)
    print("Saved dynamic moving light GIF to:", gif_path)

    # Save 3-panel comparison
    comp = Image.new("RGB", (512 * 3, 384), (15, 15, 18))
    for i, f in enumerate(frames):
        comp.paste(f, (i * 512, 0))
    comp_path = brain / "true_3d_dynamic_moving_light_panels.png"
    comp.save(comp_path)
    print("Saved panels to:", comp_path)

if __name__ == "__main__":
    test()
