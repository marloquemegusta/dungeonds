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

// Programs window/blend registers of one engine for this frame. tide_top is the first line
// darkened by the tide (tide_window_top()): >= 192 no tide, <= 0 whole screen, otherwise the
// engine switches to the tide blend settings at that line (VCOUNT interrupt).
void hwshadow_screen_regs(int sub, int tide_top);
// Software shadows selected: no OBJ window, no split interrupt (the tide module programs the regs).
void hwshadow_regs_off(void);

#endif
#endif
