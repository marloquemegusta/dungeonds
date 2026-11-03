#ifndef GAME_H
#define GAME_H

#include <nds.h>
#include <stdio.h>
#include <string.h>

#define SCREEN_W 256
#define SCREEN_H 192

// Fixed point 8.8 (no FPU on the Nintendo DS)
typedef int32_t fixed;
#define FIXED_SHIFT 8
#define TO_FIXED(x) ((fixed)((x) << FIXED_SHIFT))
#define TO_INT(x)   ((int)((x) >> FIXED_SHIFT))

// Half-tile helpers for the 2:1 dimetric projection.
#define TILE_HALF_W 16
#define TILE_HALF_H 8

// Direction constants (8 directions matching sprite rows)
// 0: South, 1: SW, 2: West, 3: NW, 4: North, 5: NE, 6: East, 7: SE
enum {
    DIR_SOUTH = 0,
    DIR_SOUTHWEST = 1,
    DIR_WEST = 2,
    DIR_NORTHWEST = 3,
    DIR_NORTH = 4,
    DIR_NORTHEAST = 5,
    DIR_EAST = 6,
    DIR_SOUTHEAST = 7
};

typedef struct {
    fixed x;       // 8.8 fixed point tile-space X (tile centre = int + 0.5)
    fixed y;       // 8.8 fixed point tile-space Y
    int dir;       // 0..7
    int frame;     // 0..7
    int is_moving;
    int anim_timer;
    int char_id;   // 0 = CHAR_HERO, 1 = CHAR_CHARGER
} Player;

typedef struct {
    uint32_t magic;             // 0x50455246 ("PERF")
    uint32_t frame_index;
    uint32_t cpu_ticks;         // CPU ticks taken before present/vblank
    uint32_t cpu_budget;        // 280095 ticks (100% of 1 frame at 60 FPS, 33.514 MHz)
    uint32_t cpu_percent;       // cpu_ticks * 100 / cpu_budget
    uint32_t vcount_done;       // Scanline (REG_VCOUNT) when CPU rendering completed
    uint32_t vblanks_elapsed;   // VBlanks elapsed (1 = 60fps, 2 = 30fps)
    uint32_t fps;               // Current FPS (60 / vblanks_elapsed)
    uint32_t logic_ticks;       // player_update ticks
    uint32_t top_render_ticks;  // top screen render ticks
    uint32_t bot_render_ticks;  // bottom screen render ticks
    uint32_t present_ticks;     // presentation + wait ticks
    uint32_t floor_ticks;       // draw_floor ticks
    uint32_t shadow_ticks;      // draw_shadow_mask ticks
    uint32_t blit_ticks;        // blit tiles and player ticks
    uint32_t show_hud;          // 0 = off, 1 = on
    uint32_t dirty_leaks;       // DIRTY_VERIFY: non-zero pixels left after the span clear (accumulated)
} PerfStats;

extern volatile PerfStats g_perf;

// Painted-span tracking for the bitmap BG page being drawn. Every painter calls
// dirty_row() for the pixels it writes so the next use of that page only has to
// clear those spans (x1 exclusive, empty when x0 >= x1).
typedef struct {
    uint16_t x0, x1;
} DirtySpan;
extern DirtySpan *g_dirty_cur;

static inline void dirty_row(int y, int x0, int x1) {
    if ((unsigned)y >= SCREEN_H) return;
    if (x0 < 0) x0 = 0;
    if (x1 > SCREEN_W) x1 = SCREEN_W;
    if (x0 >= x1) return;
    DirtySpan *s = &g_dirty_cur[y];
    if (x0 < (int)s->x0) s->x0 = (uint16_t)x0;
    if (x1 > (int)s->x1) s->x1 = (uint16_t)x1;
}

static inline void dirty_rect(int x0, int y0, int x1, int y1) {
    if (y0 < 0) y0 = 0;
    if (y1 > SCREEN_H) y1 = SCREEN_H;
    for (int y = y0; y < y1; y++) dirty_row(y, x0, x1);
}

#endif // GAME_H
