// Generado por tools/generate_punch_sprites.py: no editar a mano.
#include "punch.h"

// Fila de pies dentro de la celda 48x48 del lab, por golpe y direccion (S, SW, W, NW, N, NE, E, SE).
const uint8_t g_punch_ground_anchor[PUNCH_NUM_MOVES][PUNCH_NUM_DIRS] = {
    { 36, 36, 36, 36, 36, 36, 36, 36 }, // punch_a
    { 37, 37, 37, 37, 37, 37, 37, 37 }, // punch_b
    { 37, 37, 37, 37, 37, 37, 37, 37 }, // gancho
};

// Rezo del Glifo (corazon_pray): fila de pies por direccion.
const uint8_t g_pray_ground_anchor[PUNCH_NUM_DIRS] = { 38, 38, 38, 38, 38, 38, 38, 38 };
