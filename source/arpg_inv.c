#include "arpg_inv.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "gameplay.h"
#include "modifiers.h"
#include "upgrades.h"
#include "remate.h"
#include <stdio.h>
#include <string.h>

// Todo el estado vive en g_arpg.inv para que el guardado lo escriba de un bloque (arpg_progress.c).
// LÍMITE decidido: solo Rayo, Ejecución y Pecho tienen contenido en la protodemo; Glifo y Levantar
// existen como pestañas selladas pero no se generan reliquias ni tomos suyos.

static const char *const s_rarity_name[] = { "Común", "Poco común", "Rara", "Épica", "Legendaria" };
static const char *const s_school_name[] = { "Rayo", "Ejecución", "Glifo", "Levantar", "Pecho" };
// Índice = id de mecánica (ARPG_MECH_*).
static const char *const s_mech_name[] = {
    "Glifo", "Prisa", "Sed de Ceniza", "Lanza de Longinos", "Llama Votiva", "Brasa", "Auto de Fe",
    "Zarza Ardiente", "Aura de Cilicio", "Martirio Contagioso", "Levantar", "Paso de Procesión", "Ofrenda",
    "Viático", "Corazón Flagelado", "Pira", "Llaga Abierta", "Redil", "Doble Sello"
};
static const char *const s_mech_desc[] = {
    "Sello arcano: se abre, espera y detona.",
    "Abrevia la plegaria de carga del Rayo.",
    "Abatir aviva la siguiente carga; errar la pesa.",
    "Atraviesa a todos los enemigos",
    "Al cargar, la mira prende a quien toca",
    "Aviva el ardor de las llamas",
    "Consume el fuego del enemigo",
    "Prende Quemado al esperar y detonar",
    "Aro de brasas a tus pies que quema",
    "Todo ardiente estalla al morir",
    "Liturgia de los caídos en cera.",
    "Paso lento mientras cargas la plegaria.",
    "Letanía sellada.",
    "Al abatir de cerca, restituye vida",
    "Al sufrir daño: onda y Rayo cargado",
    "Rematar a un ardiente lo hace estallar",
    "Media vida máx.; más daño por quinto herido",
    "Arrastra a todos hacia el centro",
    "Tras detonar, el sello se reabre una vez gratis."
};
// Cifra propia del aura, en línea aparte: nombre de la línea y formato (%d = mech_val). NULL = sin cifra.
static const char *const s_mech_stat_name[] = {
    0, 0, 0, "Daño", "Quemadura", "Daño", "Daño", 0, "Quemadura", "Explosión", 0, 0, 0,
    "Vida", "Onda", "Explosión", "Daño", 0, 0
};
static const char *const s_mech_stat_fmt[] = {
    0, 0, 0, "+%d %%", "%d pts/s", "+%d %%", "+%d %%", 0, "%d pts/s", "%d pts", 0, 0, 0,
    "+%d pts", "%d pts", "%d pts", "+%d %% por quinto", 0, 0
};
static const char *const s_line_name[ARPG_LINE_COUNT] = {
    "Daño", "Carga", "Alcance", "Quemadura", "Vida máx.", "Velocidad", "Maná máx.", "Regen. maná", "Cura remate", "Radio", "Espera", "Coste"
};
static const char *const s_legendary_name[] = {
    "",
    "Sello del Corazón Abierto",
    "Brasero de Pira",
    "Astilla del Estandarte",
    "Ampolla del Santo Óleo"
};
// [TUNABLE-PLACEHOLDER] cera que da desguazar, por rareza.
static const uint16_t s_wax_value[ARPG_RAR_COUNT] = { 2, 4, 8, 16, 32 };

#define MECH_COUNT ((int)(sizeof(s_mech_name) / sizeof(s_mech_name[0])))

// Delta de g_mods que aportan las líneas del equipo actual. Se guarda para aplicar solo el cambio
// al equipar/desequipar en vivo; arpg_inv_apply() lo reconstruye desde cero tras mods_reset.
typedef struct {
    int damage_rayo;     // sniper_damage_pct (%)
    int damage_ejec;     // punch_damage_pct (%)
    int charge_pct;      // % de reducción sobre 48 frames base (tope 75 %)
    int range_rayo_pct;  // % de alcance extra sobre 110 px base
    int charge;          // sniper_aim (frames recortados, negativo = más rápido)
    int range_rayo;      // sniper_range (px)
    int range_ejec;      // remate_range_bonus (%)
    int burn;            // fire_dmg_pct (%)
    int burn_ejec;       // punch_burn_pct (%)
    int life;            // max_hp (pts)
    int speed;           // speed_pct (%)
    int max_mana;        // max_mana (pts)
    int mana_regen;      // mana_regen_pct (%)
    int remate_heal;     // remate_heal_bonus (pts)
    uint16_t relic_bits; // bit = RELIC_* que una mecánica equipada activa
} InvModDelta;

static InvModDelta s_last;
static int s_have_last = 0;

static void item_clear(ArpgInvItem *it) {
    memset(it, 0, sizeof(*it));
    it->kind = ARPG_ITEM_EMPTY;
    it->mech = ARPG_MECH_NONE;
}

static void item_make(ArpgInvItem *it, uint8_t kind, uint8_t school, uint8_t rarity, uint8_t mech) {
    item_clear(it);
    it->kind = kind;
    it->school = school;
    it->rarity = rarity;
    it->mech = mech;
    it->level = 1;
    it->name_id = 0;
}

static void item_line(ArpgInvItem *it, uint8_t kind, int16_t val) {
    if (it->nlines >= 2) return;
    it->line_kind[it->nlines] = kind;
    it->line_val[it->nlines] = val;
    it->nlines++;
}

static int rarity_ok(uint8_t r) { return r < ARPG_RAR_COUNT; }

// El hechizo activo (g_arpg.spell) vuelve a Rayo si su tomo ya no está puesto.
static void fix_active_spell(void) {
    int sp = (int)g_arpg.spell;
    if (sp != ARPG_SPELL_RAYO && !arpg_inv_has_spell(sp)) g_arpg.spell = ARPG_SPELL_RAYO;
}

void arpg_inv_init(ArpgInventory *inv) {
    memset(inv, 0, sizeof(*inv));
    for (int i = 0; i < ARPG_INV_BAG; i++) item_clear(&inv->bag[i]);
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) item_clear(&inv->socket[s][k]);
    for (int i = 0; i < ARPG_INV_SPELLS; i++) item_clear(&inv->spell[i]);
    for (int i = 0; i < ARPG_INV_STASH; i++) {      // el alijo solo guarda reliquias validas
        ArpgInvItem *it = &g_arpg.stash[i];
        if (it->kind == ARPG_ITEM_EMPTY) continue;
        int bad = it->kind != ARPG_ITEM_RELIC || it->school >= ARPG_INV_SCHOOLS || it->rarity >= ARPG_RAR_COUNT ||
                  it->nlines > 2 || (it->mech >= MECH_COUNT && it->mech != ARPG_MECH_NONE);
        for (int l = 0; !bad && l < it->nlines; l++)
            if (it->line_kind[l] >= ARPG_LINE_COUNT) bad = 1;
        if (bad) item_clear(it);
    }
    item_make(&inv->spell[0], ARPG_ITEM_RAYO, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    inv->wax = 0;
}

static int add_item(ArpgInventory *inv, const ArpgInvItem *item) {
    for (int i = 0; i < ARPG_INV_BAG; i++) {
        if (inv->bag[i].kind == ARPG_ITEM_EMPTY) {
            inv->bag[i] = *item;
            return i;
        }
    }
    return -1;
}

// Partida nueva (DESIGN-ARPG.md §3): solo el Rayo equipado y la bolsa vacía; el tomo de Glifo se gana en la
// Capilla del párroco (encounters_act1.c).
void arpg_inv_new_game(void) {
    arpg_inv_init(&g_arpg.inv);
}

void arpg_inv_make_tome(ArpgInvItem *it, int school) {
    item_make(it, ARPG_ITEM_TOME, (uint8_t)school, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
}

// Fixed relic a delivered penance pays (arpg_campaign.c): Llama Votiva, Redil, Lanza de Longinos or Pira.
// Same recipes as the sample bag below. Anything else leaves `it` empty.
void arpg_inv_make_reward(ArpgInvItem *it, int mech) {
    item_clear(it);
    if (mech == ARPG_MECH_LLAMA_VOTIVA) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_RARE, ARPG_MECH_LLAMA_VOTIVA);
        it->mech_val = 24;
        item_line(it, ARPG_LINE_BURN, 12);
    } else if (mech == ARPG_MECH_REDIL) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_REDIL);
        item_line(it, ARPG_LINE_RADIUS, 12);
    } else if (mech == ARPG_MECH_LANZA) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_EPIC, ARPG_MECH_LANZA);
        it->mech_val = 28;
        item_line(it, ARPG_LINE_CHARGE, 12);
        item_line(it, ARPG_LINE_RANGE, 16);
    } else if (mech == ARPG_MECH_PIRA) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_RARE, ARPG_MECH_PIRA);
        it->mech_val = 75;
        item_line(it, ARPG_LINE_DAMAGE, 14);
    }
    if (it->kind != ARPG_ITEM_EMPTY) it->level |= ARPG_ITEM_FIXED;   // never lost on death
}

