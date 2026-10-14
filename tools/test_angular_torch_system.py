import numpy as np
from PIL import Image
from pathlib import Path
import math

def test():
    brain = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
    world_img_path = r"walkthroughs/scifi-dungeon-tripo/assets/00_spawn.png"
    coll_path = Path(r"assets\scifi_baked\scifi_coll.npy")
    occ_path = Path(r"assets\scifi_baked\scifi_occ.npy")

    coll = np.load(coll_path)
    occ = np.load(occ_path)
    im = Image.open(world_img_path).crop((0, 192, 256, 384)).convert("RGB")
    im_arr = np.array(im, dtype=np.uint8)

    cam_x, cam_y = 233, 137
    # Player at spawn
    px, py = 361, 233
    
    # 1. Cast 256 angular rays on collision grid to find obstacle distance
    NUM_ANGLES = 256
    MAX_R = 90
    shadow_dist = np.full(NUM_ANGLES, MAX_R, dtype=np.float32)

    pcx = px // 4
    pcy = py // 4

    for a_idx in range(NUM_ANGLES):
        angle = 2.0 * math.pi * a_idx / NUM_ANGLES
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for r in range(1, MAX_R):
            gx = int(round(px + cos_a * r))
            gy = int(round(py + sin_a * r))
            cx = gx // 4
            cy = gy // 4
            if 0 <= cx < coll.shape[1] and 0 <= cy < coll.shape[0]:
                if coll[cy, cx] == 3: # Solid tall wall
                    shadow_dist[a_idx] = r
                    break
            else:
                shadow_dist[a_idx] = r
                break

    # 2. Render torch circle around player
    out_arr = np.zeros_like(im_arr)

    # Player position in screen coordinates
    spx = px - cam_x
    spy = py - cam_y

    for dy in range(-MAX_R, MAX_R + 1):
        sy = spy + dy
        if sy < 0 or sy >= 192: continue
        wy = cam_y + sy
        for dx in range(-MAX_R, MAX_R + 1):
            sx = spx + dx
            if sx < 0 or sx >= 256: continue
            wx = cam_x + sx

            # Ground anchor check for elevated walls
            occ_y = occ[wy, wx] if 0 <= wy < 512 and 0 <= wx < 768 else -1
            is_wall = occ_y >= 0
            gy = occ_y if is_wall else wy
            gx = wx

            # Distance and angle to ground anchor
            g_dx = gx - px
            g_dy = gy - py
            dist = math.hypot(g_dx, g_dy)
            if dist > MAX_R: continue

            angle = math.atan2(g_dy, g_dx)
            if angle < 0: angle += 2 * math.pi
            a_idx = int(round(angle * NUM_ANGLES / (2 * math.pi))) % NUM_ANGLES

            # Check occlusion against shadow_dist
            # For walls facing player, give 4px grace so the wall face itself is lit
            cutoff = shadow_dist[a_idx] + (4.0 if is_wall else 1.0)
            if dist > cutoff:
                continue # In shadow!

            # Smooth physical falloff (16 levels)
            atten = 1.0 / (1.0 + (dist / 32.0)**2)
            
            # Reactor contact shadow on floor
            if not is_wall and g_dy > 12 and abs(g_dx) < 22 and dist > 25:
                atten *= 0.25

            light = int(round(min(1.0, atten * 1.6) * 16.0))
            if light <= 0: continue

            # Scale color with 5-bit precision
            for c in range(3):
                comp_5 = int(im_arr[sy, sx, c] >> 3)
                shaded = (comp_5 * light) >> 4
                out_arr[sy, sx, c] = (shaded << 3) | (shaded >> 2)

    out_img = Image.fromarray(out_arr).resize((512, 384), Image.Resampling.NEAREST)
    out_path = brain / "angular_dynamic_torch_preview.png"
    out_img.save(out_path)
    print("Saved preview to:", out_path)

if __name__ == "__main__":
    test()
