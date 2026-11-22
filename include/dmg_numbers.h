#ifndef DMG_NUMBERS_H
#define DMG_NUMBERS_H

#include "game.h"

typedef enum {
    DMG_NUM_NORMAL = 0, // Player hitting enemy (warm ivory)
    DMG_NUM_DOT,        // Burn / periodic damage (muted ash-violet, vertical)
    DMG_NUM_PLAYER,     // Enemy hitting hero (muted crimson)
    DMG_NUM_HEAL,       // Health restored (+N, muted sage-green)
    DMG_NUM_MANA,       // Mana restored (+N, muted slate-blue)
} DmgNumKind;

void dmg_numbers_reset(void);
void dmg_numbers_set_player_pos(fixed x, fixed y);
void dmg_numbers_spawn(fixed world_x, fixed world_y, int value, DmgNumKind kind);
void dmg_numbers_spawn_player(int value, DmgNumKind kind);
void dmg_numbers_update(void);
void dmg_numbers_draw(uint16_t *buffer, int cam_x, int cam_y);

#endif
