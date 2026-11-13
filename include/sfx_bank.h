#ifndef SFX_BANK_H
#define SFX_BANK_H

#include <stdint.h>

#define SFX_SAMPLE_RATE 16384

typedef enum {
    SFX_HEART_CHARGE,
    SFX_HEART_FIRE,
    SFX_ENEMY_HIT,
    SFX_ENEMY_DEATH,
    SFX_PLAYER_HURT,
    SFX_COUNT
} SfxId;

typedef struct {
    const int8_t *data;
    uint32_t length;
} SfxClip;

extern const SfxClip g_sfx_bank[SFX_COUNT];

#endif /* SFX_BANK_H */