// Fixed chest prize of the act I (Cilicio, Zarza Ardiente, Llaga Abierta): same recipes as the sample bag,
// marked ARPG_ITEM_FIXED so dying never takes it. Any other mech leaves `it` empty.
void arpg_inv_make_fixed_prize(ArpgInvItem *it, int mech) {
    item_clear(it);
    if (mech == ARPG_MECH_CILICIO) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_EPIC, ARPG_MECH_CILICIO);
        it->mech_val = 26;
        item_line(it, ARPG_LINE_LIFE, 25);
        item_line(it, ARPG_LINE_SPEED, 6);
    } else if (mech == ARPG_MECH_ZARZA) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_ZARZA);
        item_line(it, ARPG_LINE_DAMAGE, 15);
    } else if (mech == ARPG_MECH_LLAGA) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_RARE, ARPG_MECH_LLAGA);
        it->mech_val = 20;
        item_line(it, ARPG_LINE_MANA, 18);
    } else if (mech == ARPG_MECH_REDIL) {
        item_make(it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_REDIL);
        item_line(it, ARPG_LINE_RADIUS, 12);
    }
    if (it->kind != ARPG_ITEM_EMPTY) it->level |= ARPG_ITEM_FIXED;
}

// Death: the bag slot is emptied (no wax; the object is simply lost).
void arpg_inv_bag_discard(int index) {
    if ((unsigned)index < ARPG_INV_BAG) item_clear(&g_arpg.inv.bag[index]);
}

// Death: a socketed relic of this descent is lost too.
void arpg_inv_socket_discard(int school, int socket) {
    if ((unsigned)school < ARPG_INV_SCHOOLS && (unsigned)socket < ARPG_INV_SOCKETS) item_clear(&g_arpg.inv.socket[school][socket]);
}

// Bolsa de ejemplo de la variante arpg-todo: reliquias de Rayo, Ejecución, Pecho y Glifo y los dos tomos.
static void add_sample_bag(void) {
    ArpgInventory *inv = &g_arpg.inv;
    ArpgInvItem it;

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_RARE, ARPG_MECH_LLAMA_VOTIVA);
    it.mech_val = 24;
    item_line(&it, ARPG_LINE_BURN, 12);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_DAMAGE, 10);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_EPIC, ARPG_MECH_LANZA);
    it.mech_val = 28;
    item_line(&it, ARPG_LINE_CHARGE, 12);
    item_line(&it, ARPG_LINE_RANGE, 16);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
    it.level = 10;
    item_line(&it, ARPG_LINE_DAMAGE, 42);
    item_line(&it, ARPG_LINE_CHARGE, 34);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_LEGENDARY, ARPG_MECH_AUTO_FE);
    it.mech_val = 120;
    it.name_id = 1;
    item_line(&it, ARPG_LINE_DAMAGE, 22);
    item_line(&it, ARPG_LINE_BURN, 18);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_RARE, ARPG_MECH_PIRA);
    it.mech_val = 75;
    item_line(&it, ARPG_LINE_DAMAGE, 14);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
    it.level = 4;
    item_line(&it, ARPG_LINE_DAMAGE, 24);
    item_line(&it, ARPG_LINE_REMATE_HEAL, 16);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_LEGENDARY, ARPG_MECH_PIRA);
    it.mech_val = 115;
    it.name_id = 2;
    item_line(&it, ARPG_LINE_BURN, 20);
    item_line(&it, ARPG_LINE_RANGE, 18);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_RANGE, 10);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_EPIC, ARPG_MECH_CILICIO);
    it.mech_val = 26;
    item_line(&it, ARPG_LINE_LIFE, 25);
    item_line(&it, ARPG_LINE_SPEED, 6);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_RARE, ARPG_MECH_LLAGA);
    it.mech_val = 20;
    item_line(&it, ARPG_LINE_MANA, 18);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    it.level = 10;
    item_line(&it, ARPG_LINE_LIFE, 68);
    add_item(inv, &it);

    // Tomos de Glifo (verde) y Levantar (negro): equipables para desbloquear hechizos.
    item_make(&it, ARPG_ITEM_TOME, ARPG_SCHOOL_GLIFO, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_TOME, ARPG_SCHOOL_LEVANTAR, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
    add_item(inv, &it);

    // Reliquias de Glifo: auras Redil y Zarza Ardiente (Raras), con una línea del hechizo cada una.
    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_REDIL);
    item_line(&it, ARPG_LINE_RADIUS, 12);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_ZARZA);
    item_line(&it, ARPG_LINE_DAMAGE, 15);
    add_item(inv, &it);
}

