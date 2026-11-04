#include "modifiers.h"
#include "gameplay.h"
#include "collision.h"
#include <string.h>

// Provided by main.c: 1 when a wall surface hides the world pixel from an actor at `depth`.
int world_pixel_hidden(int x, int y, int depth);

ModEffects g_mods;

typedef struct {
    const char *name;           // upper case ASCII: the HUD font has no accents
    uint16_t color;
} ModInfo;

enum {
    MOD_PIERCING_PELLETS = 0,   // shotgun pellets go through 1 enemy, -25% damage
    MOD_DOUBLE_CHAMBER,         // +3 pellets, +12 frames between shots
    MOD_LIGHT_TRIGGER,          // sniper aims 8 frames faster, -25% damage
    MOD_LONG_BARREL,            // sniper +50% damage, aims 10 frames slower
    MOD_BLOODLUST,              // a kill readies the shotgun at once, -1 max hit
    MOD_BONE_PLATE,             // +2 max hits (and heals 2), -12% speed
    MOD_LIGHT_FEET,             // +15% speed, -20 i-frames
    MOD_BRUTAL_KICK             // shotgun shove x2, own recoil x2
};

static const ModInfo s_info[MOD_COUNT] = {
    [MOD_PIERCING_PELLETS] = { "PERFORANTES",      RGB15(31, 22, 4)  | BIT(15) },
    [MOD_DOUBLE_CHAMBER]   = { "RECAMARA DOBLE",   RGB15(31, 12, 4)  | BIT(15) },
    [MOD_LIGHT_TRIGGER]    = { "GATILLO LIGERO",   RGB15(6, 30, 31)  | BIT(15) },
    [MOD_LONG_BARREL]      = { "CANON LARGO",      RGB15(8, 14, 31)  | BIT(15) },
    [MOD_BLOODLUST]        = { "SED DE SANGRE",    RGB15(31, 4, 6)   | BIT(15) },
    [MOD_BONE_PLATE]       = { "CORAZA OSEA",      RGB15(28, 28, 22) | BIT(15) },
    [MOD_LIGHT_FEET]       = { "PIES LIGEROS",     RGB15(10, 31, 10) | BIT(15) },
    [MOD_BRUTAL_KICK]      = { "RETROCESO BRUTAL", RGB15(26, 6, 30)  | BIT(15) },
};

typedef struct {
    int active;
    int x, y;                   // ground position, world px
    int id;
    int armed;                  // set once the player has stepped away: standing on it when it appears takes nothing
} Pedestal;

#define NUM_PEDESTALS 2
#define PICKUP_RADIUS 14        // ground px (metric dx^2 + 4 dy^2)
#define HINT_RADIUS 60
#define TOAST_FRAMES 150

static Pedestal s_pedestals[NUM_PEDESTALS];
static int s_owned = 0;         // bit mask of taken modifiers
static int s_delay = 0;         // frames before the pedestals can be taken
static int s_toast_id = MOD_NONE;
static int s_toast_timer = 0;
static int s_near_id = MOD_NONE;
static uint32_t s_tick = 0;
static uint32_t s_run = 0;

static void apply(int id) {
    switch (id) {
        case MOD_PIERCING_PELLETS:
            g_mods.shotgun_pierce += 1;
            g_mods.shotgun_damage_pct = g_mods.shotgun_damage_pct * 75 / 100;
            break;
        case MOD_DOUBLE_CHAMBER:
            g_mods.shotgun_pellets += 3;
            g_mods.shotgun_cooldown += 12;
            break;
        case MOD_LIGHT_TRIGGER:
            g_mods.sniper_aim -= 8;
            g_mods.sniper_damage_pct = g_mods.sniper_damage_pct * 75 / 100;
            break;
        case MOD_LONG_BARREL:
            g_mods.sniper_damage_pct = g_mods.sniper_damage_pct * 150 / 100;
            g_mods.sniper_aim += 10;
            break;
        case MOD_BLOODLUST:
            g_mods.kill_resets_shotgun = 1;
            g_mods.max_hp -= 1;
            g_player_state.max_hp -= 1;
            if (g_player_state.hp > g_player_state.max_hp) g_player_state.hp = g_player_state.max_hp;
            break;
        case MOD_BONE_PLATE:
            g_mods.max_hp += 2;
            g_mods.speed_pct = g_mods.speed_pct * 88 / 100;
            g_player_state.max_hp += 2;
            g_player_state.hp += 2;
            break;
        case MOD_LIGHT_FEET:
            g_mods.speed_pct = g_mods.speed_pct * 115 / 100;
            g_mods.iframes -= 20;
            break;
        case MOD_BRUTAL_KICK:
            g_mods.knock_pct *= 2;
            g_mods.recoil_pct *= 2;
            break;
        default:
            break;
    }
}

void mods_reset(void) {
    memset(&g_mods, 0, sizeof(g_mods));
    g_mods.shotgun_damage_pct = 100;
    g_mods.sniper_damage_pct = 100;
    g_mods.speed_pct = 100;
    g_mods.knock_pct = 100;
    g_mods.recoil_pct = 100;
    memset(s_pedestals, 0, sizeof(s_pedestals));
    s_owned = 0;
    s_delay = 0;
    s_toast_id = MOD_NONE;
    s_toast_timer = 0;
    s_near_id = MOD_NONE;
    rng_seed(cpuGetTiming() ^ (++s_run * 2654435761u));
}

