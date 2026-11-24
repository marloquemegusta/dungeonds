#include "room_pool.h"
#include "hwshadow.h"
#include "perfprof.h"
#include <stdio.h>
#ifdef ARM9
#include <filesystem.h>
#endif

int room_pool_fs_ready(void) {
#ifdef ARM9
    static int s_tried, s_ok;
    if (!s_tried) { s_tried = 1; s_ok = nitroFSInit(NULL); PP_NOTE("nitrofs_init ok=%d", s_ok); }
    return s_ok;
#else
    return 1;
#endif
}

// Plain .bss: the loader overwrites it, the start-up clear costs a few ms once.
static uint8_t s_pool[ROOM_POOL_BYTES] __attribute__((aligned(4)));
static uint32_t s_pool_top;

void room_pool_reset(void) {
#if HW_SHADOWS
    // The hardware shadow cache is keyed by mask pointer: the next room puts other masks at the same addresses.
    hwshadow_invalidate_range(s_pool, s_pool + ROOM_POOL_BYTES);
#endif
    s_pool_top = 0;
}

void *room_pool_alloc(uint32_t bytes) {
    const uint32_t n = (bytes + 3u) & ~3u;
    if (n > (uint32_t)ROOM_POOL_BYTES - s_pool_top) return (void *)0;
    void *p = &s_pool[s_pool_top];
    s_pool_top += n;
    return p;
}

uint32_t room_pool_mark(void) { return s_pool_top; }

void room_pool_rewind(uint32_t mark) {
    if (mark >= s_pool_top) return;
#if HW_SHADOWS
    hwshadow_invalidate_range(&s_pool[mark], s_pool + ROOM_POOL_BYTES);
#endif
    s_pool_top = mark;
}

uint32_t room_pool_used(void) { return s_pool_top; }
uint32_t room_pool_free(void) { return (uint32_t)ROOM_POOL_BYTES - s_pool_top; }
uint32_t room_pool_capacity(void) { return ROOM_POOL_BYTES; }
