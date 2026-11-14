#ifndef ENEMY_LASER_H
#define ENEMY_LASER_H

#include <stdint.h>
#include "gameplay.h"

// Ojo del Tribunal drawing (DESIGN.md 6.10 "Mirada colimada"). None of it holds state: the FSM lives in
// enemy_ai.c (Enemy state, state_timer, aim_px/aim_py).
// Collimating gaze band (TRACK, LOCK) and sentence beam (SENTENCE) of every Ojo, under the actor sprites.
void enemy_lasers_render(uint16_t *buffer, const Enemy *enemies, int count, int cam_x, int cam_y);

// Ground distance (px) from (fx, fy) along the true-ground unit vector (vx, vy) (1.15) to the first wall or
// column, or max_len; the sentence beam and the gaze band are cut there.
int ojo_ray_wall_dist(int fx, int fy, int vx, int vy, int max_len);

// Mouth charge aura drawn on top of the Ojo's sprite at the hand-held head.
void enemy_ojo_mouth_glow_render(uint16_t *buffer, const Enemy *e, int idx, int cam_x, int cam_y, int depth);

#endif // ENEMY_LASER_H
