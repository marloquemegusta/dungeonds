#include "pickups.h"
#include "inventory.h"
#include "dmg_numbers.h"
#include "collision.h"
#include "groundfx.h"
#include "hud_icons_gfx.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "modifiers.h"
#include "gameplay.h"
#include "sfx.h"
#include <stdio.h>
#if ENCOUNTERS_PROTO
#include "placeholders_gfx.h"
#endif

#define HEAL_PICKUP_RECYCLE_BELOW_PX 400 // [TUNABLE-PLACEHOLDER]
#define HEAL_PICKUP_HOVER_PX 3           // base height above ground shadow
#define PICKUP_MAGNET_STEP TO_FIXED(2)   // [TUNABLE-PLACEHOLDER] px per frame towards the hero inside the magnet radius
#define REMATE_ORB_OFFSET_PX 8           // [TUNABLE-PLACEHOLDER] health and mana orbs of one finisher are split by this

#if ENCOUNTERS_PROTO
#define PICKUP_SPRITE_W PH_RUNA_XP_W     // placeholder sprites are 12x12
#define PICKUP_SPRITE_H PH_RUNA_XP_H
#else
#define PICKUP_SPRITE_W HUD_ICON_W
#define PICKUP_SPRITE_H HUD_ICON_H
#endif

typedef struct { fixed x, y; int active; int kind; int amount; ArpgInvItem relic; } HealPickup;
static HealPickup s_pickups[HEAL_PICKUP_MAX_ACTIVE];
static uint32_t s_rng = 1;
static uint32_t s_anim_tick = 0;
static char s_loot_toast[48];
static int s_loot_toast_t = 0;
static int s_relic_tip_pending = 0;   // aviso "engarzala" a continuacion del "+ nombre"

#if SANDBOX
// Scenario hook (never in the shipping ROM): non-zero forces the next enemy death to drop a heart.
uint8_t g_pickup_force_drop = 0;
uint8_t g_remate_force_heal = 0;    // non-zero: the next remates always restore life and mana
#endif

void pickups_init(uint32_t seed) {
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) s_pickups[i].active = 0;
    s_rng = seed ? seed : 1u;
    s_anim_tick = 0;
    s_loot_toast[0] = 0;
    s_loot_toast_t = 0;
    s_relic_tip_pending = 0;
}

void pickups_shift_y(int dy_px) {
    fixed shift = TO_FIXED(dy_px);
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++)
        if (s_pickups[i].active) s_pickups[i].y += shift;
}

void pickups_enemy_killed(const Enemy *enemy) {
    if (!enemy) return;
#if ENCOUNTERS_PROTO
    return;     // ARPG: no random hearts from kills; only the remate drops orbs (pickups_remate_drops)
#endif
    int force = (enemy->type == ENEMY_TYPE_ABANDERADO);
#if SANDBOX
    if (g_pickup_force_drop) { force = 1; g_pickup_force_drop = 0; }
#endif
    if (!force) {
        s_rng = s_rng * 1664525u + 1013904223u;
        if ((s_rng % HEAL_PICKUP_CHANCE_DENOMINATOR) != 0) return;
    }
    int slot = -1;
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        if (!s_pickups[i].active) { slot = i; break; }
    }
    if (slot < 0 && force) {
        // Boss drop replaces the lowest (oldest/farthest behind) cross if all slots are occupied.
        slot = 0;
        for (int i = 1; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
            if (s_pickups[i].y > s_pickups[slot].y) slot = i;
        }
    }
    if (slot < 0) return;
    s_pickups[slot].x = enemy->x;
    s_pickups[slot].y = enemy->y;
    s_pickups[slot].kind = PICKUP_KIND_HEALTH;
    s_pickups[slot].amount = 0;
    s_pickups[slot].active = 1;
}

