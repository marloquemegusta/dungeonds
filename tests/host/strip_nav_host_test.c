#include <stdio.h>

#include "navfield.h"
#include "strip.h"

// staged = 1 mimics main.c: nav_stage_step() in slices while the rebase is prepared, and the shift
// reuses it. The run returns a checksum of the walkable count and of the whole distance field after
// each rebase; both variants must match (the staging is only an earlier evaluation of the same data).
static uint32_t run(int staged, int *rebases_out) {
    uint32_t sum = 0;
    int player_y = strip_start_y();
    int rebases = 0;
    strip_start(0x6a09e667u);
    if (strip_height_m(player_y) != 0) {
        puts("FAIL: strip start height should be zero");
        return 0xffffffffu;
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
        strip_prepare_step(player_y);
        if (staged && strip_stage_enter()) {
            nav_stage_step(STRIP_SHIFT_PX / NAV_NODE_PX, 128, strip_stage_id());
            strip_stage_leave();
        }
        uint32_t sid = strip_stage_id();
        int shift = strip_rebase_if_needed(player_y);
        if (shift) {
            player_y += shift;
            rebases++;
            nav_shift_down(STRIP_SHIFT_PX / NAV_NODE_PX, strip_start_x(), player_y, staged ? sid : 0);
            nav_set_goal(strip_start_x(), player_y);
            if (nav_distance(strip_start_x(), player_y - 256) == NAV_UNREACHABLE) {
                puts("FAIL: shifted navigation must remain readable during the amortized rebuild");
                return 0xffffffffu;
            }
            for (int frame = 0; frame < 32; frame++) nav_update(300);
            sum = sum * 31u + (uint32_t)nav_walkable_count();
            for (int y = 0; y < STRIP_WIN_H_PX; y += NAV_NODE_PX)
                for (int x = 0; x < 512; x += NAV_NODE_PX)
                    sum = sum * 33u + (uint32_t)nav_distance(x, y);
            if (nav_distance(strip_start_x(), player_y - 256) == NAV_UNREACHABLE) {
                puts("FAIL: nav lost the center-lane path after rebase");
                return 0xffffffffu;
            }
        }
    }
    *rebases_out = rebases;
    if (rebases < 2) {
        puts("FAIL: climb did not cross two rebases");
        return 0xffffffffu;
    }
    // Logical height is the full climb in px (start + shift - player_y), converted like strip.c.
    if (strip_height_m(player_y) != (CLIMB_PX * 100) / STRIP_PIXELS_PER_METER_100X) {
        puts("FAIL: absolute height should include distance climbed across rebases");
        return 0xffffffffu;
    }
    for (int y = NAV_NODE_PX / 2; y < STRIP_WIN_H_PX; y += NAV_NODE_PX) {
        if (nav_distance(strip_start_x(), y) == NAV_UNREACHABLE) {
            puts("FAIL: the full strip lane must remain within uint8 nav distance range");
            return 0xffffffffu;
        }
    }
    return sum;
}

int main(void) {
    int rebases = 0, rebases2 = 0;
    uint32_t plain = run(0, &rebases);
    uint32_t staged = run(1, &rebases2);
    if (plain == 0xffffffffu || staged == 0xffffffffu) return 1;
    if (plain != staged || rebases != rebases2) {
        puts("FAIL: staged nav shift differs from the unstaged one");
        return 1;
    }
    printf("STRIP_NAV_HOST_TEST=PASS rebases=%d width=%d height=%d\n",
           rebases, nav_width(), nav_height());
    return 0;
}
