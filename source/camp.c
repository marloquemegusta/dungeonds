#include "camp.h"
#if CAMP_SCENE

#include "arena.h"
#include "collision.h"
#include "player_sprite.h"
#include "camp_props_gfx.h"
#include "camp_arena_data.h"
#include "camp_marco.h"
#include "bestiary_font.h"
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// The camp is its own static room, one screen wide and two screens tall, shown whole across both
// DS screens (top = world rows 0..192, bottom = 192..384). The floor and walls come from the
// cathedral kit (baked by tools/camp/bake_camp_arena.py with a paler, colder floor palette); the
// props (bonfire, bedroll, chest, table, lectern, door) are drawn as software sprites on top, the
// same way the HUD and the room fixtures are.

#define CAMP_ROOM_W (CAMP_WORLD_W)       // 256
#define CAMP_ROOM_H (CAMP_WORLD_H)       // 384
#define CAMP_COLL_W (CAMP_ROOM_W / COLLISION_SCALE)
#define CAMP_COLL_H (CAMP_ROOM_H / COLLISION_SCALE)

// Warm, muted FX_SH_*-style colours (never pure primaries). The bonfire flame itself is a precalculated
// strip (nitrofiles/camp/hoguera_fuego.bin, tools/camp/fuego_frames.py) with the same ramp.
#define COL_GOLD    (RGB15(27, 20, 11) | BIT(15))
#define COL_INK     (RGB15(29, 25, 19) | BIT(15))
#define COL_INK_SH  (RGB15(1, 1, 2) | BIT(15))

#define CAMP_DOOR_HIT_W (CAMP_MARCO_DOOR_X1 - CAMP_MARCO_DOOR_X0)   // hole of the gate in the wall frame
#define CAMP_DOOR_HIT_H (CAMP_MARCO_DOOR_Y1 - CAMP_MARCO_DOOR_Y0)
#define CAMP_REACH_PX 34                 // ground px: hero this close to a prop can use it

typedef struct {
    const uint16_t *pix;
    int w, h;
    int x, y;            // ground point (bottom-centre of the sprite)
    const char *name;
    int act;             // CAMP_ACT_*
    const uint8_t *shadow;   // baked ground shadow (4-bit nibbles), on its own canvas
    int shw, shh;            // shadow canvas size
    int shox, shoy;          // canvas top-left relative to the colour sprite top-left
} CampProp;

// Disposition (world px, y down): the door up top and centred (shown on the top screen), the camp
// itself on the bottom screen â€” bonfire with the bedroll beside it, table and chest on the left,
// lectern on the right (DESIGN.md: the camp as its own room).
static CampProp s_props[] = {
    // The door is the gate panel of the wall frame (tools/camp/marco_build.py): no sprite and no shadow, only
    // the interaction point. w/h is the hole of the gate (touch area), x/y the threshold.
    { NULL,  CAMP_DOOR_HIT_W, CAMP_DOOR_HIT_H, 128, CAMP_MARCO_BASE_N + 1, "Puerta",       CAMP_ACT_DOOR,
      NULL,  0,  0,  0,  0  },
    { NULL,    CAMP_MESA_W,    CAMP_MESA_H,      60, 250, "Mesa",         CAMP_ACT_NONE,
      NULL,    CAMP_MESA_SHADOW_W,    CAMP_MESA_SHADOW_H,
      CAMP_MESA_SHADOW_OX,    CAMP_MESA_SHADOW_OY    },
    { NULL,   CAMP_ARCON_W,   CAMP_ARCON_H,     58, 292, "ArcÃ³n",        CAMP_ACT_INVENTORY,
      NULL,   CAMP_ARCON_SHADOW_W,   CAMP_ARCON_SHADOW_H,
      CAMP_ARCON_SHADOW_OX,   CAMP_ARCON_SHADOW_OY   },
    { NULL,   CAMP_ATRIL_W,   CAMP_ATRIL_H,    198, 296, "Atril",        CAMP_ACT_CODEX,
      NULL,   CAMP_ATRIL_SHADOW_W,   CAMP_ATRIL_SHADOW_H,
      CAMP_ATRIL_SHADOW_OX,   CAMP_ATRIL_SHADOW_OY   },
    { NULL, CAMP_HOGUERA_W, CAMP_HOGUERA_H,  128, 300, "Hoguera",      CAMP_ACT_NONE,
      NULL, CAMP_HOGUERA_SHADOW_W, CAMP_HOGUERA_SHADOW_H,
      CAMP_HOGUERA_SHADOW_OX, CAMP_HOGUERA_SHADOW_OY },
    { NULL,  CAMP_JERGON_W,  CAMP_JERGON_H,   196, 346, "JergÃ³n",       CAMP_ACT_SLEEP,
      NULL,  CAMP_JERGON_SHADOW_W,  CAMP_JERGON_SHADOW_H,
      CAMP_JERGON_SHADOW_OX,  CAMP_JERGON_SHADOW_OY  },
};
#define CAMP_PROP_COUNT ((int)(sizeof(s_props) / sizeof(s_props[0])))

