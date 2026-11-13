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


class SniperFuegoContractTest(unittest.TestCase):
    # DESIGN.md 6.10 (chosen 2026-11-12): the sniper always draws fuego (C), whatever g_fx_style says.
    SNIPER = WEAPONS_C.split("// Sniper shot (fire palette, DESIGN.md 6.10)")[1].split("// Moves and ages")[0]
    IMPACT = WEAPONS_C.split("static void spawn_impact(")[1].split("static void spawn_flash(")[0]
    AIM = WEAPONS_C.split("// Sniper fuego (DESIGN.md 6.10):")[1].split("// Parts with volume")[0]
    TRAIL = WEAPONS_C.split("// Sniper trail (DESIGN.md 6.10, fuego):")[1].split("// Pellets: A short streak")[0]

    def test_sniper_effects_ignore_the_style_selector(self):
        for code in (self.SNIPER, self.AIM, self.TRAIL):
            self.assertNotIn("g_fx_style", code)
        self.assertIn("int style = sniper ? 2 : g_fx_style;", self.IMPACT)
        self.assertIn("s_sparks[i].sniper = sniper;", self.IMPACT)

    def test_only_the_fire_palette_is_left_for_the_sniper(self):
        for gone in ("FX_AIM", "FX_TRAIL_A", "FX_TRAIL_B", "FX_TRAIL_C", "FX_MARK", "FX_BLUE_LIGHT",
                     "FX_DARK", "FX_AIM_DIM", "FXP_RING", "FXP_MARK", "AIM_EMBERS", "render_fire_beam"):
            self.assertNotIn(gone, WEAPONS_C, gone)
        self.assertIn("put_px(t, px, py, ((s_aim_timer >> 1) & 1) ? FX_SH_IVORY : FX_SH_GOLD);", self.AIM)
        self.assertIn("FXP_CROSS, 4, in->muzzle_x, in->muzzle_y", self.SNIPER)
        cross = WEAPONS_C.split("case FXP_CROSS: {")[1].split("case FXP_FRAG")[0]
        self.assertIn("FX_SH_GOLD : FX_SH_EMBER", cross)

    def test_shot_trail_and_embers_keep_the_fuego_numbers(self):
        self.assertIn("int core = life >= 4 ? FX_SH_IVORY : life >= 2 ? FX_SH_GOLD : FX_SH_EMBER;", self.TRAIL)
        self.assertIn("for (int i = 0; i < 16; i++) {", self.TRAIL)
        self.assertIn("int w = (6 * (256 - s_aim_prog)) >> 8;", self.AIM)
        self.assertIn("int n = 8 + ((s_aim_prog * 16) >> 8);", self.AIM)     # 8..24 embers a frame
        self.assertIn("if (age == 7) continue;", self.AIM)                   # each ember lives 7 frames
        self.assertIn("int o = (h & 1) ? w : -w;", self.AIM)                 # embers leave from the rim
        self.assertNotIn("rng_range", self.AIM)
        self.assertIn("if (s_aim_len <= 0 || w <= 0) return;", self.AIM)
        self.assertIn("s_aim_prog >= 180", self.AIM)


