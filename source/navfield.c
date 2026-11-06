#include "navfield.h"
#include "collision.h"
#include "arena.h"

#include <string.h>

#define NAV_NODES (NAV_MAX_W * NAV_MAX_H)

static int s_w = 0, s_h = 0;               // grid of the active arena
static uint8_t s_walkable[NAV_NODES];
static uint8_t s_dist[2][NAV_NODES];       // [read, build] swapped when a search completes
static int s_read = 0;
static uint16_t s_queue[NAV_NODES]; // packed x (6 bits) and y (remaining bits)
static int s_head = 0, s_tail = 0;         // search in progress when head < tail
static int s_goal_node = -1;               // node the next search starts from
static int s_goal_node_x = 0, s_goal_node_y = 0;
static int s_walkable_count = 0;
static int s_refresh_cursor = 0;
static int s_refresh_x = 0, s_refresh_y = 0;
static int s_refreshing = 0;
static int s_field_valid = 0;
static int s_goal_px = 0, s_goal_py = 0;

static const int8_t s_dx[8] = { 1, -1, 0, 0, 1, 1, -1, -1 };
static const int8_t s_dy[8] = { 0, 0, 1, -1, 1, -1, 1, -1 };
static int resolve_goal(int node, int px, int py);

static inline int node_of(int px, int py) {
    int nx = px / NAV_NODE_PX, ny = py / NAV_NODE_PX;
    if (px < 0 || py < 0 || nx >= s_w || ny >= s_h) return -1;
    return ny * s_w + nx;
}

// A diagonal step may not cut the corner of a blocked node.
static inline int step_allowed(int nx, int ny, int k) {
    int tx = nx + s_dx[k], ty = ny + s_dy[k];
    if ((unsigned)tx >= s_w || (unsigned)ty >= s_h) return 0;
    if (!s_walkable[ty * s_w + tx]) return 0;
    if (s_dx[k] != 0 && s_dy[k] != 0) {
        if (!s_walkable[ny * s_w + tx] || !s_walkable[ty * s_w + nx]) return 0;
    }
    return 1;
}

int nav_width(void) { return s_w; }
int nav_height(void) { return s_h; }

static void set_grid_size(void) {
    s_w = g_arena->world_w / NAV_NODE_PX;
    s_h = g_arena->world_h / NAV_NODE_PX;
    if (s_w > NAV_MAX_W) s_w = NAV_MAX_W;
    if (s_h > NAV_MAX_H) s_h = NAV_MAX_H;
}

static int node_walkable(int nx, int ny) {
    fixed cx = TO_FIXED(nx * NAV_NODE_PX + NAV_NODE_PX / 2);
    fixed cy = TO_FIXED(ny * NAV_NODE_PX + NAV_NODE_PX / 2);
    return position_is_free(cx, cy);
}

void nav_init(void) {
    set_grid_size();
    s_walkable_count = 0;
    for (int ny = 0; ny < s_h; ny++) {
        for (int nx = 0; nx < s_w; nx++) {
            int index = ny * s_w + nx;
            int ok = node_walkable(nx, ny);
            s_walkable[index] = (uint8_t)ok;
            s_walkable_count += ok;
        }
    }
    for (int i = 0; i < NAV_NODES; i++) {
        s_dist[0][i] = NAV_UNREACHABLE;
        s_dist[1][i] = NAV_UNREACHABLE;
    }
    s_read = 0;
    s_head = s_tail = 0;
    s_goal_node = -1;
    s_goal_node_x = s_goal_node_y = 0;
    s_refresh_cursor = 0;
    s_refresh_x = s_refresh_y = 0;
    s_refreshing = 0;
    s_field_valid = 0;
}

void nav_refresh_begin(int goal_px, int goal_py) {
    set_grid_size();
    s_walkable_count = 0;
    s_refresh_cursor = 0;
    s_refresh_x = s_refresh_y = 0;
    s_refreshing = 1;
    s_field_valid = 0;
    s_head = s_tail = 0;
    s_goal_node = -1;
    s_goal_px = goal_px;
    s_goal_py = goal_py;
}

void nav_shift_down(int rows, int goal_px, int goal_py) {
    if (rows <= 0 || rows >= s_h) {
        nav_refresh_begin(goal_px, goal_py);
        return;
    }
    int keep_rows = s_h - rows;
    int removed_walkable = 0;
    for (int i = 0; i < rows * s_w; i++) removed_walkable += s_walkable[i] != 0;
    memmove(s_walkable + rows * s_w, s_walkable, (size_t)keep_rows * (size_t)s_w);
    for (int b = 0; b < 2; b++) {
        memmove(s_dist[b] + rows * s_w, s_dist[b], (size_t)keep_rows * (size_t)s_w);
        for (int i = 0; i < rows * s_w; i++) s_dist[b][i] = NAV_UNREACHABLE;
    }
    s_walkable_count -= removed_walkable;
    for (int ny = 0; ny < rows; ny++) {
        for (int nx = 0; nx < s_w; nx++) {
            int index = ny * s_w + nx;
            int ok = node_walkable(nx, ny);
            s_walkable[index] = (uint8_t)ok;
            s_walkable_count += ok;
        }
    }
    s_goal_px = goal_px;
    s_goal_py = goal_py;
    s_refreshing = 0;
    s_refresh_cursor = 0;
    s_refresh_x = s_refresh_y = 0;
    s_goal_node = resolve_goal(node_of(goal_px, goal_py), goal_px, goal_py);
    s_head = s_tail = 0;
}

int nav_walkable_count(void) {
    return s_walkable_count;
}

