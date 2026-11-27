#include "arpg_log.h"
#include <nds.h>
#include <fat.h>
#include <stdio.h>
#include <string.h>

ArpgCampaignLog g_clog;

static uint32_t s_frames;
static int s_room = -1;
static const char *s_room_name = "campamento";
static int s_fat_tried, s_fat_ok;

static const char *const s_ev_name[] = { "?", "inicio", "salida_campamento", "entra_sala", "coge", "entrega", "muerte", "nivel", "vence" };

void arpg_log_frame(uint32_t vblanks) { s_frames = vblanks; }

void arpg_log_room(int room, const char *name) {
    s_room = room;
    s_room_name = name ? name : "campamento";
}

void arpg_log_event(int ev, const char *detail) {
    const uint32_t sec = s_frames / 60u;
    if (g_clog.n < CLOG_RAM_MAX) {
        const int i = g_clog.n++;
        g_clog.sec[i] = sec;
        g_clog.ev[i] = (uint8_t)ev;
        g_clog.room[i] = (int8_t)s_room;
    }
    if (!s_fat_tried) {
        s_fat_tried = 1;
        s_fat_ok = fatInitDefault();
    }
    if (!s_fat_ok) return;
    FILE *f = fopen("fat:/dungeonds_campana.log", "ab");     // FAT only commits the size on fclose: open, write, close
    if (!f) f = fopen("sd:/dungeonds_campana.log", "ab");
    if (!f) return;
    fprintf(f, "t=%lus sala=%d(%s) %s%s%s\n", (unsigned long)sec, s_room, s_room_name,
            s_ev_name[(ev > 0 && ev <= CLOG_VENCE) ? ev : 0], detail ? " " : "", detail ? detail : "");
    fclose(f);
}
