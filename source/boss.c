#include "boss.h"

// Translation unit never empty (ISO C) when ENCOUNTERS_PROTO=0.
typedef int boss_translation_unit_not_empty;

#if ENCOUNTERS_PROTO

#include <nds.h>
#include <string.h>
#include "bestiary_font.h"
#include "encounters_act1.h"
#include "upgrades.h"

// ---------------------------------------------------------------------------
// Timing (vblanks, the main loop passes the elapsed ones)
// ---------------------------------------------------------------------------

// All the pacing of the intro and the victory (DESIGN.md 6.13.7 "Ritmo"), in vblanks (60 = 1 s). The voices set their own
// length (BossDef.voice_*_frames, from the WAV), the rest is here.
// Intro: hold, slow zoom, pause, name, title, pause, voice + phrase, tail, zoom out.
#define T_INTRO_HOLD 48           // [TUNABLE-PLACEHOLDER] frozen, no zoom
#define T_INTRO_ZOOM 108          // [TUNABLE-PLACEHOLDER] x1 -> x2, slowing down at the end
#define T_INTRO_PAUSE1 36         // [TUNABLE-PLACEHOLDER] before the name
#define T_NAME_FADE 30            // [TUNABLE-PLACEHOLDER] also the victory name
#define T_TITLE_DELAY 24          // [TUNABLE-PLACEHOLDER] title starts this long after the name
#define T_TITLE_FADE 24           // [TUNABLE-PLACEHOLDER]
#define T_INTRO_PAUSE2 36         // [TUNABLE-PLACEHOLDER] before the voice
#define T_INTRO_TAIL 72           // [TUNABLE-PLACEHOLDER] still after the voice ends
#define T_INTRO_OUT 30            // [TUNABLE-PLACEHOLDER] zoom out, text fades
// Victory: boss falls (not frozen), hold, slow zoom, fade to bone (name and title appear), strike, pause, voice + phrase, tail.
#define T_VIC_PRE 24              // [TUNABLE-PLACEHOLDER] the boss and its escort fall before the screens freeze
#define T_VIC_HOLD 60             // [TUNABLE-PLACEHOLDER] frozen on its last pose
#define T_VIC_ZOOM 90             // [TUNABLE-PLACEHOLDER]
#define T_VIC_FADE 90             // [TUNABLE-PLACEHOLDER]
#define T_VIC_STRIKE 36           // [TUNABLE-PLACEHOLDER] the red line wipes in
#define T_VIC_PAUSE 30            // [TUNABLE-PLACEHOLDER] before the voice
#define T_VIC_TAIL 90             // [TUNABLE-PLACEHOLDER] still after the voice, then the Reliquia

#define I_ZOOM_END (T_INTRO_HOLD + T_INTRO_ZOOM)
#define I_NAME_START (I_ZOOM_END + T_INTRO_PAUSE1)
#define I_TITLE_START (I_NAME_START + T_TITLE_DELAY)
#define I_VOICE_START (I_TITLE_START + T_TITLE_FADE + T_INTRO_PAUSE2)
#define V_ZOOM_END (T_VIC_HOLD + T_VIC_ZOOM)
#define V_FADE_END (V_ZOOM_END + T_VIC_FADE)
#define V_NAME_START (V_ZOOM_END + T_VIC_FADE / 3)
#define V_TITLE_START (V_NAME_START + T_TITLE_DELAY)
#define V_STRIKE_START V_FADE_END
#define V_VOICE_START (V_STRIKE_START + T_VIC_STRIKE + T_VIC_PAUSE)


#define PHASE_FRAMES 60           // invulnerable second of a phase change
#define FADE_STEPS 16
#define ESCORT_SLOTS 6
#define BOSS_BODY_CENTER 28       // px from the feet to the middle of the sprite (zoom focus)
#define BOSS_HEAD 56              // px from the feet to the top of the head

