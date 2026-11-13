#include "weapons.h"
#include "gameplay.h"
#include "modifiers.h"
#include "grenade.h"
#include "groundfx.h"
#include "hitvolume.h"

/* TUNABLE-PLACEHOLDER: Player Weapons Tuning Table (Fixed-Point 8.8).
 * Goal hits to kill (DESIGN.md 4.3): shotgun point blank 1 shooter / 2-3 charger,
 * sniper 1 shooter / 2 charger. */
const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES] = {
    [WEAPON_SHOTGUN] = {
        .name = "SHOTGUN",
        .damage_per_hit = 40,       /* 40 dmg * 5 pellets = 200 point blank (scale 100 = 1.0) */
        .pellets = 5,
        .fire_cooldown = 36,        /* marked pump between shots */
        .projectile_speed = 1536,   /* 6.0 px/frame */
        .projectile_range = 22,     /* ~132 px: lethal close, weak far */
        .spread_angle = 120,
        .aim_min_frames = 0,
        .knockback = 640,           /* 2.5 px/frame shove */
        .stun_frames = 10,
        .recoil = 512,              /* 2 px kick back */
        .shake_amp = 2,
        .shake_frames = 6
    },
    [WEAPON_SNIPER] = {
        .name = "SNIPER",
        .damage_per_hit = 150,      /* skeleton 100 hp: 1 hit, shooter 200: 2, charger 300: 2 (scale 100 = 1.0) */
        .pellets = 1,
        .fire_cooldown = 40,
        .projectile_speed = 0,
        .projectile_range = 320,    /* ray length in ground px */
        .spread_angle = 0,
        .aim_min_frames = 24,       /* ~0.4 s before the shot is armed */
        .knockback = 0,
        .stun_frames = 0,
        .recoil = 0,
        .shake_amp = 3,
        .shake_frames = 8
    },
    [WEAPON_GRENADE] = {
        .name = "GRENADE",
        .damage_per_hit = 300,      /* damage at the blast centre; falls to 75 at the rim */
        .pellets = 1,
        .fire_cooldown = 60,
        .projectile_speed = 0,
        .projectile_range = 150,    /* maximum throw distance in ground px */
        .spread_angle = 0,
        .aim_min_frames = 0,
        .knockback = 768,           /* 3 px/frame shove at the centre */
        .stun_frames = 12,
        .recoil = 0,
        .shake_amp = 4,
        .shake_frames = 10
    }
};

int g_fx_style = 0;

char weapons_fx_style_letter(void) {
    return (char)('A' + (g_fx_style % FX_STYLE_COUNT));
}

int g_aura_style = 0;                     // sniper aura look (weapons.h): 0 = L, 1 = G, 2 = E, 3 = H

char weapons_aura_style_letter(void) {
    static const char letters[AURA_STYLE_COUNT] = {'L', 'G', 'E', 'H'};
    return letters[g_aura_style % AURA_STYLE_COUNT];
}

#define ENEMY_HIT_RADIUS 11          // ground px (pellets); the sniper ray uses body_hit_test
#define SNIPER_CANCEL_RADIUS 12      // screen px around the player's body
#define MIN_AIM_DISTANCE 4           // ground px; closer than this there is no direction

#define MAX_SPARKS 40
#define SPARK_LIFE_MIN 6

typedef struct {
    int active;
    fixed x, y;           // 8.8 screen-space world position (height already applied)
    fixed vx, vy;
    int life, max_life;
    int sniper;           // sniper impact: fire palette, gold, orange, ash (DESIGN.md 6.10)
} WeaponSpark;

typedef struct {
    int life;
    int x, y;             // muzzle in world px (height applied)
    int dir_x, dir_y;     // 8.8 screen direction of the shot
} MuzzleFlash;

typedef struct {
    int life;
    int x0, y0, x1, y1;   // world px, height applied
} SniperTrail;

enum { AIM_IDLE = 0, AIM_AIMING, AIM_READY, AIM_CANCELLED };

static PlayerProjectile s_player_projectiles[MAX_PLAYER_PROJECTILES];
static WeaponSpark s_sparks[MAX_SPARKS];
static MuzzleFlash s_flash;
static SniperTrail s_trail;

// Generic effect parts (shotgun cone, casing, smoke, dust, sniper rings and crosses...).
// One shared pool of 32 slots per weapon; kind FXP_NONE = free slot.
#define MAX_FX_PARTS 32
enum {
    FXP_NONE = 0,
    FXP_CONE,       // shotgun fire cone (B, C); vx,vy = shot direction; life 4 = 3 drawn frames
    FXP_SMOKE,      // grey puff that rises and drifts (B)
    FXP_SHELL,      // spent casing: gravity and two bounces (B); aux = bounces
    FXP_DUST,       // dust cloud of dots (impacts in B, recoil in C); size = spread
    FXP_ARC,        // shock arc on the ground (C), floor pass; aux = centre index (0..31)
    FXP_CROSS,      // sniper cross flash, muzzle and hits (fire palette); size = arm
    FXP_FRAG        // fragment with gravity (C shotgun and sniper impacts)
};

typedef struct {
    int kind;
    int life, max_life;
    int size;              // radius / arm length / spread, per kind
    int aux;               // per kind, see FXP_*
    fixed x, y;            // world px (8.8), same space as the pellets and sparks
    fixed h, vh;           // height above (x,y) in 8.8, vertical speed in 8.8 px/frame
    fixed vx, vy;          // 8.8 px per frame
} FxPart;

static FxPart s_fx[MAX_FX_PARTS];

// Palette of the effects (DESIGN.md 4.9, 6.10): enum and RGB15 table, same order. Declared before the aura
// looks, which use the colours.
enum {
    FX_CORE = 0, FX_HOT, FX_COOL,                  // muzzle flash
    FX_PELLET_HEAD,
    FX_SPARK_A, FX_SPARK_B, FX_SPARK_C,            // impact sparks, hot to cold
    FX_TAIL,                                       // pellet tail, dim blue
    FX_WHITE, FX_YELLOW, FX_ORANGE,                // shotgun cone, white to orange
    FX_CYAN, FX_CYAN_DIM,                          // shotgun shock arcs (C), fade out
    FX_BRASS,                                      // spent casing
    FX_SMOKE_A, FX_SMOKE_B, FX_SMOKE_C,            // grey smoke, light to dark
    FX_DUST_A, FX_DUST_B,                          // dust, light to dark
    FX_GOLD, FX_BLOOD, FX_RED, FX_ASH,             // fire palette (DESIGN.md 6.10): gold, blood red, ember, ash
    FX_BLACK,                                      // thorn spikes (aura E)
    FX_NUM_COLORS
};

static const uint16_t s_fx_rgb[FX_NUM_COLORS] = {
    RGB15(31, 31, 24), RGB15(31, 24, 6), RGB15(28, 12, 2),
    RGB15(31, 30, 20),
    RGB15(31, 30, 18), RGB15(31, 18, 3), RGB15(20, 5, 2),
    RGB15(10, 14, 20),                             // FX_TAIL
    RGB15(31, 31, 31), RGB15(31, 28, 8), RGB15(31, 15, 3),
    RGB15(16, 28, 31), RGB15(8, 16, 24),
    RGB15(28, 22, 8),                              // FX_BRASS
    RGB15(17, 17, 18), RGB15(11, 11, 12), RGB15(6, 6, 7),
    RGB15(22, 20, 16), RGB15(13, 12, 10),
    RGB15(31, 21, 4),                              // FX_GOLD
    RGB15(15, 2, 2),                               // FX_BLOOD
    RGB15(28, 5, 2),                               // FX_RED
    RGB15(9, 8, 8),                                // FX_ASH
    RGB15(2, 1, 1)                                 // FX_BLACK
};

// Sniper charge aura (DESIGN.md 4.9, 6.10). Look L (default, F2): flame tongues, 6..8 short wavy flames
// from the feet ellipse, yellow at the base, orange and red at the tip, with dithered edges. A flame is a
// polyline with a 3 px step; each step takes a zig-zag heading plus one LCG jitter, so it looks angular.
// The flames rebuild every 2-3 frames (every 2 at READY) so they crackle; the anchors turn slowly round the
// body. A flame whose anchor is in the back half of the ellipse (sin < 0) is drawn on the floor pass, under
// the sprite; the others on the pass after it. Walls hide pixels as for the other actor FX. Fixed pool and
// hard caps: 8 flames of 5 steps.
#define AURA_STEP 3                      // px per bolt step
#define AURA_BOLT_PTS 6                  // a flame has up to 5 steps
#define AURA_MAX_BOLTS 8                 // flame tongues in the pool (slots 0..7)
#define AURA_BOLT_LIFE 3                 // frames a built flame lives (a rebuild comes every 2-3 frames)
#define AURA_FLASH_FRAMES 3
#define AURA_SEG_MAX_STEPS 48            // hard cap on every line walk
typedef struct {
    int active;
    int n;                // points; steps = n - 1
    int px[AURA_BOLT_PTS], py[AURA_BOLT_PTS];   // world px; point 0 on the feet ellipse
    int back;             // anchor in the back half: floor pass
    int occl;             // a wall may hide some of it (tested when built)
    int age, life;        // frames
} AuraBolt;
static AuraBolt s_aura_bolts[AURA_MAX_BOLTS];
static uint32_t s_aura_seed = 1;         // shape and jitter source (LCG): no division, no rng_range per point
static int s_aura_rot = 0;               // anchor rotation, 32 = one turn; +1 per rebuild
static int s_aura_regen = 0;             // frames until the next rebuild (0 = rebuild now)
static int s_aura_x = 0, s_aura_y = 0;     // player's feet (world px), set while aiming
static int s_aura_frames = 1;              // aim frames until READY (charge = timer / this)
static int s_aura_flash = 0;               // READY flash frames left

