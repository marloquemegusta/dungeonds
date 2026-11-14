import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")
LASER_C = (ROOT / "source" / "enemy_laser.c").read_text(encoding="utf-8")
LASER_H = (ROOT / "include" / "enemy_laser.h").read_text(encoding="utf-8")
GROUNDFX_C = (ROOT / "source" / "groundfx.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
SANDBOX_C = (ROOT / "source" / "sandbox.c").read_text(encoding="utf-8")
ENCOUNTERS_C = (ROOT / "source" / "encounters.c").read_text(encoding="utf-8")


def tuning(field):
    block = GAMEPLAY_C.split("[ENEMY_TYPE_SHOOTER] = {")[1].split("}")[0]
    return int(re.search(rf"\.{field} = (\d+)", block).group(1))


def define(name):
    value = re.search(rf"#define {name} ([A-Z0-9_]+)", GAMEPLAY_H).group(1)
    return int(value) if value.isdigit() else define(value)


def shooter_function():
    return AI_C.split("static void update_shooter")[1].split("ITCM_CODE void enemy_ai_update")[0]


def fire_function():
    return AI_C.split("static void ojo_fire")[1].split("// Advances the sentence gesture")[0]


class OjoGazeContractTest(unittest.TestCase):
    """DESIGN.md 6.10 "Mirada colimada": CHASE -> TRACK -> LOCK -> SENTENCE -> COOLDOWN -> CHASE."""

    def test_state_machine_has_exactly_the_designed_states(self):
        enum = GAMEPLAY_H.split("typedef enum {\n    ENEMY_STATE_CHASE")[1].split("} EnemyState;")[0]
        states = re.findall(r"ENEMY_STATE_(\w+)", enum)
        # The first seven keep their values: the charger scenarios read them by number.
        self.assertEqual(states, ["ATTACK", "POSITION", "TELEGRAPH", "CHARGE", "RECOVER", "STUNNED",
                                  "TRACK", "LOCK", "SENTENCE", "COOLDOWN", "DEAD", "DORMANT"])
        for removed in ("LASER_AIM", "LASER_FIX", "LASER_FIRE", "shooter_aim", "laser_covers", "lasers_charging",
                        "shooter_reposition", "CONDEMNED", "ENEMY_STATE_LOOK", "g_condemn", "CondemnState",
                        "gaze_update_player", "s_gaze_seen"):
            self.assertNotIn(removed, AI_C, removed)
            self.assertNotIn(removed, GAMEPLAY_H, removed)
            self.assertNotIn(removed, GAMEPLAY_C, removed)
            self.assertNotIn(removed, MAIN_C, removed)

    def test_no_cone_or_shared_count_leftovers(self):
        for removed in ("OJO_CONE_", "OJO_FILL_FRAMES", "OJO_DRAIN_RATE", "OJO_CLOSE_FRAMES", "OJO_TURN_",
                        "OJO_LOSE_FRAMES", "gaze_x", "gaze_y", "condemn_reset"):
            for text in (AI_C, GAMEPLAY_H, GAMEPLAY_C, LASER_C, LASER_H, MAIN_C, SANDBOX_C, ENCOUNTERS_C):
                self.assertNotIn(removed, text, removed)
        for removed in ("enemy_gaze_render_floor", "enemy_gaze_render_light", "draw_cone_ex"):
            for text in (LASER_C, LASER_H, MAIN_C):
                self.assertNotIn(removed, text, removed)

    def test_decided_cifras(self):
        self.assertEqual(define("OJO_TRACK_FRAMES"), 40)
        self.assertEqual(define("OJO_LOCK_FRAMES"), 20)
        self.assertIn("#define OJO_AIM_FRAMES (OJO_TRACK_FRAMES + OJO_LOCK_FRAMES)", GAMEPLAY_H)   # 60 frames of mouth charge
        self.assertEqual(define("OJO_MAX_LOOKING"), 2)
        self.assertEqual(define("OJO_SIGHT_RANGE"), 140)
        self.assertEqual(tuning("attack_cooldown"), 90)
        self.assertEqual(tuning("max_hp"), 300)
        self.assertEqual(tuning("speed"), 110)
        self.assertLessEqual(define("OJO_BEAM_FRAMES"), 6)          # gesture of 4-6 frames

    def test_tunables_are_marked(self):
        for line in GAMEPLAY_H.splitlines():
            if line.startswith("#define OJO_") and not line.startswith("#define OJO_ONE"):
                self.assertIn("[TUNABLE-PLACEHOLDER]", line, line)

    def test_states_chain_in_order(self):
        body = shooter_function()
        track = body.split("case ENEMY_STATE_TRACK:")[1].split("case ENEMY_STATE_LOCK:")[0]
        self.assertIn("e->state = ENEMY_STATE_LOCK;", track)
        self.assertIn("e->state_timer = OJO_LOCK_FRAMES;", track)
        lock = body.split("case ENEMY_STATE_LOCK:")[1].split("case ENEMY_STATE_SENTENCE:")[0]
        self.assertIn("e->state = ENEMY_STATE_SENTENCE;", lock)
        self.assertIn("ojo_fire(e, player_x, player_y);", lock)
        sentence = body.split("case ENEMY_STATE_SENTENCE:")[1].split("case ENEMY_STATE_COOLDOWN:")[0]
        self.assertIn("e->state = ENEMY_STATE_COOLDOWN;", sentence)
        cooldown = body.split("case ENEMY_STATE_COOLDOWN:")[1].split("case ENEMY_STATE_POSITION:")[0]
        self.assertIn("e->state = ENEMY_STATE_CHASE;", cooldown)
        chase = body.split("case ENEMY_STATE_CHASE:")[1]
        self.assertIn("e->state = ENEMY_STATE_TRACK;", chase)
        self.assertIn("e->state_timer = OJO_TRACK_FRAMES;", chase)
        # LOCK and SENTENCE are entered only from the FSM above.
        self.assertNotIn("ENEMY_STATE_LOCK;", body.replace("case ENEMY_STATE_LOCK:", "").replace("e->state = ENEMY_STATE_LOCK;", ""))

    def test_the_line_follows_in_track_and_freezes_in_lock(self):
        body = shooter_function()
        track = body.split("case ENEMY_STATE_TRACK:")[1].split("case ENEMY_STATE_LOCK:")[0]
        self.assertIn("e->aim_px = px;", track)
        self.assertIn("e->aim_py = py;", track)
        lock = body.split("case ENEMY_STATE_LOCK:")[1].split("case ENEMY_STATE_SENTENCE:")[0]
        self.assertNotIn("aim_px =", lock)                            # the point stays where the hero was
        self.assertNotIn("e->dir =", lock)

    def test_walls_and_columns_cut_the_gaze_and_the_beam(self):
        track = shooter_function().split("case ENEMY_STATE_TRACK:")[1].split("case ENEMY_STATE_LOCK:")[0]
        self.assertIn("los_has_line_of_sight(wx, wy, px, py, 0)", track)   # no clear line: the point stays
        # Entering TRACK needs a clear line, not only the cached walking flags.
        chase = shooter_function().split("case ENEMY_STATE_CHASE:")[1]
        self.assertIn("los_has_line_of_sight(wx, wy, px, py, 0)", chase)
        self.assertIn("VIEW_SIGHT", chase)
        # The beam is cut at the first wall or column and only hurts up to the cut.
        fire = fire_function()
        self.assertIn("ojo_ray_wall_dist(mxi, myi, ux << 7, uy << 7, OJO_BEAM_MAX_LEN)", fire)
        self.assertIn("along <= cut", fire)

    def test_the_sentence_hits_once_near_the_locked_line_and_respects_iframes(self):
        fire = fire_function()
        self.assertEqual(fire.count("player_take_hit(&g_player_state)"), 1)    # i-frames live inside it
        self.assertIn("cross <= OJO_HIT_HALF_WIDTH", fire)
        self.assertIn("along >= 0", fire)
        body = shooter_function()
        self.assertEqual(body.count("ojo_fire("), 1)                             # fired once, on entering SENTENCE
        beam = body.split("case ENEMY_STATE_SENTENCE:")[1].split("case ENEMY_STATE_COOLDOWN:")[0]
        self.assertNotIn("player_take_hit", beam)                  # the beam frames only draw

    def test_at_most_two_ojos_aim_and_the_rest_wait_or_walk(self):
        chase = shooter_function().split("case ENEMY_STATE_CHASE:")[1]
        self.assertIn("ojos_looking(enemies, num_enemies) < OJO_MAX_LOOKING", chase)
        count = AI_C.split("static int ojos_looking")[1].split("// Look loop")[0]
        for state in ("TRACK", "LOCK", "SENTENCE"):
            self.assertIn(f"ENEMY_STATE_{state}", count)
        self.assertIn("e->state = ENEMY_STATE_POSITION;", chase)   # waits close by without a slot
        self.assertIn("chase_step(", chase)                         # otherwise it keeps closing in

    def test_search_has_no_light_only_a_slow_sweep(self):
        chase = shooter_function().split("case ENEMY_STATE_CHASE:")[1]
        self.assertIn("s_search_sweep", chase)
        render = LASER_C.split("void enemy_lasers_render")[1].split("// ----")[0]
        self.assertNotIn("ENEMY_STATE_CHASE", render)              # nothing is drawn while it searches

    def test_a_shove_breaks_the_aim(self):
        stun = AI_C.split("if (e->stun_timer > 0) {")[1].split("continue;")[0]
        for state in ("TRACK", "LOCK", "SENTENCE"):
            self.assertIn(f"ENEMY_STATE_{state}", stun)
        self.assertIn("e->state = ENEMY_STATE_CHASE;", stun.split("ENEMY_TYPE_SHOOTER")[1].split("ENEMY_TYPE_CHARGER")[0])

    def test_it_walks_slowly_and_the_player_can_outrun_it(self):
        hero = int(re.search(r'\{ "Corazon Abierto Hero", (\d+),', (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")).group(1))
        self.assertLess(tuning("speed"), hero // 2)                 # about a third of the hero

    def test_no_projectile_or_old_laser_leftovers(self):
        self.assertFalse((ROOT / "source" / "projectiles.c").exists())
        self.assertFalse((ROOT / "include" / "projectiles.h").exists())
        for text in (AI_C, MAIN_C, GAMEPLAY_H):
            self.assertNotIn("enemy_projectile", text)
            self.assertNotIn("SHOOTER_LASER", text)
        self.assertNotIn("position_duration", GAMEPLAY_H)

    def test_new_enemies_start_with_a_clean_aim(self):
        for text in (SANDBOX_C, ENCOUNTERS_C):
            self.assertIn("e->aim_px = e->aim_py = e->beam_len = 0;", text)


class OjoRenderContractTest(unittest.TestCase):
    def test_the_beam_loop_is_bounded(self):
        draw = LASER_C.split("static void draw_laser")[1].split("// ----")[0]
        self.assertIn("for (int d = 1; d <= len; d++)", draw)
        self.assertIn("if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;", draw)
        self.assertNotIn("while (1)", draw)
        self.assertNotIn("for (;;)", draw)
        self.assertLessEqual(draw.count("while"), 1)                 # only the one-time perpendicular norm
        self.assertIn("(oy < -8 && ey < -8)", draw)                  # off-screen beams skip the loop
        render = LASER_C.split("void enemy_lasers_render")[1].split("// ----")[0]
        self.assertIn("e->state == ENEMY_STATE_SENTENCE", render)    # the sentence draws the beam
        self.assertIn("draw_laser(buffer, e, cam_x, cam_y)", render)

    def test_the_band_is_bounded_cut_by_walls_and_occluded(self):
        band = LASER_C.split("static void draw_gaze_band")[1].split("void enemy_lasers_render")[0]
        self.assertIn("for (int d = 1; d <= len; d++)", band)
        self.assertIn("if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;", band)
        self.assertNotIn("while", band)
        self.assertNotIn("for (;;)", band)
        self.assertIn("ray_hit_dist(", band)                         # stops at the first wall or column
        self.assertIn("world_pixel_hidden(px + cam_x, py + cam_y, depth)", band)
        self.assertIn("(oy < -8 && ey2 < -8)", band)                 # off-screen bands skip the loop
        self.assertIn("OJO_LANTERN_HEIGHT", band)                    # it leaves the lantern, not the mouth
        self.assertIn("OJO_TARGET_HEIGHT", band)                     # and reaches the hero's chest
        self.assertIn("dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);", band)
        render = LASER_C.split("void enemy_lasers_render")[1].split("// ----")[0]
        self.assertIn("ENEMY_STATE_TRACK", render)
        self.assertIn("ENEMY_STATE_LOCK", render)

    def test_the_band_narrows_with_the_whole_aim(self):
        prog = LASER_C.split("static int ojo_aim_progress")[1].split("static inline void band_plot")[0]
        self.assertIn("OJO_TRACK_FRAMES - e->state_timer", prog)
        self.assertIn("OJO_TRACK_FRAMES + OJO_LOCK_FRAMES - e->state_timer", prog)
        self.assertIn("div32(", prog)
        band = LASER_C.split("static void draw_gaze_band")[1].split("void enemy_lasers_render")[0]
        self.assertIn("OJO_BAND_HALF * (256 - prog)", band)           # wide at first, 0 on the last frame
        self.assertIn("if (w == 0)", band)                            # armed: 1 px line

    def test_the_beam_is_spectral_and_one_dirty_row_per_row(self):
        self.assertIn("OJO_FX_CORE", LASER_C)
        self.assertIn("dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);", LASER_C)
        self.assertIn("enemy_lasers_render(buffer, g_enemies, MAX_ENEMIES, cam_x, cam_y);", MAIN_C)
        beam = MAIN_C.index("enemy_lasers_render(buffer, g_enemies, MAX_ENEMIES, cam_x, cam_y);")
        actors = MAIN_C.index("for (int i = 0; i < count; i++)", MAIN_C.index("PP_T0(pp_blit);"))
        self.assertLess(beam, actors)                            # actor sprites occlude the beam and the band

    def test_the_ojo_palette_is_desaturated(self):
        # DESIGN.md 6.10 "Efectos desaturados": a muted verdigris ramp, no pure green, no pure white, peak near FX_SH_IVORY.
        colors = re.findall(r"#define OJO_FX_\w+\s+\(RGB15\((\d+), (\d+), (\d+)\)", LASER_C)
        self.assertEqual(len(colors), 5)
        for r, g, b in map(lambda c: tuple(int(x) for x in c), colors):
            self.assertLessEqual(max(r, g, b), 29)                    # the hero's ivory peak (29,25,19)
            self.assertLess(g - max(r, b), 10, (r, g, b))             # tinted green, not a primary
            self.assertGreaterEqual(r, 2)                             # never a pure channel
        peak = max(colors, key=lambda c: sum(int(x) for x in c))
        self.assertLess(min(int(x) for x in peak), 24)                # not white
        self.assertNotIn("TINT_", LASER_C)

    def test_ground_line_is_a_bounded_bresenham(self):
        line = GROUNDFX_C.split("static void ground_line")[1].split("// Walks the ellipse")[0]
        self.assertIn("if (x0 == x1 && y0 == y1) break;", line)      # always terminates at the end point
        self.assertIn("void gfx_ground_line(", GROUNDFX_C)

    def test_mouth_charges_with_its_own_aim_and_no_mark_is_drawn_on_the_hero(self):
        self.assertNotIn("condemn_mark_render", MAIN_C + LASER_C + LASER_H)
        glow = LASER_C.split("void enemy_ojo_mouth_glow_render")[1].split("// ----")[0]
        self.assertIn("ojo_aim_progress(e)", glow)
        self.assertNotIn("g_condemn", glow)
        self.assertIn("enemy_muzzle(e, &mx, &my, &mh);", glow)
        draw = MAIN_C.split("static void draw_enemy")[1].split("static void bone_effect_pixel")[0]
        self.assertIn("enemy_ojo_mouth_glow_render(buffer, e, (int)(e - g_enemies), cam_x, cam_y, s_draw_item_depth);", draw)

    def test_ojo_is_native_56x56_with_its_rendered_body_hit_volume(self):
        config = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
        self.assertIn('{ "El Ojo del Tribunal", 110, 9, 56, 56, 80, 80 }', config)
        self.assertNotIn("blit_ojo_scaled", MAIN_C)
        hit = (ROOT / "include" / "hitvolume.h").read_text(encoding="utf-8")
        self.assertRegex(hit, r"#define OJO_BODY_HIT_RX 18\b")
        self.assertRegex(hit, r"#define OJO_BODY_HIT_RY 22\b")

    def test_no_floating_point(self):
        for text in (LASER_C, LASER_H, AI_C):
            self.assertIsNone(re.search(r"\b(?:float|double)\b", text))

    def test_hot_loops_have_no_c_division(self):
        # Rule 2: hardware div32 / sqrt32 or shifts only in the gaze code.
        for text in (shooter_function(), fire_function()):
            self.assertIsNone(re.search(r"[^/*]/ [^/*]", re.sub(r"//.*", "", text)))
            self.assertNotIn(" % ", re.sub(r"//.*", "", text))


if __name__ == "__main__":
    unittest.main()
