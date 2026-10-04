#include "game.h"
#include "dungeon_data.h"
#include "player_sprite.h"

// Backbuffer in main RAM for double buffering bottom screen (15-bit direct color FB)
static uint16_t s_backbuffer[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));
static int s_active_vram_bank = 0; // 0 = showing A (draw to B), 1 = showing B (draw to A)

static Player s_player;

// Check collision with solid tiles
static int is_tile_solid(int pixel_x, int pixel_y) {
    if (pixel_x < 0 || pixel_x >= SCREEN_W || pixel_y < 0 || pixel_y >= SCREEN_H) {
        return 1;
    }
    int col = pixel_x / TILE_W;
    int row = pixel_y / TILE_H;
    if (col < 0 || col >= MAP_COLS || row < 0 || row >= MAP_ROWS) {
        return 1;
    }
    return g_dungeon_collision[row][col];
}

// Check player hitbox (radius ~10 px around center feet)
static int can_move_to(fixed fx, fixed fy) {
    int px = TO_INT(fx);
    int py = TO_INT(fy);
    int r = 8;
    if (is_tile_solid(px - r, py - r)) return 0;
    if (is_tile_solid(px + r, py - r)) return 0;
    if (is_tile_solid(px - r, py + r)) return 0;
    if (is_tile_solid(px + r, py + r)) return 0;
    return 1;
}

// Render the 16x12 dungeon tilemap into the backbuffer
static void render_dungeon_map(void) {
    for (int r = 0; r < MAP_ROWS; r++) {
        for (int c = 0; c < MAP_COLS; c++) {
            uint8_t tile_idx = g_dungeon_map[r][c];
            const uint16_t *tile_pixels = g_dungeon_tiles[tile_idx];
            int dest_x = c * TILE_W;
            int dest_y = r * TILE_H;

            for (int ty = 0; ty < TILE_H; ty++) {
                uint16_t *dst_row = &s_backbuffer[(dest_y + ty) * SCREEN_W + dest_x];
                const uint16_t *src_row = &tile_pixels[ty * TILE_W];
                memcpy(dst_row, src_row, TILE_W * sizeof(uint16_t));
            }
        }
    }
}

// Render player sprite with transparency & ground shadow
static void render_player_sprite(void) {
    int px = TO_INT(s_player.x);
    int py = TO_INT(s_player.y);

    // Sprite top-left relative to feet center (cx = px, cy = py - 18)
    int start_x = px - (PLAYER_SPRITE_W / 2);
    int start_y = py - (PLAYER_SPRITE_H / 2) - 8;

    // 1. Draw subtle ground shadow under feet
    int shadow_cx = px;
    int shadow_cy = py + 16;
    for (int dy = -4; dy <= 4; dy++) {
        int sy = shadow_cy + dy;
        if (sy < 0 || sy >= SCREEN_H) continue;
        int rx = 12 - (dy * dy);
        if (rx <= 0) continue;
        for (int dx = -rx; dx <= rx; dx++) {
            int sx = shadow_cx + dx;
            if (sx < 0 || sx >= SCREEN_W) continue;
            // Darken existing pixel
            uint16_t col = s_backbuffer[sy * SCREEN_W + sx];
            int r = (col & 0x1F) >> 1;
            int g = ((col >> 5) & 0x1F) >> 1;
            int b = ((col >> 10) & 0x1F) >> 1;
            s_backbuffer[sy * SCREEN_W + sx] = r | (g << 5) | (b << 10) | 0x8000;
        }
    }

    // 2. Draw 64x64 frame pixels
    const uint16_t *frame_pixels = g_player_frames[s_player.dir][s_player.frame];

    for (int sy = 0; sy < PLAYER_SPRITE_H; sy++) {
        int dy = start_y + sy;
        if (dy < 0 || dy >= SCREEN_H) continue;

        uint16_t *dst_row = &s_backbuffer[dy * SCREEN_W];
        const uint16_t *src_row = &frame_pixels[sy * PLAYER_SPRITE_W];

        for (int sx = 0; sx < PLAYER_SPRITE_W; sx++) {
            int dx = start_x + sx;
            if (dx < 0 || dx >= SCREEN_W) continue;

            uint16_t pixel = src_row[sx];
            // If non-transparent (bit 15 set)
            if (pixel & 0x8000) {
                dst_row[dx] = pixel;
            }
        }
    }
}