// Variante arpg-todo: equipa un conjunto de ejemplo de reliquias de Rayo/Ejecución/Pecho y deja
// solo el Rayo equipado (sin tomos), así el radial no abre con un único hechizo.
void arpg_inv_unlock_all(void) {
    ArpgInventory *inv = &g_arpg.inv;
    arpg_inv_new_game();
    add_sample_bag();

    item_make(&inv->spell[0], ARPG_ITEM_RAYO, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_make(&inv->spell[1], ARPG_ITEM_TOME, ARPG_SCHOOL_GLIFO, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
    item_clear(&inv->spell[2]);
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) item_clear(&inv->socket[s][k]);

    item_make(&inv->socket[ARPG_SCHOOL_RAYO][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_EPIC, ARPG_MECH_LANZA);
    inv->socket[ARPG_SCHOOL_RAYO][0].mech_val = 30;
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][0], ARPG_LINE_CHARGE, 12);
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][0], ARPG_LINE_RANGE, 15);
    item_make(&inv->socket[ARPG_SCHOOL_RAYO][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_RARE, ARPG_MECH_LLAMA_VOTIVA);
    inv->socket[ARPG_SCHOOL_RAYO][1].mech_val = 28;
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][1], ARPG_LINE_BURN, 14);
    item_make(&inv->socket[ARPG_SCHOOL_RAYO][2], ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_LEGENDARY, ARPG_MECH_AUTO_FE);
    inv->socket[ARPG_SCHOOL_RAYO][2].mech_val = 125;
    inv->socket[ARPG_SCHOOL_RAYO][2].name_id = 1;
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][2], ARPG_LINE_DAMAGE, 24);
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][2], ARPG_LINE_BURN, 18);

    item_make(&inv->socket[ARPG_SCHOOL_GLIFO][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_REDIL);
    item_make(&inv->socket[ARPG_SCHOOL_GLIFO][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_ZARZA);

    item_make(&inv->socket[ARPG_SCHOOL_EJECUCION][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_RARE, ARPG_MECH_PIRA);
    inv->socket[ARPG_SCHOOL_EJECUCION][0].mech_val = 80;
    item_line(&inv->socket[ARPG_SCHOOL_EJECUCION][0], ARPG_LINE_DAMAGE, 16);
    item_make(&inv->socket[ARPG_SCHOOL_EJECUCION][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_LEGENDARY, ARPG_MECH_PIRA);
    inv->socket[ARPG_SCHOOL_EJECUCION][1].mech_val = 120;
    inv->socket[ARPG_SCHOOL_EJECUCION][1].name_id = 2;
    item_line(&inv->socket[ARPG_SCHOOL_EJECUCION][1], ARPG_LINE_BURN, 22);
    item_line(&inv->socket[ARPG_SCHOOL_EJECUCION][1], ARPG_LINE_REMATE_HEAL, 10);

    item_make(&inv->socket[ARPG_SCHOOL_PECHO][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_EPIC, ARPG_MECH_CILICIO);
    inv->socket[ARPG_SCHOOL_PECHO][0].mech_val = 28;
    item_line(&inv->socket[ARPG_SCHOOL_PECHO][0], ARPG_LINE_LIFE, 30);
    item_line(&inv->socket[ARPG_SCHOOL_PECHO][0], ARPG_LINE_SPEED, 8);
    item_make(&inv->socket[ARPG_SCHOOL_PECHO][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_LEGENDARY, ARPG_MECH_LLAGA);
    inv->socket[ARPG_SCHOOL_PECHO][1].mech_val = 28;
    inv->socket[ARPG_SCHOOL_PECHO][1].name_id = 3;
    item_line(&inv->socket[ARPG_SCHOOL_PECHO][1], ARPG_LINE_LIFE, 40);
    item_line(&inv->socket[ARPG_SCHOOL_PECHO][1], ARPG_LINE_MANA, 30);
}

int arpg_inv_add(const ArpgInvItem *item) {
    if (!item || item->kind == ARPG_ITEM_EMPTY) return -1;
    return add_item(&g_arpg.inv, item);
}

int arpg_inv_stash_add(const ArpgInvItem *item) {
    if (!item || item->kind == ARPG_ITEM_EMPTY) return -1;
    int s = arpg_inv_first_free_stash();
    if (s < 0) return -1;
    g_arpg.stash[s] = *item;
    return s;
}

int arpg_inv_bag_count(void) {
    int n = 0;
    for (int i = 0; i < ARPG_INV_BAG; i++)
        if (g_arpg.inv.bag[i].kind != ARPG_ITEM_EMPTY) n++;
    return n;
}

int arpg_inv_bag_empty(int index) {
    if ((unsigned)index >= ARPG_INV_BAG) return 1;
    return g_arpg.inv.bag[index].kind == ARPG_ITEM_EMPTY;
}

const ArpgInvItem *arpg_inv_bag_item(int index) {
    if ((unsigned)index >= ARPG_INV_BAG) return 0;
    if (g_arpg.inv.bag[index].kind == ARPG_ITEM_EMPTY) return 0;
    return &g_arpg.inv.bag[index];
}

int arpg_inv_first_free_bag(void) {
    for (int i = 0; i < ARPG_INV_BAG; i++)
        if (g_arpg.inv.bag[i].kind == ARPG_ITEM_EMPTY) return i;
    return -1;
}

const ArpgInvItem *arpg_inv_stash_item(int index) {
    if ((unsigned)index >= ARPG_INV_STASH) return 0;
    if (g_arpg.stash[index].kind == ARPG_ITEM_EMPTY) return 0;
    return &g_arpg.stash[index];
}

int arpg_inv_first_free_stash(void) {
    for (int i = 0; i < ARPG_INV_STASH; i++)
        if (g_arpg.stash[i].kind == ARPG_ITEM_EMPTY) return i;
    return -1;
}

int arpg_inv_stash_store(int bag_index) {
    if ((unsigned)bag_index >= ARPG_INV_BAG || g_arpg.inv.bag[bag_index].kind != ARPG_ITEM_RELIC) return 0;
    int s = arpg_inv_first_free_stash();
    if (s < 0) return 0;
    g_arpg.stash[s] = g_arpg.inv.bag[bag_index];
    item_clear(&g_arpg.inv.bag[bag_index]);
    return 1;
}

int arpg_inv_stash_take(int stash_index) {
    if ((unsigned)stash_index >= ARPG_INV_STASH || g_arpg.stash[stash_index].kind == ARPG_ITEM_EMPTY) return 0;
    int b = arpg_inv_first_free_bag();
    if (b < 0) return 0;
    g_arpg.inv.bag[b] = g_arpg.stash[stash_index];
    item_clear(&g_arpg.stash[stash_index]);
    return 1;
}

int arpg_inv_stash_move(int bag_index, int stash_index) {
    if ((unsigned)bag_index >= ARPG_INV_BAG || (unsigned)stash_index >= ARPG_INV_STASH) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index], *s = &g_arpg.stash[stash_index];
    if (b->kind != ARPG_ITEM_EMPTY && b->kind != ARPG_ITEM_RELIC) return 0;   // al alijo solo van reliquias
    if (b->kind == ARPG_ITEM_EMPTY && s->kind == ARPG_ITEM_EMPTY) return 0;
    ArpgInvItem t = *b; *b = *s; *s = t;
    return 1;
}

int arpg_inv_socket_count(int school) {
    if ((unsigned)school >= ARPG_INV_SCHOOLS) return 0;
    return (school == ARPG_SCHOOL_PECHO) ? 2 : 3;
}

int arpg_inv_socket_unlock_level(int school, int socket) {
    (void)school;
    return socket <= 0 ? 1 : socket == 1 ? ARPG_SOCKET2_LEVEL : ARPG_SOCKET3_LEVEL;
}

int arpg_inv_socket_open(int school, int socket) {
    if ((unsigned)school >= ARPG_INV_SCHOOLS || (unsigned)socket >= (unsigned)arpg_inv_socket_count(school)) return 0;
#if ARPG_ALL_UNLOCKED
    return 1;
#else
    return (g_arpg.level ? (int)g_arpg.level : 1) >= arpg_inv_socket_unlock_level(school, socket);
#endif
}

// Las reliquias de un engarce cerrado (guardado viejo, nivel que baja) vuelven a la bolsa o, si esta esta llena, al alijo.
static void expel_from_locked_sockets(void) {
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) {
            ArpgInvItem *it = &g_arpg.inv.socket[s][k];
            if (it->kind == ARPG_ITEM_EMPTY || arpg_inv_socket_open(s, k)) continue;
            int b = arpg_inv_first_free_bag();
            if (b >= 0) { g_arpg.inv.bag[b] = *it; item_clear(it); continue; }
            int t = arpg_inv_first_free_stash();
            if (t >= 0) { g_arpg.stash[t] = *it; item_clear(it); }
        }
}

const ArpgInvItem *arpg_inv_socket_item(int school, int socket) {
    if ((unsigned)school >= ARPG_INV_SCHOOLS) return 0;
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school)) return 0;
    if (g_arpg.inv.socket[school][socket].kind == ARPG_ITEM_EMPTY) return 0;
    return &g_arpg.inv.socket[school][socket];
}

// Un engarce solo admite reliquias de su escuela.
static int socket_accepts(const ArpgInvItem *item, int school) {
    if (!item || item->kind != ARPG_ITEM_RELIC) return 0;
    return (int)item->school == school;
}

int arpg_inv_can_equip(const ArpgInvItem *it) {
    if (!it || it->kind == ARPG_ITEM_EMPTY) return 0;
    int req = (it->level & ARPG_ITEM_LEVEL_MASK) ? (int)(it->level & ARPG_ITEM_LEVEL_MASK) : 1;
    int hero = g_arpg.level ? (int)g_arpg.level : 1;
    return hero >= req;
}

int arpg_inv_equip_relic(int bag_index, int school, int socket) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school) || !arpg_inv_socket_open(school, socket)) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (!socket_accepts(b, school)) return 0;
    if (!arpg_inv_can_equip(b)) return 0;
    if (g_arpg.inv.socket[school][socket].kind != ARPG_ITEM_EMPTY) return 0;
    g_arpg.inv.socket[school][socket] = *b;
    item_clear(b);
    return 1;
}

int arpg_inv_swap_relic(int bag_index, int school, int socket) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school) || !arpg_inv_socket_open(school, socket)) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (!socket_accepts(b, school)) return 0;
    if (!arpg_inv_can_equip(b)) return 0;
    ArpgInvItem tmp = g_arpg.inv.socket[school][socket];
    g_arpg.inv.socket[school][socket] = *b;
    *b = tmp;
    return 1;
}

int arpg_inv_unequip_socket(int school, int socket) {
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school)) return 0;
    ArpgInvItem *s = &g_arpg.inv.socket[school][socket];
    if (s->kind == ARPG_ITEM_EMPTY) return 0;
    int slot = arpg_inv_first_free_bag();
    if (slot < 0) return 0;
    g_arpg.inv.bag[slot] = *s;
    item_clear(s);
    return 1;
}

// Un tomo entra en un hueco de hechizo libre (el 0 siempre es Rayo). Si los huecos 1..2 están llenos,
// sustituye al último y el tomo desplazado vuelve a la bolsa (en el hueco que deja el nuevo).
int arpg_inv_equip_tome(int bag_index) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (b->kind != ARPG_ITEM_TOME) return 0;
    if (!arpg_inv_can_equip(b)) return 0;
    for (int i = 1; i < ARPG_INV_SPELLS; i++) {
        if (g_arpg.inv.spell[i].kind == ARPG_ITEM_EMPTY) {
            g_arpg.inv.spell[i] = *b;
            item_clear(b);
            return 1;
        }
    }
    ArpgInvItem tmp = g_arpg.inv.spell[ARPG_INV_SPELLS - 1];
    g_arpg.inv.spell[ARPG_INV_SPELLS - 1] = *b;
    *b = tmp;
    fix_active_spell();
    return 1;
}

