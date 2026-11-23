#include "weapons.h"
#include "gameplay.h"
#include "modifiers.h"
#include "upgrades.h"
#include "groundfx.h"
#include "hitvolume.h"
#include "sfx.h"
#include "dmg_numbers.h"
#include "arpg.h"
#include "arpg_inv.h"
#include "allies.h"
#if ENCOUNTERS_PROTO
#include "encounters_act1.h"
#endif

/* TUNABLE-PLACEHOLDER: Player Weapon Tuning Table (Fixed-Point 8.8). */
const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES] = {
    [WEAPON_SNIPER] = {
        .name = "SNIPER",
        .damage_per_hit = ARPG_RAY_DAMAGE,   /* ARPG: 100 (was 150, arpg.h) */
        .pellets = 1,
        .fire_cooldown = 0,         /* no recovery: a new press charges at once (DESIGN.md 6.10, 6.12.10) */
        .projectile_speed = 0,
        .projectile_range = 110,    /* base ray length in ground px (DESIGN.md 6.12.10); Alcance adds g_mods.sniper_range */
        .spread_angle = 0,
        .aim_min_frames = 48,       /* 0.8 s before the shot is armed; Prisa -10 per rank down to 8 */
        .knockback = 0,
        .stun_frames = 0,
        .recoil = 0,
        .shake_amp = 3,
        .shake_frames = 8
    }
};

int g_fx_style = 0;

char weapons_fx_style_letter(void) {
    return (char)('A' + (g_fx_style % FX_STYLE_COUNT));
}

// Charge auras are the look of the relics (DESIGN.md 6.12.8): a bitmask of AURA_STYLE_* bits, rebuilt every
// frame from the relics in weapons_update. The sandbox can force extra bits through g_aura_debug_mask.
int g_aura_debug_mask = 0;
static int s_aura_mask = 0;

// The one place that maps relics to their look (DESIGN.md 6.12.6, column "Como se ve"). Auras: Cilicio = E (thorn
// ring), Sed de Ceniza = H (ash), Viatico = G (glow). Corazon Flagelado = L (flames) only while its instant charge
// is pending: part C raises that bit through g_aura_force_mask. Llama Votiva (flaming aim line, render_aim_line)
// and Lanza de Longinos (no look of its own: the beam just pierces everyone) have no aura. Auto de Fe: spark burst in fire_sniper.
int g_aura_force_mask = 0;
static int relic_aura_mask(void) {
    int m = 0;
    if (upgrades_has_relic(RELIC_CILICIO))    m |= 1 << AURA_STYLE_E;
    if (upgrades_has_relic(RELIC_SED_CENIZA)) m |= 1 << AURA_STYLE_H;
    if (upgrades_has_relic(RELIC_VIATICO))    m |= 1 << AURA_STYLE_G;
    return m;
}

static inline int aura_on(int style) {
    return (s_aura_mask >> style) & 1;
}

// HUD debug letter: '-' without auras, the letter of the only one, '+' when several are stacked.
char weapons_aura_style_letter(void) {
    static const char letters[AURA_STYLE_COUNT] = {'L', 'G', 'E', 'H'};
    if (s_aura_mask == 0) return '-';
    for (int i = 0; i < AURA_STYLE_COUNT; i++)
        if (s_aura_mask == (1 << i)) return letters[i];
    return '+';
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

static WeaponSpark s_sparks[MAX_SPARKS];
static MuzzleFlash s_flash;
static SniperTrail s_trail;

// Generic effect parts (sniper crosses and impact fragments).
// One shared pool of 32 slots; kind FXP_NONE = free slot.
#define MAX_FX_PARTS 32
enum {
    FXP_NONE = 0,
    FXP_CROSS,      // sniper cross flash, muzzle and hits (fire palette); size = arm
    FXP_FRAG        // fragment with gravity (sniper impacts)
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
    FX_SPARK_A, FX_SPARK_B, FX_SPARK_C,            // impact sparks, hot to cold
    FX_GOLD, FX_BLOOD, FX_RED, FX_ASH,             // legacy fire palette
    FX_BLACK,                                      // thorn spikes (aura E)
    // Sacred Heart desaturated/prerendered palette (DESIGN.md 6.10)
    FX_SH_IVORY, FX_SH_GOLD, FX_SH_AMBER,          // warm ivory core, antique gold, amber glow
    FX_SH_EMBER, FX_SH_CRIMSON, FX_SH_DEEP,        // terracotta ember, sacred crimson, deep blood
    FX_SH_ASH_A, FX_SH_ASH_B, FX_SH_ASH_C,         // warm umber ash, light to dark
    FX_SH_SMOKE_L, FX_SH_SMOKE_M,                  // warm ash greys lighter than the floor (burn C smoke)
    FX_NUM_COLORS
};

static const uint16_t s_fx_rgb[FX_NUM_COLORS] = {
    RGB15(31, 31, 24), RGB15(31, 24, 6), RGB15(28, 12, 2),
    RGB15(31, 30, 18), RGB15(31, 18, 3), RGB15(20, 5, 2),
    RGB15(31, 21, 4),                              // FX_GOLD
    RGB15(15, 2, 2),                               // FX_BLOOD
    RGB15(28, 5, 2),                               // FX_RED
    RGB15(9, 8, 8),                                // FX_ASH
    RGB15(4, 3, 3),                                // FX_BLACK (warm iron)
    RGB15(29, 25, 19),                             // FX_SH_IVORY
    RGB15(27, 20, 11),                             // FX_SH_GOLD
    RGB15(24, 15, 7),                              // FX_SH_AMBER
    RGB15(20, 9, 5),                               // FX_SH_EMBER
    RGB15(15, 5, 4),                               // FX_SH_CRIMSON
    RGB15(9, 3, 3),                                // FX_SH_DEEP
    RGB15(15, 13, 12), RGB15(10, 9, 8), RGB15(6, 5, 5), // FX_SH_ASH_A..C
    RGB15(22, 20, 18), RGB15(18, 16, 14)               // FX_SH_SMOKE_L, FX_SH_SMOKE_M
};

// Part C relics (DESIGN.md 6.12.6, 6.12.10). The hero position is given once a frame by main.
#define CILICIO_PERIOD 10                 // [TUNABLE-PLACEHOLDER] frames between layers of the Cilicio ring
#define FLAGELADO_RADIUS 48               // [TUNABLE-PLACEHOLDER] ground px
#define FLAGELADO_DAMAGE 100              // [TUNABLE-PLACEHOLDER] fire damage
#define FLAGELADO_LAYERS 3                // [TUNABLE-PLACEHOLDER]
#define VIATICO_RADIUS 40                 // [TUNABLE-PLACEHOLDER] ground px: kills this close count
#define VIATICO_PCT 20                    // [TUNABLE-PLACEHOLDER] /256 (~8 %): chance to steal a heart when the beam kills
#define VIATICO_PCT_NEAR 41               // [TUNABLE-PLACEHOLDER] /256 (~16 %): same, victim within VIATICO_RADIUS of the hero
#define VIATICO_CHEST 20                  // px above the hero's feet where the siphon arrives
static int s_hero_x = 0, s_hero_y = 0;    // hero feet, world px
static int s_hit_pending = 0;             // Corazon Flagelado: a hit landed, the wave is resolved in weapons_update
static int s_instant_pending = 0;         // Corazon Flagelado: the next sniper charge is READY on press
static int s_cilicio_tick = 0;
static int s_llaga_missing = 0;           // hearts below 5 while Llaga Abierta is owned (0 = off); drives its three looks

static inline int lc(int c) { return c; }   // the beam keeps its colours: Llaga Abierta no longer touches the laser

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

// Quemado visual (DESIGN.md 6.12.8, variant A): a pool of its own, separate from the impact sparks. Burning
// enemies throw rising embers (faster with more layers) and, at the layer cap, a flame tongue over the head.
// Martirio Contagioso adds a short ground ring and a burst of embers per explosion. All muted FX_SH_* colours.
#define MAX_BURN_EMBERS 128
#define BURN_EMBER_SOFT 80                // above this many live, burning enemies thin their embers (24 burning at once)
#define MAX_OCC_BODIES 24
#define MAX_BURN_RINGS 12
#define MAX_FLARES 10
#define MAX_BURN_MARKS 12
#define BURN_RING_FRAMES 10
#define MARTIRIO_QUEUE 16
#define MARTIRIO_PER_FRAME 4              // [TUNABLE-PLACEHOLDER] explosions resolved per frame (DESIGN.md 6.12.10)
#define MARTIRIO_RADIUS 32                // [TUNABLE-PLACEHOLDER] ground px
#define MARTIRIO_DAMAGE 60                // [TUNABLE-PLACEHOLDER] fire damage
#define MARTIRIO_LAYERS 2                 // [TUNABLE-PLACEHOLDER]
#define VOTIVA_FRAMES 8                   // [TUNABLE-PLACEHOLDER] frames of contact per layer
typedef struct {
    uint8_t active, kind, life, max_life;     // kind 0 = ember, 1 = flame tongue (vx = height), 2 = unused, 3 = smoke, 4 = A ember, 5 = A big ember, 6 = Llaga B blood drop
    uint8_t back;                             // ember on a body's far side: floor pass, the sprite hides it
    int8_t vx;
    int x, y, depth;                          // world px (height applied); depth = feet y for the wall test
} BurnEmber;
typedef struct { uint8_t active, age, rmax, kind; int x, y; } BurnRing;   // rmax: final radius, ground px; kind: RING_*
enum { RING_PLAIN = 0, RING_MARTIRIO, RING_FLAGELADO };
// Short effects: Auto de Fe (A burst, B pyre, C cross) and the Martirio column (C).
enum { FL_COLUMN = 0, FL_BURST, FL_KINDS };
static const uint8_t s_flare_life[FL_KINDS] = { 10, 14 };
typedef struct { uint8_t active, kind, age, aux; int x, y, depth; int16_t dx, dy; } Flare;   // FL_BURST: dx, dy = beam direction on screen, 8.8
// Auto de Fe B / C (DESIGN.md 6.12.12): the burn of an enemy hit by Auto de Fe is consumed, not erased. The enemy's own
// fire surges over the body and evaporates upward while the sprite tint fades back (B from burn A, C from burn B).
#define MAX_CONSUME 4
#define CONSUME_FRAMES 28
typedef struct { uint8_t active, age, idx, layers; int x, y; int8_t torso, head, hw; } Consume;
static Consume s_consume[MAX_CONSUME];
static int s_burn_force = -1;             // evidence hook: -1 follows the design variant, 0 / 1 force burn style A / B (g_abc_debug 64 / 128)
static int s_viatico_force = 0;           // evidence hook: the next beam kill steals a heart for sure (g_abc_debug 16)
static inline int burn_style(void) { return s_burn_force >= 0 ? s_burn_force : (g_design_variant == 1); }   // 0 = A embers and tongues, 1 = B ring of flames
// Viatico siphon (DESIGN.md 6.12.6): from the victim to the hero's chest along a curve; A thread, C wisp (B was dropped).
#define MAX_SIPHONS 3
#define SIPHON_FRAMES 24
typedef struct { uint8_t active, age; int x, y; } Siphon;          // victim torso, world px (height applied)
static Siphon s_siphons[MAX_SIPHONS];
// Snapshot of a burning enemy for the variant draws (rebuilt every frame in burn_fx_update).
typedef struct { int x, y; uint8_t layers; int8_t torso, head, hw; } BurnMark;
typedef struct { int x, y; } MartirioBlast;
static BurnEmber s_burn_embers[MAX_BURN_EMBERS];
static BurnRing s_burn_rings[MAX_BURN_RINGS];
static Flare s_flares[MAX_FLARES];
static BurnMark s_marks[MAX_BURN_MARKS];
// Characters that can hide an effect standing behind them (rebuilt every frame in burn_fx_update): feet (x, y),
// centre height cy and a half-axes ellipse a bit inside the hit ellipse, so the cut follows the sprite and not
// the wide hit volume. An effect with ground depth d is hidden by every body with y > d that covers the pixel.
typedef struct { int x, y, cy, rx, ry; } OccBody;
static OccBody s_occ[MAX_OCC_BODIES];
static int s_occ_n = 0;
static int s_occ_on = 0, s_occ_cx = 0, s_occ_cy = 0, s_occ_depth = 0;   // put_px filter, see occ_begin
static int s_mark_n = 0;
static MartirioBlast s_mq[MARTIRIO_QUEUE];
static int s_mq_head = 0, s_mq_count = 0;
static Flare *flare_new(int kind, int x, int y, int depth);
static void consume_new(const Enemy *e, int idx, int layers);
static BurnEmber *burn_ember_new(int kind, int x, int y, int depth, int life, int vx);
static void burn_body(const Enemy *e, int *torso, int *head, int *half_w);
static int aura_rand8(void);
static int viatico_roll(const Enemy *e);
static uint32_t s_burn_tick = 0;
static int s_burn_live = 0;               // live burn embers last frame (variant A throttle)
static int s_next_charge_pct = 0;         // Sed de Ceniza: change of the next charge time, % (one shot)
static int s_charge_frames = 24;          // frames of the charge in progress

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
    for (int i = 0; i < MAX_SPARKS; i++) s_sparks[i].active = 0;
    aura_reset();
    for (int i = 0; i < MAX_FX_PARTS; i++) s_fx[i].kind = FXP_NONE;
    for (int i = 0; i < MAX_BURN_EMBERS; i++) s_burn_embers[i].active = 0;
    for (int i = 0; i < MAX_BURN_RINGS; i++) s_burn_rings[i].active = 0;
    for (int i = 0; i < MAX_FLARES; i++) s_flares[i].active = 0;
    s_mark_n = 0;
    s_mq_head = s_mq_count = 0;
    s_hit_pending = s_instant_pending = 0;
    s_cilicio_tick = s_llaga_missing = 0;
    for (int i = 0; i < MAX_SIPHONS; i++) s_siphons[i].active = 0;
    for (int i = 0; i < MAX_CONSUME; i++) s_consume[i].active = 0;
    g_aura_force_mask = 0;
    s_next_charge_pct = 0;
    s_charge_frames = g_weapon_tuning[WEAPON_SNIPER].aim_min_frames;
}