static int free_spot(int x, int y, int *ox, int *oy, int avoid_x) {
    static const int8_t offsets[][2] = {
        {-20, 0}, {20, 0}, {-28, 6}, {28, 6}, {-28, -6}, {28, -6}, {0, 8}, {0, -8}, {0, 0}
    };
    for (unsigned i = 0; i < sizeof(offsets) / sizeof(offsets[0]); i++) {
        int px = x + offsets[i][0], py = y + offsets[i][1];
        if (avoid_x != 0x7fffffff && (px - avoid_x < 24 && avoid_x - px < 24)) continue;
        if (position_is_free(TO_FIXED(px), TO_FIXED(py))) {
            *ox = px;
            *oy = py;
            return 1;
        }
    }
    return 0;
}

void mods_offer(int x, int y) {
    memset(s_pedestals, 0, sizeof(s_pedestals));     // a new offer replaces any pedestal left over
    int pool[MOD_COUNT], n = 0;
    for (int id = 0; id < MOD_COUNT; id++)
        if (!(s_owned & (1 << id))) pool[n++] = id;
    if (n == 0) return;

    int first_x = 0x7fffffff;
    for (int slot = 0; slot < NUM_PEDESTALS && n > 0; slot++) {
        int px, py;
        if (!free_spot(x, y, &px, &py, first_x)) break;
        int pick = rng_range(0, n - 1);
        s_pedestals[slot].active = 1;
        s_pedestals[slot].x = px;
        s_pedestals[slot].y = py;
        s_pedestals[slot].id = pool[pick];
        pool[pick] = pool[--n];
        first_x = px;
    }
    s_delay = MOD_PEDESTAL_DELAY;
}

int mods_update(fixed player_x, fixed player_y) {
    s_tick++;
    if (s_toast_timer > 0) s_toast_timer--;
    if (s_delay > 0) s_delay--;

    int px = TO_INT(player_x), py = TO_INT(player_y);
    int taken = MOD_NONE;
    int near_id = MOD_NONE, near_d2 = HINT_RADIUS * HINT_RADIUS + 1;
    for (int i = 0; i < NUM_PEDESTALS; i++) {
        Pedestal *p = &s_pedestals[i];
        if (!p->active) continue;
        int dx = p->x - px, dy = p->y - py;
        int d2 = dx * dx + GROUND_DY2(dy);
        if (d2 > (PICKUP_RADIUS + 8) * (PICKUP_RADIUS + 8)) p->armed = 1;
        if (d2 < near_d2) { near_d2 = d2; near_id = p->id; }
        if (s_delay == 0 && p->armed && d2 <= PICKUP_RADIUS * PICKUP_RADIUS && taken == MOD_NONE) taken = p->id;
    }
    s_near_id = near_id;

    if (taken != MOD_NONE) {
        s_owned |= 1 << taken;
        apply(taken);
        memset(s_pedestals, 0, sizeof(s_pedestals));    // the other one vanishes
        s_toast_id = taken;
        s_toast_timer = TOAST_FRAMES;
        s_near_id = MOD_NONE;
    }
    return taken;
}

static inline void put(uint16_t *buffer, int sx, int sy, int wx, int wy, int depth, uint16_t c) {
    if (sx < 0 || sx >= SCREEN_W || sy < 0 || sy >= SCREEN_H) return;
    if (world_pixel_hidden(wx, wy, depth)) return;
    buffer[sy * SCREEN_W + sx] = c;
    dirty_row(sy, sx, sx + 1);
}

void mods_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    const uint16_t shade = RGB15(1, 1, 3) | BIT(15);
    const uint16_t core = RGB15(31, 31, 31) | BIT(15);

    for (int i = 0; i < NUM_PEDESTALS; i++) {
        const Pedestal *p = &s_pedestals[i];
        if (!p->active) continue;
        int gx = p->x - cam_x;
        int gy = p->y - cam_y;
        if (gx < -12 || gx > SCREEN_W + 12 || gy < -4 || gy > SCREEN_H + 24) continue;
        uint16_t col = s_info[p->id].color;
        int bob = ((s_tick >> 3) & 1) ? 1 : 0;
        int depth = p->y;

        // Base: a dark slab on the floor.
        for (int dx = -5; dx <= 5; dx++) {
            put(buffer, gx + dx, gy, p->x + dx, p->y, depth, shade);
            if (dx > -4 && dx < 4) put(buffer, gx + dx, gy + 1, p->x + dx, p->y + 1, depth, shade);
        }
        // Floating diamond: the modifier's colour with a white core.
        int cy = gy - 12 - bob;
        uint16_t body = col;
        for (int dy = -4; dy <= 4; dy++) {
            int w = 4 - (dy < 0 ? -dy : dy);
            for (int dx = -w; dx <= w; dx++) {
                uint16_t c = (dx == 0 && dy == 0) ? core : body;
                put(buffer, gx + dx, cy + dy, p->x + dx, p->y + dy - 12, depth, c);
            }
        }
    }
}

const char *mods_name(int id) {
    return (id >= 0 && id < MOD_COUNT) ? s_info[id].name : "";
}

int mods_owned_count(void) {
    int n = 0;
    for (int id = 0; id < MOD_COUNT; id++) n += (s_owned >> id) & 1;
    return n;
}

int mods_owned_mask(void) { return s_owned; }

uint16_t mods_color(int id) {
    return (id >= 0 && id < MOD_COUNT) ? s_info[id].color : (RGB15(31, 31, 31) | BIT(15));
}

const char *mods_hud_text(void) {
    if (s_near_id != MOD_NONE) return s_info[s_near_id].name;
    if (s_toast_timer > 0 && s_toast_id != MOD_NONE) return s_info[s_toast_id].name;
    return NULL;
}