void pickups_spawn(int kind, fixed x, fixed y) {
    int slot = 0;
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        if (!s_pickups[i].active) { slot = i; break; }
    }
    s_pickups[slot].x = x;
    s_pickups[slot].y = y;
    s_pickups[slot].kind = kind;
    s_pickups[slot].amount = 0;
    s_pickups[slot].active = 1;
}

#if ARPG_BOT
int pickups_nearest(int kind, int px, int py, int *ox, int *oy) {
    int best = -1;
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        const HealPickup *p = &s_pickups[i];
        if (!p->active || p->kind != kind) continue;
        int dx = TO_INT(p->x) - px, dy = TO_INT(p->y) - py;
        int d2 = dx * dx + GROUND_DY2(dy);
        if (best < 0 || d2 < best) { best = d2; *ox = TO_INT(p->x); *oy = TO_INT(p->y); }
    }
    return best;
}
#endif

void pickups_spawn_xp(fixed x, fixed y, int amount) {
    (void)x; (void)y;
    arpg_add_xp(amount);
}

void pickups_spawn_relic(fixed x, fixed y, const ArpgInvItem *item) {
    if (!item || item->kind == ARPG_ITEM_EMPTY) return;
    int slot = -1;
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        if (!s_pickups[i].active) { slot = i; break; }
    }
    if (slot < 0) {
        // Evict an orb first rather than losing a relic drop.
        for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
            if (s_pickups[i].kind != PICKUP_KIND_RELIC) { slot = i; break; }
        }
        if (slot < 0) slot = 0;
    }
    s_pickups[slot].x = x;
    s_pickups[slot].y = y;
    s_pickups[slot].kind = PICKUP_KIND_RELIC;
    s_pickups[slot].amount = 0;
    s_pickups[slot].relic = *item;
    s_pickups[slot].active = 1;
}

void pickups_drop_enemy_loot(int enemy_type, int floor, fixed x, fixed y) {
    int min_rar = ARPG_RAR_COMMON;
    int chance = 7; // ~7% normal enemies
    int lvl_bonus = 0;
    if (enemy_type == ENEMY_TYPE_ABANDERADO) return;   // the elite and the Cripta boss give their prize from the room (encounters_act1.c)
    if (enemy_type == ENEMY_TYPE_CAMPANERO) {
        chance = 100;
        min_rar = ARPG_RAR_LEGENDARY;
        lvl_bonus = 2;
    } else if (enemy_type == ENEMY_TYPE_PARROCO || enemy_type == ENEMY_TYPE_MONJA ||
               enemy_type == ENEMY_TYPE_SHOOTER || enemy_type == ENEMY_TYPE_CHARGER) {
        chance = 30;
        min_rar = ARPG_RAR_UNCOMMON;
        lvl_bonus = 1;
    }
    s_rng = s_rng * 1664525u + 1013904223u;
    if ((int)((s_rng >> 8) % 100u) >= chance) return;
    // Nivel fijo por sala/ala y escalon del enemigo (sin auto-escalado al nivel del heroe).
    int base_lvl = floor < 1 ? 1 : floor;
    int item_lvl = base_lvl + lvl_bonus;
    if (item_lvl > 99) item_lvl = 99;
    ArpgInvItem item;
    arpg_relic_roll(&item, item_lvl, min_rar, &s_rng);
    pickups_spawn_relic(x, y, &item);
}


void pickups_toast(const char *msg, int frames) {
    snprintf(s_loot_toast, sizeof(s_loot_toast), "%s", msg);
    s_loot_toast_t = frames;
}

const char *pickups_loot_toast(void) {
    return (s_loot_toast_t > 0 && s_loot_toast[0]) ? s_loot_toast : 0;
}

// Remate heal streak: a small muted spark travels from the killed enemy to the hero (shifts only, no divides).
#define HEAL_FX_FRAMES 16
#define HEAL_FX_MAX 2
typedef struct { fixed sx, sy; int t; uint16_t col; } HealFx;
static HealFx s_heal_fx[HEAL_FX_MAX];
static fixed s_heal_hx, s_heal_hy;     // hero position of the last update (streak target)

