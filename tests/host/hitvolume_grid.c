// Dumps, for a sniper ray at height H, which stylus points hit an enemy standing at the origin.
// Built and run by tests/test_sniper_hit_volume.py. Output: "old new" bits per point.
#include <stdio.h>
#include <stdlib.h>
#include "hitvolume.h"
#define ENEMY_HIT_RADIUS 11
#define GROUND_DY2(dy) ((dy) * (dy) * 4)

int main(int argc, char **argv) {
    int h = argc > 1 ? atoi(argv[1]) : 18;
    // Stylus at screen offset (px, up) from the feet: it aims at ground (px, -up + h).
    for (int up = -8; up <= 40; up++) {
        for (int px = -24; px <= 24; px++) {
            int dy = -up + h;
            int old_hit = px * px + GROUND_DY2(dy) <= ENEMY_HIT_RADIUS * ENEMY_HIT_RADIUS;
            int new_hit = body_hit_test(px, dy, h);
            printf("%d %d %d %d %d\n", px, up, old_hit, new_hit, 0);
        }
    }
    return 0;
}
