#ifndef SFX_H
#define SFX_H

typedef enum {
    SND_HEART_CHARGE = 0,
    SND_HEART_FIRE,
    SND_ENEMY_HIT,
    SND_ENEMY_DEATH,
    SND_PLAYER_HURT,
    SND_ABANDERADO_INTRO,    /* boss voices (DESIGN.md 6.13.7): played centred, one at a time */
    SND_ABANDERADO_DEFEAT,
    SND_COUNT
} SfxId;

/* Initialize NitroFS, Maxmod SFX bank, and looping BGM stream. */
void sfx_init(void);

/* Advance frame counter, store camera X for panning, and refill BGM stream. */
void sfx_frame_begin(int cam_x);

/* Play a one-shot SFX with optional world-space X panning (pass < 0 for center). */
void sfx_play(SfxId id, int world_x);

/* Start or stop the player's charge SFX (cut immediately on fire/cancel/death). */
void sfx_start_charge(void);
void sfx_stop_charge(void);

/* Start, stop, or pause/resume the looping cathedral battle BGM (NitroFS stream). */
void sfx_start_bgm(void);
void sfx_stop_bgm(void);
void sfx_set_bgm_paused(int paused);

/* Choose the BGM track: 0 = cathedral battle (bgm.raw), 1 = boss climax (boss.raw). A running stream restarts on the
 * new track from its beginning; with no stream running it only selects what sfx_start_bgm() will open. */
void sfx_set_bgm_track(int track);

/* Boss voice: a one-shot centred effect that sfx_stop_voice() can cut (skipping a boss screen). */
void sfx_play_voice(SfxId id);
void sfx_stop_voice(void);

#endif /* SFX_H */
