"""DESIGN.md 6.10, "Exvoto en el juego, versión mínima": the contract of the code that replaces the skeleton."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


GAMEPLAY_H = read("include/gameplay.h")
GAMEPLAY_C = read("source/gameplay.c")
HORDE_C = read("source/horde.c")
HORDE_H = read("include/horde.h")
AI_C = read("source/enemy_ai.c")
MELT_H = read("include/exvoto_melt.h")
MELT_C = read("source/exvoto_melt.c")
STRIP_C = read("source/strip.c")
MAIN_C = read("source/main.c")


def define(text, name):
    return int(re.search(rf"#define {name} (\d+)", text).group(1))


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


class ExvotoContractTest(unittest.TestCase):
    def test_no_floating_point_in_the_new_runtime_code(self):
        for name in ("source/exvoto_melt.c", "source/horde.c", "source/enemy_ai.c"):
            code = strip_comments(read(name))
            self.assertIsNone(re.search(r"\b(?:float|double)\b", code), name)

    def test_skeleton_is_out_of_the_horde_and_the_sprite_tables(self):
        self.assertNotIn("SKELETON", HORDE_C)
        self.assertNotIn("SKELETON", HORDE_H)
        self.assertNotIn("SKELETON", GAMEPLAY_H)
        self.assertNotIn("g_skeleton", read("include/player_sprite.h"))
        self.assertIn("ENEMY_TYPE_EXVOTO", HORDE_C)

    def test_same_numbers_as_the_skeleton(self):
        block = GAMEPLAY_C.split("[ENEMY_TYPE_EXVOTO] = {")[1].split("}")[0]
        self.assertEqual(int(re.search(r"\.max_hp = (\d+)", block).group(1)), 100)
        self.assertEqual(int(re.search(r"\.speed = (\d+)", block).group(1)), 130)
        self.assertEqual(define(HORDE_H, "HORDE_EXVOTO_PERCENT"), 60)

    def test_wake_radii_and_posture_are_the_decided_ones(self):
        self.assertEqual(define(GAMEPLAY_H, "EXVOTO_WAKE_RADIUS"), 96)
        self.assertEqual(define(GAMEPLAY_H, "EXVOTO_CHAIN_WAKE_RADIUS"), 48)
        self.assertEqual(define(GAMEPLAY_H, "EXVOTO_KNEEL_PERCENT"), 50)
        self.assertEqual(define(HORDE_H, "HORDE_EXVOTO_GROUP_MAX"), 4)

    def test_every_new_number_is_marked_tunable(self):
        for text in (GAMEPLAY_H, HORDE_H, MELT_H):
            for line in text.splitlines():
                if re.match(r"#define (EXVOTO_|HORDE_EXVOTO_|HORDE_DEVOUT_)w+ d", line):
                    self.assertIn("[TUNABLE-PLACEHOLDER]", line, line)

    def test_melt_numbers_are_the_decided_ones_and_bounded(self):
        self.assertEqual(define(MELT_H, "EXVOTO_MELT_SINK_FRAMES"), 20)
        self.assertEqual(define(MELT_H, "EXVOTO_MELT_POOL_FRAMES"), 90)
        self.assertLessEqual(define(MELT_H, "EXVOTO_MELT_MAX"), 8)       # one disc per puddle per screen
        self.assertIn("gfx_ground_disc", MELT_C)                          # 2:1 ellipse of the ground effects
        self.assertIn("exvoto_melt_spawn(e)", MAIN_C.split("static void on_enemy_death")[1])

    def test_fsm_prays_wakes_in_chain_and_rises_only_when_kneeling(self):
        self.assertIn("ENEMY_STATE_PRAY", AI_C)
        pray = AI_C.split("case ENEMY_STATE_PRAY:")[1].split("case ENEMY_STATE_RISE:")[0]
        self.assertIn("EXVOTO_WAKE_RADIUS * EXVOTO_WAKE_RADIUS", pray)
        self.assertIn("e->hit_timer > 0", pray)                           # hurt wakes it
        self.assertNotIn("player_take_hit", pray)                         # a praying Exvoto never bites
        self.assertNotIn("chase_step", pray)                              # ...nor moves
        wake = AI_C.split("static void exvoto_wake_one")[1].split("static void exvoto_wake_chain")[0]
        self.assertIn("if (e->kneel)", wake)
        self.assertIn("ENEMY_STATE_RISE", wake)
        self.assertIn("EXVOTO_CHAIN_WAKE_RADIUS", AI_C)

    def test_clips_are_character_slots_and_the_rise_ends_walking(self):
        header = read("include/player_sprite.h")
        self.assertRegex(header, r"#define NUM_CHARACTERS 7")
        for name in ("CHAR_EXVOTO ", "CHAR_EXVOTO_PRAY_STAND", "CHAR_EXVOTO_PRAY_KNEEL", "CHAR_EXVOTO_STAND_UP"):
            self.assertIn(name, header)
        rise = AI_C.split("case ENEMY_STATE_RISE:")[1].split("case ENEMY_STATE_ATTACK:")[0]
        self.assertIn("e->char_id = CHAR_EXVOTO;", rise)

    def test_clip_ticks_match_the_rise_duration(self):
        manifest = json.loads(read("assets/sprites/characters/characters.json"))["characters"]
        for name in ("exvoto", "exvoto_pray_stand", "exvoto_pray_kneel", "exvoto_stand_up"):
            self.assertEqual(manifest[name]["resolution"], 40, name)
        rise = manifest["exvoto_stand_up"]["ticksPerFrame"] * 8
        self.assertEqual(rise, define(GAMEPLAY_H, "EXVOTO_RISE_FRAMES"))

    def test_placement_uses_devout_pieces_and_falls_back_to_walking(self):
        self.assertIn("strip_devout_in_band", HORDE_C)
        self.assertIn("seat_exvoto", HORDE_C)
        seat = HORDE_C.split("static int seat_exvoto")[1].split("static int spawn_enemy")[0]
        self.assertIn("enemy_dir_from_vector(TO_FIXED(d->x - x), TO_FIXED(d->y - y))", seat)   # faces the piece
        self.assertIn("position_is_free", seat)
        self.assertIn("HORDE_EXVOTO_GROUP_MAX", seat)
        spawn = HORDE_C.split("static int spawn_enemy")[1].split("ITCM_CODE void horde_update")[0]
        self.assertIn("if (!seated)", spawn)                              # no free piece: awake and walking
        self.assertIn("enemy_exvoto_start_praying", spawn)

    def test_compositor_keeps_a_devout_list_instead_of_replanning(self):
        for kind in ("STRIP_PIECE_SANTO", "STRIP_PIECE_VELA", "STRIP_PIECE_RELICARIO"):
            self.assertIn(kind, STRIP_C.split("static int piece_is_devout")[1].split("}")[0])
        self.assertIn("s_devout_active", STRIP_C.split("int strip_devout_in_band")[1])
        self.assertNotIn("plan_block", STRIP_C.split("int strip_devout_in_band")[1].split("\n}")[0])

    def test_tide_recycles_praying_exvotos_without_reward(self):
        horde = HORDE_C.split("ITCM_CODE void horde_update")[1]
        self.assertIn("e->y >= tide_y) e->active = 0", horde)
        self.assertNotIn("enemy_hit(", horde)


if __name__ == "__main__":
    unittest.main()
