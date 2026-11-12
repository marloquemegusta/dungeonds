/*
 * Equivalence of the incremental rebase (source/strip.c) with the reference rebase
 * (tests/host/strip_rebase_ref.c, the code before strip_prepare_step). Host only.
 *
 * For each seed, 20 consecutive rebases; the full state is hashed after strip_start() and after
 * every rebase: map, collision, active runs (count and content, in order), row index, s_next_band
 * and s_shift_total_px. Four runs must produce the same sequence of hashes:
 *   A  reference rebase, no preparation (strip_rebase_ref.c);
 *   B  new code, preparation completed by strip_prepare_step() calls, then the commit;
 *   C  new code, no preparation calls: the rebase runs the whole preparation itself (slow path);
 *   D  new code, preparation half done (4 units) before each rebase: the rebase finishes it.
 * The harness also fails if a new-run staging buffer overflowed (s_stage_dropped), and prints the
 * largest number of new runs of one rebase (STRIP_STAGE_RUNS_MAX is the bound).
 *
 * Build (from the worktree root):
 *   gcc -std=gnu11 -O1 -Wall -Werror -I include tests/host/strip_rebase_equiv.c tests/host/strip_rebase_ref.c source/strip_kit.c -o <exe>
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "arena.h"
#include "strip.h"
#include "strip_rebase_ref.h"
#include "../../source/strip.c"

// strip.c reads g_arena; the harness defines it the same way the other host harnesses do.
const Arena *g_arena = 0;

#define REBASES 20
#define PREP_GUARD 100000
#define PARTIAL_UNITS 4
static const uint32_t s_seeds[] = { 0xC0DE1234u, 0x6A09E667u };

static uint64_t fnv(uint64_t h, const void *p, size_t n) {
    const unsigned char *b = (const unsigned char *)p;
    for (size_t i = 0; i < n; i++) {
        h ^= b[i];
        h *= 1099511628211ull;
    }
    return h;
}

static uint64_t view_hash(const StripStateView *v) {
    uint64_t h = 1469598103934665603ull;
    h = fnv(h, v->map, sizeof(uint16_t) * STRIP_W_TILES * STRIP_MAP_H_TILES);
    h = fnv(h, v->collision, sizeof(s_collision));
    h = fnv(h, &v->run_count, sizeof(v->run_count));
    h = fnv(h, v->runs, sizeof(DungeonOcclusionRun) * v->run_count);
    h = fnv(h, v->row_start, sizeof(uint32_t) * (STRIP_WIN_H_PX + 1));
    h = fnv(h, &v->next_band, sizeof(v->next_band));
    h = fnv(h, &v->shift_total_px, sizeof(v->shift_total_px));
    return h;
}

static void new_view(StripStateView *v) {
    v->map = s_map;
    v->collision = s_collision;
    v->runs = s_runs_active;
    v->run_count = s_occlusion_count;
    v->row_start = s_row_active;
    v->next_band = s_next_band;
    v->shift_total_px = s_shift_total_px;
}

enum { MODE_FULL, MODE_NONE, MODE_PARTIAL };

static int s_failures;
static uint32_t s_max_steps_per_prep;

// Hashes: [0] after strip_start, [1..REBASES] after each rebase.
// A rebase that returns 0 would leave both sides unchanged and still "match": every rebase must shift.
static void must_shift(int shifted, const char *who, int rebase) {
    if (shifted == STRIP_SHIFT_PX) return;
    printf("%s rebase %d returned %d (expected %d)\n", who, rebase, shifted, STRIP_SHIFT_PX);
    s_failures++;
}

static void run_reference(uint32_t seed, uint64_t *hashes) {
    StripStateView v;
    ref_strip_start(seed);
    ref_strip_state_view(&v);
    hashes[0] = view_hash(&v);
    for (int i = 0; i < REBASES; i++) {
        must_shift(ref_strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1), "reference", i);
        ref_strip_state_view(&v);
        hashes[i + 1] = view_hash(&v);
    }
}

static void run_new(uint32_t seed, int mode, uint64_t *hashes) {
    StripStateView v;
    strip_start(seed);
    new_view(&v);
    hashes[0] = view_hash(&v);
    for (int i = 0; i < REBASES; i++) {
        if (mode == MODE_FULL) {
            uint32_t guard = 0;
            while (s_prep_phase != PREP_READY) {
                strip_prepare_step(STRIP_REBASE_TOP_PX - 1);
                if (++guard > PREP_GUARD) {
                    printf("prepare never reached READY (rebase %d)\n", i);
                    s_failures++;
                    return;
                }
            }
            uint32_t steps_before_commit = s_prep_steps;
            must_shift(strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1), "full", i);
            if (s_prep_steps != steps_before_commit) {
                printf("MODE_FULL rebase %d ran preparation units in the commit\n", i);
                s_failures++;
            }
        } else if (mode == MODE_PARTIAL) {
            for (int u = 0; u < PARTIAL_UNITS; u++) strip_prepare_step(STRIP_REBASE_TOP_PX - 1);
            if (s_prep_phase == PREP_READY || s_prep_phase == PREP_IDLE) {
                printf("MODE_PARTIAL rebase %d: expected a half-done preparation (phase %d)\n",
                       i, s_prep_phase);
                s_failures++;
            }
            must_shift(strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1), "partial", i);
        } else {
            must_shift(strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1), "slow", i);
        }
        if (s_prep_steps > s_max_steps_per_prep) s_max_steps_per_prep = s_prep_steps;
        new_view(&v);
        hashes[i + 1] = view_hash(&v);
    }
}

static void compare(const char *name, const uint64_t *ref, const uint64_t *got, uint32_t seed) {
    for (int i = 0; i <= REBASES; i++) {
        if (ref[i] != got[i]) {
            s_failures++;
            printf("MISMATCH seed %08x %s at state %d: ref %016llx got %016llx\n", (unsigned)seed,
                   name, i, (unsigned long long)ref[i], (unsigned long long)got[i]);
            return;
        }
    }
    printf("  %-34s OK (%d states)\n", name, REBASES + 1);
}

int main(void) {
    uint64_t h_ref[REBASES + 1], h_full[REBASES + 1], h_none[REBASES + 1], h_part[REBASES + 1];
    for (size_t s = 0; s < sizeof(s_seeds) / sizeof(s_seeds[0]); s++) {
        uint32_t seed = s_seeds[s];
        printf("seed %08x\n", (unsigned)seed);
        run_reference(seed, h_ref);
        run_new(seed, MODE_FULL, h_full);
        compare("B preparation completed", h_ref, h_full, seed);
        run_new(seed, MODE_NONE, h_none);
        compare("C slow path (no preparation)", h_ref, h_none, seed);
        run_new(seed, MODE_PARTIAL, h_part);
        compare("D preparation half done", h_ref, h_part, seed);
    }
    printf("stage: peak new runs %u of %u, dropped %u, steps per preparation %u\n",
           (unsigned)s_stage_peak, (unsigned)STRIP_STAGE_RUNS_MAX, (unsigned)s_stage_dropped,
           (unsigned)s_max_steps_per_prep);
    if (s_stage_dropped != 0) {
        printf("STAGE OVERFLOW: %u new runs were dropped\n", (unsigned)s_stage_dropped);
        s_failures++;
    }
    if (s_stage_peak >= STRIP_STAGE_RUNS_MAX) {
        printf("STAGE AT CAPACITY: raise STRIP_STAGE_RUNS_MAX\n");
        s_failures++;
    }
    printf("STRIP_REBASE_EQUIV=%s\n", s_failures ? "FAIL" : "PASS");
    return s_failures ? 1 : 0;
}
