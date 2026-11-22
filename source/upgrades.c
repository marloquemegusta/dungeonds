#include "upgrades.h"
#include "modifiers.h"
#include "gameplay.h"
#include "weapons.h"
#include "arpg.h"
#include "arpg_inv.h"
#include <stdio.h>
#include <string.h>

typedef struct {
    const char *name;
    const char *text;       // starts with the moment it acts (DESIGN.md 6.12.2)
    uint8_t tags;
    uint8_t shape;
    uint16_t color;
    uint8_t requires;       // UPG_CAP_* bits that must be owned before this is offered (DESIGN.md 6.12.4); 0 = none
} UpgradeDef;

#define UC(r, g, b) (RGB15(r, g, b) | BIT(15))

// DESIGN.md 6.12.5. Muted palette, in the spirit of FX_SH_* (no primaries).
static const UpgradeDef s_dones[UPG_DON_COUNT] = {
    { "Fervor",   "Siempre: +14 % de daño del rayo.",
      UPG_TAG_RAFAGA, 0, UC(27, 17, 8) },
    { "Prisa",    "Siempre: cargas el rayo más rápido.",
      UPG_TAG_RAFAGA, 1, UC(22, 22, 14) },
    { "Alcance",  "Siempre: el rayo y la línea de apuntado llegan más lejos.",
      UPG_TAG_RAFAGA | UPG_TAG_VIGILIA, 2, UC(16, 20, 22) },
    { "Brasa",    "Siempre: +14 % de daño de fuego.",
      UPG_TAG_FUEGO, 3, UC(26, 12, 6), UPG_CAP_BURN_SOURCE },
    { "Rescoldo", "Al quemar: +1 capa de tope y la quemadura dura más.",
      UPG_TAG_VIGILIA, 4, UC(21, 10, 8), UPG_CAP_BURN_SOURCE },
    { "Paso",     "Siempre: andas un 7 % más rápido.",
      UPG_TAG_VIGILIA | UPG_TAG_MARTIR, 5, UC(15, 21, 14) },
    { "Vida",     "Al elegirla: +1 corazón de tope y curas 1.",
      UPG_TAG_MARTIR, 0, UC(27, 10, 10) },
};

// DESIGN.md 6.12.6. Tags follow the archetype table (6.12.3).
static const UpgradeDef s_relic_defs[UPG_RELIC_COUNT] = {
    { "Sed de Ceniza",
      "Al disparar: cada enemigo que matas acelera la siguiente carga; si no matas a nadie, va más lenta.",
      UPG_TAG_RAFAGA, 4, UC(19, 18, 17) },
    { "Lanza de Longinos",
      "Siempre: el rayo atraviesa a todos los enemigos, mueran o no.",
      UPG_TAG_RAFAGA | UPG_TAG_VIGILIA | UPG_TAG_MARTIR, 2, UC(28, 24, 14) },
    { "Auto de Fe",
      "Al impactar: el rayo hace el doble a los quemados y consume sus capas.",
      UPG_TAG_RAFAGA | UPG_TAG_FUEGO, 3, UC(27, 15, 7), UPG_CAP_BURN_SOURCE },
    { "Llama Votiva",
      "Mientras cargas: la línea de apuntado aplica capas de Quemado a lo que toca.",
      UPG_TAG_VIGILIA | UPG_TAG_FUEGO, 1, UC(27, 18, 7) },
    { "Aura de Cilicio",
      "Mientras cargas: un aro de brasas a tus pies quema a quien entra; crece con la carga.",
      UPG_TAG_VIGILIA | UPG_TAG_FUEGO, 4, UC(22, 11, 8) },
    { "Paso de Procesión",
      "Mientras cargas: puedes andar despacio, pero la carga es más lenta.",
      UPG_TAG_VIGILIA, 5, UC(16, 21, 15) },
    { "Martirio Contagioso",
      "Al matar a un quemado: explota con daño de fuego y quema alrededor.",
      UPG_TAG_FUEGO | UPG_TAG_VIGILIA | UPG_TAG_MARTIR, 0, UC(25, 13, 8), UPG_CAP_BURN_SOURCE },
    { "Corazón Flagelado",
      "Al recibir un golpe: onda de fuego y siguiente disparo cargado al instante.",
      UPG_TAG_MARTIR | UPG_TAG_FUEGO, 1, UC(26, 12, 11) },
    { "Llaga Abierta",
      "Al cogerla: vida máxima a la mitad. Siempre: más daño por corazón bajo 5.",
      UPG_TAG_MARTIR, 2, UC(24, 9, 9) },
    { "Viático",
      "Al matar con el rayo: a veces robas 1 corazón; más si está pegado a ti.",
      UPG_TAG_MARTIR, 3, UC(23, 21, 17) },
};

