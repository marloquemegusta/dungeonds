#include "game.h"
#include "dungeon_data.h"
#include "player_sprite.h"

// Dual Screen Continuous World Buffers:
// Top screen: displays world Y in [camera_y - SCREEN_H, camera_y)
// Bottom screen: displays world Y in [camera_y, camera_y + SCREEN_H)
static uint16_t s_bot_backbuffer[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));
static uint16_t s_top_backbuffer[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));

static u16 *s_top_vram = NULL;
static int s_top_bg = 0;
static int s_active_vram_bank = 0;

static Player s_player;
static int s_camera_x = 0;
static int s_camera_y = 0;

typedef struct {
    int y;        // Baseline Y for depth sorting
    int is_player;
    int prop_idx;
} DepthItem;

static int is_point_solid(int px, int py) {
    // Check dungeon hall perimeter
    if (px < 80 || px > 432 || py < 64 || py > 448) {
        return 1;
    }
    // Check pillars and obstacles
    for (int i = 0; i < g_dungeon_prop_count; i++) {
        const DungeonProp *p = &g_dungeon_props[i];
        int dx = px - p->x;
        int dy = py - p->y;
        int r = p->solid_r;
        if (dx * dx + dy * dy <= r * r) {
            return 1;
        }
    }
    return 0;
}

static int can_move_to(fixed fx, fixed fy) {
    int px = TO_INT(fx);
    int py = TO_INT(fy);
    int r = 8;
    if (is_point_solid(px - r, py - r)) return 0;
    if (is_point_solid(px + r, py - r)) return 0;
    if (is_point_solid(px - r, py + r)) return 0;
    if (is_point_solid(px + r, py + r)) return 0;
    return 1;
}

// Render floor tiles (32x16) for a given screen viewport
static void render_screen_floor(uint16_t *buffer, int cam_x, int cam_y) {
    int start_col = cam_x / FLOOR_TILE_W;
    int end_col = (cam_x + SCREEN_W) / FLOOR_TILE_W + 1;
    int start_row = cam_y / FLOOR_TILE_H;
    int end_row = (cam_y + SCREEN_H) / FLOOR_TILE_H + 1;

    if (start_col < 0) start_col = 0;
    if (end_col > WORLD_COLS) end_col = WORLD_COLS;
    if (start_row < 0) start_row = 0;
    if (end_row > WORLD_ROWS) end_row = WORLD_ROWS;

    // Void background color outside hall
    for (int i = 0; i < SCREEN_W * SCREEN_H; i++) {
        buffer[i] = RGB15(1, 1, 2) | BIT(15);
    }

    for (int r = start_row; r < end_row; r++) {
        for (int c = start_col; c < end_col; c++) {
            uint8_t tile_idx = g_world_floor_map[r][c];
            const uint16_t *tile_pixels = g_floor_tiles[tile_idx];

            int screen_tile_x = (c * FLOOR_TILE_W) - cam_x;
            int screen_tile_y = (r * FLOOR_TILE_H) - cam_y;

            for (int ty = 0; ty < FLOOR_TILE_H; ty++) {
                int dy = screen_tile_y + ty;
                if (dy < 0 || dy >= SCREEN_H) continue;

                uint16_t *dst_row = &buffer[dy * SCREEN_W];
                const uint16_t *src_row = &tile_pixels[ty * FLOOR_TILE_W];

                for (int tx = 0; tx < FLOOR_TILE_W; tx++) {
                    int dx = screen_tile_x + tx;
                    if (dx < 0 || dx >= SCREEN_W) continue;
                    uint16_t col = src_row[tx];
                    if (col & BIT(15)) {
                        dst_row[dx] = col;
                    }
                }
            }
        }
    }
}

// Draw wall/prop sprite with transparency
static void draw_prop_to_screen(uint16_t *buffer, int prop_idx, int cam_x, int cam_y) {
    const DungeonProp *p = &g_dungeon_props[prop_idx];
    const uint16_t *src_pixels = g_wall_sprites[p->type];

    // Bottom center of 32x48 sprite rests at (p->x, p->y)
    int start_x = (p->x - (WALL_SPRITE_W / 2)) - cam_x;
    int start_y = (p->y - (WALL_SPRITE_H - 6)) - cam_y;

    for (int sy = 0; sy < WALL_SPRITE_H; sy++) {
        int dy = start_y + sy;
        if (dy < 0 || dy >= SCREEN_H) continue;

        uint16_t *dst_row = &buffer[dy * SCREEN_W];
        const uint16_t *src_row = &src_pixels[sy * WALL_SPRITE_W];

        for (int sx = 0; sx < WALL_SPRITE_W; sx++) {
            int dx = start_x + sx;
            if (dx < 0 || dx >= SCREEN_W) continue;

            uint16_t col = src_row[sx];
            if (col & BIT(15)) {
                dst_row[dx] = col;
            }
        }
    }
}

