import numpy as np

WALKABLE = 0
OBSTACLE = 1
VOID = 2


def classify_vertical_hits(hits, floor=0.07301, player_height=0.05, support_tolerance=0.01):
    if not hits:
        return VOID

    sorted_hits = sorted(hits, reverse=True)
    
    # Find floor surface within support_tolerance
    floor_hit = None
    for h in sorted_hits:
        if abs(h - floor) <= support_tolerance:
            floor_hit = h
            break
            
    if floor_hit is None:
        return VOID

    # Form intervals from pairs [top, bottom, top, bottom...]
    # If odd number of hits, pair with next
    # Any solid interval that overlaps with [floor_hit, floor_hit + player_height] is an obstacle
    head_z = floor_hit + player_height
    
    # Process hit pairs from top to bottom
    i = 0
    while i < len(sorted_hits):
        top = sorted_hits[i]
        bot = sorted_hits[i + 1] if i + 1 < len(sorted_hits) else 0.0
        # If top and bot represent a solid obstacle:
        # Check if this solid block intersects (floor_hit + 0.005, head_z)
        # Exception: if top is right at floor level, it is the floor slab
        if top > floor_hit + 0.005:
            # Solid block from bot to top
            # If bot <= head_z, it blocks the player's body
            if bot < head_z:
                return OBSTACLE
        i += 2

    return WALKABLE


def project_camera_plane_to_ground(cam_origin, right, up, forward, u, v):
    p_x = cam_origin[0] + right[0] * u + up[0] * v
    p_y = cam_origin[1] + right[1] * u + up[1] * v
    p_z = cam_origin[2] + right[2] * u + up[2] * v
    t = -p_z / forward[2]
    return (p_x + forward[0] * t, p_y + forward[1] * t, p_z + forward[2] * t)


def largest_walkable_component(grid):
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    labels = np.full((h, w), -1, dtype=np.int32)
    sizes = []

    for y in range(h):
        for x in range(w):
            if grid[y, x] == 0 and not visited[y, x]:
                comp_id = len(sizes)
                queue = [(x, y)]
                visited[y, x] = True
                labels[y, x] = comp_id
                count = 0
                while queue:
                    cx, cy = queue.pop(0)
                    count += 1
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and grid[ny, nx] == 0 and not visited[ny, nx]:
                            visited[ny, nx] = True
                            labels[ny, nx] = comp_id
                            queue.append((nx, ny))
                sizes.append(count)

    return labels, sizes


def spawn_is_clear(grid, x, y):
    h, w = grid.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h or grid[ny, nx] != 0:
                return False
    return True


def choose_spawn(grid):
    labels, sizes = largest_walkable_component(grid)
    if not sizes:
        raise ValueError("no walkable components")
    largest_comp = int(np.argmax(sizes))
    h, w = grid.shape
    for y in range(h):
        for x in range(w):
            if labels[y, x] == largest_comp and spawn_is_clear(grid, x, y):
                return x, y, largest_comp, sizes
    raise ValueError("no 1-cell clearance spawn")
