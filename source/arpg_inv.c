#include "arpg_inv.h"
#include "arpg_progress.h"
#include "modifiers.h"
#include "upgrades.h"
#include <string.h>

// Todo el estado vive en g_arpg.inv para que el guardado lo escriba de un bloque (arpg_progress.c).
// LÍMITE decidido: solo Rayo y Ejecución tienen contenido; Glifo y Levantar existen (pestañas,
// tomos, mecánicas) pero no se inventan reliquias ni tomos de ejemplo. Pecho usa pasivas (líneas).

static const char *const s_rarity_name[] = { "Común", "Poco común", "Rara", "Épica", "Legendaria" };
static const char *const s_school_name[] = { "Rayo", "Ejecución", "Glifo", "Levantar", "Pecho" };
// Índice = id de nodo antiguo del árbol (source/arpg_tree.c); 0 es el Glifo/Levantar desbloqueado.
static const char *const s_mech_name[] = {
    "Glifo", "Prisa", "Sed de Ceniza", "Lanza", "Llama Votiva", "Brasa", "Auto de Fe",
    "Miasma", "Cilicio", "Martirio", "Levantar", "Procesión", "Ofrenda", "Viático", "Flagelado"
};
static const char *const s_line_name[ARPG_LINE_COUNT] = {
    "Daño", "Carga", "Alcance", "Quemadura", "Vida", "Velocidad"
};
// [TUNABLE-PLACEHOLDER] cera que da desguazar, por rareza.
static const uint16_t s_wax_value[ARPG_RAR_COUNT] = { 2, 4, 8, 16, 32 };

#define MECH_COUNT ((int)(sizeof(s_mech_name) / sizeof(s_mech_name[0])))

// Delta de g_mods que aportan las líneas del equipo actual. Se guarda para aplicar solo el cambio
// al equipar/desequipar en vivo; arpg_inv_apply() lo reconstruye desde cero tras mods_reset.
typedef struct {
    int damage_rayo;     // sniper_damage_pct
    int damage_ejec;     // punch_damage_pct
    int charge;          // sniper_aim (negativo = más rápido)
    int range;           // sniper_range
    int burn;            // fire_dmg_pct
    int life;            // max_hp
    int speed;           // speed_pct
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
}

static void item_line(ArpgInvItem *it, uint8_t kind, int16_t val) {
    if (it->nlines >= 2) return;
    it->line_kind[it->nlines] = kind;
    it->line_val[it->nlines] = val;
    it->nlines++;
}

static int rarity_ok(uint8_t r) { return r < ARPG_RAR_COUNT; }

void arpg_inv_init(ArpgInventory *inv) {
    memset(inv, 0, sizeof(*inv));
    for (int i = 0; i < ARPG_INV_BAG; i++) item_clear(&inv->bag[i]);
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) item_clear(&inv->socket[s][k]);
    for (int i = 0; i < ARPG_INV_SPELLS; i++) item_clear(&inv->spell[i]);
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

// Partida nueva: Rayo equipado y 11 reliquias de ejemplo de Rayo, Ejecución y Pecho (sin tomos:
// Glifo y Levantar aún no están definidos). Las de Rayo llevan mecánicas/Dones del rayo; las de
// Ejecución, los modificadores del remate (Viático/Flagelado) y su línea de daño del combo.
void arpg_inv_new_game(void) {
    ArpgInventory *inv = &g_arpg.inv;
    ArpgInvItem it;
    arpg_inv_init(inv);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_RARE, ARPG_MECH_LLAMA_VOTIVA);
    item_line(&it, ARPG_LINE_BURN, 10);
    item_line(&it, ARPG_LINE_RANGE, 10);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_DAMAGE, 8);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_EPIC, ARPG_MECH_SED_CENIZA);
    item_line(&it, ARPG_LINE_CHARGE, 6);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_LEGENDARY, ARPG_MECH_PRISA);
    item_line(&it, ARPG_LINE_CHARGE, 10);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_BURN, 5);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_UNCOMMON, ARPG_MECH_VIATICO);
    item_line(&it, ARPG_LINE_DAMAGE, 12);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_RARE, ARPG_MECH_FLAGELADO);
    item_line(&it, ARPG_LINE_DAMAGE, 6);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_LEGENDARY, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_DAMAGE, 20);
    item_line(&it, ARPG_LINE_SPEED, 4);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_DAMAGE, 4);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_EPIC, ARPG_MECH_CILICIO);
    item_line(&it, ARPG_LINE_LIFE, 20);
    item_line(&it, ARPG_LINE_SPEED, 4);
    add_item(inv, &it);

    item_make(&it, ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_line(&it, ARPG_LINE_LIFE, 10);
    add_item(inv, &it);
}

