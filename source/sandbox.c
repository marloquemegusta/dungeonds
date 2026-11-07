#include "sandbox.h"

// Keeps the translation unit non-empty (ISO C) when SANDBOX=0; it carries no code.
typedef int sandbox_translation_unit_not_empty;

#if SANDBOX

#include <stddef.h>
#include <string.h>
#include "encounters.h"
#include "gameplay.h"
#include "weapons.h"
#include "player_sprite.h"

SandboxMailbox g_sandbox;
int g_sandbox_freeze_ai;

// The mailbox layout is a contract with the headless scenarios (see sandbox.h).
_Static_assert(offsetof(SandboxMailbox, seq) == 0, "sandbox layout: seq");
_Static_assert(offsetof(SandboxMailbox, ack) == 4, "sandbox layout: ack");
_Static_assert(offsetof(SandboxMailbox, player_x) == 8, "sandbox layout: player_x");
_Static_assert(offsetof(SandboxMailbox, player_y) == 10, "sandbox layout: player_y");
_Static_assert(offsetof(SandboxMailbox, weapon) == 12, "sandbox layout: weapon");
_Static_assert(offsetof(SandboxMailbox, style) == 13, "sandbox layout: style");
_Static_assert(offsetof(SandboxMailbox, enemy_count) == 14, "sandbox layout: enemy_count");
_Static_assert(offsetof(SandboxMailbox, flags) == 15, "sandbox layout: flags");
_Static_assert(offsetof(SandboxMailbox, enemies) == 16, "sandbox layout: enemies");
_Static_assert(sizeof(SandboxEnemy) == 6, "sandbox layout: SandboxEnemy is 6 bytes");
_Static_assert(sizeof(SandboxMailbox) == 112, "sandbox layout: SandboxMailbox is 112 bytes");

#if PLAYGROUND
// Built-in playground layout: the player stands in the south hall and dummies are parked around
// it. Dummies that die come back by themselves after PG_RESPAWN_FRAMES simulated frames of calm.
#define PG_PLAYER_X 384
#define PG_PLAYER_Y 700
#define PG_RESPAWN_FRAMES 90     // by then the death chunks (life 28..35 frames) are gone
#define PG_DUMMY_COUNT 13
_Static_assert(PG_DUMMY_COUNT <= SANDBOX_MAX_ENEMIES, "playground: every dummy fits in the mailbox");

typedef struct {
    uint8_t type;                // SANDBOX_ENEMY_*
    int16_t x;                   // ground position, world px (feet)
    int16_t y;
} PlaygroundDummy;

static const PlaygroundDummy s_dummies[PG_DUMMY_COUNT] = {
    /* east row, y = 700 */
    { SANDBOX_ENEMY_CHARGER, 470, 700 },
    { SANDBOX_ENEMY_SHOOTER, 530, 700 },
    { SANDBOX_ENEMY_CHARGER, 590, 700 },
    { SANDBOX_ENEMY_SHOOTER, 650, 700 },
    /* west row, y = 700 */
    { SANDBOX_ENEMY_CHARGER, 300, 700 },
    { SANDBOX_ENEMY_SHOOTER, 240, 700 },
    { SANDBOX_ENEMY_CHARGER, 180, 700 },
    { SANDBOX_ENEMY_SHOOTER, 120, 700 },
    /* north */
    { SANDBOX_ENEMY_CHARGER, 330, 640 },
    { SANDBOX_ENEMY_SHOOTER, 440, 620 },
    { SANDBOX_ENEMY_CHARGER, 384, 570 },
    /* close to the player and to the south wall */
    { SANDBOX_ENEMY_CHARGER, 424, 716 },
    { SANDBOX_ENEMY_SHOOTER, 380, 745 },
};

static int s_playground_ready;                  // the built-in layout was considered at the first update
static int s_pg_managed;                        // 0 once a scenario has written the mailbox
static int s_dummy_slot[PG_DUMMY_COUNT];        // enemies[] index of each dummy, -1 when none
static int s_dummy_calm[PG_DUMMY_COUNT];        // frames the dummy has been dead
static int s_spawn_slot[SANDBOX_MAX_ENEMIES];   // slot used by sandbox_spawn for each mailbox entry
static Enemy *s_pg_enemies;                     // the array last passed to sandbox_update
static int s_pg_max_enemies;
#endif