// Draw player sprite
static void draw_player_to_screen(uint16_t *buffer, int cam_x, int cam_y) {
    int px = TO_INT(s_player.x);
    int py = TO_INT(s_player.y);

    int start_x = (px - (PLAYER_SPRITE_W / 2)) - cam_x;
    int start_y = (py - (PLAYER_SPRITE_H / 2) - 8) - cam_y;

    // Elliptical ground shadow under feet
    int shadow_cx = px - cam_x;
    int shadow_cy = (py + 16) - cam_y;
    for (int dy = -4; dy <= 4; dy++) {
        int sy = shadow_cy + dy;
        if (sy < 0 || sy >= SCREEN_H) continue;
        int rx = 14 - (dy * dy);
        if (rx <= 0) continue;
        for (int dx = -rx; dx <= rx; dx++) {
            int sx = shadow_cx + dx;
            if (sx < 0 || sx >= SCREEN_W) continue;
            uint16_t col = buffer[sy * SCREEN_W + sx];
            int r = (col & 0x1F) >> 1;
            int g = ((col >> 5) & 0x1F) >> 1;
            int b = ((col >> 10) & 0x1F) >> 1;
            buffer[sy * SCREEN_W + sx] = r | (g << 5) | (b << 10) | BIT(15);
        }
    }

    // Blit player 64x64 frame
    const uint16_t *frame_pixels = g_player_frames[s_player.dir][s_player.frame];
    for (int sy = 0; sy < PLAYER_SPRITE_H; sy++) {
        int dy = start_y + sy;
        if (dy < 0 || dy >= SCREEN_H) continue;

        uint16_t *dst_row = &buffer[dy * SCREEN_W];
        const uint16_t *src_row = &frame_pixels[sy * PLAYER_SPRITE_W];

        for (int sx = 0; sx < PLAYER_SPRITE_W; sx++) {
            int dx = start_x + sx;
            if (dx < 0 || dx >= SCREEN_W) continue;
            uint16_t pixel = src_row[sx];
            if (pixel & BIT(15)) {
                dst_row[dx] = pixel;
            }
        }
    }
}

// Render complete screen with back-to-front Y-Sorting (Diablo Occlusion)
static void render_screen_scene(uint16_t *buffer, int cam_x, int cam_y) {
    render_screen_floor(buffer, cam_x, cam_y);

    DepthItem items[MAX_DUNGEON_PROPS + 1];
    int count = 0;

    int screen_top = cam_y - 20;
    int screen_bot = cam_y + SCREEN_H + 48;

    for (int i = 0; i < g_dungeon_prop_count; i++) {
        int py = g_dungeon_props[i].y;
        if (py >= screen_top && py <= screen_bot) {
            items[count].y = py;
            items[count].is_player = 0;
            items[count].prop_idx = i;
            count++;
        }
    }

    int player_y = TO_INT(s_player.y);
    if (player_y >= screen_top && player_y <= screen_bot) {
        items[count].y = player_y;
        items[count].is_player = 1;
        items[count].prop_idx = -1;
        count++;
    }

    // Insertion sort by Y baseline
    for (int i = 1; i < count; i++) {
        DepthItem key = items[i];
        int j = i - 1;
        while (j >= 0 && items[j].y > key.y) {
            items[j + 1] = items[j];
            j--;
        }
        items[j + 1] = key;
    }

    // Render sorted: elements with lower Y drawn first, higher Y (in front) drawn on top
    for (int i = 0; i < count; i++) {
        if (items[i].is_player) {
            draw_player_to_screen(buffer, cam_x, cam_y);
        } else {
            draw_prop_to_screen(buffer, items[i].prop_idx, cam_x, cam_y);
        }
    }
}

static void present_both_screens(void) {
    // 1. Top screen direct color refresh
    DC_FlushRange(s_top_backbuffer, sizeof(s_top_backbuffer));
    dmaCopyWords(1, s_top_backbuffer, s_top_vram, sizeof(s_top_backbuffer));

    // 2. Bottom screen double buffer flip
    u16 *dest_vram = (s_active_vram_bank == 0) ? (u16 *)VRAM_B : (u16 *)VRAM_A;
    DC_FlushRange(s_bot_backbuffer, sizeof(s_bot_backbuffer));
    dmaCopyWords(2, s_bot_backbuffer, dest_vram, sizeof(s_bot_backbuffer));

    swiWaitForVBlank();

    if (s_active_vram_bank == 0) {
        videoSetMode(MODE_FB1);
        s_active_vram_bank = 1;
    } else {
        videoSetMode(MODE_FB0);
        s_active_vram_bank = 0;
    }
}