static Arena s_camp_arena;
static uint8_t (*s_camp_tiles)[64] = NULL;   // floor tiles: nitro:/camp/floor_tiles.bin (CAMP_NUM_TILES x 64)
static uint8_t s_camp_collision[(CAMP_COLL_W * CAMP_COLL_H) / 4];
static uint32_t s_camp_occ_rows[CAMP_ROOM_H + 1];
static int s_built = 0;
static int s_active = 0;
static int s_focus = -1;             // prop the hero is next to (-1 none)
static char s_toast[48];
static int s_toast_frames = 0;
static int s_anim = 0;
static const uint16_t *s_marco_n = NULL, *s_marco_l = NULL, *s_marco_r = NULL;   // wall frame sprites (nitro:/camp/marco_*.bin)
static const uint16_t *s_fire = NULL;   // bonfire flame strip: CAMP_FUEGO_FRAMES frames of CAMP_FUEGO_W x CAMP_FUEGO_H

// Screen-visible props of the current render pass, filled by camp_items_count.
static int s_vis[CAMP_PROP_COUNT];
static int s_vis_n = 0;

static void set_coll(int cx, int cy, unsigned value) {
    if (cx < 0 || cx >= CAMP_COLL_W || cy < 0 || cy >= CAMP_COLL_H) return;
    unsigned index = (unsigned)cy * CAMP_COLL_W + (unsigned)cx;
    unsigned shift = (index & 3u) << 1;
    uint8_t mask = (uint8_t)(3u << shift);
    s_camp_collision[index >> 2] =
        (uint8_t)((s_camp_collision[index >> 2] & (uint8_t)~mask) | ((value & 3u) << shift));
}

static void block_rect(int x, int y, int w, int h, unsigned v) {
    int c0 = x / COLLISION_SCALE, c1 = (x + w) / COLLISION_SCALE;
    int r0 = y / COLLISION_SCALE, r1 = (y + h) / COLLISION_SCALE;
    for (int r = r0; r <= r1; r++)
        for (int c = c0; c <= c1; c++) set_coll(c, r, v);
}

// Prop pixels and ground shadows are read from NitroFS (nitrofiles/camp/, written by
// tools/camp/generate_camp_gfx.py) instead of living in the ARM9 binary, whose static EWRAM budget
// is full. Same order as s_props.
static const char *const s_gfx_stem[] = { "puerta", "mesa", "arcon", "atril", "hoguera", "jergon" };

static void *load_camp_bin(const char *stem, const char *suffix, size_t bytes) {
    char path[64];
    snprintf(path, sizeof(path), "nitro:/camp/%s%s.bin", stem, suffix);
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    void *buf = malloc(bytes);
    if (buf && fread(buf, 1, bytes, f) != bytes) {
        free(buf);
        buf = NULL;
    }
    fclose(f);
    return buf;
}