// Removes every enemy and effect and resets the encounter bookkeeping. enemies_total stays 0,
// so encounters_update() never completes a run and no map pack is woken.
static void sandbox_clear(Enemy *enemies, int max_enemies) {
    for (int i = 0; i < max_enemies; i++) {
        enemies[i].active = 0;
        enemies[i].hp = 0;
        enemies[i].max_hp = 0;
        enemies[i].pack = -1;
    }
    weapons_init();

    EncounterManager *mgr = &g_encounter_mgr;
    memset(mgr->pack_alive, 0, sizeof(mgr->pack_alive));
    memset(mgr->pack_awake, 0, sizeof(mgr->pack_awake));
    mgr->packs_total = 0;
    mgr->packs_cleared = 0;
    mgr->enemies_total = 0;
    mgr->enemies_remaining = 0;
    mgr->state = ENCOUNTER_STATE_ACTIVE;
    mgr->clear_timer = 0;
    mgr->advance = 0;
}

// Initializes one enemy slot with the fields encounters_spawn() uses. The enemy lives in the
// reserved pack MAX_PACKS - 1; the caller marks that pack awake. ordinal only seeds dir/strafe.
static void sandbox_place(Enemy *e, EnemyType type, int x, int y, int ordinal, int asleep) {
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = MAX_PACKS - 1;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = g_enemy_tuning[type].max_hp;
    e->hp = e->max_hp;
    e->dir = (ordinal * 2) % 8;
    e->frame = 0;
    e->anim_timer = 0;
    if (asleep) e->state = ENEMY_STATE_DORMANT;
    else e->state = ENEMY_INITIAL_STATE(type);
    e->state_timer = 0;
    e->hit_timer = 0;
    e->knock_vx = 0;
    e->knock_vy = 0;
    e->stun_timer = 0;
    e->charge_hit = 0;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    e->has_los = 0;
    g_encounter_mgr.pack_alive[e->pack]++;
}

// Spawns the requested enemies into free slots, with the same field setup as encounters_spawn().
// They live in the reserved pack MAX_PACKS - 1, which is marked awake so encounters_update() never
// wakes them as a pack. enemies_total is deliberately left untouched.
static void sandbox_spawn(Enemy *enemies, int max_enemies) {
    EncounterManager *mgr = &g_encounter_mgr;
    int count = g_sandbox.enemy_count;
    if (count > SANDBOX_MAX_ENEMIES) count = SANDBOX_MAX_ENEMIES;
#if PLAYGROUND
    for (int k = 0; k < SANDBOX_MAX_ENEMIES; k++) s_spawn_slot[k] = -1;
#endif

    int spawned = 0;
    for (int k = 0; k < count; k++) {
        const SandboxEnemy *spec = &g_sandbox.enemies[k];
        EnemyType type;
        if (spec->type == SANDBOX_ENEMY_CHARGER) type = ENEMY_TYPE_CHARGER;
        else if (spec->type == SANDBOX_ENEMY_SHOOTER) type = ENEMY_TYPE_SHOOTER;
        else if (spec->type == SANDBOX_ENEMY_SKELETON) type = ENEMY_TYPE_SKELETON;
        else continue;

        int slot = -1;
        for (int i = 0; i < max_enemies; i++) {
            if (!enemies[i].active) { slot = i; break; }
        }
        if (slot < 0) break;

#if PLAYGROUND
        s_spawn_slot[k] = slot;
#endif
        sandbox_place(&enemies[slot], type, spec->x, spec->y, spawned,
                      (spec->flags & SANDBOX_ENEMY_FLAG_ASLEEP) != 0);
        spawned++;
    }

    if (spawned > 0) mgr->pack_awake[MAX_PACKS - 1] = 1;
}

#if PLAYGROUND
// Puts dummy i back on its spot with full health. A dummy keeps its slot when it has one (so R
// resets a living dummy in place); otherwise it takes the first free slot nobody else maps to.
static void pg_respawn_dummy(Enemy *enemies, int max_enemies, int i) {
    int slot = s_dummy_slot[i];
    if (slot < 0 || slot >= max_enemies) {
        slot = -1;
        for (int j = 0; j < max_enemies && slot < 0; j++) {
            if (enemies[j].active) continue;
            int claimed = 0;
            for (int d = 0; d < PG_DUMMY_COUNT; d++) claimed |= (s_dummy_slot[d] == j);
            if (!claimed) slot = j;
        }
        if (slot < 0) return;          // no room this frame: the dummy retries on the next one
        s_dummy_slot[i] = slot;
    }
    EnemyType type = (s_dummies[i].type == SANDBOX_ENEMY_CHARGER) ? ENEMY_TYPE_CHARGER : ENEMY_TYPE_SHOOTER;
    sandbox_place(&enemies[slot], type, s_dummies[i].x, s_dummies[i].y, i, 0);
    g_encounter_mgr.pack_awake[MAX_PACKS - 1] = 1;
    s_dummy_calm[i] = 0;
}

