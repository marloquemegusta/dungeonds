#include "arena.h"

const Arena *g_arena = 0;

void arena_select(int index) {
    if (g_num_arenas <= 0) return;
    g_arena = g_arenas[((index % g_num_arenas) + g_num_arenas) % g_num_arenas];
}