// Muted palette (DESIGN.md 6.10: no pure primaries).
#define COL_CREAM   (RGB15(28, 26, 21) | BIT(15))
#define COL_BONE    (RGB15(18, 16, 13) | BIT(15))
#define COL_PHRASE  (RGB15(23, 21, 16) | BIT(15))
#define COL_RED     (RGB15(19, 4, 4) | BIT(15))
#define COL_RED_LT  (RGB15(25, 9, 8) | BIT(15))
#define COL_GOLD    (RGB15(27, 20, 11) | BIT(15))
#define COL_BAR_BG  (RGB15(5, 3, 3) | BIT(15))
#define COL_BORDER  (RGB15(2, 2, 2) | BIT(15))
#define COL_SEPIA   (RGB15(7, 5, 4) | BIT(15))
#define COL_SEPIA_LT (RGB15(12, 10, 8) | BIT(15))
#define COL_SEPIA_PH (RGB15(9, 7, 5) | BIT(15))
#define COL_NUM_SH  (RGB15(4, 1, 1) | BIT(15))
#define BONE_R 30
#define BONE_G 29
#define BONE_B 27

// Layout of the lower screen text (intro and victory share it).
#define TXT_NAME_Y 62
#define TXT_TITLE_Y 94
#define TXT_LINE_Y 116
#define TXT_LINE_STEP 13

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

static const BossDef *s_def;
static BossHooks s_hooks;
static int s_pack;
static int s_state;
static int s_phase = 1;
static int s_t;                       // vblanks in the current state
static int s_phase_t;
static int s_hp, s_max_hp;
static int s_bx, s_by;                // boss feet (world px), kept while it lives
static uint8_t s_voice_done;
static uint8_t s_snap_taken;
static Enemy s_pose;                  // the boss as it was the last frame it lived (victory picture)
static uint8_t s_pose_ok;

static uint16_t s_slot_timer[ESCORT_SLOTS];
static uint8_t s_slot_entry[ESCORT_SLOTS];
static uint8_t s_spawn_n[BOSS_MAX_ESCORT];

void boss_set_hooks(const BossHooks *hooks) { s_hooks = *hooks; }

static void escort_reset(void) {
    memset(s_slot_timer, 0, sizeof(s_slot_timer));
    memset(s_spawn_n, 0, sizeof(s_spawn_n));
}

void boss_reset(const BossDef *def, int pack) {
    s_def = def;
    s_pack = pack;
    s_state = BOSS_INACTIVE;
    s_phase = 1;
    s_t = 0;
    s_phase_t = 0;
    s_hp = s_max_hp = 0;
    s_voice_done = 0;
    s_snap_taken = 0;
    s_pose_ok = 0;
    escort_reset();
    sfx_stop_voice();
    sfx_set_bgm_track(0);
}

int boss_state(void) { return s_state; }
int boss_phase(void) { return s_phase; }
int boss_mode_active(void) { return s_state >= BOSS_INTRO && s_state <= BOSS_VICTORY; }
int boss_hud_active(void) { return s_state == BOSS_COMBAT || s_state == BOSS_PHASE_CHANGE; }
static int intro_out_start(void) { return I_VOICE_START + s_def->voice_intro_frames + T_INTRO_TAIL; }
static int intro_end(void) { return intro_out_start() + T_INTRO_OUT; }
static int victory_end(void) { return T_VIC_PRE + V_VOICE_START + s_def->voice_defeat_frames + T_VIC_TAIL; }

int boss_frozen(void) {
    return s_state == BOSS_INTRO || (s_state == BOSS_VICTORY && s_t >= T_VIC_PRE);
}
int boss_blocks_damage(const Enemy *e) {
    return s_state == BOSS_PHASE_CHANGE && s_def && e->type == s_def->enemy_type;
}

static const Enemy *find_boss(const Enemy *enemies, int max_enemies) {
    for (int i = 0; i < max_enemies; i++) {
        const Enemy *e = &enemies[i];
        if (e->active && e->hp > 0 && e->type == s_def->enemy_type) return e;
    }
    return 0;
}

static void note_boss(const Enemy *boss) {
    s_hp = boss->hp;
    s_max_hp = boss->max_hp;
    s_bx = TO_INT(boss->x);
    s_by = TO_INT(boss->y);
    s_pose = *boss;
    s_pose_ok = 1;
}

