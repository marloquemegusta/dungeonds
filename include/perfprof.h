#ifndef PERFPROF_H
#define PERFPROF_H

#include <stdint.h>

// Profiling build (investigates why the game drops to 30 FPS on real hardware).
// PERF_PROFILE 1 times every render/logic stage with cpuGetTiming(), aggregates
// min/avg/max over 60-frame windows and appends one key=value line per window
// to /dungeonds_perf.log on the SD card. The HUD shows the most expensive
// stages in ms. It is independent of CRASHLOG_ENABLED. Set to 0 to compile
// every call away (zero overhead, original HUD).
#ifndef PERF_PROFILE
#define PERF_PROFILE 1
#endif

// Stage ids. Entries below PP_RANKED are ranked in the HUD.
enum {
    PP_PLAYER = 0,   // player_update
    PP_OCCL,         // build_occlusion_depth_map
    PP_ENEMIES,      // enemies_update
    PP_WEAPONS,      // weapons_and_effects_update
    PP_CLEAR,        // swiFastCopy clear of the bitmap buffer
    PP_SHADOW,       // draw_shadow_mask loop
    PP_WALLBASE,     // draw_hidden_wall_base
    PP_SORT,         // insertion sort of draw items
    PP_BLIT,         // actor blits (player/enemies/death chunks)
    PP_PROJ,         // enemy_projectiles_render + weapons_render
    PP_PICKUPS,      // pickups_render + encounters_render
    PP_HUD,          // draw_fps_hud
    PP_PCOPY,        // DC_FlushRange + dmaCopyWords in present_both_screens
    PP_BGSUB,        // update_screen_hardware_bg (top screen)
    PP_BGBOT,        // update_screen_hardware_bg (bottom screen)
    PP_RANKED,
    PP_VWAIT = PP_RANKED, // swiWaitForVBlank
    PP_CPU,          // frame start -> just before present (CPU work, no waiting)
    PP_FRAME,        // whole frame including the vblank wait
    PP_COUNT
};

#if PERF_PROFILE
#include <nds.h>
extern uint32_t g_pp_cur[PP_COUNT];

#define PP_T0(v) uint32_t v = cpuGetTiming()
#define PP_ADD(stage, v) (g_pp_cur[(stage)] += cpuGetTiming() - (v))
#define PP_SET(stage, ticks) (g_pp_cur[(stage)] = (ticks))
#define PP_INIT() perfprof_init()

void perfprof_init(void);
// Called once per presented frame, after all stages of that frame are in g_pp_cur.
void perfprof_frame_end(uint32_t frame_index, uint32_t vblanks, uint32_t vblank_count,
                        int active_page, int see_through);
// HUD text for line n (0..PERFPROF_HUD_LINES-1): two most expensive stages each, in ms.
#define PERFPROF_HUD_LINES 2
void perfprof_hud_line(int n, char *out, int out_size);
// Real fps * 10 measured over the last 60-frame window.
uint32_t perfprof_fps10(void);
#else
#define PP_T0(v) ((void)0)
#define PP_ADD(stage, v) ((void)0)
#define PP_SET(stage, ticks) ((void)0)
#define PP_INIT() ((void)0)
#endif

#endif
