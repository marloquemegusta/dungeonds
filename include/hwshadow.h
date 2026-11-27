#ifndef HWSHADOW_H
#define HWSHADOW_H

#include <stdint.h>

// Actor shadows drawn by the 2D engines instead of the CPU (DESIGN.md 3, "Sombras de personajes
// por hardware"). Each shadow mask becomes OBJ-window sprites; the window region darkens the
// floor layer only (brightness decrease), so the actor bitmap (BG2) is never darkened.
// GODRAYS_PROTO keeps the software path: it uses the same OBJ banks.
#ifndef HW_SHADOWS
#define HW_SHADOWS 1
#endif
#if defined(GODRAYS_PROTO) && GODRAYS_PROTO
#undef HW_SHADOWS
#define HW_SHADOWS 0
#endif

// Brightness-decrease level that matches the 50 % look of the software shadow (0..16).
#define HW_SHADOW_BLDY 8

#if HW_SHADOWS

// Runtime switch (the stress build toggles it to A/B on the console). Non-zero = hardware.
extern int g_hw_shadows_on;

void hwshadow_init(void);

// Per screen (sub = 0 main/bottom, 1 sub/top): start a new list, add one shadow per actor, and
// commit it inside VBlank. ox/oy are the screen position of the shadow canvas origin
// (canvas left/top minus the camera); bounds = {x, y, w, h} of the cropped mask inside it.
void hwshadow_begin(int sub);
void hwshadow_add(int sub, const uint8_t *mask, const uint8_t *bounds, int ox, int oy);
void hwshadow_commit(int sub);
void hwshadow_invalidate(const uint8_t *mask);
// Every entry whose mask lies in [lo, hi): the room pool empties or a mask buffer is overwritten.
void hwshadow_invalidate_range(const void *lo, const void *hi);

// Rastrillo of the encounter rooms (DESIGN.md 6.13.6): the gate is drawn with four regular 64x64
// OBJs from the first 128 pool tiles (reserved at init, the shadow pool never uses them). x, y is the
// screen position of the pair's top-left corner (both halves, 208x56); lift_px (0..55) slides the
// art up inside its box so the gate rises and is cut by its top edge instead of floating.
// in_front: 0 = behind actors (top gate), 1 = in front of actors (rear gate, occludes hero inside).
void hwshadow_add_verja(int sub, int x, int y, int lift_px, int in_front);

// Light of the room for the gate (source/room_light.c): OBJ palette (16 BGR555) and ground shadow (rows x 13 B: left half
// 56 px, rows x 7 B, then right half 48 px, rows x 6 B; r0 = first row of the shadow in the 104x56 gate canvas; dir 0 = it falls
// towards the camera, 1 = towards the back). rows = 0: no shadow. The tile art itself is g_verja_pixels, re-uploaded on next use.
void hwshadow_verja_set(const uint16_t *palette, const uint8_t *shadow, int r0, int rows, int dir);
// The shadow of the gate on the floor (x, y as hwshadow_add_verja). Raising the gate (lift_px) shortens it.
void hwshadow_add_verja_shadow(int sub, int x, int y, int lift_px);
extern volatile uint8_t g_verja_shadow_off;   // scenarios only: 1 hides it

// Programs window/blend registers of one engine for this frame.
void hwshadow_screen_regs(int sub);
// Software shadows selected: no OBJ window.
void hwshadow_regs_off(void);

#endif
#endif
