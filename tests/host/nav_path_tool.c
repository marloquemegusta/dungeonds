// Dev tool: picks a walkable target node that the spawn cannot see (wall in between) but is
// reachable on foot, and prints the node path from the spawn to it. Used to generate the
// walking steps of scenarios/charger_walks_around_wall.json (see tools/gen_charger_wall_scenario.py).
#include <stdio.h>
#include <stdlib.h>
#include "navfield.h"
#include "collision.h"
#include "los.h"

int main(int argc, char **argv) {
    int max_len = argc > 1 ? atoi(argv[1]) : 40;
    nav_init();
    // Field towards the spawn gives path lengths from every node.
    nav_set_goal(SPAWN_PIXEL_X, SPAWN_PIXEL_Y);
    nav_rebuild_now();
    int best_x = -1, best_y = -1, best_score = 0;
    for (int ny = 0; ny < NAV_H; ny++) {
        for (int nx = 0; nx < NAV_W; nx++) {
            int px = nx * NAV_NODE_PX + 8, py = ny * NAV_NODE_PX + 8;
            int d = nav_distance(px, py);
            if (d == NAV_UNREACHABLE || d < 6 || d > max_len) continue;
            if (los_has_line_of_sight(SPAWN_PIXEL_X, SPAWN_PIXEL_Y, px, py, 0)) continue;
            int dx = px - SPAWN_PIXEL_X, dy = py - SPAWN_PIXEL_Y;
            int straight = (int)(0.5 + __builtin_sqrt((double)(dx * dx + 4 * dy * dy)));
            int score = d * NAV_NODE_PX - straight;      // detour length
            if (score > best_score) { best_score = score; best_x = px; best_y = py; }
        }
    }
    if (best_x < 0) { printf("NONE\n"); return 1; }
    printf("TARGET %d %d detour %d\n", best_x, best_y, best_score);
    // Walk from the spawn to the target: field towards the target.
    nav_set_goal(best_x, best_y);
    nav_rebuild_now();
    int cx = SPAWN_PIXEL_X, cy = SPAWN_PIXEL_Y;
    int tx, ty;
    while (nav_distance(cx, cy) != 0 && nav_next_step(cx, cy, &tx, &ty)) {
        int sdx = (tx / NAV_NODE_PX) - (cx / NAV_NODE_PX), sdy = (ty / NAV_NODE_PX) - (cy / NAV_NODE_PX);
        printf("STEP %d %d\n", sdx, sdy);
        cx = tx; cy = ty;
    }
    return 0;
}