void boss_begin(const Enemy *enemies, int max_enemies) {
    if (!s_def || s_state != BOSS_INACTIVE) return;
    const Enemy *boss = find_boss(enemies, max_enemies);
    if (boss) note_boss(boss);
    s_state = BOSS_INTRO;
    s_t = 0;
    s_phase = 1;
    s_snap_taken = 0;
    s_voice_done = 0;
    if (s_hooks.set_barriers) s_hooks.set_barriers(1);
    sfx_stop_bgm();
    sfx_set_bgm_track(1);                    // selected now, opened when the intro ends
}

void boss_victory(void) {
    if (!s_def || s_state == BOSS_VICTORY || s_state == BOSS_REST) return;
    s_state = BOSS_VICTORY;
    s_t = 0;
    s_voice_done = 0;
    s_snap_taken = 0;
    sfx_stop_bgm();
}

// ---------------------------------------------------------------------------
// Combat: phases and escort
// ---------------------------------------------------------------------------

static void escort_update(Enemy *enemies, int max_enemies) {
    const int ph = s_phase - 1;
    const int n = s_def->n_escort[ph];
    const BossEscortDef *list = s_def->escort[ph];
    for (int i = 0; i < n; i++) {
        int live = 0, pending = 0;
        for (int k = 0; k < max_enemies; k++) {
            const Enemy *e = &enemies[k];
            if (e->active && e->hp > 0 && e->pack == s_pack && e->type == list[i].type) live++;
        }
        for (int s = 0; s < ESCORT_SLOTS; s++) if (s_slot_timer[s] && s_slot_entry[s] == i) pending++;
        for (int d = list[i].count - live - pending; d > 0; d--) {
            for (int s = 0; s < ESCORT_SLOTS; s++) {
                if (s_slot_timer[s]) continue;
                s_slot_timer[s] = list[i].refill_frames;
                s_slot_entry[s] = (uint8_t)i;
                break;
            }
        }
    }
    for (int s = 0; s < ESCORT_SLOTS; s++) {
        if (!s_slot_timer[s] || --s_slot_timer[s] != 0) continue;
        const BossEscortDef *d = &list[s_slot_entry[s]];
        if (s_hooks.spawn_escort) s_hooks.spawn_escort(d->type, d->x[s_spawn_n[s_slot_entry[s]]++ & 1]);
    }
}

int boss_combat_update(Enemy *enemies, int max_enemies) {
    if (!s_def) return 0;
    const Enemy *boss = find_boss(enemies, max_enemies);
    if (!boss) return 0;
    note_boss(boss);
    if (s_state == BOSS_COMBAT && s_phase < s_def->n_phases &&
        s_hp * 100 <= s_max_hp * (int)s_def->phase_pct[s_phase]) {
        s_phase++;
        s_state = BOSS_PHASE_CHANGE;
        s_phase_t = 0;
        escort_reset();                       // the escort follows the list of the new phase
    }
    if (s_state == BOSS_COMBAT || s_state == BOSS_PHASE_CHANGE) escort_update(enemies, max_enemies);
    return 1;
}

void boss_tick(int dt, uint32_t keys_down) {
    if (dt < 1) dt = 1;
    switch (s_state) {
    case BOSS_INTRO:
        s_t += dt;
        if (!s_voice_done && s_t >= I_VOICE_START) {
            s_voice_done = 1;
            sfx_play_voice(s_def->sfx_intro);
        }
        if (s_t >= intro_end() || (keys_down & KEY_START)) {
            s_state = BOSS_COMBAT;
            s_t = 0;
            sfx_stop_voice();
            sfx_start_bgm();                  // the boss track chosen in boss_begin()
        }
        break;
    case BOSS_PHASE_CHANGE:
        s_phase_t += dt;
        if (s_phase_t >= PHASE_FRAMES) { s_state = BOSS_COMBAT; s_phase_t = 0; }
        break;
    case BOSS_VICTORY: {
        const int was_frozen = s_t >= T_VIC_PRE;
        s_t += dt;
        if (!s_voice_done && s_t >= T_VIC_PRE + V_VOICE_START) {
            s_voice_done = 1;
            sfx_play_voice(s_def->sfx_defeat);
        }
        if (was_frozen && (keys_down & KEY_START)) s_t = victory_end();
        if (s_t >= victory_end()) {
            s_state = BOSS_REST;
            sfx_stop_voice();
            if (s_hooks.set_barriers) s_hooks.set_barriers(0);
            sfx_set_bgm_track(0);
            sfx_start_bgm();
        }
        break;
    }
    default:
        break;
    }
}

