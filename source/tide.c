#include "tide.h"
#include "game.h"

static fixed s_tide_y;
static int s_hit_timer;

void tide_init(fixed player_y) {
    s_tide_y = player_y + TO_FIXED(TIDE_START_BELOW_PLAYER_PX);
    s_hit_timer = TIDE_HIT_FRAMES;
}

void tide_update(void) { s_tide_y -= TIDE_SPEED_FIXED; }
void tide_shift_y(int dy_px) { s_tide_y += TO_FIXED(dy_px); }
fixed tide_y(void) { return s_tide_y; }
int tide_player_submerged(fixed player_y) { return player_y >= s_tide_y; }
int tide_player_slowed(fixed player_y) { return tide_player_submerged(player_y); }

void tide_damage_player(PlayerState *player, fixed player_y) {
    if (!player || player->god_mode) {
        s_hit_timer = TIDE_HIT_FRAMES;
        return;
    }
    if (!tide_player_submerged(player_y)) {
        s_hit_timer = TIDE_HIT_FRAMES;
        return;
    }
    if (s_hit_timer > 0) s_hit_timer--;
    if (s_hit_timer <= 0) {
        if (player_take_hit(player)) s_hit_timer = TIDE_HIT_FRAMES;
        else s_hit_timer = 0;
    }
}

// Darkens the floor and actors below the tide line on one screen (DESIGN.md 6.0) with the
// hardware window + brightness-decrease blend, so it costs no CPU. Mode 3 in BLDCNT bits 6-7
// is "fade to black" (2 would fade to white). Without a visible tide the blend is switched off:
// with WIN0 disabled the blend would otherwise cover the whole screen.
static void tide_window_regs(vu16 *bldcnt, vu16 *bldy, vu16 *win0h, vu16 *win0v,
                             vu16 *winin, vu16 *winout, vu32 *dispcnt, int line) {
    if (line >= SCREEN_H) {
        *bldcnt = 0;
        *dispcnt &= ~DISPLAY_WIN0_ON;
        return;
    }
    // The window starts below the edge band, which stays at full brightness so it reads as a
    // line. A tide already above the screen darkens everything (the band is not drawn then).
    int top = (line < 0) ? 0 : line + TIDE_BORDER_PX;
    if (top > SCREEN_H) top = SCREEN_H;
    *bldcnt = 0x3f | (3 << 6);       // all layers, fade to black
    *bldy = TIDE_BRIGHTNESS;
    *win0h = 0x00ff;                 // x 0..255
    *win0v = (uint16_t)((top << 8) | SCREEN_H);
    *winin = 0x003f;                 // inside: every layer + colour effect
    *winout = 0x001f;                // outside: every layer, no effect
    *dispcnt |= DISPLAY_WIN0_ON;
}

void tide_render_window(int sub_screen, int camera_y) {
    int line = TO_INT(s_tide_y) - camera_y;
    if (sub_screen) {
        tide_window_regs(&REG_BLDCNT_SUB, &REG_BLDY_SUB, &REG_WIN0H_SUB, &REG_WIN0V_SUB,
                         &REG_WININ_SUB, &REG_WINOUT_SUB, &REG_DISPCNT_SUB, line);
    } else {
        tide_window_regs(&REG_BLDCNT, &REG_BLDY, &REG_WIN0H, &REG_WIN0V,
                         &REG_WININ, &REG_WINOUT, &REG_DISPCNT, line);
    }
}

void tide_render_border(uint16_t *buffer, int camera_y) {
    int line = TO_INT(s_tide_y) - camera_y;
    if (line < 0 || line >= SCREEN_H) return;
    // Bright red at the edge, fading to dark red inside the band (the fade-to-black starts below it).
    static const uint16_t edge[TIDE_BORDER_PX] = {
        RGB15(31, 8, 8) | BIT(15), RGB15(20, 3, 4) | BIT(15), RGB15(10, 1, 2) | BIT(15)
    };
    for (int dy = 0; dy < TIDE_BORDER_PX && line + dy < SCREEN_H; dy++) {
        dirty_row(line + dy, 0, SCREEN_W);
        for (int x = 0; x < SCREEN_W; x++) buffer[(line + dy) * SCREEN_W + x] = edge[dy];
    }
}