class SniperAuraContractTest(unittest.TestCase):
    # DESIGN.md 4.9 / 6.10: the sniper aura has one look now, flame tongues (F2). K, F1 and F3 are gone.
    AURA = WEAPONS_C.split("// Sniper charge aura (DESIGN.md 4.9, 6.10)")[1].split("void weapons_render_floor(")[0]
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
        self.assertIn("#define AURA_MAX_BOLTS 8", WEAPONS_C)
        self.assertIn("#define AURA_BOLT_PTS 6", WEAPONS_C)
        self.assertIn("static AuraBolt s_aura_bolts[AURA_MAX_BOLTS];", WEAPONS_C)
        self.assertIn("int px[AURA_BOLT_PTS], py[AURA_BOLT_PTS];", WEAPONS_C)
        for gone in ("AuraStreak", "s_aura_streaks", "AURA_MAX_STREAKS", "AURA_BURST_STREAKS", "AURA_FORK",
                     "AURA_MAIN_RAYS", "AURA_FLAMES", "AURA_TURN_KINDS", "s_aura_turn", "aura_fork", "aura_bolt_walk",
                     "aura_bolt_make", "aura_bolt_draw", "aura_streak_spawn", "aura_draw_streaks", "aura_on_ready",
                     "aura_climb_heading", "AuraStrand", "s_helix", "AuraSpark", "s_aura_sparks", "aura_stroke",
                     "aura_chain_draw", "aura_bolt_spawn", "aura_spark_spawn", "AURA_HELIX"):
            self.assertNotIn(gone, WEAPONS_C, gone)

    def test_per_frame_segment_budget(self):
        # 8 flames x 5 steps = 40 segments a frame (cap 70).
        self.assertLessEqual(8 * 5, 70)
        self.assertIn("int count = 6 + ((prog * 2) >> 8);", self.AURA)            # 6..8 flames
        self.assertIn("int nseg = 3 + ((prog * 2) >> 8);", self.AURA)             # 3..5 steps
        self.assertIn("int hmax = 2 + ((prog * 6) >> 8);", self.AURA)             # bases 2..8 px
        self.assertIn("if (prog > 256) prog = 256;", self.AURA)

    def test_aura_uses_no_floating_point(self):
        for banned in (r"\bfloat\b", r"\bdouble\b", r"\bsinf?\(", r"\bcosf?\(", r"\bsqrtf?\("):
            self.assertIsNone(re.search(banned, self.AURA), banned)
            self.assertIsNone(re.search(banned, self.FLOOR), banned)
            self.assertIsNone(re.search(banned, self.RENDER), banned)

    def test_flame_directions_come_from_the_integer_table(self):
        self.assertIn("static const int s_ell_sin[32] = {", WEAPONS_C)
        self.assertIn("static const int s_ell_cos[32] = {", WEAPONS_C)
        flame = self.body("static void aura_flame_make(", self.AURA)
        self.assertIn("int zig = (k & 1) ? 2 : -2;", flame)
        self.assertIn("int heading = (base + zig + aura_jitter(1)) & 31;", flame)
        self.assertIn("x8 += s_ell_cos[heading] * AURA_STEP;", flame)
        self.assertIn("y8 += s_ell_sin[heading] * AURA_STEP;", flame)
        self.assertIn("#define AURA_STEP 3", WEAPONS_C)
        self.assertIn("b->px[k] = x8 >> 8;", flame)                          # no jitter on the flame points

    def test_hot_helpers_avoid_division(self):
        for name in ("static int aura_rand8(void)", "static int aura_jitter(int amp)",
                     "static void aura_flame_make(", "static void aura_regenerate(", "static void aura_flame_draw(",
                     "static void aura_seg(", "static void aura_draw_pass("):
            self.assertNotIn("/", self.body(name, self.AURA + self.FLOOR + self.RENDER), name)

    def test_seg_keeps_the_truncating_halve_and_a_hard_cap(self):
        seg = self.body("static void aura_seg(", self.AURA)
        self.assertIn("for (int n = 0; n < AURA_SEG_MAX_STEPS; n++) {", seg)
        self.assertIn("#define AURA_SEG_MAX_STEPS 48", WEAPONS_C)
        self.assertIn("int err = dx > dy ? dx >> 1 : -(dy >> 1);", seg)

    def test_bolts_are_rebuilt_every_two_or_three_frames(self):
        update = self.body("static void aura_update(void) {", self.AURA)
        self.assertIn("if (--s_aura_regen <= 0) {", update)
        self.assertIn("s_aura_regen = ready ? 2 : 2 + (aura_rand8() & 1);", update)
        self.assertIn("aura_regenerate(prog);", update)
        self.assertIn("#define AURA_BOLT_LIFE 3", WEAPONS_C)
        self.assertIn("if (charging) {", update)
        self.assertIn("if (g_aura_style != AURA_STYLE_L) {", update)     # the flames stay on look L
        self.assertIn("s_aura_regen = 0;", update)
        regen = self.body("static void aura_regenerate(int prog) {", self.AURA)
        self.assertIn("s_aura_rot = (s_aura_rot + 1) & 31;", regen)
        self.assertIn("int a = (s_aura_rot + i * 4) & 31;", regen)         # eight tongues round the ellipse
        self.assertIn("aura_flame_make(&s_aura_bolts[i], a, 9, h, nseg);", regen)

    def test_anchors_on_the_feet_ellipse(self):
        make = self.body("static void aura_flame_make(", self.AURA)
        self.assertIn("int ax = s_aura_x + ((s_ell_cos[a] * rx) >> 8);", make)
        self.assertIn("int ay = s_aura_y + ((s_ell_sin[a] * rx) >> 9) - h;", make)
        self.assertIn("b->back = s_ell_sin[a] < 0;", make)

    def test_flame_colours_and_no_other_looks(self):
        self.assertNotIn("FX_BLUE_LIGHT", WEAPONS_C)
        self.assertNotIn("FX_BLUE_DARK", WEAPONS_C)
        seg = self.body("static void aura_seg(", self.AURA)
        self.assertIn("(alt >= 0 && (n & 1)) ? alt : color", seg)
        flame = self.body("static void aura_flame_draw(", self.AURA)
        self.assertIn("if (k < 2) {", flame)                                  # base: 2 px
        self.assertIn("aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_SH_IVORY, FX_SH_GOLD, b->occl);", flame)
        self.assertIn("aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_SH_CRIMSON, FX_SH_DEEP, b->occl);", flame)  # tip
        for gone in ("aura_bolt_draw", "aura_streak"):
            self.assertNotIn(gone, WEAPONS_C, gone)

    def test_back_half_is_drawn_before_the_sprites_and_front_half_after(self):
        self.assertIn("aura_draw_pass(&target, cam_x, cam_y, 1);", self.FLOOR)
        self.assertIn("aura_draw_pass(&target, cam_x, cam_y, 0);", self.RENDER)
        self.assertNotIn("aura_draw_pass", self.LIGHT)
        draw_pass = self.body("static void aura_draw_pass(", self.AURA)
        self.assertIn("if (!b->active || b->back != behind) continue;", draw_pass)
        self.assertIn("aura_flame_draw(t, b, cam_x, cam_y);", draw_pass)
        main = MAIN_C
        floor = main.index("weapons_render_floor(buffer, cam_x, cam_y);")
        blit = main.index("draw_player(buffer, cam_x, cam_y);")
        light = main.index("weapons_render_light(buffer, cam_x, cam_y);")
        proj = main.index("weapons_render(buffer, cam_x, cam_y);")
        self.assertLess(floor, blit)
        self.assertLess(blit, light)
        self.assertLess(light, proj)

    def test_wall_occlusion_per_flame_and_per_pixel(self):
        self.assertIn("world_span_hidden(y, x0 - 1, x1 + 2, s_aura_y)", self.AURA)
        self.assertIn("if (occl && world_pixel_hidden(wx, wy, s_aura_y)) return;", self.AURA)
        self.assertIn("b->occl = aura_points_hidden(b->px, b->py, b->n);", self.AURA)

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
        reset = self.body("static void aura_reset(void) {", self.AURA)
        self.assertIn("s_aura_bolts[i].active = 0;", reset)
        self.assertIn("s_aura_flash = 0;", reset)
        self.assertIn("s_aura_regen = 0;", reset)
        cycle = WEAPONS_C.split("void weapons_cycle")[1].split("}\n")[0]
        self.assertIn("aura_reset();", cycle)
        init = WEAPONS_C.split("void weapons_init(void) {")[1].split("\n}\n")[0]
        self.assertIn("aura_reset();", init)

    def test_ready_flash_ring_on_floor(self):
        self.assertIn("#define AURA_FLASH_FRAMES 3", WEAPONS_C)
        self.assertIn("int ring = s_aura_flash == AURA_FLASH_FRAMES ? FX_SH_IVORY : FX_SH_GOLD;", self.FLOOR)
        self.assertIn("gfx_ground_ring(&ground, s_aura_x, s_aura_y, 12, s_fx_rgb[ring], 2);", self.FLOOR)
        self.assertIn("s_aim_state == AIM_READY", self.FLOOR)
        self.assertNotIn("gfx_ground_ring", self.LIGHT)
        self.assertIn("s_aura_flash = AURA_FLASH_FRAMES;", WEAPONS_C)

    def test_palette_matches_the_enum(self):
        enum_body = "FX_CORE = 0" + WEAPONS_C.split("enum {\n    FX_CORE = 0")[1].split("FX_NUM_COLORS")[0]
        names = set(re.findall(r"\bFX_[A-Z_0-9]+\b", enum_body))
        table = WEAPONS_C.split("static const uint16_t s_fx_rgb[FX_NUM_COLORS] = {")[1].split("};")[0]
        self.assertEqual(table.count("RGB15("), len(names))
        for gone in ("FX_BLUE_LIGHT", "FX_MARK", "FX_AIM", "FX_AIM_READY", "FX_AIM_DIM", "FX_TRAIL_A", "FX_DARK"):
            self.assertNotIn(gone, names, gone)

    def test_key_select_still_cycles_the_fx_style_first(self):
        self.assertLess(MAIN_C.index("keys_down & KEY_SELECT"), MAIN_C.index("g_fx_style = (g_fx_style + 1) % FX_STYLE_COUNT;"))

    def test_pixels_go_through_put_px(self):
        put = WEAPONS_C.split("static inline void put_px")[1].split("}\n")[0]
        self.assertIn("dirty_row(y, x, x + 1);", put)
        self.assertIn("put_px(t, sx, sy, color);", self.AURA)

    def test_aura_is_fed_by_the_feet_not_the_muzzle(self):
        self.assertIn("s_aura_x = TO_INT(in->player_x);", WEAPONS_C)
        self.assertIn("s_aura_y = TO_INT(in->player_y);", WEAPONS_C)