static const UpgradeDef s_cura = {
    "Cura", "Al elegirla: recuperas 1 corazón.", 0, 1, UC(27, 10, 10)
};

// Experience curve (DESIGN.md 6.12.10): level n -> n+1 costs 5 + 3 (n - 1).
#define UPG_XP_BASE 5
#define UPG_XP_STEP 3
#define UPG_MAX_PENDING 16
#define UPG_RELIC_EVERY 4       // relic offers at levels 4, 8, 12, 16
#define UPG_LAST_RELIC_LEVEL 16

int g_design_variant = 0;
volatile UpgradesDebug g_upg_debug;
static uint32_t s_dbg_seen_seq;

static int s_xp, s_level, s_pending, s_offer_level;
static uint8_t s_rank[UPG_DON_COUNT];
static uint16_t s_relic_mask;
static uint32_t s_rng = 1;
static UpgradeOffer s_offer[3];
static int s_offer_relic;

static uint32_t ups_rng_next(void) {
    s_rng = s_rng * 1664525u + 1013904223u;
    return s_rng >> 8;
}

static int rng_below(int n) { return (int)(ups_rng_next() % (uint32_t)n); }   // once per offer card, not per frame

static int s_force_relic;      // variant "encuentros": the next offer is a Reliquia

void upgrades_reset(uint32_t seed) {
    s_force_relic = 0;
    s_xp = 0;
    s_level = 1;
    s_pending = 0;
    s_offer_level = 2;
    s_relic_mask = 0;
    memset(s_rank, 0, sizeof(s_rank));
    memset(s_offer, 0, sizeof(s_offer));
    s_offer_relic = 0;
    s_rng = seed ? seed : 1u;
    s_dbg_seen_seq = g_upg_debug.apply_seq;
    g_upg_debug.force_levelups = 0;   // a queued debug level-up never survives into the new run
}

int upgrades_level(void) { return s_level; }
int upgrades_xp(void) { return s_xp; }
int upgrades_xp_needed(void) { return UPG_XP_BASE + UPG_XP_STEP * (s_level - 1); }
int upgrades_pending(void) { return s_pending; }
int upgrades_has_relic(int id) { return (unsigned)id < UPG_RELIC_COUNT && (s_relic_mask & (1u << id)) != 0; }
int upgrades_don_rank(int id) { return (unsigned)id < UPG_DON_COUNT ? s_rank[id] : 0; }
int upgrades_offer_level(void) { return s_offer_level; }
int upgrades_offer_is_relic(void) { return s_offer_relic; }
const UpgradeOffer *upgrades_offer(int i) { return &s_offer[(unsigned)i < 3u ? i : 0]; }

void upgrades_queue_levelup(void) {
    if (s_pending >= UPG_MAX_PENDING) return;
    s_level++;
    s_pending++;
}

void upgrades_add_xp(int amount) {
    s_xp += amount;
    while (s_xp >= upgrades_xp_needed() && s_pending < UPG_MAX_PENDING) {
        s_xp -= upgrades_xp_needed();
        s_level++;
        s_pending++;
    }
    if (s_xp >= upgrades_xp_needed()) s_xp = upgrades_xp_needed() - 1;   // queue full: keep the bar below the edge
}

// Variant "encuentros": Reliquias do not come by level (there are no levels): the golden relicario asks for one.
void upgrades_queue_relic(void) {
    s_force_relic = 1;
    upgrades_queue_levelup();
}

static int is_relic_level(int level) {
#if ENCOUNTERS_PROTO
    (void)level;
    return s_force_relic;
#else
    return level <= UPG_LAST_RELIC_LEVEL && (level & (UPG_RELIC_EVERY - 1)) == 0;
#endif
}

