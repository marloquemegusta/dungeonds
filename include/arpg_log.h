#ifndef ARPG_LOG_H
#define ARPG_LOG_H
// Campaign play log: one line per event in /dungeonds_campana.log on the SD (buffered in RAM and appended at calm moments by arpg_log_flush; format
// `t=<s> ev=<EVENT> sala=<room> [arg=<value>]`, read by an external tool: do not change it), to compare the
// real pace of a playthrough with the simulator. Active in the normal ROM. If the SD is missing the game goes on without a file.
// The last events are also kept in RAM (g_clog) so that scenarios can read them without an SD.
#include <stdint.h>

enum { CLOG_START = 1, CLOG_CAMP_OUT, CLOG_ROOM, CLOG_PICK, CLOG_DELIVER, CLOG_DEATH, CLOG_LEVEL, CLOG_MINIBOSS, CLOG_BOSS, CLOG_CAMP_IN };

#define CLOG_RAM_MAX 64
typedef struct {
    uint32_t sec[CLOG_RAM_MAX];     // game time in seconds (frames / 60)
    uint8_t  ev[CLOG_RAM_MAX];      // CLOG_*
    int8_t   room[CLOG_RAM_MAX];    // room id at that moment (-1 = camp)
    uint8_t  n;                     // events recorded (saturates at CLOG_RAM_MAX)
} ArpgCampaignLog;
extern ArpgCampaignLog g_clog;

void arpg_log_frame(uint32_t vblanks);                       // once per main-loop pass: the game clock
void arpg_log_room(int room);                                // the room the hero is in (-1 = camp)
void arpg_log_event(int ev, const char *detail);             // detail may be NULL; goes to a RAM buffer, never touches the SD
void arpg_log_flush(void);                                   // writes the pending lines to the SD: call only outside combat (camp, loading screen, save)
#endif