// Variante arpg-todo: equipa un conjunto de ejemplo de reliquias de Rayo/Ejecución/Pecho y deja
// solo el Rayo equipado (sin tomos), así el radial no abre con un único hechizo.
void arpg_inv_unlock_all(void) {
    ArpgInventory *inv = &g_arpg.inv;
    arpg_inv_new_game();

    item_make(&inv->spell[0], ARPG_ITEM_RAYO, ARPG_SCHOOL_RAYO, ARPG_RAR_COMMON, ARPG_MECH_NONE);
    item_clear(&inv->spell[1]);
    item_clear(&inv->spell[2]);
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < ARPG_INV_SOCKETS; k++) item_clear(&inv->socket[s][k]);

    item_make(&inv->socket[ARPG_SCHOOL_RAYO][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_EPIC, ARPG_MECH_SED_CENIZA);
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][0], ARPG_LINE_CHARGE, 6);
    item_make(&inv->socket[ARPG_SCHOOL_RAYO][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_RARE, ARPG_MECH_LLAMA_VOTIVA);
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][1], ARPG_LINE_BURN, 10);
    item_make(&inv->socket[ARPG_SCHOOL_RAYO][2], ARPG_ITEM_RELIC, ARPG_SCHOOL_RAYO, ARPG_RAR_LEGENDARY, ARPG_MECH_PRISA);
    item_line(&inv->socket[ARPG_SCHOOL_RAYO][2], ARPG_LINE_DAMAGE, 20);

    item_make(&inv->socket[ARPG_SCHOOL_EJECUCION][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_UNCOMMON, ARPG_MECH_VIATICO);
    item_line(&inv->socket[ARPG_SCHOOL_EJECUCION][0], ARPG_LINE_DAMAGE, 12);
    item_make(&inv->socket[ARPG_SCHOOL_EJECUCION][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_EJECUCION, ARPG_RAR_RARE, ARPG_MECH_FLAGELADO);

    item_make(&inv->socket[ARPG_SCHOOL_PECHO][0], ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_EPIC, ARPG_MECH_CILICIO);
    item_line(&inv->socket[ARPG_SCHOOL_PECHO][0], ARPG_LINE_DAMAGE, 18);
    item_make(&inv->socket[ARPG_SCHOOL_PECHO][1], ARPG_ITEM_RELIC, ARPG_SCHOOL_PECHO, ARPG_RAR_RARE, ARPG_MECH_NONE);
    item_line(&inv->socket[ARPG_SCHOOL_PECHO][1], ARPG_LINE_LIFE, 40);
}

int arpg_inv_add(const ArpgInvItem *item) {
    if (!item || item->kind == ARPG_ITEM_EMPTY) return -1;
    return add_item(&g_arpg.inv, item);
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

int arpg_inv_socket_count(int school) {
    if ((unsigned)school >= ARPG_INV_SCHOOLS) return 0;
    return (school == ARPG_SCHOOL_PECHO) ? 2 : 3;
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

int arpg_inv_equip_relic(int bag_index, int school, int socket) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school)) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (!socket_accepts(b, school)) return 0;
    if (g_arpg.inv.socket[school][socket].kind != ARPG_ITEM_EMPTY) return 0;
    g_arpg.inv.socket[school][socket] = *b;
    item_clear(b);
    return 1;
}

int arpg_inv_swap_relic(int bag_index, int school, int socket) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    if ((unsigned)socket >= (unsigned)arpg_inv_socket_count(school)) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (!socket_accepts(b, school)) return 0;
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

// Un tomo solo entra en un hueco de hechizo libre (el 0 siempre es Rayo).
int arpg_inv_equip_tome(int bag_index) {
    if ((unsigned)bag_index >= ARPG_INV_BAG) return 0;
    ArpgInvItem *b = &g_arpg.inv.bag[bag_index];
    if (b->kind != ARPG_ITEM_TOME) return 0;
    for (int i = 1; i < ARPG_INV_SPELLS; i++) {
        if (g_arpg.inv.spell[i].kind == ARPG_ITEM_EMPTY) {
            g_arpg.inv.spell[i] = *b;
            item_clear(b);
            return 1;
        }
    }
    return 0;
}

