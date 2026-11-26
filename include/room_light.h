#ifndef ROOM_LIGHT_H
#define ROOM_LIGHT_H

// Luz prerenderizada por sala (DESIGN-ARPG.md 11, TECHNICAL.md 5.7): al entrar en una sala, su paquete
// nitro:/arpg_luz/<luz>.bin sustituye el kit de catedral (paleta, tiles, suelo, muros, piezas), los sprites del heroe
// y las tablas de los enemigos; los clips de enemigo (CHR1), los remates (RMT1) y los props de sala (tipo 4) se leen
// del mismo fichero por indice. Solo se lee en la pantalla de carga (regla 3a); un solo paquete residente a la vez.
// Si el paquete no existe, se queda el arte de dia.

#include <stdint.h>
#include <stdio.h>

typedef struct {
    void *dst;
    uint32_t max_bytes;
} RoomLightSlot;

extern const RoomLightSlot g_room_light_slots[];   // generado por tools/room_light_slots.py
extern const uint32_t g_room_light_slot_count;

enum { RL_MAP = 1, RL_CHR1 = 2, RL_RMT1 = 3, RL_PROP = 4 };

#define ROOM_LIGHT_NONE 0xFF
#define ROOM_LIGHT_COUNT 12

// Estado legible por los escenarios. id: indice de la luz cargada (ROOM_LIGHT_NONE = arte de dia); room: sala pedida.
typedef struct {
    uint8_t id;
    uint8_t room;
    uint8_t ok;          // 1 = el ultimo intento cargo el paquete
    uint8_t entries;     // entradas del indice LEXT
    uint32_t loads;      // cargas realizadas
    uint32_t bytes;      // bytes del paquete cargado
    uint32_t load_ticks; // cpuGetTiming() de la ultima carga (33514 ticks = 1 ms)
    uint32_t err;        // punto donde fallo la ultima carga (0 = sin fallo)
} RoomLightState;
extern volatile RoomLightState g_room_light;

// Carga la luz de la sala `room` si no es ya la residente. Devuelve 1 si queda cargada una luz de sala.
int room_light_load(int room);
const char *room_light_id(void);

// Abre el paquete residente posicionado en los datos de una entrada (kind RL_*), o NULL si no hay.
FILE *room_light_open(uint32_t kind, const char *name, uint32_t *len);
// Atajo para los clips de enemigo: `file` es la ruta relativa a NitroFS ("chars/exvoto.bin").
FILE *room_light_open_clip(const char *file);

#endif