// ---------------------------------------------------------------------------
// Text helpers (Codex font, optionally scaled by whole pixels)
// ---------------------------------------------------------------------------

static uint16_t s_txt[SCREEN_W * 16];

// Draws `s` with the top-left at (x, y), each font pixel as scale x scale. Returns nothing; clips to the page.
static void text_scaled(uint16_t *page, int x, int y, const char *s, int scale, uint16_t col, int mark_dirty) {
    memset(s_txt, 0, sizeof(s_txt));
    bestiary_font_draw_utf8(s_txt, 0, 1, s, 0x8001);
    int w = bestiary_font_measure_utf8(s);
    if (w > SCREEN_W) w = SCREEN_W;
    for (int sy = 0; sy < 16; sy++) {
        const uint16_t *row = s_txt + sy * SCREEN_W;
        for (int dy = 0; dy < scale; dy++) {
            int py = y + sy * scale + dy;
            if ((unsigned)py >= SCREEN_H) continue;
            if (mark_dirty) dirty_row(py, x, x + w * scale);
            uint16_t *drow = page + py * SCREEN_W;
            for (int sx = 0; sx < w; sx++) {
                if (!row[sx]) continue;
                for (int dx = 0; dx < scale; dx++) {
                    int px = x + sx * scale + dx;
                    if ((unsigned)px < SCREEN_W) drow[px] = col;
                }
            }
        }
    }
}

static int text_width(const char *s, int scale) { return bestiary_font_measure_utf8(s) * scale; }

static void text_centered(uint16_t *page, int y, const char *s, int scale, uint16_t col) {
    text_scaled(page, (SCREEN_W - text_width(s, scale)) / 2, y, s, scale, col, 0);
}

// Colour between two palette entries in 8 steps (a = 0 is `from`, 8 is `to`): the text fades through a handful of ramps.
static uint16_t ramp(uint16_t from, uint16_t to, int a) {
    const int fr = from & 31, fg = (from >> 5) & 31, fb = (from >> 10) & 31;
    const int tr = to & 31, tg = (to >> 5) & 31, tb = (to >> 10) & 31;
    return (uint16_t)(0x8000 | (fr + (((tr - fr) * a) >> 3)) | ((fg + (((tg - fg) * a) >> 3)) << 5) |
                      ((fb + (((tb - fb) * a) >> 3)) << 10));
}

// 0..8 over `dur` vblanks starting at `start`.
static int alpha8(int t, int start, int dur) {
    if (t <= start) return 0;
    if (t >= start + dur) return 8;
    return ((t - start) * 8) / dur;
}

static int utf8_chars(const char *s) {
    int n = 0;
    for (; *s && *s != '\n'; s++) if (((unsigned char)*s & 0xC0) != 0x80) n++;
    return n;
}

// Lines separated by '\n', each centred by its full width; only the first `visible` characters are drawn (the phrase is
// written while the voice says it).
static void text_lines_reveal(uint16_t *page, int y, const char *s, uint16_t col, int visible) {
    char line[96], part[96];
    int n = 0;
    for (const char *p = s;; p++) {
        if (*p == '\n' || *p == 0) {
            line[n] = 0;
            const int chars = utf8_chars(line);
            const int show = visible < chars ? visible : chars;
            if (show > 0) {
                int k = 0, seen = 0;
                for (int i = 0; line[i] && k < (int)sizeof(part) - 1; i++) {
                    if (((unsigned char)line[i] & 0xC0) != 0x80) {
                        if (seen == show) break;
                        seen++;
                    }
                    part[k++] = line[i];
                }
                part[k] = 0;
                text_scaled(page, (SCREEN_W - text_width(line, 1)) / 2, y, part, 1, col, 0);
            }
            visible -= chars;
            y += TXT_LINE_STEP;
            n = 0;
            if (*p == 0) break;
        } else if (n < (int)sizeof(line) - 1) {
            line[n++] = *p;
        }
    }
}

static int phrase_total(const char *s) {
    int n = 0;
    for (; *s; s++) if (*s != '\n' && ((unsigned char)*s & 0xC0) != 0x80) n++;
    return n;
}

