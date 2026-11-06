import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCOUNTERS_H = (ROOT / "include" / "encounters.h").read_text(encoding="utf-8")
ENCOUNTERS_C = (ROOT / "source" / "encounters.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
ENEMY_AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")


class EncountersContractTest(unittest.TestCase):
    """DESIGN.md 5: dormant packs wake together, a cleared pack heals and offers modifiers."""

    def test_enemies_start_dormant_with_their_pack_from_the_arena_data(self):
        spawn = ENCOUNTERS_C.split("int encounters_spawn")[1].split("static void wake_pack")[0]
        self.assertIn("g_arena->enemies[i]", spawn)
        self.assertIn("e->state = ENEMY_STATE_DORMANT;", spawn)
        self.assertIn("e->pack = spec->pack", spawn)
        self.assertNotIn("rng", spawn)                      # no random placement: the layout is designed

    def test_dormant_enemies_have_no_ai(self):
        self.assertIn("if (e->state == ENEMY_STATE_DORMANT) continue;", ENEMY_AI_C)

    def test_a_pack_wakes_as_a_whole_near_the_player_or_when_hurt(self):
        update = ENCOUNTERS_C.split("void encounters_update")[1].split("void encounters_record_kill")[0]
        self.assertIn("PACK_WAKE_RADIUS * PACK_WAKE_RADIUS", update)
        self.assertIn("if (e->hp < e->max_hp) wake[e->pack] = 1;", update)
        self.assertIn("wake_pack(enemies, max_enemies, p);", update)
        self.assertIn("GROUND_DY2", update)                 # ground metric, not screen distance

    def test_wake_radius_is_the_designed_one(self):
        self.assertEqual(int(re.search(r"#define PACK_WAKE_RADIUS (\d+)", ENCOUNTERS_H).group(1)), 220)

    def test_clearing_a_pack_heals_one_hit_and_offers_modifiers_except_the_last(self):
        update = ENCOUNTERS_C.split("void encounters_update")[1].split("void encounters_record_kill")[0]
        self.assertIn("mgr->pack_alive[p] > 0 && alive[p] == 0", update)
        self.assertIn("g_player_state.hp++", update)
        self.assertIn("if (mgr->packs_cleared < mgr->packs_total) mods_offer(mgr->kill_x[p], mgr->kill_y[p]);", update)

    def test_clearing_every_pack_completes_the_run(self):
        update = ENCOUNTERS_C.split("void encounters_update")[1].split("void encounters_record_kill")[0]
        self.assertIn("if (total_alive == 0 && mgr->enemies_total > 0)", update)
        self.assertIn("mgr->clear_timer = RUN_COMPLETE_FRAMES;", update)
        self.assertIn("if (!mgr->advance && --mgr->clear_timer <= 0) mgr->advance = 1;", update)
        self.assertEqual(int(re.search(r"#define RUN_COMPLETE_FRAMES (\d+)", ENCOUNTERS_H).group(1)), 180)

    def test_main_updates_packs_and_modifiers_each_simulated_frame(self):
        self.assertIn("encounters_update(&g_encounter_mgr, g_enemies, MAX_ENEMIES, s_player.x, s_player.y);", MAIN_C)
        self.assertIn("mods_update(s_player.x, s_player.y);", MAIN_C)
        self.assertIn("int simulate = g_hitstop_frames <= 0 && s_transition == TRANSITION_NONE", MAIN_C)

    def test_every_run_start_loses_the_modifiers(self):
        restart = MAIN_C.split("static void arena_restart(void)")[1].split("\n}")[0]
        self.assertIn("mods_reset();", restart)
        self.assertLess(restart.index("mods_reset();"), restart.index("player_state_init"))
        self.assertIn("encounters_spawn(&g_encounter_mgr, g_enemies, MAX_ENEMIES);", restart)

    def test_death_restarts_the_whole_run_not_just_a_room(self):
        self.assertIn("if (g_player_state.is_dead && !s_strip_mode) arena_restart();", MAIN_C)

    def test_the_banner_fade_and_new_run_after_completion(self):
        self.assertIn("arena_enter(encounters_next_arena(&g_encounter_mgr));", MAIN_C)
        self.assertIn("MAZMORRA COMPLETADA", MAIN_C)

    def test_no_exit_portal_or_floors_left(self):
        for removed in ("exit_open", "encounters_render", "floor_tuning", "advance_floor", "wave_index"):
            self.assertNotIn(removed, ENCOUNTERS_H + ENCOUNTERS_C + MAIN_C, removed)


if __name__ == "__main__":
    unittest.main()