static void load_camp_gfx(void) {
    if (!s_camp_tiles)
        s_camp_tiles = load_camp_bin("floor_tiles", "", (size_t)CAMP_NUM_TILES * 64);
    if (!s_fire)
        s_fire = load_camp_bin("hoguera_fuego", "",
                               (size_t)CAMP_FUEGO_W * CAMP_FUEGO_H * CAMP_FUEGO_FRAMES * 2);
    if (!s_marco_n) s_marco_n = load_camp_bin("marco_norte", "", (size_t)CAMP_ROOM_W * CAMP_MARCO_NORTH_H * 2);
    if (!s_marco_l) s_marco_l = load_camp_bin("marco_izq", "", (size_t)CAMP_MARCO_SIDE_W * CAMP_MARCO_SIDE_H * 2);
    if (!s_marco_r) s_marco_r = load_camp_bin("marco_der", "", (size_t)CAMP_MARCO_SIDE_W * CAMP_MARCO_SIDE_H * 2);
    for (int i = 0; i < CAMP_PROP_COUNT; i++) {
        CampProp *p = &s_props[i];
        if (p->pix || p->act == CAMP_ACT_DOOR) continue;   // the door is in the baked wall: nothing to load
        p->pix = load_camp_bin(s_gfx_stem[i], "", (size_t)p->w * p->h * 2);
        p->shadow = load_camp_bin(s_gfx_stem[i], "_shadow", (size_t)((p->shw + 1) / 2) * p->shh);
    }
}

static void build_arena(void) {
    load_camp_gfx();
    memset(s_camp_collision, 0, sizeof(s_camp_collision));
    // Walls = the inner edge of the wall frame: 24 px each side, the north wall (gate set into it) and the
    // foot. The hero stops in front of the wall and can walk right up to the gate.
    block_rect(0, 0, 24, CAMP_ROOM_H, 3);
    block_rect(CAMP_ROOM_W - 24, 0, 24, CAMP_ROOM_H, 3);
    block_rect(0, 0, CAMP_ROOM_W, 104, 3);   // north wall (base of the panels y=CAMP_MARCO_BASE_N); the gate is a threshold below it
    block_rect(0, CAMP_ROOM_H - 10, CAMP_ROOM_W, 10, 3);
    // Props block their base so the hero stops in front of them (the door is a threshold: no block).
    for (int i = 0; i < CAMP_PROP_COUNT; i++) {
        const CampProp *p = &s_props[i];
        if (p->act == CAMP_ACT_DOOR) continue;
        int fw = (p->w * 7) / 10;
        block_rect(p->x - fw / 2, p->y - 6, fw, 10, 1);
    }

    memset(&s_camp_arena, 0, sizeof(s_camp_arena));
    s_camp_arena.name = "Campamento";
    s_camp_arena.world_w = CAMP_ROOM_W;
    s_camp_arena.world_h = CAMP_ROOM_H;
    s_camp_arena.collision_w = CAMP_COLL_W;
    s_camp_arena.collision_h = CAMP_COLL_H;
    s_camp_arena.map_w = CAMP_MAP_W;
    s_camp_arena.map_h = CAMP_MAP_H;
    // Without the floor tiles (read failed) num_tiles stays 0: the renderer then draws void instead of
    // reading a NULL table (main.c checks tile_id >= num_tiles before touching tiles).
    s_camp_arena.num_tiles = s_camp_tiles ? CAMP_NUM_TILES : 0;
    s_camp_arena.player_x = CAMP_START_X;
    s_camp_arena.player_y = CAMP_START_Y;
    s_camp_arena.num_enemies = 0;
    s_camp_arena.collision = s_camp_collision;
    s_camp_arena.palette = g_camp_palette;
    s_camp_arena.tiles = s_camp_tiles;
    s_camp_arena.map = g_camp_floor_map;
    s_camp_arena.occlusion_runs = 0;
    s_camp_arena.occlusion_row_start = s_camp_occ_rows;
    s_camp_arena.enemies = 0;
    s_built = 1;
}

const Arena *camp_arena(void) {
    if (!s_built) build_arena();
    return &s_camp_arena;
}

int camp_active(void) { return s_active; }
void camp_set_active(int on) {
    s_active = on;
    s_focus = -1;
    s_toast_frames = 0;
    s_toast[0] = 0;
}

void camp_toast(const char *msg) {
    if (!msg) msg = "";
    strncpy(s_toast, msg, sizeof(s_toast) - 1);
    s_toast[sizeof(s_toast) - 1] = 0;
    s_toast_frames = 150;
}

static int prop_focus(const Player *p) {
    int px = TO_INT(p->x), py = TO_INT(p->y);
    int best = -1, best_d = CAMP_REACH_PX * CAMP_REACH_PX;
    for (int i = 0; i < CAMP_PROP_COUNT; i++) {
        int dx = px - s_props[i].x;
        int dy = py - (s_props[i].y - 4);
        int d = dx * dx + GROUND_DY2(dy);
        if (d < best_d) { best_d = d; best = i; }
    }
    return best;
}

