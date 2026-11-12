/*
 * Host timing of the strip rebase (source/strip.c), before and after the incremental preparation.
 * Not part of the ROM. The DS budget is in TECHNICAL.md / AGENTS.md (560190 ticks per frame): this
 * file only compares the host cost of the parts, so the work per call can be checked by ratio.
 *
 * Measured per seed (20 consecutive rebases each):
 *   REF    reference rebase (tests/host/strip_rebase_ref.c, the code before this change);
 *   SLOW   new rebase without preparation calls (the whole preparation runs inside the rebase);
 *   UNIT   one strip_prepare_step() call while the preparation runs (max and average);
 *   COMMIT new rebase with the preparation READY (the commit alone).
 * Target (task criterion): UNIT max and COMMIT max each below 8 % of the REF average.
 *
 * Build (MinGW gcc, from the worktree root):
 *   gcc -std=gnu11 -O2 -Wall -Werror -I include tests/host/strip_rebase_profile.c tests/host/strip_rebase_ref.c source/strip_kit.c -o <exe>
 */
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "arena.h"
#include "strip.h"
#include "strip_rebase_ref.h"
#include "../../source/strip.c"

const Arena *g_arena = 0;

#define REBASES 20
#define PREP_GUARD 100000
static const uint32_t s_seeds[] = { 0xC0DE1234u, 0x6A09E667u };

static long long s_qpc_hz;

static long long now_ns(void) {
    LARGE_INTEGER c;
    QueryPerformanceCounter(&c);
    long long whole = c.QuadPart / s_qpc_hz;
    long long rest = c.QuadPart % s_qpc_hz;
    return whole * 1000000000LL + (rest * 1000000000LL) / s_qpc_hz;
}

typedef struct {
    long long sum, max, min, n;
} Stat;

static void stat_add(Stat *s, long long v) {
    if (s->n == 0 || v < s->min) s->min = v;
    if (v > s->max) s->max = v;
    s->sum += v;
    s->n++;
}

static double avg_us(const Stat *s) { return s->n ? (double)s->sum / (double)s->n / 1000.0 : 0.0; }
static double max_us(const Stat *s) { return (double)s->max / 1000.0; }

int main(void) {
    LARGE_INTEGER f;
    QueryPerformanceFrequency(&f);
    s_qpc_hz = f.QuadPart;

    Stat ref = {0}, slow = {0}, unit = {0}, commit = {0};
    static const char *phase_name[] = { "IDLE (arranque)", "BANDS (una banda)", "PLAN (parte de plan)",
                                        "COUNT (cubos)", "PREFIX (1)", "PLACE (dispersion)",
                                        "INSERT (orden x)", "COPY (conservados)", "INDEX (1)" };
    Stat by_phase[PREP_READY] = {{0}};
    uint32_t peak_new = 0, steps = 0;
    uint32_t total_new_check = 0;

    for (size_t si = 0; si < sizeof(s_seeds) / sizeof(s_seeds[0]); si++) {
        uint32_t seed = s_seeds[si];

        ref_strip_start(seed);
        for (int i = 0; i < REBASES; i++) {
            long long t0 = now_ns();
            ref_strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1);
            stat_add(&ref, now_ns() - t0);
        }

        strip_start(seed);
        for (int i = 0; i < REBASES; i++) {
            long long t0 = now_ns();
            strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1);
            stat_add(&slow, now_ns() - t0);
        }

        strip_start(seed);
        for (int i = 0; i < REBASES; i++) {
            uint32_t guard = 0;
            while (s_prep_phase != PREP_READY) {
                int phase = s_prep_phase;
                long long t0 = now_ns();
                strip_prepare_step(STRIP_REBASE_TOP_PX - 1);
                long long dt = now_ns() - t0;
                stat_add(&unit, dt);
                stat_add(&by_phase[phase], dt);
                if (++guard > PREP_GUARD) {
                    printf("preparation did not finish\n");
                    return 1;
                }
            }
            if (s_prep_steps > steps) steps = s_prep_steps;
            long long t0 = now_ns();
            strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1);
            stat_add(&commit, now_ns() - t0);
        }
        if (s_stage_peak > peak_new) peak_new = s_stage_peak;
        total_new_check += s_stage_dropped;
    }

    printf("%-44s %10s %10s %10s %8s\n", "medida (host)", "avg us", "max us", "min us", "calls");
    printf("%-44s %10.2f %10.2f %10.2f %8lld\n", "REF rebase (codigo anterior)",
           avg_us(&ref), max_us(&ref), (double)ref.min / 1000.0, ref.n);
    printf("%-44s %10.2f %10.2f %10.2f %8lld\n", "NUEVO rebase sin preparar (ruta lenta)",
           avg_us(&slow), max_us(&slow), (double)slow.min / 1000.0, slow.n);
    printf("%-44s %10.2f %10.2f %10.2f %8lld\n", "NUEVO strip_prepare_step (una llamada)",
           avg_us(&unit), max_us(&unit), (double)unit.min / 1000.0, unit.n);
    printf("%-44s %10.2f %10.2f %10.2f %8lld\n", "NUEVO commit con preparacion lista",
           avg_us(&commit), max_us(&commit), (double)commit.min / 1000.0, commit.n);

    printf("\nNUEVO strip_prepare_step por fase (us):\n");
    for (int p = 0; p < PREP_READY; p++) {
        printf("  %-24s avg %8.2f  max %8.2f  llamadas %lld\n", phase_name[p],
               avg_us(&by_phase[p]), max_us(&by_phase[p]), by_phase[p].n);
    }

    double ref_avg = avg_us(&ref);
    printf("\n%% del REF medio: unit max %.1f %%, unit avg %.1f %%, commit max %.1f %%, commit avg %.1f %%\n",
           100.0 * max_us(&unit) / ref_avg, 100.0 * avg_us(&unit) / ref_avg,
           100.0 * max_us(&commit) / ref_avg, 100.0 * avg_us(&commit) / ref_avg);
    printf("units per preparation: %u (6 bands, 2 block plans in 10 parts each, chunks, prefix, index)\n",
           (unsigned)steps);
    printf("new runs per rebase: peak %u (buffer %u), dropped %u\n", (unsigned)peak_new,
           (unsigned)STRIP_STAGE_RUNS_MAX, (unsigned)total_new_check);
    return total_new_check ? 1 : 0;
}
