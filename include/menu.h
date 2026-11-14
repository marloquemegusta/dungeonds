#ifndef MENU_H
#define MENU_H

#include <stdint.h>

typedef enum {
    MENU_NONE = 0,
    MENU_TITLE,
    MENU_PAUSE,
    MENU_BESTIARY,
    MENU_CONTROLS
} MenuState;

typedef enum {
    MENU_ACT_NONE = 0,
    MENU_ACT_START_NEW,
    MENU_ACT_RESUME
} MenuAction;

/* Open the title menu, open the pause menu, or close any active menu. */
void menu_open_title(void);
void menu_open_pause(void);
void menu_close(void);

/* Query whether a menu is currently open and which state is active. */
int menu_is_open(void);
MenuState menu_state(void);

/* Process D-pad and stylus input for the active menu. */
MenuAction menu_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y);

/* Render the active menu onto the 256x192 16bpp bottom-screen buffer. */
void menu_render_bottom(uint16_t *buf);

#endif /* MENU_H */