// Looks G, E and H (DESIGN.md, segunda ronda de auras). Integer only; fixed pools and hard caps:
//   G glow:   12 rays x 14 px from the chest, floor pass (the body covers them).
//   E thorns: 16 spikes x 3 px on the feet ellipse (contract cap 24) + 16 drops, floor pass.
//   H ash:    6 smoke volutes (cap 6) + 16 embers (cap 16), front pass (over the body).
#define GLOW_RAYS 12
#define GLOW_MAX_LEN 14
#define THORN_SPIKES 16
#define THORN_LEN 3
#define THORN_DROPS 16
#define ASH_VOLUTES 6
#define ASH_EMBERS 16
#define AURA_FADE_FRAMES 3               // G/E/H keep drawing this many frames after the release (the shot)
typedef struct { int active, x, y, life, color; } AuraMote;          // one-px mote: thorn drop, ember
typedef struct { int active, ax, ay, age, life, ph; } AshVolute;     // smoke column from a shoulder
static int s_aura_cx = 0, s_aura_cy = 0;   // chest (world px): the muzzle point at its height
static int s_aura_prog_live = 0;           // charge of the last charging frame (G/E/H draw with it)
static int s_aura_fade = 0;                // frames left to draw G/E/H after the release
static int s_aura_was_ready = 0;
static int s_aura_tick = 0;                // frame counter: glow turn and spawn rates
static int s_glow_rot = 0;                 // ray rotation, 32 = one turn; one step every 4 frames
static AuraMote s_drops[THORN_DROPS];
static AuraMote s_embers[ASH_EMBERS];
static AshVolute s_volutes[ASH_VOLUTES];

static void aura_reset(void) {
    for (int i = 0; i < AURA_MAX_BOLTS; i++) s_aura_bolts[i].active = 0;
    for (int i = 0; i < THORN_DROPS; i++) s_drops[i].active = 0;
    for (int i = 0; i < ASH_EMBERS; i++) s_embers[i].active = 0;
    for (int i = 0; i < ASH_VOLUTES; i++) s_volutes[i].active = 0;
    s_aura_flash = 0;
    s_aura_regen = 0;
    s_aura_fade = 0;
    s_aura_was_ready = 0;
}

static int s_weapon_cooldown = 0;
static int s_aim_state = AIM_IDLE;
static int s_aim_timer = 0;
static int s_aim_prog = 0;          // collimation 0..256 (256 = armed), set once per frame in weapons_input
static fixed s_aim_dir_x = 0, s_aim_dir_y = 256;
static fixed s_aim_muzzle_x = 0, s_aim_muzzle_y = 0;
static int s_aim_muzzle_h = 0;
static int s_aim_len = 0;         // ground px the laser reaches before a wall
static fixed s_last_dir_x = 0, s_last_dir_y = 0;
static int s_shake_timer = 0, s_shake_frames = 1, s_shake_amp = 0;
static uint32_t s_shake_tick = 0;

static inline int abs_int(int v) {
    return v < 0 ? -v : v;
}

static uint32_t int_sqrt(uint32_t n) {
    if (n == 0) return 0;
    uint32_t root = 0;
    uint32_t bit = 1u << 30;
    while (bit > n) bit >>= 2;
    while (bit != 0) {
        if (n >= root + bit) {
            n -= root + bit;
            root = (root >> 1) + bit;
        } else {
            root >>= 1;
        }
        bit >>= 2;
    }
    return root;
}

void weapons_init(void) {
    s_weapon_cooldown = 0;
    s_aim_state = AIM_IDLE;
    s_aim_timer = 0;
    s_aim_prog = 0;
    s_last_dir_x = s_last_dir_y = 0;
    s_shake_timer = 0;
    s_flash.life = 0;
    s_trail.life = 0;
    s_aim_len = 0;
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) s_player_projectiles[i].active = 0;
    for (int i = 0; i < MAX_SPARKS; i++) s_sparks[i].active = 0;
    aura_reset();
    for (int i = 0; i < MAX_FX_PARTS; i++) s_fx[i].kind = FXP_NONE;
    grenade_init();
}

void weapons_shift_y(int dy_px) {
    fixed fdy = TO_FIXED(dy_px);
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++)
        if (s_player_projectiles[i].active) s_player_projectiles[i].y += fdy;
    for (int i = 0; i < MAX_SPARKS; i++)
        if (s_sparks[i].active) s_sparks[i].y += fdy;
    for (int i = 0; i < MAX_FX_PARTS; i++)
        if (s_fx[i].kind != FXP_NONE) s_fx[i].y += fdy;
    if (s_flash.life > 0) s_flash.y += dy_px;
    if (s_trail.life > 0) { s_trail.y0 += dy_px; s_trail.y1 += dy_px; }
    if (s_aim_state != AIM_IDLE && s_aim_state != AIM_CANCELLED) s_aim_muzzle_y += fdy;
    for (int i = 0; i < AURA_MAX_BOLTS; i++)
        if (s_aura_bolts[i].active)
            for (int p = 0; p < s_aura_bolts[i].n; p++) s_aura_bolts[i].py[p] += dy_px;
    s_aura_y += dy_px;
    s_aura_cy += dy_px;
    for (int i = 0; i < THORN_DROPS; i++)
        if (s_drops[i].active) s_drops[i].y += dy_px;
    for (int i = 0; i < ASH_EMBERS; i++)
        if (s_embers[i].active) s_embers[i].y += dy_px;
    for (int i = 0; i < ASH_VOLUTES; i++)
        if (s_volutes[i].active) s_volutes[i].ay += dy_px;
}

void weapons_cycle(PlayerState *player) {
    if (!player) return;
    player->current_weapon = (WeaponType)((player->current_weapon + 1) % NUM_WEAPON_TYPES);
    s_aim_state = AIM_IDLE;
    s_aim_timer = 0;
    s_aim_prog = 0;
    aura_reset();
    grenade_cancel();
}

const char *weapons_get_name(WeaponType type) {
    if (type >= 0 && type < NUM_WEAPON_TYPES) return g_weapon_tuning[type].name;
    return "UNKNOWN";
}

int weapons_get_active_projectile_count(void) {
    int count = 0;
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        if (s_player_projectiles[i].active) count++;
    }
    return count;
}

void weapons_last_shot_dir(fixed *dir_x, fixed *dir_y) {
    *dir_x = s_last_dir_x;
    *dir_y = s_last_dir_y;
}

void weapons_shake_offset(int *dx, int *dy) {
    *dx = 0;
    *dy = 0;
    if (s_shake_timer <= 0) return;
    int amp = (s_shake_amp * s_shake_timer) / s_shake_frames;
    if (amp < 1) amp = 1;
    // Deterministic zig-zag so scenarios stay reproducible.
    *dx = (s_shake_tick & 1) ? amp : -amp;
    *dy = (s_shake_tick & 2) ? (amp + 1) / 2 : -((amp + 1) / 2);
}

// ---------------------------------------------------------------------------
// Effects: procedural strokes, no sprites (DESIGN.md 4.7)
// ---------------------------------------------------------------------------

// 2:1 ellipse as a 32-step table (unit circle x256). Screen point of radius r at step k:
// x = r*C[k] >> 8, y = r*S[k] >> 9 (flat on the ground) or >> 8 (upright).
static const int s_ell_cos[32] = {
    256, 251, 237, 213, 181, 142, 98, 50, 0, -50, -98, -142, -181, -213, -237, -251,
    -256, -251, -237, -213, -181, -142, -98, -50, 0, 50, 98, 142, 181, 213, 237, 251
};
static const int s_ell_sin[32] = {
    0, 50, 98, 142, 181, 213, 237, 251, 256, 251, 237, 213, 181, 142, 98, 50,
    0, -50, -98, -142, -181, -213, -237, -251, -256, -251, -237, -213, -181, -142, -98, -50
};
static const int s_dust_dx[6] = {-3, 2, -1, 4, -4, 1};
static const int s_dust_dy[6] = {1, -2, 3, 0, -1, 2};

// Pool slot for a new part, or 0 when the pool is full (the effect is simply skipped).
static FxPart *fx_spawn(int kind, int life, fixed x, fixed y) {
    for (int i = 0; i < MAX_FX_PARTS; i++) {
        FxPart *p = &s_fx[i];
        if (p->kind != FXP_NONE) continue;
        p->kind = kind;
        p->life = life;
        p->max_life = life;
        p->size = 0;
        p->aux = 0;
        p->x = x;
        p->y = y;
        p->h = 0;
        p->vh = 0;
        p->vx = 0;
        p->vy = 0;
        return p;
    }
    return 0;
}

// Ellipse index whose screen direction best matches the shot (dot product, no trig).
static int ellipse_index_for(fixed dir_x, fixed dir_y) {
    int best = 0;
    fixed best_dot = dir_x * s_ell_cos[0] + ((dir_y * s_ell_sin[0]) >> 1);
    for (int i = 1; i < 32; i++) {
        fixed dot = dir_x * s_ell_cos[i] + ((dir_y * s_ell_sin[i]) >> 1);
        if (dot > best_dot) {
            best_dot = dot;
            best = i;
        }
    }
    return best;
}