// Migración de guardados anteriores a la v4: el Tomo y las reliquias de Redil y Zarza de la partida nueva
// pueden faltar. Los añade a la bolsa si no están en ningún sitio (bolsa, engarces o hechizos).
static int inv_has_item(int kind, int school, int mech) {
    const ArpgInventory *inv = &g_arpg.inv;
    for (int i = 0; i < ARPG_INV_BAG; i++)
        if (inv->bag[i].kind == kind && inv->bag[i].school == school && inv->bag[i].mech == mech) return 1;
    for (int i = 0; i < ARPG_INV_SPELLS; i++)
        if (inv->spell[i].kind == kind && inv->spell[i].school == school) return 1;
    for (int k = 0; k < ARPG_INV_SOCKETS; k++)
        if (inv->socket[school][k].kind == kind && inv->socket[school][k].mech == mech) return 1;
    return 0;
}

int arpg_inv_has_tome(int school) { return inv_has_item(ARPG_ITEM_TOME, school, ARPG_MECH_NONE); }

// Guardado dañado o de otra versión: cualquier objeto con valores fuera de rango se descarta
// (la interfaz indexa tablas por rareza, escuela y línea) y el hueco 0 vuelve a ser Rayo.
void arpg_inv_sanitize(void) {
    ArpgInventory *inv = &g_arpg.inv;
    ArpgInvItem *all[ARPG_INV_BAG + ARPG_INV_SPELLS + ARPG_INV_SCHOOLS * ARPG_INV_SOCKETS];
    int n = 0;
    for (int i = 0; i < ARPG_INV_BAG; i++) all[n++] = &inv->bag[i];
    for (int i = 1; i < ARPG_INV_SPELLS; i++) all[n++] = &inv->spell[i];
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) all[n++] = &inv->socket[s][k];
    for (int i = 0; i < n; i++) {
        ArpgInvItem *it = all[i];
        if (it->kind == ARPG_ITEM_EMPTY) continue;
        int bad = (it->kind != ARPG_ITEM_RELIC && it->kind != ARPG_ITEM_TOME) || it->school >= ARPG_INV_SCHOOLS ||
                  it->rarity >= ARPG_RAR_COUNT || it->nlines > 2 || (it->mech >= MECH_COUNT && it->mech != ARPG_MECH_NONE);
        for (int l = 0; !bad && l < it->nlines; l++)
            if (it->line_kind[l] >= ARPG_LINE_COUNT) bad = 1;
        if (bad) item_clear(it);
    }
    // Un engarce o un hueco de hechizo solo admite lo suyo.
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) {
            ArpgInvItem *it = &inv->socket[s][k];
            if (it->kind != ARPG_ITEM_EMPTY && (it->kind != ARPG_ITEM_RELIC || it->school != s || k >= arpg_inv_socket_count(s)))
                item_clear(it);
        }
    for (int i = 1; i < ARPG_INV_SPELLS; i++)
        if (inv->spell[i].kind != ARPG_ITEM_EMPTY && inv->spell[i].kind != ARPG_ITEM_TOME) item_clear(&inv->spell[i]);
    item_make(&inv->spell[0], ARPG_ITEM_RAYO, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    fix_active_spell();
    expel_from_locked_sockets();
}

void arpg_inv_migrate_glifo(void) {
    ArpgInventory *inv = &g_arpg.inv;
    ArpgInvItem it;
    if (!inv_has_item(ARPG_ITEM_TOME, ARPG_SCHOOL_GLIFO, ARPG_MECH_NONE)) {
        item_make(&it, ARPG_ITEM_TOME, ARPG_SCHOOL_GLIFO, ARPG_RAR_UNCOMMON, ARPG_MECH_NONE);
        add_item(inv, &it);
    }
    if (!inv_has_item(ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_MECH_REDIL)) {
        item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_REDIL);
        item_line(&it, ARPG_LINE_RADIUS, 12);
        add_item(inv, &it);
    }
    if (!inv_has_item(ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_MECH_ZARZA)) {
        item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_GLIFO, ARPG_RAR_RARE, ARPG_MECH_ZARZA);
        item_line(&it, ARPG_LINE_DAMAGE, 15);
        add_item(inv, &it);
    }
}

int arpg_inv_unequip_tome(int school) {
    if ((unsigned)school >= ARPG_INV_SPELLS) return 0;
    ArpgInvItem *s = &g_arpg.inv.spell[school];
    if (s->kind != ARPG_ITEM_TOME) return 0;
    int slot = arpg_inv_first_free_bag();
    if (slot < 0) return 0;
    g_arpg.inv.bag[slot] = *s;
    item_clear(s);
    fix_active_spell();
    return 1;
}

int arpg_inv_wax_value(int rarity) {
    if (!rarity_ok((uint8_t)rarity)) return 0;
    return (int)s_wax_value[rarity];
}

int arpg_inv_scrap(int bag_index) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (b->kind == ARPG_ITEM_EMPTY) return 0;
    { unsigned w = (unsigned)g_arpg.inv.wax + s_wax_value[rarity_ok(b->rarity) ? b->rarity : 0]; g_arpg.inv.wax = (uint16_t)(w > 65535u ? 65535u : w); }
    item_clear(b);
    return 1;
}

int arpg_inv_has_spell(int spell) {
    if (spell == ARPG_SPELL_RAYO) return 1;
    if (spell == ARPG_SPELL_GLIFO)
        for (int i = 0; i < ARPG_INV_SPELLS; i++)
            if (g_arpg.inv.spell[i].kind == ARPG_ITEM_TOME && g_arpg.inv.spell[i].school == ARPG_SCHOOL_GLIFO)
                return 1;
    if (spell == ARPG_SPELL_LEVANTAR)
        for (int i = 0; i < ARPG_INV_SPELLS; i++)
            if (g_arpg.inv.spell[i].kind == ARPG_ITEM_TOME && g_arpg.inv.spell[i].school == ARPG_SCHOOL_LEVANTAR)
                return 1;
    return 0;
}

int arpg_inv_equipped_spell(int slot) {
    if ((unsigned)slot >= ARPG_INV_SPELLS) return -1;
    const ArpgInvItem *it = &g_arpg.inv.spell[slot];
    if (it->kind == ARPG_ITEM_RAYO) return ARPG_SPELL_RAYO;
    if (it->kind == ARPG_ITEM_TOME && it->school == ARPG_SCHOOL_GLIFO) return ARPG_SPELL_GLIFO;
    // Levantar queda fuera de la protodemo: aunque un guardado antiguo lo tenga puesto, no sale en el radial.
    return -1;
}

int arpg_inv_has_mechanic(int mech) {
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < arpg_inv_socket_count(s); k++)
            if (g_arpg.inv.socket[s][k].kind != ARPG_ITEM_EMPTY && g_arpg.inv.socket[s][k].mech == mech)
                return 1;
    return 0;
}

int arpg_inv_glifo_line(int kind) {
    int sum = 0;
    for (int k = 0; k < ARPG_INV_SOCKETS; k++) {
        const ArpgInvItem *it = &g_arpg.inv.socket[ARPG_SCHOOL_GLIFO][k];
        if (it->kind == ARPG_ITEM_EMPTY) continue;
        for (int i = 0; i < it->nlines; i++)
            if (it->line_kind[i] == kind) sum += it->line_val[i];
    }
    return sum;
}

// ---------------------------------------------------------------------------
// Modificadores: las líneas equipadas se suman a g_mods (reutiliza los Dones del roguelike).
// ---------------------------------------------------------------------------

static void line_add(InvModDelta *d, const ArpgInvItem *it, int kind, int val) {
    if (it->school == ARPG_SCHOOL_GLIFO) return;   // las líneas de Glifo se leen con arpg_inv_glifo_line()
    switch (kind) {
    case ARPG_LINE_DAMAGE:
        if (it->school == ARPG_SCHOOL_EJECUCION) d->damage_ejec += val;
        else d->damage_rayo += val;
        break;
    case ARPG_LINE_CHARGE:      d->charge_pct += val; break;
    case ARPG_LINE_RANGE:
        if (it->school == ARPG_SCHOOL_EJECUCION) d->range_ejec += val;
        else d->range_rayo_pct += val;
        break;
    case ARPG_LINE_BURN:
        d->burn += val;
        if (it->school == ARPG_SCHOOL_EJECUCION) d->burn_ejec += val;
        break;
    case ARPG_LINE_LIFE:        d->life += val; break;
    case ARPG_LINE_SPEED:       d->speed += val; break;
    case ARPG_LINE_MANA:        d->max_mana += val; break;
    case ARPG_LINE_MANA_REGEN:  d->mana_regen += val; break;
    case ARPG_LINE_REMATE_HEAL: d->remate_heal += val; break;
    default: break;
    }
}

