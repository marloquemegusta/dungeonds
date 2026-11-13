#include <stdio.h>
#include <nds.h>

typedef volatile uint16_t vu16;
typedef volatile uint32_t vu32;
#define DISPLAY_WIN0_ON BIT(13)
static vu16 REG_BLDCNT, REG_BLDY, REG_WIN0H, REG_WIN0V, REG_WININ, REG_WINOUT;
static vu16 REG_BLDCNT_SUB, REG_BLDY_SUB, REG_WIN0H_SUB, REG_WIN0V_SUB, REG_WININ_SUB, REG_WINOUT_SUB;
static vu32 REG_DISPCNT, REG_DISPCNT_SUB;

#include "../../source/tide.c"

static DirtySpan s_dirty_dummy[SCREEN_H];
DirtySpan *g_dirty_cur = s_dirty_dummy;
int player_take_hit(PlayerState *p) { (void)p; return 1; }

static int s_failures;
#define CHECK(cond, msg) do { if (!(cond)) { ++s_failures; printf("FAIL: %s\n", msg); } } while (0)

int main(void) {
    CHECK(tide_speed_for_distance(-50) == TIDE_SPEED_MIN_FIXED, "negative dist clamps to min");
    CHECK(tide_speed_for_distance(0) == TIDE_SPEED_MIN_FIXED, "zero dist uses min");
    CHECK(tide_speed_for_distance(TIDE_SPRING_NEAR_PX) == TIDE_SPEED_MIN_FIXED, "near threshold uses min");
    CHECK(tide_speed_for_distance(TIDE_SPRING_FAR_PX) == TIDE_SPEED_MAX_FIXED, "far threshold uses max");
    CHECK(tide_speed_for_distance(1000) == TIDE_SPEED_MAX_FIXED, "beyond far clamps to max");

    fixed prev = tide_speed_for_distance(TIDE_SPRING_NEAR_PX);
    for (int d = TIDE_SPRING_NEAR_PX + 1; d <= TIDE_SPRING_FAR_PX; d++) {
        fixed cur = tide_speed_for_distance(d);
        CHECK(cur >= prev, "spring speed is monotonically non-decreasing");
        prev = cur;
    }

    // Even when slowed by 25% inside the tide (181 * 3 / 4 = 135), player outruns tide (40).
    CHECK(((181 * 3) >> 2) > TIDE_SPEED_MIN_FIXED * 3, "slowed player runs >3x faster than near tide");

    // When player stands still, tide eventually reaches player_y.
    fixed player_y = TO_FIXED(1000);
    tide_init(player_y);
    for (int f = 0; f < 1400; f++) tide_update(player_y);
    CHECK(tide_player_submerged(player_y), "tide reaches stationary player");

    // When player runs upward at 181 fixed/frame, tide stays behind around equilibrium (~320 px).
    player_y = TO_FIXED(5000);
    tide_init(player_y);
    for (int f = 0; f < 1000; f++) {
        player_y -= 181;
        tide_update(player_y);
    }
    int eq_dist = TO_INT(tide_y() - player_y);
    CHECK(eq_dist >= 280 && eq_dist <= 340, "tide stabilizes around elastic equilibrium when running");

    if (s_failures) return 1;
    printf("TIDE_HOST_TEST=PASS\n");
    return 0;
}