// Fragment thrown from an impact point (screen coordinates, height 0).
static void spawn_frag(int x, int y, fixed back_x, fixed back_y) {
    FxPart *p = fx_spawn(FXP_FRAG, 12, TO_FIXED(x), TO_FIXED(y));
    if (!p) return;
    int speed = 256 + rng_range(0, 256);
    int side = rng_range(-256, 256);
    p->vx = ((back_x * speed) >> 8) + ((-back_y * side) >> 8);
    p->vy = ((back_y * speed) >> 8) + ((back_x * side) >> 8);
    p->vh = 384 + rng_range(0, 256);
}

static void spawn_dust(fixed x, fixed y, int size, int life) {
    FxPart *p = fx_spawn(FXP_DUST, life, x, y);
    if (p) p->size = size;
}

// Sparks leave the impact point opposite to the shot, with a sideways spread.
// Shotgun pellets follow g_fx_style: B adds a dust cloud; C adds a bigger spark burst and a fragment.
// Sniper impacts always take style C and its palette (gold, orange, ash) in render_fx.
static void spawn_impact(int x, int y, fixed back_x, fixed back_y, int count, int sniper) {
    int style = sniper ? 2 : g_fx_style;
    int n = count;
    if (style == 1) n = count > 1 ? count - 1 : 1;
    else if (style == 2) n = count + 2;
    for (int k = 0; k < n; k++) {
        for (int i = 0; i < MAX_SPARKS; i++) {
            if (s_sparks[i].active) continue;
            int speed = 320 + (int)(rng_next() % 400u);                  // 1.25..2.8 px/frame
            int side = (int)(rng_next() % 641u) - 320;                   // +-1.25 px/frame
            s_sparks[i].active = 1;
            s_sparks[i].x = TO_FIXED(x);
            s_sparks[i].y = TO_FIXED(y);
            s_sparks[i].vx = ((back_x * speed) >> 8) + ((-back_y * side) >> 8);
            s_sparks[i].vy = ((back_y * speed) >> 8) + ((back_x * side) >> 8) - 64;
            s_sparks[i].max_life = SPARK_LIFE_MIN + (int)(rng_next() % 5u);
            s_sparks[i].life = s_sparks[i].max_life;
            s_sparks[i].sniper = sniper;
            break;
        }
    }
    if (style == 1) {
        spawn_dust(TO_FIXED(x), TO_FIXED(y), 1, 10);
    } else if (style == 2) {
        spawn_frag(x, y, back_x, back_y);
    }
}

static void spawn_flash(const WeaponInput *in, fixed dir_x, fixed dir_y) {
    s_flash.life = 3;
    s_flash.x = TO_INT(in->muzzle_x);
    s_flash.y = TO_INT(in->muzzle_y) - in->muzzle_h;
    s_flash.dir_x = dir_x;
    s_flash.dir_y = dir_y;
}

// Shotgun: wide cone at the muzzle (B, C); B throws a casing and leaves smoke;
// C kicks up dust at the feet and draws a shock arc on the ground.
static void spawn_shell(const WeaponInput *in, fixed dir_x, fixed dir_y) {
    FxPart *p = fx_spawn(FXP_SHELL, 28, in->muzzle_x, in->muzzle_y);
    if (!p) return;
    p->h = TO_FIXED(in->muzzle_h);
    p->vx = (-dir_y * 3) >> 1;          // 1.5 px/frame to the side of the shot
    p->vy = (dir_x * 3) >> 1;
    p->vh = 640;
}

static void spawn_smoke(fixed x, fixed y, fixed h, fixed vx, fixed vy, int life) {
    FxPart *p = fx_spawn(FXP_SMOKE, life, x, y);
    if (!p) return;
    p->h = h;
    p->vh = 64 + rng_range(0, 64);      // rises slowly
    p->vx = vx;
    p->vy = vy;
    p->size = 3 + rng_range(0, 1);
}

static void spawn_recoil_dust(const WeaponInput *in) {
    for (int k = 0; k < 3; k++) {
        FxPart *p = fx_spawn(FXP_DUST, 12,
                             in->player_x + rng_range(-6, 6) * 256,
                             in->player_y + rng_range(-4, 4) * 256);
        if (!p) return;
        p->size = 2;
        p->vx = rng_range(-96, 96);
        p->vy = rng_range(-64, 64);
    }
}

static void spawn_arc(const WeaponInput *in, fixed dir_x, fixed dir_y) {
    FxPart *p = fx_spawn(FXP_ARC, 8, in->player_x, in->player_y);
    if (p) p->aux = ellipse_index_for(dir_x, dir_y);
}

static void spawn_shotgun_fx(const WeaponInput *in, fixed dir_x, fixed dir_y) {
    if (g_fx_style == 0) return;
    FxPart *cone = fx_spawn(FXP_CONE, 4, in->muzzle_x, in->muzzle_y);
    if (cone) {
        cone->h = TO_FIXED(in->muzzle_h);
        cone->vx = dir_x;
        cone->vy = dir_y;
    }
    if (g_fx_style == 1) {
        spawn_shell(in, dir_x, dir_y);
        for (int k = 0; k < 4; k++) {
            fixed x = in->muzzle_x + dir_x * rng_range(4, 12) + rng_range(-2, 2) * 256;
            fixed y = in->muzzle_y + dir_y * rng_range(4, 12) + rng_range(-2, 2) * 256;
            spawn_smoke(x, y, TO_FIXED(in->muzzle_h), dir_x >> 7, dir_y >> 7, rng_range(22, 30));
        }
    } else {
        spawn_arc(in, dir_x, dir_y);
        spawn_recoil_dust(in);
    }
}

// Sniper shot (fire palette, DESIGN.md 6.10): a cross at the muzzle and, when the shot ends at a wall,
// another one there. Hits: sniper_hit_fx.
static void sniper_shot_fx(const WeaponInput *in, fixed end_x, fixed end_y, int end_blocked) {
    FxPart *p = fx_spawn(FXP_CROSS, 4, in->muzzle_x, in->muzzle_y);
    if (p) {
        p->h = TO_FIXED(in->muzzle_h);
        p->size = 6;
    }
    if (!end_blocked) return;
    p = fx_spawn(FXP_CROSS, 4, end_x, end_y);
    if (p) {
        p->h = TO_FIXED(in->muzzle_h);
        p->size = 5;
    }
}

// Sniper hit on an enemy along the ray: a cross (fire palette).
static void sniper_hit_fx(const WeaponInput *in, fixed x, fixed y) {
    FxPart *p = fx_spawn(FXP_CROSS, 4, x, y);
    if (p) {
        p->h = TO_FIXED(in->muzzle_h);
        p->size = 5;
    }
}

// Moves and ages the generic parts once per frame.
static void fx_update(void) {
    for (int i = 0; i < MAX_FX_PARTS; i++) {
        FxPart *p = &s_fx[i];
        if (p->kind == FXP_NONE) continue;
        switch (p->kind) {
        case FXP_SMOKE:
            p->x += p->vx;
            p->y += p->vy;
            p->h += p->vh;
            break;
        case FXP_DUST:
            p->x += p->vx;
            p->y += p->vy;
            p->vx -= p->vx >> 3;
            p->vy -= p->vy >> 3;
            break;
        case FXP_SHELL:
            if (p->aux < 2) {
                p->x += p->vx;
                p->y += p->vy;
                p->h += p->vh;
                p->vh -= 40;                    // gravity
                if (p->h < 0) {
                    p->h = 0;
                    p->aux++;
                    if (p->aux >= 2) {
                        p->vh = 0;
                        p->vx = 0;
                        p->vy = 0;
                    } else {
                        p->vh = -(p->vh >> 1);
                        p->vx = (p->vx * 3) >> 2;
                        p->vy = (p->vy * 3) >> 2;
                    }
                }
            }
            break;
        case FXP_FRAG:
            p->x += p->vx;
            p->y += p->vy;
            p->h += p->vh;
            p->vh -= 48;
            if (p->h < 0) {
                p->h = 0;
                p->vh = 0;
                p->vx = 0;
                p->vy = 0;
            }
            break;
        default:
            break;
        }
        if (--p->life <= 0) p->kind = FXP_NONE;
    }
}

void weapons_request_shake(int amp, int frames) {
    s_shake_amp = amp;
    s_shake_frames = frames > 0 ? frames : 1;
    s_shake_timer = s_shake_frames;
}

static void request_shake(const WeaponTuning *tuning) {
    weapons_request_shake(tuning->shake_amp, tuning->shake_frames);
}

// ---------------------------------------------------------------------------
// Aiming
// ---------------------------------------------------------------------------

// The stylus touches a pixel of the screen. Shots fly at muzzle height, so the
// touched pixel is read as a point at that height: its ground point lies
// `muzzle_h` pixels below it. Returns 0 when the touch is on top of the muzzle.
static int compute_aim(const WeaponInput *in, fixed *dir_x, fixed *dir_y) {
    int ax = in->touch_x - TO_INT(in->muzzle_x);
    int ay = (in->touch_y + in->muzzle_h) - TO_INT(in->muzzle_y);
    uint32_t len = int_sqrt((uint32_t)(ax * ax + GROUND_DY2(ay)));
    if ((int)len < MIN_AIM_DISTANCE) return 0;
    *dir_x = (fixed)((ax * 256) / (int)len);
    *dir_y = (fixed)((ay * 256) / (int)len);
    return 1;
}

// ---------------------------------------------------------------------------
// Firing
// ---------------------------------------------------------------------------

static void shove_enemy(Enemy *e, const WeaponTuning *tuning, fixed dir_x, fixed dir_y) {
    if (!e->active || e->hp <= 0 || tuning->knockback <= 0) return;
    fixed knock = tuning->knockback * g_mods.knock_pct / 100;
    e->knock_vx = (dir_x * knock) >> 8;
    e->knock_vy = (dir_y * knock) >> 8;
    e->stun_timer = tuning->stun_frames * g_mods.knock_pct / 100;
}

