#include "arpg_campaign.h"
#include "arpg_quest.h"
#include "arpg_progress.h"
#include "arpg_inv.h"
#include "arpg_log.h"
#include <string.h>

// One row per penance (QUEST_*): the object's name, the fixed relic its delivery pays (ARPG_MECH_*, ARPG_MECH_NONE = none),
// the room where the object waits (ids of encounters_act1.c) and what the voice says in the confessional: every line comes out
// in order, one notice each (the camp toast is one line wide, so at most ~46 characters), and the last ones say how to get there.
// Tone: LORE.md 2 (the voice speaks like the dogma; it calls penance what the player sees as a theft; no modern words).
#define QUEST_LINES 6
typedef struct {
    const char *name;
    int reward_mech;
    int room;
    const char *goal;          // the mission line of the map
    const char *text[QUEST_LINES];
} QuestInfo;

enum { ROOM_CAPILLA = 10, ROOM_MISA = 11, ROOM_MONJARANA = 14, ROOM_CRIPTA = 15 };

static const QuestInfo s_quest[QUEST_COUNT] = {
    { "Lista del coro", ARPG_MECH_LLAMA_VOTIVA, ROOM_CAPILLA, "Trae la lista del coro",
      { "Don Tomás no entregó a sus muchachos.", "Trae la lista del coro de su capilla.",
        "Sube a la Nave 1 y sal por la izquierda.", "Enfermería y Osario: siempre a la izquierda.",
        "La capilla del párroco está al fondo.", 0 } },
    { "Llave de la capilla", ARPG_MECH_LANZA, ROOM_MISA, "Trae la llave de la Misa",
      { "La Misa guarda la llave de la capilla.", "En la Nave 3, sal por la izquierda.",
        "Esta penitencia es opcional.", 0, 0, 0 } },
    { "Denuncia de Sor Leonor", ARPG_MECH_PIRA, ROOM_MONJARANA, "Trae la denuncia de Sor Leonor",
      { "Sor Leonor denunció al padre Anselmo.", "Trae su denuncia de la Nave 4.",
        "Sube por las Naves 2 y 3 hasta la Nave 4.", "A la derecha: la Galería de la monjaraña.", 0, 0 } },
    { "Estandarte", ARPG_MECH_NONE, ROOM_CRIPTA, "Trae el estandarte de la Cripta",
      { "La Cripta está abierta. Te espera el estandarte.", "Está en la Nave 4, por la puerta de arriba.", 0, 0, 0, 0 } },
};

static const char *const s_done_text[3] = {
    "No queda penitencia que cumplir.", "La voz calla. Rezar ya no la mueve.", 0
};

// ---- Notices ----
#define NOTICE_MAX 12
#define NOTICE_LEN 56
static char s_notice[NOTICE_MAX][NOTICE_LEN];
static int s_notice_n = 0;

static void notice_clear(void) { s_notice_n = 0; }
static void notice_push(const char *s) {
    if (s_notice_n >= NOTICE_MAX) return;
    size_t l = strlen(s);
    if (l > NOTICE_LEN - 1) l = NOTICE_LEN - 1;
    memcpy(s_notice[s_notice_n], s, l);
    s_notice[s_notice_n][l] = 0;
    s_notice_n++;
}
static void notice_push2(const char *a, const char *b) {
    char buf[NOTICE_LEN];
    size_t la = strlen(a);
    if (la > NOTICE_LEN - 1) la = NOTICE_LEN - 1;
    memcpy(buf, a, la);
    size_t lb = strlen(b);
    if (la + lb > NOTICE_LEN - 1) lb = NOTICE_LEN - 1 - la;
    memcpy(buf + la, b, lb);
    buf[la + lb] = 0;
    notice_push(buf);
}

int arpg_campaign_notice_pending(void) { return s_notice_n; }

const char *arpg_campaign_next_notice(void) {
    static char out[NOTICE_LEN];
    if (s_notice_n <= 0) return 0;
    memcpy(out, s_notice[0], NOTICE_LEN);
    for (int i = 1; i < s_notice_n; i++) memcpy(s_notice[i - 1], s_notice[i], NOTICE_LEN);
    s_notice_n--;
    return out;
}

