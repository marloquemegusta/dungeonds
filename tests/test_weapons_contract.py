import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEAPONS_H = (ROOT / "include" / "weapons.h").read_text(encoding="utf-8")
WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
GRENADE_H = (ROOT / "include" / "grenade.h").read_text(encoding="utf-8")
GRENADE_C = (ROOT / "source" / "grenade.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def parse_weapon_table():
    """Reads g_weapon_tuning from weapons.c into {name: {field: int}}."""
    start = WEAPONS_C.index("const WeaponTuning g_weapon_tuning")
    body = WEAPONS_C[start:WEAPONS_C.index("};\n", start)]
    table = {}
    for name, block in re.findall(r"\[(WEAPON_\w+)\]\s*=\s*\{(.*?)\n    \}", body, re.DOTALL):
        fields = {}
        for key, value in re.findall(r"\.(\w+)\s*=\s*(-?\d+)", block):
            fields[key] = int(value)
        table[name] = fields
    return table


def parse_enemy_hp():
    return {
        "charger": int(re.search(r"ENEMY_TYPE_CHARGER\] = \{\s*\.max_hp = (\d+)", GAMEPLAY_C).group(1)),
        "shooter": int(re.search(r"ENEMY_TYPE_SHOOTER\] = \{\s*\.max_hp = (\d+)", GAMEPLAY_C).group(1)),
        "skeleton": int(re.search(r"ENEMY_TYPE_SKELETON\] = \{\s*\.max_hp = (\d+)", GAMEPLAY_C).group(1)),
    }


def hits_to_kill(hp, damage):
    return -(-hp // damage)


class WeaponsContractTest(unittest.TestCase):
    def test_only_three_weapons_without_ammo(self):
        self.assertIn("WEAPON_SHOTGUN = 0", WEAPONS_H)
        self.assertIn("WEAPON_SNIPER", WEAPONS_H)
        self.assertIn("WEAPON_GRENADE", WEAPONS_H)
        for removed in ("WEAPON_PISTOL", "WEAPON_GATLING", "WEAPON_HEAVY", "max_ammo", "ammo_cost",
                        "spinup_delay"):
            self.assertNotIn(removed, WEAPONS_H, removed)
            self.assertNotIn(removed, WEAPONS_C, removed)
        self.assertEqual(set(parse_weapon_table()), {"WEAPON_SHOTGUN", "WEAPON_SNIPER", "WEAPON_GRENADE"})

    def test_sniper_point_blank_hits_to_kill(self):
        table = parse_weapon_table()
        hp = parse_enemy_hp()
        sniper = table["WEAPON_SNIPER"]
        self.assertEqual(sniper["damage_per_hit"], 150)   # scale 100 = 1.0
        self.assertEqual(hits_to_kill(hp["shooter"], sniper["damage_per_hit"]), 2)
        self.assertEqual(hits_to_kill(hp["charger"], sniper["damage_per_hit"]), 2)

    def test_enemy_health_scale_is_hundredths(self):
        self.assertEqual(parse_enemy_hp(), {"charger": 300, "shooter": 200, "skeleton": 100})

    def test_sniper_one_shots_the_skeleton(self):
        sniper = parse_weapon_table()["WEAPON_SNIPER"]
        self.assertEqual(hits_to_kill(parse_enemy_hp()["skeleton"], sniper["damage_per_hit"]), 1)

    def test_shotgun_point_blank_hits_to_kill(self):
        table = parse_weapon_table()
        hp = parse_enemy_hp()
        shotgun = table["WEAPON_SHOTGUN"]
        full_blast = shotgun["damage_per_hit"] * shotgun["pellets"]
        self.assertEqual(shotgun["damage_per_hit"], 40)    # scale 100 = 1.0
        self.assertGreaterEqual(full_blast, hp["shooter"])
        shots = hits_to_kill(hp["charger"], full_blast)
        self.assertEqual(shots, 2)                                # DESIGN.md 6.9.1: charger in 2 point-blank shots
        self.assertEqual(hits_to_kill(hp["skeleton"], full_blast), 1)

    def test_sniper_needs_minimum_aim_time(self):
        sniper = parse_weapon_table()["WEAPON_SNIPER"]
        self.assertGreaterEqual(sniper["aim_min_frames"], 20)   # ~0.4 s at 60 FPS
        self.assertLessEqual(sniper["aim_min_frames"], 30)

    def test_shotgun_has_pump_recoil_and_shove(self):
        shotgun = parse_weapon_table()["WEAPON_SHOTGUN"]
        self.assertGreaterEqual(shotgun["fire_cooldown"], 24)
        self.assertGreater(shotgun["recoil"], 0)
        self.assertGreater(shotgun["knockback"], 0)
        self.assertGreater(shotgun["stun_frames"], 0)

    def test_shots_leave_from_the_muzzle_not_the_feet(self):
        # Pellets and the sniper ray start at the muzzle ground point and are drawn at its height;
        # only a muzzle buried in a wall falls back to the player's ground point.
        origin = WEAPONS_C.split("static void shot_origin")[1].split("static void fire_shotgun")[0]
        self.assertIn("*x = in->muzzle_x;", origin)
        self.assertIn("bullet_position_is_free(in->muzzle_x, in->muzzle_y)", origin)
        self.assertIn("proj->x = origin_x;", WEAPONS_C)
        self.assertIn("proj->height = in->muzzle_h;", WEAPONS_C)
        self.assertIn("shot_origin(in, &cur_x, &cur_y);", WEAPONS_C)
        self.assertIn("player_muzzle(&in.muzzle_x, &in.muzzle_y, &in.muzzle_h);", MAIN_C)
        self.assertIn("g_character_muzzle", MAIN_C)

    def test_switching_weapons_keeps_the_fire_cooldown(self):
        cycle = WEAPONS_C.split("void weapons_cycle")[1].split("}\n")[0]
        self.assertNotIn("s_weapon_cooldown", cycle)

    def test_hitstop_never_shrinks_within_a_frame(self):
        self.assertIn("if (g_hitstop_frames < hitstop) g_hitstop_frames = hitstop;", GAMEPLAY_C)

    def test_sniper_stops_the_player_on_the_press_frame(self):
        self.assertIn("if (pressed && weapons_can_start_aim(&g_player_state)) s_rooted = 1;", MAIN_C)

    def test_shotgun_fires_once_per_touch(self):
        self.assertIn("if (in->touch_pressed && has_aim && s_weapon_cooldown <= 0)", WEAPONS_C)

    def test_sniper_fires_on_release_when_armed_and_can_be_cancelled(self):
        self.assertIn("if (s_aim_state == AIM_READY) {", WEAPONS_C)
        self.assertIn("s_aim_state = AIM_CANCELLED;", WEAPONS_C)
        self.assertIn("player->current_weapon = (WeaponType)((player->current_weapon + 1) % NUM_WEAPON_TYPES);", WEAPONS_C)
        self.assertIn("s_aim_state = AIM_IDLE;", WEAPONS_C)

    def test_sniper_pierces_each_enemy_once(self):
        self.assertIn("hit_mask & (1u << i)", WEAPONS_C)
        self.assertIn("bullet_position_is_free(nx, ny)", WEAPONS_C)

    def test_no_pixel_squares_for_pellets_or_impacts(self):
        # DESIGN.md 4.7: strokes with a fading trail replace the old squares and crosses.
        self.assertIn("draw_line(t, ", WEAPONS_C)
        self.assertNotIn("buffer[(sy + 1) * SCREEN_W + sx] = edge;", WEAPONS_C)

    def test_fx_are_drawn_on_both_screens(self):
        # DESIGN.md 4.7: aim laser, pellets, trail, flash and sparks show on both screens because
        # render_screen() (run once per screen) calls weapons_render() with its own camera.
        render = MAIN_C.split("static void render_screen")[1].split("static const char s_fps_chars")[0]
        self.assertIn("weapons_render(buffer, cam_x, cam_y);", render)
        self.assertIn("render_screen(s_top_page, s_dirty_top, view_x, view_y - SCREEN_H", MAIN_C)

    def test_grenade_contract(self):
        # DESIGN.md 4.9: 1.5 s fuse, 56 px radius, 300 at the centre falling to 75 at the rim (scale 100 = 1.0).
        grenade = parse_weapon_table()["WEAPON_GRENADE"]
        hp = parse_enemy_hp()
        self.assertIn("#define GRENADE_FUSE_FRAMES 90", GRENADE_H)
        self.assertIn("#define GRENADE_RADIUS 56", GRENADE_H)
        self.assertIn("#define GRENADE_DAMAGE_RIM 75", GRENADE_H)
        self.assertIn("#define GRENADE_MAX_ACTIVE 2", GRENADE_H)
        self.assertEqual(grenade["damage_per_hit"], 300)
        self.assertGreaterEqual(grenade["damage_per_hit"], hp["charger"])   # centre kills a charger
        self.assertGreaterEqual(75, 1)
        self.assertEqual(grenade["projectile_range"], 150)
        self.assertEqual(grenade["recoil"], 0)

    def test_grenade_uses_no_floating_point(self):
        for banned in (r"float", r"double", r"sinf", r"cosf", r"sqrt\("):
            self.assertIsNone(re.search(banned, GRENADE_C), banned)

    def test_grenade_friendly_fire_and_walls(self):
        self.assertIn("player_take_hit(", GRENADE_C)
        self.assertIn("bullet_position_is_free", GRENADE_C)

    def test_feel_hooks(self):
        self.assertIn("g_hitstop_frames", GAMEPLAY_C)
        self.assertIn("weapons_shake_offset", MAIN_C)
        self.assertIn("s_flash.life = 3;", WEAPONS_C)


class SniperAuraContractTest(unittest.TestCase):
    # DESIGN.md 4.9 "Aura de carga del francotirador": look K (lightning rays), C (bolt crown) or V (sparks).
    AURA = WEAPONS_C.split("// Sniper charge aura (DESIGN.md 4.9)")[1].split("void weapons_render_floor(")[0]
    FLOOR = WEAPONS_C.split("void weapons_render_floor(")[1].split("void weapons_render_light(")[0]
    LIGHT = WEAPONS_C.split("void weapons_render_light(")[1].split("void weapons_render(")[0]
    RENDER = WEAPONS_C.split("void weapons_render(")[1]

    @staticmethod
    def body(name, text):
        """Body of a C function, comments stripped."""
        start = text.index(name)
        end = text.index("\n}\n", start)
        return re.sub(r"//[^\n]*", "", text[start:end])

    def test_pools_and_caps(self):
        self.assertIn("#define AURA_MAX_BOLTS 14", WEAPONS_C)
        self.assertIn("#define AURA_MAIN_K 6", WEAPONS_C)
        self.assertIn("#define AURA_MAIN_C 8", WEAPONS_C)
        self.assertIn("#define AURA_BOLT_PTS 7", WEAPONS_C)
        self.assertIn("#define AURA_FORK_STEPS 8", WEAPONS_C)
        self.assertIn("#define AURA_MAX_STREAKS 24", WEAPONS_C)
        self.assertIn("#define AURA_BURST_STREAKS 12", WEAPONS_C)
        self.assertIn("static AuraBolt s_aura_bolts[AURA_MAX_BOLTS];", WEAPONS_C)
        self.assertIn("static AuraStreak s_aura_streaks[AURA_MAX_STREAKS];", WEAPONS_C)
        self.assertIn("int px[AURA_BOLT_PTS], py[AURA_BOLT_PTS];", WEAPONS_C)
        for gone in ("AuraStrand", "s_helix", "AuraSpark", "s_aura_sparks", "aura_stroke", "aura_chain_draw",
                     "aura_bolt_spawn", "aura_spark_spawn", "AURA_HELIX"):
            self.assertNotIn(gone, WEAPONS_C, gone)

    def test_per_frame_segment_budget(self):
        # K: 6 bolts x 6 steps + forks; C: 8 crown x 5 + 2 thin x 6 + forks. Forks share AURA_FORK_STEPS.
        k_total = 6 * 6 + 8
        c_total = 8 * 5 + 2 * 6 + 8
        self.assertLessEqual(k_total, 70)
        self.assertLessEqual(c_total, 70)
        self.assertIn("int count = 2 + ((prog * 4) >> 8);", self.AURA)            # K: 2..6 bolts
        self.assertIn("int nseg = 4 + ((prog * 2) >> 8);", self.AURA)             # K: 4..6 steps
        self.assertIn("int crowns = 3 + ((prog * 5) >> 8);", self.AURA)           # C: 3..8 crown bolts
        self.assertIn("int crown_steps = 3 + ((prog * 2) >> 8);", self.AURA)      # C: 3..5 steps
        self.assertIn("int wraps = prog >> 7;", self.AURA)                        # C: 0..2 thin
        self.assertIn("int wrap_steps = 4 + ((prog * 2) >> 8);", self.AURA)       # 4..6 steps
        self.assertIn("if (prog > 256) prog = 256;", self.AURA)
        self.assertIn("s_aura_fork_steps = AURA_FORK_STEPS;", self.AURA)
        self.assertIn("if (nseg > s_aura_fork_steps) nseg = s_aura_fork_steps;", self.AURA)

    def test_aura_uses_no_floating_point(self):
        for banned in (r"\bfloat\b", r"\bdouble\b", r"\bsinf?\(", r"\bcosf?\(", r"\bsqrtf?\("):
            self.assertIsNone(re.search(banned, self.AURA), banned)
            self.assertIsNone(re.search(banned, self.FLOOR), banned)
            self.assertIsNone(re.search(banned, self.RENDER), banned)

    def test_bolt_directions_come_from_the_integer_table(self):
        self.assertIn("static const int s_ell_sin[32] = {", WEAPONS_C)
        self.assertIn("static const int s_ell_cos[32] = {", WEAPONS_C)
        walk = self.body("static void aura_bolt_walk(AuraBolt *b, int x8, int y8, int heading, int nseg, int fork_ok) {", self.AURA)
        self.assertIn("x8 += s_ell_cos[heading] * AURA_STEP;", walk)
        self.assertIn("y8 += s_ell_sin[heading] * AURA_STEP;", walk)
        self.assertIn("#define AURA_STEP 3", WEAPONS_C)
        self.assertIn("heading = (heading + s_aura_turn[(aura_rand8() * AURA_TURN_KINDS) >> 8]) & 31;", walk)
        self.assertIn("static const int s_aura_turn[AURA_TURN_KINDS] = {-4, -3, -2, 2, 3, 4};", WEAPONS_C)
        self.assertIn("b->px[k] = (x8 >> 8) + aura_jitter(1);", walk)

    def test_hot_helpers_avoid_division(self):
        for name in ("static int aura_rand8(void)", "static int aura_jitter(int amp)",
                     "static void aura_bolt_walk(", "static void aura_fork(", "static void aura_bolt_make(",
                     "static void aura_regenerate(", "static void aura_bolt_draw(", "static void aura_seg(",
                     "static void aura_draw_pass("):
            self.assertNotIn("/", self.body(name, self.AURA + self.FLOOR + self.RENDER), name)

    def test_seg_keeps_the_truncating_halve_and_a_hard_cap(self):
        seg = self.body("static void aura_seg(", self.AURA)
        self.assertIn("for (int n = 0; n < AURA_SEG_MAX_STEPS; n++) {", seg)
        self.assertIn("#define AURA_SEG_MAX_STEPS 48", WEAPONS_C)
        self.assertIn("int err = dx > dy ? dx >> 1 : -(dy >> 1);", seg)

    def test_fork_is_depth_one(self):
        fork = self.body("static void aura_fork(", self.AURA)
        self.assertIn("aura_bolt_walk(c, x8, y8, hc, nseg, 0);", fork)
        self.assertNotIn("aura_fork(", fork.split("\n", 1)[1])
        walk = self.body("static void aura_bolt_walk(AuraBolt *b, int x8, int y8, int heading, int nseg, int fork_ok) {", self.AURA)
        self.assertIn("if (fork_ok && k == fork_at", walk)
        self.assertIn("aura_fork(b, x8, y8, heading);", walk)

    def test_bolts_are_rebuilt_every_two_or_three_frames(self):
        update = self.body("static void aura_update(void) {", self.AURA)
        self.assertIn("if (--s_aura_regen <= 0) {", update)
        self.assertIn("s_aura_regen = ready ? 2 : 2 + (aura_rand8() & 1);", update)
        self.assertIn("aura_regenerate(prog);", update)
        self.assertIn("#define AURA_BOLT_LIFE 3", WEAPONS_C)
        self.assertIn("if (charging && g_aura_style != AURA_STYLE_V) {", update)
        self.assertIn("s_aura_regen = 0;", update)
        regen = self.body("static void aura_regenerate(int prog) {", self.AURA)
        self.assertIn("s_aura_rot = (s_aura_rot + 1) & 31;", regen)

    def test_anchors_on_the_feet_ellipse_and_climbing_tangent(self):
        make = self.body("static void aura_bolt_make(", self.AURA)
        self.assertIn("int ax = s_aura_x + ((s_ell_cos[a] * rx) >> 8);", make)
        self.assertIn("int ay = s_aura_y + ((s_ell_sin[a] * rx) >> 9) - h;", make)
        self.assertIn("b->back = s_ell_sin[a] < 0;", make)
        climb = self.body("static int aura_climb_heading(int a) {", self.AURA)
        self.assertIn("return s_ell_sin[t] < 0 ? t : (a + 24) & 31;", climb)

    def test_crown_from_ground_and_thin_wraps(self):
        regen = self.body("static void aura_regenerate(int prog) {", self.AURA)
        self.assertIn("aura_bolt_make(&s_aura_bolts[i], a, 9, 0, heading, crown_steps, 2);", regen)
        self.assertIn("aura_bolt_make(&s_aura_bolts[AURA_MAIN_C + w], a, 11, h, heading, wrap_steps, 1);", regen)
        self.assertIn("int heading = (24 + side * (1 + ((aura_rand8() * 4) >> 8))) & 31;", regen)
        self.assertIn("int h = 8 + ((aura_rand8() * 10) >> 8);", regen)     # wraps at mid height
        self.assertIn("int hmax = 4 + ((prog * 22) >> 8);", regen)          # K anchors grow in height

    def test_k_thin_and_c_two_px_colours(self):
        draw = self.body("static void aura_bolt_draw(", self.AURA)
        self.assertNotIn("FX_BLUE_DARK", WEAPONS_C)                                                    # no dark halo
        self.assertIn("if (b->thick == 2 && k < 2) {", draw)                                           # crown base: 2 px
        self.assertIn("aura_seg(t, x0 + ox, y0 + oy, x1 + ox, y1 + oy, cam_x, cam_y, FX_BLUE_LIGHT, -1, b->occl);", draw)
        self.assertIn("aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_WHITE, FX_BLUE_LIGHT, b->occl);", draw)   # 1 px, blue alternate
        self.assertIn("(alt >= 0 && (n & 1)) ? alt : color", self.body("static void aura_seg(", self.AURA))
        regen = self.body("static void aura_regenerate(int prog) {", self.AURA)
        self.assertIn("aura_bolt_make(&s_aura_bolts[i], a, 10, h, heading, nseg, 1);", regen)   # K: thin

    def test_back_half_is_drawn_before_the_sprites_and_front_half_after(self):
        self.assertIn("aura_draw_pass(&target, cam_x, cam_y, 1);", self.FLOOR)
        self.assertIn("aura_draw_pass(&target, cam_x, cam_y, 0);", self.RENDER)
        self.assertNotIn("aura_draw_pass", self.LIGHT)
        draw_pass = self.body("static void aura_draw_pass(", self.AURA)
        self.assertIn("if (b->active && b->back == behind) aura_bolt_draw(t, b, cam_x, cam_y);", draw_pass)
        self.assertIn("if (g_aura_style == AURA_STYLE_V) {", draw_pass)
        main = MAIN_C
        floor = main.index("weapons_render_floor(buffer, cam_x, cam_y);")
        blit = main.index("draw_player(buffer, cam_x, cam_y);")
        light = main.index("weapons_render_light(buffer, cam_x, cam_y);")
        proj = main.index("weapons_render(buffer, cam_x, cam_y);")
        self.assertLess(floor, blit)
        self.assertLess(blit, light)
        self.assertLess(light, proj)

    def test_wall_occlusion_per_bolt_and_per_pixel(self):
        self.assertIn("world_span_hidden(y, x0 - 1, x1 + 2, s_aura_y)", self.AURA)
        self.assertIn("if (occl && world_pixel_hidden(wx, wy, s_aura_y)) return;", self.AURA)
        self.assertIn("b->occl = aura_points_hidden(b->px, b->py, b->n);", self.AURA)

    def test_streaks_v_unchanged(self):
        spawn = self.body("static void aura_streak_spawn(", self.AURA)
        self.assertIn("int rx = rng_range(6, 10);", spawn)
        self.assertIn("s->life = rng_range(14, 20);", spawn)
        draw = self.body("static void aura_draw_streaks(", self.AURA)
        self.assertIn("int color = above < 5 ? FX_WHITE : above < 10 ? FX_YELLOW : top;", draw)
        tone = self.body("static int aura_top_color(void) {", self.AURA)
        self.assertIn("FX_ORANGE", tone)
        update = self.body("static void aura_update(void) {", self.AURA)
        self.assertIn("if (charging && g_aura_style == AURA_STYLE_V && rng_range(0, 255) < 70 + (prog >> 1)) {", update)
        self.assertIn("aura_streak_spawn(6, 14, rng_range(1, 1 + (prog >> 7)));", update)

    def test_stops_on_release_death_or_switch(self):
        charging = self.body("static int aura_charging(void) {", self.AURA)
        self.assertIn("s_aim_state == AIM_AIMING", charging)
        self.assertIn("s_aim_state == AIM_READY", charging)
        self.assertNotIn("AIM_CANCELLED", charging)
        self.assertIn("WEAPON_SNIPER", charging)
        self.assertIn("!g_player_state.is_dead", charging)
        age = self.body("static int aura_age(", self.AURA)
        self.assertIn("if (!charging && *life - *age > keep) *life = *age + keep;", age)
        update = self.body("static void aura_update(void) {", self.AURA)
        self.assertIn("aura_age(&b->age, &b->life, charging, 2)", update)
        self.assertIn("aura_age(&s->age, &s->life, charging, 3)", update)
        reset = self.body("static void aura_reset(void) {", self.AURA)
        self.assertIn("s_aura_bolts[i].active = 0;", reset)
        self.assertIn("s_aura_streaks[i].active = 0;", reset)
        self.assertIn("s_aura_flash = 0;", reset)
        self.assertIn("s_aura_regen = 0;", reset)
        cycle = WEAPONS_C.split("void weapons_cycle")[1].split("}\n")[0]
        self.assertIn("aura_reset();", cycle)
        init = WEAPONS_C.split("void weapons_init(void) {")[1].split("\n}\n")[0]
        self.assertIn("aura_reset();", init)

    def test_ready_flash_ring_on_floor_and_burst(self):
        self.assertIn("#define AURA_FLASH_FRAMES 3", WEAPONS_C)
        self.assertIn("gfx_ground_ring(&ground, s_aura_x, s_aura_y, 12, s_fx_rgb[FX_WHITE], 0);", self.FLOOR)
        self.assertIn("s_aim_state == AIM_READY", self.FLOOR)
        self.assertNotIn("gfx_ground_ring", self.LIGHT)
        burst = self.body("static void aura_on_ready(void) {", self.AURA)
        self.assertIn("s_aura_flash = AURA_FLASH_FRAMES;", burst)
        self.assertIn("aura_streak_spawn(12, 14, 2);", burst)
        self.assertIn("i < AURA_BURST_STREAKS", burst)
        self.assertIn("aura_on_ready();", WEAPONS_C)

    def test_palette_has_blue_entries_and_matching_table(self):
        enum_body = "FX_CORE = 0" + WEAPONS_C.split("enum {\n    FX_CORE = 0")[1].split("FX_NUM_COLORS")[0]
        names = set(re.findall(r"\bFX_[A-Z_0-9]+\b", enum_body))
        table = WEAPONS_C.split("static const uint16_t s_fx_rgb[FX_NUM_COLORS] = {")[1].split("};")[0]
        self.assertEqual(table.count("RGB15("), len(names))
        self.assertIn("FX_BLUE_LIGHT", names)
        self.assertNotIn("FX_BLUE_DARK", names)

    def test_key_y_cycles_k_c_v_and_the_hud_shows_it(self):
        self.assertIn("int g_aura_style = 0;", WEAPONS_C)
        self.assertIn("extern int g_aura_style;", WEAPONS_H)
        self.assertIn("char weapons_aura_style_letter(void);", WEAPONS_H)
        self.assertIn("#define AURA_STYLE_COUNT 3", WEAPONS_H)
        self.assertIn("enum { AURA_STYLE_K = 0, AURA_STYLE_C = 1, AURA_STYLE_V = 2 };", WEAPONS_H)
        self.assertIn("static const char letters[AURA_STYLE_COUNT] = {'K', 'C', 'V'};", WEAPONS_C)
        self.assertIn("if (keys_down & KEY_Y) {\n        g_aura_style = (g_aura_style + 1) % AURA_STYLE_COUNT;\n    }", MAIN_C)
        self.assertLess(MAIN_C.index("keys_down & KEY_SELECT"), MAIN_C.index("keys_down & KEY_Y"))
        self.assertIn('"WPN:%s FX:%c%c"', MAIN_C)
        self.assertIn("weapons_aura_style_letter());", MAIN_C)
        self.assertIn("char labels[HUD_LINES][32];", MAIN_C)

    def test_pixels_go_through_put_px(self):
        put = WEAPONS_C.split("static inline void put_px")[1].split("}\n")[0]
        self.assertIn("dirty_row(y, x, x + 1);", put)
        self.assertIn("put_px(t, sx, sy, color);", self.AURA)

    def test_aura_is_fed_by_the_feet_not_the_muzzle(self):
        self.assertIn("s_aura_x = TO_INT(in->player_x);", WEAPONS_C)
        self.assertIn("s_aura_y = TO_INT(in->player_y);", WEAPONS_C)


class SniperCollimationContractTest(unittest.TestCase):
    AIM = WEAPONS_C.split("// Collimation band: at each ray point")[1].split("// Parts with volume")[0]

    def test_progress_is_set_once_per_frame_and_reset(self):
        self.assertIn("static int s_aim_prog = 0;", WEAPONS_C)
        self.assertIn("s_aim_prog = (s_aim_timer << 8) / aim_frames;", WEAPONS_C)
        self.assertIn("if (s_aim_prog > 256) s_aim_prog = 256;", WEAPONS_C)
        self.assertEqual(WEAPONS_C.count("/ aim_frames;"), 1)
        init = WEAPONS_C.split("void weapons_init(void) {")[1].split("\n}\n")[0]
        self.assertIn("s_aim_prog = 0;", init)
        cycle = WEAPONS_C.split("void weapons_cycle")[1].split("}\n")[0]
        self.assertIn("s_aim_prog = 0;", cycle)
        self.assertIn("s_aim_timer = 0;\n            s_aim_prog = 0;", WEAPONS_C)

    def test_collimation_uses_no_floating_point_or_divide(self):
        code = re.sub(r"//[^\n]*", "", self.AIM)
        for banned in (r"\bfloat\b", r"\bdouble\b"):
            self.assertIsNone(re.search(banned, code), banned)
        self.assertNotIn("/", code)
        self.assertNotIn("%", code)

    def test_cloud_is_capped_at_128_points_and_has_no_blink(self):
        self.assertIn("if (n > 128) n = 128;", self.AIM)
        self.assertIn("uint32_t seed", self.AIM)
        self.assertNotIn("((s_aim_timer >> 1) & 1)", self.AIM)
        self.assertNotIn("rng_range", self.AIM)

    def test_dim_colour_and_green_threshold(self):
        self.assertIn("FX_AIM_DIM,", WEAPONS_C)
        self.assertIn("RGB15(15, 4, 5)                                // FX_AIM_DIM", WEAPONS_C)
        self.assertIn("s_aim_prog >= 180", self.AIM)
        self.assertIn("int w = (6 * (256 - s_aim_prog)) >> 8;", self.AIM)


if __name__ == "__main__":
    unittest.main()