// The muzzle hangs off the feet; against a wall it can land inside the bullet-blocking
// cells. Then the shot starts at the player's ground point (the flash stays at the muzzle).
static void shot_origin(const WeaponInput *in, fixed *x, fixed *y) {
    if (bullet_position_is_free(in->muzzle_x, in->muzzle_y)) {
        *x = in->muzzle_x;
        *y = in->muzzle_y;
    } else {
        *x = in->player_x;
        *y = in->player_y;
    }
}

// Length in ground px a straight shot from the muzzle travels before a wall (0..range).
static int ray_length(const WeaponInput *in, fixed dir_x, fixed dir_y, int range) {
    fixed x, y;
    shot_origin(in, &x, &y);
    int d = 0;
    for (; d < range; d += 2) {
        x += dir_x * 2;
        y += dir_y * 2;
        if (!bullet_position_is_free(x, y)) break;
    }
    return d;
}

static void fire_shotgun(const WeaponTuning *tuning, const WeaponInput *in, fixed dir_x, fixed dir_y) {
    fixed origin_x, origin_y;
    shot_origin(in, &origin_x, &origin_y);
    fixed perp_x = -dir_y;
    fixed perp_y = dir_x;
    spawn_shotgun_fx(in, dir_x, dir_y);
    int pellets =(tuning->pellets > 0 ? tuning->pellets : 1) + g_mods.shotgun_pellets;
    int pellet_damage = tuning->damage_per_hit * g_mods.shotgun_damage_pct / 100;
    if (pellet_damage < 1) pellet_damage = 1;
    for (int p_idx = 0; p_idx < pellets; p_idx++) {
        int slot = -1;
        for (int s = 0; s < MAX_PLAYER_PROJECTILES; s++) {
            if (!s_player_projectiles[s].active) { slot = s; break; }
        }
        if (slot < 0) break;

        int spread_idx = (pellets > 1) ? (p_idx - (pellets / 2)) : 0;
        fixed jitter = (fixed)rng_range(-(int)tuning->spread_angle / 4, (int)tuning->spread_angle / 4);
        fixed spread_offset = (spread_idx * tuning->spread_angle) / 2 + jitter;
        PlayerProjectile *proj = &s_player_projectiles[slot];
        proj->active = 1;
        proj->weapon_type = WEAPON_SHOTGUN;
        proj->x = origin_x;
        proj->y = origin_y;
        proj->vx = ((dir_x * tuning->projectile_speed) >> 8) + ((perp_x * spread_offset) >> 8);
        proj->vy = ((dir_y * tuning->projectile_speed) >> 8) + ((perp_y * spread_offset) >> 8);
        proj->height = in->muzzle_h;
        proj->life = tuning->projectile_range;
        proj->max_life = tuning->projectile_range;
        proj->damage = pellet_damage;
        proj->pierce = g_mods.shotgun_pierce;
        proj->hit_mask = 0;
    }
}

// Piercing ray: damages every enemy on the line once and stops at the first wall.
static void fire_sniper(const WeaponTuning *tuning, const WeaponInput *in, fixed dir_x, fixed dir_y,
                        Enemy *enemies, int max_enemies) {
    fixed cur_x, cur_y;
    shot_origin(in, &cur_x, &cur_y);
    fixed step_x = dir_x * 2;
    fixed step_y = dir_y * 2;
    uint32_t hit_mask = 0;
    int end_blocked = 0;

    for (int d = 0; d < tuning->projectile_range; d += 2) {
        fixed nx = cur_x + step_x;
        fixed ny = cur_y + step_y;
        if (!bullet_position_is_free(nx, ny)) { end_blocked = 1; break; }
        cur_x = nx;
        cur_y = ny;

        for (int i = 0; i < max_enemies; i++) {
            Enemy *e = &enemies[i];
            if (!e->active || e->hp <= 0 || (hit_mask & (1u << i))) continue;
            int edx = TO_INT(cur_x - e->x);
            int edy = TO_INT(cur_y - e->y);
            int hit = (e->char_id == CHAR_CHARGER)
                ? body_hit_test_ex(edx, edy, in->muzzle_h, CHARGER_BODY_HIT_CY, CHARGER_BODY_HIT_RX, CHARGER_BODY_HIT_RY)
                : body_hit_test(edx, edy, in->muzzle_h);
            if (hit) {
                hit_mask |= 1u << i;
                spawn_impact(TO_INT(cur_x), TO_INT(cur_y) - in->muzzle_h, -dir_x, -dir_y, 4, 1);
                int sniper_damage = tuning->damage_per_hit * g_mods.sniper_damage_pct / 100;
                enemy_hit(e, sniper_damage < 1 ? 1 : sniper_damage, dir_x * 4, dir_y * 4);
                shove_enemy(e, tuning, dir_x, dir_y);
                sniper_hit_fx(in, cur_x, cur_y);
            }
        }
    }

    s_trail.life = 6;
    s_trail.x0 = TO_INT(in->muzzle_x);
    s_trail.y0 = TO_INT(in->muzzle_y) - in->muzzle_h;
    s_trail.x1 = TO_INT(cur_x);
    s_trail.y1 = TO_INT(cur_y) - in->muzzle_h;
    if (end_blocked) {
        spawn_impact(s_trail.x1, s_trail.y1, -dir_x, -dir_y, 6, 1);
    }
    sniper_shot_fx(in, cur_x, cur_y, end_blocked);
}

static int fire_weapon(PlayerState *player, const WeaponInput *in, fixed dir_x, fixed dir_y,
                       Enemy *enemies, int max_enemies) {
    const WeaponTuning *tuning = &g_weapon_tuning[player->current_weapon];
    s_weapon_cooldown = tuning->fire_cooldown + (player->current_weapon == WEAPON_SHOTGUN ? g_mods.shotgun_cooldown : 0);
    s_last_dir_x = dir_x;
    s_last_dir_y = dir_y;
    if (player->current_weapon == WEAPON_SHOTGUN) {
        fire_shotgun(tuning, in, dir_x, dir_y);
    } else {
        fire_sniper(tuning, in, dir_x, dir_y, enemies, max_enemies);
    }
    spawn_flash(in, dir_x, dir_y);
    request_shake(tuning);
    return WEAPON_RESULT_FIRED;
}

// The aura runs while the sniper charges (AIM_AIMING..AIM_READY) and only then rebuilds. Releasing,
// cancelling, switching weapon or dying stops the rebuilds at once; live flames are cut to a
// few frames more.
static int aura_charging(void) {
    return (s_aim_state == AIM_AIMING || s_aim_state == AIM_READY) &&
           g_player_state.current_weapon == WEAPON_SNIPER && !g_player_state.is_dead;
}

// Random byte from the LCG (high bits).
static int aura_rand8(void) {
    s_aura_seed = s_aura_seed * 1664525u + 1013904223u;
    return (int)(s_aura_seed >> 24);                   // 0..255
}

// Jitter in -amp..amp.
static int aura_jitter(int amp) {
    return ((aura_rand8() * (2 * amp + 1)) >> 8) - amp;
}

// True when a wall may hide part of the points: one span test per row of their box.
static int aura_points_hidden(const int *px, const int *py, int n) {
    int x0 = px[0], x1 = px[0], y0 = py[0], y1 = py[0];
    for (int k = 1; k < n; k++) {
        if (px[k] < x0) x0 = px[k];
        if (px[k] > x1) x1 = px[k];
        if (py[k] < y0) y0 = py[k];
        if (py[k] > y1) y1 = py[k];
    }
    for (int y = y0 - 1; y <= y1 + 1; y++) {
        if (world_span_hidden(y, x0 - 1, x1 + 2, s_aura_y)) return 1;
    }
    return 0;
}

// One flame tongue: anchor on the feet ellipse (step a, radius rx, lifted h px), then nseg steps of 3 px
// that lean outwards and waver: the heading swings two table steps either side of straight up (24), with
// one LCG jitter step. No forks. Depth follows the anchor.
static void aura_flame_make(AuraBolt *b, int a, int rx, int h, int nseg) {
    int ax = s_aura_x + ((s_ell_cos[a] * rx) >> 8);
    int ay = s_aura_y + ((s_ell_sin[a] * rx) >> 9) - h;
    int side = s_ell_cos[a] >= 0 ? 1 : -1;
    int base = (24 + side) & 31;
    int x8 = ax * 256, y8 = ay * 256;
    b->active = 1;
    b->back = s_ell_sin[a] < 0;
    b->age = 0;
    b->life = AURA_BOLT_LIFE;
    b->n = nseg + 1;
    b->px[0] = ax;
    b->py[0] = ay;
    for (int k = 1; k <= nseg; k++) {
        int zig = (k & 1) ? 2 : -2;
        int heading = (base + zig + aura_jitter(1)) & 31;
        x8 += s_ell_cos[heading] * AURA_STEP;
        y8 += s_ell_sin[heading] * AURA_STEP;
        b->px[k] = x8 >> 8;
        b->py[k] = y8 >> 8;
    }
    b->occl = aura_points_hidden(b->px, b->py, b->n);
}

