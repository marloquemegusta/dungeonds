#include "godrays.h"

#if defined(GODRAYS_PROTO) && GODRAYS_PROTO

#include <nds.h>
#include "godrays_gfx.h"
#include "strip.h"
#include "tide.h"

#define GODRAY_OAM_LIMIT 128
#define GODRAY_PIECE_LIMIT 96
#define GODRAY_SCREEN 192
#define GODRAY_SLOT_COUNT 3

static uint32_t s_frame;
volatile uint32_t g_godray_debug[4];
static const uint8_t s_breath[32] = {
    12, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 16, 16,
    16, 16, 16, 16, 15, 15, 14, 14, 13, 13, 13, 12, 12, 12, 12, 12
};

static int floor_div(int value, int divisor) {
    int result = value / divisor;
    if (value < 0 && value % divisor) result--;
    return result;
}

static void setup_blend(int sub) {
    // OBJ is the first target. Main floor is BG1, sub floor is BG0;
    // BG2 is the actor bitmap on both engines.
    uint16_t targets = (uint16_t)(sub ? (BIT(0) | BIT(2)) : (BIT(1) | BIT(2))); // 2nd-target layer bits, shifted to 8-13 below
    vu16 *bldcnt = sub ? &REG_BLDCNT_SUB : &REG_BLDCNT;
    vu16 *bldalpha = sub ? &REG_BLDALPHA_SUB : &REG_BLDALPHA;
    vu16 *winin = sub ? &REG_WININ_SUB : &REG_WININ;
    vu16 *winout = sub ? &REG_WINOUT_SUB : &REG_WINOUT;
    *bldcnt = (uint16_t)(BIT(4) | (1 << 6) | (targets << 8));
    *bldalpha = (uint16_t)(s_breath[(s_frame >> 2) & 31] | (16 << 8));
    // Enable color effects in both windows; no WIN0 is active in the prototype.
    *winin = 0x003f;
    *winout = 0x003f;
}

static void load_engine(OamState *oam, uint8_t *tiles, uint16_t *palette) {
    oamInit(oam, SpriteMapping_1D_32, false);
    DC_FlushRange(g_godray_tiles, GODRAY_TILE_BYTES);
    DC_FlushRange(g_godray_palettes, sizeof(uint16_t) * 16 * (GODRAY_RAY_COUNT + 1));
    dmaCopy(g_godray_tiles, tiles, GODRAY_TILE_BYTES);
    dmaCopy(g_godray_palettes, palette, sizeof(uint16_t) * 16 * (GODRAY_RAY_COUNT + 1));
}

void godrays_init(void) {
    s_frame = 0;
    vramSetBankE(VRAM_E_MAIN_SPRITE);
    vramSetBankI(VRAM_I_SUB_SPRITE);
    load_engine(&oamMain, (uint8_t *)0x06400000, (uint16_t *)SPRITE_PALETTE);
    load_engine(&oamSub, (uint8_t *)0x06600000, (uint16_t *)SPRITE_PALETTE_SUB);
    oamEnable(&oamMain);
    oamEnable(&oamSub);
    REG_DISPCNT &= ~DISPLAY_WIN0_ON;
    REG_DISPCNT_SUB &= ~DISPLAY_WIN0_ON;
    setup_blend(0);
    setup_blend(1);
}

static void set_obj(OamState *oam, int id, int x, int y, int tile_offset,
                    uint8_t *gfx_base, int palette, SpriteSize size, int hflip, int semi) {
    int hidden = x <= -64 || x >= 256 || y <= -64 || y >= 192;
    oamSet(oam, id, x, y, 0, palette, size, SpriteColorFormat_16Color,
           (u16 *)(gfx_base + tile_offset), -1, false, hidden,
           hflip, false, false);
    if (!hidden && semi) oam->oamMemory[id].attribute[0] |= BIT(10);
}

static SpriteSize piece_size(const GodrayPiece *piece) {
    // Square cells from the converter (CHUNK in tools/godrays/convert_rays.py).
    if (piece->width == 16 && piece->height == 16) return SpriteSize_16x16;
    if (piece->width == 32 && piece->height == 32) return SpriteSize_32x32;
    return SpriteSize_64x64;
}

static void hide_remaining(OamState *oam, int first) {
    for (int id = first; id < GODRAY_OAM_LIMIT; id++)
        oam->oamMemory[id].attribute[0] = ATTR0_DISABLED;
}

// Integer hash of a screen index: stable side, height and ray per screen.
static uint32_t screen_hash(int screen) {
    uint32_t x = (uint32_t)screen;
    uint32_t h = x * 0x9E3779B1u;
    h ^= h >> 15;
    return h;
}