void weapons_shift_y(int dy_px) {
    fixed fdy = TO_FIXED(dy_px);
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
    s_hero_y += dy_px;
    for (int i = 0; i < THORN_DROPS; i++)
        if (s_drops[i].active) s_drops[i].y += dy_px;
    for (int i = 0; i < ASH_EMBERS; i++)
        if (s_embers[i].active) s_embers[i].y += dy_px;
    for (int i = 0; i < ASH_VOLUTES; i++)
        if (s_volutes[i].active) s_volutes[i].ay += dy_px;
    for (int i = 0; i < MAX_BURN_EMBERS; i++)
        if (s_burn_embers[i].active) { s_burn_embers[i].y += dy_px; s_burn_embers[i].depth += dy_px; }
    for (int i = 0; i < MAX_BURN_RINGS; i++)
        if (s_burn_rings[i].active) s_burn_rings[i].y += dy_px;
    for (int i = 0; i < MAX_FLARES; i++)
        if (s_flares[i].active) { s_flares[i].y += dy_px; s_flares[i].depth += dy_px; }
    for (int i = 0; i < s_mark_n; i++) s_marks[i].y += dy_px;
    for (int i = 0; i < MAX_SIPHONS; i++)
        if (s_siphons[i].active) s_siphons[i].y += dy_px;
    for (int i = 0; i < s_mq_count; i++)
        s_mq[(s_mq_head + i) & (MARTIRIO_QUEUE - 1)].y += dy_px;
}

// Drops a charge in progress (level-up screen, DESIGN.md 6.12.8) without firing.
void weapons_cancel_aim(void) {
    if (s_aim_state == AIM_AIMING || s_aim_state == AIM_READY) sfx_stop_charge();
    s_aim_state = AIM_IDLE;
    s_aim_timer = 0;
    s_aim_prog = 0;
    aura_reset();
}

