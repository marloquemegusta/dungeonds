import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")
SPRITE_C = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
ENCOUNTERS_C = (ROOT / "source" / "encounters.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def skeleton_function():
    return AI_C.split("static void update_skeleton")[1].split("// Charger (DESIGN.md 6.9.1)")[0]


def charger_function():
    return AI_C.split("static void update_charger")[1].split("// Necron shooter")[0]


def tuning(kind, field):
    block = GAMEPLAY_C.split(f"[ENEMY_TYPE_{kind}] = {{")[1].split("}")[0]
    return int(re.search(rf"\.{field} = (\d+)", block).group(1))


def define(name):
    return int(re.search(rf"#define {name} (\d+)", GAMEPLAY_H).group(1))


def hero_speed():
    return int(re.search(r'\{ "Corazon Abierto Hero", (\d+),', SPRITE_C).group(1))


class SkeletonContractTest(unittest.TestCase):
    """DESIGN.md 6.9.1: the 0.3 charger AI under a new name. CHASE <-> ATTACK, slow, one bite."""

    def test_fsm_has_only_chase_and_attack(self):
        body = skeleton_function()
        self.assertIn("case ENEMY_STATE_ATTACK:", body)
        self.assertIn("case ENEMY_STATE_CHASE:", body)
        for removed in ("TELEGRAPH", "CHARGE", "IDLE", "ALERT", "SEARCH", "last_seen", "los_lost"):
            self.assertNotIn(removed, body, removed)

    def test_tuning_is_the_decided_one(self):
        self.assertEqual(tuning("SKELETON", "max_hp"), 100)
        self.assertEqual(tuning("SKELETON", "speed"), 130)
        ratio = tuning("SKELETON", "speed") / hero_speed()
        self.assertTrue(0.35 <= ratio <= 0.45, ratio)          # ~40 % of the hero

    def test_bite_has_cooldown_and_needs_a_clear_line(self):
        body = skeleton_function()
        self.assertIn("e->state_timer = tuning->attack_cooldown;", body)
        self.assertLessEqual(tuning("SKELETON", "attack_cooldown"), 40)
        bite = body.split("// Bite")[1].split("refresh_view")[0]
        self.assertIn("los_has_line_of_sight(wx, wy, px, py, 0)", bite)
        self.assertIn("line_is_walkable(wx, wy, px, py)", bite)   # low walls do not block line of sight

    def test_it_walks_down_the_navigation_field(self):
        self.assertIn("nav_next_step(wx, wy, &step_x, &step_y)", AI_C.split("static void chase_step")[1].split("static void refresh_view")[0])
        self.assertIn("nav_update(NAV_BUDGET_PER_FRAME);", MAIN_C)
        self.assertIn("nav_set_goal(TO_INT(s_player.x), TO_INT(s_player.y));", MAIN_C)

    def test_it_uses_its_own_sprite_through_one_function(self):
        self.assertIn("return CHAR_SKELETON;", GAMEPLAY_H.split("enemy_type_char_id")[1])
        self.assertIn("enemy_type_char_id(type)", ENCOUNTERS_C)

    def test_a_woken_pack_chases_at_once(self):
        # DESIGN.md 5: no detection states; a woken pack goes straight to its first active state.
        self.assertIn("e->state = ENEMY_INITIAL_STATE(e->type);", ENCOUNTERS_C)
        self.assertIn("(type) == ENEMY_TYPE_SHOOTER ? ENEMY_STATE_POSITION : ENEMY_STATE_CHASE", GAMEPLAY_H)


class ChargerContractTest(unittest.TestCase):
    """DESIGN.md 6.9.1: CHASE -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE, STUNNED by a wall or a shotgun hit."""

    def test_tuning_is_the_decided_one(self):
        self.assertEqual(tuning("CHARGER", "max_hp"), 300)
        self.assertEqual(tuning("CHARGER", "speed"), 150)
        self.assertEqual(tuning("CHARGER", "charge_speed"), 650)
        self.assertEqual(tuning("CHARGER", "telegraph_duration"), 30)
        self.assertGreater(tuning("CHARGER", "charge_speed"), 2 * hero_speed() - 10)   # the player cannot outrun it
        self.assertEqual(define("CHARGER_ENGAGE_DIST"), 160)
        self.assertEqual(define("CHARGER_RECOVER_FRAMES"), 60)
        self.assertEqual(define("CHARGER_STUN_WALL_FRAMES"), 90)
        self.assertEqual(define("CHARGER_STUN_HIT_FRAMES"), 60)

    def test_charge_covers_about_the_engage_distance(self):
        px = define("CHARGER_CHARGE_FRAMES") * tuning("CHARGER", "charge_speed") / 256
        self.assertTrue(155 <= px <= 175, px)

    def test_fsm_states_and_order(self):
        body = charger_function()
        for state in ("TELEGRAPH", "CHARGE", "RECOVER", "STUNNED", "CHASE"):
            self.assertIn(f"ENEMY_STATE_{state}", body, state)
        telegraph = body.split("case ENEMY_STATE_TELEGRAPH:")[1].split("case ENEMY_STATE_CHARGE:")[0]
        self.assertIn("e->state = ENEMY_STATE_CHARGE;", telegraph)
        charge = body.split("case ENEMY_STATE_CHARGE:")[1].split("case ENEMY_STATE_RECOVER:")[0]
        self.assertIn("e->state = ENEMY_STATE_RECOVER;", charge)
        recover = body.split("case ENEMY_STATE_RECOVER:")[1].split("case ENEMY_STATE_CHASE:")[0]
        self.assertIn("e->state = ENEMY_STATE_CHASE;", recover)

    def test_telegraph_locks_the_direction_once(self):
        body = charger_function()
        chase = body.split("case ENEMY_STATE_CHASE:")[1]
        self.assertIn("aim_vector(wx, wy, px, py, &e->aim_dir_x, &e->aim_dir_y)", chase)
        telegraph = body.split("case ENEMY_STATE_TELEGRAPH:")[1].split("case ENEMY_STATE_CHARGE:")[0]
        self.assertNotIn("aim_vector", telegraph)                # it does not follow the player
        self.assertIn("g_charger_telegraph_frames", MAIN_C)       # uses dedicated telegraph clip without blinking

    def test_telegraph_needs_a_clear_walkable_view_within_range(self):
        refresh = AI_C.split("static void refresh_view")[1].split("// Skeleton")[0]
        self.assertIn("los_has_line_of_sight(wx, wy, px, py, 0)", refresh)
        self.assertIn("line_is_walkable(wx, wy, px, py)", refresh)
        chase = charger_function().split("case ENEMY_STATE_CHASE:")[1]
        self.assertIn("CHARGER_ENGAGE_DIST * CHARGER_ENGAGE_DIST", chase)

    def test_charge_goes_straight_and_stops_dead_on_a_wall(self):
        charge = charger_function().split("case ENEMY_STATE_CHARGE:")[1].split("case ENEMY_STATE_RECOVER:")[0]
        self.assertIn("sweep_position(&e->x, &e->y, vx, vy)", charge)
        self.assertNotIn("move_with_slide", charge)              # no sliding along the obstacle
        blocked = charge.split("if (!sweep_position")[1].split("break;")[0]
        self.assertIn("e->state = ENEMY_STATE_STUNNED;", blocked)
        self.assertIn("e->state_timer = CHARGER_STUN_WALL_FRAMES;", blocked)

    def test_charge_hurts_once_and_respects_i_frames(self):
        charge = charger_function().split("case ENEMY_STATE_CHARGE:")[1].split("case ENEMY_STATE_RECOVER:")[0]
        self.assertIn("if (!e->charge_hit)", charge)
        self.assertIn("player_take_hit(&g_player_state);", charge)   # i-frames live inside player_take_hit
        self.assertIn("e->charge_hit = 1;", charge)
        self.assertIn("CHARGER_HIT_RADIUS * CHARGER_HIT_RADIUS", charge)

    def test_a_shotgun_hit_during_telegraph_or_charge_stuns(self):
        stun = AI_C.split("if (e->stun_timer > 0) {")[1].split("continue;")[0]
        self.assertIn("e->type == ENEMY_TYPE_CHARGER", stun)
        self.assertIn("e->state == ENEMY_STATE_TELEGRAPH || e->state == ENEMY_STATE_CHARGE", stun)
        self.assertIn("e->state = ENEMY_STATE_STUNNED;", stun)
        self.assertIn("e->state_timer = CHARGER_STUN_HIT_FRAMES;", stun)

    def test_the_sniper_does_not_stun(self):
        weapons_c = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
        sniper = weapons_c.split("[WEAPON_SNIPER] = {")[1].split("}")[0]
        self.assertIn(".knockback = 0", sniper)
        self.assertIn(".stun_frames = 0", sniper)
        shove = weapons_c.split("static void shove_enemy")[1].split("}")[0]
        self.assertIn("tuning->knockback <= 0", shove)           # no knockback, no stun

    def test_tunables_are_marked(self):
        for line in GAMEPLAY_H.splitlines():
            if line.startswith("#define CHARGER_"):
                self.assertIn("[TUNABLE-PLACEHOLDER]", line, line)


if __name__ == "__main__":
    unittest.main()