// ---- Loot of the descent (half of it is lost on death) ----
// The bag, the sockets and the spell slots at the moment of leaving the camp, as one hash per object. After the
// descent, a bag relic with no equal object in that list was picked up down there. Equal objects are matched one to one.
#define SNAP_MAX (ARPG_INV_BAG + ARPG_INV_SCHOOLS * ARPG_INV_SOCKETS + ARPG_INV_SPELLS)
static uint32_t s_snap[SNAP_MAX];
static int s_snap_n = 0;
static int s_snap_valid = 0;

static uint32_t item_hash(const ArpgInvItem *it) {
    const uint8_t *p = (const uint8_t *)it;
    uint32_t h = 2166136261u;
    for (unsigned i = 0; i < sizeof(*it); i++) h = (h ^ p[i]) * 16777619u;
    return h;
}

void arpg_campaign_descent_begin(void) {
    const ArpgInventory *inv = &g_arpg.inv;
    s_snap_n = 0;
    for (int i = 0; i < ARPG_INV_BAG; i++)
        if (inv->bag[i].kind != ARPG_ITEM_EMPTY) s_snap[s_snap_n++] = item_hash(&inv->bag[i]);
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++)
            if (inv->socket[s][k].kind != ARPG_ITEM_EMPTY) s_snap[s_snap_n++] = item_hash(&inv->socket[s][k]);
    for (int i = 0; i < ARPG_INV_SPELLS; i++)
        if (inv->spell[i].kind != ARPG_ITEM_EMPTY) s_snap[s_snap_n++] = item_hash(&inv->spell[i]);
    s_snap_valid = 1;
    notice_clear();         // the notices of the last visit were shown already
    arpg_world_rest();      // entering from the camp: everything is alive again (sleeping no longer does it)
}

// Half (rounded down) of the relics picked up this descent, in the bag or socketed; the last ones go first (bag slots, then
// sockets). Same "lost" criterion as the snapshot: no equal object at the camp exit, not fixed. Returns how many.
static int lose_half_of_loot(int floor_extra) {
    if (!s_snap_valid) return floor_extra;
    uint8_t used[SNAP_MAX];
    memset(used, 0, sizeof(used));
    // Candidate code: < ARPG_INV_BAG is a bag slot, else ARPG_INV_BAG + school * ARPG_INV_SOCKETS + socket.
    uint8_t fresh[ARPG_INV_BAG + ARPG_INV_SCHOOLS * ARPG_INV_SOCKETS];
    int n = 0;
    for (int c = 0; c < ARPG_INV_BAG + ARPG_INV_SCHOOLS * ARPG_INV_SOCKETS; c++) {
        const ArpgInvItem *it = c < ARPG_INV_BAG ? &g_arpg.inv.bag[c]
                                                 : &g_arpg.inv.socket[(c - ARPG_INV_BAG) / ARPG_INV_SOCKETS][(c - ARPG_INV_BAG) % ARPG_INV_SOCKETS];
        if (it->kind == ARPG_ITEM_EMPTY) continue;
        uint32_t h = item_hash(it);
        int found = 0;
        for (int j = 0; j < s_snap_n && !found; j++)
            if (!used[j] && s_snap[j] == h) { used[j] = 1; found = 1; }
        if (!found && it->kind == ARPG_ITEM_RELIC && !(it->level & ARPG_ITEM_FIXED)) fresh[n++] = (uint8_t)c;   // tomes and fixed prizes are never lost
    }
    // The relics of the floor that did not fit (floor_extra) are the last ones: they go first, and all of them are lost.
    int lose = (n + floor_extra) / 2;
    int from_bag = lose > floor_extra ? lose - floor_extra : 0;
    if (from_bag > n) from_bag = n;
    for (int k = 0; k < from_bag; k++) {
        int c = fresh[n - 1 - k];
        if (c < ARPG_INV_BAG) arpg_inv_bag_discard(c);
        else arpg_inv_socket_discard((c - ARPG_INV_BAG) / ARPG_INV_SOCKETS, (c - ARPG_INV_BAG) % ARPG_INV_SOCKETS);
    }
    if (from_bag > 0) arpg_inv_recalc();      // a socketed relic may have gone: its bonuses go with it
    return from_bag + floor_extra;
}

// ---- Carried object ----
static void lose_carried(void) {
    for (int q = 0; q < QUEST_COUNT; q++)
        if (arpg_quest_carrying(q)) notice_push2("Se ha perdido ", s_quest[q].name);
    arpg_quest_drop_carried();
}