class AuraLooksContractTest(unittest.TestCase):
    """Second round of sniper auras (DESIGN.md, segunda ronda de auras): selector and looks G, E and H."""
    # The new state, helpers and aura_update (aura_update keeps the flame divide, so it is cut out of the scan).
    SRC = WEAPONS_C.split("// Free slot of a mote pool")[1].split("static void aura_update(void) {")[0]
    DRAWS = "// Tapered ray walk for G (glow):" + WEAPONS_C.split("// Tapered ray walk for G (glow):")[1].split("void weapons_render_floor(")[0]
    FLOOR = WEAPONS_C.split("void weapons_render_floor(")[1].split("void weapons_render_light(")[0]
    RENDER = WEAPONS_C.split("void weapons_render(")[1]
    NEW = SRC + DRAWS

    @staticmethod
    def code(text):
        return re.sub(r"//[^\n]*", "", text)

    def test_selector_has_four_looks_and_letters(self):
        self.assertIn("#define AURA_STYLE_COUNT 4", WEAPONS_H)
        self.assertIn("enum { AURA_STYLE_L = 0, AURA_STYLE_G = 1, AURA_STYLE_E = 2, AURA_STYLE_H = 3 };", WEAPONS_H)
        self.assertIn("extern int g_aura_style;", WEAPONS_H)
        self.assertIn("char weapons_aura_style_letter(void);", WEAPONS_H)
        self.assertIn("{'L', 'G', 'E', 'H'}", WEAPONS_C)
        self.assertIn("int g_aura_style = 0;", WEAPONS_C)

    def test_key_y_cycles_and_the_hud_shows_both_letters(self):
        self.assertIn("if (keys_down & KEY_Y) {", MAIN_C)
        self.assertIn("g_aura_style = (g_aura_style + 1) % AURA_STYLE_COUNT;", MAIN_C)
        self.assertIn('"WPN:%s FX:%c%c"', MAIN_C)
        self.assertIn("weapons_aura_style_letter());", MAIN_C)

    def test_sandbox_sets_the_look_from_flag_bits_3_4(self):
        sandbox_h = (ROOT / "include" / "sandbox.h").read_text(encoding="utf-8")
        sandbox_c = (ROOT / "source" / "sandbox.c").read_text(encoding="utf-8")
        self.assertIn("#define SANDBOX_FLAG_AURA_SHIFT 3", sandbox_h)
        self.assertIn("#define SANDBOX_FLAG_AURA_MASK  (3 << SANDBOX_FLAG_AURA_SHIFT)", sandbox_h)
        self.assertIn("g_aura_style = ((flags & SANDBOX_FLAG_AURA_MASK) >> SANDBOX_FLAG_AURA_SHIFT) % AURA_STYLE_COUNT;",
                      sandbox_c)

    def test_looks_stay_in_their_own_branch(self):
        update = WEAPONS_C.split("static void aura_update(void) {")[1].split("\n}\n")[0]
        self.assertIn("if (g_aura_style != AURA_STYLE_L) {", update)
        self.assertIn("aura_fx_update(charging, ready, prog);", update)
        self.assertIn("if (g_aura_style == AURA_STYLE_E) {", self.NEW)
        self.assertIn("if (g_aura_style == AURA_STYLE_H) {", self.NEW)

    def test_caps_are_fixed_and_commented(self):
        self.assertIn("#define GLOW_RAYS 12", WEAPONS_C)
        self.assertIn("#define GLOW_MAX_LEN 14", WEAPONS_C)
        self.assertIn("#define THORN_SPIKES 16", WEAPONS_C)
        self.assertLessEqual(16, 24)                              # contract cap of the spikes
        self.assertIn("#define THORN_DROPS 16", WEAPONS_C)
        self.assertIn("#define ASH_VOLUTES 6", WEAPONS_C)
        self.assertIn("#define ASH_EMBERS 16", WEAPONS_C)
        self.assertIn("contract cap 24", WEAPONS_C)
        self.assertIn("cap 6", WEAPONS_C)
        self.assertIn("cap 16", WEAPONS_C)

    def test_every_loop_is_bounded_by_a_fixed_cap(self):
        # Pool sizes and macros; "n" is the pool size argument of mote_free; "w" is the volute width (clamped to 4);
        # "12" and "2" are the burst count and the two rows of a volute.
        allowed = {"GLOW_RAYS", "THORN_SPIKES", "THORN_DROPS", "ASH_VOLUTES", "ASH_EMBERS", "AURA_MAX_BOLTS",
                   "AURA_SEG_MAX_STEPS", "n", "w", "12", "2"}
        code = self.code(self.NEW)
        bounds = re.findall(r"for \(int \w+ = 0; \w+ < (\w+|\d+); \w+\+\+\)", code)
        self.assertTrue(bounds)
        for bound in bounds:
            self.assertIn(bound, allowed, bound)

    def test_glow_geometry(self):
        self.assertIn("static int glow_len(int prog) {", self.NEW)
        self.assertIn("return 4 + ((prog * (GLOW_MAX_LEN - 4)) >> 8);", self.NEW)    # 4..14 px
        self.assertIn("int shortl = (len * 171) >> 8;", self.NEW)                    # alternate long and short
        self.assertIn("int l = (i & 1) ? shortl : len;", self.NEW)
        self.assertIn("if ((s_aura_tick & 3) == 0) s_glow_rot = (s_glow_rot + 1) & 31;", self.NEW)  # 1 step / 4 frames
        self.assertIn("FX_SH_IVORY : FX_SH_GOLD", self.DRAWS)

    def test_glow_is_centred_on_the_chest_muzzle(self):
        self.assertIn("s_aura_cx = TO_INT(in->muzzle_x);", WEAPONS_C)
        self.assertIn("s_aura_cy = TO_INT(in->muzzle_y) - in->muzzle_h;", WEAPONS_C)
        self.assertIn("s_aura_cy += dy_px;", WEAPONS_C)                               # follows the scroll

    def test_thorn_and_ash_geometry(self):
        self.assertIn("return 12 - ((prog * 6) >> 8);", self.NEW)                   # closes 12 -> 6 px
        self.assertIn("int a = (2 * (aura_rand8() & 15)) & 31;", self.NEW)          # 16 spikes, 2 steps apart
        self.assertIn("aura_seg(t, x0, y0, x1, y1, cam_x, cam_y, FX_BLACK, FX_SH_DEEP, 1);", self.DRAWS)
        self.assertIn("int target = 3 + ((prog * 3) >> 8);", self.NEW)              # 3..6 volutes
        self.assertIn("int w = 2 + (v->age >> 3);", self.DRAWS)

    def test_palette_has_the_new_colour_in_the_enum_and_table(self):
        enum_body = WEAPONS_C.split("enum {\n    FX_CORE = 0")[1].split("FX_NUM_COLORS")[0]
        self.assertIn("FX_BLACK,", enum_body)
        table = WEAPONS_C.split("static const uint16_t s_fx_rgb[FX_NUM_COLORS] = {")[1].split("};")[0]
        self.assertIn("FX_SH_IVORY", table)

    def test_no_float_and_no_divide_in_the_new_looks(self):
        code = self.code(self.NEW)
        for banned in (r"\bfloat\b", r"\bdouble\b", r"\bsinf?\(", r"\bcosf?\(", r"\bsqrtf?\("):
            self.assertIsNone(re.search(banned, code), banned)
        self.assertNotIn("/", code)
        self.assertNotIn("%", code)

    def test_draw_passes_floor_for_glow_and_thorns_front_for_ash(self):
        self.assertIn("if (g_aura_style == AURA_STYLE_G) glow_draw(", self.FLOOR)
        self.assertIn("if (g_aura_style == AURA_STYLE_E) thorn_draw(", self.FLOOR)
        self.assertIn("if (aura_fx_live() && g_aura_style == AURA_STYLE_H) ash_draw(", self.RENDER)
        self.assertNotIn("ash_draw(", self.FLOOR)
        self.assertNotIn("glow_draw(", self.RENDER)

    def test_thorn_ring_only_at_ready_in_the_floor_pass(self):
        self.assertIn("if (s_aim_state == AIM_READY && g_aura_style == AURA_STYLE_E)", self.FLOOR)
        self.assertIn("gfx_ground_ring(&ground, s_aura_x, s_aura_y, 7, s_fx_rgb[FX_SH_CRIMSON], 2);", self.FLOOR)

    def test_the_new_looks_stop_with_the_charge_after_a_few_frames(self):
        self.assertIn("#define AURA_FADE_FRAMES 3", WEAPONS_C)
        self.assertIn("return aura_charging() || s_aura_fade > 0;", self.NEW)
        cycle = WEAPONS_C.split("void weapons_cycle")[1].split("}\n")[0]
        self.assertIn("aura_reset();", cycle)


class SniperCollimationContractTest(unittest.TestCase):
    AIM = WEAPONS_C.split("// Collimation band:")[1].split("// Parts with volume")[0]

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

    def test_aim_band_is_the_only_collimation_shape(self):
        self.assertIn("static void aim_band(", WEAPONS_C)
        self.assertIn("aim_band(t, px, py, w, centre, FX_SH_CRIMSON, FX_SH_DEEP);", self.AIM)
        self.assertNotIn("aim_halo", WEAPONS_C)

    def test_dim_colour_and_ready_threshold(self):
        self.assertIsNone(re.search(r"\bFX_AIM_DIM\b", WEAPONS_C))
        self.assertIsNotNone(re.search(r"RGB15\(27, 20, 11\),\s+// FX_SH_GOLD", WEAPONS_C))
        self.assertIn("s_aim_prog >= 180", self.AIM)
        self.assertIn("int w = (6 * (256 - s_aim_prog)) >> 8;", self.AIM)


if __name__ == "__main__":
    unittest.main()