// Stylus tap on a prop: the touch is on the bottom screen, whose view starts at world row CAMP_CAM_Y.
static int prop_hit(int i, int tx, int ty) {
    const CampProp *p = &s_props[i];
    int left = p->x - p->w / 2;
    int top = p->y - p->h;
    int wx = tx, wy = ty + CAMP_CAM_Y;
    return wx >= left && wx < left + p->w && wy >= top && wy < p->y;
}

int camp_update(Player *p, uint32_t keys_held, uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    s_anim++;
    if (s_toast_frames > 0) s_toast_frames--;

    // Walk (d-pad only; the stylus is for touching props). Same speed and 8-direction diagonal
    // normalisation as the dungeon so the hero feels identical.
    fixed speed = g_characters[CHAR_HERO].speed;
    int sdx = ((keys_held & KEY_RIGHT) ? 1 : 0) - ((keys_held & KEY_LEFT) ? 1 : 0);
    int sdy = ((keys_held & KEY_DOWN) ? 1 : 0) - ((keys_held & KEY_UP) ? 1 : 0);
    if (sdx != 0 || sdy != 0) {
        if (sdy > 0 && sdx == 0) p->dir = DIR_SOUTH;
        else if (sdy > 0 && sdx < 0) p->dir = DIR_SOUTHWEST;
        else if (sdy == 0 && sdx < 0) p->dir = DIR_WEST;
        else if (sdy < 0 && sdx < 0) p->dir = DIR_NORTHWEST;
        else if (sdy < 0 && sdx == 0) p->dir = DIR_NORTH;
        else if (sdy < 0 && sdx > 0) p->dir = DIR_NORTHEAST;
        else if (sdy == 0 && sdx > 0) p->dir = DIR_EAST;
        else p->dir = DIR_SOUTHEAST;

        fixed vx = sdx * speed;
        fixed vy = sdy * speed;
        if (sdx != 0 && sdy != 0) { vx = (vx * 181) >> 8; vy = (vy * 181) >> 8; }
        vy >>= GROUND_Y_SHIFT;

        int moved = 0;
        fixed nx = p->x, ny = p->y;
        if (sweep_position(&nx, &ny, vx, vy)) {
            moved = nx != p->x || ny != p->y;
        } else {
            nx = p->x; ny = p->y;
            if (sweep_position(&nx, &ny, vx, 0)) moved = nx != p->x;
            else {
                nx = p->x; ny = p->y;
                if (sweep_position(&nx, &ny, 0, vy)) moved = ny != p->y;
            }
        }
        if (moved) { p->x = nx; p->y = ny; }
        p->is_moving = moved;
        if (moved) {
            if (++p->anim_timer >= g_characters[CHAR_HERO].anim_period) {
                p->anim_timer = 0;
                p->frame = (p->frame + 1) % PLAYER_NUM_FRAMES;
            }
        } else {
            p->frame = 0;
            p->anim_timer = 0;
        }
    } else {
        p->is_moving = 0;
        p->frame = 0;
        p->anim_timer = 0;
    }
    p->char_id = CHAR_HERO;

    // Focus: the nearest prop within reach shows its name.
    s_focus = prop_focus(p);

    // Interaction: A next to the focused prop, or a stylus tap on its sprite (bottom screen only).
    int tapped = touch_pressed && touch_y >= 0 && touch_y < SCREEN_H;
    int act = CAMP_ACT_NONE;
    if (s_focus >= 0) {
        const CampProp *fp = &s_props[s_focus];
        int trigger = (keys_down & KEY_A) != 0;
        if (tapped && prop_hit(s_focus, touch_x, touch_y)) trigger = 1;
        if (trigger) act = fp->act;
    }
    return act;
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

// The bonfire (its flame is drawn on top of the hoguera sprite by draw_prop).
#define CAMP_BONFIRE_INDEX 4
// Flame root above the bonfire's ground point: the middle of the log pile.
#define CAMP_FLAME_ROOT_DY 9
// Flame animation: one frame every 3 ticks (20 fps), looping over CAMP_FUEGO_FRAMES.
#define CAMP_FLAME_TICKS 3

// Opaque-pixel blit of a baked RGB15 sprite (0 = transparent) at world (x, y) of the camp.
static void blit_marco(const uint16_t *pix, int w, int h, int x, int y, uint16_t *buffer, int cam_x, int cam_y,
                       int row0, int row1) {
    if (!pix) return;                    // NitroFS read failed: the frame is simply not drawn
    if (row0 < 0) row0 = 0;
    if (row1 > h) row1 = h;
    for (int row = row0; row < row1; row++) {
        int sy = y + row - cam_y;
        if ((unsigned)sy >= SCREEN_H) continue;
        const uint16_t *srow = pix + row * w;
        uint16_t *drow = buffer + sy * SCREEN_W;
        int min_x = SCREEN_W, max_x = -1;
        for (int col = 0; col < w; col++) {
            uint16_t c = srow[col];
            if (!c) continue;
            int sx = x + col - cam_x;
            if ((unsigned)sx >= SCREEN_W) continue;
            drow[sx] = c;
            if (sx < min_x) min_x = sx;
            if (sx > max_x) max_x = sx;
        }
        if (max_x >= min_x) dirty_row(sy, min_x, max_x + 1);
    }
}

// The bonfire's light on the floor is baked into the camp floor (tools/camp/bake_camp_arena.py). This hook,
// called right after the floor and before shadows and actors, draws the wall frame (north wall with the gate,
// side walls, buttresses: tools/camp/marco_build.py), so heroes and props always paint over it.
void camp_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    blit_marco(s_marco_n, CAMP_ROOM_W, CAMP_MARCO_NORTH_H, 0, 0, buffer, cam_x, cam_y, 0, CAMP_MARCO_NORTH_H);
    blit_marco(s_marco_l, CAMP_MARCO_SIDE_W, CAMP_MARCO_SIDE_H, 0, CAMP_MARCO_SIDE_Y0, buffer, cam_x, cam_y,
               0, CAMP_MARCO_SIDE_H);
    blit_marco(s_marco_r, CAMP_MARCO_SIDE_W, CAMP_MARCO_SIDE_H, CAMP_ROOM_W - CAMP_MARCO_SIDE_W, CAMP_MARCO_SIDE_Y0,
               buffer, cam_x, cam_y, 0, CAMP_MARCO_SIDE_H);
}

