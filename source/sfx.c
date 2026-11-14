#include "sfx.h"
#include <stdint.h>
#include <stdio.h>

#ifdef ARM9
#include <nds.h>
#include <filesystem.h>
#include <maxmod9.h>
#include "soundbank.h"
#endif

#define SFX_PAN_CENTER 128
#define BGM_SAMPLE_RATE 11025
#define BGM_BUFFER_LEN 2048

static uint32_t s_frame = 0;
static int s_cam_x = 0;
static uint32_t s_rng = 0x12345678u;
static uint32_t s_last_played[SND_COUNT];

#ifdef ARM9
static mm_sfxhand s_charge_handle = 0;
static FILE *s_bgm_file = NULL;
static int s_audio_ready = 0;
static int s_stream_active = 0;
static int s_bgm_paused = 0;
static long s_bgm_saved_pos = 0;

static const mm_word s_mm_ids[SND_COUNT] = {
    [SND_HEART_CHARGE] = SFX_HEART_CHARGE,
    [SND_HEART_FIRE]   = SFX_HEART_FIRE,
    [SND_ENEMY_HIT]    = SFX_ENEMY_HIT,
    [SND_ENEMY_DEATH]  = SFX_ENEMY_DEATH,
    [SND_PLAYER_HURT]  = SFX_PLAYER_HURT,
};
#endif

typedef struct {
    uint8_t volume;       /* 0..255 */
    uint8_t cooldown;     /* minimum frames between triggers */
    uint8_t jitter_pct;   /* +/- percentage pitch jitter */
} SfxMixRule;

static const SfxMixRule s_mix_rules[SND_COUNT] = {
    [SND_HEART_CHARGE] = { .volume = 175, .cooldown = 0, .jitter_pct = 0  },
    [SND_HEART_FIRE]   = { .volume = 245, .cooldown = 0, .jitter_pct = 4  },
    [SND_ENEMY_HIT]    = { .volume = 190, .cooldown = 2, .jitter_pct = 12 },
    [SND_ENEMY_DEATH]  = { .volume = 220, .cooldown = 3, .jitter_pct = 6  },
    [SND_PLAYER_HURT]  = { .volume = 255, .cooldown = 0, .jitter_pct = 0  },
};

static uint32_t next_rng(void) {
    s_rng = s_rng * 1664525u + 1013904223u;
    return s_rng;
}

static uint8_t compute_pan(int world_x) {
    if (world_x < 0) return SFX_PAN_CENTER;
    int rel = world_x - s_cam_x;
    /* Map [0..256] screen X to [32..224] pan so edges stay audible on both speakers. */
    int pan = 32 + ((rel * 192) >> 8);
    if (pan < 32) pan = 32;
    if (pan > 224) pan = 224;
    return (uint8_t)pan;
}

static uint16_t compute_rate(uint8_t jitter_pct) {
    if (jitter_pct == 0) return 1024;
    /* Maxmod rate: 1024 = 1.0x. Map top 8 bits of LCG to [-jitter_pct .. +jitter_pct]. */
    int r = (int)(next_rng() >> 24) - 128; /* -128..127 */
    int delta = (1024 * r * (int)jitter_pct) / (128 * 100);
    return (uint16_t)(1024 + delta);
}

#ifdef ARM9
static mm_word bgm_stream_cb(mm_word length, mm_addr dest, mm_stream_formats format) {
    (void)format;
    if (!s_bgm_file) return 0;
    uint8_t *out = (uint8_t *)dest;
    size_t got = fread(out, 1, (size_t)length, s_bgm_file);
    if (got < (size_t)length) {
        fseek(s_bgm_file, 0, SEEK_SET);
        size_t rem = (size_t)length - got;
        size_t got2 = fread(out + got, 1, rem, s_bgm_file);
        got += got2;
    }
    return (mm_word)got;
}
#endif