static void player_init(void) {
    // Spawn player in center aisle of grand crypt
    s_player.x = TO_FIXED(256);
    s_player.y = TO_FIXED(280);
    s_player.vx = 0;
    s_player.vy = 0;
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
}

static void player_update(uint32_t keys_held) {
    fixed speed = TO_FIXED(1);
    fixed diag_speed = TO_FIXED(1) * 181 / 256;

    int dx = 0;
    int dy = 0;

    if (keys_held & KEY_UP)    dy -= 1;
    if (keys_held & KEY_DOWN)  dy += 1;
    if (keys_held & KEY_LEFT)  dx -= 1;
    if (keys_held & KEY_RIGHT) dx += 1;

    if (dx != 0 || dy != 0) {
        s_player.is_moving = 1;

        if (dx == 0 && dy > 0)       s_player.dir = DIR_SOUTH;
        else if (dx < 0 && dy > 0)  s_player.dir = DIR_SOUTHWEST;
        else if (dx < 0 && dy == 0) s_player.dir = DIR_WEST;
        else if (dx < 0 && dy < 0)  s_player.dir = DIR_NORTHWEST;
        else if (dx == 0 && dy < 0)  s_player.dir = DIR_NORTH;
        else if (dx > 0 && dy < 0)  s_player.dir = DIR_NORTHEAST;
        else if (dx > 0 && dy == 0) s_player.dir = DIR_EAST;
        else if (dx > 0 && dy > 0)  s_player.dir = DIR_SOUTHEAST;

        fixed move_x = 0;
        fixed move_y = 0;

        if (dx != 0 && dy != 0) {
            move_x = (dx > 0) ? diag_speed : -diag_speed;
            move_y = (dy > 0) ? diag_speed : -diag_speed;
        } else {
            move_x = (dx > 0) ? speed : (dx < 0 ? -speed : 0);
            move_y = (dy > 0) ? speed : (dy < 0 ? -speed : 0);
        }

        // Sliding collision against hall perimeter and pillars
        if (can_move_to(s_player.x + move_x, s_player.y + move_y)) {
            s_player.x += move_x;
            s_player.y += move_y;
        } else if (can_move_to(s_player.x + move_x, s_player.y)) {
            s_player.x += move_x;
        } else if (can_move_to(s_player.x, s_player.y + move_y)) {
            s_player.y += move_y;
        }

        s_player.anim_timer++;
        if (s_player.anim_timer >= 5) {
            s_player.anim_timer = 0;
            s_player.frame = (s_player.frame + 1) % PLAYER_NUM_FRAMES;
        }
    } else {
        s_player.is_moving = 0;
        s_player.frame = 0;
        s_player.anim_timer = 0;
    }

    // Camera follow centering the player
    int target_cam_x = TO_INT(s_player.x) - (SCREEN_W / 2);
    int target_cam_y = TO_INT(s_player.y) - (SCREEN_H / 2);

    if (target_cam_x < 0) target_cam_x = 0;
    if (target_cam_x > WORLD_W - SCREEN_W) target_cam_x = WORLD_W - SCREEN_W;
    if (target_cam_y < SCREEN_H) target_cam_y = SCREEN_H;
    if (target_cam_y > WORLD_H - SCREEN_H) target_cam_y = WORLD_H - SCREEN_H;

    s_camera_x = target_cam_x;
    s_camera_y = target_cam_y;
}

int main(void) {
    // Bottom Screen: Direct VRAM Framebuffer Mode (Bank A & B)
    lcdMainOnBottom();
    vramSetBankA(VRAM_A_LCD);
    vramSetBankB(VRAM_B_LCD);
    videoSetMode(MODE_FB0);

    // Top Screen: Sub Engine Mode 5 Direct Color 16-bit BMP on VRAM C
    videoSetModeSub(MODE_5_2D);
    vramSetBankC(VRAM_C_SUB_BG);
    s_top_bg = bgInitSub(3, BgType_Bmp16, BgSize_B16_256x256, 0, 0);
    s_top_vram = (u16 *)bgGetGfxPtr(s_top_bg);

    player_init();

    while (1) {
        scanKeys();
        uint32_t keys_held = keysHeld();

        player_update(keys_held);

        // Continuous Dual Screen Rendering
        render_screen_scene(s_top_backbuffer, s_camera_x, s_camera_y - SCREEN_H);
        render_screen_scene(s_bot_backbuffer, s_camera_x, s_camera_y);

        present_both_screens();
    }

    return 0;
}
