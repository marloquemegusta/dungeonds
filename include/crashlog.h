#ifndef CRASHLOG_H
#define CRASHLOG_H

#include <stdint.h>

// Debug aid for hardware crashes (data/prefetch aborts). When enabled, the game
// keeps a ring of breadcrumbs and installs an exception handler that writes the
// CPU registers plus the last breadcrumbs to the SD card (/dungeonds_crash.log)
// and prints them on screen. Disabled builds compile every call away.
#ifndef CRASHLOG_ENABLED
#define CRASHLOG_ENABLED 0
#endif

#if CRASHLOG_ENABLED
void crashlog_init(void);
void crashlog_set_frame(uint32_t frame);
void crashlog_mark(uint16_t code, int32_t a, int32_t b);
// L+R+START shows the report directly, L+R+SELECT raises a real exception.
void crashlog_poll_test_trigger(void);
#define CRASH_INIT() crashlog_init()
#define CRASH_POLL() crashlog_poll_test_trigger()
#define CRASH_FRAME(f) crashlog_set_frame(f)
#define CRASH_MARK(code, a, b) crashlog_mark((code), (int32_t)(a), (int32_t)(b))
#else
#define CRASH_INIT() ((void)0)
#define CRASH_POLL() ((void)0)
#define CRASH_FRAME(f) ((void)0)
#define CRASH_MARK(code, a, b) ((void)0)
#endif

// Breadcrumb codes.
enum {
    CL_FRAME_START = 1,    // a = frame
    CL_OCCLUSION_DONE,
    CL_ENEMIES_DONE,
    CL_WEAPONS_DONE,
    CL_RENDER_START,
    CL_DRAW_ITEM,          // a = item ref, b = depth
    CL_RENDER_DONE,
    CL_PRESENT_DONE,
    CL_ENEMY_HIT = 20,     // a = type, b = hp after
    CL_ENEMY_KILL,         // a = type, b = char_id
    CL_DEATH_CHUNKS,       // a = char_id, b = dir
    CL_WAVE_SPAWN,         // a = wave
    CL_PICKUP_SPAWN,       // a = type, b = ok
    CL_DEATH_HOOK_DONE
};

#endif