static void heal_fx_spawn(fixed x, fixed y, uint16_t col) {
    for (int i = 0; i < HEAL_FX_MAX; i++) {
        if (s_heal_fx[i].t > 0) continue;
        s_heal_fx[i].sx = x; s_heal_fx[i].sy = y - TO_FIXED(10); s_heal_fx[i].t = HEAL_FX_FRAMES; s_heal_fx[i].col = col;
        return;
    }
}

// The finisher restores life and mana at once (no orbs): same chances and relic bonus as the old drops.
// Silent: the finisher's own sound covers the whole action (DESIGN-ARPG.md); the spark and the +N show the heal.
void pickups_remate_drops(fixed x, fixed y) {
    s_rng = s_rng * 1664525u + 1013904223u;
    int hp_roll = (int)((s_rng >> 8) % 100u);
    s_rng = s_rng * 1664525u + 1013904223u;
    int mana_roll = (int)((s_rng >> 8) % 100u);
#if SANDBOX
    if (g_remate_force_heal) { hp_roll = 0; mana_roll = 0; }   // scenario hook: both rolls succeed
#endif
    PlayerState *player = &g_player_state;
    if (hp_roll < BAL(remate_hp_chance, ARPG_REMATE_HP_CHANCE) && player->hp < player->max_hp) {
        int gain = BAL(remate_hp, ARPG_REMATE_HP) + g_mods.remate_heal_bonus;
        player->hp += gain;
        if (player->hp > player->max_hp) player->hp = player->max_hp;
        dmg_numbers_spawn(x - TO_FIXED(REMATE_ORB_OFFSET_PX), y - TO_FIXED(18), gain, DMG_NUM_HEAL);
        heal_fx_spawn(x - TO_FIXED(3), y, RGB15(15, 24, 13) | BIT(15));
    }
    if (mana_roll < BAL(remate_mana_chance, ARPG_REMATE_MANA_CHANCE)) {
        int gain = BAL(remate_mana, ARPG_REMATE_MANA) + g_mods.remate_heal_bonus / 2;
        player->mana += gain;
        if (player->mana > player->max_mana) player->mana = player->max_mana;
        dmg_numbers_spawn(x + TO_FIXED(REMATE_ORB_OFFSET_PX), y - TO_FIXED(18), gain, DMG_NUM_MANA);
        heal_fx_spawn(x + TO_FIXED(3), y, RGB15(13, 19, 27) | BIT(15));
    }
}

void pickups_fx_draw(uint16_t *buffer, int cam_x, int cam_y) {
    for (int i = 0; i < HEAL_FX_MAX; i++) {
        HealFx *f = &s_heal_fx[i];
        if (f->t <= 0) continue;
        // Trail of 3 samples (head, then two steps behind); progress in 16ths.
        for (int k = 0; k < 3; k++) {
            int prog = HEAL_FX_FRAMES - f->t - k * 2;
            if (prog < 0) continue;
            fixed px = f->sx + (((s_heal_hx - f->sx) * prog) >> 4);
            fixed py = f->sy + (((s_heal_hy - TO_FIXED(10) - f->sy) * prog) >> 4) - TO_FIXED((prog * (HEAL_FX_FRAMES - prog)) >> 3);   // arcs up to 8 px
            int cx = TO_INT(px) - cam_x, cy = TO_INT(py) - cam_y;
            const uint16_t col = k == 0 ? (RGB15(26, 23, 18) | BIT(15)) : f->col;
            const int sz = k == 0 ? 3 : k == 1 ? 2 : 1;
            for (int yy = 0; yy < sz; yy++)
                for (int xx = 0; xx < sz; xx++) {
                    int sx2 = cx + xx, sy2 = cy + yy;
                    if (sx2 >= 0 && sx2 < SCREEN_W && sy2 >= 0 && sy2 < SCREEN_H) buffer[sy2 * SCREEN_W + sx2] = col;
                }
        }
    }
}

