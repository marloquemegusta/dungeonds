// Host test for collision and navigation. Built and run by tests/test_navfield.py against the
// real baked arenas (source/arena_*.c) and the real collision/navfield/los code.
#include <stdio.h>
#include <stdlib.h>
#include "arena.h"
#include "navfield.h"
#include "collision.h"

static int s_failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { s_failures++; printf("FAIL: " __VA_ARGS__); printf("\n"); } } while (0)

static int walkable_node(int nx, int ny) {
    return position_is_free(TO_FIXED(nx * NAV_NODE_PX + NAV_NODE_PX / 2), TO_FIXED(ny * NAV_NODE_PX + NAV_NODE_PX / 2));
}

static void run_arena(int index) {
    arena_select(index);
    const int sx = g_arena->player_x, sy = g_arena->player_y;
    nav_init();
    const int w = nav_width(), h = nav_height();
    int walkable = nav_walkable_count();
    printf("-- arena %d \"%s\" %dx%d: %d walkable nodes of %d\n", index, g_arena->name, g_arena->world_w, g_arena->world_h, walkable, w * h);
    CHECK(walkable > 60, "too few walkable nodes");
    CHECK(w <= NAV_MAX_W && h <= NAV_MAX_H, "arena does not fit the navigation buffers");

    // The player start and every enemy spawn point stand on free floor and reach each other.
    CHECK(position_is_free(TO_FIXED(sx), TO_FIXED(sy)), "player start is not free");
    nav_set_goal(sx, sy);
    nav_rebuild_now();
    CHECK(nav_distance(sx, sy) == 0, "goal node distance must be 0");
    for (int i = 0; i < g_arena->num_enemies; i++) {
        const ArenaEnemy *e = &g_arena->enemies[i];
        CHECK(position_is_free(TO_FIXED(e->x), TO_FIXED(e->y)), "enemy %d spawn (%d,%d) is not free", i, e->x, e->y);
        CHECK(nav_distance(e->x, e->y) != NAV_UNREACHABLE, "enemy %d spawn (%d,%d) cannot reach the player start", i, e->x, e->y);
    }

    // Every reachable node has a finite distance, and following the gradient from it reaches
    // the goal in exactly that many steps without touching a wall.
    int reachable = 0, checked_paths = 0;
    for (int ny = 0; ny < h; ny++) {
        for (int nx = 0; nx < w; nx++) {
            int px = nx * NAV_NODE_PX + NAV_NODE_PX / 2, py = ny * NAV_NODE_PX + NAV_NODE_PX / 2;
            int d = nav_distance(px, py);
            if (d == NAV_UNREACHABLE) continue;
            reachable++;
            CHECK(walkable_node(nx, ny), "reachable node (%d,%d) is not walkable", nx, ny);
            int steps = 0, cx = px, cy = py;
            while (nav_distance(cx, cy) != 0 && steps < 300) {
                int tx, ty;
                if (!nav_next_step(cx, cy, &tx, &ty)) break;
                CHECK(nav_distance(tx, ty) == nav_distance(cx, cy) - 1, "gradient step does not lower the distance at (%d,%d)", cx, cy);
                CHECK(position_is_free(TO_FIXED(tx), TO_FIXED(ty)), "gradient step lands in a wall at (%d,%d)", tx, ty);
                cx = tx; cy = ty; steps++;
            }
            if ((nx + ny) % 5 == 0) {
                checked_paths++;
                CHECK(steps == d, "path from (%d,%d) took %d steps, field says %d", nx, ny, steps, d);
            }
            if (s_failures > 20) return;
        }
    }
    printf("   reachable from the start: %d, paths checked: %d\n", reachable, checked_paths);
    CHECK(reachable == walkable, "the whole floor must be one connected area (%d of %d reachable)", reachable, walkable);

    // The incremental search must give the same field as the one-shot search, within a few frames.
    {
        static uint8_t reference[NAV_MAX_W * NAV_MAX_H];
        for (int ny = 0; ny < h; ny++)
            for (int nx = 0; nx < w; nx++)
                reference[ny * w + nx] = (uint8_t)nav_distance(nx * NAV_NODE_PX + 8, ny * NAV_NODE_PX + 8);
        nav_init();
        nav_set_goal(sx, sy);
        int frames = 0;
        while (nav_distance(sx, sy) != 0 && frames < 200) { nav_update(300); frames++; }
        printf("   incremental search finished in %d frames of 300 nodes\n", frames);
        CHECK(frames <= 40, "incremental search is too slow (%d frames)", frames);
        int diff = 0;
        for (int ny = 0; ny < h; ny++)
            for (int nx = 0; nx < w; nx++)
                diff += reference[ny * w + nx] != (uint8_t)nav_distance(nx * NAV_NODE_PX + 8, ny * NAV_NODE_PX + 8);
        CHECK(diff == 0, "incremental field differs from the one-shot field in %d nodes", diff);
    }

    // A body can stand on a node whose centre is blocked (hugging a wall): from there the
    // gradient must still lead somewhere instead of giving up.
    {
        nav_set_goal(sx, sy);
        nav_rebuild_now();
        int tested = 0, failed = 0;
        for (int ny = 1; ny < h - 1; ny++) {
            for (int nx = 1; nx < w - 1; nx++) {
                int px = nx * NAV_NODE_PX + 8, py = ny * NAV_NODE_PX + 8;
                if (walkable_node(nx, ny)) continue;
                int has_reachable_neighbour = 0;
                for (int dy = -1; dy <= 1; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                        if ((dx || dy) && nav_distance(px + dx * NAV_NODE_PX, py + dy * NAV_NODE_PX) != NAV_UNREACHABLE) has_reachable_neighbour = 1;
                if (!has_reachable_neighbour) continue;
                tested++;
                int tx, ty;
                if (!nav_next_step(px, py, &tx, &ty) || nav_distance(tx, ty) == NAV_UNREACHABLE) failed++;
            }
        }
        printf("   blocked-centre nodes next to the floor: %d, without a way out: %d\n", tested, failed);
        CHECK(failed == 0, "%d blocked-centre nodes have no way out", failed);
    }

    // Open floor is walkable in a straight line; a line through the arena edge is not.
    CHECK(line_is_walkable(sx, sy, sx + 3, sy), "a line of a few px on open floor must be walkable");
    CHECK(!line_is_walkable(sx, sy, sx, -200), "a line leaving the arena must not be walkable");

    // A goal inside a wall is ignored; the previous goal stays.
    nav_set_goal(2, 2);
    CHECK(nav_distance(sx, sy) == 0, "an unwalkable goal must not replace the current one");
}

int main(void) {
    printf("arenas: %d\n", g_num_arenas);
    CHECK(g_num_arenas >= 1, "no arenas");
    for (int i = 0; i < g_num_arenas; i++) run_arena(i);
    printf(s_failures ? "NAV_HOST_TEST=FAIL\n" : "NAV_HOST_TEST=PASS\n");
    return s_failures ? 1 : 0;
}
