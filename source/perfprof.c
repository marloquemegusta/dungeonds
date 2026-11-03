#include "perfprof.h"

#if PERF_PROFILE

#include "crashlog.h"
#include <fat.h>
#include <stdio.h>
#include <string.h>

#define WINDOW_FRAMES 60
#define TICKS_PER_MS 33514u

#if CRASHLOG_ENABLED
extern int crashlog_sd_ready(void);
#endif

uint32_t g_pp_cur[PP_COUNT];

static const char *const s_names[PP_COUNT] = {
    "pl", "occ", "en", "wp", "clr", "sh", "wb", "sort", "blit", "proj",
    "pick", "hud", "pcopy", "bgsub", "bgbot", "vwait", "cpu", "frame"
};
// Two-letter HUD tags (only glyphs present in the HUD font).
static const char *const s_tags[PP_COUNT] = {
    "PL", "OC", "EN", "WE", "CL", "SH", "WB", "SO", "BL", "PR",
    "PI", "HU", "PC", "BS", "BB", "VW", "CP", "FR"
};

static uint32_t s_min[PP_COUNT], s_max[PP_COUNT];
static uint64_t s_sum[PP_COUNT];
static uint32_t s_n;
static uint32_t s_vb_sum, s_vb_multi, s_see;
static uint32_t s_fi_same, s_pg_same, s_vbp_same;
static int s_have_prev;
static uint32_t s_prev_fi_par, s_prev_vb_par;
static int s_prev_page;
static uint32_t s_window_no;
static uint32_t s_sd_prev_ticks, s_sd_prev_len;

static uint32_t s_hud_avg[PP_COUNT];
static uint32_t s_hud_fps10 = 600;

static char s_hud_text[2][56];
static FILE *s_file;
static char s_line[1400];
static void build_hud_text(void);

static void reset_window(void) {
    for (int i = 0; i < PP_COUNT; i++) {
        s_min[i] = 0xFFFFFFFFu;
        s_max[i] = 0;
        s_sum[i] = 0;
    }
    s_n = s_vb_sum = s_vb_multi = s_see = 0;
    s_fi_same = s_pg_same = s_vbp_same = 0;
}

void perfprof_init(void) {
    int sd_ok;
#if CRASHLOG_ENABLED
    sd_ok = crashlog_sd_ready(); // already mounted by crashlog_init
#else
    sd_ok = fatInitDefault();
#endif
    if (sd_ok) {
        s_file = fopen("/dungeonds_perf.log", "ab");
        if (s_file) {
            fputs("BOOT perf_log=1 window=60 ticks_per_ms=33514 budget=560190\n", s_file);
            fflush(s_file);
        }
    }
    reset_window();
}

uint32_t perfprof_fps10(void) { return s_hud_fps10; }

static void write_window(uint32_t frame_index) {
    int len = snprintf(s_line, sizeof(s_line),
                       "PERF win=%lu f=%lu n=%lu vb=%lu vb2=%lu see=%lu fi_same=%lu pg_same=%lu vbp_same=%lu "
                       "sdw_ticks=%lu sdw_len=%lu",
                       (unsigned long)s_window_no, (unsigned long)frame_index, (unsigned long)s_n,
                       (unsigned long)s_vb_sum, (unsigned long)s_vb_multi, (unsigned long)s_see,
                       (unsigned long)s_fi_same, (unsigned long)s_pg_same, (unsigned long)s_vbp_same,
                       (unsigned long)s_sd_prev_ticks, (unsigned long)s_sd_prev_len);
    for (int i = 0; i < PP_COUNT && len < (int)sizeof(s_line) - 64; i++) {
        uint32_t avg = (uint32_t)(s_sum[i] / s_n);
        len += snprintf(s_line + len, sizeof(s_line) - len, " %s_min=%lu %s_avg=%lu %s_max=%lu",
                        s_names[i], (unsigned long)s_min[i], s_names[i], (unsigned long)avg,
                        s_names[i], (unsigned long)s_max[i]);
    }
    s_line[len++] = '\n';
    s_line[len] = 0;
    if (s_file) {
        uint32_t t0 = cpuGetTiming();
        fwrite(s_line, 1, len, s_file);
        fflush(s_file);
        s_sd_prev_ticks = cpuGetTiming() - t0;
        s_sd_prev_len = (uint32_t)len;
    }
}

void perfprof_frame_end(uint32_t frame_index, uint32_t vblanks, uint32_t vblank_count,
                        int active_page, int see_through) {
    for (int i = 0; i < PP_COUNT; i++) {
        uint32_t v = g_pp_cur[i];
        if (v < s_min[i]) s_min[i] = v;
        if (v > s_max[i]) s_max[i] = v;
        s_sum[i] += v;
        g_pp_cur[i] = 0;
    }
    s_n++;
    s_vb_sum += vblanks;
    if (vblanks > 1) s_vb_multi++;
    if (see_through) s_see++;
    // Does the blink phase (frame_index & 1), the displayed page and the real
    // vblank parity alternate on every presented frame? "same" counts failures.
    uint32_t fp = frame_index & 1, vp = vblank_count & 1;
    if (s_have_prev) {
        if (fp == s_prev_fi_par) s_fi_same++;
        if (active_page == s_prev_page) s_pg_same++;
        if (vp == s_prev_vb_par) s_vbp_same++;
    }
    s_have_prev = 1;
    s_prev_fi_par = fp;
    s_prev_vb_par = vp;
    s_prev_page = active_page;

    if (s_n >= WINDOW_FRAMES) {
        for (int i = 0; i < PP_COUNT; i++) s_hud_avg[i] = (uint32_t)(s_sum[i] / s_n);
        // fps*10 = n frames / (vblanks / 59.83 Hz) * 10
        s_hud_fps10 = s_vb_sum ? (s_n * 5983u) / (s_vb_sum * 10u) : 600;
        build_hud_text();
        write_window(frame_index); // once per window (~1 s); its cost is reported in the next line
        s_window_no++;
        reset_window();
    }
}

static void fmt_tenths(char *out, int size, const char *tag, uint32_t ticks) {
    uint32_t t = ticks * 10u / TICKS_PER_MS; // tenths of ms
    if (t > 999) t = 999;
    snprintf(out, size, "%s:%lu.%lu", tag, (unsigned long)(t / 10), (unsigned long)(t % 10));
}

static void build_hud_text(void) {
    // Four most expensive ranked stages of the last window (built once per window:
    // snprintf is too costly to run every frame).
    int top[4] = {-1, -1, -1, -1};
    for (int k = 0; k < 4; k++) {
        uint32_t best = 0;
        for (int i = 0; i < PP_RANKED; i++) {
            int used = 0;
            for (int j = 0; j < k; j++) used |= (top[j] == i);
            if (!used && s_hud_avg[i] > best) { best = s_hud_avg[i]; top[k] = i; }
        }
    }
    // Line 0: top 3 stages; line 1: stage 4 (unused by the HUD, kept for completeness).
    char t[4][16];
    for (int k = 0; k < 4; k++) {
        t[k][0] = 0;
        if (top[k] >= 0) fmt_tenths(t[k], sizeof(t[k]), s_tags[top[k]], s_hud_avg[top[k]]);
    }
    snprintf(s_hud_text[0], sizeof(s_hud_text[0]), "%s %s %s", t[0], t[1], t[2]);
    snprintf(s_hud_text[1], sizeof(s_hud_text[1]), "%s", t[3]);
}

void perfprof_hud_line(int n, char *out, int out_size) {
    strncpy(out, s_hud_text[n], out_size - 1);
    out[out_size - 1] = 0;
}

#endif
