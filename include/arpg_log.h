#ifndef ARPG_LOG_H
#define ARPG_LOG_H
// Campaign play log: one line per event in /dungeonds_campana.log on the SD (append, closed after each line), to compare the
// real pace of a playthrough with the simulator. Active in the normal ROM. If the SD is missing the game goes on without a file.
// The last events are also kept in RAM (g_clog) so that scenarios can read them without an SD.
#include <stdint.h>

enum { CLOG_INICIO = 1, CLOG_SALIDA, CLOG_SALA, CLOG_COGE, CLOG_ENTREGA, CLOG_MUERTE, CLOG_NIVEL, CLOG_VENCE };

#define CLOG_RAM_MAX 64
typedef struct {
    uint32_t sec[CLOG_RAM_MAX];     // game time in seconds (frames / 60)
    uint8_t  ev[CLOG_RAM_MAX];      // CLOG_*
    int8_t   room[CLOG_RAM_MAX];    // room id at that moment (-1 = camp)
    uint8_t  n;                     // events recorded (saturates at CLOG_RAM_MAX)
} ArpgCampaignLog;
extern ArpgCampaignLog g_clog;

void arpg_log_frame(uint32_t vblanks);                       // once per main-loop pass: the game clock
void arpg_log_room(int room, const char *name);              // the room the hero is in (-1 = camp)
void arpg_log_event(int ev, const char *detail);             // detail may be NULL
#endif
