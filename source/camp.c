#include "camp.h"
#if CAMP_SCENE

#include "arena.h"
#include "collision.h"
#include "player_sprite.h"
#include "camp_props_gfx.h"
#include "camp_arena_data.h"
#include "bestiary_font.h"
#include <stddef.h>
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

// Warm, muted FX_SH_*-style colours for the bonfire glow and flame (never pure primaries).
#define COL_EMBER   (RGB15(20, 9, 5) | BIT(15))
#define COL_AMBER   (RGB15(24, 15, 7) | BIT(15))
#define COL_GOLD    (RGB15(27, 20, 11) | BIT(15))
#define COL_IVORY   (RGB15(29, 25, 19) | BIT(15))
#define COL_INK     (RGB15(29, 25, 19) | BIT(15))
#define COL_INK_SH  (RGB15(1, 1, 2) | BIT(15))

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
static const CampProp s_props[] = {
    { g_camp_puerta,  CAMP_PUERTA_W,  CAMP_PUERTA_H,   128, 104, "Puerta",       CAMP_ACT_DOOR,
      g_camp_puerta_shadow,  CAMP_PUERTA_SHADOW_W,  CAMP_PUERTA_SHADOW_H,
      CAMP_PUERTA_SHADOW_OX,  CAMP_PUERTA_SHADOW_OY  },
    { g_camp_mesa,    CAMP_MESA_W,    CAMP_MESA_H,      60, 250, "Mesa",         CAMP_ACT_NONE,
      g_camp_mesa_shadow,    CAMP_MESA_SHADOW_W,    CAMP_MESA_SHADOW_H,
      CAMP_MESA_SHADOW_OX,    CAMP_MESA_SHADOW_OY    },
    { g_camp_arcon,   CAMP_ARCON_W,   CAMP_ARCON_H,     58, 292, "ArcÃ³n",        CAMP_ACT_INVENTORY,
      g_camp_arcon_shadow,   CAMP_ARCON_SHADOW_W,   CAMP_ARCON_SHADOW_H,
      CAMP_ARCON_SHADOW_OX,   CAMP_ARCON_SHADOW_OY   },
    { g_camp_atril,   CAMP_ATRIL_W,   CAMP_ATRIL_H,    198, 296, "Atril",        CAMP_ACT_CODEX,
      g_camp_atril_shadow,   CAMP_ATRIL_SHADOW_W,   CAMP_ATRIL_SHADOW_H,
      CAMP_ATRIL_SHADOW_OX,   CAMP_ATRIL_SHADOW_OY   },
    { g_camp_hoguera, CAMP_HOGUERA_W, CAMP_HOGUERA_H,  112, 312, "Hoguera",      CAMP_ACT_NONE,
      g_camp_hoguera_shadow, CAMP_HOGUERA_SHADOW_W, CAMP_HOGUERA_SHADOW_H,
      CAMP_HOGUERA_SHADOW_OX, CAMP_HOGUERA_SHADOW_OY },
    { g_camp_jergon,  CAMP_JERGON_W,  CAMP_JERGON_H,   158, 320, "JergÃ³n",       CAMP_ACT_SLEEP,
      g_camp_jergon_shadow,  CAMP_JERGON_SHADOW_W,  CAMP_JERGON_SHADOW_H,
      CAMP_JERGON_SHADOW_OX,  CAMP_JERGON_SHADOW_OY  },
};
#define CAMP_PROP_COUNT ((int)(sizeof(s_props) / sizeof(s_props[0])))

static Arena s_camp_arena;
static uint8_t s_camp_collision[(CAMP_COLL_W * CAMP_COLL_H) / 4];
static uint32_t s_camp_occ_rows[CAMP_ROOM_H + 1];
static int s_built = 0;
static int s_active = 0;
static int s_focus = -1;             // prop the hero is next to (-1 none)
static char s_toast[48];
static int s_toast_frames = 0;
static int s_anim = 0;

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