// Reliquia del roguelike que corresponde a una mecánica equipada (-1 si no hay ninguna).
// Prisa y Brasa no tienen reliquia propia y no se tiran en el botín (Prisa es una línea de stat; Brasa se
// descartó, DESIGN-ARPG.md §5), así que aquí solo cuentan sus líneas.
static int mech_relic_bit(int mech) {
    switch (mech) {
    case ARPG_MECH_SED_CENIZA:   return RELIC_SED_CENIZA;
    case ARPG_MECH_LANZA:        return RELIC_LANZA;
    case ARPG_MECH_LLAMA_VOTIVA: return RELIC_LLAMA_VOTIVA;
    case ARPG_MECH_AUTO_FE:      return RELIC_AUTO_FE;
    case ARPG_MECH_CILICIO:      return RELIC_CILICIO;
    case ARPG_MECH_MARTIRIO:     return RELIC_MARTIRIO;
    case ARPG_MECH_PROCESION:    return RELIC_PROCESION;
    case ARPG_MECH_VIATICO:      return RELIC_VIATICO;
    case ARPG_MECH_FLAGELADO:    return RELIC_FLAGELADO;
    case ARPG_MECH_LLAGA:        return RELIC_LLAGA;
    default:                     return -1;
    }
}

static int calc_max_hp(void) {
    int full_hp = BAL(hero_hp_base, ARPG_HP_BASE) + (g_arpg_level - 1) * BAL(hero_hp_level, ARPG_HP_PER_LEVEL) + g_mods.max_hp;
    int hp = upgrades_has_relic(RELIC_LLAGA) ? (full_hp + 1) / 2 : full_hp;
    return hp < 1 ? 1 : hp;
}

static int calc_max_mana(void) {
    int m = BAL(hero_mana_base, ARPG_MANA_BASE) + (g_arpg_level - 1) * BAL(hero_mana_level, ARPG_MANA_PER_LEVEL) + g_mods.max_mana;
    return m < 10 ? 10 : m;
}

static void compute_delta(InvModDelta *d) {
    memset(d, 0, sizeof(*d));
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++) {
        for (int k = 0; k < arpg_inv_socket_count(s); k++) {
            const ArpgInvItem *it = arpg_inv_socket_item(s, k);
            if (!it) continue;
            for (int i = 0; i < it->nlines && i < 2; i++)
                line_add(d, it, it->line_kind[i], it->line_val[i]);
            int bit = mech_relic_bit(it->mech);
            if (bit >= 0) d->relic_bits |= (uint16_t)(1u << bit);
        }
    }
    int cp = d->charge_pct;
    if (cp > 75) cp = 75;
    if (cp < 0) cp = 0;
    d->charge = -(48 * cp + 50) / 100;
    d->range_rayo = (110 * d->range_rayo_pct + 50) / 100;
}

static void apply_delta(const InvModDelta *d) {
    g_mods.sniper_damage_pct += d->damage_rayo;
    g_mods.punch_damage_pct += d->damage_ejec;
    g_mods.sniper_aim += d->charge;
    g_mods.sniper_range += d->range_rayo;
    g_mods.remate_range_bonus += d->range_ejec;
    g_mods.fire_dmg_pct += d->burn;
    g_mods.punch_burn_pct += d->burn_ejec;
    g_mods.max_hp += d->life;
    g_mods.speed_pct += d->speed;
    g_mods.max_mana += d->max_mana;
    g_mods.mana_regen_pct += d->mana_regen;
    g_mods.remate_heal_bonus += d->remate_heal;
}

void arpg_inv_apply(void) {
    fix_active_spell();
    InvModDelta d;
    compute_delta(&d);
    apply_delta(&d);
    for (int id = 0; id < UPG_RELIC_COUNT; id++)
        if (d.relic_bits & (1u << id)) upgrades_grant_relic(id);
    s_last = d;
    s_have_last = 1;
}

void arpg_inv_ensure_applied(void) {
    if (!s_have_last) arpg_inv_recalc();
}

// En vivo: aplica solo la diferencia de líneas, actualiza reliquias por mecánica y recalcula
// Vida máx. y Maná máx. de g_player_state al instante.
void arpg_inv_recalc(void) {
    expel_from_locked_sockets();
    InvModDelta d;
    compute_delta(&d);
    if (!s_have_last) {
        memset(&s_last, 0, sizeof(s_last));
        s_have_last = 1;
    }
    InvModDelta diff;
    diff.damage_rayo = d.damage_rayo - s_last.damage_rayo;
    diff.damage_ejec = d.damage_ejec - s_last.damage_ejec;
    diff.charge_pct = 0;
    diff.range_rayo_pct = 0;
    diff.charge = d.charge - s_last.charge;
    diff.range_rayo = d.range_rayo - s_last.range_rayo;
    diff.range_ejec = d.range_ejec - s_last.range_ejec;
    diff.burn = d.burn - s_last.burn;
    diff.burn_ejec = d.burn_ejec - s_last.burn_ejec;
    diff.life = d.life - s_last.life;
    diff.speed = d.speed - s_last.speed;
    diff.max_mana = d.max_mana - s_last.max_mana;
    diff.mana_regen = d.mana_regen - s_last.mana_regen;
    diff.remate_heal = d.remate_heal - s_last.remate_heal;
    diff.relic_bits = 0;
    apply_delta(&diff);
    for (int id = 0; id < UPG_RELIC_COUNT; id++) {
        int was = (s_last.relic_bits >> id) & 1, now = (d.relic_bits >> id) & 1;
        if (was && !now) upgrades_revoke_relic(id);
        else if (!was && now) upgrades_grant_relic(id);
    }
    if (g_player_state.max_hp > 0) {
        int new_max_hp = calc_max_hp();
        g_player_state.max_hp = new_max_hp;
        if (g_player_state.hp > new_max_hp) g_player_state.hp = new_max_hp;
        if (g_player_state.hp < 1 && !g_player_state.is_dead) g_player_state.hp = 1;

        int new_max_mana = calc_max_mana();
        g_player_state.max_mana = new_max_mana;
        if (g_player_state.mana > new_max_mana) g_player_state.mana = new_max_mana;
    }
    s_last = d;
}

int arpg_inv_preview_socket(int bag_index, int school, int socket, ArpgInvPreview *out) {
    if (!out) return 0;
    for (int i = 0; i < ARPG_LINE_COUNT; i++) { out->before[i] = 0; out->after[i] = 0; }
    out->valid = 0;
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school)) return 0;
    const ArpgInvItem *item = arpg_inv_bag_item(bag_index);
    if (!socket_accepts(item, school)) return 0;

    // Mismo recorrido que compute_delta(): solo los engarces de esa escuela y sus líneas.
    for (int k = 0; k < arpg_inv_socket_count(school); k++) {
        const ArpgInvItem *cur = arpg_inv_socket_item(school, k);
        const ArpgInvItem *use = (k == socket) ? item : cur;
        if (cur)
            for (int i = 0; i < cur->nlines && i < 2; i++)
                out->before[cur->line_kind[i]] += cur->line_val[i];
        if (use)
            for (int i = 0; i < use->nlines && i < 2; i++)
                out->after[use->line_kind[i]] += use->line_val[i];
    }
    out->valid = 1;
    return 1;
}

const char *arpg_inv_rarity_name(int rarity) {
    return rarity_ok((uint8_t)rarity) ? s_rarity_name[rarity] : "";
}

const char *arpg_inv_school_name(int school) {
    return ((unsigned)school < ARPG_INV_SCHOOLS) ? s_school_name[school] : "";
}

const char *arpg_inv_mechanic_name(int mech) {
    return ((unsigned)mech < (unsigned)MECH_COUNT) ? s_mech_name[mech] : "";
}

const char *arpg_inv_mechanic_desc(int mech) {
    return ((unsigned)mech < (unsigned)MECH_COUNT) ? s_mech_desc[mech] : "";
}

static int default_mech_val(int mech) {
    switch (mech) {
    case ARPG_MECH_LANZA:        return 20;
    case ARPG_MECH_LLAMA_VOTIVA: return 24;
    case ARPG_MECH_AUTO_FE:      return 100;
    case ARPG_MECH_CILICIO:      return 20;
    case ARPG_MECH_PIRA:         return 75;
    case ARPG_MECH_LLAGA:        return 20;
    case ARPG_MECH_MARTIRIO:     return 60;
    case ARPG_MECH_FLAGELADO:    return 100;
    case ARPG_MECH_VIATICO:      return 20;
    default:                     return 10;
    }
}

