import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")
PROJECTILES_C = (ROOT / "source" / "projectiles.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def tuning(field):
    block = GAMEPLAY_C.split("[ENEMY_TYPE_SHOOTER] = {")[1].split("}")[0]
    return int(re.search(rf"\.{field} = (\d+)", block).group(1))


class ShooterContractTest(unittest.TestCase):
    """DESIGN.md 4.5: POSITION -> TELEGRAPH -> BURST(3) -> COOLDOWN -> POSITION."""

    def test_state_machine_has_exactly_the_designed_states(self):
        enum = GAMEPLAY_H.split("typedef enum {\n    ENEMY_STATE_CHASE")[1].split("} EnemyState;")[0]
        states = re.findall(r"ENEMY_STATE_(\w+)", enum)
        self.assertEqual(states, ["ATTACK", "POSITION", "TELEGRAPH", "BURST", "COOLDOWN", "DEAD", "DORMANT"])
        shooter = AI_C.split("static void update_shooter")[1].split("void enemy_ai_update")[0]
        for removed in ("IDLE", "ALERT", "SEARCH", "AIM", "last_seen", "los_lost"):
            self.assertNotIn(removed, shooter, removed)

    def test_telegraph_is_about_a_third_of_a_second(self):
        self.assertTrue(15 <= tuning("telegraph_duration") <= 21)

    def test_burst_is_three_slow_projectiles(self):
        self.assertEqual(tuning("burst_count"), 3)
        self.assertLessEqual(tuning("projectile_speed"), 512)     # <= 2 px/frame: dodgeable
        self.assertGreater(tuning("burst_interval"), 4)

    def test_band_and_speed(self):
        self.assertLess(tuning("preferred_dist_min"), tuning("preferred_dist_max"))
        hero = int(re.search(r'\{ "Space Marine Hero", (\d+),', (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")).group(1))
        self.assertLess(tuning("speed"), hero)                    # the player can close the gap

    def test_it_backs_off_closes_in_and_strafes(self):
        body = AI_C.split("static void shooter_reposition")[1].split("static void shooter_fire")[0]
        self.assertIn("ground_dist < tuning->preferred_dist_min", body)
        self.assertIn("ground_dist > tuning->preferred_dist_max", body)
        self.assertIn("nav_next_step(", body)                     # no view: walks the field
        self.assertIn("strafing && !moved", body)                 # a blocked strafe reverses

    def test_shots_come_from_the_muzzle_with_slight_lead(self):
        fire = AI_C.split("static void shooter_fire")[1].split("static void update_shooter")[0]
        self.assertIn("enemy_muzzle(e, &mx, &my, &mh);", fire)
        self.assertIn("enemy_projectile_spawn_linear(mx, my, vx, vy, mh,", fire)
        # The lead used to be divided by 256 (no lead at all): the displacement is player_v * frames.
        self.assertIn("(player_vx * travel_frames) >> SHOOTER_LEAD_SHIFT", fire)
        shift = int(re.search(r"#define SHOOTER_LEAD_SHIFT (\d+)", AI_C).group(1))
        self.assertLessEqual(shift, 2)

    def test_projectiles_fly_at_muzzle_height_and_hit_in_ground_metric(self):
        self.assertIn("sy = TO_INT(p->y) - p->height - cam_y;", PROJECTILES_C)
        self.assertIn("dx * dx + GROUND_DY2(dy) <= PROJECTILE_HIT_RADIUS", PROJECTILES_C)
        self.assertIn("player_take_hit(&g_player_state);", PROJECTILES_C)

    def test_weapon_flashes_during_the_telegraph(self):
        self.assertIn("if (e->state == ENEMY_STATE_TELEGRAPH)", MAIN_C)
        self.assertIn("draw_telegraph_flash(buffer, e, cam_x, cam_y);", MAIN_C)

    def test_a_shove_cancels_the_telegraph_and_a_buried_muzzle_still_fires(self):
        stun = AI_C.split("if (e->stun_timer > 0) {")[1].split("continue;")[0]
        self.assertIn("e->state = ENEMY_STATE_POSITION;", stun)
        fire = AI_C.split("static void shooter_fire")[1].split("static void update_shooter")[0]
        self.assertIn("if (!bullet_position_is_free(mx, my))", fire)

    def test_projectile_pool_fits_all_shooters(self):
        pool = int(re.search(r"#define MAX_ENEMY_PROJECTILES (\d+)", (ROOT / "include" / "projectiles.h").read_text(encoding="utf-8")).group(1))
        self.assertGreaterEqual(pool, 24)

    def test_it_only_telegraphs_with_a_clear_bullet_line(self):
        body = AI_C.split("case ENEMY_STATE_POSITION:\n        default:")[1]
        self.assertIn("(e->has_los & VIEW_BULLET)", body)
        self.assertIn("bullet_line_is_free(wx, wy, px, py)", AI_C)


if __name__ == "__main__":
    unittest.main()