// Present backbuffer to VRAM and flip hardware banks
static void present_frame(void) {
    u16 *dest_vram = (s_active_vram_bank == 0) ? (u16 *)VRAM_B : (u16 *)VRAM_A;
    dmaCopy(s_backbuffer, dest_vram, sizeof(s_backbuffer));

    swiWaitForVBlank();

    if (s_active_vram_bank == 0) {
        videoSetMode(MODE_FB1); // Display VRAM_B
        s_active_vram_bank = 1;
    } else {
        videoSetMode(MODE_FB0); // Display VRAM_A
        s_active_vram_bank = 0;
    }
}

static void player_init(void) {
    // Start at center of room
    s_player.x = TO_FIXED(128);
    s_player.y = TO_FIXED(96);
    s_player.vx = 0;
    s_player.vy = 0;
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
}

static void player_update(uint32_t keys_held) {
    fixed speed = TO_FIXED(1); // 1 pixel per frame
    fixed diag_speed = TO_FIXED(1) * 181 / 256; // 0.707 in 8.8 fixed

    int dx = 0;
    int dy = 0;

    if (keys_held & KEY_UP)    dy -= 1;
    if (keys_held & KEY_DOWN)  dy += 1;
    if (keys_held & KEY_LEFT)  dx -= 1;
    if (keys_held & KEY_RIGHT) dx += 1;

    if (dx != 0 || dy != 0) {
        s_player.is_moving = 1;

        // Determine 8-way direction
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

        // Try movement with axis sliding
        if (can_move_to(s_player.x + move_x, s_player.y + move_y)) {
            s_player.x += move_x;
            s_player.y += move_y;
        } else if (can_move_to(s_player.x + move_x, s_player.y)) {
            s_player.x += move_x;
        } else if (can_move_to(s_player.x, s_player.y + move_y)) {
            s_player.y += move_y;
        }

        // Cycle animation frames (every 5 ticks ~ 12 fps)
        s_player.anim_timer++;
        if (s_player.anim_timer >= 5) {
            s_player.anim_timer = 0;
            s_player.frame = (s_player.frame + 1) % PLAYER_NUM_FRAMES;
        }
    } else {
        s_player.is_moving = 0;
        s_player.frame = 0; // Return to idle pose
        s_player.anim_timer = 0;
    }
}

int main(void) {
    // 1. Configure Main Engine for Direct VRAM Framebuffer Mode
    vramSetBankA(VRAM_A_LCD);
    vramSetBankB(VRAM_B_LCD);
    videoSetMode(MODE_FB0); // Start displaying VRAM_A

    // 2. Configure Sub Engine for top screen status console
    videoSetModeSub(MODE_0_2D);
    vramSetBankC(VRAM_C_SUB_BG);
    consoleInit(NULL, 0, BgType_Text4bpp, BgSize_T_256x256, 31, 0, false, true);

    printf("\x1b[1;1H=== DUNGEON DS ===\n");
    printf("\x1b[2;1HModulo: Ruinas Goticas\n");
    printf("\x1b[3;1HMotor: 8-Dir Pre-render 2D\n");
    printf("\x1b[5;1H[D-Pad]: Mover Personaje\n");
    printf("\x1b[6;1HColisiones: Activas (Muros)\n");
    printf("\x1b[8;1HTiles: Dreadhollow 3D Baked\n");
    printf("\x1b[9;1HMonster: Mixamo Skeletal\n");

    player_init();

    while (1) {
        scanKeys();
        uint32_t keys_held = keysHeld();

        player_update(keys_held);

        // Update Top HUD coordinates
        printf("\x1b[12;1HPos: (%3d, %3d)  Dir: %d\n", TO_INT(s_player.x), TO_INT(s_player.y), s_player.dir);
        printf("\x1b[13;1HEstado: %s (Frame %d)\n", s_player.is_moving ? "CAMINANDO " : "EN ESPERA ", s_player.frame);

        // Draw scene
        render_dungeon_map();
        render_player_sprite();

        // Push to display
        present_frame();
    }

    return 0;
}
