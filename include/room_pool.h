#ifndef ROOM_POOL_H
#define ROOM_POOL_H

#include <stdint.h>

// Room pool ("deposito de sala"): one static arena of EWRAM where the art of the room that is loaded now lives
// (enemy sprites). At each loading point room_pool_reset() empties it and the loader (chars_pool.c) refills it with only
// what is about to be used. Bump allocator: no free(), only
// reset or rewind to a mark. Everything it hands out is 4-byte aligned and zero-free (not cleared).
//
// Main: the five enemy groups together take 1.370.264 B (nitrofiles/chars, headers excluded), the most any act loads at
// once, so the pool is that plus a small margin (the ARPG branch needs 1.702.000 for its heavier enemies).
#ifndef ROOM_POOL_BYTES
#define ROOM_POOL_BYTES 1372000
#endif

// NitroFS is mounted once (the room loaders can run at boot, before the sound start-up that used to mount it).
int room_pool_fs_ready(void);

void room_pool_reset(void);                 // empties the pool and drops the shadow cache entries that pointed into it
void *room_pool_alloc(uint32_t bytes);      // NULL if it does not fit (nothing is allocated then)
uint32_t room_pool_mark(void);              // current top; room_pool_rewind(mark) frees everything allocated after it
void room_pool_rewind(uint32_t mark);
uint32_t room_pool_used(void);
uint32_t room_pool_free(void);
uint32_t room_pool_capacity(void);

#endif
