#include "arpg_campaign.h"
#include "arpg_quest.h"
#include "arpg_progress.h"
#include "arpg_inv.h"
#include "arpg_log.h"
#include <string.h>

// One row per penance (QUEST_*): the object's name, the fixed relic its delivery pays (ARPG_MECH_*, ARPG_MECH_NONE = none)
// and what the voice says in the confessional (lines of at most ~44 characters: the camp toast is one line wide).
// Tone: LORE.md 2 (the voice speaks like the dogma; it calls penance what the player sees as a theft; no modern words).
typedef struct {
    const char *name;
    int reward_mech;
    const char *text[3];
} QuestInfo;

static const QuestInfo s_quest[QUEST_COUNT] = {
    { "Lista del coro", ARPG_MECH_LLAMA_VOTIVA,
      { "Don Tomás no entregó a sus muchachos.", "Trae la lista del coro de su capilla.", 0 } },
    { "Llave de la capilla", ARPG_MECH_LANZA,
      { "La Misa guarda la llave de la capilla.", 0, 0 } },
    { "Denuncia de Sor Leonor", ARPG_MECH_PIRA,
      { "Sor Leonor denunció al padre Anselmo.", "Trae su denuncia de la Nave 4.", 0 } },
    { "Estandarte", ARPG_MECH_NONE,
      { "La Cripta está abierta. Te espera el estandarte.", 0, 0 } },
};

// Sor Leonor (obligatory) and la Misa (optional) are offered together once Don Tomas has been served.
static const char *const s_pair_text[3] = {
    "Sor Leonor denunció al padre Anselmo.", "Trae su denuncia de la Nave 4.", "La Misa guarda la llave de la capilla."
};
static const char *const s_done_text[3] = {
    "No queda penitencia que cumplir.", "La voz calla. Rezar ya no la mueve.", 0
};

// ---- Notices ----
#define NOTICE_MAX 6
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
static int lose_half_of_loot(void) {
    if (!s_snap_valid) return 0;
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
    int lose = n / 2;
    for (int k = 0; k < lose; k++) {
        int c = fresh[n - 1 - k];
        if (c < ARPG_INV_BAG) arpg_inv_bag_discard(c);
        else arpg_inv_socket_discard((c - ARPG_INV_BAG) / ARPG_INV_SOCKETS, (c - ARPG_INV_BAG) % ARPG_INV_SOCKETS);
    }
    return lose;
}

// ---- Carried object ----
static void lose_carried(void) {
    for (int q = 0; q < QUEST_COUNT; q++)
        if (arpg_quest_carrying(q)) notice_push2("Se ha perdido ", s_quest[q].name);
    arpg_quest_drop_carried();
}

void arpg_campaign_on_death(void) {
    arpg_log_event(CLOG_DEATH, 0);
    notice_clear();
    int lost = lose_half_of_loot();
    if (lost > 0) {
        char num[4];
        num[0] = (char)('0' + (lost > 9 ? 9 : lost));
        num[1] = 0;
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
    const char *const *text;
    if (q >= QUEST_COUNT) text = s_done_text;
    else if (q == QUEST_LEONOR && !arpg_quest_delivered(QUEST_MISA)) text = s_pair_text;   // Leonor and the Misa are offered together
    else text = s_quest[q].text;
    if (q < QUEST_COUNT) {
        int given = q == QUEST_TOMAS ? 1 : q == QUEST_LEONOR ? 3 : 4;   // offered = how many penances the voice has named
        if (given > g_quest.offered) g_quest.offered = (uint8_t)given;
    }
    notice_clear();
    for (int i = 0; i < 3; i++)
        if (text[i]) notice_push(text[i]);
}
