#include "sfx.h"
#include <stdint.h>

#ifdef ARM9
#include <nds.h>
#endif

#define SFX_SCREEN_W 256
#define SFX_PAN_CENTER 64

static uint32_t s_frame = 0;
static int s_cam_x = 0;
static int s_charge_channel = -1;
static uint32_t s_rng = 0x12345678u;
static uint32_t s_last_played[SFX_COUNT];

typedef struct {
    uint8_t volume;       /* 0..127 */
    uint8_t cooldown;     /* minimum frames between triggers */
    uint8_t jitter_pct;   /* +/- percentage pitch jitter */
} SfxMixRule;

static const SfxMixRule s_mix_rules[SFX_COUNT] = {
    [SFX_HEART_CHARGE] = { .volume = 82,  .cooldown = 0, .jitter_pct = 0  },
    [SFX_HEART_FIRE]   = { .volume = 120, .cooldown = 0, .jitter_pct = 4  },
    [SFX_ENEMY_HIT]    = { .volume = 92,  .cooldown = 2, .jitter_pct = 12 },
    [SFX_ENEMY_DEATH]  = { .volume = 108, .cooldown = 3, .jitter_pct = 6  },
    [SFX_PLAYER_HURT]  = { .volume = 127, .cooldown = 0, .jitter_pct = 0  },
};

static uint32_t next_rng(void) {
    s_rng = s_rng * 1664525u + 1013904223u;
    return s_rng;
}

static uint8_t compute_pan(int world_x) {
    if (world_x < 0) return SFX_PAN_CENTER;
    int rel = world_x - s_cam_x;
    /* Map [0..256] screen X to [16..112] pan so extreme edges stay audible on both speakers. */
    int pan = 16 + ((rel * 96) >> 8);
    if (pan < 16) pan = 16;
    if (pan > 112) pan = 112;
    return (uint8_t)pan;
}

static uint16_t compute_freq(uint8_t jitter_pct) {
    if (jitter_pct == 0) return SFX_SAMPLE_RATE;
    /* Map top 8 bits of LCG to [-jitter_pct .. +jitter_pct] in integer math. */
    int r = (int)(next_rng() >> 24) - 128; /* -128..127 */
    int delta = (SFX_SAMPLE_RATE * r * (int)jitter_pct) / (128 * 100);
    return (uint16_t)(SFX_SAMPLE_RATE + delta);
}

void sfx_init(void) {
#ifdef ARM9
    soundEnable();
#endif
    s_frame = 1;
    s_cam_x = 0;
    s_charge_channel = -1;
    for (int i = 0; i < SFX_COUNT; i++) {
        s_last_played[i] = 0;
    }
}

void sfx_frame_begin(int cam_x) {
    s_frame++;
    s_cam_x = cam_x;
}

void sfx_play(SfxId id, int world_x) {
    if (id < 0 || id >= SFX_COUNT) return;
    const SfxMixRule *rule = &s_mix_rules[id];
    if (rule->cooldown > 0 && (s_frame - s_last_played[id]) < rule->cooldown) {
        return;
    }
    s_last_played[id] = s_frame;

#ifdef ARM9
    const SfxClip *clip = &g_sfx_bank[id];
    if (!clip->data || clip->length == 0) return;
    uint16_t freq = compute_freq(rule->jitter_pct);
    uint8_t pan = compute_pan(world_x);
    soundPlaySample(clip->data, SoundFormat_8Bit, clip->length, freq,
                    rule->volume, pan, false, 0);
#else
    (void)world_x;
#endif
}

void sfx_start_charge(void) {
    sfx_stop_charge();
#ifdef ARM9
    const SfxClip *clip = &g_sfx_bank[SFX_HEART_CHARGE];
    const SfxMixRule *rule = &s_mix_rules[SFX_HEART_CHARGE];
    if (!clip->data || clip->length == 0) return;
    s_charge_channel = soundPlaySample(clip->data, SoundFormat_8Bit, clip->length,
                                       SFX_SAMPLE_RATE, rule->volume, SFX_PAN_CENTER,
                                       false, 0);
#endif
}

void sfx_stop_charge(void) {
#ifdef ARM9
    if (s_charge_channel >= 0) {
        soundKill(s_charge_channel);
        s_charge_channel = -1;
    }
#endif
}
