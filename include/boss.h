#ifndef BOSS_H
#define BOSS_H

#include <stdint.h>
#include "game.h"
#include "gameplay.h"
#include "sfx.h"

// Common boss mode (DESIGN.md 6.13.7): intro, life bar, phases with an invulnerable second, escort and victory.
// A new boss is a BossDef (a const sheet) plus its AI; nothing here is specific to one boss.
// Only exists in the build variant "encuentros" (ENCOUNTERS_PROTO=1).

#if ENCOUNTERS_PROTO

#define BOSS_MAX_PHASES 3
#define BOSS_MAX_ESCORT 3        // entries of an escort list (one entry per enemy type: do not repeat a type in a list)

// One escort entry: `count` enemies of `type` alive at once; one that falls comes back `refill_frames` later,
// walking in from the top of the room at floor x `x[0]` / `x[1]` (alternating).
typedef struct {
    EnemyType type;
    uint8_t count;
    uint16_t refill_frames;
    int16_t x[2];
} BossEscortDef;

typedef struct {
    EnemyType enemy_type;
    const char *name;            // shown big in the intro and under the life bar
    const char *title;           // shown small under the name
    const char *line_intro;      // spoken in the intro, '\n' = line break
    const char *line_defeat;     // spoken on the victory screen
    SfxId sfx_intro, sfx_defeat;
    uint16_t voice_intro_frames, voice_defeat_frames;   // length of each voice in vblanks (include/sfx_voice_len.h)
    uint8_t n_phases;            // 1..3
    uint8_t phase_pct[BOSS_MAX_PHASES];   // life % at which each phase starts (phase_pct[0] = 100)
    uint8_t n_escort[BOSS_MAX_PHASES];
    const BossEscortDef *escort[BOSS_MAX_PHASES];
} BossDef;

enum { BOSS_INACTIVE = 0, BOSS_INTRO, BOSS_COMBAT, BOSS_PHASE_CHANGE, BOSS_VICTORY, BOSS_REST };

// What the room owner (encounters_act1.c) gives the boss mode.
typedef struct {
    void (*spawn_escort)(EnemyType type, int floor_x);   // one enemy walks in awake from the top of the room
    void (*set_barriers)(int closed);                    // the two barriers of the room
} BossHooks;

void boss_set_hooks(const BossHooks *hooks);
void boss_reset(const BossDef *def, int pack);   // new act: INACTIVE; `pack` = owner id of the boss and its escort
void boss_begin(const Enemy *enemies, int max_enemies);   // the hero crossed the bottom edge: close the room, intro
// Once per simulated frame while the boss fight runs: phases, escort and the position of the boss.
// Returns 1 while the boss lives, 0 when it fell (the caller kills the escort and calls boss_victory()).
int boss_combat_update(Enemy *enemies, int max_enemies);
void boss_victory(void);
// Every main loop iteration (outside menus): `dt` vblanks since the last call; START skips the intro and the victory.
void boss_tick(int dt, uint32_t keys_down);

int boss_state(void);
int boss_mode_active(void);                      // intro, combat, phase change or victory: the room is closed
int boss_phase(void);                            // 1-based; what the boss AI asks
int boss_frozen(void);                           // the simulation stops: intro and victory screens
int boss_blocks_damage(const Enemy *e);          // 1 = the boss takes no damage now (phase change)

// Frozen screens. main.c renders both views into the snapshot buffers once per freeze, then each frame:
//   boss_frozen_prepare(); copy boss_frozen_bottom() into the back page; present; boss_frozen_top() into the top page.
int boss_snapshot_pending(void);
// [top != 0] the view the zoom looks at: world y of its top edge = boss_focus_view_y(), so the boss sits in the middle;
// [top == 0] the lower screen as it is. 256x192 BGR555 with bit 15 set, floor included.
uint16_t *boss_snapshot_buffer(int top);
int boss_focus_view_y(void);
void boss_snapshot_commit(int view_x);
const Enemy *boss_last_pose(void);               // the boss on the last frame it lived (victory snapshot draws it)
void boss_frozen_bottom(uint16_t *page);         // whole page, opaque
void boss_frozen_top(uint16_t *page);            // whole page, opaque (only touches it when it changed)

// HUD: life bar in the top row of the bottom screen, name under it. `right` = x where the bar must end.
typedef void (*BossTextFn)(uint16_t *buffer, int x, int y, const char *s, uint16_t ink);
int boss_hud_active(void);
void boss_draw_hud(uint16_t *buffer, int right, BossTextFn text);
// Phase numeral over the boss while it changes phase (drawn by every screen that shows the boss).
void boss_draw_world(uint16_t *buffer, int cam_x, int cam_y);

#endif // ENCOUNTERS_PROTO
#endif // BOSS_H