int arpg_inv_mechanic_value(int mech) {
    int best = 0;
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++) {
        for (int k = 0; k < arpg_inv_socket_count(s); k++) {
            const ArpgInvItem *it = arpg_inv_socket_item(s, k);
            if (!it || it->mech != mech) continue;
            int v = it->mech_val > 0 ? (int)it->mech_val : default_mech_val(mech);
            if (v > best) best = v;
        }
    }
    return best;
}

void arpg_inv_mechanic_format(const ArpgInvItem *it, char *buf, int n) {
    if (!buf || n <= 0) return;
    buf[0] = 0;
    if (!it || it->mech == ARPG_MECH_NONE) return;
    snprintf(buf, (size_t)n, "%s", arpg_inv_mechanic_desc(it->mech));
}

int arpg_inv_mechanic_stat(const ArpgInvItem *it, char *name, int nn, char *val, int nv) {
    if (!it || (unsigned)it->mech >= (unsigned)MECH_COUNT || !s_mech_stat_name[it->mech]) return 0;
    int v = it->mech_val > 0 ? (int)it->mech_val : default_mech_val(it->mech);
    snprintf(name, (size_t)nn, "%s", s_mech_stat_name[it->mech]);
    snprintf(val, (size_t)nv, s_mech_stat_fmt[it->mech], v);
    return 1;
}

const char *arpg_inv_line_name(int kind) {
    return ((unsigned)kind < ARPG_LINE_COUNT) ? s_line_name[kind] : "";
}

int arpg_inv_line_is_pct(int kind) {
    switch (kind) {
    case ARPG_LINE_DAMAGE:
    case ARPG_LINE_CHARGE:
    case ARPG_LINE_RANGE:
    case ARPG_LINE_BURN:
    case ARPG_LINE_SPEED:
    case ARPG_LINE_MANA_REGEN:
    case ARPG_LINE_RADIUS:
    case ARPG_LINE_WAIT:
    case ARPG_LINE_COST:
        return 1;
    default:
        return 0;
    }
}

void arpg_inv_line_format(int kind, int val, char *buf, int n) {
    if (!buf || n <= 0) return;
    if (arpg_inv_line_is_pct(kind)) snprintf(buf, (size_t)n, "%+d %%", val);
    else snprintf(buf, (size_t)n, "%+d pts", val);
}

void arpg_inv_line_format_delta(int kind, int before, int after, char *buf, int n) {
    if (!buf || n <= 0) return;
    if (arpg_inv_line_is_pct(kind)) snprintf(buf, (size_t)n, "%d->%d%%", before, after);
    else snprintf(buf, (size_t)n, "%d->%d pts", before, after);
}

// Base real de una línea porcentual en esa escuela (px, pts o décimas de segundo) para dar el valor real
// entre paréntesis. unit: 1 = px, 2 = pts, 3 = décimas de segundo (negativo = más rápido). 0 = sin base.
static int line_real(int school, int kind, int val, int *unit) {
    *unit = 0;
    if (school == ARPG_SCHOOL_RAYO) {
        if (kind == ARPG_LINE_RANGE) { *unit = 1; return (110 * val + (val < 0 ? -50 : 50)) / 100; }
        if (kind == ARPG_LINE_CHARGE) {
            int cp = val > 75 ? 75 : val;
            *unit = 3;
            return -(((48 * cp + 50) / 100) * 10 + 30) / 60;
        }
    } else if (school == ARPG_SCHOOL_EJECUCION) {
        if (kind == ARPG_LINE_RANGE) { *unit = 1; return (REMATE_RANGE * val + 50) / 100; }
        if (kind == ARPG_LINE_DAMAGE) { *unit = 2; return (ARPG_PUNCH_DAMAGE * val + 50) / 100; }
    } else if (school == ARPG_SCHOOL_GLIFO) {
        if (kind == ARPG_LINE_RADIUS) { *unit = 1; return (ARPG_GLIFO_RADIUS * val + 50) / 100; }
        if (kind == ARPG_LINE_DAMAGE) { *unit = 2; return (ARPG_GLIFO_DAMAGE * val + 50) / 100; }
    }
    return 0;
}

static void fmt_tenths(char *buf, int n, int t) {      // décimas de segundo con signo -> "0,8" / "-0,1"
    int neg = t < 0;
    if (neg) t = -t;
    if (t > 999) t = 999;
    snprintf(buf, (size_t)n, "%s%d,%d", neg ? "-" : "", t / 10, t % 10);
}

void arpg_inv_line_format_real(int school, int kind, int val, char *buf, int n) {
    if (!buf || n <= 0) return;
    arpg_inv_line_format(kind, val, buf, n);
    int unit;
    int real = line_real(school, kind, val, &unit);
    if (!unit || real == 0) return;
    size_t len = strlen(buf);
    if (len + 2 >= (size_t)n) return;
    char *p = buf + len;
    int left = n - (int)len;
    if (unit == 1) snprintf(p, (size_t)left, " (%+d px)", real);
    else if (unit == 2) snprintf(p, (size_t)left, " (%+d)", real);
    else {
        char t[12];
        fmt_tenths(t, sizeof(t), real);
        if (real > 0) snprintf(p, (size_t)left, " (+%s s)", t);
        else snprintf(p, (size_t)left, " (%s s)", t);
    }
}

// ---------------------------------------------------------------------------
// Ficha de la escuela: totales reales con la base. Lee g_mods (lo que ya aplica arpg_inv_apply) y las
// mismas constantes que usan weapons.c, punch.c, remate.c, glifo.c y gameplay.c.
// ---------------------------------------------------------------------------

static ArpgSheetRow *sheet_next(ArpgSheetRow *rows, int *n, int max, int group, const char *name) {
    if (*n >= max) return 0;
    ArpgSheetRow *r = &rows[(*n)++];
    r->group = (uint8_t)group;
    snprintf(r->name, sizeof(r->name), "%s", name);
    r->val[0] = 0;
    return r;
}

// base -> total con unidad; si no cambia, solo el total.
static void put_arrow(ArpgSheetRow *rows, int *n, int max, const char *name, int base, int total, const char *unit) {
    ArpgSheetRow *r = sheet_next(rows, n, max, 0, name);
    if (!r) return;
    if (base == total) snprintf(r->val, sizeof(r->val), "%d%s%s", total, unit[0] ? " " : "", unit);
    else snprintf(r->val, sizeof(r->val), "%d -> %d%s%s", base, total, unit[0] ? " " : "", unit);
}

static void put_secs(ArpgSheetRow *rows, int *n, int max, const char *name, int base_t, int total_t) {
    ArpgSheetRow *r = sheet_next(rows, n, max, 0, name);
    if (!r) return;
    char a[10], b[10];
    fmt_tenths(a, sizeof(a), base_t);
    fmt_tenths(b, sizeof(b), total_t);
    if (base_t == total_t) snprintf(r->val, sizeof(r->val), "%s s", a);
    else snprintf(r->val, sizeof(r->val), "%s -> %s s", a, b);
}

static int rayo_damage_total(void) {
    int pct = g_mods.sniper_damage_pct + arpg_inv_mechanic_value(ARPG_MECH_LANZA);
    return ARPG_RAY_DAMAGE * pct / 100;
}
static int rayo_range_total(void) { return 110 + g_mods.sniper_range; }
static int rayo_charge_frames(void) { return 48 + g_mods.sniper_aim; }
static int ejec_damage_total(void) { return ARPG_PUNCH_DAMAGE * g_mods.punch_damage_pct / 100; }
static int ejec_range_total(void) { return REMATE_RANGE * (100 + g_mods.remate_range_bonus) / 100; }
static int glifo_damage_total(void) { return ARPG_GLIFO_DAMAGE * (100 + arpg_inv_glifo_line(ARPG_LINE_DAMAGE)) / 100; }
static int glifo_radius_total(void) { return ARPG_GLIFO_RADIUS * (100 + arpg_inv_glifo_line(ARPG_LINE_RADIUS)) / 100; }
static int glifo_wait_k(void) {
    int k = 100 - arpg_inv_glifo_line(ARPG_LINE_WAIT);
    return k < ARPG_GLIFO_WAIT_MIN_PCT ? ARPG_GLIFO_WAIT_MIN_PCT : k;
}
static int glifo_cost_total(void) {
    int c = ARPG_GLIFO_COST * (100 - arpg_inv_glifo_line(ARPG_LINE_COST)) / 100;
    return c < ARPG_GLIFO_COST_MIN ? ARPG_GLIFO_COST_MIN : c;
}
static int tenths_of_frames(int frames) { return (frames * 10 + 30) / 60; }

