// Host test for the navigation field. Built and run by tests/test_navfield.py against the
// real baked collision grid (source/diablo_dungeon.c) and the real collision/navfield code.
#include <stdio.h>
#include <stdlib.h>
#include "navfield.h"
#include "collision.h"

static int s_failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { s_failures++; printf("FAIL: " __VA_ARGS__); printf("\n"); } } while (0)

static int walkable_node(int nx, int ny) {
    return position_is_free(TO_FIXED(nx * NAV_NODE_PX + NAV_NODE_PX / 2), TO_FIXED(ny * NAV_NODE_PX + NAV_NODE_PX / 2));
}

int main(void) {
    nav_init();
    int walkable = nav_walkable_count();
    printf("walkable nodes: %d of %d\n", walkable, NAV_W * NAV_H);
    CHECK(walkable > 200, "too few walkable nodes");

    // Goal: the player spawn.
    nav_set_goal(SPAWN_PIXEL_X, SPAWN_PIXEL_Y);
    nav_rebuild_now();
    CHECK(nav_distance(SPAWN_PIXEL_X, SPAWN_PIXEL_Y) == 0, "goal node distance must be 0");

    // Count reachable nodes; every one has a finite distance, and following the gradient
    // from each one reaches the goal in exactly that many steps without touching a wall.
    int reachable = 0, checked_paths = 0;
    for (int ny = 0; ny < NAV_H; ny++) {
        for (int nx = 0; nx < NAV_W; nx++) {
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
            if ((nx + ny) % 7 == 0) {
                checked_paths++;
                CHECK(steps == d, "path from (%d,%d) took %d steps, field says %d", nx, ny, steps, d);
            }
            if (s_failures > 20) goto done;
        }
    }
    printf("reachable nodes from spawn: %d, paths checked: %d\n", reachable, checked_paths);
    CHECK(reachable > walkable / 2, "most of the floor must be reachable from the spawn (%d of %d)", reachable, walkable);

    // The incremental search must give the same field as the one-shot search.
    {
        static uint8_t reference[NAV_W * NAV_H];
        for (int ny = 0; ny < NAV_H; ny++)
            for (int nx = 0; nx < NAV_W; nx++)
                reference[ny * NAV_W + nx] = (uint8_t)nav_distance(nx * NAV_NODE_PX + 8, ny * NAV_NODE_PX + 8);
        nav_init();
        nav_set_goal(SPAWN_PIXEL_X, SPAWN_PIXEL_Y);
        int frames = 0;
        while (nav_distance(SPAWN_PIXEL_X, SPAWN_PIXEL_Y) != 0 && frames < 200) { nav_update(300); frames++; }
        printf("incremental search finished in %d frames of 300 nodes\n", frames);
        CHECK(frames <= 40, "incremental search is too slow (%d frames)", frames);
        int diff = 0;
        for (int ny = 0; ny < NAV_H; ny++)
            for (int nx = 0; nx < NAV_W; nx++)
                diff += reference[ny * NAV_W + nx] != (uint8_t)nav_distance(nx * NAV_NODE_PX + 8, ny * NAV_NODE_PX + 8);
        CHECK(diff == 0, "incremental field differs from the one-shot field in %d nodes", diff);
    }

    // A body can stand on a node whose centre is blocked (hugging a wall): from there the
    // gradient must still lead somewhere instead of giving up.
    {
        nav_set_goal(SPAWN_PIXEL_X, SPAWN_PIXEL_Y);
        nav_rebuild_now();
        int tested = 0, failed = 0;
        for (int ny = 1; ny < NAV_H - 1; ny++) {
            for (int nx = 1; nx < NAV_W - 1; nx++) {
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
        printf("blocked-centre nodes next to the floor: %d, without a way out: %d\n", tested, failed);
        CHECK(failed == 0, "%d blocked-centre nodes have no way out", failed);
    }

    // Low walls: the walkable-line test must see a blocked node between two walkable ones.
    {
        int pairs = 0, blocked = 0;
        for (int ny = 0; ny < NAV_H; ny++) {
            for (int nx = 0; nx + 2 < NAV_W; nx++) {
                if (!walkable_node(nx, ny) || walkable_node(nx + 1, ny) || !walkable_node(nx + 2, ny)) continue;
                pairs++;
                blocked += !line_is_walkable(nx * NAV_NODE_PX + 8, ny * NAV_NODE_PX + 8, (nx + 2) * NAV_NODE_PX + 8, ny * NAV_NODE_PX + 8);
            }
        }
        printf("wall-between pairs: %d, seen as blocked: %d\n", pairs, blocked);
        CHECK(pairs == 0 || blocked * 10 >= pairs * 9, "line_is_walkable misses walls (%d of %d)", blocked, pairs);
        CHECK(line_is_walkable(SPAWN_PIXEL_X, SPAWN_PIXEL_Y, SPAWN_PIXEL_X + 3, SPAWN_PIXEL_Y), "a line of a few px on open floor must be walkable");
    }

    // A goal inside a wall is ignored; the previous goal stays.
    nav_set_goal(2, 2);
    CHECK(nav_distance(SPAWN_PIXEL_X, SPAWN_PIXEL_Y) == 0, "an unwalkable goal must not replace the current one");

done:
    printf(s_failures ? "NAV_HOST_TEST=FAIL\n" : "NAV_HOST_TEST=PASS\n");
    return s_failures ? 1 : 0;
}