// Characters showing `t` vblanks after the voice started (the voice length sets the pace).
static int phrase_visible(const char *s, int t, int voice_frames) {
    if (t <= 0) return 0;
    const int total = phrase_total(s);
    if (t >= voice_frames) return total;
    return (total * t) / voice_frames;
}

// ---------------------------------------------------------------------------
// Life bar
// ---------------------------------------------------------------------------

#define BAR_X 6
#define BAR_Y 12                 // 6 rows (1 border + 4 + 1) centred on the middle of the hearts (y 6 + 18/2)
#define BAR_H 6

static void fill_span(uint16_t *row, int x0, int x1, uint16_t c) {
    for (int x = x0; x < x1; x++) row[x] = c;
}

void boss_draw_hud(uint16_t *buffer, int right, BossTextFn text) {
    if (!s_def) return;
    const int x0 = BAR_X, x1 = right;
    if (x1 - x0 < 16) return;
    const int inner0 = x0 + 1, inner1 = x1 - 1;
    const int inner_w = inner1 - inner0;
    int fill = s_max_hp > 0 ? (s_hp * inner_w) / s_max_hp : 0;
    if (s_hp > 0 && fill < 1) fill = 1;
    if (fill > inner_w) fill = inner_w;
    for (int r = 0; r < BAR_H; r++) {
        const int y = BAR_Y + r;
        dirty_row(y, x0, x1);
        uint16_t *row = buffer + y * SCREEN_W;
        if (r == 0 || r == BAR_H - 1) {
            fill_span(row, x0, x1, COL_BORDER);
            continue;
        }
        row[x0] = COL_BORDER;
        row[x1 - 1] = COL_BORDER;
        const uint16_t c = (r == 1) ? COL_RED_LT : COL_RED;
        fill_span(row, inner0, inner0 + fill, c);
        fill_span(row, inner0 + fill, inner1, COL_BAR_BG);
    }
    for (int i = 1; i < s_def->n_phases; i++) {            // a cream mark at the life where phase i+1 starts
        const int mx = inner0 + (inner_w * (int)s_def->phase_pct[i]) / 100;
        const int broken = s_phase > i;
        if (!broken) {
            for (int r = 0; r < BAR_H; r++) {
                dirty_row(BAR_Y + r, mx, mx + 1);
                buffer[(BAR_Y + r) * SCREEN_W + mx] = COL_CREAM;
            }
            continue;
        }
        // Broken: short golden sparks around where the mark stood (they flicker while the phase changes).
        const int hot = (s_state == BOSS_PHASE_CHANGE && s_phase == i + 1);
        const int flick = hot ? ((s_phase_t >> 2) & 1) : 0;
        static const int8_t spark[][2] = { {-1,1}, {1,1}, {0,2}, {0,3}, {-1,4}, {1,4}, {-2,0}, {2,0}, {-2,5}, {2,5}, {0,-1} };
        const int n = hot ? (flick ? 11 : 8) : 6;
        for (int k = 0; k < n; k++) {
            const int sx = mx + spark[k][0], sy = BAR_Y + spark[k][1];
            if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) continue;
            dirty_row(sy, sx, sx + 1);
            buffer[sy * SCREEN_W + sx] = COL_GOLD;
        }
    }
    text(buffer, BAR_X, BAR_Y + BAR_H + 2, s_def->name, COL_CREAM);
}

// ---------------------------------------------------------------------------
// Phase numeral over the boss
// ---------------------------------------------------------------------------

void boss_draw_world(uint16_t *buffer, int cam_x, int cam_y) {
    if (s_state != BOSS_PHASE_CHANGE || !s_def) return;
    const char *num = s_phase >= 3 ? "III" : "II";
    const int w = text_width(num, 3);
    const int x = s_bx - cam_x - w / 2;
    const int y = s_by - cam_y + 8;                  // just in front of the feet (the room's top edge would cut it above the head)
    if (y + 48 <= 0 || y >= SCREEN_H || x + w <= 0 || x >= SCREEN_W) return;
    text_scaled(buffer, x + 1, y + 1, num, 3, COL_NUM_SH, 1);
    text_scaled(buffer, x, y, num, 3, COL_RED, 1);
}

// ---------------------------------------------------------------------------
// Frozen screens: snapshot, zoom, vignette and fade to bone
// ---------------------------------------------------------------------------