int arpg_inv_sheet(int school, ArpgSheetRow *rows, int max) {
    int n = 0;
    ArpgSheetRow *r;
    if (!rows || max <= 0) return 0;
    switch (school) {
    case ARPG_SCHOOL_RAYO:
        put_arrow(rows, &n, max, "Daño", ARPG_RAY_DAMAGE, rayo_damage_total(), "");
        put_arrow(rows, &n, max, "Alcance", 110, rayo_range_total(), "px");
        put_secs(rows, &n, max, "Carga", tenths_of_frames(48), tenths_of_frames(rayo_charge_frames()));
        put_arrow(rows, &n, max, "Maná", ARPG_RAY_COST, ARPG_RAY_COST, "");
        if (g_mods.fire_dmg_pct != 100) put_arrow(rows, &n, max, "Quemadura", 100, g_mods.fire_dmg_pct, "%");
        break;
    case ARPG_SCHOOL_EJECUCION:
        put_arrow(rows, &n, max, "Daño", ARPG_PUNCH_DAMAGE, ejec_damage_total(), "");
        put_arrow(rows, &n, max, "Alcance", REMATE_RANGE, ejec_range_total(), "px");
        if (g_mods.punch_burn_pct > 0 && (r = sheet_next(rows, &n, max, 0, "Quemadura")) != 0)
            snprintf(r->val, sizeof(r->val), "+%d %%", g_mods.punch_burn_pct);
        if (g_mods.remate_heal_bonus > 0 && (r = sheet_next(rows, &n, max, 0, "Cura remate")) != 0)
            snprintf(r->val, sizeof(r->val), "+%d pts", g_mods.remate_heal_bonus);
        break;
    case ARPG_SCHOOL_GLIFO:
        put_arrow(rows, &n, max, "Daño", ARPG_GLIFO_DAMAGE, glifo_damage_total(), "");
        put_arrow(rows, &n, max, "Radio", ARPG_GLIFO_RADIUS, glifo_radius_total(), "px");
        put_secs(rows, &n, max, "Espera",
                 tenths_of_frames(ARPG_GLIFO_OPEN_FRAMES + ARPG_GLIFO_WAIT_FRAMES),
                 tenths_of_frames((ARPG_GLIFO_OPEN_FRAMES + ARPG_GLIFO_WAIT_FRAMES) * glifo_wait_k() / 100));
        put_arrow(rows, &n, max, "Maná", ARPG_GLIFO_COST, glifo_cost_total(), "");
        break;
    case ARPG_SCHOOL_PECHO: {
        int period = (BAL(mana_regen_frames, ARPG_MANA_REGEN_FRAMES) * 100) / (100 + g_mods.mana_regen_pct);
        char t[10];
        put_arrow(rows, &n, max, "Nivel", g_arpg_level, g_arpg_level, "");
        put_arrow(rows, &n, max, "Vida", calc_max_hp(), calc_max_hp(), "");
        put_arrow(rows, &n, max, "Maná", calc_max_mana(), calc_max_mana(), "");
        fmt_tenths(t, sizeof(t), tenths_of_frames(period));
        if ((r = sheet_next(rows, &n, max, 0, "Regen. maná")) != 0) snprintf(r->val, sizeof(r->val), "1 pt / %s s", t);
        put_arrow(rows, &n, max, "Velocidad", g_mods.speed_pct, g_mods.speed_pct, "%");
        break;
    }
    default: break;
    }
    return n;
}

const char *arpg_inv_item_name(const ArpgInvItem *it) {
    if (!it || it->kind == ARPG_ITEM_EMPTY) return "";
    if (it->kind == ARPG_ITEM_TOME) {
        if (it->school == ARPG_SCHOOL_GLIFO) return "Tomo de Glifo";
        if (it->school == ARPG_SCHOOL_LEVANTAR) return "Tomo de Levantar";
        return "Tomo de Rayo";
    }
    if (it->kind == ARPG_ITEM_RAYO) return "Rayo";
    if (it->name_id > 0 && it->name_id < (uint8_t)(sizeof(s_legendary_name) / sizeof(s_legendary_name[0])))
        return s_legendary_name[it->name_id];
    if (it->mech != ARPG_MECH_NONE) return arpg_inv_mechanic_name(it->mech);
    switch (it->school) {
    case ARPG_SCHOOL_RAYO:      return "Punta de Lanza";
    case ARPG_SCHOOL_EJECUCION: return "Nudillera Votiva";
    case ARPG_SCHOOL_GLIFO:     return "Hostia de Glifo";
    case ARPG_SCHOOL_LEVANTAR:  return "Cráneo Votivo";
    case ARPG_SCHOOL_PECHO:     return "Sagrado Corazón";
    default:                    return "Reliquia";
    }
}

// ---------------------------------------------------------------------------
// Generador de reliquias de la protodemo (Rayo, Ejecución, Pecho)
// ---------------------------------------------------------------------------

static uint32_t roll_u32(uint32_t *rng) {
    uint32_t x = *rng;
    if (!x) x = 0x6D2B79F5u;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *rng = x;
    return x;
}

static int roll_range(uint32_t *rng, int lo, int hi) {
    if (hi <= lo) return lo;
    return lo + (int)(roll_u32(rng) % (uint32_t)(hi - lo + 1));
}

static int16_t roll_line_value(int kind, int level, int rarity, uint32_t *rng) {
    // Escalado entero por nivel (1..99) y rareza (0..4): sin float.
    int lvl = level < 1 ? 1 : (level > 99 ? 99 : level);
    int scale_pct = 100 + (lvl - 1) * 35 + rarity * 8;
    int base = 5;
    switch (kind) {
    case ARPG_LINE_DAMAGE:      base = roll_range(rng, 6, 12);  break;
    case ARPG_LINE_CHARGE:      base = roll_range(rng, 6, 12);  break;
    case ARPG_LINE_RANGE:       base = roll_range(rng, 8, 16);  break;
    case ARPG_LINE_BURN:        base = roll_range(rng, 6, 14);  break;
    case ARPG_LINE_LIFE:        base = roll_range(rng, 10, 20); break;
    case ARPG_LINE_SPEED:       base = roll_range(rng, 3, 6);   break;
    case ARPG_LINE_MANA:        base = roll_range(rng, 8, 16);  break;
    case ARPG_LINE_MANA_REGEN:  base = roll_range(rng, 10, 22); break;
    case ARPG_LINE_REMATE_HEAL: base = roll_range(rng, 4, 10);  break;
    case ARPG_LINE_RADIUS:      base = roll_range(rng, 6, 12);  break;
    case ARPG_LINE_WAIT:        base = roll_range(rng, 4, 9);   break;
    case ARPG_LINE_COST:        base = roll_range(rng, 4, 9);   break;
    default: break;
    }
    int val = (base * scale_pct + 50) / 100;
    if (kind == ARPG_LINE_CHARGE && val > 60) val = 60;
    if ((kind == ARPG_LINE_WAIT || kind == ARPG_LINE_COST) && val > 45) val = 45;
    if (val < 1) val = 1;
    return (int16_t)val;
}

static int roll_line_for_school(int school, int level, int rarity, int exclude_kind, uint32_t *rng, uint8_t *out_kind, int16_t *out_val) {
    static const uint8_t rayo_lines[]  = { ARPG_LINE_DAMAGE, ARPG_LINE_CHARGE, ARPG_LINE_RANGE, ARPG_LINE_BURN };
    static const uint8_t ejec_lines[]  = { ARPG_LINE_DAMAGE, ARPG_LINE_RANGE, ARPG_LINE_BURN, ARPG_LINE_REMATE_HEAL };
    static const uint8_t pecho_lines[] = { ARPG_LINE_LIFE, ARPG_LINE_MANA, ARPG_LINE_MANA_REGEN, ARPG_LINE_SPEED };
    static const uint8_t glifo_lines[] = { ARPG_LINE_DAMAGE, ARPG_LINE_RADIUS, ARPG_LINE_WAIT, ARPG_LINE_COST };

    const uint8_t *pool = rayo_lines;
    int count = 4;
    if (school == ARPG_SCHOOL_EJECUCION) pool = ejec_lines;
    else if (school == ARPG_SCHOOL_PECHO) pool = pecho_lines;
    else if (school == ARPG_SCHOOL_GLIFO) pool = glifo_lines;

    uint8_t kind = pool[roll_u32(rng) % (uint32_t)count];
    if (kind == exclude_kind) kind = pool[(roll_u32(rng) % (uint32_t)(count - 1) + 1) % (uint32_t)count];
    if (kind == exclude_kind) {
        for (int i = 0; i < count; i++) if (pool[i] != exclude_kind) { kind = pool[i]; break; }
    }

    *out_kind = kind;
    *out_val = roll_line_value(kind, level, rarity, rng);
    return 1;
}