// The goal node is the player's; if the player stands off a node centre that is not
// walkable, take the nearest walkable neighbour.
static int resolve_goal(int node, int px, int py) {
    if (node < 0) return -1;
    int nx = px / NAV_NODE_PX, ny = py / NAV_NODE_PX;
    if (s_walkable[node]) {
        s_goal_node_x = nx;
        s_goal_node_y = ny;
        return node;
    }
    int best = -1, best_d2 = 0x7FFFFFFF;
    for (int k = 0; k < 8; k++) {
        int tx = nx + s_dx[k], ty = ny + s_dy[k];
        if ((unsigned)tx >= s_w || (unsigned)ty >= s_h || !s_walkable[ty * s_w + tx]) continue;
        int cx = tx * NAV_NODE_PX + NAV_NODE_PX / 2 - px;
        int cy = ty * NAV_NODE_PX + NAV_NODE_PX / 2 - py;
        int d2 = cx * cx + GROUND_DY2(cy);
        if (d2 < best_d2) {
            best_d2 = d2;
            best = ty * s_w + tx;
            s_goal_node_x = tx;
            s_goal_node_y = ty;
        }
    }
    return best;
}

void nav_set_goal(int goal_px, int goal_py) {
    s_goal_px = goal_px;
    s_goal_py = goal_py;
    if (s_refreshing) return;
    int node = resolve_goal(node_of(goal_px, goal_py), goal_px, goal_py);
    if (node >= 0) s_goal_node = node;
}

static void start_search(void) {
    uint8_t *dist = s_dist[1 - s_read];
    for (int i = 0; i < s_w * s_h; i++) dist[i] = NAV_UNREACHABLE;
    s_head = 0;
    s_tail = 0;
    dist[s_goal_node] = 0;
    s_queue[s_tail++] = (uint16_t)((s_goal_node_y << 6) | s_goal_node_x);
}

void nav_update(int budget) {
    while (s_refreshing && budget > 0 && s_refresh_cursor < s_w * s_h) {
        int index = s_refresh_cursor++;
        int ok = node_walkable(s_refresh_x, s_refresh_y);
        s_walkable[index] = (uint8_t)ok;
        s_walkable_count += ok;
        if (++s_refresh_x == s_w) { s_refresh_x = 0; s_refresh_y++; }
        budget--;
    }
    if (s_refreshing && s_refresh_cursor >= s_w * s_h) {
        s_refreshing = 0;
        int node = resolve_goal(node_of(s_goal_px, s_goal_py), s_goal_px, s_goal_py);
        if (node >= 0) s_goal_node = node;
    }
    if (budget <= 0) return;
    if (s_head >= s_tail) {
        if (s_goal_node < 0) return;
        start_search();
    }
    uint8_t *dist = s_dist[1 - s_read];
    while (budget-- > 0 && s_head < s_tail) {
        uint16_t packed = s_queue[s_head++];
        int nx = packed & 63, ny = packed >> 6;
        int node = ny * s_w + nx;
        int next = dist[node] + 1;
        if (next >= NAV_UNREACHABLE) continue;
        for (int k = 0; k < 8; k++) {
            if (!step_allowed(nx, ny, k)) continue;
            int target = (ny + s_dy[k]) * s_w + (nx + s_dx[k]);
            if (dist[target] != NAV_UNREACHABLE) continue;
            dist[target] = (uint8_t)next;
            int tx = nx + s_dx[k], ty = ny + s_dy[k];
            s_queue[s_tail++] = (uint16_t)((ty << 6) | tx);
        }
    }
    if (s_head >= s_tail) {
        // Finished: the field just built becomes the one enemies read.
        s_read = 1 - s_read;
        s_head = s_tail = 0;
        s_field_valid = 1;
    }
}

void nav_rebuild_now(void) {
    if (!s_refreshing && s_goal_node < 0) return;
    s_head = s_tail = 0;
    nav_update(NAV_NODES * 8);
}

int nav_distance(int px, int py) {
    if (!s_field_valid || s_refreshing) return NAV_UNREACHABLE;
    int node = node_of(px, py);
    if (node < 0) return NAV_UNREACHABLE;
    return s_dist[s_read][node];
}

int nav_next_step(int px, int py, int *target_px, int *target_py) {
    if (!s_field_valid || s_refreshing) return 0;
    int node = node_of(px, py);
    if (node < 0) return 0;
    const uint8_t *dist = s_dist[s_read];
    int here = dist[node];
    if (here == 0) return 0;
    int nx = px / NAV_NODE_PX, ny = py / NAV_NODE_PX;
    int best = here, best_k = -1;
    for (int k = 0; k < 8; k++) {
        // A body can stand where its node's centre is blocked (hugging a wall); then no
        // corner rule applies from this node, any reachable neighbour is a way out.
        if (here == NAV_UNREACHABLE) {
            int tx = nx + s_dx[k], ty = ny + s_dy[k];
            if ((unsigned)tx >= s_w || (unsigned)ty >= s_h || !s_walkable[ty * s_w + tx]) continue;
        } else if (!step_allowed(nx, ny, k)) {
            continue;
        }
        int d = dist[(ny + s_dy[k]) * s_w + (nx + s_dx[k])];
        if (d < best) {
            best = d;
            best_k = k;
        }
    }
    if (best_k < 0) return 0;
    *target_px = (nx + s_dx[best_k]) * NAV_NODE_PX + NAV_NODE_PX / 2;
    *target_py = (ny + s_dy[best_k]) * NAV_NODE_PX + NAV_NODE_PX / 2;
    return 1;
}
