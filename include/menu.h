#ifndef MENU_H
#define MENU_H

#include <stdint.h>

typedef enum {
    MENU_NONE = 0,
    MENU_TITLE,
    MENU_PAUSE,
    MENU_BESTIARY,
    MENU_CONTROLS,
    MENU_LEVELUP,       /* DESIGN.md 6.12.8: pick 1 of 3 cards, no cancel */
    MENU_INVENTORY      /* DESIGN.md 7.4: reliquias y tomos (arcón del campamento o pausa) */
} MenuState;

typedef enum {
    MENU_ACT_NONE = 0,
    MENU_ACT_START_NEW,
    MENU_ACT_START_INTRO, /* NUEVA PARTIDA desde el titulo: tarjetas de introduccion y partida */
    MENU_ACT_RESUME,
    MENU_ACT_LEVELUP_PICK, /* a card was chosen: read it with menu_levelup_pick() */
    MENU_ACT_CONTINUE,     /* CONTINUAR desde el titulo: cargar la partida guardada */
    MENU_ACT_TO_CAMP       /* pausa: volver al campamento */
} MenuAction;

/* Open the title menu, open the pause menu, or close any active menu. */
void menu_open_title(void);
void menu_open_pause(int from_camp);   /* from_camp != 0 hides "Volver al campamento" */
/* Inventario (DESIGN.md 7.4). Volver/B lo cierra: vuelve al padre (campamento o pausa). */
void menu_open_inventory(void);
/* Códice (bestiary) from the camp's lectern: opens the viewer, B closes it back to the camp scene. */
void menu_open_codex(void);
void menu_close(void);
/* Level-up cards (upgrades_begin_offer() must have run). */
void menu_open_levelup(void);
int menu_levelup_pick(void);

/* Query whether a menu is currently open and which state is active. */
int menu_is_open(void);
MenuState menu_state(void);

/* Process D-pad and stylus input for the active menu. */
MenuAction menu_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y);

/* Render the active menu onto the 256x192 16bpp bottom-screen buffer. */
void menu_render_bottom(uint16_t *buf);

#endif /* MENU_H */