void arpg_relic_roll_school(ArpgInvItem *out, int school, int floor, int min_rarity, uint32_t *rng) {
    if (!out) return;
    int lvl = floor < 1 ? 1 : (floor > 99 ? 99 : floor);
    if (school != ARPG_SCHOOL_RAYO && school != ARPG_SCHOOL_EJECUCION && school != ARPG_SCHOOL_PECHO &&
        school != ARPG_SCHOOL_GLIFO)
        school = ARPG_SCHOOL_RAYO;

    // Probabilidades base de rareza, desplazadas por profundidad.
    int r_roll = (int)(roll_u32(rng) % 100u);
    int bonus = (lvl - 1) * 2;
    int rarity = ARPG_RAR_COMMON;
    if (r_roll + bonus >= 98) rarity = ARPG_RAR_LEGENDARY;
    else if (r_roll + bonus >= 88) rarity = ARPG_RAR_EPIC;
    else if (r_roll + bonus >= 68) rarity = ARPG_RAR_RARE;
    else if (r_roll + bonus >= 38) rarity = ARPG_RAR_UNCOMMON;
    if (rarity < min_rarity) rarity = min_rarity;
    if (rarity >= ARPG_RAR_COUNT) rarity = ARPG_RAR_LEGENDARY;

    uint8_t mech = ARPG_MECH_NONE;
    uint8_t mech_val = 0;
    uint8_t name_id = 0;
    if (rarity == ARPG_RAR_LEGENDARY) {
        if (school == ARPG_SCHOOL_RAYO) { mech = ARPG_MECH_AUTO_FE; name_id = 1; }
        else if (school == ARPG_SCHOOL_EJECUCION) { mech = ARPG_MECH_PIRA; name_id = 2; }
        else if (school == ARPG_SCHOOL_GLIFO) { mech = ARPG_MECH_DOBLE_SELLO; name_id = 4; }
        else { mech = ARPG_MECH_LLAGA; name_id = 3; }
    } else if (rarity >= ARPG_RAR_RARE) {
        if (school == ARPG_SCHOOL_RAYO)
            mech = (roll_u32(rng) & 1u) ? ARPG_MECH_LANZA : ARPG_MECH_LLAMA_VOTIVA;
        else if (school == ARPG_SCHOOL_EJECUCION)
            mech = ARPG_MECH_PIRA;
        else if (school == ARPG_SCHOOL_GLIFO)
            mech = (roll_u32(rng) & 1u) ? ARPG_MECH_REDIL : ARPG_MECH_ZARZA;
        else
            mech = (roll_u32(rng) & 1u) ? ARPG_MECH_CILICIO : ARPG_MECH_LLAGA;
    }
    if (mech != ARPG_MECH_NONE) {
        int scale_pct = 100 + (lvl - 1) * 25 + rarity * 10;
        int base = 10;
        int lo = 5, hi = 250;
        switch (mech) {
        case ARPG_MECH_LANZA:        base = roll_range(rng, 14, 24); lo = 10; hi = 95;  break;
        case ARPG_MECH_LLAMA_VOTIVA: base = roll_range(rng, 18, 32); lo = 12; hi = 150; break;
        case ARPG_MECH_AUTO_FE:      base = roll_range(rng, 90, 120); lo = 90; hi = 180; break;
        case ARPG_MECH_PIRA:
            base = (rarity == ARPG_RAR_LEGENDARY) ? roll_range(rng, 85, 115) : roll_range(rng, 55, 85);
            lo = 40; hi = 220;
            break;
        case ARPG_MECH_CILICIO:      base = roll_range(rng, 16, 28); lo = 12; hi = 140; break;
        case ARPG_MECH_LLAGA:
            base = (rarity == ARPG_RAR_LEGENDARY) ? roll_range(rng, 22, 30) : roll_range(rng, 15, 22);
            lo = 12; hi = 45;
            break;
        default: break;
        }
        int v = (base * scale_pct + 50) / 100;
        if (v < lo) v = lo;
        if (v > hi) v = hi;
        mech_val = (uint8_t)v;
    }

    item_make(out, ARPG_ITEM_RELIC, (uint8_t)school, (uint8_t)rarity, mech);
    out->mech_val = mech_val;
    out->level = (uint8_t)lvl;
    out->name_id = name_id;

    if (name_id == 3) {
        item_line(out, ARPG_LINE_LIFE, roll_line_value(ARPG_LINE_LIFE, lvl, rarity, rng));
        item_line(out, ARPG_LINE_MANA, roll_line_value(ARPG_LINE_MANA, lvl, rarity, rng));
    } else {
        int nlines = (rarity == ARPG_RAR_COMMON || rarity == ARPG_RAR_RARE) ? 1 : 2;
        uint8_t k0 = 0xFF;
        for (int i = 0; i < nlines; i++) {
            uint8_t k = 0;
            int16_t v = 0;
            roll_line_for_school(school, lvl, rarity, k0, rng, &k, &v);
            item_line(out, k, v);
            k0 = k;
        }
    }
}

void arpg_relic_roll(ArpgInvItem *out, int floor, int min_rarity, uint32_t *rng) {
    static const uint8_t active_schools[4] = { ARPG_SCHOOL_RAYO, ARPG_SCHOOL_EJECUCION, ARPG_SCHOOL_PECHO, ARPG_SCHOOL_GLIFO };
    int school = active_schools[roll_u32(rng) % 4u];
    arpg_relic_roll_school(out, school, floor, min_rarity, rng);
}

#if MINIROM
#include "minirom.h"
// Mini ROM ("mecanicas" of the JSON): a relic of that mechanic goes to the first free socket of its school (the known
// recipes when there is one, a plain Rare otherwise) and the tome of Glifo / Levantar is equipped so the school is usable.
void arpg_inv_minirom_equip(int mech) {
    int school;
    switch (mech) {
    case ARPG_MECH_PRISA: case ARPG_MECH_SED_CENIZA: case ARPG_MECH_LANZA: case ARPG_MECH_LLAMA_VOTIVA:
    case ARPG_MECH_BRASA: case ARPG_MECH_AUTO_FE: school = ARPG_SCHOOL_RAYO; break;
    case ARPG_MECH_GLIFO: case ARPG_MECH_ZARZA: case ARPG_MECH_REDIL: case ARPG_MECH_DOBLE_SELLO: school = ARPG_SCHOOL_GLIFO; break;
    case ARPG_MECH_LEVANTAR: case ARPG_MECH_PROCESION: case ARPG_MECH_OFRENDA: school = ARPG_SCHOOL_LEVANTAR; break;
    case ARPG_MECH_VIATICO: case ARPG_MECH_FLAGELADO: case ARPG_MECH_PIRA: school = ARPG_SCHOOL_EJECUCION; break;
    case ARPG_MECH_CILICIO: case ARPG_MECH_MARTIRIO: case ARPG_MECH_LLAGA: school = ARPG_SCHOOL_PECHO; break;
    default: return;
    }
    ArpgInventory *inv = &g_arpg.inv;
    for (int k = 0; k < ARPG_INV_SOCKETS; k++)
        if (inv->socket[school][k].kind == ARPG_ITEM_RELIC && inv->socket[school][k].mech == mech) return;   // already there
    int k = 0;
    while (k < ARPG_INV_SOCKETS && inv->socket[school][k].kind != ARPG_ITEM_EMPTY) k++;
    if (k >= arpg_inv_socket_count(school)) return;
    ArpgInvItem *it = &inv->socket[school][k];
    arpg_inv_make_reward(it, mech);
    if (it->kind == ARPG_ITEM_EMPTY) arpg_inv_make_fixed_prize(it, mech);
    if (it->kind == ARPG_ITEM_EMPTY) { item_make(it, ARPG_ITEM_RELIC, (uint8_t)school, ARPG_RAR_RARE, (uint8_t)mech); it->mech_val = 60; }
    it->level &= (uint8_t)ARPG_ITEM_LEVEL_MASK;
    if (school == ARPG_SCHOOL_GLIFO || school == ARPG_SCHOOL_LEVANTAR) {
        int have = 0, free_slot = -1;
        for (int s = 1; s < ARPG_INV_SPELLS; s++) {
            if (inv->spell[s].kind == ARPG_ITEM_TOME && inv->spell[s].school == school) have = 1;
            else if (inv->spell[s].kind == ARPG_ITEM_EMPTY && free_slot < 0) free_slot = s;
        }
        if (!have && free_slot > 0) arpg_inv_make_tome(&inv->spell[free_slot], school);
    }
}
#endif
