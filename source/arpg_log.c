#include "arpg_log.h"
#include <nds.h>
#include "arpg_progress.h"
#include <stdio.h>
#include <string.h>

ArpgCampaignLog g_clog;

static uint32_t s_frames;
static int s_room = -1;
static char s_pend[1024];
static int s_pend_n;
static int s_root;      // 0 = fat:/, 1 = sd:/ (the one that worked last)

static const char *const s_ev_name[] = { "?", "START", "CAMP_OUT", "ROOM", "PICK", "DELIVER", "DEATH", "LEVEL", "MINIBOSS", "BOSS", "CAMP_IN" };

void arpg_log_frame(uint32_t vblanks) { s_frames = vblanks; }
void arpg_log_room(int room) { s_room = room; }

void arpg_log_event(int ev, const char *detail) {
    const uint32_t sec = s_frames / 60u;
    if (g_clog.n < CLOG_RAM_MAX) {
        const int i = g_clog.n++;
        g_clog.sec[i] = sec;
        g_clog.ev[i] = (uint8_t)ev;
        g_clog.room[i] = (int8_t)s_room;
    }
    char line[96];
    const int len = snprintf(line, sizeof(line), "t=%lu ev=%s sala=%d%s%s\n", (unsigned long)sec,
                             s_ev_name[(ev > 0 && ev <= CLOG_CAMP_IN) ? ev : 0], s_room, detail ? " arg=" : "", detail ? detail : "");
    if (len <= 0) return;
    const int n = len < (int)sizeof(line) ? len : (int)sizeof(line) - 1;
    if (s_pend_n + n > (int)sizeof(s_pend)) arpg_log_flush();      // full: only happens after a very long stretch without calm moments
    if (s_pend_n + n > (int)sizeof(s_pend)) return;
    memcpy(s_pend + s_pend_n, line, (size_t)n);
    s_pend_n += n;
}

// FAT only commits the size on fclose: open, write, close. Remembers which root worked (fat:/ or sd:/).
void arpg_log_flush(void) {
    if (s_pend_n <= 0) return;
    if (!arpg_fat_ready()) { s_pend_n = 0; return; }
    static const char *const paths[2] = { "fat:/dungeonds_campana.log", "sd:/dungeonds_campana.log" };
    for (int t = 0; t < 2; t++) {
        const int i = (s_root + t) & 1;
        FILE *f = fopen(paths[i], "ab");
        if (!f) continue;
        const int ok = fwrite(s_pend, 1, (size_t)s_pend_n, f) == (size_t)s_pend_n;
        fclose(f);
        if (ok) { s_root = i; break; }
    }
    s_pend_n = 0;       // without a card (or on a failed write) the lines are dropped; g_clog keeps the last ones
}