static uint16_t s_snap[2][SCREEN_W * SCREEN_H] __attribute__((aligned(4)));   // [0] boss view (upper), [1] lower view
// Vignette: light = table[tx[x] + ty[y]], an ellipse; ordered dither (Bayer 4x4) between the 16 levels.
static uint16_t s_vtx[SCREEN_W], s_vty[SCREEN_H];
static uint8_t s_vlight[512];
static uint8_t s_vig_ready;
static int s_src;                     // snapshot the zoom looks at (always [0])
static int s_fx, s_fy;                // focus in that snapshot (screen px)
static int s_last_zoom, s_last_fade;
const Enemy *boss_last_pose(void) { return s_pose_ok ? &s_pose : 0; }

int boss_snapshot_pending(void) { return boss_frozen() && !s_snap_taken; }
int boss_focus_view_y(void) { return s_by - BOSS_BODY_CENTER - SCREEN_H / 2; }
uint16_t *boss_snapshot_buffer(int top) { return s_snap[top ? 0 : 1]; }

static void vignette_build(void) {
    // Elliptical focus: untouched in the middle, about 1/8 of the light in the corners. Integer maths only.
    for (int x = 0; x < SCREEN_W; x++) {
        int dx = 2 * x + 1 - SCREEN_W;
        if (dx < 0) dx = -dx;
        s_vtx[x] = (uint16_t)((dx * dx) >> 8);
    }
    for (int y = 0; y < SCREEN_H; y++) {
        int dy = 2 * y + 1 - SCREEN_H;
        if (dy < 0) dy = -dy;
        const int ny = (dy * 341) >> 8;
        s_vty[y] = (uint16_t)((ny * ny) >> 8);
    }
    for (int r2 = 0; r2 < 512; r2++) {
        int l = 255;
        if (r2 > 130) l = 255 - (((r2 - 130) * 43000) >> 16);
        if (l < 32) l = 32;
        s_vlight[r2] = (uint8_t)l;
    }
    s_vig_ready = 1;
}

// Light in sixteenths (16 = untouched): halves, quarters, eighths and sixteenths of the colour added up.
static inline uint16_t shade16(uint16_t c, unsigned f) {
    if (f >= 16) return c;
    uint32_t o = 0;
    if (f & 8) o += (c >> 1) & 0x3DEFu;
    if (f & 4) o += (c >> 2) & 0x1CE7u;
    if (f & 2) o += (c >> 3) & 0x0C63u;
    if (f & 1) o += (c >> 4) & 0x0421u;
    return (uint16_t)(o | 0x8000u);
}

static void darken_30(uint16_t *dst, const uint16_t *src) {
    for (int i = 0; i < SCREEN_W * SCREEN_H; i++) {
        const uint16_t c = src[i];
        dst[i] = (uint16_t)((((c >> 2) & 0x1CE7u) + ((c >> 4) & 0x0421u)) | 0x8000u);     // ~31 % of the light
    }
}

typedef struct {
    uint16_t a[32];          // c * (colour that stays)
    uint16_t g[32];          // gray * (colour that turns grey)
    uint16_t wr, wg, wb;     // bone * (bone mixed in)
} FadeLut;

static void fade_lut(FadeLut *l, int t) {
    // Colour drains completely, bone white mixes in up to 11/16 (the picture stays readable, like the maquette).
    const int dn = t * 16, wn = t * 11;
    const int A = ((256 - dn) * (256 - wn)) >> 8, B = (dn * (256 - wn)) >> 8, C = wn;
    for (int i = 0; i < 32; i++) { l->a[i] = (uint16_t)(i * A); l->g[i] = (uint16_t)(i * B); }
    l->wr = (uint16_t)(BONE_R * C);
    l->wg = (uint16_t)(BONE_G * C);
    l->wb = (uint16_t)(BONE_B * C);
}

static inline uint16_t fade_px(uint16_t c, const FadeLut *l) {
    const unsigned r = c & 31, g = (c >> 5) & 31, b = (c >> 10) & 31;
    const unsigned gray = (r * 5 + g * 9 + b * 2) >> 4;
    const unsigned gv = l->g[gray];
    return (uint16_t)(0x8000u | ((l->a[r] + gv + l->wr) >> 8) | (((l->a[g] + gv + l->wg) >> 8) << 5) |
                      (((l->a[b] + gv + l->wb) >> 8) << 10));
}

