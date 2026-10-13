import numpy as np
import json
from collections import deque

coll = np.load(r"C:\Users\malfonso\.gemini\antigravity\brain\295f906d-3c8b-4b9a-8a57-3b3f945e38a6\scratch\wh40k_coll.npy")
H, W = coll.shape

start = (400, 240)
target = (475, 156)

queue = deque([start])
visited = {start: None}

while queue:
    curr = queue.popleft()
    if curr == target:
        break
    cx, cy = curr
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        nx, ny = cx + dx, cy + dy
        if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in visited:
            if coll[ny, nx] == 0:
                visited[(nx, ny)] = curr
                queue.append((nx, ny))

path = []
curr = target
while curr:
    path.append(curr)
    curr = visited[curr]
path.reverse()

# Simplify path into keypress segments
# Each cell is 4 pixels. Character speed is ~1.5 pixels per frame.
# Each cell step takes ~4 / 1.5 = ~2.7 frames (or 3 frames).
# Let's trace direction segments:
segments = []
current_dir = None
count = 0

for i in range(len(path) - 1):
    c0 = path[i]
    c1 = path[i+1]
    dx = c1[0] - c0[0]
    dy = c1[1] - c0[1]
    
    # Map (dx, dy) to buttons
    buttons = []
    if dy < 0: buttons.append("UP")
    elif dy > 0: buttons.append("DOWN")
    if dx < 0: buttons.append("LEFT")
    elif dx > 0: buttons.append("RIGHT")
    dir_key = tuple(sorted(buttons))
    
    if dir_key == current_dir:
        count += 1
    else:
        if current_dir is not None:
            segments.append((current_dir, count))
        current_dir = dir_key
        count = 1
segments.append((current_dir, count))

print(f"Path broken into {len(segments)} directional segments:")
steps = [{ "frames": 30, "capture": "00_spawn" }]

for dir_key, cell_count in segments:
    # Estimate frames: 1 cell is 4 pixels. Character speed in diagonal vs cardinal:
    # Cardinal: speed = 1.0 or 1.5? Let's check: fixed 8.8.
    # In main.c, speed is fixed (e.g. 1.0 or 1.5).
    # With 3 frames per cell:
    frames = cell_count * 3
    btn_str = "+".join(dir_key) if len(dir_key) > 1 else dir_key[0]
    steps.append({
        "button_down": btn_str,
        "frames": frames
    })
    steps.append({
        "button_up": btn_str,
        "frames": 2
    })

# At destination behind the wall, capture!
steps.append({ "frames": 20, "capture": "01_behind_wall_occluded" })

scenario = {
    "name": "wh40k_cathedral_occlusion_exact",
    "steps": steps,
    "assertions": {
        "screen_changes": [
            { "from": "00_spawn", "to": "01_behind_wall_occluded", "min_changed_pixels": 250 }
        ]
    }
}

out_path = r"C:\codexlocal\dungeonds\.worktrees\wh40k-floor-preview\scenarios\wh40k_cathedral_occlusion_exact.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(scenario, f, indent=2)

print(f"Generated {out_path} with {len(steps)} steps!")