void pickups_update(fixed player_x, fixed player_y, PlayerState *player) {
    s_anim_tick++;
    s_heal_hx = player_x; s_heal_hy = player_y;
    for (int i = 0; i < HEAL_FX_MAX; i++) if (s_heal_fx[i].t > 0) s_heal_fx[i].t--;
    if (s_loot_toast_t > 0) s_loot_toast_t--;
    if (s_loot_toast_t <= 0 && s_relic_tip_pending) {
        s_relic_tip_pending = 0;
        pickups_toast("Engárzala en el arcón o desde la pausa", 180);
    }
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        HealPickup *p = &s_pickups[i];
        if (!p->active) continue;
        if (p->kind != PICKUP_KIND_RELIC && p->y > player_y + TO_FIXED(HEAL_PICKUP_RECYCLE_BELOW_PX)) {
            p->active = 0;
            continue;
        }
        const int magnet = (p->kind == PICKUP_KIND_RELIC) ? 0 : ARPG_PICKUP_MAGNET;
        int dx = TO_INT(p->x - player_x);
        int dy = TO_INT(p->y - player_y);
        int d2 = dx * dx + GROUND_DY2(dy);
        if (magnet > 0 && d2 <= magnet * magnet && d2 > HEAL_PICKUP_RADIUS * HEAL_PICKUP_RADIUS) {
            // Magnet: 2 px per frame along the direction to the hero (one divide per orb per frame).
            fixed fx = player_x - p->x, fy = player_y - p->y;
            fixed ax = fx < 0 ? -fx : fx, ay = fy < 0 ? -fy : fy;
            fixed m = ax > ay ? ax : ay;
            if (m > 0) {
                p->x += (fx * PICKUP_MAGNET_STEP) / m;
                p->y += (fy * PICKUP_MAGNET_STEP) / m;
            }
            dx = TO_INT(p->x - player_x);
            dy = TO_INT(p->y - player_y);
        }
        const int grab_r = (p->kind == PICKUP_KIND_RELIC) ? (HEAL_PICKUP_RADIUS + 4) : HEAL_PICKUP_RADIUS;
        if (dx * dx + GROUND_DY2(dy) > grab_r * grab_r) continue;
        if (p->kind == PICKUP_KIND_RELIC) {
            if (arpg_inv_add(&p->relic) >= 0) {
                snprintf(s_loot_toast, sizeof(s_loot_toast), "+ %s", arpg_inv_item_name(&p->relic));
                s_loot_toast_t = 120;
                if (arpg_tip_take(ARPG_TIP_RELIQUIA)) s_relic_tip_pending = 1;
                sfx_play_pitched(SND_PICKUP_ORB, TO_INT(p->x), 1180);
                p->active = 0;
            } else if (s_loot_toast_t <= 0) {
                snprintf(s_loot_toast, sizeof(s_loot_toast), "Bolsa llena");
                s_loot_toast_t = 60;
            }
            continue;
        }
        if (p->kind == PICKUP_KIND_MANA) {
            if (player) {
                int gain = BAL(remate_mana, ARPG_REMATE_MANA) + g_mods.remate_heal_bonus / 2;
                player->mana += gain;
                if (player->mana > player->max_mana) player->mana = player->max_mana;
                dmg_numbers_spawn(player_x, player_y - TO_FIXED(18), gain, DMG_NUM_MANA);
            }
            sfx_play_pitched(SND_PICKUP_ORB, TO_INT(p->x), 1024);
        } else if (player && player->hp < player->max_hp) {
            int gain = BAL(remate_hp, ARPG_REMATE_HP) + g_mods.remate_heal_bonus;
            player->hp += gain;
            if (player->hp > player->max_hp) player->hp = player->max_hp;
            dmg_numbers_spawn(player_x, player_y - TO_FIXED(18), gain, DMG_NUM_HEAL);
            sfx_play_pitched(SND_PICKUP_ORB, TO_INT(p->x), 920);
        }
        p->active = 0;
    }
}