static uint32_t owned_tags(void) {
    uint32_t t = 0;
    for (int i = 0; i < UPG_RELIC_COUNT; i++)
        if (s_relic_mask & (1u << i)) t |= s_relic_defs[i].tags;
    return t;
}

// Capabilities the player has right now, derived from the relics owned. Requirements (UpgradeDef.requires)
// are checked against this when offers are built; the debug grant path does not check them.
static uint32_t owned_caps(void) {
    uint32_t c = 0;
    if (s_relic_mask & ((1u << RELIC_LLAMA_VOTIVA) | (1u << RELIC_CILICIO) | (1u << RELIC_FLAGELADO)))
        c |= UPG_CAP_BURN_SOURCE;
    return c;
}

// Builds the 3 cards for the next pending level (DESIGN.md 6.12.4).
void upgrades_begin_offer(void) {
    int n = 0;
    s_offer_relic = 0;

    if (is_relic_level(s_offer_level)) {
        int cand[UPG_RELIC_COUNT];
        int nc = 0;
        uint32_t caps = owned_caps();
        for (int i = 0; i < UPG_RELIC_COUNT; i++)
            if (!(s_relic_mask & (1u << i)) && (s_relic_defs[i].requires & ~caps) == 0) cand[nc++] = i;

        // From the 2nd relic on, one card shares an archetype with a relic already owned.
        uint32_t tags = owned_tags();
        if (tags && nc > 0) {
            int share[UPG_RELIC_COUNT];
            int ns = 0;
            for (int k = 0; k < nc; k++)
                if (s_relic_defs[cand[k]].tags & tags) share[ns++] = k;
            if (ns > 0) {
                int k = share[rng_below(ns)];
                s_offer[n].kind = UPG_KIND_RELIC;
                s_offer[n].id = (uint8_t)cand[k];
                n++;
                cand[k] = cand[--nc];
            }
        }
        while (n < 3 && nc > 0) {
            int k = rng_below(nc);
            s_offer[n].kind = UPG_KIND_RELIC;
            s_offer[n].id = (uint8_t)cand[k];
            n++;
            cand[k] = cand[--nc];
        }
        if (n > 0) s_offer_relic = 1;
    }

    // Fill with Dones that are not at their top rank, then with the heal.
    uint32_t dcaps = owned_caps();
    int avail[UPG_DON_COUNT];
    int na = 0;
    for (int i = 0; i < UPG_DON_COUNT; i++)
        if (s_rank[i] < UPG_MAX_RANK && (s_dones[i].requires & ~dcaps) == 0) avail[na++] = i;
    while (n < 3 && na > 0) {
        int k = rng_below(na);
        s_offer[n].kind = UPG_KIND_DON;
        s_offer[n].id = (uint8_t)avail[k];
        n++;
        avail[k] = avail[--na];
    }
    while (n < 3) {
        s_offer[n].kind = UPG_KIND_CURA;
        s_offer[n].id = 0;
        n++;
    }
}

static void heal_one(void) {
    if (g_player_state.hp < g_player_state.max_hp) {
        g_player_state.hp += ARPG_HEAL_PICKUP;
        if (g_player_state.hp > g_player_state.max_hp) g_player_state.hp = g_player_state.max_hp;
    }
}

// Total effect of each Don at its top rank, spread over UPG_MAX_RANK ranks (DESIGN.md 6.12.10). The cumulative
// share is rounded up, so the ranks add up exactly to the total whatever UPG_MAX_RANK is.
static int rank_step(int total, int rank) {
    return (total * rank + UPG_MAX_RANK - 1) / UPG_MAX_RANK - (total * (rank - 1) + UPG_MAX_RANK - 1) / UPG_MAX_RANK;
}

