#ifndef UPGRADES_H
#define UPGRADES_H

#include <stdint.h>
#include <stddef.h>

// DESIGN.md 6.12: in-run upgrades of the Open Heart (Dones and Relics).
// 1 of 3 Dones (stackable stats, 7 ranks) or, on levels 4/8/12/16, 1 of 3 Reliquias (once per run).
// Dones write into g_mods (modifiers.h); relics only set an owned bit that other modules read.

#define UPG_DON_COUNT   7
#define UPG_RELIC_COUNT 10
#define UPG_MAX_RANK    7

// Archetype tags (DESIGN.md 6.12.3), used to keep relic offers "con cabeza" (6.12.4).
#define UPG_TAG_RAFAGA  1u
#define UPG_TAG_VIGILIA 2u
#define UPG_TAG_MARTIR  4u
#define UPG_TAG_FUEGO   8u

enum { DON_FERVOR = 0, DON_PRISA, DON_ALCANCE, DON_BRASA, DON_RESCOLDO, DON_PASO, DON_VIDA };

enum {
    RELIC_SED_CENIZA = 0, RELIC_LANZA, RELIC_AUTO_FE, RELIC_LLAMA_VOTIVA, RELIC_CILICIO,
    RELIC_PROCESION, RELIC_MARTIRIO, RELIC_FLAGELADO, RELIC_LLAGA, RELIC_VIATICO
};

// Capabilities an upgrade can require (DESIGN.md 6.12.4 "Requisitos"). Derived from the relics owned.
#define UPG_CAP_BURN_SOURCE 1u      // owns Llama Votiva, Aura de Cilicio or Coraz�n Flagelado

enum { UPG_KIND_DON = 0, UPG_KIND_RELIC, UPG_KIND_CURA };

typedef struct {
    uint8_t kind;   // UPG_KIND_*
    uint8_t id;     // DON_* / RELIC_* (unused for the heal)
} UpgradeOffer;

// New run: xp, level, ranks, relics and the pending queue go back to the start. Call after mods_reset().
void upgrades_reset(uint32_t seed);

void upgrades_add_xp(int amount);
void upgrades_queue_levelup(void);          // debug (X key): one extra level-up at once
void upgrades_queue_relic(void);            // variant "encuentros": queues an offer that is a Reliquia (golden relicario)
int upgrades_pending(void);                 // level-ups waiting for a choice
int upgrades_level(void);
int upgrades_xp(void);
int upgrades_xp_needed(void);               // xp to go from the current level to the next

// Offer flow: begin -> read the 3 cards -> choose(i). Begin consumes nothing; choose consumes one pending level.
void upgrades_begin_offer(void);
int upgrades_offer_level(void);             // level this offer belongs to (header "NIVEL n")
int upgrades_offer_is_relic(void);
const UpgradeOffer *upgrades_offer(int i);  // i = 0..2
void upgrades_choose(int i);

// Card text for an offer. The title carries the rank the Don would reach ("Fervor II").
void upgrades_offer_title(const UpgradeOffer *o, char *buf, int buf_size);
const char *upgrades_offer_text(const UpgradeOffer *o);
int upgrades_offer_shape(const UpgradeOffer *o);        // placeholder icon shape 0..5
uint16_t upgrades_offer_color(const UpgradeOffer *o);   // RGB15 | BIT(15)
const char *upgrades_offer_art_id(const UpgradeOffer *o);   // file name of the card art (levelup_cards.h), NULL for the heal

// Damage helpers (DESIGN.md 6.12.2): every beam and every fire damage goes through one of them, so the
// modifiers (Fervor, Brasa, Llaga Abierta later) live in one place. Both return at least 1.
int upgrades_beam_damage(int base);
int upgrades_fire_damage(int base);

int upgrades_has_relic(int relic_id);       // for the weapon / fire / hit code of parts B and C
int upgrades_don_rank(int don_id);
int upgrades_llaga_missing(void);          // hearts below 5 with Llaga Abierta owned, else 0

// Design review variant (debug): 0 = A, 1 = B, 2 = C. SELECT cycles it (play and level-up screen); the level-up
// cards read it for the art treatment and g_fx_style follows it so the weapon-effect test builds keep working.
extern int g_design_variant;
void upgrades_cycle_design_variant(void);

// Scenario / playtest hook. The scenario runner reads and writes it by symbol + byte offset:
//   0  u32 apply_seq       write a new value to apply the fields below (once per change)
//   4  u32 applied_seq     (read) copy of the last apply_seq that was processed
//   8  u16 relic_mask      relics to grant (bit = RELIC_*); each one not yet owned runs its pick logic once
//  10  u8  don_ranks[7]    target ranks 0..4 per DON_*; the stat effects are applied until the rank is reached
//  17  u8  force_levelups  queue this many level-ups at once (cleared after use)
//  18  u8  design_variant  0..2; applied with apply_seq, then mirrors g_design_variant every frame
//  19  u8  level           (read)
//  20  u16 xp              (read)
//  22  u16 owned_relics    (read) relic bitmask
typedef struct {
    uint32_t apply_seq;
    uint32_t applied_seq;
    uint16_t relic_mask;
    uint8_t don_ranks[UPG_DON_COUNT];
    uint8_t force_levelups;
    uint8_t design_variant;
    uint8_t level;
    uint16_t xp;
    uint16_t owned_relics;
} UpgradesDebug;

_Static_assert(sizeof(UpgradesDebug) == 24, "UpgradesDebug layout is read by scenarios by offset");
_Static_assert(offsetof(UpgradesDebug, don_ranks) == 10, "UpgradesDebug.don_ranks offset");
_Static_assert(offsetof(UpgradesDebug, level) == 19, "UpgradesDebug.level offset");
_Static_assert(offsetof(UpgradesDebug, owned_relics) == 22, "UpgradesDebug.owned_relics offset");

extern volatile UpgradesDebug g_upg_debug;
void upgrades_debug_update(void);           // call once per frame

#endif // UPGRADES_H