const char *weapons_get_name(WeaponType type) {
    if (type >= 0 && type < NUM_WEAPON_TYPES) return g_weapon_tuning[type].name;
    return "UNKNOWN";
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

// Sparks leave the impact point opposite to the shot, with a sideways spread.
static void spawn_impact(int x, int y, fixed back_x, fixed back_y, int count, int sniper) {
    int n = count + 2;
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
    spawn_frag(x, y, back_x, back_y);
}

static void spawn_flash(const WeaponInput *in, fixed dir_x, fixed dir_y) {
    s_flash.life = 3;
    s_flash.x = TO_INT(in->muzzle_x);
    s_flash.y = TO_INT(in->muzzle_y) - in->muzzle_h;
    s_flash.dir_x = dir_x;
    s_flash.dir_y = dir_y;
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
    if (!e->active || e->hp <= 0 || e->type == ENEMY_TYPE_ABANDERADO || tuning->knockback <= 0) return;
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

// Sniper ray length: base plus the Alcance Don (DESIGN.md 6.12.5).
static int sniper_range(void) {
    return g_weapon_tuning[WEAPON_SNIPER].projectile_range + g_mods.sniper_range;
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

// Ray (DESIGN.md 6.12.2): pierces the enemies it kills and stops at the first one that survives the hit
// (Lanza de Longinos: pierces them all) and at the first wall. Beam damage goes through upgrades.c.
static void fire_sniper(const WeaponTuning *tuning, const WeaponInput *in, fixed dir_x, fixed dir_y,
                        Enemy *enemies, int max_enemies) {
    fixed cur_x, cur_y;
    shot_origin(in, &cur_x, &cur_y);
    fixed step_x = dir_x * 2;
    fixed step_y = dir_y * 2;
    uint32_t hit_mask = 0;
    int end_blocked = 0;
    int survivor = 0;                   // an enemy lived through the hit: the ray ends here
    int kills = 0;                      // Sed de Ceniza
    const int pierce_all = upgrades_has_relic(RELIC_LANZA);
#if ENCOUNTERS_PROTO
    // DESIGN.md 6.13.6: the ray goes on with the damage it has left after a kill; a survivor stops it.
    int beam_left = upgrades_beam_damage(tuning->damage_per_hit);
    int relic_done = 0;
#endif

    const int range = sniper_range();
    for (int d = 0; d < range; d += 2) {
        fixed nx = cur_x + step_x;
        fixed ny = cur_y + step_y;
        if (!bullet_position_is_free(nx, ny)) { end_blocked = 1; break; }
        cur_x = nx;
        cur_y = ny;

        for (int i = 0; i < max_enemies; i++) {
            Enemy *e = &enemies[i];
            if (!e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE || (hit_mask & (1u << i)) || g_enemy_ally[i]) continue;
#if ENCOUNTERS_PROTO
            if (enc_untouchable(e)) continue;      // asleep: the ray goes through (DESIGN.md 6.13.6)
#endif
            int edx = TO_INT(cur_x - e->x);
            int edy = TO_INT(cur_y - e->y);
            int hit = (e->char_id == CHAR_CHARGER || e->char_id == CHAR_ABANDERADO)
                ? body_hit_test_ex(edx, edy, in->muzzle_h, CHARGER_BODY_HIT_CY, CHARGER_BODY_HIT_RX, CHARGER_BODY_HIT_RY)
                : (e->char_id == CHAR_OJO)
                ? body_hit_test_ex(edx, edy, in->muzzle_h, OJO_BODY_HIT_CY, OJO_BODY_HIT_RX, OJO_BODY_HIT_RY)
                : body_hit_test(edx, edy, in->muzzle_h);
            if (hit) {
                hit_mask |= 1u << i;
#if ENCOUNTERS_PROTO
                if (e->type == ENEMY_TYPE_PARROCO) {
                    // Parroco (DESIGN-ARPG s5): immune to the Ray. The Lanza goes through it without a mark; any other
                    // ray breaks on it: no damage, a 0 number, a short fan of sparks and a wax-white flash of its body.
                    if (pierce_all) continue;
                    int padv = (TO_INT(e->x - cur_x) * dir_x + TO_INT(e->y - cur_y) * dir_y) >> 8;
                    if (padv < 0) padv = 0;
                    if (padv > 14) padv = 14;
                    cur_x += dir_x * padv;
                    cur_y += dir_y * padv;
                    e->gesture = ARPG_PARROCO_FLASH_FRAMES;
                    dmg_numbers_spawn_zero(e->x, e->y - TO_FIXED(16));
                    survivor = 1;
                    spawn_impact(TO_INT(cur_x), TO_INT(cur_y) - in->muzzle_h, -dir_x, -dir_y, 8, 1);
                    sniper_hit_fx(in, cur_x, cur_y);
                    continue;
                }
                int sniper_damage = beam_left;
                const int hp_before = e->hp;
#else
                int sniper_damage = upgrades_beam_damage(tuning->damage_per_hit);
#endif
                const int auto_fe = e->burn_layers && upgrades_has_relic(RELIC_AUTO_FE);   // Auto de Fe: consumes the layers
                const int af_layers = e->burn_layers;
                if (auto_fe) {
                    int af_pct = 100;
#if ENCOUNTERS_PROTO
                    int mv = arpg_inv_mechanic_value(ARPG_MECH_AUTO_FE);
                    if (mv > 0) af_pct = mv;
#endif
                    sniper_damage = sniper_damage * (100 + af_pct) / 100;
                    burn_clear(e);
#if ENCOUNTERS_PROTO
                    beam_left = sniper_damage;
#endif
                }
                // Where a surviving enemy stops the ray: the touch of its wide hit ellipse is well in front of the
                // sprite, so the ray goes on to the projection of its centre onto the ray (at most 14 px further),
                // i.e. visibly into the body. A kill keeps the touch point (the ray goes on through).
                int adv = 0;
                if (!pierce_all) {
                    adv = (TO_INT(e->x - cur_x) * dir_x + TO_INT(e->y - cur_y) * dir_y) >> 8;
                    if (adv < 0) adv = 0;
                    if (adv > 14) adv = 14;
                }
                // Viatico: a lethal beam hit may steal a heart; the victim then stays suspended (see enemy_suspend_update).
                if (e->hp <= sniper_damage && viatico_roll(e)) e->suspend_req = 1;
                enemy_hit(e, sniper_damage, dir_x * 4, dir_y * 4);
#if ENCOUNTERS_PROTO
                enc_note_beam_hit(e);
#endif
                if (e->hp <= 0) {
                    kills++;
#if ENCOUNTERS_PROTO
                    if (!pierce_all) {
                        beam_left -= hp_before;
                        if (beam_left <= 0) survivor = 1;       // the ray spent all its damage on this kill
                    }
#endif
                } else {
                    survivor = 1;
                    cur_x += (dir_x * adv);
                    cur_y += (dir_y * adv);
                }
                const int fx_x = TO_INT(cur_x), fx_y = TO_INT(cur_y) - in->muzzle_h;
                spawn_impact(fx_x, fx_y, -dir_x, -dir_y, 4, 1);
                if (auto_fe) {
                    if (g_design_variant == 0) {                                          // A: sparks spraying from the impact point along the beam
                        Flare *f = flare_new(FL_BURST, fx_x, fx_y, TO_INT(e->y) + 1);
                        if (f) { f->dx = (int16_t)dir_x; f->dy = (int16_t)dir_y; }
                    } else if (e->hp > 0) {
                        consume_new(e, i, af_layers);                                     // B / C: the burn is consumed
                    }
                }
                shove_enemy(e, tuning, dir_x, dir_y);
                sniper_hit_fx(in, cur_x, cur_y);
            }
        }
#if ENCOUNTERS_PROTO
        if (!relic_done) {                 // the relicario of the corridor is a target too
            int rx, ry;
            if (enc_relic_target(&rx, &ry) && body_hit_test(TO_INT(cur_x) - rx, TO_INT(cur_y) - ry, in->muzzle_h)) {
                relic_done = 1;
                enc_relic_hit(upgrades_beam_damage(tuning->damage_per_hit));
                spawn_impact(TO_INT(cur_x), TO_INT(cur_y) - in->muzzle_h, -dir_x, -dir_y, 4, 1);
                survivor = 1;
            }
        }
#endif
        if (survivor && !pierce_all) { end_blocked = 1; break; }
    }
    if (upgrades_has_relic(RELIC_SED_CENIZA)) {          // each kill speeds the next charge up, a miss slows it
        s_next_charge_pct = kills > 0 ? -(kills * 15 > 60 ? 60 : kills * 15) : 30;
    } else {
        s_next_charge_pct = 0;
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
    const WeaponTuning *tuning = &g_weapon_tuning[WEAPON_SNIPER];
    player->mana -= ARPG_RAY_COST;                // ARPG: each shot costs mana (arpg.h)
    if (player->mana < 0) player->mana = 0;
    s_weapon_cooldown = tuning->fire_cooldown;
    s_last_dir_x = dir_x;
    s_last_dir_y = dir_y;
    sfx_stop_charge();
    sfx_play(SND_HEART_FIRE, TO_INT(in->player_x));
    s_instant_pending = 0;                       // the instant shot is spent (Corazon Flagelado)
    fire_sniper(tuning, in, dir_x, dir_y, enemies, max_enemies);
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

// Aura de Cilicio ring (DESIGN.md 6.12.10): 12 ground px at charge 0, 40 at READY. Gameplay and look share it.
static int cilicio_radius(int prog) {
    return 12 + ((28 * prog) >> 8);
}

// Thorn crown radius: 12 px open at charge 0, 6 px closed at READY (the spikes reach THORN_LEN beyond).
static int thorn_radius(int prog) {
    if (upgrades_has_relic(RELIC_CILICIO)) return cilicio_radius(prog) - THORN_LEN;   // the spike tips mark the burning ring
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
            mote_set(&s_drops[slot], x, y, 5, FX_SH_CRIMSON);
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
            ember_spawn(s_aura_cx + (aura_rand8() & 15) - 8, s_aura_cy - 2, 8, dense ? FX_SH_CRIMSON : FX_SH_EMBER);
    }
    if (ready && !s_aura_was_ready) {
        for (int k = 0; k < 12; k++)
            ember_spawn(s_aura_cx + (aura_rand8() & 31) - 16, s_aura_cy - (aura_rand8() & 7), 12, FX_SH_GOLD);
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
    if (aura_on(AURA_STYLE_E)) {
        thorn_update(charging, prog);
    } else {
        for (int i = 0; i < THORN_DROPS; i++) s_drops[i].active = 0;
    }
    if (aura_on(AURA_STYLE_H)) {
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
    if (!aura_on(AURA_STYLE_L)) {
        // Without the flames look the bolts are cut at once, so none is left when the look comes back.
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

int weapons_aim_line(int *mx, int *my, int *gx, int *gy) {
    if (s_aim_state != AIM_AIMING && s_aim_state != AIM_READY) return 0;
    *mx = TO_INT(s_aim_muzzle_x);
    *my = TO_INT(s_aim_muzzle_y);
    *gx = (int)s_aim_dir_x;
    *gy = (int)s_aim_dir_y * 2;
    return 1;
}

void weapons_ready_instant(void) {
    s_instant_pending = 1;
}

int weapons_aim_progress(void) {
    return s_aim_prog;
}

int weapons_can_start_aim(const PlayerState *player) {
    (void)player;
    return s_weapon_cooldown <= 0 && s_aim_state == AIM_IDLE;
}

int weapons_input(PlayerState *player, const WeaponInput *in, Enemy *enemies, int max_enemies) {
    if (!player || !in || player->is_dead) {
        if (s_aim_state == AIM_AIMING || s_aim_state == AIM_READY) sfx_stop_charge();
        s_aim_state = AIM_IDLE;
        return 0;
    }

    fixed dir_x = 0, dir_y = 0;
    int has_aim = in->touch_down ? compute_aim(in, &dir_x, &dir_y) : 0;

    // Sacred ray: touch to aim (the player stops), release to fire once armed. A fresh press always
    // starts the charge at once, even right after a shot: the post-shot cooldown is dropped so
    // the player never waits for the recovery to end before charging again, and the charge
    // restarts from zero (timer and progress) on this very frame.
    int result = 0;
    if (s_aim_state == AIM_IDLE) {
        if (in->touch_pressed) s_weapon_cooldown = 0;
        // ARPG: the ray needs mana for one shot; without it the press does nothing.
        if ((in->touch_pressed || in->touch_down) && s_weapon_cooldown <= 0 && player->mana >= ARPG_RAY_COST) {
            s_aim_state = AIM_AIMING;
            s_aim_timer = 0;
            s_aim_prog = 0;
            // Charge time: base + Prisa, then the one-shot change of Sed de Ceniza (DESIGN.md 6.12.6).
            int frames = g_weapon_tuning[WEAPON_SNIPER].aim_min_frames + g_mods.sniper_aim;
            if (frames < 6) frames = 6;
            int pct = s_next_charge_pct + (upgrades_has_relic(RELIC_PROCESION) ? 50 : 0);   // Procesion: +50 % time
            frames = frames * (100 + pct) / 100;
            s_charge_frames = frames < 4 ? 4 : frames;
            s_next_charge_pct = 0;
            if (s_instant_pending) s_aim_timer = s_charge_frames;       // Corazon Flagelado: READY on press
            sfx_start_charge();
        }
    }
    if (s_aim_state == AIM_IDLE) return 0;

    if (!in->touch_down) {
        if (s_aim_state == AIM_READY) {
            result = fire_weapon(player, in, s_aim_dir_x, s_aim_dir_y, enemies, max_enemies);
        } else {
            sfx_stop_charge();
        }
        s_aim_state = AIM_IDLE;
        return result;
    }

    if (s_aim_state == AIM_CANCELLED) return 0;

    // Dragging the stylus back onto the character cancels the shot.
    int bx = in->touch_x - TO_INT(in->player_x);
    int by = in->touch_y - (TO_INT(in->player_y) - in->muzzle_h);
    if (bx * bx + by * by <= SNIPER_CANCEL_RADIUS * SNIPER_CANCEL_RADIUS) {
        sfx_stop_charge();
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
    s_aim_len = ray_length(in, s_aim_dir_x, s_aim_dir_y, sniper_range());
    s_aim_timer++;
    int aim_frames = s_charge_frames;
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

// ---------------------------------------------------------------------------
// Quemado: embers, Llama Votiva, Martirio Contagioso (DESIGN.md 6.12.6, 6.12.8)
// ---------------------------------------------------------------------------

// Body ellipse of an enemy (hitvolume.h): torso height, head height and half width, by sprite size.
static void burn_body(const Enemy *e, int *torso, int *head, int *half_w) {
    if (e->char_id == CHAR_CHARGER || e->char_id == CHAR_ABANDERADO) {
        *torso = CHARGER_BODY_HIT_CY; *head = CHARGER_BODY_HIT_CY + CHARGER_BODY_HIT_RY; *half_w = CHARGER_BODY_HIT_RX;
    } else if (e->char_id == CHAR_OJO) {
        *torso = OJO_BODY_HIT_CY; *head = OJO_BODY_HIT_CY + OJO_BODY_HIT_RY; *half_w = OJO_BODY_HIT_RX;
    } else {
        *torso = BODY_HIT_CY; *head = BODY_HIT_CY + BODY_HIT_RY; *half_w = BODY_HIT_RX;
    }
}

static BurnEmber *burn_ember_new(int kind, int x, int y, int depth, int life, int vx) {
    for (int i = 0; i < MAX_BURN_EMBERS; i++) {
        BurnEmber *b = &s_burn_embers[i];
        if (b->active) continue;
        b->active = 1;
        b->kind = (uint8_t)kind;
        b->x = x;
        b->y = y;
        b->depth = depth;
        b->life = b->max_life = (uint8_t)life;
        b->back = 0;
        b->vx = (int8_t)vx;
        return b;
    }
    return NULL;
}

static void consume_new(const Enemy *e, int idx, int layers) {
    for (int i = 0; i < MAX_CONSUME; i++) {
        Consume *c = &s_consume[i];
        if (c->active && c->idx != idx) continue;       // a second hit restarts the enemy's own slot
        int torso, head, hw;
        burn_body(e, &torso, &head, &hw);
        c->active = 1; c->age = 0; c->idx = (uint8_t)idx; c->layers = (uint8_t)layers;
        c->x = TO_INT(e->x); c->y = TO_INT(e->y);
        c->torso = (int8_t)torso; c->head = (int8_t)head; c->hw = (int8_t)hw;
        return;
    }
}

// Tint level 1..4 an enemy keeps while its burn is consumed (fades to 0), read by main.c draw_enemy.
int weapons_consume_tint(int enemy_idx) {
    for (int i = 0; i < MAX_CONSUME; i++) {
        const Consume *c = &s_consume[i];
        if (!c->active || c->idx != enemy_idx) continue;
        const int top = c->layers > 4 ? 4 : c->layers;
        return (top * (CONSUME_FRAMES - c->age) + CONSUME_FRAMES - 1) / CONSUME_FRAMES;
    }
    return 0;
}

static Flare *flare_new(int kind, int x, int y, int depth) {
    for (int i = 0; i < MAX_FLARES; i++) {
        Flare *f = &s_flares[i];
        if (f->active) continue;
        f->active = 1; f->kind = (uint8_t)kind; f->age = 0; f->aux = 0; f->dx = 0; f->dy = 0; f->x = x; f->y = y; f->depth = depth;
        return f;
    }
    return NULL;
}

static void burn_ring_new(int x, int y, int rmax, int kind) {
    for (int i = 0; i < MAX_BURN_RINGS; i++) {
        if (s_burn_rings[i].active) continue;
        s_burn_rings[i].active = 1;
        s_burn_rings[i].age = 0;
        s_burn_rings[i].rmax = (uint8_t)rmax;
        s_burn_rings[i].kind = (uint8_t)kind;
        s_burn_rings[i].x = x;
        s_burn_rings[i].y = y;
        return;
    }
}

// Rising embers around burning bodies: one every (8 - layers) frames per enemy (at least every 2) at torso
// height, plus a flame tongue over the head at the layer cap. The pool is global and capped; when it is
// full the new ones are simply not born.
static void burn_fx_update(Enemy *enemies, int max_enemies) {
    s_burn_tick++;
    s_occ_n = 0;
    for (int i = 0; i < max_enemies && s_occ_n < MAX_OCC_BODIES; i++) {
        const Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE) continue;
        int torso, head, hw;
        burn_body(e, &torso, &head, &hw);
        OccBody *o = &s_occ[s_occ_n++];
        o->x = TO_INT(e->x); o->y = TO_INT(e->y); o->cy = torso;
        o->rx = (hw * 2) / 3; o->ry = head - torso - 2;
    }
    int live = 0;
    for (int i = 0; i < MAX_BURN_EMBERS; i++) {
        BurnEmber *b = &s_burn_embers[i];
        if (!b->active) continue;
        if (--b->life == 0) { b->active = 0; continue; }
        live++;
        if (b->kind == 3) {
            int age = b->max_life - b->life;
            if ((age & 3) != 3) b->y -= 1;                 // smoke climbs 3/4 px a frame
            if ((age & 3) == 3) b->x += b->vx;
        } else if (b->kind == 7) {
            int age = b->max_life - b->life;
            if ((age & 1) == 0) b->y -= 1;                 // pale mote: half a px a frame
            if ((age % 5) == 4) b->x += b->vx;
        } else if (b->kind == 4 || b->kind == 5) {
            int age = b->max_life - b->life;
            if ((age & 3) != 3) b->y -= 1;                 // climbs 3/4 px a frame: ~20 px over its life
            if ((age % 3) == 2) b->x += b->vx;             // sideways drift
        } else if (b->kind == 0) {
            int age = b->max_life - b->life;
            if (age & 1) b->y -= 1;                        // rises 1 px every 2 frames
            if ((age & 3) == 3) b->x += b->vx;             // slight drift
        } else if (b->kind == 6) {
            if (b->y < b->depth) b->y += 1;                // Llaga B blood drop: falls 1 px a frame, then splats on the floor
        }
    }
    s_burn_live = live;
    for (int i = 0; i < MAX_SIPHONS; i++)
        if (s_siphons[i].active && ++s_siphons[i].age >= SIPHON_FRAMES) s_siphons[i].active = 0;
    for (int i = 0; i < MAX_BURN_RINGS; i++) {
        BurnRing *r = &s_burn_rings[i];
        if (r->active && ++r->age >= BURN_RING_FRAMES) r->active = 0;
    }
    for (int i = 0; i < MAX_FLARES; i++) {
        Flare *f = &s_flares[i];
        if (f->active && ++f->age >= s_flare_life[f->kind]) f->active = 0;
    }
    for (int i = 0; i < MAX_CONSUME; i++) {
        Consume *c = &s_consume[i];
        if (!c->active) continue;
        const Enemy *e = &enemies[c->idx];
        if (++c->age >= CONSUME_FRAMES || !e->active || e->hp <= 0) { c->active = 0; continue; }
        int torso, head, hw;
        burn_body(e, &torso, &head, &hw);
        c->x = TO_INT(e->x); c->y = TO_INT(e->y);
        c->torso = (int8_t)torso; c->head = (int8_t)head; c->hw = (int8_t)hw;
        if (g_design_variant == 2 && c->age >= 20 && c->age < 26) {   // C: the sheet of flame dissolves into embers at the head
            BurnEmber *em = burn_ember_new(4, c->x + (aura_rand8() % 9) - 4, c->y - head, c->y, 16 + (aura_rand8() & 7), (aura_rand8() % 3) - 1);
            if (em) em->back = (uint8_t)(aura_rand8() & 1);
        }
    }
    const int cap = BURN_BASE_CAP + g_mods.burn_cap_bonus;
    const int variant = burn_style();
    s_mark_n = 0;
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->burn_layers || !e->active) continue;
        int torso, head, hw;
        burn_body(e, &torso, &head, &hw);
        int ex = TO_INT(e->x), ey = TO_INT(e->y);
        if (variant != 0 && s_mark_n < MAX_BURN_MARKS) {         // B: ring of flames
            BurnMark *m = &s_marks[s_mark_n++];
            m->x = ex; m->y = ey; m->layers = e->burn_layers;
            m->torso = (int8_t)torso; m->head = (int8_t)head; m->hw = (int8_t)hw;
        }
        if (e->burn_ember > 0) {
            e->burn_ember--;
        } else if (variant == 0) {
            // A: dense rising embers from the trunk; the rate, the number per burst and the big ones grow with the layers.
            const int L = e->burn_layers;
            int period = L >= 4 ? 1 : L >= 2 ? 2 : 3;
            e->burn_ember = (uint8_t)(period - 1);
            int n = 1 + (L >= 3) + (L >= 5);
            if (s_burn_live > BURN_EMBER_SOFT) n = (s_burn_tick & 1) ? 0 : 1;     // pool pressure: thin out
            for (int k = 0; k < n; k++) {
                int ox = ((aura_rand8() * (2 * hw - 1)) >> 8) - (hw - 1);
                int h = (aura_rand8() * (head - 2)) >> 8;                         // anywhere on the body
                int big = (aura_rand8() & 3) < (L >= 3 ? 2 : 1);
                BurnEmber *em = burn_ember_new(big ? 5 : 4, ex + ox, ey - 2 - h, ey, 18 + (aura_rand8() & 7), (aura_rand8() % 3) - 1);
                if (em) em->back = (uint8_t)(aura_rand8() & 1);                   // half of them burn on the far side of the body
            }
        }
        if (variant == 0 && e->burn_layers >= 3 && ((s_burn_tick + (uint32_t)i) & 1) == 0) {
            // Flame tongues over the head, from 3 layers: one, then three at the cap. vx carries the height.
            const int L = e->burn_layers;
            const int tall = 3 + (L >= cap) + (aura_rand8() & 1);
            burn_ember_new(1, ex + (aura_rand8() & 1) - 1, ey - head - 1, ey, 2, tall);
            if (L >= cap) {
                burn_ember_new(1, ex - 4 + (aura_rand8() & 1), ey - head + 1, ey, 2, 2 + (aura_rand8() & 1));
                burn_ember_new(1, ex + 4 - (aura_rand8() & 1), ey - head + 1, ey, 2, 2 + (aura_rand8() & 1));
            }
        }
    }
}

// Llama Votiva: while charging, the aim line burns what it touches (1 layer per VOTIVA_FRAMES of contact).
// No walk along the line: each enemy is projected onto the aim segment (ground metric for the distance
// along it, screen metric for the distance across it), integer maths only.
static void votive_update(Enemy *enemies, int max_enemies) {
    int on = upgrades_has_relic(RELIC_LLAMA_VOTIVA) && aura_charging() && s_aim_len > 0;
    int dlen = 0;
    if (on) dlen = (int)int_sqrt((uint32_t)(s_aim_dir_x * s_aim_dir_x + s_aim_dir_y * s_aim_dir_y));
    int mx = TO_INT(s_aim_muzzle_x), my = TO_INT(s_aim_muzzle_y);
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!on || !e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE || g_enemy_ally[i]) { e->votive_hits = 0; continue; }
        int torso, head, hw;
        burn_body(e, &torso, &head, &hw);
        int wx = TO_INT(e->x) - mx, wy = TO_INT(e->y) - my;
        int reach = s_aim_len + 24;
        if (wx > reach || wx < -reach || wy > reach || wy < -reach) continue;
        int along = (wx * s_aim_dir_x + 4 * wy * s_aim_dir_y) >> 8;     // ground px from the muzzle
        int r = hw - 4;                                                  // reach of the line across the body
        if (along < 0 || along > s_aim_len + r) continue;
        int sy = wy - torso + s_aim_muzzle_h;                            // body centre vs the line (screen)
        int cross = wx * s_aim_dir_y - sy * s_aim_dir_x;
        if (cross < 0) cross = -cross;
        if (cross > r * dlen) continue;
        if (++e->votive_hits >= VOTIVA_FRAMES) {
            e->votive_hits = 0;
            burn_apply(e, 1);
        }
    }
}

// A burning enemy died (called from the death hook with the enemy still intact): Martirio Contagioso queues
// an explosion at its feet. The queue is small; beyond it the blast is dropped.
void weapons_enemy_died(const Enemy *e) {
    if (!e->burn_layers || !upgrades_has_relic(RELIC_MARTIRIO) || s_mq_count >= MARTIRIO_QUEUE) return;
    MartirioBlast *q = &s_mq[(s_mq_head + s_mq_count) & (MARTIRIO_QUEUE - 1)];
    q->x = TO_INT(e->x);
    q->y = TO_INT(e->y);
    s_mq_count++;
}

void weapons_pira_explode(const Enemy *e) {
    if (!e || !e->burn_layers || s_mq_count >= MARTIRIO_QUEUE) return;
    MartirioBlast *q = &s_mq[(s_mq_head + s_mq_count) & (MARTIRIO_QUEUE - 1)];
    q->x = TO_INT(e->x);
    q->y = TO_INT(e->y);
    s_mq_count++;
}

// One fire blast: ring, burst of embers, then the layers to every enemy inside the radius (layers first, so a
// kill chains) and fire damage by the quiet path. Shared by Martirio Contagioso and Corazon Flagelado.
static void blast(int bx, int by, int radius, int damage, int layers, int embers, int kind, Enemy *enemies, int max_enemies) {
    burn_ring_new(bx, by, radius, kind);
    if (g_design_variant == 2 && kind == RING_MARTIRIO) flare_new(FL_COLUMN, bx, by, by);   // C: column of fire from the corpse
    if (g_design_variant != 0 && kind == RING_MARTIRIO) embers = 3;   // B / C keep their own look; A matches Corazon Flagelado A
    const int span = ((radius * 5) >> 2) + 1, half = (radius * 5) >> 3;
    const int vspan = (radius >> 1) + 1, vhalf = radius >> 2;
    for (int k = 0; k < embers; k++) {
        int ox = (int)((aura_rand8() * span) >> 8) - half;
        int oy = (int)((aura_rand8() * vspan) >> 8) - vhalf;
        burn_ember_new(0, bx + ox, by + oy - 6, by, 12 + (aura_rand8() & 3), (aura_rand8() % 3) - 1);
    }
    const int r2 = radius * radius;
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE || g_enemy_ally[i]) continue;
        int dx = TO_INT(e->x) - bx, dy = TO_INT(e->y) - by;
        if (dx * dx + GROUND_DY2(dy) > r2) continue;
        burn_apply(e, layers);
        enemy_hit_quiet(e, upgrades_fire_damage(damage));
    }
}

// At most MARTIRIO_PER_FRAME explosions a frame (chains continue on the following frames).
static void martirio_update(Enemy *enemies, int max_enemies) {
    for (int n = 0; n < MARTIRIO_PER_FRAME && s_mq_count > 0; n++) {
        MartirioBlast b = s_mq[s_mq_head];
        s_mq_head = (s_mq_head + 1) & (MARTIRIO_QUEUE - 1);
        s_mq_count--;
        int dmg = MARTIRIO_DAMAGE;
#if ENCOUNTERS_PROTO
        int pv = arpg_inv_mechanic_value(ARPG_MECH_PIRA);
        if (pv > 0) dmg = pv;
#endif
        blast(b.x, b.y, MARTIRIO_RADIUS, dmg, MARTIRIO_LAYERS, 8, RING_MARTIRIO, enemies, max_enemies);
    }
}

// Corazon Flagelado: the wave of a hit taken (flag raised by player_take_hit), then the next charge is instant.
static void flagelado_update(Enemy *enemies, int max_enemies) {
    if (!s_hit_pending) return;
    s_hit_pending = 0;
    if (g_player_state.is_dead) return;
    blast(s_hero_x, s_hero_y, FLAGELADO_RADIUS, FLAGELADO_DAMAGE, FLAGELADO_LAYERS, 12, RING_FLAGELADO, enemies, max_enemies);
    s_instant_pending = 1;
    if (s_aim_state == AIM_AIMING) s_aim_timer = s_charge_frames;     // a charge in progress is armed now
}

// Aura de Cilicio: always active while alive (heart modification); grows further while charging.
static void cilicio_update(Enemy *enemies, int max_enemies) {
    if (!upgrades_has_relic(RELIC_CILICIO) || g_player_state.is_dead) { s_cilicio_tick = 0; return; }
    if (++s_cilicio_tick < CILICIO_PERIOD) return;
    s_cilicio_tick = 0;
    int prog = aura_charging() ? (s_aim_prog > 160 ? s_aim_prog : 160) : 160;
    const int r = cilicio_radius(prog), r2 = r * r;
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE || g_enemy_ally[i]) continue;
        int dx = TO_INT(e->x) - s_hero_x, dy = TO_INT(e->y) - s_hero_y;
        if (dx * dx + GROUND_DY2(dy) <= r2) burn_apply(e, 1);
    }
}

// Viatico siphon: starts at the victim's torso; the heart is already added by the caller.
static void siphon_new(int x, int y) {
    for (int i = 0; i < MAX_SIPHONS; i++) {
        Siphon *q = &s_siphons[i];
        if (q->active) continue;
        q->active = 1; q->age = 0; q->x = x; q->y = y;
        return;
    }
}

// Viatico (DESIGN.md 6.12.10): a beam kill steals 1 heart with ~8 % chance (~16 % if the victim stood within
// VIATICO_RADIUS of the hero), never above the maximum. Called from fire_sniper only, so fire deaths do not count.
// Returns 1 when it procs: the caller then suspends the victim's death (DESIGN.md 6.12.12).
static int viatico_roll(const Enemy *e) {
    if (!upgrades_has_relic(RELIC_VIATICO) || g_player_state.is_dead || g_player_state.hp >= g_player_state.max_hp) return 0;
    int dx = TO_INT(e->x) - s_hero_x, dy = TO_INT(e->y) - s_hero_y;
    int near = dx * dx + GROUND_DY2(dy) <= VIATICO_RADIUS * VIATICO_RADIUS;
    if (!s_viatico_force && aura_rand8() >= (near ? VIATICO_PCT_NEAR : VIATICO_PCT)) return 0;
    s_viatico_force = 0;
    g_player_state.hp += ARPG_HEAL_PICKUP;          // one heart (ARPG: heal in points)
    if (g_player_state.hp > g_player_state.max_hp) g_player_state.hp = g_player_state.max_hp;
    int torso, head, hw;
    burn_body(e, &torso, &head, &hw);
    siphon_new(TO_INT(e->x), TO_INT(e->y) - torso);
    return 1;
}

void weapons_set_hero_pos(int x, int y) {
    s_hero_x = x;
    s_hero_y = y;
}

void weapons_player_hit(void) {
    if (upgrades_has_relic(RELIC_FLAGELADO) && !g_player_state.is_dead) s_hit_pending = 1;
}

// Llaga Abierta (DESIGN.md 6.12.12): hearts below 5. B (A renders like B) = blood dripping from the chest wound (a few drops
// at 4 hearts, heavy at 1, drops that fall to the floor leave a short fading trail) and an ascended look: a faint
// pale-gold brightening of the hero (main.c) and pale motes drifting up. C = red vignette (weapons_render_overlay).
static void llaga_update(void) {
    int missing = upgrades_llaga_missing();
    s_llaga_missing = g_player_state.is_dead ? 0 : missing;
    if (s_llaga_missing == 0 || g_design_variant == 2) return;
    const int m = s_llaga_missing;
    int drops = (aura_rand8() & 31) < m * m * 2 ? 1 : 0;           // 2, 8, 18, 32 in 32 frames per missing heart count
    if (m >= 4 && (aura_rand8() & 1)) drops++;
    for (int k = 0; k < drops; k++)
        burn_ember_new(6, s_hero_x + (aura_rand8() % 5) - 2, s_hero_y - 20, s_hero_y + 1 + (aura_rand8() & 3), m >= 3 ? 52 : 40, 0);
    static const uint8_t mote_rate[5] = { 0, 3, 8, 14, 22 };       // ascended motes per 32 frames: a few at 1 missing, a swarm at 4
    for (int k = 0; k < (m >= 3 ? 2 : 1); k++)
        if ((aura_rand8() & 31) < mote_rate[m] >> k)
            burn_ember_new(7, s_hero_x + (aura_rand8() % 17) - 8, s_hero_y - 4 - (aura_rand8() % 30), s_hero_y, 24 + (aura_rand8() & 7), (aura_rand8() % 3) - 1);
}

// Hero sprite glow level for Llaga Abierta B (0 = none, 1..4 = hearts missing: the ascended aura grows with the blood); read by main.c.
int weapons_llaga_tint(void) {
    if (g_design_variant == 2 || s_llaga_missing == 0) return 0;
    return s_llaga_missing > 4 ? 4 : s_llaga_missing;
}

// Evidence hook for the design-variant scenarios (scenarios/abc_*.json): the runner writes a bit mask here to fire a
// cue on demand (1 Viatico siphon from a point right of the hero, 2 Corazon Flagelado wave, 4 Martirio blast in front of the hero, 8 Auto de Fe sparks, 16 next beam kill steals a heart, 32 plain sniper trail, 64 / 128 force burn style A / B). Cleared at once.
volatile uint8_t g_abc_debug = 0;

void weapons_update(Enemy *enemies, int max_enemies) {
    if (g_abc_debug) {
        uint8_t cmd = g_abc_debug;
        g_abc_debug = 0;
        if (cmd & 1) siphon_new(s_hero_x + 44, s_hero_y - 8);
        if ((cmd & 2) && upgrades_has_relic(RELIC_FLAGELADO)) s_hit_pending = 1;
        if (cmd & 8) {
            Flare *f = flare_new(FL_BURST, s_hero_x + 14, s_hero_y - 20, s_hero_y + 1);
            if (f) { f->dx = 200; f->dy = -110; }
        }
        if (cmd & 16) s_viatico_force = 1;                    // the next beam kill steals a heart for sure
        if (cmd & 64) s_burn_force = 0;                       // burn drawn as A / B whatever the variant (Auto de Fe B / C start from them)
        if (cmd & 128) s_burn_force = 1;
        if (cmd & 32) {                                       // 32 plain trail, drawn up and to the right
            s_trail.life = 6;
            s_trail.x0 = s_hero_x; s_trail.y0 = s_hero_y - 24;
            s_trail.x1 = s_hero_x + 44; s_trail.y1 = s_hero_y - 24 - 70;
            s_last_dir_x = 110; s_last_dir_y = -231;
        }
        if ((cmd & 4) && s_mq_count < MARTIRIO_QUEUE) {
            MartirioBlast *q = &s_mq[(s_mq_head + s_mq_count) & (MARTIRIO_QUEUE - 1)];
            q->x = s_hero_x;
            q->y = s_hero_y - 36;
            s_mq_count++;
        }
    }
    if (s_weapon_cooldown > 0) s_weapon_cooldown--;
    if (s_flash.life > 0) s_flash.life--;
    if (s_trail.life > 0) s_trail.life--;
    if (s_shake_timer > 0) { s_shake_timer--; s_shake_tick++; }

    for (int i = 0; i < MAX_SPARKS; i++) {
        WeaponSpark *s = &s_sparks[i];
        if (!s->active) continue;
        s->x += s->vx;
        s->y += s->vy;
        s->vy += 32;                      // light gravity
        if (--s->life <= 0) s->active = 0;
    }

    fx_update();

    if (s_instant_pending && upgrades_has_relic(RELIC_FLAGELADO)) g_aura_force_mask |= 1 << AURA_STYLE_L;   // Corazon Flagelado: flames while the instant shot waits
    else g_aura_force_mask &= ~(1 << AURA_STYLE_L);
    s_aura_mask = relic_aura_mask() | g_aura_force_mask | g_aura_debug_mask;
    aura_update();

    // Quemado: ticks, aim-line contact, explosions and embers, once a frame outside the enemy AI.
    burn_update(enemies, max_enemies);
    enemy_suspend_update(enemies, max_enemies);
    votive_update(enemies, max_enemies);
    flagelado_update(enemies, max_enemies);
    martirio_update(enemies, max_enemies);
    cilicio_update(enemies, max_enemies);
    llaga_update();
    burn_fx_update(enemies, max_enemies);
}

// ---------------------------------------------------------------------------
// Rendering: procedural strokes. render_screen() calls weapons_render() once per screen,
// so the aim laser, pellets, trail, flash and sparks show on both of them.
// ---------------------------------------------------------------------------

typedef struct {
    uint16_t *p16;        // screen page (BGR555 with the alpha bit)
} FxTarget;

// True when a character standing in front of ground depth `depth` covers the world pixel (wx, wy).
static int occ_hidden(int wx, int wy, int depth) {
    for (int i = 0; i < s_occ_n; i++) {
        const OccBody *b = &s_occ[i];
        if (b->y <= depth) continue;                       // not in front of the effect
        int dx = wx - b->x, dy = wy - (b->y - b->cy);
        if (dx < -b->rx || dx > b->rx || dy < -b->ry || dy > b->ry) continue;
        if (dx * dx * (b->ry * b->ry) + dy * dy * (b->rx * b->rx) <= (b->rx * b->rx) * (b->ry * b->ry)) return 1;
    }
    return 0;
}

// While on, put_px skips the pixels the bodies in front of `depth` hide (effects attached to a character).
static inline void occ_begin(int cam_x, int cam_y, int depth) {
    s_occ_on = s_occ_n > 0;
    s_occ_cx = cam_x; s_occ_cy = cam_y; s_occ_depth = depth;
}
static inline void occ_end(void) { s_occ_on = 0; }

static inline void put_px(const FxTarget *t, int x, int y, int color) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
    if (s_occ_on && occ_hidden(x + s_occ_cx, y + s_occ_cy, s_occ_depth)) return;
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

// Small flame column rising from (sx, sy): gold base, amber, ember, crimson tip (muted FX_SH_*). The tip
// flickers with the seed; a base of 3+ px gets a one-px skirt. Used by the B / C variants of the fire effects.
static void flame_stack(const FxTarget *t, int sx, int sy, int h, int seed) {
    if (h < 1) h = 1;
    for (int j = 0; j < h; j++) {
        if (j == h - 1 && h > 2 && (seed & 1)) continue;
        int col = j * 3 < h ? FX_SH_GOLD : j * 3 < 2 * h ? FX_SH_AMBER : (j == h - 1 ? FX_SH_CRIMSON : FX_SH_EMBER);
        put_px(t, sx, sy - j, col);
        if (h >= 4 && j * 2 < h) { put_px(t, sx - 1, sy - j, j == 0 ? FX_SH_EMBER : FX_SH_AMBER); put_px(t, sx + 1, sy - j, j == 0 ? FX_SH_EMBER : FX_SH_AMBER); }
    }
}

// Screen point of the aim ray at distance d (ground px) from the muzzle.
static void aim_point(int d, int cam_x, int cam_y, int *x, int *y) {
    *x = TO_INT(s_aim_muzzle_x + s_aim_dir_x * d) - cam_x;
    *y = TO_INT(s_aim_muzzle_y + s_aim_dir_y * d) - s_aim_muzzle_h - cam_y;
}

static void draw_cross(const FxTarget *t, int cx, int cy, int arm, int color) {
    draw_line(t, cx - arm, cy, cx + arm, cy, color);
    draw_line(t, cx, cy - arm, cx, cy + arm, color);
}

// Collimation band: volumetric falloff across -w..w. Core takes `centre`, inner glow takes `inner`,
// and the outer edge feathers out with an organic spatial+temporal dither of `rim`.
static void aim_band(const FxTarget *t, int px, int py, int w, int centre, int inner, int rim) {
    for (int o = -w; o <= w; o++) {
        int x = px + ((s_aim_dir_y * o) >> 8);
        int y = py - ((s_aim_dir_x * o) >> 8);
        int ao = o < 0 ? -o : o;
        if (o == 0) {
            put_px(t, x, y, centre);
        } else if (ao == w) {
            if (((x * 3 + y * 5 + s_aim_timer) & 3) == 0) put_px(t, x, y, rim);
        } else if (ao * 2 >= w) {
            if (((x + y + s_aim_timer) & 1) == 0) put_px(t, x, y, inner);
        } else {
            put_px(t, x, y, inner);
        }
    }
}

// Llama Votiva B / C (DESIGN.md 6.12.11): sparks that swirl round the aim line in an irregular, procedural way,
// like sunspots drifting and turning (not a helix). Every spark is a pure function of (index, frame): a hash
// gives its start, speed, spin and radius; a slow turbulence term (the table sine of position and time) bends
// its angle and radius so neighbours do not move in step. variant 0 (B): sparse single sparks, jittered
// radius, the odd bright clump. variant 1 (C): blobs of 2..4 px with a dithered rim that drift and turn.
// Cost: at most 44 sparks (B) or 14 blobs (C) a frame. No divides: the wrap along the line is a subtraction.
static inline uint32_t votive_hash(uint32_t a, uint32_t b) {
    uint32_t h = (a * 2654435761u) ^ (b * 2246822519u);
    h = h * 1664525u + 1013904223u;
    return h ^ (h >> 15);
}

static void votive_sparks(const FxTarget *t, int cam_x, int cam_y, int clumpy) {
    const int len = s_aim_len;
    if (len < 8) return;
    const int tm = s_aim_timer;
    const int n = clumpy ? 8 + (len >> 5) : 18 + (len >> 3);
    const int nmax = clumpy ? 14 : 44;
    for (int i = 0; i < (n > nmax ? nmax : n); i++) {
        uint32_t h = votive_hash((uint32_t)i, 7u);
        int sp = 1 + (int)(h & 3);                                   // 1..4 half-px per frame along the line
        int d = (int)(((h >> 8) & 255) * (uint32_t)len >> 8) + (((tm & 127) * sp) >> 1);
        while (d >= len) d -= len;
        int turb = s_ell_sin[((d >> 3) + (tm >> 2) + (int)(h >> 20)) & 31];          // -256..256, drifts with time
        int ph = (int)(h >> 12) + ((tm * (1 + (int)((h >> 4) & 3))) >> 1) + (turb >> 5);   // spin, bent by the turbulence
        int r = (clumpy ? 4 : 3) + (int)((h >> 6) & 3) + ((s_ell_sin[((tm >> 1) + (int)(h >> 9)) & 31] * (clumpy ? 2 : 3)) >> 8);
        if (r < 2) r = 2;
        int o = (s_ell_sin[ph & 31] * r) >> 8;                       // across the line
        int front = s_ell_cos[ph & 31] > 0;
        int px, py;
        aim_point(d + 1, cam_x, cam_y, &px, &py);
        int ax = (s_aim_dir_y * o) >> 8, ay = -((s_aim_dir_x * o) >> 8);
        int x = px + ax, y = py + ay;
        // The strand in front of the line is never hidden by the bodies it crosses; the one behind is (as the body is in front of it).
        occ_begin(cam_x, cam_y, front ? 1000000 : TO_INT(s_aim_muzzle_y + s_aim_dir_y * (d + 1)));
        if (!clumpy) {
            int bright = (h & 15) == 0;
            put_px(t, x, y, bright ? FX_SH_IVORY : front ? FX_SH_GOLD : FX_SH_EMBER);
            put_px(t, x + 1, y, bright ? FX_SH_GOLD : front ? FX_SH_AMBER : FX_SH_CRIMSON);
            if (!bright) put_px(t, x, y + 1, front ? FX_SH_EMBER : FX_SH_DEEP);
            if (bright) { put_px(t, x + 1, y, FX_SH_GOLD); put_px(t, x, y - 1, FX_SH_GOLD); }
            else if (front) put_px(t, x - ((s_aim_dir_x * sp) >> 9), y - 1, FX_SH_EMBER);         // a short tail
        } else {
            int big = ((h >> 3) & 3) != 0;                           // mostly 3..4 px blobs, some 2 px
            int hot = ((h >> 26) & 3) == 0 || (front && (h & 8));                      // some clumps are brighter
            int core = hot ? FX_SH_GOLD : front ? FX_SH_AMBER : FX_SH_EMBER;
            int rim = hot ? FX_SH_AMBER : front ? FX_SH_EMBER : FX_SH_CRIMSON;
            put_px(t, x, y, core);
            put_px(t, x + 1, y, core);
            if (big) { put_px(t, x, y + 1, core); put_px(t, x - 1, y, rim); put_px(t, x + 1, y + 1, rim); }
            if (((x + y + tm) & 1) == 0) { put_px(t, x - 1, y - 1, rim); put_px(t, x + 2, y, rim); }
            if (big && ((x + y + tm) & 1)) { put_px(t, x, y - 1, rim); put_px(t, x + 2, y + 1, FX_SH_DEEP); }
            put_px(t, x + 3 * (front ? -1 : 1), y + 1, FX_SH_DEEP);   // a speck that trails behind
        }
        occ_end();
    }
}

// Sniper fuego (DESIGN.md 6.10): desaturated sacred-fire collimated band (deep crimson/terracotta glow
// narrowing to a warm ivory/gold filament when armed), with rising ember motes.
static void render_aim_line(const FxTarget *t, int cam_x, int cam_y) {
    if (s_aim_state != AIM_AIMING && s_aim_state != AIM_READY) return;
    int ready = s_aim_state == AIM_READY;
    int w = (6 * (256 - s_aim_prog)) >> 8;          // lateral half-width in px (6 at 0 %, 0 when armed)
    const int votive = upgrades_has_relic(RELIC_LLAMA_VOTIVA);
    if (votive) votive_sparks(t, cam_x, cam_y, 0);        // B chosen (DESIGN.md 6.12.12); A and C render like B
    if (ready) {
        for (int d = 1; d <= s_aim_len; d++) {
            int px, py;
            aim_point(d, cam_x, cam_y, &px, &py);
            put_px(t, px, py, ((s_aim_timer >> 1) & 1) ? lc(FX_SH_IVORY) : lc(FX_SH_GOLD));
        }
        return;
    }
    int centre = s_aim_prog >= 180 ? lc(FX_SH_GOLD) : lc(FX_SH_EMBER);
    for (int d = 1; d <= s_aim_len; d++) {
        int px, py;
        aim_point(d, cam_x, cam_y, &px, &py);
        aim_band(t, px, py, w, centre, lc(FX_SH_CRIMSON), lc(FX_SH_DEEP));
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
        put_px(t, x, y, age < 3 ? lc(FX_SH_GOLD) : age < 6 ? lc(FX_SH_EMBER) : lc(FX_SH_CRIMSON));
    }
}

// Parts with volume, drawn over the sprites: crosses and fragments.
// age = frames since spawn (1 on the first frame drawn).
static void render_fx_parts(const FxTarget *t, int cam_x, int cam_y) {
    for (int i = 0; i < MAX_FX_PARTS; i++) {
        const FxPart *p = &s_fx[i];
        if (p->kind == FXP_NONE) continue;
        int age = p->max_life - p->life;
        int sx = TO_INT(p->x) - cam_x;
        int sy = TO_INT(p->y) - TO_INT(p->h) - cam_y;
        switch (p->kind) {
        case FXP_CROSS: {
            int arm = p->size - (age - 1);
            if (arm < 1) arm = 1;
            int col = age == 1 ? FX_SH_IVORY : age == 2 ? FX_SH_GOLD : FX_SH_EMBER;
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

static void draw_line_dither(const FxTarget *t, int x0, int y0, int x1, int y1, int color, int phase) {
    if ((x0 < 0 && x1 < 0) || (x0 >= SCREEN_W && x1 >= SCREEN_W) ||
        (y0 < 0 && y1 < 0) || (y0 >= SCREEN_H && y1 >= SCREEN_H)) return;
    int dx = abs_int(x1 - x0), dy = abs_int(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = (dx > dy ? dx : -dy) / 2;
    int step = 0;
    for (;;) {
        if (((step + phase) & 1) == 0) put_px(t, x0, y0, color);
        step++;
        if (x0 == x1 && y0 == y1) break;
        int e2 = err;
        if (e2 > -dx) { err -= dy; x0 += sx; }
        if (e2 < dy) { err += dx; y0 += sy; }
    }
}

// Sniper trail (DESIGN.md 6.10, fuego): warm ivory core, antique gold inner glow, dithered terracotta/crimson
// outer halo so the edges feather instead of reading as flat stripes; cooling embers along the line.
static void render_trail(const FxTarget *t, int cam_x, int cam_y) {
    int x0 = s_trail.x0 - cam_x, y0 = s_trail.y0 - cam_y;
    int x1 = s_trail.x1 - cam_x, y1 = s_trail.y1 - cam_y;
    int life = s_trail.life;
    int core = life >= 4 ? lc(FX_SH_IVORY) : life >= 2 ? lc(FX_SH_GOLD) : lc(FX_SH_EMBER);
    int side = life >= 4 ? lc(FX_SH_GOLD) : lc(FX_SH_AMBER);
    if (life >= 4) {
        draw_line_dither(t, x0, y0 - 2, x1, y1 - 2, lc(FX_SH_EMBER), life);
        draw_line_dither(t, x0, y0 + 2, x1, y1 + 2, lc(FX_SH_EMBER), life + 1);
    }
    if (life >= 2) {
        if (life >= 3) {
            draw_line(t, x0, y0 - 1, x1, y1 - 1, side);
            draw_line(t, x0, y0 + 1, x1, y1 + 1, side);
        } else {
            draw_line_dither(t, x0, y0 - 1, x1, y1 - 1, side, life);
            draw_line_dither(t, x0, y0 + 1, x1, y1 + 1, side, life + 1);
        }
    }
    draw_line(t, x0, y0, x1, y1, core);
    if (life <= 2) {
        int dx = x1 - x0, dy = y1 - y0;
        for (int i = 0; i < 16; i++) {
            if (((i + life) & 1) != 0) continue;
            int px = x0 + ((dx * i) >> 4);
            int py = y0 + ((dy * i) >> 4);
            put_px(t, px, py - ((i >> 2) & 1), lc(FX_SH_CRIMSON));
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
    render_fx_parts(t, cam_x, cam_y);
    render_flash(t, cam_x, cam_y);

    // Impact sparks: two-pixel strokes along their velocity, cooling as they die.
    for (int i = 0; i < MAX_SPARKS; i++) {
        WeaponSpark *s = &s_sparks[i];
        if (!s->active) continue;
        int age = (s->life * 3) / s->max_life;        // 2 young .. 0 old
        int color = s->sniper ? (age >= 2 ? FX_SH_GOLD : age == 1 ? FX_SH_EMBER : FX_SH_ASH_B)
                              : (age >= 2 ? FX_SPARK_A : age == 1 ? FX_SPARK_B : FX_SPARK_C);
        int hx = TO_INT(s->x) - cam_x, hy = TO_INT(s->y) - cam_y;
        put_px(t, hx, hy, color);
        put_px(t, hx - (s->vx > 96) + (s->vx < -96), hy - (s->vy > 96) + (s->vy < -96), color);
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

// One F2 flame (desaturated sacred fire): warm ivory/gold core at the base, amber/ember in the middle,
// crimson/deep blood at the tip so it blends with the prerendered heart.
static void aura_flame_draw(const FxTarget *t, const AuraBolt *b, int cam_x, int cam_y) {
    for (int k = 0; k + 1 < b->n; k++) {
        int x0 = b->px[k], y0 = b->py[k], x1 = b->px[k + 1], y1 = b->py[k + 1];
        if (k < 2) {
            int steep = abs_int(y1 - y0) > abs_int(x1 - x0);
            int ox = steep, oy = !steep;              // one px across the stroke
            aura_seg(t, x0 + ox, y0 + oy, x1 + ox, y1 + oy, cam_x, cam_y, FX_SH_AMBER, FX_SH_EMBER, b->occl);
            aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_SH_IVORY, FX_SH_GOLD, b->occl);
        } else if (k < 4) {
            aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_SH_EMBER, FX_SH_CRIMSON, b->occl);
        } else {
            aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_SH_CRIMSON, FX_SH_DEEP, b->occl);
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

// Tapered ray walk for G (glow): fades from core -> mid -> dithered outer tip with no hard dot.
static void glow_ray(const FxTarget *t, int x0, int y0, int x1, int y1, int cam_x, int cam_y,
                     int len, int blink) {
    int dx = abs_int(x1 - x0), dy = abs_int(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = dx > dy ? dx >> 1 : -(dy >> 1);
    int c1 = len >> 1;
    int c2 = (len * 3) >> 2;
    for (int n = 0; n < AURA_SEG_MAX_STEPS; n++) {
        if (n < c1) {
            aura_px(t, x0, y0, cam_x, cam_y, blink ? FX_SH_IVORY : FX_SH_GOLD, 1);
        } else if (n < c2) {
            aura_px(t, x0, y0, cam_x, cam_y, blink ? FX_SH_GOLD : FX_SH_AMBER, 1);
        } else if ((n & 1) == 0) {
            aura_px(t, x0, y0, cam_x, cam_y, FX_SH_EMBER, 1);
        }
        if (x0 == x1 && y0 == y1) break;
        int e2 = err;
        if (e2 > -dx) { err -= dy; x0 += sx; }
        if (e2 < dy) { err += dx; y0 += sy; }
    }
}

// G, glow: 12 tapered rays from the chest, alternately long and short (2/3), fading out at the tips.
// Floor pass: the body covers them.
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
        glow_ray(t, s_aura_cx, s_aura_cy, ex, ey, cam_x, cam_y, l, blink);
    }
}

// E, thorn crown: 16 spikes of 3 px, outwards from the closing ellipse, warm iron with deep blood and
// muted crimson tip catchlights; drops fall from the tips. Floor pass.
static void thorn_draw(const FxTarget *t, int cam_x, int cam_y, int prog) {
    int r = thorn_radius(prog);
    for (int i = 0; i < THORN_SPIKES; i++) {
        int a = (2 * i) & 31;
        int x0, y0, x1, y1;
        aura_floor_point(a, r, &x0, &y0);
        aura_floor_point(a, r + THORN_LEN, &x1, &y1);
        aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_BLACK, FX_SH_DEEP, 1);
        aura_px(t, x1, y1, cam_x, cam_y, FX_SH_CRIMSON, 1);
    }
    for (int i = 0; i < THORN_DROPS; i++) {
        const AuraMote *d = &s_drops[i];
        if (d->active) aura_px(t, d->x, d->y, cam_x, cam_y, d->color, 1);
    }
}

// H, ash: warm umber-ash volutes 2..4 px wide that widen as they rise with rounded/dithered edges;
// warm embers over them. Front pass: drawn over the body.
static void ash_draw(const FxTarget *t, int cam_x, int cam_y, int prog) {
    int core_col = prog >= 180 ? FX_SH_ASH_C : FX_SH_ASH_B;
    for (int i = 0; i < ASH_VOLUTES; i++) {
        const AshVolute *v = &s_volutes[i];
        if (!v->active) continue;
        int x = v->ax + (((s_ell_sin[(v->ph + v->age) & 31]) * 3) >> 8);   // sway +-3 px
        int y = v->ay - v->age;
        int w = 2 + (v->age >> 3);
        if (w > 4) w = 4;
        int core = v->age < 3 ? FX_SH_ASH_A : core_col;
        for (int r = 0; r < 2; r++) {
            for (int k = 0; k < w; k++) {
                int edge = (k == 0 || k == w - 1);
                if (edge && ((k + r + v->age) & 1)) continue;
                int col = edge ? FX_SH_ASH_A : core;
                aura_px(t, x + k, y - r, cam_x, cam_y, col, 1);
            }
        }
    }
    for (int i = 0; i < ASH_EMBERS; i++) {
        const AuraMote *e = &s_embers[i];
        if (e->active) aura_px(t, e->x, e->y, cam_x, cam_y, e->color, 1);
    }
}

// Variant draws of the burning enemies (one wall test per enemy). B: a ring of small flames round the feet,
// taller with more layers. C: charred flecks on the silhouette edge (layers * 2 + 3 of them, up to 10) and,
// from burn_fx_update, ash smoke over the head. Depth (DESIGN.md 4.9): behind = 1 is the floor pass, which draws the
// part on the far side of the body (the sprite covers it); behind = 0 draws the near side over the sprite, hidden
// only by a wall or by a character standing in front.
static void burn_marks_draw(const FxTarget *t, int cam_x, int cam_y, int behind) {
    const int v = burn_style();
    if (v == 0) return;
    for (int i = 0; i < s_mark_n; i++) {
        const BurnMark *m = &s_marks[i];
        int sx = m->x - cam_x, sy = m->y - cam_y;
        if (sx < -24 || sx >= SCREEN_W + 24 || sy < -4 || sy >= SCREEN_H + 40) continue;
        if (world_pixel_hidden(m->x, m->y - m->torso, m->y)) continue;
        {
            int rx = m->hw - 3;
            int h = 3 + (m->layers >> 1);
            for (int k = 0; k < 6; k++) {
                int a = (k * 5 + (int)(s_burn_tick >> 3)) & 31;
                if ((s_ell_sin[a] < 0) != behind) continue;               // far half of the ring: behind the body
                int fh = h + (((int)(s_burn_tick >> 1) + k) & 1);
                if (!behind) occ_begin(cam_x, cam_y, m->y + ((s_ell_sin[a] * rx) >> 9));
                flame_stack(t, sx + ((s_ell_cos[a] * rx) >> 8), sy + ((s_ell_sin[a] * rx) >> 9), fh, (int)s_burn_tick + k + i);
                occ_end();
            }
        }
    }
}

// Ash smoke puff (burn C): a dithered round blob that grows and fades from warm light ash to darker ash.
static void smoke_puff(const FxTarget *t, int sx, int sy, int age) {
    int r = age < 6 ? 1 : age < 12 ? 2 : age < 19 ? 3 : 4;
    int rr = r * r, inner = (r - 1) * (r - 1);
    int core = age < 14 ? FX_SH_SMOKE_L : FX_SH_SMOKE_M;
    for (int dy = -r; dy <= r; dy++) {
        for (int dx = -r; dx <= r; dx++) {
            int d2 = dx * dx + dy * dy;
            if (d2 > rr) continue;
            int chk = (sx + dx + sy + dy) & 1;
            if (d2 > inner && chk) continue;                       // feathered rim
            if (age > 20 && chk) continue;                         // thinning out at the end
            put_px(t, sx + dx, sy + dy, d2 > inner ? FX_SH_ASH_A : core);
        }
    }
}

// Short effects: Auto de Fe A (sparks from the impact point) and the Martirio column (C).
static void flares_draw(const FxTarget *t, int cam_x, int cam_y, int behind) {
    static const uint8_t col_h[10] = { 4, 9, 14, 18, 20, 20, 17, 13, 8, 3 };
    // Auto de Fe A: nine sparks fly from the impact point along the beam (forward speed, sideways spread) and sag under a
    // light gravity; four embers let go of the same point and fall. 1 px each, ivory -> gold -> amber -> ember.
    static const uint8_t spd[9] = { 9, 7, 11, 6, 8, 10, 5, 12, 7 };
    static const int8_t lat[9] = { 0, 3, -3, 5, -5, 2, -2, 6, -6 };
    static const int8_t emb_x[4] = { -4, -1, 2, 5 };
    for (int i = 0; i < MAX_FLARES; i++) {
        const Flare *f = &s_flares[i];
        if (!f->active) continue;
        int age = f->age;
        if (behind) continue;
        if (world_pixel_hidden(f->x, f->y, f->depth)) continue;
        int sx = f->x - cam_x, sy = f->y - cam_y;
        occ_begin(cam_x, cam_y, f->depth);                              // hidden by whoever stands in front of its feet
        if (f->kind == FL_BURST) {
            const int dx = f->dx, dy = f->dy;
            for (int k = 0; k < 9; k++) {
                const int fwd = (spd[k] * age) >> 2, sd = (lat[k] * age) >> 3, fall = (age * age) >> 4;
                const int x = sx + ((dx * fwd - dy * sd) >> 8);
                const int y = sy + ((dy * fwd + dx * sd) >> 8) + fall;
                if (age >= 10 && ((k + age) & 1)) continue;             // thinning out
                const int col = age < 3 ? FX_SH_IVORY : age < 6 ? FX_SH_GOLD : age < 9 ? FX_SH_AMBER : FX_SH_EMBER;
                put_px(t, x, y, col);
                if (k < 4 && age < 8) {                                 // the fast ones leave a short streak
                    put_px(t, x - ((dx * 2) >> 8), y - ((dy * 2) >> 8), age < 4 ? FX_SH_AMBER : FX_SH_EMBER);
                }
            }
            if (age >= 2) {
                for (int j = 0; j < 4; j++) {
                    const int a = age - 2;
                    put_px(t, sx + emb_x[j] + (((a + j) >> 2) & 1), sy - 1 + ((a * (3 + (j & 1))) >> 2), a < 5 ? FX_SH_AMBER : FX_SH_EMBER);
                }
            }
        } else {                                                        // FL_COLUMN
            int hh = col_h[age];
            for (int j = 0; j < hh; j++) {
                int hwid = j * 3 < hh ? 2 : (j * 3 < 2 * hh ? 1 : 0);
                int col = j * 4 < hh ? FX_SH_GOLD : j * 2 < hh ? FX_SH_AMBER : j * 4 < 3 * hh ? FX_SH_EMBER : FX_SH_CRIMSON;
                for (int dx = -hwid; dx <= hwid; dx++) {
                    if (hwid > 0 && (dx == hwid || dx == -hwid) && ((j + age + dx) & 3) == 0) continue;
                    put_px(t, sx + dx, sy - j, col);
                }
            }
        }
        occ_end();
    }
}

// Auto de Fe B / C (DESIGN.md 6.12.12): the enemy's own burn is consumed. Depth as in burn_marks_draw: behind = 1 is the floor
// pass (the far side of the body, covered by the sprite), behind = 0 the near side over the sprite.
// B (from burn A): columns of flame engulf the body from the feet (frames 0..9), then lift off the feet and climb away shrinking.
// C (from burn B): the ring of flames at the feet rises up the body as a sheet of flame, narrowing, and dissolves at the head.
static void consume_draw(const FxTarget *t, int cam_x, int cam_y, int behind) {
    const int v = g_design_variant;
    if (v == 0) return;
    for (int i = 0; i < MAX_CONSUME; i++) {
        const Consume *c = &s_consume[i];
        if (!c->active) continue;
        const int sx = c->x - cam_x, sy = c->y - cam_y, age = c->age, head = c->head, hw = c->hw;
        if (sx < -24 || sx >= SCREEN_W + 24 || sy < -4 || sy >= SCREEN_H + 40) continue;
        if (world_pixel_hidden(c->x, c->y - c->torso, c->y)) continue;
        if (v == 1) {
            int lift = 0, h;
            const int top = (head * 2) / 5 + 3;                         // tallest tongue: well below the head, they climb instead
            if (age < 10) h = 3 + (((top - 3) * age) / 9);
            else { lift = (head * (age - 9)) / 18; h = (top * (CONSUME_FRAMES - 1 - age)) / 18 + 1; }
            if (h < 1) continue;
            for (int k = 0; k < 7; k++) {
                if ((k & 1) != behind) continue;                          // odd columns burn on the far side of the body
                int kk = k - 3, ak = kk < 0 ? -kk : kk;
                int th = h - ak * 4 - (((age >> 1) + k * 3) % 3);
                if (th < 1) continue;
                if (!behind) occ_begin(cam_x, cam_y, c->y);
                flame_stack(t, sx + (kk * (hw - 2)) / 3, sy - lift, th, age + k);
                occ_end();
            }
        } else {
            const int lift = (head * age) / (CONSUME_FRAMES - 2);
            const int rx = hw - 2 - (((hw / 3) * age) / CONSUME_FRAMES);
            const int fh = age < 8 ? 5 : age < 20 ? 4 : 3;
            for (int k = 0; k < 16; k++) {
                const int a = k * 2;
                if ((s_ell_sin[a] < 0) != behind) continue;               // far half of the ring: behind the body
                if (((k + age) & 3) == 0) continue;                       // flicker
                if (age >= 22 && ((k + age) & 1)) continue;               // dissolving
                if (!behind) occ_begin(cam_x, cam_y, c->y + ((s_ell_sin[a] * rx) >> 9));
                flame_stack(t, sx + ((s_ell_cos[a] * rx) >> 8), sy - lift + ((s_ell_sin[a] * rx) >> 9), fh, age + k);
                occ_end();
            }
        }
    }
}

// Viatico siphon (DESIGN.md 6.12.11): a point of the quadratic curve victim -> bend -> chest, u = 0..256.
// The bend is lifted 22 px and pushed sideways by `lean`, so the path arcs instead of running straight.
static void siphon_point(const Siphon *q, int u, int lean, int cam_x, int cam_y, int *x, int *y) {
    const int x0 = q->x, y0 = q->y, x2 = s_hero_x, y2 = s_hero_y - VIATICO_CHEST;
    const int x1 = ((x0 + x2) >> 1) + lean, y1 = ((y0 + y2) >> 1) - 22;
    const int a = (256 - u) * (256 - u), b = 2 * u * (256 - u), c = u * u;
    *x = ((a * x0 + b * x1 + c * x2 + 32768) >> 16) - cam_x;
    *y = ((a * y0 + b * y1 + c * y2 + 32768) >> 16) - cam_y;
}

static void siphons_draw(const FxTarget *t, int cam_x, int cam_y) {
    const int v = g_design_variant == 2 ? 2 : 0;       // B was dropped (DESIGN.md 6.12.12): it renders like A
    for (int i = 0; i < MAX_SIPHONS; i++) {
        const Siphon *q = &s_siphons[i];
        if (!q->active) continue;
        const int age = q->age;
        const int u = (age * 256 * 9 / 8) / SIPHON_FRAMES;           // head position; reaches the chest at 8/9 of the life
        const int hu = u > 256 ? 256 : u;
        const int lean = (q->x < s_hero_x) ? -10 : 10;
        int x, y;
        if (v == 0) {
            // A: a thin thread, 2 px tall near its head; the head runs in and the tail follows 120/256 behind.
            const int tail = hu > 120 ? hu - 120 : 0;
            for (int w = tail; w <= hu; w += 4) {
                siphon_point(q, w, lean, cam_x, cam_y, &x, &y);
                int d = hu - w;
                put_px(t, x, y, d < 14 ? FX_SH_AMBER : d < 50 ? FX_SH_EMBER : d < 90 ? FX_SH_CRIMSON : FX_SH_DEEP);
                if (d < 70) put_px(t, x, y + 1, d < 30 ? FX_SH_CRIMSON : FX_SH_DEEP);
            }
        } else {
            // C: a pale soul wisp: a bright head weaving across the path, with a fading tail of smoke.
            for (int k = 0; k < 10; k++) {
                int du = hu - k * 9;
                if (du < 0) break;
                siphon_point(q, du, lean, cam_x, cam_y, &x, &y);
                int wob = (s_ell_sin[(du / 10 + age) & 31] * (4 - (k >> 1))) >> 8;   // weaves side to side, calmer along the tail
                x += wob;
                int col = k == 0 ? FX_SH_IVORY : k < 3 ? FX_SH_SMOKE_L : k < 5 ? FX_SH_SMOKE_M : FX_SH_ASH_A;
                put_px(t, x, y, col);
                put_px(t, x, y + 1, k < 5 ? FX_SH_SMOKE_M : FX_SH_ASH_A);
                if (k < 3) { put_px(t, x + 1, y, FX_SH_SMOKE_L); put_px(t, x - 1, y, FX_SH_SMOKE_L); put_px(t, x, y - 1, FX_SH_SMOKE_L); }
                if (k == 0) { put_px(t, x - 1, y - 1, FX_SH_GOLD); put_px(t, x + 1, y + 1, FX_SH_GOLD); }
            }
        }
        if (age >= SIPHON_FRAMES - 6) {                                 // arrival: a short crimson / ivory flash on the chest
            siphon_point(q, 256, 0, cam_x, cam_y, &x, &y);
            int col = v == 2 ? FX_SH_IVORY : FX_SH_CRIMSON;
            int r = age - (SIPHON_FRAMES - 6);
            for (int a = 0; a < 32; a += 4) put_px(t, x + ((s_ell_cos[a] * (1 + (r >> 1))) >> 8), y + ((s_ell_sin[a] * (1 + (r >> 1))) >> 8), col);
        }
    }
}

// Llaga Abierta B halo: a dithered pale ring round the body (drawn behind the sprite, so it reads as rim light), from 3 hearts
// missing; at 4 a second, wider ring that pulses. 16 / 32 points a frame at most.
static void llaga_halo_draw(const FxTarget *t, int cam_x, int cam_y) {
    const int m = s_llaga_missing;
    if (m < 3 || g_design_variant == 2) return;
    const int cx = s_hero_x - cam_x, cy = s_hero_y - 14 - cam_y;
    const int ph = (int)s_burn_tick;
    for (int a = (ph & 1); a < 32; a += 2) {                       // checker: half the points each frame, alternating
        int x = cx + ((s_ell_cos[a] * 11) >> 8), y = cy + ((s_ell_sin[a] * 17) >> 8);
        put_px(t, x, y, m >= 4 ? FX_SH_GOLD : FX_SH_SMOKE_L);
    }
    if (m >= 4) {
        const int r = 14 + ((ph >> 3) & 1) * 2;                      // slow pulse
        for (int a = ((ph >> 1) & 1); a < 32; a += 2) {
            int x = cx + ((s_ell_cos[a] * r) >> 8), y = cy + ((s_ell_sin[a] * (r + 8)) >> 8);
            put_px(t, x, y, (a & 2) ? FX_SH_SMOKE_M : FX_SH_ASH_A);
        }
    }
}

// Quemado embers: muted ember, amber and ash that fade with age; the flame tongue is two warm pixels
// that flicker. Hidden by walls in front of the enemy's feet.
static void burn_fx_draw(const FxTarget *t, int cam_x, int cam_y, int behind) {
    burn_marks_draw(t, cam_x, cam_y, behind);
    if (behind) llaga_halo_draw(t, cam_x, cam_y);
    consume_draw(t, cam_x, cam_y, behind);
    flares_draw(t, cam_x, cam_y, behind);
    if (!behind) siphons_draw(t, cam_x, cam_y);
    for (int i = 0; i < MAX_BURN_EMBERS; i++) {
        const BurnEmber *b = &s_burn_embers[i];
        if (!b->active || b->back != behind) continue;
        int sx = b->x - cam_x, sy = b->y - cam_y;
        if ((unsigned)(sx + 6) >= SCREEN_W + 12u || (unsigned)(sy + 6) >= SCREEN_H + 12u) continue;
        if (world_pixel_hidden(b->x, b->y, b->depth)) continue;
        if (!behind) occ_begin(cam_x, cam_y, b->depth);
        if (b->kind == 7) {                              // Llaga B: pale ascended mote, ivory fading to warm ash
            int f4 = (b->max_life - b->life) * 4 / b->max_life;
            put_px(t, sx, sy, f4 == 0 ? FX_SH_IVORY : f4 == 1 ? FX_SH_GOLD : f4 == 2 ? FX_SH_SMOKE_L : FX_SH_SMOKE_M);
            if (f4 == 0) put_px(t, sx, sy - 1, FX_SH_GOLD);
        } else if (b->kind == 6) {                       // Llaga B: blood drop falling from the chest wound, then a fading splat
            if (b->y < b->depth) {
                put_px(t, sx, sy, FX_SH_CRIMSON);
                put_px(t, sx, sy - 1, FX_SH_DEEP);
            } else {
                int age = b->max_life - b->life;
                if (age < 34 || (age & 1)) { put_px(t, sx - 1, sy, FX_SH_DEEP); put_px(t, sx, sy, FX_SH_CRIMSON); put_px(t, sx + 1, sy, FX_SH_DEEP); }
            }
        } else if (b->kind == 3) {                       // ash smoke (C)
            smoke_puff(t, sx, sy, b->max_life - b->life);
        } else if (b->kind == 1) {
            flame_stack(t, sx, sy, b->vx, (int)s_burn_tick + i);
        } else if (b->kind == 4 || b->kind == 5) {       // A: warm core fading to ash, big ones are a plus / 2x2
            int age = b->max_life - b->life, f5 = age * 5 / b->max_life;
            int col = f5 == 0 ? FX_SH_IVORY : f5 == 1 ? FX_SH_GOLD : f5 == 2 ? FX_SH_AMBER : f5 == 3 ? FX_SH_EMBER : FX_SH_ASH_B;
            put_px(t, sx, sy, col);
            if (b->kind == 5 && f5 < 3) {
                int c2 = f5 == 0 ? FX_SH_AMBER : FX_SH_EMBER;
                put_px(t, sx - 1, sy, c2); put_px(t, sx + 1, sy, c2); put_px(t, sx, sy - 1, c2);
                if (f5 == 0) put_px(t, sx, sy + 1, c2);
            } else if (b->kind == 5) {
                put_px(t, sx, sy - 1, FX_SH_ASH_C);
            }
        } else {
            int age3 = (b->max_life - b->life) * 3;
            put_px(t, sx, sy, age3 < b->max_life ? FX_SH_AMBER : age3 < 2 * b->max_life ? FX_SH_EMBER : FX_SH_ASH_B);
        }
        occ_end();
    }
}

// Martirio rings: expanding 2:1 ground ring, amber then ember then ash (floor pass, under the actors).
static void burn_rings_draw(const GroundTarget *g) {
    static const uint8_t radius[BURN_RING_FRAMES] = { 8, 12, 16, 19, 22, 25, 27, 29, 31, 32 };
    for (int i = 0; i < MAX_BURN_RINGS; i++) {
        const BurnRing *r = &s_burn_rings[i];
        if (!r->active) continue;
        int col = r->age < 3 ? FX_SH_AMBER : r->age < 7 ? FX_SH_EMBER : FX_SH_ASH_A;
        const int rr = (radius[r->age] * r->rmax) >> 5;
        const int v = g_design_variant;
        if (v != 0 && r->kind == RING_MARTIRIO) {
            if (v == 2) { gfx_ground_ring(g, r->x, r->y, rr >> 1, s_fx_rgb[col], 0); continue; }   // C: small ring + column
            // B: cross of four tongues along the 2:1 ground axes (x arm rr, y arm rr / 2), thick while it is young.
            if (world_pixel_hidden(r->x, r->y, r->y)) continue;
            const FxTarget ft = { g->buffer };
            int sx = r->x - g->cam_x, sy = r->y - g->cam_y, ry = rr >> 1, thick = r->age < 6;
            draw_line(&ft, sx - rr, sy, sx + rr, sy, col);
            draw_line(&ft, sx, sy - ry, sx, sy + ry, col);
            if (thick) {
                draw_line(&ft, sx - rr, sy + 1, sx + rr, sy + 1, col);
                draw_line(&ft, sx + 1, sy - ry, sx + 1, sy + ry, col);
            }
            flame_stack(&ft, sx - rr, sy, 2 + (rr >> 4), r->age); flame_stack(&ft, sx + rr, sy, 2 + (rr >> 4), r->age + 1);
            flame_stack(&ft, sx, sy - ry, 2 + (rr >> 4), r->age + 2); flame_stack(&ft, sx, sy + ry, 2 + (rr >> 4), r->age + 3);
            continue;
        }
        if (v == 1 && r->kind == RING_FLAGELADO) {
            // B: six thin lashes curling outwards; only the last 18 px of each are drawn so they read as flying.
            if (world_pixel_hidden(r->x, r->y, r->y)) continue;
            const FxTarget ft = { g->buffer };
            const int sx = r->x - g->cam_x, sy = r->y - g->cam_y;
            for (int k = 0; k < 6; k++) {
                int px = 0, py = 0, have = 0;
                for (int i = rr > 18 ? rr - 18 : 2; i <= rr; i += 3) {
                    int a = (k * 5 + (i >> 3) + (r->age >> 1)) & 31;
                    int x = sx + ((s_ell_cos[a] * i) >> 8), y = sy + ((s_ell_sin[a] * i) >> 9);
                    int c = i > rr - 5 ? FX_SH_AMBER : i > rr - 11 ? FX_SH_EMBER : FX_SH_CRIMSON;
                    if (have) {
                        draw_line(&ft, px, py, x, y, c);
                        if (i > rr - 11) draw_line(&ft, px, py + 1, x, y + 1, c);
                    }
                    px = x; py = y; have = 1;
                }
            }
            continue;
        }
        if (v == 2 && r->kind == RING_FLAGELADO) {
            // C: crimson outer ring, and an amber inner ring that follows 3 frames later at 2/3 of the reach.
            gfx_ground_ring(g, r->x, r->y, rr, s_fx_rgb[r->age < 6 ? FX_SH_CRIMSON : FX_SH_DEEP], 0);
            if (r->age >= 3) {
                int ri = (((radius[r->age - 3] * r->rmax) >> 5) * 5) >> 3;
                gfx_ground_ring(g, r->x, r->y, ri, s_fx_rgb[r->age < 7 ? FX_SH_AMBER : FX_SH_EMBER], 0);
            }
            continue;
        }
        gfx_ground_ring(g, r->x, r->y, rr, s_fx_rgb[col], 0);
    }
}

// Beat of Llaga Abierta C, a double beat (lub-dub): phase 0..31 of a 32-step beat; the speed is missing / 4 steps a frame.
static const uint8_t s_beat_r[32] = { 0, 3, 6, 8, 9, 10, 10, 9, 8, 6, 4, 2, 0, 0, 3, 6, 8, 9, 9, 8, 6, 4, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
static inline int llaga_phase(void) { return (int)((s_burn_tick * (uint32_t)s_llaga_missing) >> 2) & 31; }

// Llaga Abierta C: a red vignette on the border of the bottom screen, pulsing like a heart.
// Only border pixels are written: a dithered band whose width follows the beat and the missing hearts.
void weapons_render_overlay(uint16_t *buffer) {
    if (!buffer || g_design_variant != 2 || s_llaga_missing == 0) return;
    static const uint8_t mask[10] = { 0, 0, 1, 1, 3, 3, 7, 7, 7, 15 };
    const int beat = s_beat_r[llaga_phase()];
    const int w = 3 + (s_llaga_missing >= 3) + ((beat + 2) >> 2);                      // 3..9 px
    for (int y = 0; y < SCREEN_H; y++) {
        const int dy = y < SCREEN_H - 1 - y ? y : SCREEN_H - 1 - y;
        int x0 = 0, x1 = SCREEN_W;
        if (dy >= w) { x0 = w; x1 = SCREEN_W - w; }
        for (int pass = 0; pass < 2; pass++) {
            int a = pass ? x1 : 0, e = pass ? SCREEN_W : x0;
            if (dy < w) { if (pass) break; a = 0; e = SCREEN_W; }
            for (int x = a; x < e; x++) {
                int dx = x < SCREEN_W - 1 - x ? x : SCREEN_W - 1 - x;
                int d = dx < dy ? dx : dy;
                if (d >= w) continue;
                if (((x + (y << 1)) & mask[d]) != 0) continue;
                buffer[y * SCREEN_W + x] = s_fx_rgb[d < 2 ? (beat >= 6 ? FX_SH_EMBER : FX_SH_CRIMSON) : d < 5 ? FX_SH_CRIMSON : FX_SH_DEEP] | BIT(15);
            }
            dirty_row(y, a, e);
        }
    }
}

void weapons_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    GroundTarget ground = { buffer, cam_x, cam_y };
    burn_rings_draw(&ground);
    // READY flash: a dashed 2:1 warm glow ring on the floor around the feet, under the actors.
    if (s_aura_flash > 0 && s_aim_state == AIM_READY) {
        int ring = s_aura_flash == AURA_FLASH_FRAMES ? FX_SH_IVORY : FX_SH_GOLD;
        gfx_ground_ring(&ground, s_aura_x, s_aura_y, 12, s_fx_rgb[ring], 2);
    }
    // Look E at READY: a dashed muted crimson ring round the closed crown.
    const int cilicio = upgrades_has_relic(RELIC_CILICIO);
    if (s_aim_state == AIM_READY && aura_on(AURA_STYLE_E) && !cilicio)
        gfx_ground_ring(&ground, s_aura_x, s_aura_y, 7, s_fx_rgb[FX_SH_CRIMSON], 2);
    // Aura de Cilicio: always active around the hero while alive (heart modification).
    if (cilicio && !g_player_state.is_dead) {
        int cprog = aura_fx_live() ? (s_aura_prog_live > 160 ? s_aura_prog_live : 160) : 160;
        if (!aura_fx_live()) { s_aura_x = s_hero_x; s_aura_y = s_hero_y; }
        gfx_ground_ring(&ground, s_aura_x, s_aura_y, cilicio_radius(cprog), s_fx_rgb[FX_SH_EMBER], 2);
        FxTarget target = { buffer };
        aura_draw_pass(&target, cam_x, cam_y, 1);
        burn_fx_draw(&target, cam_x, cam_y, 1);
        if (aura_fx_live() && aura_on(AURA_STYLE_G)) glow_draw(&target, cam_x, cam_y, s_aura_prog_live);
        thorn_draw(&target, cam_x, cam_y, cprog);
        return;
    }
    FxTarget target = { buffer };
    aura_draw_pass(&target, cam_x, cam_y, 1);         // style L: arcs behind the body
    burn_fx_draw(&target, cam_x, cam_y, 1);           // far side of the effects attached to a body: the sprite covers it
    if (aura_fx_live()) {
        if (aura_on(AURA_STYLE_G)) glow_draw(&target, cam_x, cam_y, s_aura_prog_live);
        if (aura_on(AURA_STYLE_E)) thorn_draw(&target, cam_x, cam_y, s_aura_prog_live);
    }
}

void weapons_render_light(uint16_t *buffer, int cam_x, int cam_y) {
    (void)buffer; (void)cam_x; (void)cam_y;
}

void weapons_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    FxTarget target = { buffer };
    render_fx(&target, cam_x, cam_y);
    aura_draw_pass(&target, cam_x, cam_y, 0);         // style L: arcs in front of the body
    if (aura_fx_live() && aura_on(AURA_STYLE_H)) ash_draw(&target, cam_x, cam_y, s_aura_prog_live);
    burn_fx_draw(&target, cam_x, cam_y, 0);
}
