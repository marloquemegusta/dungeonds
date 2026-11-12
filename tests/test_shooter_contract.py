import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")
LASER_C = (ROOT / "source" / "enemy_laser.c").read_text(encoding="utf-8")
LASER_H = (ROOT / "include" / "enemy_laser.h").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def tuning(field):
    block = GAMEPLAY_C.split("[ENEMY_TYPE_SHOOTER] = {")[1].split("}")[0]
    return int(re.search(rf"\.{field} = (\d+)", block).group(1))


def define(name):
    return int(re.search(rf"#define {name} (\d+)", GAMEPLAY_H).group(1))


def shooter_function():
    return AI_C.split("static void update_shooter")[1].split("void enemy_ai_update")[0]


class ShooterLaserContractTest(unittest.TestCase):
    """DESIGN.md 6.9.1: POSITION -> LASER_AIM -> LASER_FIX -> LASER_FIRE -> COOLDOWN -> POSITION."""

    def test_state_machine_has_exactly_the_designed_states(self):
        enum = GAMEPLAY_H.split("typedef enum {\n    ENEMY_STATE_CHASE")[1].split("} EnemyState;")[0]
        states = re.findall(r"ENEMY_STATE_(\w+)", enum)
        self.assertEqual(states, ["ATTACK", "POSITION", "TELEGRAPH", "CHARGE", "RECOVER", "STUNNED",
                                  "LASER_AIM", "LASER_FIX", "LASER_FIRE", "COOLDOWN", "DEAD", "DORMANT"])
        for removed in ("IDLE", "ALERT", "SEARCH", "BURST", "last_seen", "los_lost"):
            self.assertNotIn(removed, shooter_function(), removed)

    def test_decided_timings(self):
        self.assertEqual(define("SHOOTER_LASER_TRACK_FRAMES") + define("SHOOTER_LASER_FIX_FRAMES"), 60)
        self.assertEqual(define("SHOOTER_LASER_FIX_FRAMES"), 20)
        self.assertEqual(define("SHOOTER_LASER_FIRE_FRAMES"), 8)
        self.assertEqual(tuning("attack_cooldown"), 90)
        self.assertEqual(define("SHOOTER_MAX_CHARGING"), 2)
        self.assertEqual(tuning("max_hp"), 200)
        self.assertEqual(tuning("speed"), 180)

    def test_tunables_are_marked(self):
        for line in GAMEPLAY_H.splitlines():
            if line.startswith("#define SHOOTER_"):
                self.assertIn("[TUNABLE-PLACEHOLDER]", line, line)

    def test_states_chain_in_order(self):
        body = shooter_function()
        aim = body.split("case ENEMY_STATE_LASER_AIM:")[1].split("case ENEMY_STATE_LASER_FIX:")[0]
        self.assertIn("e->state = ENEMY_STATE_LASER_FIX;", aim)
        fix = body.split("case ENEMY_STATE_LASER_FIX:")[1].split("case ENEMY_STATE_LASER_FIRE:")[0]
        self.assertIn("e->state = ENEMY_STATE_LASER_FIRE;", fix)
        fire = body.split("case ENEMY_STATE_LASER_FIRE:")[1].split("case ENEMY_STATE_COOLDOWN:")[0]
        self.assertIn("e->state = ENEMY_STATE_COOLDOWN;", fire)
        cooldown = body.split("case ENEMY_STATE_COOLDOWN:")[1].split("case ENEMY_STATE_POSITION:")[0]
        self.assertIn("e->state = ENEMY_STATE_POSITION;", cooldown)

    def test_the_line_follows_while_charging_and_is_locked_while_fixed(self):
        body = shooter_function()
        aim = body.split("case ENEMY_STATE_LASER_AIM:")[1].split("case ENEMY_STATE_LASER_FIX:")[0]
        self.assertIn("shooter_aim(e, player_x, player_y);", aim)
        for locked in ("LASER_FIX", "LASER_FIRE"):
            part = body.split(f"case ENEMY_STATE_{locked}:")[1].split("case ENEMY_STATE_")[0]
            self.assertNotIn("shooter_aim", part, locked)

    def test_beam_hurts_once_per_shot_inside_the_line_and_ignores_columns(self):
        fire = shooter_function().split("case ENEMY_STATE_LASER_FIRE:")[1].split("case ENEMY_STATE_COOLDOWN:")[0]
        self.assertIn("if (laser_covers(e, player_x, player_y)) player_take_hit(&g_player_state);", fire)
        covers = AI_C.split("static int laser_covers")[1].split("static int lasers_charging")[0]
        for wall_test in ("bullet_", "position_is_free", "line_is_walkable", "los_has_line_of_sight"):
            self.assertNotIn(wall_test, covers, wall_test)       # the beam does not stop at columns
        self.assertIn("SHOOTER_LASER_HALF_WIDTH", covers)
        self.assertIn("SHOOTER_LASER_LENGTH", covers)

    def test_at_most_two_lasers_charge_and_the_rest_wait(self):
        body = shooter_function().split("case ENEMY_STATE_POSITION:")[1]
        self.assertIn("lasers_charging(enemies, num_enemies) < SHOOTER_MAX_CHARGING", body)
        count = AI_C.split("static int lasers_charging")[1].split("static void update_shooter")[0]
        self.assertIn("ENEMY_STATE_LASER_AIM", count)
        self.assertIn("ENEMY_STATE_LASER_FIX", count)

    def test_band_and_speed(self):
        self.assertLess(tuning("preferred_dist_min"), tuning("preferred_dist_max"))
        hero = int(re.search(r'\{ "Corazon Abierto Hero", (\d+),', (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")).group(1))
        self.assertLess(tuning("speed"), hero)                    # the player can close the gap

    def test_it_backs_off_closes_in_and_strafes(self):
        body = AI_C.split("static void shooter_reposition")[1].split("static void shooter_aim")[0]
        self.assertIn("ground_dist < tuning->preferred_dist_min", body)
        self.assertIn("ground_dist > tuning->preferred_dist_max", body)
        self.assertIn("nav_next_step(", body)                     # no view: walks the field
        self.assertIn("strafing && !moved", body)                 # a blocked strafe reverses

    def test_a_shove_cancels_the_laser(self):
        stun = AI_C.split("if (e->stun_timer > 0) {")[1].split("continue;")[0]
        self.assertIn("ENEMY_STATE_LASER_AIM", stun)
        self.assertIn("ENEMY_STATE_LASER_FIX", stun)
        self.assertIn("e->state = ENEMY_STATE_POSITION;", stun)

    def test_it_only_charges_with_a_clear_bullet_line(self):
        body = shooter_function().split("case ENEMY_STATE_POSITION:")[1]
        self.assertIn("(e->has_los & VIEW_BULLET)", body)
        self.assertIn("bullet_line_is_free(wx, wy, px, py)", AI_C)

    def test_old_enemy_projectiles_are_gone(self):
        self.assertFalse((ROOT / "source" / "projectiles.c").exists())
        self.assertFalse((ROOT / "include" / "projectiles.h").exists())
        for text in (AI_C, MAIN_C, GAMEPLAY_H):
            self.assertNotIn("enemy_projectile", text)
        self.assertNotIn("BURST", GAMEPLAY_H)
        self.assertNotIn("projectile_speed", GAMEPLAY_H)


class LaserRenderContractTest(unittest.TestCase):
    def test_the_draw_loop_is_bounded(self):
        draw = LASER_C.split("static void draw_laser")[1].split("void enemy_lasers_render")[0]
        self.assertIn("for (int d = 1; d <= SHOOTER_LASER_LENGTH; d++)", draw)
        self.assertNotIn("while (1)", draw)
        self.assertNotIn("for (;;)", draw)
        self.assertLessEqual(draw.count("while"), 1)             # only the one-time perpendicular norm
        self.assertIn("(oy < 0 && ey < 0)", draw)                # off-screen beams skip the loop

    def test_it_draws_green_pixels_in_the_screen_buffer(self):
        self.assertIn("RGB15(6, 30, 10)", LASER_C)
        self.assertIn("dirty_row(y, x, x + 1);", LASER_C)
        self.assertIn("enemy_lasers_render(buffer, g_enemies, MAX_ENEMIES, cam_x, cam_y);", MAIN_C)

    def test_width_grows_from_aim_to_fix_to_fire(self):
        widths = LASER_C.split("static int laser_width")[1].split("}")[0]
        self.assertIn("LASER_FIRE) return 3;", widths)
        self.assertIn("LASER_FIX) return 2;", widths)
        self.assertIn("return 0;", widths)

    def test_no_floating_point(self):
        for text in (LASER_C, LASER_H, AI_C):
            self.assertIsNone(re.search(r"\b(?:float|double)\b", text))


if __name__ == "__main__":
    unittest.main()