static int render_screen(OamState *oam, uint8_t *gfx_base, int camera_x,
                         int camera_y, int sub, int tide_visible) {
    int id = 0;
    // Physical world line A = camera_y - shift is invariant under a rebase
    // (shift and camera_y move together), so a ray at world y W is drawn at
    // ray_y = W - A = screen*GODRAY_SCREEN + off + shift - camera_y.
    int shift = (int)strip_shift_total_px();
    int A = camera_y - shift;
    int first_screen = floor_div(A, GODRAY_SCREEN) - 1;
    int dust_x[GODRAY_SLOT_COUNT];
    int dust_y[GODRAY_SLOT_COUNT];
    int dust_palette[GODRAY_SLOT_COUNT];
    int dust_count = 0;

    for (int slot = 0; slot < GODRAY_SLOT_COUNT && id < GODRAY_PIECE_LIMIT; slot++) {
        int screen = first_screen + slot;
        uint32_t h = screen_hash(screen);
        int hflip = (int)(h & 1u);
        int off = (int)((h >> 8) % 96u);
        int ray_y = screen * GODRAY_SCREEN + off + shift - camera_y;
        if (ray_y > 192 || ray_y < -128) continue;
        int ray = (int)((h >> 4) % (uint32_t)GODRAY_RAY_COUNT);
        int ray_x = hflip ? 208 : 48;
        const GodrayRange range = g_godray_ranges[ray];
        int visible_piece = 0;
        for (unsigned p = 0; p < range.piece_count && id < GODRAY_PIECE_LIMIT; p++) {
            const GodrayPiece *piece = &g_godray_pieces[range.first_piece + p];
            int x = ray_x + (hflip ? 256 - piece->x - piece->width : piece->x) - camera_x;
            int y = ray_y + piece->y;
            if (x <= -(int)piece->width || x >= 256 || y <= -(int)piece->height || y >= 192) continue;
            set_obj(oam, id++, x, y, piece->tile_offset, gfx_base, ray,
                    piece_size(piece), hflip, 1);
            visible_piece++;
        }
        if (visible_piece && dust_count < GODRAY_SLOT_COUNT) {
            dust_x[dust_count] = ray_x + (hflip ? 96 : 72) - camera_x;
            dust_y[dust_count] = ray_y + 40;
            dust_palette[dust_count] = GODRAY_RAY_COUNT;
            dust_count++;
        }
    }

    int mote = 0;
    for (int d = 0; d < dust_count && id < GODRAY_OAM_LIMIT; d++) {
        for (int n = 0; n < 6 && id < GODRAY_OAM_LIMIT; n++, mote++) {
            int phase = (int)((s_frame + mote * 19u) & 63u);
            int drift_x = ((phase * (mote + 1) >> 3) & 15) - 7;
            int drift_y = (phase >> 2) - 8;
            int x = dust_x[d] + n * 11 + drift_x;
            int y = dust_y[d] + n * 9 + drift_y;
            int frame = (int)((s_frame + (uint32_t)mote * 7u) >> 4) & 1;
            set_obj(oam, id++, x, y, GODRAY_DUST_OFFSET + frame * 32, gfx_base,
                    dust_palette[d], SpriteSize_8x8, 0, 1);
        }
    }
    if (tide_visible) {
        for (int hide = 0; hide < GODRAY_OAM_LIMIT; hide++)
            oam->oamMemory[hide].attribute[0] = ATTR0_DISABLED;
    }
    hide_remaining(oam, id);
    if (!tide_visible) setup_blend(sub);
    return id;
}

void godrays_update(int camera_x, int top_camera_y, int bottom_camera_y) {
    s_frame++;
    // Tide rendering belongs to a separate layer. If enabled later, the whole
    // engine is hidden while its line is visible so semi-transparent OBJ never
    // becomes opaque inside the tide's fade-to-black window.
    render_screen(&oamSub, (uint8_t *)0x06600000, camera_x, top_camera_y, 1,
                  tide_visible_on_screen(top_camera_y));
    render_screen(&oamMain, (uint8_t *)0x06400000, camera_x, bottom_camera_y, 0,
                  tide_visible_on_screen(bottom_camera_y));
}

void godrays_present(void) {
    oamUpdate(&oamSub);
    oamUpdate(&oamMain);
    g_godray_debug[0] = REG_BLDCNT;
    g_godray_debug[1] = REG_BLDALPHA;
    g_godray_debug[2] = OAM[0];
    g_godray_debug[3] = REG_DISPCNT;
}

#else

void godrays_init(void) { }
void godrays_update(int camera_x, int top_camera_y, int bottom_camera_y) {
    (void)camera_x;
    (void)top_camera_y;
    (void)bottom_camera_y;
}
void godrays_present(void) { }

#endif
