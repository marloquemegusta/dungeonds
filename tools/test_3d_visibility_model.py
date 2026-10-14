import numpy as np
from PIL import Image
from pathlib import Path
import math

brain = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
scifi_world_path = Path(r"C:\codexlocal\dungeonds\.worktrees\fog-and-visibility\walkthroughs\scifi-dungeon-tripo\assets\00_spawn.png")
coll_path = Path(r"C:\codexlocal\dungeonds\.worktrees\fog-and-visibility\assets\scifi_baked\scifi_coll.npy")
occ_path = Path(r"C:\codexlocal\dungeonds\.worktrees\fog-and-visibility\assets\scifi_baked\scifi_occ.npy")

coll = np.load(coll_path)
occ = np.load(occ_path) # (512, 768)
world_img = Image.open(scifi_world_path).crop((0, 192, 256, 384)).convert("RGB")
img_arr = np.array(world_img, dtype=np.float32) / 255.0

cam_x, cam_y = 233, 137
px, py = 361, 233 # player ground pos

# Let's inspect what happens with:
# 1. 3D Torch Light: Position (px, py, z=1.2m)
# 2. Smooth physical falloff (1 / (1 + (d/R)^2))
# 3. Proper wall illumination:
#    In the room, the perimeter walls have collision == 3.
#    Rays travel to the walls. The wall face FACING the player is fully illuminated!
#    Only areas BEYOND the wall (different room) are in shadow.
# 4. Low obstacle (reactor):
#    Light shines OVER the reactor (since torch is at 1.2m, reactor is 0.8m).
#    It only casts a local ground shadow behind it, but does NOT shadow the walls!

# Compute lighting for each screen pixel:
lit_img = np.zeros_like(img_arr)

# Precalculate line of sight from player to all ground cells in a 120px radius
# Using 512 radial rays or dense grid
MAX_DIST = 140.0
cos_elev = math.cos(math.radians(30)) # dimetric aspect

for sy in range(192):
    wy = cam_y + sy
    for sx in range(256):
        wx = cam_x + sx
        
        # Ground anchor for this pixel
        occ_y = occ[wy, wx] if 0 <= wy < 512 and 0 <= wx < 768 else -1
        is_elevated_wall = occ_y >= 0
        ground_y = occ_y if is_elevated_wall else wy
        ground_x = wx
        
        # Physical 2D ground distance
        dx = (ground_x - px)
        dy = (ground_y - py)
        dist = math.hypot(dx, dy)
        
        if dist > MAX_DIST:
            continue
            
        # Line of sight check to ground anchor:
        # Trace line from (px, py) to (ground_x, ground_y) on collision grid
        steps = int(max(abs(dx), abs(dy)))
        blocked = False
        if steps > 0:
            for s in range(1, steps):
                tx = px + dx * s / steps
                ty = py + dy * s / steps
                cx = int(tx // 4)
                cy = int(ty // 4)
                if 0 <= cx < coll.shape[1] and 0 <= cy < coll.shape[0]:
                    if coll[cy, cx] == 3:
                        # Hit a wall before reaching target!
                        blocked = True
                        break
        
        if blocked:
            continue
            
        # Pixel is visible!
        # Now compute 3D lighting intensity:
        # Torch height Z = 1.2m (approx 15 pixels in screen scale)
        # 3D distance
        dist_3d = math.hypot(dist, 15.0)
        
        # Smooth quadratic falloff
        atten = 1.0 / (1.0 + (dist_3d / 45.0)**2)
        
        # Ambient light level in illuminated room
        intensity = max(0.0, atten)
        
        # Check if behind reactor for shadow:
        # Reactor is around cx in [88, 100], cy in [62, 70]
        # If ground_x, ground_y is in reactor shadow cone:
        rcx, rcy = 94 * 4, 66 * 4
        if ground_y > rcy and abs(ground_x - rcx) < 20 and dist > 35:
            intensity *= 0.25 # Soft contact shadow
            
        lit_img[sy, sx] = img_arr[sy, sx] * min(1.0, intensity * 1.6)

out_arr = np.clip(lit_img * 255.0, 0, 255).astype(np.uint8)
out_im = Image.fromarray(out_arr).resize((512, 384), Image.Resampling.NEAREST)
out_path = brain / "simulated_3d_torch_lighting.png"
out_im.save(out_path)
print("Saved to:", out_path)
