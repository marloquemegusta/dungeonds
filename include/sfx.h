#ifndef SFX_H
#define SFX_H

typedef enum {
    SND_HEART_CHARGE = 0,
    SND_HEART_FIRE,
    SND_ENEMY_HIT,
    SND_ENEMY_DEATH,
    SND_PLAYER_HURT,
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

/* Start or stop the looping cathedral battle BGM (NitroFS stream). */
void sfx_start_bgm(void);
void sfx_stop_bgm(void);

#endif /* SFX_H */