static void build_arena(void) {
    memset(s_camp_collision, 0, sizeof(s_camp_collision));
    // Walls: the 24 px of cathedral wall each side, a thin far edge at the very top (behind the door)
    // and the foot. The hero can walk right up to the door and under it.
    block_rect(0, 0, 24, CAMP_ROOM_H, 3);
    block_rect(CAMP_ROOM_W - 24, 0, 24, CAMP_ROOM_H, 3);
    block_rect(0, 0, CAMP_ROOM_W, 44, 3);
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
    s_camp_arena.num_tiles = CAMP_NUM_TILES;
    s_camp_arena.player_x = CAMP_START_X;
    s_camp_arena.player_y = CAMP_START_Y;
    s_camp_arena.num_enemies = 0;
    s_camp_arena.collision = s_camp_collision;
    s_camp_arena.palette = g_camp_palette;
    s_camp_arena.tiles = g_camp_tiles;
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

// The bonfire (single source of truth for its glow and its procedural flame).
#define CAMP_BONFIRE_INDEX 4
// Warm, dim pool of light on the floor under the bonfire, dithered so the stone still shows through.
void camp_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    const CampProp *f = &s_props[CAMP_BONFIRE_INDEX];
    int cx = f->x - cam_x;
    int cy = f->y - 8 - cam_y;
    // The actor page is transparent over the hardware floor, so painting a filled disc would read as
    // a rug. Instead scatter a few warm embers on the stone: sparse, dimmer towards the edge.
    const int rx = 36, ry = 15;
    for (int dy = -ry; dy <= ry; dy++) {
        int sy = cy + dy;
        if ((unsigned)sy >= SCREEN_H) continue;
        for (int dx = -rx; dx <= rx; dx++) {
            int q = (dx * dx * 100) / (rx * rx) + (dy * dy * 100) / (ry * ry);
            if (q > 100) continue;
            int sx = cx + dx;
            if ((unsigned)sx >= SCREEN_W) continue;
            // Sparse: the inner embers denser than the outer ones; a scattered 2-of-3 pattern.
            int keep = q < 45 ? 2 : 1;
            if (((sx * 7 + sy * 13) & 3) >= keep) continue;
            uint16_t c = q < 45 ? COL_EMBER : (q < 75 ? COL_GOLD : COL_AMBER);
            buffer[sy * SCREEN_W + sx] = c;
            dirty_row(sy, sx, sx + 1);
        }
    }
}

static void draw_prop(int index, uint16_t *buffer, int cam_x, int cam_y) {
    const CampProp *p = &s_props[index];
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
    // The bonfire wears a small animated flame and flicker (procedural, muted FX_SH_* colours).
    if (index == CAMP_BONFIRE_INDEX) {
        int fx = p->x - cam_x;
        int base = p->y - cam_y - 6;
        int sway = ((s_anim >> 2) & 3) - 1;
        for (int j = 0; j < 9; j++) {
            int sy = base - j;
            if ((unsigned)sy >= SCREEN_H) continue;
            int off = (j >= 6) ? (sway * (j - 5)) / 3 : 0;
            int sx = fx + off;
            uint16_t c = j < 2 ? COL_IVORY : j < 5 ? COL_GOLD : j < 7 ? COL_AMBER : COL_EMBER;
            int half = j < 5 ? 1 : 0;
            for (int k = -half; k <= half; k++) {
                int px = sx + k;
                if ((unsigned)px >= SCREEN_W) continue;
                buffer[sy * SCREEN_W + px] = c;
                dirty_row(sy, px, px + 1);
            }
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
    // The focused prop's name, above it, on the screen that shows the prop (top or bottom).
    if (s_focus >= 0) {
        const CampProp *p = &s_props[s_focus];
        int sx = p->x - cam_x;
        int sy = p->y - p->h - cam_y - 14;
        if (sy >= 0 && sy < SCREEN_H - 14) draw_centered(buffer, sx, sy, p->name, COL_IVORY);
    }
    // The short message of the last action (e.g. what sleeping did), on the bottom screen.
    if (s_toast_frames > 0 && s_toast[0] && cam_y >= CAMP_CAM_Y)
        draw_centered(buffer, SCREEN_W / 2, 150, s_toast, COL_GOLD);
}

#endif // CAMP_SCENE
