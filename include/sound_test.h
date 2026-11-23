#ifndef SOUND_TEST_H
#define SOUND_TEST_H

// Variante "prueba-sonidos" (SOUND_TEST=1, sobre ARPG_LAB): sala de pruebas de sonido. El menu del lab (SELECT) elige una
// ESCENA; cada una monta, delante del heroe, el grupo de enemigos (o la campana) que dispara unos sonidos concretos.
// 0 = el mapa normal del juego; 1..7 = escenas montadas (las salas no se pueblan). Todo el modulo compila a nada en el resto.
#include "lab_tuning.h"
#include "game.h"
#include "gameplay.h"

#if SOUND_TEST
#define SND_SCENE_COUNT 8

extern int g_snd_scene;                                      // escena elegida en el menu (se aplica al cerrarlo)
extern const char *const g_snd_scene_names[SND_SCENE_COUNT];
extern const char *const g_snd_scene_sounds[SND_SCENE_COUNT];   // que sonidos se oyen en la escena
extern const char *const g_snd_scene_todo[SND_SCENE_COUNT];     // que hacer para dispararlos

void sound_test_reset(void);
// Una vez por frame simulado: monta la escena elegida si cambio y mantiene sus enemigos / su campana.
void sound_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y);
void sound_test_shift_y(int dy_px);       // el mundo se reubica en y (strip_shift_world_y)
int sound_test_freeze(void);              // 1 = la IA de los enemigos esta parada (escenas 1, 2 y 5)
int sound_test_rooms_empty(void);         // 1 = las salas no se pueblan (escena >= 1)
#endif

#endif
