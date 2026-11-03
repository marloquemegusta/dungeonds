import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCOUNTERS_H = (ROOT / "include" / "encounters.h").read_text(encoding="utf-8")
ENCOUNTERS_C = (ROOT / "source" / "encounters.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


class EncountersContractTest(unittest.TestCase):
    """DESIGN.md 4.6: closed arenas, every enemy active at once, half a second, next arena."""

    def test_pause_is_half_a_second(self):
        frames = int(re.search(r"#define ENCOUNTER_CLEAR_PAUSE_FRAMES (\d+)", ENCOUNTERS_H).group(1))
        self.assertEqual(frames, 30)

    def test_enemies_come_from_the_arena_data_and_all_start_active(self):
        spawn = ENCOUNTERS_C.split("int encounters_spawn")[1].split("void encounters_update")[0]
        self.assertIn("g_arena->enemies[i]", spawn)
        self.assertIn("e->active = 1;", spawn)
        self.assertIn("ENEMY_STATE_CHASE : ENEMY_STATE_POSITION", spawn)
        self.assertNotIn("rng", spawn)                      # no random placement: the layout is designed

    def test_last_kill_starts_the_pause_and_the_pause_raises_advance(self):
        update = ENCOUNTERS_C.split("void encounters_update")[1].split("void encounters_record_kill")[0]
        self.assertIn("if (alive == 0 && mgr->enemies_total > 0)", update)
        self.assertIn("mgr->clear_timer = ENCOUNTER_CLEAR_PAUSE_FRAMES;", update)
        self.assertIn("if (--mgr->clear_timer <= 0) mgr->advance = 1;", update)

    def test_arenas_cycle_and_the_enemy_codes_match(self):
        self.assertIn("return (mgr->arena + 1) % g_num_arenas;", ENCOUNTERS_C)
        self.assertIn("_Static_assert(ARENA_ENEMY_CHARGER == ENEMY_TYPE_CHARGER", ENCOUNTERS_C)

    def test_main_fades_loads_the_next_arena_and_freezes_the_simulation(self):
        self.assertIn("arena_enter(encounters_next_arena(&g_encounter_mgr));", MAIN_C)
        self.assertIn("setBrightness(3, -s_fade_level);", MAIN_C)
        self.assertIn("int simulate = g_hitstop_frames <= 0 && s_transition == TRANSITION_NONE;", MAIN_C)

    def test_death_restarts_the_current_arena_not_the_game(self):
        restart = MAIN_C.split("static void arena_restart(void)")[1].split("\n}")[0]
        self.assertIn("encounters_spawn(&g_encounter_mgr, s_enemies, MAX_ENEMIES);", restart)
        self.assertNotIn("arena_select", restart)

    def test_a_restart_or_new_arena_starts_clean(self):
        restart = MAIN_C.split("static void arena_restart(void)")[1].split("\n}")[0]
        self.assertIn("s_keys_down_latch = 0;", restart)
        self.assertIn("update_camera();", restart)
        fade = MAIN_C.split("static void transition_update")[1].split("\n}")[0]
        self.assertLess(fade.index("setBrightness(3, -16);"), fade.index("arena_enter("))

    def test_no_exit_portal_or_floors_left(self):
        for removed in ("exit_open", "encounters_render", "floor_tuning", "advance_floor", "wave_index"):
            self.assertNotIn(removed, ENCOUNTERS_H + ENCOUNTERS_C + MAIN_C, removed)


if __name__ == "__main__":
    unittest.main()
