#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "arena.h"
#include "strip.h"

#define MAP_BYTES (64u * 256u * sizeof(uint16_t))
#define COLLISION_BYTES (128u * 512u / 4u)
#define CELL_COUNT (128u * 512u)

static uint16_t s_map_a[64u * 256u];
static uint16_t s_map_b[64u * 256u];
static uint8_t s_collision_a[COLLISION_BYTES];
static uint8_t s_collision_b[COLLISION_BYTES];
static int s_failures;

#define CHECK(condition, message) do { if (!(condition)) { ++s_failures; printf("FAIL: %s\n", message); } } while (0)

static unsigned collision_at(const uint8_t *collision, unsigned index) {
    return (collision[index >> 2] >> ((index & 3u) * 2u)) & 3u;
}

static int body_clear(const uint8_t *collision, int x, int y) {
    if (x < 1 || x >= 127 || y < 1 || y >= 511) return 0;
    for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++)
            if (collision_at(collision, (unsigned)(y + dy) * 128u + (unsigned)(x + dx)) & 1u) return 0;
    return 1;
}

static int has_bottom_to_top_path(const uint8_t *collision) {
    static int queue[CELL_COUNT];
    static uint8_t seen[CELL_COUNT];
    unsigned head = 0, tail = 0;
    memset(seen, 0, sizeof(seen));
    for (int x = 1; x < 127; x++) {
        int index = 509 * 128 + x;
        if (body_clear(collision, x, 509)) {
            seen[index] = 1;
            queue[tail++] = index;
        }
    }
    while (head < tail) {
        int index = queue[head++];
        int y = index >> 7;
        if (y == 2) return 1;
        const int next[4] = {index - 128, index + 128, index - 1, index + 1};
        for (int n = 0; n < 4; n++) {
            int target = next[n];
            int nx = target & 127, ny = target >> 7;
            if (seen[target] || !body_clear(collision, nx, ny)) continue;
            seen[target] = 1;
            queue[tail++] = target;
        }
    }
    return 0;
}

static void check_edges_and_start(void) {
    const Arena *arena = strip_arena();
    CHECK(g_arena == arena, "strip_start must install the strip as g_arena");
    CHECK(strip_start_x() == 256 && strip_start_y() == 1792, "player start must be centered and 256 px above bottom");
    CHECK(arena->num_enemies == 0 && arena->occlusion_runs == 0, "strip has no enemies or occlusion runs");
    for (unsigned y = 0; y < arena->collision_h; y++) {
        CHECK(collision_at(arena->collision, y * 128u) == 3, "left wall must stay solid");
        CHECK(collision_at(arena->collision, y * 128u + 127u) == 3, "right wall must stay solid");
    }
    for (unsigned x = 0; x < arena->collision_w; x++)
        CHECK(collision_at(arena->collision, (arena->collision_h - 1u) * 128u + x) == 3,
              "bottom collision row must be solid");
    for (unsigned band = 13; band < 16; band++) {
        for (unsigned y = band * 32u; y < (band + 1u) * 32u && y < 511u; y++)
            for (unsigned x = 1; x < 127; x++)
                CHECK(collision_at(arena->collision, y * 128u + x) == 0,
                      "starting bands must have no column footprints");
    }
}

static void check_rebase_continuity(void) {
    const Arena *arena = strip_arena();
    memcpy(s_map_a, arena->map, MAP_BYTES);
    memcpy(s_collision_a, arena->collision, COLLISION_BYTES);
    CHECK(strip_rebase_if_needed(STRIP_REBASE_TOP_PX) == 0, "threshold itself must not rebase");
    CHECK(strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1) == STRIP_SHIFT_PX, "player above threshold must rebase once");
    CHECK(strip_shift_total_px() == STRIP_SHIFT_PX, "shift total must accumulate the rebase");
    memcpy(s_map_b, arena->map, MAP_BYTES);
    memcpy(s_collision_b, arena->collision, COLLISION_BYTES);
    CHECK(memcmp(s_map_a, s_map_b + 64u * 64u, (256u - 64u) * 64u * sizeof(uint16_t)) == 0,
          "map rows in the overlap must remain identical after rebase");
    // The bottom boundary is reasserted solid after the shift; all preceding
    // collision rows in the overlap are copied byte-for-byte.
    CHECK(memcmp(s_collision_a, s_collision_b + 128u * 32u, (512u - 128u - 1u) * 32u) == 0,
          "collision rows in the overlap must remain identical except the solid bottom boundary");
    for (int band = 1; band < 500; band++) {
        int delta = strip_lane_center_px(band) - strip_lane_center_px(band - 1);
        if (delta < 0) delta = -delta;
        CHECK(delta <= 8, "neighboring lane centers must differ by at most 8 px, including rebase seams");
    }
}

int main(void) {
    strip_start(0x12345678u);
    check_edges_and_start();
    memcpy(s_map_a, strip_arena()->map, MAP_BYTES);
    memcpy(s_collision_a, strip_arena()->collision, COLLISION_BYTES);
    strip_start(0x12345678u);
    CHECK(memcmp(s_map_a, strip_arena()->map, MAP_BYTES) == 0, "same seed must reproduce tilemap");
    CHECK(memcmp(s_collision_a, strip_arena()->collision, COLLISION_BYTES) == 0, "same seed must reproduce collision");
    strip_start(0x87654321u);
    CHECK(memcmp(s_map_a, strip_arena()->map, MAP_BYTES) != 0 ||
          memcmp(s_collision_a, strip_arena()->collision, COLLISION_BYTES) != 0,
          "different seeds must change generated content");
    strip_start(0x12345678u);
    check_rebase_continuity();

    strip_start(0x243f6a88u);
    for (int band = 0; band < 500; band += 4) {
        CHECK(has_bottom_to_top_path(strip_arena()->collision), "3x3-cell actor must cross the current window");
        CHECK(strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1) == STRIP_SHIFT_PX,
              "forced rebase should generate four more bands");
    }
    printf(s_failures == 0 ? "STRIP_HOST_TEST=PASS\n" : "STRIP_HOST_TEST=FAIL\n");
    return s_failures == 0 ? 0 : 1;
}