void arpg_campaign_on_death(int floor_extra) {
    arpg_log_event(CLOG_DEATH, 0);
    notice_clear();
    int lost = lose_half_of_loot(floor_extra);
    if (lost > 0) {
        char num[4];
        if (lost > 99) lost = 99;
        if (lost >= 10) { num[0] = (char)('0' + lost / 10); num[1] = (char)('0' + lost % 10); num[2] = 0; }
        else { num[0] = (char)('0' + lost); num[1] = 0; }
        char buf[NOTICE_LEN];
        strcpy(buf, "Has perdido ");
        strcat(buf, num);
        strcat(buf, lost == 1 ? " objeto" : " objetos");
        notice_push(buf);
    }
    lose_carried();
    s_snap_valid = 0;
    arpg_world_rest();      // the cathedral fills up again (it also does when entering from the camp)
}

void arpg_campaign_on_retreat(void) {
    notice_clear();
    lose_carried();
    s_snap_valid = 0;
}

// ---- Arrival on foot ----
void arpg_campaign_arrive_on_foot(void) {
    notice_clear();
    int now = arpg_quest_deliver_all();
    for (int q = 0; q < QUEST_COUNT; q++) {
        if (!((now >> q) & 1)) continue;
        notice_push2("La voz acepta ", s_quest[q].name);
        arpg_log_event(CLOG_DELIVER, q == QUEST_TOMAS ? "tomas" : q == QUEST_MISA ? "misa" : q == QUEST_LEONOR ? "leonor" : "abanderado");
        if (s_quest[q].reward_mech == ARPG_MECH_NONE) continue;
        ArpgInvItem it;
        arpg_inv_make_reward(&it, s_quest[q].reward_mech);
        if (it.kind == ARPG_ITEM_EMPTY) continue;
        if (arpg_inv_add(&it) >= 0 || arpg_inv_stash_add(&it) >= 0) notice_push2("Recibes ", arpg_inv_item_name(&it));
    }
}

// ---- Confessional ----
void arpg_campaign_confess(void) {
    // Order: Tomas, then Leonor (+ the optional Misa), then the Abanderado. q = the penance the voice speaks of now.
    int q;
    if (!arpg_quest_delivered(QUEST_TOMAS)) q = QUEST_TOMAS;
    else if (!arpg_quest_delivered(QUEST_LEONOR)) q = QUEST_LEONOR;
    else if (!arpg_quest_delivered(QUEST_ABANDERADO)) q = QUEST_ABANDERADO;
    else q = QUEST_COUNT;
    if (q < QUEST_COUNT) {
        int given = q == QUEST_TOMAS ? 1 : q == QUEST_LEONOR ? 3 : 4;   // offered = how many penances the voice has named
        if (given > g_quest.offered) g_quest.offered = (uint8_t)given;
    }
    notice_clear();
    if (q >= QUEST_COUNT) {
        for (int i = 0; i < 3; i++)
            if (s_done_text[i]) notice_push(s_done_text[i]);
        return;
    }
    for (int i = 0; i < QUEST_LINES && s_quest[q].text[i]; i++) notice_push(s_quest[q].text[i]);
    // Leonor and the Misa are offered together: the optional one follows.
    if (q == QUEST_LEONOR && !arpg_quest_delivered(QUEST_MISA))
        for (int i = 0; i < QUEST_LINES && s_quest[QUEST_MISA].text[i]; i++) notice_push(s_quest[QUEST_MISA].text[i]);
}

// ---- Objective of the map (SELECT) ----
int arpg_campaign_objectives(ArpgObjective *out) {
    int n = 0;
    if (g_quest.carrying) {      // an object in the hand: the way is back to the camp
        out[0].room = ARPG_EXIT_TO_CAMP;
        out[0].line = "Vuelve al campamento";
        return 1;
    }
    if (g_quest.offered == 0) {
        out[0].room = -1;
        out[0].line = "Reza en la hoguera: la voz te dará penitencia.";
        return 1;
    }
    for (int q = 0; q < QUEST_COUNT; q++) {
        int given = q == QUEST_TOMAS ? 1 : q == QUEST_ABANDERADO ? 4 : 3;
        if (g_quest.offered < given || arpg_quest_delivered(q)) continue;
        if (q == QUEST_ABANDERADO && !arpg_quest_delivered(QUEST_LEONOR)) continue;
        out[n].room = s_quest[q].room;
        out[n].line = s_quest[q].goal;
        n++;
    }
    if (n == 0) { out[0].room = -1; out[0].line = "No queda penitencia que cumplir."; n = 1; }
    return n;
}
