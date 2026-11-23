#ifndef CAMP_HERO_H
#define CAMP_HERO_H
// The hero walking in the camp, lit by the bonfire from 8 azimuths (DESIGN.md 7.5). The 8 variants live in
// NitroFS (nitrofiles/camp/hero_a<N>.bin, baked by tools/camp/bake_camp_hero.py); only the current frame is read
// into a small buffer. The dungeon never uses this.
#include <stdint.h>

// The bonfire's ground point (the Hoguera entry of camp.c).
#define CAMP_FIRE_X 128
#define CAMP_FIRE_Y 300

#define CAMP_HERO_REC_MAX 4096     // largest baked frame (pixels + runs + shadow mask); tools/camp/bake_camp_hero.py

typedef struct {
    const uint16_t *pix;           // BGR555 rows, even pitch, bit 15 = opaque (blit_stride format)
    const uint16_t *runs;          // opaque runs per row (blit_stride format)
    const uint8_t *bounds;         // sprite crop {x, y, w, h} in the 40x40 cell
    const uint8_t *mask;           // shadow, 1 bpp cropped to sbounds
    const uint8_t *sbounds;        // shadow crop {x, y, w, h} in the 80x80 shadow canvas
    int anchor;                    // ground row of the sprite cell
} CampHeroFrame;

// Azimuth 0..7 (S, SW, W, NW, N, NE, E, SE: where the hero stands relative to the bonfire, ground plane), with
// hysteresis so a hero walking along a sector border does not flicker between two lights. (x, y): world px.
int camp_hero_azimuth(int x, int y);
// Forget the current azimuth (entering the camp).
void camp_hero_reset(void);
// Frame of the walk (dir 0..7, frame 0..7) under the light of the hero's position; NULL when the baked files
// are missing (the caller then draws the dungeon sprite).
const CampHeroFrame *camp_hero_frame(int x, int y, int dir, int frame);
// Closes the open file (leaving the camp).
void camp_hero_release(void);

#endif