void sfx_init(void) {
    s_frame = 1;
    s_cam_x = 0;
    for (int i = 0; i < SND_COUNT; i++) {
        s_last_played[i] = 0;
    }

#ifdef ARM9
    s_charge_handle = 0;
    if (!nitroFSInit(NULL)) return;
    mmInitDefault("nitro:/soundbank.bin");
    for (int i = 0; i < SND_COUNT; i++) {
        mmLoadEffect(s_mm_ids[i]);
    }
    s_audio_ready = 1;
    sfx_start_bgm();
#endif
}

void sfx_frame_begin(int cam_x) {
    s_frame++;
    s_cam_x = cam_x;
#ifdef ARM9
    if (s_stream_active) {
        mmStreamUpdate();
    }
#endif
}

void sfx_play(SfxId id, int world_x) {
    if (id < 0 || id >= SND_COUNT) return;
    const SfxMixRule *rule = &s_mix_rules[id];
    if (rule->cooldown > 0 && (s_frame - s_last_played[id]) < rule->cooldown) {
        return;
    }
    s_last_played[id] = s_frame;

#ifdef ARM9
    if (!s_audio_ready) return;
    mm_sound_effect eff = {
        .id      = s_mm_ids[id],
        .rate    = compute_rate(rule->jitter_pct),
        .handle  = 0,
        .volume  = rule->volume,
        .panning = compute_pan(world_x),
    };
    mmEffectEx(&eff);
#else
    (void)world_x;
#endif
}

void sfx_start_charge(void) {
    sfx_stop_charge();
#ifdef ARM9
    if (!s_audio_ready) return;
    mm_sound_effect eff = {
        .id      = s_mm_ids[SND_HEART_CHARGE],
        .rate    = 1024,
        .handle  = 0,
        .volume  = s_mix_rules[SND_HEART_CHARGE].volume,
        .panning = SFX_PAN_CENTER,
    };
    s_charge_handle = mmEffectEx(&eff);
#endif
}

void sfx_stop_charge(void) {
#ifdef ARM9
    if (s_charge_handle) {
        mmEffectCancel(s_charge_handle);
        s_charge_handle = 0;
    }
#endif
}

#ifdef ARM9
static void open_bgm_stream(void) {
    mm_stream st = {
        .sampling_rate = BGM_SAMPLE_RATE,
        .buffer_length = BGM_BUFFER_LEN,
        .callback      = bgm_stream_cb,
        .format        = MM_STREAM_8BIT_MONO,
        .timer         = MM_TIMER0,
        .manual        = true,
    };
    mmStreamOpen(&st);
    s_stream_active = 1;
}
#endif

void sfx_start_bgm(void) {
    sfx_stop_bgm();
#ifdef ARM9
    s_bgm_saved_pos = 0;
    s_bgm_paused = 0;
    if (!s_audio_ready) return;
    if (!s_bgm_file) {
        s_bgm_file = fopen("nitro:/bgm.raw", "rb");
    } else {
        fseek(s_bgm_file, 0, SEEK_SET);
    }
    if (s_bgm_file) {
        open_bgm_stream();
    }
#endif
}

void sfx_stop_bgm(void) {
#ifdef ARM9
    if (s_stream_active) {
        mmStreamClose();
        s_stream_active = 0;
    }
    s_bgm_paused = 0;
    s_bgm_saved_pos = 0;
#endif
}

void sfx_set_bgm_paused(int paused) {
#ifdef ARM9
    if (paused) {
        sfx_stop_charge();
        if (s_stream_active) {
            long pos = s_bgm_file ? ftell(s_bgm_file) : 0;
            s_bgm_saved_pos = pos >= 0 ? pos : 0;
            mmStreamClose();
            s_stream_active = 0;
            s_bgm_paused = 1;
        }
    } else {
        if (s_bgm_paused && s_audio_ready && s_bgm_file) {
            fseek(s_bgm_file, s_bgm_saved_pos, SEEK_SET);
            open_bgm_stream();
            s_bgm_paused = 0;
        }
    }
#else
    (void)paused;
#endif
}