// Rebuilds every flame for the current charge: 6..8 flames from the feet ellipse. Count, length and height
// grow with prog (0..256); READY is prog 256 (all flames, longest and highest). Every slot is cleared first,
// so a rebuild never keeps a shape.
static void aura_regenerate(int prog) {
    for (int i = 0; i < AURA_MAX_BOLTS; i++) s_aura_bolts[i].active = 0;
    s_aura_rot = (s_aura_rot + 1) & 31;
    int count = 6 + ((prog * 2) >> 8);            // 6..8
    int nseg = 3 + ((prog * 2) >> 8);             // 3..5 steps: 9..15 px
    int hmax = 2 + ((prog * 6) >> 8);             // bases 2..8 px high
    for (int i = 0; i < count; i++) {
        int a = (s_aura_rot + i * 4) & 31;        // eight tongues spread round the ellipse
        int h = (aura_rand8() * hmax) >> 8;
        aura_flame_make(&s_aura_bolts[i], a, 9, h, nseg);
    }
}

// Ages a pool entry. When the charge stops it is cut to `keep` more frames. Returns 1 while alive.
static int aura_age(int *age, int *life, int charging, int keep) {
    if (!charging && *life - *age > keep) *life = *age + keep;
    *age += 1;
    return *age < *life;
}

// Free slot of a mote pool, or -1 when full.
static int mote_free(AuraMote *pool, int n) {
    for (int i = 0; i < n; i++)
        if (!pool[i].active) return i;
    return -1;
}

static void mote_set(AuraMote *m, int x, int y, int life, int color) {
    m->active = 1;
    m->x = x;
    m->y = y;
    m->life = life;
    m->color = color;
}

static void ember_spawn(int x, int y, int life, int color) {
    int slot = mote_free(s_embers, ASH_EMBERS);
    if (slot >= 0) mote_set(&s_embers[slot], x, y, life, color);
}

// Floor point of ellipse step a (0..31) at radius r px: 2:1, as the flame anchors.
static void aura_floor_point(int a, int r, int *x, int *y) {
    *x = s_aura_x + ((s_ell_cos[a] * r) >> 8);
    *y = s_aura_y + ((s_ell_sin[a] * r) >> 9);
}

// Thorn crown radius: 12 px open at charge 0, 6 px closed at READY (the spikes reach THORN_LEN beyond).
static int thorn_radius(int prog) {
    return 12 - ((prog * 6) >> 8);
}

// Glow ray length: 4 px at charge 0, GLOW_MAX_LEN at READY.
static int glow_len(int prog) {
    return 4 + ((prog * (GLOW_MAX_LEN - 4)) >> 8);
}

// E: drops fall one px a frame from a random spike tip, one every 4 frames while charging.
static void thorn_update(int charging, int prog) {
    for (int i = 0; i < THORN_DROPS; i++) {
        AuraMote *d = &s_drops[i];
        if (!d->active) continue;
        d->y += 1;
        if (--d->life <= 0) d->active = 0;
    }
    if (charging && (s_aura_tick & 3) == 0) {
        int slot = mote_free(s_drops, THORN_DROPS);
        if (slot >= 0) {
            int a = (2 * (aura_rand8() & 15)) & 31;       // 16 spikes, two table steps apart
            int x, y;
            aura_floor_point(a, thorn_radius(prog) + THORN_LEN, &x, &y);
            mote_set(&s_drops[slot], x, y, 5, FX_RED);
        }
    }
}

static void volute_spawn(void) {
    for (int i = 0; i < ASH_VOLUTES; i++) {
        AshVolute *v = &s_volutes[i];
        if (v->active) continue;
        v->active = 1;
        v->ax = s_aura_cx + ((aura_rand8() & 1) ? -4 : 4);   // from either shoulder
        v->ay = s_aura_cy - 2;
        v->age = 0;
        v->life = 16;
        v->ph = aura_rand8() & 31;
        return;
    }
}

// H: volutes rise one px a frame from the shoulders (3..6 alive, more with the charge); embers come from the
// chest, every 2 frames at high charge and every 4 otherwise; READY throws one burst of 12 gold embers.
static void ash_update(int charging, int ready, int prog) {
    for (int i = 0; i < ASH_VOLUTES; i++) {
        AshVolute *v = &s_volutes[i];
        if (v->active && ++v->age >= v->life) v->active = 0;
    }
    for (int i = 0; i < ASH_EMBERS; i++) {
        AuraMote *e = &s_embers[i];
        if (!e->active) continue;
        e->y -= 1;
        if (--e->life <= 0) e->active = 0;
    }
    if (charging) {
        int target = 3 + ((prog * 3) >> 8);
        int live = 0;
        for (int i = 0; i < ASH_VOLUTES; i++) live += s_volutes[i].active;
        if ((s_aura_tick & 3) == 0 && live < target) volute_spawn();
        int dense = prog >= 180;
        if ((s_aura_tick & (dense ? 1 : 3)) == 0)
            ember_spawn(s_aura_cx + (aura_rand8() & 15) - 8, s_aura_cy - 2, 8, dense ? FX_RED : FX_ORANGE);
    }
    if (ready && !s_aura_was_ready) {
        for (int k = 0; k < 12; k++)
            ember_spawn(s_aura_cx + (aura_rand8() & 31) - 16, s_aura_cy - (aura_rand8() & 7), 12, FX_GOLD);
    }
}

// Per-frame state of G, E and H. Each look clears the pools it does not use, so a style switch never shows
// the motes of the previous one. The glow only turns (no pool).
static void aura_fx_update(int charging, int ready, int prog) {
    s_aura_tick++;
    if (charging) {
        s_aura_prog_live = prog;
        s_aura_fade = AURA_FADE_FRAMES;
    } else if (s_aura_fade > 0) {
        s_aura_fade--;
    }
    if ((s_aura_tick & 3) == 0) s_glow_rot = (s_glow_rot + 1) & 31;
    if (g_aura_style == AURA_STYLE_E) {
        thorn_update(charging, prog);
    } else {
        for (int i = 0; i < THORN_DROPS; i++) s_drops[i].active = 0;
    }
    if (g_aura_style == AURA_STYLE_H) {
        ash_update(charging, ready, prog);
    } else {
        for (int i = 0; i < ASH_EMBERS; i++) s_embers[i].active = 0;
        for (int i = 0; i < ASH_VOLUTES; i++) s_volutes[i].active = 0;
    }
    s_aura_was_ready = ready;
}

// True while G/E/H should be drawn: the charge runs, or the shot is still in its few frames.
static int aura_fx_live(void) {
    return aura_charging() || s_aura_fade > 0;
}

static void aura_update(void) {
    if (s_aura_flash > 0) s_aura_flash--;
    int charging = aura_charging();
    int ready = s_aim_state == AIM_READY;
    int prog = 0;
    if (charging) {
        prog = (s_aim_timer << 8) / s_aura_frames;     // one divide per frame
        if (prog > 256) prog = 256;
    }
    aura_fx_update(charging, ready, prog);
    if (g_aura_style != AURA_STYLE_L) {
        // G, E and H draw their own state: the flames are cut at once, so none is left when switching back.
        for (int i = 0; i < AURA_MAX_BOLTS; i++) s_aura_bolts[i].active = 0;
        s_aura_regen = 0;
        return;
    }
    for (int i = 0; i < AURA_MAX_BOLTS; i++) {
        AuraBolt *b = &s_aura_bolts[i];
        if (b->active && !aura_age(&b->age, &b->life, charging, 2)) b->active = 0;
    }
    // The flames rebuild every 2-3 frames (every 2 at READY); the rebuilds stop with the charge.
    if (charging) {
        if (--s_aura_regen <= 0) {
            s_aura_regen = ready ? 2 : 2 + (aura_rand8() & 1);
            aura_regenerate(prog);
        }
    } else {
        s_aura_regen = 0;
    }
}

// Sniper charge state for the hero's animation: charging = AIM_AIMING or AIM_READY; progress 0..256.
int weapons_aim_charging(void) {
    return s_aim_state == AIM_AIMING || s_aim_state == AIM_READY;
}

int weapons_aim_progress(void) {
    return s_aim_prog;
}

int weapons_can_start_aim(const PlayerState *player) {
    return player->current_weapon == WEAPON_SNIPER && s_weapon_cooldown <= 0 && s_aim_state == AIM_IDLE;
}