// Ground shadows of props next to a side wall are drawn after the frame and would stain it: repaint only the
// rows of the wall that such a shadow covers (a few dozen rows, at the end of the frame).
static void repaint_marco_under_shadows(uint16_t *buffer, int cam_x, int cam_y) {
    for (int i = 0; i < CAMP_PROP_COUNT; i++) {
        const CampProp *p = &s_props[i];
        if (!p->shadow) continue;
        int left = p->x - p->w / 2 + p->shox;
        int top = p->y - p->h + p->shoy - CAMP_MARCO_SIDE_Y0;
        if (left < CAMP_MARCO_SIDE_W)
            blit_marco(s_marco_l, CAMP_MARCO_SIDE_W, CAMP_MARCO_SIDE_H, 0, CAMP_MARCO_SIDE_Y0, buffer, cam_x, cam_y,
                       top, top + p->shh);
        if (left + p->shw > CAMP_ROOM_W - CAMP_MARCO_SIDE_W)
            blit_marco(s_marco_r, CAMP_MARCO_SIDE_W, CAMP_MARCO_SIDE_H, CAMP_ROOM_W - CAMP_MARCO_SIDE_W,
                       CAMP_MARCO_SIDE_Y0, buffer, cam_x, cam_y, top, top + p->shh);
    }
}

