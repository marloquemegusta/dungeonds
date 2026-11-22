#ifndef PUNCH_H
#define PUNCH_H

// Combo de punetazos (DESIGN.md 7.2; walkthroughs/arpg-predemo/diseno_juego_final.md 10): L corto encadena
// directo (punch_a) -> cruzado (punch_b) -> gancho. Un nuevo L durante el golpe o hasta PUNCH_CHAIN_FRAMES
// despues saca el siguiente; si no, el combo vuelve a empezar por el directo. Los frames de cada golpe viven en
// nitrofiles/punch/<golpe>_d<dir>.bin y se cargan al empezar (un buffer unico, como el remate): tres clips de
// 48x48 en 8 direcciones no caben en el .rodata que queda (~110 KB libres de los 3,5 MiB).
#include <stdint.h>
#include "game.h"
#include "gameplay.h"

#define PUNCH_MOVE_A 0              // directo (corazon_punch_a)
#define PUNCH_MOVE_B 1              // cruzado (corazon_punch_b)
#define PUNCH_MOVE_HOOK 2           // gancho (corazon_gancho)
#define PUNCH_NUM_MOVES 3
#define PUNCH_NUM_DIRS 8
#define PUNCH_NUM_FRAMES 8          // fotogramas por golpe (characters.json: 8 por direccion)
#define PUNCH_CELL 48               // celda del lab (characters.json resolution)
#define PUNCH_TICKS 3               // [TUNABLE-PLACEHOLDER] frames de juego por fotograma de la animacion (~0,4 s por golpe)
#define PUNCH_CHAIN_FRAMES 10       // [TUNABLE-PLACEHOLDER] ventana tras el golpe para encadenar el siguiente con otro L
#define PUNCH_RANGE 28              // [TUNABLE-PLACEHOLDER] alcance del punetazo (px de suelo)
#define PUNCH_DAMAGE_A 50           // [TUNABLE-PLACEHOLDER] dano del directo
#define PUNCH_DAMAGE_B 50           // [TUNABLE-PLACEHOLDER] dano del cruzado
#define PUNCH_DAMAGE_HOOK 90        // [TUNABLE-PLACEHOLDER] dano del gancho
#define PUNCH_HOOK_PUSH 192         // [TUNABLE-PLACEHOLDER] 8.8: empuje del gancho (0,75 px/frame)
#define PUNCH_MAX_BIN_BYTES 16384   // [TUNABLE-PLACEHOLDER] tamano del buffer; el bin mas grande ronda los 12 KB
#define PUNCH_BIN_MAGIC 0x48434E50u  // 'PNCH'
// [TUNABLE-PLACEHOLDER] Golpe en movimiento: el heroe anda al 65 % y el clip de andar baja su cadencia
// en la misma proporcion (current_period / pct) para que los pies no deslicen. El tren superior sigue el
// clip del golpe; el inferior, el de andar (composicion en draw_punch).
#define PUNCH_WALK_SPEED_PCT 65     // % de la velocidad normal mientras pega andando
#define PUNCH_WALK_SPLIT 16         // px sobre los pies donde se corta: debajo anda, encima pega

typedef struct {
    uint32_t magic;
    uint32_t pix_bytes;
    uint32_t runs_bytes;
    uint8_t  bounds[PUNCH_NUM_FRAMES][4];
    uint32_t pix_off[PUNCH_NUM_FRAMES];
    uint32_t run_off[PUNCH_NUM_FRAMES];
} PunchBinHeader;

// Empieza un golpe (PUNCH_MOVE_*). `soft_lock` 1 = parado: apunta al enemigo mas cercano a <= PUNCH_RANGE
// (o hacia delante si no hay ninguno). 0 = andando: pega en `hero_dir` y solo alcanza en un cono frontal de
// +-45 grados, para no girarse hacia un enemigo que queda detras. Aplica ya el dano y el empuje.
int punch_start(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir, int move, int soft_lock);
// Un L nuevo durante el golpe o en su ventana de encadenado: 1 si el combo sigue con el golpe siguiente.
int punch_try_chain(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir, int soft_lock);
// Una vez por frame simulado: avanza la animacion y la ventana de encadenado.
void punch_update(void);
// 1 mientras dura el golpe: el heroe anda al PUNCH_WALK_SPEED_PCT % y se dibuja con el clip del golpe
// (parado, entero; andando, compuesto sobre el clip de andar: piernas de abajo, punetazo de arriba).
int punch_active(void);
int punch_move(void);           // golpe en curso (0..2)
int punch_frame(void);          // fotograma (0..PUNCH_NUM_FRAMES-1)
int punch_dir(void);            // direccion del golpe (0..7)
int punch_chain_window(void);   // frames de ventana que quedan (0 = combo terminado)
void punch_reset(void);

// Fotograma en curso para dibujar: pixeles BGR555 y bounds {x, y, w, h} dentro de la celda PUNCH_CELL,
// sus tramos opacos por fila (blit_stride) y la fila de pies dentro de la celda (la del walk, para no saltar de
// altura entre clips). NULL / 0 sin golpe activo.
const uint16_t *punch_pixels(void);
const uint16_t *punch_runs(void);
const uint8_t *punch_bounds(void);
int punch_ground_anchor(void);

// Fila de pies por golpe y direccion (source/punch_sprites.c, generado por tools/generate_punch_sprites.py).
extern const uint8_t g_punch_ground_anchor[PUNCH_NUM_MOVES][PUNCH_NUM_DIRS];

#endif