int pickups_item(int i, int cam_x, int cam_y, int *depth) {
    const HealPickup *p = &s_pickups[i];
    if (!p->active) return 0;
    int cx = TO_INT(p->x) - cam_x;
    int cy = TO_INT(p->y) - cam_y;
    if (cx - (PICKUP_SPRITE_W >> 1) >= SCREEN_W || cx + (PICKUP_SPRITE_W >> 1) + 1 <= 0 ||
        cy + 1 <= 0 || cy - PICKUP_SPRITE_H - HEAL_PICKUP_HOVER_PX - 3 >= SCREEN_H) return 0;
    *depth = TO_INT(p->y);
    return 1;
}

void pickups_draw(uint16_t *buffer, int i, int cam_x, int cam_y) {
    static const int8_t bob_lut[16] = {
        0, 0, -1, -1, -2, -2, -2, -1, -1, 0, 1, 1, 2, 2, 1, 1
    };
    const int bob_y = bob_lut[(s_anim_tick >> 2) & 15];
    const uint16_t shadow_col = RGB15(4, 3, 3) | BIT(15);
    const int half_w = PICKUP_SPRITE_W >> 1;
    const HealPickup *p = &s_pickups[i];
    const int depth = TO_INT(p->y);
    int cx = TO_INT(p->x) - cam_x;
    int cy = TO_INT(p->y) - cam_y;
    int x0 = cx - half_w;
    const int bob = bob_y;
    int y0 = cy - PICKUP_SPRITE_H - HEAL_PICKUP_HOVER_PX + bob;

    // Walls in front hide the pickup and its shadow pixel by pixel; the test only runs when some wall run reaches the sprite.
    int occ = 0;
    for (int r = y0; r <= cy + 1 && !occ; r++)
        if ((unsigned)r < SCREEN_H && world_span_hidden(r + cam_y, x0 + cam_x, x0 + PICKUP_SPRITE_W + cam_x, depth)) occ = 1;

    // Subtle ground shadow beneath the levitating pickup (relics with an icon cast their own projected shadow).
    int own_shadow = 0;
#if ENCOUNTERS_PROTO
    own_shadow = (p->kind == PICKUP_KIND_RELIC && inv_item_floor_icon24(&p->relic) != NULL);
#endif
    for (int sy = cy - 1; sy <= cy && !own_shadow; sy++) {
        if ((unsigned)sy >= SCREEN_H) continue;
        dirty_row(sy, cx - 3, cx + 4);
        for (int sx = cx - 3; sx <= cx + 3; sx++) {
            if ((unsigned)sx >= SCREEN_W) continue;
            if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
            buffer[sy * SCREEN_W + sx] = shadow_col;
        }
    }

#if ENCOUNTERS_PROTO
    if (p->kind == PICKUP_KIND_RELIC) {
        // Desaturated rarity gem + subtle vertical beam for Legendary drops.
        static const uint16_t rar_col[ARPG_RAR_COUNT] = {
            RGB15(20, 19, 17) | BIT(15), // Común (hueso)
            RGB15(10, 18, 11) | BIT(15), // Poco común (salvia)
            RGB15(10, 14, 22) | BIT(15), // Rara (pizarra)
            RGB15(18, 11, 20) | BIT(15), // Épica (violeta apagado)
            RGB15(24, 18, 7)  | BIT(15)  // Legendaria (oro viejo)
        };
        const uint8_t rar = (p->relic.rarity < ARPG_RAR_COUNT) ? p->relic.rarity : 0;
        const uint16_t col = rar_col[rar];
        const uint16_t rim = RGB15(7, 6, 5) | BIT(15);
        const int rcy = y0 + (PICKUP_SPRITE_H >> 1);
        const uint16_t *icon = inv_item_floor_icon24(&p->relic);
        if (icon) {
            // 24x24 archetype icon: projected floor shadow, translucent rarity halo (3 px), then the icon.
            const int ix = cx - 12, iy = rcy - 12;
            const uint8_t *shm = inv_item_floor_shadow(&p->relic);
            const uint8_t *aur = inv_item_floor_aura30(&p->relic);
            if (shm) {
                const int sx0 = cx + INV_FLOOR_SH_OX, sy0 = cy + INV_FLOOR_SH_OY;
                for (int my = 0; my < INV_FLOOR_SH_H; my++) {
                    int sy = sy0 + my;
                    if ((unsigned)sy >= SCREEN_H) continue;
                    dirty_row(sy, sx0, sx0 + INV_FLOOR_SH_W);
                    for (int mx = 0; mx < INV_FLOOR_SH_W; mx++) {
                        int sx = sx0 + mx;
                        if (!shm[my * INV_FLOOR_SH_W + mx] || (unsigned)sx >= SCREEN_W) continue;
                        if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
                        uint16_t b = buffer[sy * SCREEN_W + sx];
                        if (!b) b = world_floor_color_at(sx + cam_x, sy + cam_y);
                        buffer[sy * SCREEN_W + sx] = (uint16_t)(((b & 0x7BDEu) >> 1) | BIT(15));
                    }
                }
            }
            if (rar == ARPG_RAR_LEGENDARY) {
                for (int py = iy - 19; py < iy - 6; py++) {
                    if ((unsigned)py >= SCREEN_H || (unsigned)cx >= SCREEN_W) continue;
                    if (occ && world_pixel_hidden(cx + cam_x, py + cam_y, depth)) continue;
                    dirty_row(py, cx, cx + 1);
                    buffer[py * SCREEN_W + cx] = col;
                }
            }
            if (aur) {
                // Translucent halo: rarity colour over what is below, 50 / 25 / 12.5 % at ring 1 / 2 / 3 (outer ring pulses 12.5 <-> 25 %).
                const uint16_t acol = (rar == 0) ? (uint16_t)(RGB15(24, 23, 20) | BIT(15)) : col;
                const uint16_t ac2 = (uint16_t)((acol & 0x739Cu) >> 2), ac3 = (uint16_t)((acol & 0x6318u) >> 3);
                const int pulse = (s_anim_tick >> 5) & 1;
                for (int ay = 0; ay < 30; ay++) {
                    int sy = iy - 3 + ay;
                    if ((unsigned)sy >= SCREEN_H) continue;
                    dirty_row(sy, ix - 3, ix + 27);
                    for (int ax = 0; ax < 30; ax++) {
                        int d = aur[ay * 30 + ax];
                        if (d == 0 || d > 3) continue;
                        int sx = ix - 3 + ax;
                        if ((unsigned)sx >= SCREEN_W) continue;
                        if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
                        uint16_t b = buffer[sy * SCREEN_W + sx];
                        if (!b) b = world_floor_color_at(sx + cam_x, sy + cam_y);
                        uint16_t o;
                        if (d == 1) o = (uint16_t)(((b & 0x7BDEu) >> 1) + ((acol & 0x7BDEu) >> 1));
                        else if (d == 2 || pulse) o = (uint16_t)(((b & 0x7BDEu) >> 1) + ((b & 0x739Cu) >> 2) + ac2); // 75 % floor + 25 % rarity
                        else o = (uint16_t)(b - ((b & 0x6318u) >> 3) + ac3);                                       // 87.5 % floor + 12.5 % rarity
                        buffer[sy * SCREEN_W + sx] = (uint16_t)(o | BIT(15));
                    }
                }
            }
            for (int gy = 0; gy < 24; gy++) {
                int sy = iy + gy;
                if ((unsigned)sy >= SCREEN_H) continue;
                dirty_row(sy, ix, ix + 24);
                for (int gx = 0; gx < 24; gx++) {
                    uint16_t c = icon[gy * 24 + gx];
                    int sx = ix + gx;
                    if (!c || (unsigned)sx >= SCREEN_W) continue;
                    if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
                    buffer[sy * SCREEN_W + sx] = c;
                }
            }
            return;
        }
        if (rar == ARPG_RAR_LEGENDARY) {
            for (int py = rcy - 18; py < rcy - 4; py++) {
                if ((unsigned)py >= SCREEN_H || (unsigned)cx >= SCREEN_W) continue;
                if (occ && world_pixel_hidden(cx + cam_x, py + cam_y, depth)) continue;
                dirty_row(py, cx, cx + 1);
                buffer[py * SCREEN_W + cx] = col;
            }
        }
        for (int ddy = -4; ddy <= 4; ddy++) {
            int sy = rcy + ddy;
            if ((unsigned)sy >= SCREEN_H) continue;
            int ext = 4 - (ddy < 0 ? -ddy : ddy);
            dirty_row(sy, cx - ext, cx + ext + 1);
            for (int ddx = -ext; ddx <= ext; ddx++) {
                int sx = cx + ddx;
                if ((unsigned)sx >= SCREEN_W) continue;
                if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
                int edge = (ddx == -ext || ddx == ext || ddy == -4 || ddy == 4);
                buffer[sy * SCREEN_W + sx] = edge ? rim : col;
            }
        }
        return;
    }
    // ARPG placeholders (include/placeholders_gfx.h): 0 pixels are transparent.
    const uint16_t *sprite = (p->kind == PICKUP_KIND_MANA) ? g_ph_orbe_mana : g_ph_orbe_vida;
    for (int gy = 0; gy < PICKUP_SPRITE_H; gy++) {
        int sy = y0 + gy;
        if ((unsigned)sy >= SCREEN_H) continue;
        dirty_row(sy, x0, x0 + PICKUP_SPRITE_W);
        const uint16_t *row = &sprite[gy * PICKUP_SPRITE_W];
        for (int gx = 0; gx < PICKUP_SPRITE_W; gx++) {
            uint16_t c = row[gx];
            if (!c) continue;
            int sx = x0 + gx;
            if ((unsigned)sx >= SCREEN_W) continue;
            if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
            buffer[sy * SCREEN_W + sx] = c;
        }
    }
    return;
#else
    if (p->kind == PICKUP_KIND_MANA) {
        // Mana orb: slate diamond (|dx|+|dy| <= 4) with a lighter top pixel, centred on the heart's middle.
        const uint16_t mana_col = RGB15(6, 9, 18) | BIT(15);
        const uint16_t mana_top = RGB15(10, 14, 24) | BIT(15);
        const int mcy = y0 + (HUD_ICON_H >> 1);
        for (int ddy = -4; ddy <= 4; ddy++) {
            int sy = mcy + ddy;
            if ((unsigned)sy >= SCREEN_H) continue;
            int ext = 4 - (ddy < 0 ? -ddy : ddy);
            dirty_row(sy, cx - ext, cx + ext + 1);
            for (int ddx = -ext; ddx <= ext; ddx++) {
                int sx = cx + ddx;
                if ((unsigned)sx >= SCREEN_W) continue;
                if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
                buffer[sy * SCREEN_W + sx] = (ddy == -4) ? mana_top : mana_col;
            }
        }
        return;
    }

    for (int gy = 0; gy < HUD_ICON_H; gy++) {
        int sy = y0 + gy;
        if ((unsigned)sy >= SCREEN_H) continue;
        dirty_row(sy, x0, x0 + HUD_ICON_W);
        const uint16_t *row = &g_hud_heart_full[gy * HUD_ICON_W];
        for (int gx = 0; gx < HUD_ICON_W; gx++) {
            uint16_t c = row[gx];
            if (!c) continue;
            int sx = x0 + gx;
            if ((unsigned)sx >= SCREEN_W) continue;
            if (occ && world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) continue;
            buffer[sy * SCREEN_W + sx] = c;
        }
    }
#endif
}