static void draw_prop(int index, uint16_t *buffer, int cam_x, int cam_y) {
    const CampProp *p = &s_props[index];
    if (!p->pix) return;                 // NitroFS read failed: the prop is simply not drawn
    int left = p->x - p->w / 2 - cam_x;
    int top = p->y - p->h - cam_y;
    for (int y = 0; y < p->h; y++) {
        int sy = top + y;
        if ((unsigned)sy >= SCREEN_H) continue;
        const uint16_t *srow = p->pix + y * p->w;
        uint16_t *drow = buffer + sy * SCREEN_W;
        int min_x = SCREEN_W, max_x = -1;
        for (int x = 0; x < p->w; x++) {
            uint16_t c = srow[x];
            if (!c) continue;
            int sx = left + x;
            if ((unsigned)sx >= SCREEN_W) continue;
            drow[sx] = c;
            if (sx < min_x) min_x = sx;
            if (sx > max_x) max_x = sx;
        }
        if (max_x >= min_x) dirty_row(sy, min_x, max_x + 1);
    }
    // The bonfire wears its precalculated flame strip (muted FX_SH_* ramp), frame picked by s_anim.
    if (index == CAMP_BONFIRE_INDEX && s_fire) {
        const uint16_t *frame = s_fire + ((s_anim / CAMP_FLAME_TICKS) % CAMP_FUEGO_FRAMES) * CAMP_FUEGO_W * CAMP_FUEGO_H;
        int fleft = p->x - cam_x - CAMP_FUEGO_BASE_X;
        int ftop = p->y - cam_y - CAMP_FLAME_ROOT_DY - (CAMP_FUEGO_H - 1);
        for (int y = 0; y < CAMP_FUEGO_H; y++) {
            int sy = ftop + y;
            if ((unsigned)sy >= SCREEN_H) continue;
            const uint16_t *srow = frame + y * CAMP_FUEGO_W;
            uint16_t *drow = buffer + sy * SCREEN_W;
            int min_x = SCREEN_W, max_x = -1;
            for (int x = 0; x < CAMP_FUEGO_W; x++) {
                uint16_t c = srow[x];
                if (!c) continue;
                int sx = fleft + x;
                if ((unsigned)sx >= SCREEN_W) continue;
                drow[sx] = c;
                if (sx < min_x) min_x = sx;
                if (sx > max_x) max_x = sx;
            }
            if (max_x >= min_x) dirty_row(sy, min_x, max_x + 1);
        }
    }
}

int camp_items_count(int cam_x, int cam_y) {
    (void)cam_x;
    s_vis_n = 0;
    for (int i = 0; i < CAMP_PROP_COUNT; i++) {
        const CampProp *p = &s_props[i];
        int top = p->y - p->h, bot = p->y;
        if (bot <= cam_y || top >= cam_y + SCREEN_H) continue;
        s_vis[s_vis_n++] = i;
    }
    return s_vis_n;
}

int camp_item_depth(int index) {
    if (index < 0 || index >= s_vis_n) return 0;
    return s_props[s_vis[index]].y;
}

void camp_item_draw(int index, uint16_t *buffer, int cam_x, int cam_y, int depth) {
    (void)depth;
    if (index < 0 || index >= s_vis_n) return;
    draw_prop(s_vis[index], buffer, cam_x, cam_y);
}

int camp_item_shadow(int index, const uint8_t **mask, uint8_t *bounds, int *left, int *top) {
    if (index < 0 || index >= s_vis_n) return 0;
    const CampProp *p = &s_props[s_vis[index]];
    if (!p->shadow) return 0;
    *mask = p->shadow;
    bounds[0] = 0;
    bounds[1] = 0;
    bounds[2] = (uint8_t)p->shw;
    bounds[3] = (uint8_t)p->shh;
    *left = p->x - p->w / 2 + p->shox;
    *top = p->y - p->h + p->shoy;
    return 1;
}

static void draw_centered(uint16_t *buffer, int cx, int y, const char *s, uint16_t ink) {
    int w = bestiary_font_measure_utf8(s);
    int x = cx - w / 2;
    for (int row = 0; row < bestiary_font_line_height() + 1; row++) dirty_row(y + row, x, x + w + 2);
    bestiary_font_draw_utf8(buffer, x + 1, y + 1, s, COL_INK_SH);
    bestiary_font_draw_utf8(buffer, x, y, s, ink);
}

void camp_render_overlay(uint16_t *buffer, int cam_x, int cam_y) {
    repaint_marco_under_shadows(buffer, cam_x, cam_y);
    // The short message of the last action (e.g. what sleeping did), on the bottom screen.
    if (s_toast_frames > 0 && s_toast[0] && cam_y >= CAMP_CAM_Y)
        draw_centered(buffer, SCREEN_W / 2, 150, s_toast, COL_GOLD);
}

#endif // CAMP_SCENE
