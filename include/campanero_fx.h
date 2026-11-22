#ifndef CAMPANERO_FX_H
#define CAMPANERO_FX_H
// Campanero de Animas: floor rings of the bell (DESIGN-ARPG.md section 9).
#include <stdint.h>
#define CFX_TANIDO 0   // minor toll: no damage, ignores tall pieces, silences every glyph it crosses
#define CFX_TOQUE  1   // major toll: hurts the hero, stopped by tall pieces (columns, statues)
void cfx_reset(void);                                  // clears every ring (new room / run)
void cfx_shift_y(int dy_px);                           // strip rebase, like glifo_shift_y
void cfx_emit(int kind, int ox, int oy);               // a ring is born at the bell (world px of the feet); plays its sound
void cfx_update(void);                                 // once per simulated frame: rings grow, tanidos silence glyphs
int cfx_toque_hit(int x, int y);                       // 1 if a live toque front crosses world point (x,y) this frame and it is not shadowed
void cfx_render_floor(uint16_t *buffer, int cam_x, int cam_y);   // under the actors
#endif