static void apply_don(int id) {
    if (s_rank[id] >= UPG_MAX_RANK) return;
    s_rank[id]++;
    switch (id) {
    case DON_FERVOR:   g_mods.sniper_damage_pct += rank_step(100, s_rank[id]); break;
    case DON_PRISA:    g_mods.sniper_aim -= rank_step(40, s_rank[id]); break;   // 48 -> 8 frames at the top rank
    case DON_ALCANCE:  g_mods.sniper_range += rank_step(256, s_rank[id]); break;
    case DON_BRASA:    g_mods.fire_dmg_pct += rank_step(100, s_rank[id]); break;
    case DON_RESCOLDO: g_mods.burn_cap_bonus += rank_step(4, s_rank[id]); g_mods.burn_dur_bonus += rank_step(120, s_rank[id]); break;
    case DON_PASO:     g_mods.speed_pct += rank_step(48, s_rank[id]); break;
    case DON_VIDA:
        int hearts = rank_step(4, s_rank[id]) * 20;   // +4 hearts over all ranks (20 life points each, ARPG); every rank still heals 1
        g_mods.max_hp += hearts;
        g_player_state.max_hp += hearts;
        heal_one();
        break;
    default: break;
    }
}

// Llaga Abierta (DESIGN.md 6.12.10): max hearts halve, rounding up (5 -> 3). Both the live value and g_mods.max_hp
// (the base player_state_init and the later Vida picks add to) drop by the same amount, so Vida still adds +1.
// In ARPG (ENCOUNTERS_PROTO), player_state_init() and arpg_inv_recalc() halve live max_hp so unequipping restores it.
static void apply_llaga(void) {
#if !ENCOUNTERS_PROTO
    int max = g_player_state.max_hp;
    int drop = max - (max + 1) / 2;
    g_mods.max_hp -= drop;
    g_player_state.max_hp = max - drop;
    if (g_player_state.hp > g_player_state.max_hp) g_player_state.hp = g_player_state.max_hp;
#endif
}

// Hearts below 5 while Llaga Abierta is owned (0 without it): the damage bonus and the crimson look read this.
int upgrades_llaga_missing(void) {
    if (!(s_relic_mask & (1u << RELIC_LLAGA))) return 0;
#if ENCOUNTERS_PROTO
    if (g_player_state.max_hp <= 0 || g_player_state.hp >= g_player_state.max_hp) return 0;
    int missing = 5 - (g_player_state.hp * 5) / g_player_state.max_hp;
    if (missing < 1) missing = 1;
    return missing > 4 ? 4 : missing;
#else
    int hearts = (g_player_state.hp + 19) / 20;     // life points -> hearts (20 per heart)
    int missing = PLAYER_MAX_HP - hearts;
    return missing > 0 ? missing : 0;
#endif
}

// Llaga Abierta damage: +20 % (or mech_val % in ARPG) per fifth / heart below the start.
static int llaga_pct(void) {
    int step = 20;
#if ENCOUNTERS_PROTO
    int mv = arpg_inv_mechanic_value(ARPG_MECH_LLAGA);
    if (mv > 0) step = mv;
#endif
    return 100 + step * upgrades_llaga_missing();
}

static void grant_relic(int id) {
    if (id >= UPG_RELIC_COUNT || (s_relic_mask & (1u << id))) return;
    s_relic_mask |= (uint16_t)(1u << id);   // behaviour lives in the weapon / fire / hit code
    if (id == RELIC_LLAGA) apply_llaga();
}

// ARPG inventory (arpg_inv.c) grants the equipped relics at the start of a run through these.
void upgrades_grant_relic(int id) {
    grant_relic(id);
}

void upgrades_set_don_rank(int id, int rank) {
    if ((unsigned)id >= UPG_DON_COUNT) return;
    if (rank > UPG_MAX_RANK) rank = UPG_MAX_RANK;
    while (s_rank[id] < rank) apply_don(id);
}

void upgrades_revoke_relic(int id) {
    if (id >= UPG_RELIC_COUNT) return;
    s_relic_mask &= (uint16_t)~(1u << id);   // the inventory un-equipped it; behaviour code stops reading it
}

void upgrades_choose(int i) {
    if (s_pending <= 0 || (unsigned)i >= 3u) return;
    const UpgradeOffer *o = &s_offer[i];
    if (o->kind == UPG_KIND_DON) apply_don(o->id);
    else if (o->kind == UPG_KIND_RELIC) grant_relic(o->id);
    else heal_one();
    s_pending--;
    s_offer_level++;
    if (s_offer_relic) s_force_relic = 0;      // a forced Reliquia offer is spent (variant "encuentros")
}

