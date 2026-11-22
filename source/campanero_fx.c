#include "campanero_fx.h"

// STUB: the floor rings, the glyph silencing and the bell sounds are implemented in the other branch.
void cfx_reset(void) {}
void cfx_shift_y(int dy_px) { (void)dy_px; }
void cfx_emit(int kind, int ox, int oy) { (void)kind; (void)ox; (void)oy; }
void cfx_update(void) {}
int cfx_toque_hit(int x, int y) { (void)x; (void)y; return 0; }
void cfx_render_floor(uint16_t *buffer, int cam_x, int cam_y) { (void)buffer; (void)cam_x; (void)cam_y; }