int weapons_input(PlayerState *player, const WeaponInput *in, Enemy *enemies, int max_enemies) {
    if (!player || !in || player->is_dead) {
        s_aim_state = AIM_IDLE;
        grenade_cancel();
        return 0;
    }

    if (player->current_weapon == WEAPON_GRENADE) {
        s_aim_state = AIM_IDLE;
        return grenade_input(player, in);
    }

    fixed dir_x = 0, dir_y = 0;
    int has_aim = in->touch_down ? compute_aim(in, &dir_x, &dir_y) : 0;

    if (player->current_weapon == WEAPON_SHOTGUN) {
        // One shot per touch: holding the stylus does not repeat.
        if (in->touch_pressed && has_aim && s_weapon_cooldown <= 0) {
            return fire_weapon(player, in, dir_x, dir_y, enemies, max_enemies);
        }
        return 0;
    }

    // Sniper: touch to aim (the player stops), release to fire once armed.
    int result = 0;
    if (s_aim_state == AIM_IDLE) {
        if (in->touch_pressed && s_weapon_cooldown <= 0) {
            s_aim_state = AIM_AIMING;
            s_aim_timer = 0;
            s_aim_prog = 0;
        }
    }
    if (s_aim_state == AIM_IDLE) return 0;

    if (!in->touch_down) {
        if (s_aim_state == AIM_READY) {
            result = fire_weapon(player, in, s_aim_dir_x, s_aim_dir_y, enemies, max_enemies);
        }
        s_aim_state = AIM_IDLE;
        return result;
    }

    if (s_aim_state == AIM_CANCELLED) return 0;

    // Dragging the stylus back onto the character cancels the shot.
    int bx = in->touch_x - TO_INT(in->player_x);
    int by = in->touch_y - (TO_INT(in->player_y) - in->muzzle_h);
    if (bx * bx + by * by <= SNIPER_CANCEL_RADIUS * SNIPER_CANCEL_RADIUS) {
        s_aim_state = AIM_CANCELLED;
        return 0;
    }

    if (has_aim) {
        s_aim_dir_x = dir_x;
        s_aim_dir_y = dir_y;
    }
    s_aim_muzzle_x = in->muzzle_x;
    s_aim_muzzle_y = in->muzzle_y;
    s_aim_muzzle_h = in->muzzle_h;
    s_aim_len = ray_length(in, s_aim_dir_x, s_aim_dir_y, g_weapon_tuning[WEAPON_SNIPER].projectile_range);
    s_aim_timer++;
    int aim_frames = g_weapon_tuning[WEAPON_SNIPER].aim_min_frames + g_mods.sniper_aim;
    if (aim_frames < 6) aim_frames = 6;
    // Collimation progress: the only divide of the aim laser, once per frame. READY gives 256.
    s_aim_prog = (s_aim_timer << 8) / aim_frames;
    if (s_aim_prog > 256) s_aim_prog = 256;
    s_aura_x = TO_INT(in->player_x);
    s_aura_y = TO_INT(in->player_y);
    s_aura_cx = TO_INT(in->muzzle_x);                 // chest: the muzzle point, at its height
    s_aura_cy = TO_INT(in->muzzle_y) - in->muzzle_h;
    s_aura_frames = aim_frames;
    if (s_aim_timer >= aim_frames && s_aim_state == AIM_AIMING) {
        s_aim_state = AIM_READY;
        s_aura_flash = AURA_FLASH_FRAMES;
    }
    return WEAPON_RESULT_ROOTED;
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

void weapons_notify_kill(void) {
    if (g_mods.kill_resets_shotgun) s_weapon_cooldown = 0;
}

void weapons_update(Enemy *enemies, int max_enemies) {
    if (s_weapon_cooldown > 0) s_weapon_cooldown--;
    if (s_flash.life > 0) s_flash.life--;
    if (s_trail.life > 0) s_trail.life--;
    if (s_shake_timer > 0) { s_shake_timer--; s_shake_tick++; }
    grenade_update(enemies, max_enemies, &g_player_state);

    for (int i = 0; i < MAX_SPARKS; i++) {
        WeaponSpark *s = &s_sparks[i];
        if (!s->active) continue;
        s->x += s->vx;
        s->y += s->vy;
        s->vy += 32;                      // light gravity
        if (--s->life <= 0) s->active = 0;
    }

    fx_update();
    aura_update();

    const WeaponTuning *shotgun = &g_weapon_tuning[WEAPON_SHOTGUN];
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        PlayerProjectile *p = &s_player_projectiles[i];
        if (!p->active) continue;

        if (--p->life <= 0) {
            p->active = 0;
            continue;
        }

        int major = abs_int(p->vx) > abs_int(p->vy) ? abs_int(p->vx) : abs_int(p->vy);
        int steps = (major + 511) / 512;
        if (steps < 1) steps = 1;
        int blocked = 0;
        for (int s = 1; s <= steps; s++) {
            fixed nx = p->x + (p->vx / steps);
            fixed ny = p->y + (p->vy / steps);
            if (!bullet_position_is_free(nx, ny)) { blocked = 1; break; }
            p->x = nx;
            p->y = ny;
        }
        if (blocked) {
            spawn_impact(TO_INT(p->x), TO_INT(p->y) - p->height, -p->vx / 8, -p->vy / 8, 3, 0);
            p->active = 0;
            continue;
        }

        for (int e_idx = 0; e_idx < max_enemies; e_idx++) {
            Enemy *e = &enemies[e_idx];
            if (!e->active || e->hp <= 0 || (p->hit_mask & (1u << e_idx))) continue;
            int dx = TO_INT(p->x - e->x);
            int dy = TO_INT(p->y - e->y);
            if (dx * dx + GROUND_DY2(dy) > ENEMY_HIT_RADIUS * ENEMY_HIT_RADIUS) continue;

            // Damage falls off from 100% at the muzzle to 25% at the end of the range.
            int damage = (p->damage * (64 + (192 * p->life) / p->max_life)) >> 8;
            if (damage < 1) damage = 1;
            spawn_impact(TO_INT(p->x), TO_INT(p->y) - p->height, -p->vx / 8, -p->vy / 8, 3, 0);
            enemy_hit(e, damage, p->vx, p->vy);
            fixed len_dir_x = p->vx * 256 / shotgun->projectile_speed;
            fixed len_dir_y = p->vy * 256 / shotgun->projectile_speed;
            shove_enemy(e, shotgun, len_dir_x, len_dir_y);
            if (p->pierce > 0) {            // "perforantes": the pellet goes on through
                p->pierce--;
                p->hit_mask |= 1u << e_idx;
                continue;
            }
            p->active = 0;
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Rendering: procedural strokes. render_screen() calls weapons_render() once per screen,
// so the aim laser, pellets, trail, flash and sparks show on both of them.
// ---------------------------------------------------------------------------

typedef struct {
    uint16_t *p16;        // screen page (BGR555 with the alpha bit)
} FxTarget;

static inline void put_px(const FxTarget *t, int x, int y, int color) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
    t->p16[y * SCREEN_W + x] = s_fx_rgb[color] | BIT(15);
    dirty_row(y, x, x + 1);
}

// Draws a one-pixel Bresenham line in screen space.
static void draw_line(const FxTarget *t, int x0, int y0, int x1, int y1, int color) {
    // Nothing of the line can reach this screen: skip the walk.
    if ((x0 < 0 && x1 < 0) || (x0 >= SCREEN_W && x1 >= SCREEN_W) ||
        (y0 < 0 && y1 < 0) || (y0 >= SCREEN_H && y1 >= SCREEN_H)) return;
    int dx = abs_int(x1 - x0), dy = abs_int(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = (dx > dy ? dx : -dy) / 2;
    for (;;) {
        put_px(t, x0, y0, color);
        if (x0 == x1 && y0 == y1) break;
        int e2 = err;
        if (e2 > -dx) { err -= dy; x0 += sx; }
        if (e2 < dy) { err += dx; y0 += sy; }
    }
}

// Screen point of the aim ray at distance d (ground px) from the muzzle.
static void aim_point(int d, int cam_x, int cam_y, int *x, int *y) {
    *x = TO_INT(s_aim_muzzle_x + s_aim_dir_x * d) - cam_x;
    *y = TO_INT(s_aim_muzzle_y + s_aim_dir_y * d) - s_aim_muzzle_h - cam_y;
}

// Filled disc with an optional checkerboard rim (no transparency on the DS).
static void draw_disc(const FxTarget *t, int cx, int cy, int r, int color, int dither) {
    int rr = r * r;
    int inner = (r - 1) * (r - 1);
    for (int dy = -r; dy <= r; dy++) {
        for (int dx = -r; dx <= r; dx++) {
            int d2 = dx * dx + dy * dy;
            if (d2 > rr) continue;
            if (dither && d2 > inner && ((cx + dx + cy + dy) & 1)) continue;
            put_px(t, cx + dx, cy + dy, color);
        }
    }
}

static void draw_cross(const FxTarget *t, int cx, int cy, int arm, int color) {
    draw_line(t, cx - arm, cy, cx + arm, cy, color);
    draw_line(t, cx, cy - arm, cx, cy + arm, color);
}

// Shotgun cone: a wedge that widens from the muzzle; age 0 white, 1 yellow, 2 orange.
static void draw_cone(const FxTarget *t, int ox, int oy, fixed dir_x, fixed dir_y, int idx, int wide) {
    static const int len_b[3] = {14, 12, 8}, half_b[3] = {12, 10, 7};
    static const int len_c[3] = {20, 17, 12}, half_c[3] = {16, 13, 9};
    if (idx < 0 || idx > 2) return;
    int len = wide ? len_c[idx] : len_b[idx];
    int half = wide ? half_c[idx] : half_b[idx];
    int color = idx == 0 ? FX_WHITE : idx == 1 ? FX_YELLOW : FX_ORANGE;
    for (int k = 1; k <= len; k++) {
        int cx = ox + ((dir_x * k) >> 8);
        int cy = oy + ((dir_y * k) >> 8);
        int w = (half * k) >> 4;        // grows toward the tip, about half-width at the end
        int sx = (-dir_y * w) >> 8;
        int sy = (dir_x * w) >> 8;
        draw_line(t, cx - sx, cy - sy, cx + sx, cy + sy, color);
    }
}

// Collimation band: at each ray point paint offsets -w..w across the aim. The centre takes `centre`,
// the inner offsets `inner`, and the rim (|o| == w) only on a checkerboard of `rim`.
static void aim_band(const FxTarget *t, int px, int py, int w, int centre, int inner, int rim) {
    for (int o = -w; o <= w; o++) {
        int x = px + ((s_aim_dir_y * o) >> 8);
        int y = py - ((s_aim_dir_x * o) >> 8);
        if (o == 0) put_px(t, x, y, centre);
        else if (o == w || o == -w) {
            if (((x + y) & 1) == 0) put_px(t, x, y, rim);
        } else put_px(t, x, y, inner);
    }
}

// Sniper fuego (DESIGN.md 6.10, the only look): the collimated band starts from the A1 band: blood red inside,
// a dithered orange rim, the centre red and orange past 70 %. Armed, the line is 1 px and flickers white and
// yellow. While charging it also throws embers off the rim: 8..24 per frame (cap 32), each rising 1 px a frame
// for 7 frames. No division: a hash per ember gives its distance along the ray, the lifecycle comes from the
// frame counter.
static void render_aim_line(const FxTarget *t, int cam_x, int cam_y) {
    if (s_aim_state != AIM_AIMING && s_aim_state != AIM_READY) return;
    int ready = s_aim_state == AIM_READY;
    int w = (6 * (256 - s_aim_prog)) >> 8;          // lateral half-width in px (6 at 0 %, 0 when armed)

    if (ready) {
        for (int d = 1; d <= s_aim_len; d++) {
            int px, py;
            aim_point(d, cam_x, cam_y, &px, &py);
            put_px(t, px, py, ((s_aim_timer >> 1) & 1) ? FX_WHITE : FX_YELLOW);
        }
        return;
    }
    int centre = s_aim_prog >= 180 ? FX_ORANGE : FX_RED;
    for (int d = 1; d <= s_aim_len; d++) {
        int px, py;
        aim_point(d, cam_x, cam_y, &px, &py);
        aim_band(t, px, py, w, centre, FX_BLOOD, FX_ORANGE);
    }
    if (s_aim_len <= 0 || w <= 0) return;
    int n = 8 + ((s_aim_prog * 16) >> 8);             // 8..24, under the cap of 32
    for (int i = 0; i < n; i++) {
        int tt = s_aim_timer + i * 5;                  // embers are staggered by 5 frames
        int age = tt & 7;                              // frames alive: it rises 1 px each
        if (age == 7) continue;                        // gone
        uint32_t h = ((uint32_t)(tt >> 3) * 2654435761u + (uint32_t)i * 2246822519u) * 1664525u + 1013904223u;
        int d = 1 + (int)(((h >> 16) * (uint32_t)s_aim_len) >> 16);      // 1..len along the ray
        int o = (h & 1) ? w : -w;                      // off the rim of the band
        int px, py;
        aim_point(d, cam_x, cam_y, &px, &py);
        int x = px + ((s_aim_dir_y * o) >> 8);
        int y = py - ((s_aim_dir_x * o) >> 8) - age;
        put_px(t, x, y, age < 3 ? FX_GOLD : age < 6 ? FX_ORANGE : FX_RED);
    }
}

// Parts with volume, drawn over the sprites: cones, smoke, shells, dust, crosses,
// fragments. FXP_ARC lies on the floor and are drawn by render_fx_ground.
// age = frames since spawn (1 on the first frame drawn).
static void render_fx_parts(const FxTarget *t, int cam_x, int cam_y) {
    for (int i = 0; i < MAX_FX_PARTS; i++) {
        const FxPart *p = &s_fx[i];
        if (p->kind == FXP_NONE) continue;
        int age = p->max_life - p->life;
        int sx = TO_INT(p->x) - cam_x;
        int sy = TO_INT(p->y) - TO_INT(p->h) - cam_y;
        switch (p->kind) {
        case FXP_CONE:
            draw_cone(t, sx, sy, p->vx, p->vy, age - 1, g_fx_style == 2);
            break;
        case FXP_SMOKE: {
            // Light grey while young, dark and dithered at the rim when old.
            int late = age * 3 >= p->max_life * 2;
            int col = age * 3 < p->max_life ? FX_SMOKE_A : late ? FX_SMOKE_C : FX_SMOKE_B;
            draw_disc(t, sx, sy, p->size + (age >> 3), col, late);
            break;
        }
        case FXP_SHELL:
            put_px(t, sx, sy, FX_BRASS);
            put_px(t, sx + 1, sy, FX_BRASS);
            break;
        case FXP_DUST: {
            int late = age * 2 > p->max_life;
            int spread = p->size + (age >> 1);
            for (int k = 0; k < 6; k++) {
                int x = sx + ((s_dust_dx[k] * spread) >> 1);
                int y = sy + ((s_dust_dy[k] * spread) >> 1);
                if (late && ((x + y) & 1)) continue;
                put_px(t, x, y, late ? FX_DUST_B : FX_DUST_A);
            }
            break;
        }
        case FXP_CROSS: {
            int arm = p->size - (age - 1);
            if (arm < 1) arm = 1;
            int col = age == 1 ? FX_WHITE : age == 2 ? FX_GOLD : FX_ORANGE;
            draw_cross(t, sx, sy, arm, col);
            break;
        }
        case FXP_FRAG:
            put_px(t, sx, sy, age <= 4 ? FX_SPARK_A : age <= 8 ? FX_SPARK_B : FX_SPARK_C);
            break;
        default:
            break;
        }
    }
}

// Sniper trail (DESIGN.md 6.10, fuego): 5 px, white core, yellow then orange on each side, cooling; in its
// last two frames red embers stay along the line (16 points at most).
static void render_trail(const FxTarget *t, int cam_x, int cam_y) {
    int x0 = s_trail.x0 - cam_x, y0 = s_trail.y0 - cam_y;
    int x1 = s_trail.x1 - cam_x, y1 = s_trail.y1 - cam_y;
    int life = s_trail.life;
    int core = life >= 4 ? FX_WHITE : life >= 2 ? FX_YELLOW : FX_ORANGE;
    int side = life >= 4 ? FX_YELLOW : FX_ORANGE;
    if (life >= 4) {
        draw_line(t, x0, y0 - 2, x1, y1 - 2, FX_ORANGE);
        draw_line(t, x0, y0 + 2, x1, y1 + 2, FX_ORANGE);
    }
    if (life >= 2) {
        draw_line(t, x0, y0 - 1, x1, y1 - 1, side);
        draw_line(t, x0, y0 + 1, x1, y1 + 1, side);
    }
    draw_line(t, x0, y0, x1, y1, core);
    if (life <= 2) {
        int dx = x1 - x0, dy = y1 - y0;
        for (int i = 0; i < 16; i++) {
            if (((i + life) & 1) != 0) continue;
            int px = x0 + ((dx * i) >> 4);
            int py = y0 + ((dy * i) >> 4);
            put_px(t, px, py - ((i >> 2) & 1), FX_RED);
        }
    }
}

// Pellets: A short streak (4 px) cooling to blue; B bright head with a dotted tail;
// C long luminous streak (18 px) with a bright front.
static void render_pellets(const FxTarget *t, int cam_x, int cam_y) {
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        PlayerProjectile *p = &s_player_projectiles[i];
        if (!p->active) continue;
        int hx = TO_INT(p->x) - cam_x;
        int hy = TO_INT(p->y) - p->height - cam_y;
        if (g_fx_style == 0) {
            int tx = hx - ((p->vx * 11) >> 12), ty = hy - ((p->vy * 11) >> 12);
            int mx = hx - ((p->vx * 11) >> 13), my = hy - ((p->vy * 11) >> 13);
            draw_line(t, tx, ty, mx, my, FX_TAIL);
            draw_line(t, mx, my, hx, hy, FX_COOL);
            put_px(t, hx, hy, FX_PELLET_HEAD);
        } else if (g_fx_style == 1) {
            for (int k = 1; k <= 3; k++) {
                put_px(t, hx - ((p->vx * k) >> 9), hy - ((p->vy * k) >> 9), FX_TAIL);
            }
            put_px(t, hx, hy, FX_PELLET_HEAD);
            put_px(t, hx + 1, hy, FX_PELLET_HEAD);
        } else {
            int tx = hx - ((p->vx * 3) >> 8), ty = hy - ((p->vy * 3) >> 8);
            int mx = hx - (p->vx >> 8), my = hy - (p->vy >> 8);
            draw_line(t, tx, ty, mx, my, FX_TAIL);
            draw_line(t, mx, my, hx, hy, FX_COOL);
            put_px(t, hx, hy, FX_PELLET_HEAD);
        }
    }
}

static void render_flash(const FxTarget *t, int cam_x, int cam_y) {
    if (s_flash.life <= 0) return;
    int x = s_flash.x - cam_x, y = s_flash.y - cam_y;
    int reach = 2 + s_flash.life * 2;                 // 8, 6, 4 px as it fades
    for (int k = 1; k <= reach; k++) {
        int px = x + ((s_flash.dir_x * k) >> 8);
        int py = y + ((s_flash.dir_y * k) >> 8);
        put_px(t, px, py, k * 2 > reach ? FX_COOL : FX_HOT);
    }
    put_px(t, x, y, FX_CORE);
    put_px(t, x - 1, y, FX_HOT);
    put_px(t, x + 1, y, FX_HOT);
    put_px(t, x, y - 1, FX_HOT);
    put_px(t, x, y + 1, FX_HOT);
}

static void render_fx(const FxTarget *t, int cam_x, int cam_y) {
    render_aim_line(t, cam_x, cam_y);

    if (s_trail.life > 0) render_trail(t, cam_x, cam_y);
    render_pellets(t, cam_x, cam_y);
    render_fx_parts(t, cam_x, cam_y);
    render_flash(t, cam_x, cam_y);

    // Impact sparks: two-pixel strokes along their velocity, cooling as they die.
    for (int i = 0; i < MAX_SPARKS; i++) {
        WeaponSpark *s = &s_sparks[i];
        if (!s->active) continue;
        int age = (s->life * 3) / s->max_life;        // 2 young .. 0 old
        int color = s->sniper ? (age >= 2 ? FX_GOLD : age == 1 ? FX_ORANGE : FX_ASH)
                              : (age >= 2 ? FX_SPARK_A : age == 1 ? FX_SPARK_B : FX_SPARK_C);
        int hx = TO_INT(s->x) - cam_x, hy = TO_INT(s->y) - cam_y;
        put_px(t, hx, hy, color);
        put_px(t, hx - (s->vx > 96) + (s->vx < -96), hy - (s->vy > 96) + (s->vy < -96), color);
    }
}

// Ground parts (DESIGN.md 4.9): 2:1 ellipses on the floor, drawn on the floor pass under the
// shadows and sprites. Their x,y is already the ground world point (they never carry height),
// and groundfx applies the camera and the wall test itself.
static void render_fx_ground(const GroundTarget *g) {
    for (int i = 0; i < MAX_FX_PARTS; i++) {
        const FxPart *p = &s_fx[i];
        if (p->kind != FXP_ARC) continue;
        int age = p->max_life - p->life;
        int wx = TO_INT(p->x);
        int wy = TO_INT(p->y);
        int r = 4 + 4 * age;
        uint16_t col = s_fx_rgb[age <= 2 ? FX_WHITE : age <= 4 ? FX_CYAN : FX_CYAN_DIM];
        // 9 steps of the 32-step table centred on the shot direction. The window is split
        // in two when it wraps past step 32, so no call gets a1 > 32.
        int a0 = (p->aux - 4) & 31;
        int a1 = a0 + 9;
        if (a1 <= 32) {
            gfx_ground_arc(g, wx, wy, r, a0, a1, col, 1);
        } else {
            gfx_ground_arc(g, wx, wy, r, a0, 32, col, 1);
            gfx_ground_arc(g, wx, wy, r, 0, a1 - 32, col, 1);
        }
    }
}

// One aura pixel at world px (wx, wy). Off-screen pixels are skipped; with `occl` so are the
// pixels a wall hides (depth = the feet, as for the other actor FX).
static void aura_px(const FxTarget *t, int wx, int wy, int cam_x, int cam_y, int color, int occl) {
    int sx = wx - cam_x, sy = wy - cam_y;
    if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) return;
    if (occl && world_pixel_hidden(wx, wy, s_aura_y)) return;
    put_px(t, sx, sy, color);
}

// One-pixel Bresenham segment between two world points (no division, hard step cap). With alt >= 0
// every other pixel of the segment takes the colour alt (flames: yellow with orange).
static void aura_seg(const FxTarget *t, int x0, int y0, int x1, int y1, int cam_x, int cam_y,
                     int color, int alt, int occl) {
    int dx = abs_int(x1 - x0), dy = abs_int(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    // dx >> 1 and -(dy >> 1) keep the error term symmetric; a plain floor shift of -dy skews it and
    // the walk can run past its end point forever.
    int err = dx > dy ? dx >> 1 : -(dy >> 1);
    for (int n = 0; n < AURA_SEG_MAX_STEPS; n++) {
        aura_px(t, x0, y0, cam_x, cam_y, (alt >= 0 && (n & 1)) ? alt : color, occl);
        if (x0 == x1 && y0 == y1) break;
        int e2 = err;
        if (e2 > -dx) { err -= dy; x0 += sx; }
        if (e2 < dy) { err += dx; y0 += sy; }
    }
}

// One F2 flame. Steps 0-1 are the base, 2 px wide (a parallel orange line one px to one side, the yellow
// core on top); steps 2-3 are orange with a red dither; the tip is red with an orange dither.
static void aura_flame_draw(const FxTarget *t, const AuraBolt *b, int cam_x, int cam_y) {
    for (int k = 0; k + 1 < b->n; k++) {
        int x0 = b->px[k], y0 = b->py[k], x1 = b->px[k + 1], y1 = b->py[k + 1];
        if (k < 2) {
            int steep = abs_int(y1 - y0) > abs_int(x1 - x0);
            int ox = steep, oy = !steep;              // one px across the stroke
            aura_seg(t, x0 + ox, y0 + oy, x1 + ox, y1 + oy, cam_x, cam_y, FX_ORANGE, -1, b->occl);
            aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_YELLOW, FX_ORANGE, b->occl);
        } else if (k < 4) {
            aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_ORANGE, FX_RED, b->occl);
        } else {
            aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_RED, FX_ORANGE, b->occl);
        }
    }
}

