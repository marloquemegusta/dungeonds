#ifndef INVENTORY_H
#define INVENTORY_H

// Pantalla de inventario (DESIGN.md 7.4, mockup B). La escuela activa (nombre, icono, engarces
// grandes y vista previa del cambio) va en la pantalla superior; la bolsa y la ficha, en la inferior.

#include <stdint.h>

#include "arpg_inv.h"
#include <stdint.h>
// Icono de suelo 24x24 del objeto (NULL si no hay arte).
const uint16_t *inv_item_floor_icon24(const ArpgInvItem *it);
// Aura (30x30 u8, icono en 3,3: 0 opaco, 1..3 distancia, 255 nada) y sombra proyectada (INV_FLOOR_SH_W x INV_FLOOR_SH_H, 1 = sombra,
// origen relativo a la base del icono: INV_FLOOR_SH_OX/OY). NULL si no hay arte. Misma geometria que tools/bake_inv_floor_art.py.
#define INV_FLOOR_SH_W 36
#define INV_FLOOR_SH_H 10
#define INV_FLOOR_SH_OX (-24)
#define INV_FLOOR_SH_OY 0
const uint8_t *inv_item_floor_aura30(const ArpgInvItem *it);
const uint8_t *inv_item_floor_shadow(const ArpgInvItem *it);
void inventory_open(void);
// Informa si el lápiz sigue pulsado cada frame para arrastrar reliquias (drag & drop).
void inventory_set_touch_held(int touch_held, int touch_x, int touch_y);
// Procesa entrada del menú. Devuelve 1 cuando debe cerrarse (B sin confirmación).
int  inventory_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y);
void inventory_render(uint16_t *buf);
// Panel de la pantalla superior (256x192). Solo se llama mientras el inventario está abierto.
void inventory_render_top(uint16_t *buf);
// 1 si el panel superior debe repintarse (contenido cambiado). La pantalla es de un solo
// buffer: repintarlo cada frame se pasa del VBlank y rasga la imagen.
int  inventory_top_redraw_pending(void);

#endif // INVENTORY_H