static int ease_out(int u) {                    // 0..256 -> 0..256, fast then slowing down
    return 256 - (((256 - u) * (256 - u)) >> 8);
}

static int ease_inout(int u) {                  // 0..256 smoothstep
    return (u * u * (768 - 2 * u)) >> 16;
}

// Nearest-neighbour zoom of the focus region: x1 at e = 0, x2 at e = 256 (128 x 96 px become 256 x 192).
// mode 0 plain, 1 vignette (strength follows e, dithered), 2 fade with `lut`. Writes straight to `dst` (the top page).
static void zoom_render(uint16_t *dst, const uint16_t *src, int e, int mode, const FadeLut *lut) {
    static const uint8_t bayer[16] = { 0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5 };
    const int step = 256 - ((128 * e) >> 8);                       // 8.8 source px per output px
    const int w = step, h = (step * 3) >> 2;
    int cx = 128 + (((s_fx - 128) * e) >> 8);
    int cy = 96 + (((s_fy - 96) * e) >> 8);
    int x0 = cx - w / 2, y0 = cy - h / 2;
    if (x0 < 0) x0 = 0;
    if (x0 > SCREEN_W - w) x0 = SCREEN_W - w;
    if (y0 < 0) y0 = 0;
    if (y0 > SCREEN_H - h) y0 = SCREEN_H - h;
    uint8_t le[512];
    if (mode == 1) for (int i = 0; i < 512; i++) le[i] = (uint8_t)(255 - (((255 - s_vlight[i]) * e) >> 8));   // fades in with the zoom
    int sy = y0 << 8;
    for (int y = 0; y < SCREEN_H; y++) {
        const uint16_t *srow = src + (sy >> 8) * SCREEN_W;
        uint16_t *drow = dst + y * SCREEN_W;
        int sx = x0 << 8;
        if (mode == 0) {
            for (int x = 0; x < SCREEN_W; x++) { drow[x] = srow[sx >> 8]; sx += step; }
        } else if (mode == 1) {
            const int ty = s_vty[y];
            const uint8_t *brow = bayer + ((y & 3) << 2);
            for (int x = 0; x < SCREEN_W; x++) {
                unsigned f = ((unsigned)le[s_vtx[x] + ty] + brow[x & 3]) >> 4;
                drow[x] = shade16(srow[sx >> 8], f > 16 ? 16 : f);
                sx += step;
            }
        } else {
            for (int x = 0; x < SCREEN_W; x++) { drow[x] = fade_px(srow[sx >> 8], lut); sx += step; }
        }
        sy += step;
    }
}

void boss_snapshot_commit(int view_x) {
    if (!s_vig_ready) vignette_build();
    s_src = 0;
    s_fy = SCREEN_H / 2;                      // snapshot [0] is rendered with the boss in the middle (boss_focus_view_y)
    s_fx = s_bx - view_x;
    if (s_fx < 0) s_fx = 0;
    if (s_fx >= SCREEN_W) s_fx = SCREEN_W - 1;
    s_snap_taken = 1;
    s_last_zoom = -1;
    s_last_fade = -1;
    if (s_state == BOSS_INTRO) darken_30(s_snap[1], s_snap[1]);      // in place: the intro never needs the original
}

// Zoom amount (0 = x1, 256 = x2) and fade step of the frozen screens at the current time.
static int zoom_amount(void) {
    if (s_state == BOSS_INTRO) {
        const int t = s_t, out = intro_out_start();
        if (t < T_INTRO_HOLD) return 0;
        if (t < I_ZOOM_END) return ease_out(((t - T_INTRO_HOLD) * 256) / T_INTRO_ZOOM);
        if (t < out) return 256;
        if (t < out + T_INTRO_OUT) return 256 - ease_inout(((t - out) * 256) / T_INTRO_OUT);
        return 0;
    }
    const int tv = s_t - T_VIC_PRE;
    if (tv < T_VIC_HOLD) return 0;
    if (tv < V_ZOOM_END) return ease_out(((tv - T_VIC_HOLD) * 256) / T_VIC_ZOOM);
    return 256;
}