// Draws the flames of one depth: behind = 1 for the floor pass (under the sprites), 0 for the front pass
// (over them).
static void aura_draw_pass(const FxTarget *t, int cam_x, int cam_y, int behind) {
    for (int i = 0; i < AURA_MAX_BOLTS; i++) {
        const AuraBolt *b = &s_aura_bolts[i];
        if (!b->active || b->back != behind) continue;
        aura_flame_draw(t, b, cam_x, cam_y);
    }
}

// G, glow: 12 rays from the chest, alternately long and short (2/3), tips white. At READY the rays are at
// full length and blink white every 2 frames. Floor pass: the body covers them.
static void glow_draw(const FxTarget *t, int cam_x, int cam_y, int prog) {
    static const uint8_t step[GLOW_RAYS] = { 0, 3, 5, 8, 11, 13, 16, 19, 21, 24, 27, 29 };   // 12 of 32 steps
    int len = glow_len(prog);
    int shortl = (len * 171) >> 8;
    int blink = s_aim_state == AIM_READY && ((s_aim_timer >> 1) & 1);
    for (int i = 0; i < GLOW_RAYS; i++) {
        int a = (s_glow_rot + step[i]) & 31;
        int l = (i & 1) ? shortl : len;
        int ex = s_aura_cx + ((s_ell_cos[a] * l) >> 8);
        int ey = s_aura_cy + ((s_ell_sin[a] * l) >> 8);     // upright: no 2:1 squash
        aura_seg(t, s_aura_cx, s_aura_cy, ex, ey, cam_x, cam_y, blink ? FX_WHITE : FX_GOLD, -1, 1);
        aura_px(t, ex, ey, cam_x, cam_y, FX_WHITE, 1);
    }
}