// Dead dummies (their slot is free or their enemy is no longer alive) count calm frames and come
// back after PG_RESPAWN_FRAMES. A living dummy resets its counter.
static void pg_tick(Enemy *enemies, int max_enemies) {
    for (int i = 0; i < PG_DUMMY_COUNT; i++) {
        int slot = s_dummy_slot[i];
        if (slot >= 0 && slot < max_enemies && enemies[slot].active && enemies[slot].hp > 0) {
            s_dummy_calm[i] = 0;
            continue;
        }
        if (s_dummy_calm[i] < PG_RESPAWN_FRAMES) s_dummy_calm[i]++;
        if (s_dummy_calm[i] >= PG_RESPAWN_FRAMES) pg_respawn_dummy(enemies, max_enemies, i);
    }
}

// Writes the built-in layout into the mailbox and queues it (seq++), so the normal request path
// applies it on this same frame.
static void pg_queue_layout(void) {
    g_sandbox.player_x = PG_PLAYER_X;
    g_sandbox.player_y = PG_PLAYER_Y;
    g_sandbox.weapon = 0;
    g_sandbox.style = 0;
    g_sandbox.flags = SANDBOX_FLAG_CLEAR | SANDBOX_FLAG_FREEZE_AI | SANDBOX_FLAG_GOD;
    g_sandbox.enemy_count = PG_DUMMY_COUNT;
    for (int i = 0; i < PG_DUMMY_COUNT; i++) {
        g_sandbox.enemies[i].type = s_dummies[i].type;
        g_sandbox.enemies[i].flags = 0;
        g_sandbox.enemies[i].x = s_dummies[i].x;
        g_sandbox.enemies[i].y = s_dummies[i].y;
    }
    g_sandbox.seq++;
}
#endif

// R in the playground: every dummy goes back to its spot with full health, living ones included.
// Does nothing once a scenario has taken over the mailbox, or in a build without PLAYGROUND.
void sandbox_respawn(void) {
#if PLAYGROUND
    if (!s_pg_managed || !s_pg_enemies) return;
    for (int i = 0; i < PG_DUMMY_COUNT; i++) pg_respawn_dummy(s_pg_enemies, s_pg_max_enemies, i);
#endif
}

void sandbox_update(Enemy *enemies, int max_enemies, fixed *player_x, fixed *player_y) {
#if PLAYGROUND
    int own_layout = 0;
    s_pg_enemies = enemies;
    s_pg_max_enemies = max_enemies;
    if (!s_playground_ready) {
        s_playground_ready = 1;
        // A scenario request already waiting at boot wins over the built-in layout.
        if (g_sandbox.seq == g_sandbox.ack) {
            pg_queue_layout();
            own_layout = 1;
            s_pg_managed = 1;
        }
    }
    if (s_pg_managed) pg_tick(enemies, max_enemies);
#endif

    if (g_sandbox.seq == g_sandbox.ack) return;

#if PLAYGROUND
    // Any request that is not the built-in layout (a scenario writing the mailbox) takes over:
    // the built-in dummies stop managing themselves.
    if (!own_layout) s_pg_managed = 0;
#endif

    uint8_t flags = g_sandbox.flags;

    if (flags & SANDBOX_FLAG_CLEAR) {
        sandbox_clear(enemies, max_enemies);
    }

    *player_x = TO_FIXED(g_sandbox.player_x);
    *player_y = TO_FIXED(g_sandbox.player_y);
    g_player_state.hp = g_player_state.max_hp;
    g_player_state.is_dead = 0;
    g_player_state.invuln_timer = 0;
    g_player_state.god_mode = (flags & SANDBOX_FLAG_GOD) != 0;
    g_player_state.current_weapon = (WeaponType)(g_sandbox.weapon % NUM_WEAPON_TYPES);
    g_fx_style = g_sandbox.style % FX_STYLE_COUNT;
    g_aura_style = ((flags & SANDBOX_FLAG_AURA_MASK) >> SANDBOX_FLAG_AURA_SHIFT) % AURA_STYLE_COUNT;

    g_sandbox_freeze_ai = (flags & SANDBOX_FLAG_FREEZE_AI) != 0;

    sandbox_spawn(enemies, max_enemies);

#if PLAYGROUND
    if (own_layout) {
        for (int i = 0; i < PG_DUMMY_COUNT; i++) {
            s_dummy_slot[i] = s_spawn_slot[i];
            s_dummy_calm[i] = 0;
        }
    }
#endif

    g_sandbox.ack = g_sandbox.seq;
}

#endif // SANDBOX
