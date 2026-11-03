#include "navfield.h"
#include "collision.h"
#include "diablo_dungeon.h"

#define NAV_NODES (NAV_W * NAV_H)

static uint8_t s_walkable[NAV_NODES];
static uint8_t s_dist[2][NAV_NODES];       // [read, build] swapped when a search completes
static int s_read = 0;
static uint16_t s_queue[NAV_NODES];
static int s_head = 0, s_tail = 0;         // search in progress when head < tail
static int s_goal_node = -1;               // node the next search starts from
static int s_walkable_count = 0;

static const int8_t s_dx[8] = { 1, -1, 0, 0, 1, 1, -1, -1 };
static const int8_t s_dy[8] = { 0, 0, 1, -1, 1, -1, 1, -1 };

static inline int node_of(int px, int py) {
    int nx = px / NAV_NODE_PX, ny = py / NAV_NODE_PX;
    if (px < 0 || py < 0 || nx >= NAV_W || ny >= NAV_H) return -1;
    return ny * NAV_W + nx;
}

// A diagonal step may not cut the corner of a blocked node.
static inline int step_allowed(int nx, int ny, int k) {
    int tx = nx + s_dx[k], ty = ny + s_dy[k];
    if ((unsigned)tx >= NAV_W || (unsigned)ty >= NAV_H) return 0;
    if (!s_walkable[ty * NAV_W + tx]) return 0;
    if (s_dx[k] != 0 && s_dy[k] != 0) {
        if (!s_walkable[ny * NAV_W + tx] || !s_walkable[ty * NAV_W + nx]) return 0;
    }
    return 1;
}

void nav_init(void) {
    s_walkable_count = 0;
    for (int ny = 0; ny < NAV_H; ny++) {
        for (int nx = 0; nx < NAV_W; nx++) {
            fixed cx = TO_FIXED(nx * NAV_NODE_PX + NAV_NODE_PX / 2);
            fixed cy = TO_FIXED(ny * NAV_NODE_PX + NAV_NODE_PX / 2);
            int ok = position_is_free(cx, cy);
            s_walkable[ny * NAV_W + nx] = (uint8_t)ok;
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
}

int nav_walkable_count(void) {
    return s_walkable_count;
}

// The goal node is the player's; if the player stands off a node centre that is not
// walkable, take the nearest walkable neighbour.
static int resolve_goal(int node, int px, int py) {
    if (node < 0) return -1;
    if (s_walkable[node]) return node;
    int nx = node % NAV_W, ny = node / NAV_W;
    int best = -1, best_d2 = 0x7FFFFFFF;
    for (int k = 0; k < 8; k++) {
        int tx = nx + s_dx[k], ty = ny + s_dy[k];
        if ((unsigned)tx >= NAV_W || (unsigned)ty >= NAV_H || !s_walkable[ty * NAV_W + tx]) continue;
        int cx = tx * NAV_NODE_PX + NAV_NODE_PX / 2 - px;
        int cy = ty * NAV_NODE_PX + NAV_NODE_PX / 2 - py;
        int d2 = cx * cx + GROUND_DY2(cy);
        if (d2 < best_d2) {
            best_d2 = d2;
            best = ty * NAV_W + tx;
        }
    }
    return best;
}

void nav_set_goal(int goal_px, int goal_py) {
    int node = resolve_goal(node_of(goal_px, goal_py), goal_px, goal_py);
    if (node >= 0) s_goal_node = node;
}

static void start_search(void) {
    uint8_t *dist = s_dist[1 - s_read];
    for (int i = 0; i < NAV_NODES; i++) dist[i] = NAV_UNREACHABLE;
    s_head = 0;
    s_tail = 0;
    dist[s_goal_node] = 0;
    s_queue[s_tail++] = (uint16_t)s_goal_node;
}

void nav_update(int budget) {
    if (s_head >= s_tail) {
        if (s_goal_node < 0) return;
        start_search();
    }
    uint8_t *dist = s_dist[1 - s_read];
    while (budget-- > 0 && s_head < s_tail) {
        int node = s_queue[s_head++];
        int nx = node % NAV_W, ny = node / NAV_W;
        int next = dist[node] + 1;
        if (next >= NAV_UNREACHABLE) continue;
        for (int k = 0; k < 8; k++) {
            if (!step_allowed(nx, ny, k)) continue;
            int target = (ny + s_dy[k]) * NAV_W + (nx + s_dx[k]);
            if (dist[target] != NAV_UNREACHABLE) continue;
            dist[target] = (uint8_t)next;
            s_queue[s_tail++] = (uint16_t)target;
        }
    }
    if (s_head >= s_tail) {
        // Finished: the field just built becomes the one enemies read.
        s_read = 1 - s_read;
        s_head = s_tail = 0;
    }
}

void nav_rebuild_now(void) {
    if (s_goal_node < 0) return;
    s_head = s_tail = 0;
    nav_update(NAV_NODES * 8);
}

int nav_distance(int px, int py) {
    int node = node_of(px, py);
    if (node < 0) return NAV_UNREACHABLE;
    return s_dist[s_read][node];
}

int nav_next_step(int px, int py, int *target_px, int *target_py) {
    int node = node_of(px, py);
    if (node < 0) return 0;
    const uint8_t *dist = s_dist[s_read];
    int here = dist[node];
    if (here == 0) return 0;
    int nx = node % NAV_W, ny = node / NAV_W;
    int best = here, best_k = -1;
    for (int k = 0; k < 8; k++) {
        // A body can stand where its node's centre is blocked (hugging a wall); then no
        // corner rule applies from this node, any reachable neighbour is a way out.
        if (here == NAV_UNREACHABLE) {
            int tx = nx + s_dx[k], ty = ny + s_dy[k];
            if ((unsigned)tx >= NAV_W || (unsigned)ty >= NAV_H || !s_walkable[ty * NAV_W + tx]) continue;
        } else if (!step_allowed(nx, ny, k)) {
            continue;
        }
        int d = dist[(ny + s_dy[k]) * NAV_W + (nx + s_dx[k])];
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