int arpg_inv_unequip_tome(int school) {
    if ((unsigned)school >= ARPG_INV_SPELLS) return 0;
    ArpgInvItem *s = &g_arpg.inv.spell[school];
    if (s->kind != ARPG_ITEM_TOME) return 0;
    int slot = arpg_inv_first_free_bag();
    if (slot < 0) return 0;
    g_arpg.inv.bag[slot] = *s;
    item_clear(s);
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
    g_arpg.inv.wax = (uint16_t)(g_arpg.inv.wax + s_wax_value[rarity_ok(b->rarity) ? b->rarity : 0]);
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
    if (it->kind == ARPG_ITEM_TOME && it->school == ARPG_SCHOOL_LEVANTAR) return ARPG_SPELL_LEVANTAR;
    return -1;
}

int arpg_inv_has_mechanic(int mech) {
    for (int s = 0; s < ARPG_INV_SCHOOLS; s++)
        for (int k = 0; k < arpg_inv_socket_count(s); k++)
            if (g_arpg.inv.socket[s][k].kind != ARPG_ITEM_EMPTY && g_arpg.inv.socket[s][k].mech == mech)
                return 1;
    return 0;
}

// ---------------------------------------------------------------------------
// Modificadores: las líneas equipadas se suman a g_mods (reutiliza los Dones del roguelike).
// ---------------------------------------------------------------------------

static void line_add(InvModDelta *d, const ArpgInvItem *it, int kind, int val) {
    switch (kind) {
    case ARPG_LINE_DAMAGE:
        if (it->school == ARPG_SCHOOL_EJECUCION) d->damage_ejec += val;
        else d->damage_rayo += val;
        break;
    case ARPG_LINE_CHARGE: d->charge -= val; break;   // valor = frames que se recortan
    case ARPG_LINE_RANGE:  d->range += val; break;
    case ARPG_LINE_BURN:   d->burn += val; break;
    case ARPG_LINE_LIFE:   d->life += val; break;
    case ARPG_LINE_SPEED:  d->speed += val; break;
    default: break;
    }
}

// Reliquia del roguelike que corresponde a una mecánica equipada (-1 si no hay ninguna).
// Prisa y Brasa no tienen reliquia propia: su efecto de Don lo aplica arpg_tree_apply() en el
// arranque de la partida (nodos 1 y 5), así que aquí solo cuentan sus líneas.
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
    default:                     return -1;
    }
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
}

static void apply_delta(const InvModDelta *d) {
    g_mods.sniper_damage_pct += d->damage_rayo;
    g_mods.punch_damage_pct += d->damage_ejec;
    g_mods.sniper_aim += d->charge;
    g_mods.sniper_range += d->range;
    g_mods.fire_dmg_pct += d->burn;
    g_mods.max_hp += d->life;
    g_mods.speed_pct += d->speed;
}

void arpg_inv_apply(void) {
    InvModDelta d;
    compute_delta(&d);
    apply_delta(&d);
    for (int id = 0; id < UPG_RELIC_COUNT; id++)
        if (d.relic_bits & (1u << id)) upgrades_grant_relic(id);
    s_last = d;
    s_have_last = 1;
}

// En vivo: aplica solo la diferencia de líneas y ajusta las reliquias concedidas por mecánica
// (grant al engarzar, revoke al quitar). Al cambiar desde la pausa no se recrea el jugador, así que
// Vida/Velocidad entran en la siguiente partida (igual que los efectos del árbol antiguo, que se
// aplicaban en arena_restart).
void arpg_inv_recalc(void) {
    InvModDelta d;
    compute_delta(&d);
    if (!s_have_last) { apply_delta(&d); s_last = d; s_have_last = 1; return; }
    InvModDelta diff;
    diff.damage_rayo = d.damage_rayo - s_last.damage_rayo;
    diff.damage_ejec = d.damage_ejec - s_last.damage_ejec;
    diff.charge = d.charge - s_last.charge;
    diff.range = d.range - s_last.range;
    diff.burn = d.burn - s_last.burn;
    diff.life = d.life - s_last.life;
    diff.speed = d.speed - s_last.speed;
    diff.relic_bits = 0;
    apply_delta(&diff);
    for (int id = 0; id < UPG_RELIC_COUNT; id++) {
        int was = (s_last.relic_bits >> id) & 1, now = (d.relic_bits >> id) & 1;
        if (was && !now) upgrades_revoke_relic(id);
        else if (!was && now) upgrades_grant_relic(id);
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

const char *arpg_inv_line_name(int kind) {
    return ((unsigned)kind < ARPG_LINE_COUNT) ? s_line_name[kind] : "";
}
