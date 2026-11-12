#include <stdio.h>

#include "navfield.h"
#include "strip.h"

int main(void) {
    int player_y = strip_start_y();
    int rebases = 0;
    strip_start(0x6a09e667u);
    if (strip_height_m(player_y) != 0) {
        puts("FAIL: strip start height should be zero");
        return 1;
    }
    nav_init();
    nav_set_goal(strip_start_x(), player_y);
    nav_rebuild_now();

    // Climb far enough to cross two rebases: the first fires when the actor reaches
    // STRIP_REBASE_TOP_PX, the second one STRIP_SHIFT_PX later, plus a margin. Each rebase moves
    // the live actor down with the window while preserving the logical height.
    enum { CLIMB_PX = STRIP_WIN_H_PX - 256 - STRIP_REBASE_TOP_PX + STRIP_SHIFT_PX + 128 };
    for (int climbed = 0; climbed < CLIMB_PX; climbed++) {
        player_y--;
        int shift = strip_rebase_if_needed(player_y);
        if (shift) {
            player_y += shift;
            rebases++;
            nav_shift_down(STRIP_SHIFT_PX / NAV_NODE_PX, strip_start_x(), player_y);
            nav_set_goal(strip_start_x(), player_y);
            if (nav_distance(strip_start_x(), player_y - 256) == NAV_UNREACHABLE) {
                puts("FAIL: shifted navigation must remain readable during the amortized rebuild");
                return 1;
            }
            for (int frame = 0; frame < 32; frame++) nav_update(300);
            if (nav_distance(strip_start_x(), player_y - 256) == NAV_UNREACHABLE) {
                puts("FAIL: nav lost the center-lane path after rebase");
                return 1;
            }
        }
    }
    if (rebases < 2) {
        puts("FAIL: climb did not cross two rebases");
        return 1;
    }
    // Logical height is the full climb in px (start + shift - player_y), converted like strip.c.
    if (strip_height_m(player_y) != (CLIMB_PX * 100) / STRIP_PIXELS_PER_METER_100X) {
        puts("FAIL: absolute height should include distance climbed across rebases");
        return 1;
    }
    for (int y = NAV_NODE_PX / 2; y < STRIP_WIN_H_PX; y += NAV_NODE_PX) {
        if (nav_distance(strip_start_x(), y) == NAV_UNREACHABLE) {
            puts("FAIL: the full strip lane must remain within uint8 nav distance range");
            return 1;
        }
    }
    printf("STRIP_NAV_HOST_TEST=PASS rebases=%d width=%d height=%d\n",
           rebases, nav_width(), nav_height());
    return 0;
}
