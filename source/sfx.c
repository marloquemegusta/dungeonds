#include "cfxprof.h"
#include "sfx.h"
#include "room_pool.h"
#include "lab_tuning.h"
#include <stdint.h>
#include <stdio.h>

#ifdef ARM9
#include <nds.h>
#include <filesystem.h>
#include <maxmod9.h>
#include "soundbank.h"
#endif

#define SFX_PAN_CENTER 128
/* BGM tracks in NitroFS: the one place that names them (the boss track is being redone). */
#define SFX_BGM_FILE_NORMAL "nitro:/bgm.raw"
#define SFX_BGM_FILE_BOSS "nitro:/boss.raw"
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
static int s_bgm_track = 0;
static mm_sfxhand s_voice_handle = 0;
#ifdef ARM9
static int s_voice_loaded = -1;      /* SfxId of the boss voice sample currently in RAM (-1 none) */

/* Boss voices are 50-115 KB each: loaded only while they play (the boss snapshots need ~192 KB of the heap while the screens are frozen). */
static int sfx_is_voice(int id) {
    return id == SND_ABANDERADO_INTRO || id == SND_ABANDERADO_DEFEAT || id == SND_CAMPANERO_INTRO || id == SND_CAMPANERO_DEFEAT;
}
#endif
static long s_bgm_saved_pos = 0;