// E, thorn crown: 16 spikes of 3 px, outwards from the closing ellipse, black with dark red; the drops fall
// red from the tips. Floor pass.
static void thorn_draw(const FxTarget *t, int cam_x, int cam_y, int prog) {
    int r = thorn_radius(prog);
    for (int i = 0; i < THORN_SPIKES; i++) {
        int a = (2 * i) & 31;
        int x0, y0, x1, y1;
        aura_floor_point(a, r, &x0, &y0);
        aura_floor_point(a, r + THORN_LEN, &x1, &y1);
        aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_BLACK, FX_BLOOD, 1);
    }
    for (int i = 0; i < THORN_DROPS; i++) {
        const AuraMote *d = &s_drops[i];
        if (d->active) aura_px(t, d->x, d->y, cam_x, cam_y, d->color, 1);
    }
}

// H, ash: grey volutes 2..4 px wide that widen as they rise, with a dithered edge; embers over them.
// Front pass: they are drawn over the body (no back half).
static void ash_draw(const FxTarget *t, int cam_x, int cam_y, int prog) {
    int core_col = prog >= 180 ? FX_SMOKE_C : FX_SMOKE_B;
    for (int i = 0; i < ASH_VOLUTES; i++) {
        const AshVolute *v = &s_volutes[i];
        if (!v->active) continue;
        int x = v->ax + (((s_ell_sin[(v->ph + v->age) & 31]) * 3) >> 8);   // sway +-3 px
        int y = v->ay - v->age;
        int w = 2 + (v->age >> 3);
        if (w > 4) w = 4;
        int core = v->age < 3 ? FX_SMOKE_A : core_col;
        for (int r = 0; r < 2; r++) {
            for (int k = 0; k < w; k++) {
                int edge = (k == 0 || k == w - 1);
                int col = (edge && ((k + r) & 1)) ? FX_SMOKE_A : core;
                aura_px(t, x + k, y - r, cam_x, cam_y, col, 1);
            }
        }
    }
    for (int i = 0; i < ASH_EMBERS; i++) {
        const AuraMote *e = &s_embers[i];
        if (e->active) aura_px(t, e->x, e->y, cam_x, cam_y, e->color, 1);
    }
}

void weapons_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    GroundTarget ground = { buffer, cam_x, cam_y };
    grenade_render_floor(&ground);
    render_fx_ground(&ground);
    // READY flash: a 2:1 ring on the floor around the feet, under the actors. White on the first frame, then gold.
    if (s_aura_flash > 0 && s_aim_state == AIM_READY) {
        int ring = s_aura_flash == AURA_FLASH_FRAMES ? FX_WHITE : FX_GOLD;
        gfx_ground_ring(&ground, s_aura_x, s_aura_y, 12, s_fx_rgb[ring], 0);
    }
    // Look E at READY: a thin red ring round the closed crown.
    if (s_aim_state == AIM_READY && g_aura_style == AURA_STYLE_E)
        gfx_ground_ring(&ground, s_aura_x, s_aura_y, 7, s_fx_rgb[FX_RED], 0);
    FxTarget target = { buffer };
    aura_draw_pass(&target, cam_x, cam_y, 1);         // style L: arcs behind the body
    if (aura_fx_live()) {
        if (g_aura_style == AURA_STYLE_G) glow_draw(&target, cam_x, cam_y, s_aura_prog_live);
        if (g_aura_style == AURA_STYLE_E) thorn_draw(&target, cam_x, cam_y, s_aura_prog_live);
    }
}

void weapons_render_light(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    GroundTarget ground = { buffer, cam_x, cam_y };
    grenade_render_light(&ground);
}

void weapons_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    FxTarget target = { buffer };
    render_fx(&target, cam_x, cam_y);
    aura_draw_pass(&target, cam_x, cam_y, 0);         // style L: arcs in front of the body
    if (aura_fx_live() && g_aura_style == AURA_STYLE_H) ash_draw(&target, cam_x, cam_y, s_aura_prog_live);
    grenade_render(buffer, cam_x, cam_y);
}
