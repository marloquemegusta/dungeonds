#ifndef SFX_H
#define SFX_H

#include "sfx_bank.h"

/* Initialize DS audio hardware and internal SFX mixer state. */
void sfx_init(void);

/* Advance frame counter and store current camera X for stereo panning. */
void sfx_frame_begin(int cam_x);

/* Play a one-shot SFX with optional world-space X panning (pass < 0 for center). */
void sfx_play(SfxId id, int world_x);

/* Start or stop the player's charge SFX (cut immediately on fire/cancel/death). */
void sfx_start_charge(void);
void sfx_stop_charge(void);

#endif /* SFX_H */