static const mm_word s_mm_ids[SND_COUNT] = {
    [SND_HEART_CHARGE] = SFX_HEART_CHARGE,
    [SND_HEART_FIRE]   = SFX_HEART_FIRE,
    [SND_ENEMY_HIT]    = SFX_ENEMY_HIT,
    [SND_ENEMY_DEATH]  = SFX_ENEMY_DEATH,
    [SND_PLAYER_HURT]  = SFX_PLAYER_HURT,
    [SND_ABANDERADO_INTRO]  = SFX_ABANDERADO_INTRO,
    [SND_ABANDERADO_DEFEAT] = SFX_ABANDERADO_DERROTA,
    [SND_PUNCH_WHOOSH]      = SFX_PUNCH_WHOOSH,
    [SND_PUNCH_HIT]         = SFX_PUNCH_HIT,
    [SND_REMATE_CERA]       = SFX_REMATE_CERA,
    [SND_REMATE_VIGA]       = SFX_REMATE_VIGA,
    [SND_REMATE_OJO]        = SFX_REMATE_OJO,
    [SND_REMATE_DERRETIR]   = SFX_REMATE_DERRETIR,
    [SND_REMATE_TIRON]       = SFX_REMATE_TIRON,
    [SND_REMATE_CAIDA]       = SFX_REMATE_CAIDA,
    [SND_REMATE_FORCEJEO]    = SFX_REMATE_FORCEJEO,
    [SND_REMATE_MANO]        = SFX_REMATE_MANO,
    [SND_WOBBLE_CUE]        = SFX_WOBBLE_CUE,
    [SND_GLIFO_CRACK]       = SFX_GLIFO_GRIETA,
    [SND_GLIFO_DETONATE]    = SFX_GLIFO_DETONACION,
    [SND_OJO_CHARGE]        = SFX_OJO_CHARGE,
    [SND_OJO_FIRE]          = SFX_OJO_FIRE,
    [SND_CIRENEO_CHARGE]    = SFX_CIRENEO_CHARGE,
    [SND_CIRENEO_WALL]      = SFX_CIRENEO_WALL,
    [SND_MONJA_HEAL]        = SFX_MONJA_HEAL,
    [SND_MONAGUILLO_EMERGE] = SFX_MONAGUILLO_EMERGE,
    [SND_BOSS_PHASE]        = SFX_BOSS_PHASE,
    [SND_PICKUP_ORB]        = SFX_PICKUP_ORB,
    [SND_CHEST_OPEN]        = SFX_CHEST_OPEN,
    [SND_DOOR_OPEN]         = SFX_DOOR_OPEN,
    [SND_UI_CLICK]          = SFX_UI_CLICK,
    [SND_RELIC_SOCKET]      = SFX_RELIC_SOCKET,
    [SND_LEVEL_UP]          = SFX_LEVEL_UP,
    [SND_CFX_LIFT]          = SFX_LAB_CREAK,
    [SND_CFX_TANIDO]        = SFX_LAB_BELL_H2,
    [SND_CFX_BONG]          = SFX_LAB_BONG,
    [SND_CFX_BELL_LOW]      = SFX_LAB_BELL_H0,
    [SND_CFX_GLASS_A]       = SFX_LAB_GLASS1,
    [SND_CFX_GLASS_B]       = SFX_LAB_GLASS4,
    [SND_CAMPANERO_INTRO]   = SFX_CAMPANERO_INTRO,
    [SND_CAMPANERO_DEFEAT]  = SFX_CAMPANERO_DERROTA,
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
    [SND_ABANDERADO_INTRO]  = { .volume = 255, .cooldown = 0, .jitter_pct = 0 },
    [SND_ABANDERADO_DEFEAT] = { .volume = 255, .cooldown = 0, .jitter_pct = 0 },
    [SND_PUNCH_WHOOSH]      = { .volume = 185, .cooldown = 3, .jitter_pct = 8  },
    [SND_PUNCH_HIT]         = { .volume = 235, .cooldown = 2, .jitter_pct = 10 },
    [SND_REMATE_CERA]       = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_VIGA]       = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_OJO]        = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_DERRETIR]   = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_TIRON]       = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_CAIDA]       = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_FORCEJEO]    = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_REMATE_MANO]        = { .volume = 245, .cooldown = 6, .jitter_pct = 4  },
    [SND_WOBBLE_CUE]        = { .volume = 180, .cooldown = 8, .jitter_pct = 0  },
    [SND_GLIFO_CRACK]       = { .volume = 255, .cooldown = 4, .jitter_pct = 4  },   /* the clip peaks at 0,36: loud to match */
    [SND_GLIFO_DETONATE]    = { .volume = 235, .cooldown = 4, .jitter_pct = 3  },
    [SND_OJO_CHARGE]        = { .volume = 185, .cooldown = 8, .jitter_pct = 4  },
    [SND_OJO_FIRE]          = { .volume = 240, .cooldown = 4, .jitter_pct = 4  },
    [SND_CIRENEO_CHARGE]    = { .volume = 215, .cooldown = 8, .jitter_pct = 6  },
    [SND_CIRENEO_WALL]      = { .volume = 255, .cooldown = 6, .jitter_pct = 6  },
    [SND_MONJA_HEAL]        = { .volume = 165, .cooldown = 12, .jitter_pct = 4 },
    [SND_MONAGUILLO_EMERGE] = { .volume = 175, .cooldown = 6, .jitter_pct = 10 },
    [SND_BOSS_PHASE]        = { .volume = 250, .cooldown = 10, .jitter_pct = 0 },
    [SND_PICKUP_ORB]        = { .volume = 180, .cooldown = 2, .jitter_pct = 6  },
    [SND_CHEST_OPEN]        = { .volume = 225, .cooldown = 6, .jitter_pct = 0  },
    [SND_DOOR_OPEN]         = { .volume = 220, .cooldown = 10, .jitter_pct = 0 },
    [SND_UI_CLICK]          = { .volume = 175, .cooldown = 2, .jitter_pct = 0  },
    [SND_RELIC_SOCKET]      = { .volume = 220, .cooldown = 3, .jitter_pct = 0  },
    [SND_LEVEL_UP]          = { .volume = 245, .cooldown = 10, .jitter_pct = 0 },
    [SND_CFX_LIFT]          = { .volume = 255, .cooldown = 4, .jitter_pct = 4 },
    [SND_CFX_TANIDO]        = { .volume = 215, .cooldown = 4, .jitter_pct = 3 },
    [SND_CFX_BONG]          = { .volume = 250, .cooldown = 4, .jitter_pct = 2 },
    [SND_CFX_BELL_LOW]      = { .volume = 235, .cooldown = 4, .jitter_pct = 2 },
    [SND_CFX_GLASS_A]       = { .volume = 210, .cooldown = 3, .jitter_pct = 6 },
    [SND_CFX_GLASS_B]       = { .volume = 210, .cooldown = 3, .jitter_pct = 6 },
    [SND_CAMPANERO_INTRO]   = { .volume = 255, .cooldown = 0, .jitter_pct = 0 },
    [SND_CAMPANERO_DEFEAT]  = { .volume = 255, .cooldown = 0, .jitter_pct = 0 },
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
    if (!room_pool_fs_ready()) return;
    mmInitDefault("nitro:/soundbank.bin");
    for (int i = 0; i < SND_COUNT; i++) {
        if (!sfx_is_voice(i)) mmLoadEffect(s_mm_ids[i]);
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

#ifdef ARM9
#if ARPG_LAB
/* Lab build: candidate variants of an event (Kenney CC0, assets/sfx/baked/lab_*.wav) are loaded on first use. */
static const mm_word s_lab_mm_ids[LABV_COUNT] = {
#define X(n, label, mm) [LABV_##n] = mm,
    LAB_VARIANTS(X)
#undef X
};
static uint8_t s_lab_loaded[LABV_COUNT];

static mm_word event_mm_id(SfxId id) {
    int c = lab_sfx_candidate(id);
    if (c < 0 || c >= LABV_COUNT) return s_mm_ids[id];
    if (!s_lab_loaded[c]) {
        mmLoadEffect(s_lab_mm_ids[c]);
        s_lab_loaded[c] = 1;
    }
    return s_lab_mm_ids[c];
}
#else
#define event_mm_id(id) s_mm_ids[id]
#endif
#endif

void sfx_play_pitched(SfxId id, int world_x, uint16_t rate) {
    if (id < 0 || id >= SND_COUNT) return;
    const SfxMixRule *rule = &s_mix_rules[id];
    if (rule->cooldown > 0 && (s_frame - s_last_played[id]) < rule->cooldown) {
        return;
    }
    s_last_played[id] = s_frame;

#ifdef ARM9
    if (!s_audio_ready) return;
    CP_BEGIN(CP_MMARGS);
    mm_sound_effect eff = {
        .id      = event_mm_id(id),
        .rate    = rate ? rate : compute_rate(rule->jitter_pct),
        .handle  = 0,
        .volume  = rule->volume,
        .panning = compute_pan(world_x),
    };
    CP_END(CP_MMARGS);
    CP_BEGIN(CP_MMEFF);
    mmEffectEx(&eff);
    CP_END(CP_MMEFF);
#else
    (void)world_x;
    (void)rate;
#endif
}

void sfx_play(SfxId id, int world_x) {
    sfx_play_pitched(id, world_x, 0);
}

#if ARPG_LAB
void sfx_lab_preview(int ev) {
    if (ev < 0 || ev >= SND_COUNT) return;
#ifdef ARM9
    if (sfx_is_voice(ev)) {            /* boss voices are not resident: sfx_play_voice loads the sample while it plays */
        sfx_play_voice((SfxId)ev);
        return;
    }
#endif
    s_last_played[ev] = s_frame - 100;     /* a preview ignores the event cooldown */
    sfx_play_pitched((SfxId)ev, -1, 1024);
}

void sfx_lab_play_candidate(int labv) {
#ifdef ARM9
    if (labv < 0 || labv >= LABV_COUNT || !s_audio_ready) return;
    if (!s_lab_loaded[labv]) {
        mmLoadEffect(s_lab_mm_ids[labv]);
        s_lab_loaded[labv] = 1;
    }
    mm_sound_effect eff = {
        .id      = s_lab_mm_ids[labv],
        .rate    = 1024,
        .handle  = 0,
        .volume  = 220,
        .panning = SFX_PAN_CENTER,
    };
    mmEffectEx(&eff);
#else
    (void)labv;
#endif
}

void sfx_lab_prepare(int ev) {
#ifdef ARM9
    if (ev >= 0 && ev < SND_COUNT && s_audio_ready) (void)event_mm_id((SfxId)ev);
#else
    (void)ev;
#endif
}
#endif

void sfx_start_charge(void) {
    sfx_stop_charge();
#ifdef ARM9
    if (!s_audio_ready) return;
    mm_sound_effect eff = {
        .id      = event_mm_id(SND_HEART_CHARGE),
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
        s_bgm_file = fopen(s_bgm_track ? SFX_BGM_FILE_BOSS : SFX_BGM_FILE_NORMAL, "rb");
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

void sfx_set_bgm_track(int track) {
    track = track ? 1 : 0;
    if (track == s_bgm_track) return;
    s_bgm_track = track;
#ifdef ARM9
    int was_running = s_stream_active;
    if (was_running) sfx_stop_bgm();
    if (s_bgm_file) {
        fclose(s_bgm_file);
        s_bgm_file = NULL;
    }
    s_bgm_saved_pos = 0;
    if (was_running) sfx_start_bgm();
#endif
}

void sfx_play_voice(SfxId id) {
    sfx_stop_voice();
#ifdef ARM9
    if (!s_audio_ready || id < 0 || id >= SND_COUNT) return;
    if (sfx_is_voice(id)) {
        mmLoadEffect(s_mm_ids[id]);
        s_voice_loaded = id;
    }
    mm_sound_effect eff = {
        .id      = event_mm_id(id),
        .rate    = 1024,
        .handle  = 0,
        .volume  = s_mix_rules[id].volume,
        .panning = SFX_PAN_CENTER,
    };
    s_voice_handle = mmEffectEx(&eff);
#else
    (void)id;
#endif
}

void sfx_stop_voice(void) {
#ifdef ARM9
    if (s_voice_handle) {
        mmEffectCancel(s_voice_handle);
        s_voice_handle = 0;
    }
    if (s_voice_loaded >= 0) {
        mmUnloadEffect(s_mm_ids[s_voice_loaded]);
        s_voice_loaded = -1;
    }
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