static int victory_fade_step(void) {
    const int tv = s_t - T_VIC_PRE;
    if (tv <= V_ZOOM_END) return 0;
    const int fs = ((tv - V_ZOOM_END) * FADE_STEPS) / T_VIC_FADE;
    return fs > FADE_STEPS ? FADE_STEPS : fs;
}

void boss_frozen_bottom(uint16_t *page) {
    if (s_state == BOSS_INTRO) {
        const uint16_t dark = RGB15(4, 3, 3) | BIT(15);
        const int t = s_t, out = intro_out_start();
        const int ao = t >= out ? 8 - alpha8(t, out, T_INTRO_OUT) : 8;       // everything fades while the view pulls back
        swiFastCopy(s_snap[1], page, COPY_MODE_COPY | (SCREEN_W * SCREEN_H * 2 / 4));
        int a = alpha8(t, I_NAME_START, T_NAME_FADE);
        if (a > ao) a = ao;
        if (a > 0) text_centered(page, TXT_NAME_Y, s_def->name, 2, ramp(dark, COL_CREAM, a));
        a = alpha8(t, I_TITLE_START, T_TITLE_FADE);
        if (a > ao) a = ao;
        if (a > 0) text_centered(page, TXT_TITLE_Y, s_def->title, 1, ramp(dark, COL_BONE, a));
        const int vis = phrase_visible(s_def->line_intro, t - I_VOICE_START, s_def->voice_intro_frames);
        if (vis > 0 && ao > 0) text_lines_reveal(page, TXT_LINE_Y, s_def->line_intro, ramp(dark, COL_PHRASE, ao), vis);
        return;
    }
    const int tv = s_t - T_VIC_PRE;
    const int fs = victory_fade_step();
    if (fs == 0) {
        swiFastCopy(s_snap[1], page, COPY_MODE_COPY | (SCREEN_W * SCREEN_H * 2 / 4));
    } else {
        FadeLut l;
        fade_lut(&l, fs);
        for (int i = 0; i < SCREEN_W * SCREEN_H; i++) page[i] = fade_px(s_snap[1][i], &l);
    }
    const uint16_t bone = RGB15(BONE_R, BONE_G, BONE_B) | BIT(15);
    int a = alpha8(tv, V_NAME_START, T_NAME_FADE);
    if (a > 0) text_centered(page, TXT_NAME_Y, s_def->name, 2, ramp(bone, COL_SEPIA, a));
    a = alpha8(tv, V_TITLE_START, T_TITLE_FADE);
    if (a > 0) text_centered(page, TXT_TITLE_Y, s_def->title, 1, ramp(bone, COL_SEPIA_LT, a));
    const int vis = phrase_visible(s_def->line_defeat, tv - V_VOICE_START, s_def->voice_defeat_frames);
    if (vis > 0) text_lines_reveal(page, TXT_LINE_Y, s_def->line_defeat, COL_SEPIA_PH, vis);
    int len = ((tv - V_STRIKE_START) * (text_width(s_def->name, 2) + 12)) / T_VIC_STRIKE;     // the red line wipes in
    if (tv <= V_STRIKE_START) return;
    const int nw = text_width(s_def->name, 2) + 12;
    if (len > nw) len = nw;
    const int sx = (SCREEN_W - nw) / 2;
    for (int r = 0; r < 2; r++) {
        uint16_t *row = page + (TXT_NAME_Y + 14 + r) * SCREEN_W;
        for (int x = 0; x < len; x++) row[sx + x] = COL_RED;
    }
}

// After the vblank: the zoomed boss view straight into the top page, only when it changed.
void boss_frozen_top(uint16_t *page) {
    if (s_state != BOSS_INTRO && s_state != BOSS_VICTORY) return;
    const int e = zoom_amount();
    const int fs = s_state == BOSS_VICTORY ? victory_fade_step() : 0;
    if (e == s_last_zoom && fs == s_last_fade) return;
    s_last_zoom = e;
    s_last_fade = fs;
    FadeLut l;
    fade_lut(&l, fs);
    zoom_render(page, s_snap[s_src], e, s_state == BOSS_INTRO ? 1 : (fs ? 2 : 0), &l);
}

#endif // ENCOUNTERS_PROTO