static const UpgradeDef *def_of(const UpgradeOffer *o) {
    if (o->kind == UPG_KIND_DON && o->id < UPG_DON_COUNT) return &s_dones[o->id];
    if (o->kind == UPG_KIND_RELIC && o->id < UPG_RELIC_COUNT) return &s_relic_defs[o->id];
    return &s_cura;
}

void upgrades_offer_title(const UpgradeOffer *o, char *buf, int buf_size) {
    static const char *const roman[UPG_MAX_RANK + 1] = { "", "I", "II", "III", "IV", "V", "VI", "VII" };
    const UpgradeDef *d = def_of(o);
    if (o->kind == UPG_KIND_DON) snprintf(buf, (size_t)buf_size, "%s %s", d->name, roman[s_rank[o->id] + 1]);
    else snprintf(buf, (size_t)buf_size, "%s", d->name);
}

const char *upgrades_offer_text(const UpgradeOffer *o) { return def_of(o)->text; }
int upgrades_offer_shape(const UpgradeOffer *o) { return def_of(o)->shape; }
uint16_t upgrades_offer_color(const UpgradeOffer *o) { return def_of(o)->color; }

const char *upgrades_offer_art_id(const UpgradeOffer *o) {
    static const char *const don_art[UPG_DON_COUNT] = {
        "fervor", "prisa", "alcance", "brasa", "rescoldo", "paso", "vida"
    };
    static const char *const relic_art[UPG_RELIC_COUNT] = {
        "sed_ceniza", "lanza_longinos", "auto_de_fe", "llama_votiva", "aura_cilicio",
        "paso_procesion", "martirio", "flagelado", "llaga_abierta", "viatico"
    };
    if (o->kind == UPG_KIND_DON && o->id < UPG_DON_COUNT) return don_art[o->id];
    if (o->kind == UPG_KIND_RELIC && o->id < UPG_RELIC_COUNT) return relic_art[o->id];
    return NULL;
}

void upgrades_cycle_design_variant(void) {
    g_design_variant = (g_design_variant + 1) % 3;
    g_fx_style = g_design_variant;
}

void upgrades_debug_update(void) {
    uint32_t seq = g_upg_debug.apply_seq;
    if (seq != s_dbg_seen_seq) {
        s_dbg_seen_seq = seq;
        for (int i = 0; i < UPG_RELIC_COUNT; i++)
            if (g_upg_debug.relic_mask & (1u << i)) grant_relic(i);
        for (int d = 0; d < UPG_DON_COUNT; d++) {
            int target = g_upg_debug.don_ranks[d];
            if (target > UPG_MAX_RANK) target = UPG_MAX_RANK;
            while (s_rank[d] < target) apply_don(d);
        }
        for (int n = g_upg_debug.force_levelups; n > 0; n--) upgrades_queue_levelup();
        g_upg_debug.force_levelups = 0;
        g_design_variant = g_upg_debug.design_variant % 3;
        g_fx_style = g_design_variant;
        g_upg_debug.applied_seq = seq;
    }
    g_upg_debug.design_variant = (uint8_t)g_design_variant;
    g_upg_debug.level = (uint8_t)s_level;
    g_upg_debug.xp = (uint16_t)s_xp;
    g_upg_debug.owned_relics = s_relic_mask;
}

int upgrades_beam_damage(int base) {
    int pct = g_mods.sniper_damage_pct;
#if ENCOUNTERS_PROTO
    if (upgrades_has_relic(RELIC_LANZA)) pct += arpg_inv_mechanic_value(ARPG_MECH_LANZA);
#endif
    int d = base * pct / 100;
    d = d * llaga_pct() / 100;
    return d < 1 ? 1 : d;
}

int upgrades_fire_damage(int base) {
    int d = base * g_mods.fire_dmg_pct / 100;
    d = d * llaga_pct() / 100;
    return d < 1 ? 1 : d;
}

int upgrades_punch_damage(int base) {
    int d = base * g_mods.punch_damage_pct / 100;
    d = d * llaga_pct() / 100;
    return d < 1 ? 1 : d;
}
