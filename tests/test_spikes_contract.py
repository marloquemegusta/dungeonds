"""Contracts of the frame-time spike work (rebase spreading, death-chunk cap, laser draw, peak profiling).

Behaviour of the rebase itself is covered by tests/test_strip.py (reference equivalence, staged nav
shift); these checks pin the shape that keeps the shift frame cheap.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def body_of(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:i + 1]
    raise AssertionError(signature)


class IncrementalRebaseContract(unittest.TestCase):
    def test_commit_moves_nothing(self):
        strip = read("source", "strip.c")
        commit = body_of(strip, "static int commit_prepared(void)")
        self.assertNotIn("memmove", commit)
        self.assertNotIn("memcpy", commit)
        self.assertNotIn("enforce_hard_edges", commit)
        # the floor arrays swap roles like the run arrays
        self.assertIn("s_map = s_map_res;", commit)
        self.assertIn("s_collision = s_collision_res;", commit)

    def test_floor_copy_is_sliced_and_has_a_phase(self):
        strip = read("source", "strip.c")
        self.assertIn("PREP_FLOOR", strip)
        self.assertRegex(strip, r"case PREP_FLOOR:\s+prep_floor\(\); break;")
        floor = body_of(strip, "static void prep_floor(void)")
        self.assertIn("STRIP_FLOOR_MAP_SLICES", floor)
        self.assertIn("STRIP_FLOOR_COL_SLICES", floor)
        self.assertRegex(strip, r"STRIP_FLOOR_MAP_SLICES\s+\d+")

    def test_bands_are_built_in_slices_of_a_few_stamps(self):
        strip = read("source", "strip.c")
        m = re.search(r"#define STRIP_PREP_PIECES (\d+)", strip)
        self.assertIsNotNone(m)
        self.assertLessEqual(int(m.group(1)), 5)
        band = body_of(strip, "static void prep_band(void)")
        self.assertIn("stamp_band_slice(", band)
        self.assertIn("STRIP_PREP_PIECES", band)
        self.assertIn("band_floor(", band)

    def test_prepare_starts_early_enough_for_the_longer_preparation(self):
        header = read("include", "strip.h")
        m = re.search(r"#define STRIP_PREPARE_MARGIN_PX (\d+)", header)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 512)

    def test_nav_walkability_is_staged_ahead(self):
        main = read("source", "main.c")
        nav = read("source", "navfield.c")
        step = body_of(main, "static void strip_nav_stage_step(void)")
        self.assertIn("strip_stage_enter()", step)
        self.assertIn("nav_stage_step(", step)
        self.assertIn("strip_stage_leave();", step)
        budget = re.search(r"#define NAV_STAGE_NODES_PER_FRAME (\d+)", main)
        self.assertIsNotNone(budget)
        self.assertLessEqual(int(budget.group(1)), 128)
        # prepare, then stage, then the rebase check: the shift frame reuses the staged rows
        i_prep = main.index("strip_prepare_step(TO_INT(s_player.y));")
        i_stage = main.index("strip_nav_stage_step();", i_prep)
        i_rebase = main.index("strip_rebase_if_needed(", i_stage)
        self.assertLess(i_prep, i_stage)
        self.assertLess(i_stage, i_rebase)
        self.assertIn("strip_stage_id());", main[i_rebase:i_rebase + 400])
        shift = body_of(nav, "void nav_shift_down(")
        self.assertIn("memcpy(s_walkable, s_stage_walk", shift)
        # the staged loop divides once per call, not per node
        stage = body_of(nav, "int nav_stage_step(")
        self.assertEqual(stage.count(" / s_w"), 1)

    def test_no_floating_point_in_the_touched_code(self):
        for name in ("strip.c", "navfield.c", "enemy_laser.c"):
            self.assertIsNone(re.search(r"\b(?:float|double)\b", read("source", name)), name)


class DeathChunkCapContract(unittest.TestCase):
    def test_per_frame_cap_and_queue(self):
        main = read("source", "main.c")
        cap = re.search(r"#define DEATH_SPAWNS_PER_FRAME (\d+)", main)
        self.assertIsNotNone(cap)
        self.assertLessEqual(int(cap.group(1)), 3)
        size = re.search(r"#define MAX_PENDING_DEATHS (\d+)", main)
        self.assertIsNotNone(size)
        n = int(size.group(1))
        self.assertEqual(n & (n - 1), 0, "the queue wraps with a mask")
        hook = body_of(main, "static void on_enemy_death(")
        self.assertIn("s_death_spawn_budget > 0", hook)
        self.assertIn("s_pending_count < MAX_PENDING_DEATHS", hook)
        # kills never wait: the kill bookkeeping stays immediate
        self.assertIn("weapons_notify_kill();", hook)
        self.assertIn("pickups_enemy_killed(e);", hook)

    def test_queue_is_drained_at_frame_start_and_follows_the_rebase(self):
        main = read("source", "main.c")
        begin = body_of(main, "static void death_chunks_frame_begin(void)")
        self.assertIn("s_death_spawn_budget = DEATH_SPAWNS_PER_FRAME;", begin)
        self.assertIn("death_chunks_spawn(&s_pending_deaths[s_pending_head]);", begin)
        sim = main.index("if (simulate) {\n            death_chunks_frame_begin();")
        self.assertGreater(sim, 0)
        shift = body_of(main, "static void strip_shift_world_y(int dy_px)")
        self.assertIn("s_pending_deaths", shift)
        reset = main.index("memset(s_death_chunks, 0, sizeof(s_death_chunks));")
        self.assertIn("s_pending_head = s_pending_count = 0;", main[reset:reset + 120])


class LaserDrawContract(unittest.TestCase):
    def test_laser_paints_without_per_pixel_dirty_calls(self):
        laser = read("source", "enemy_laser.c")
        draw = body_of(laser, "static void draw_laser(")
        self.assertEqual(draw.count("dirty_row("), 1, "one dirty_row per touched row, after the beam")
        self.assertIn("s_row_x0", draw)
        # the per-pixel multiplications moved out of the step loop
        loop = draw[draw.index("for (int d = 1;"):]
        self.assertNotIn("perp_x *", loop)
        self.assertNotIn("perp_y *", loop)
        self.assertIn("ITCM_CODE", laser)


class PeakProfilingContract(unittest.TestCase):
    NAMES = ["pl", "en", "wp", "dclr", "sh", "sort", "blit", "proj", "pick", "hud", "bgsub", "bgbot", "vwait",
             "cpu", "frame"]

    def test_profiler_mirrors_the_window_peaks(self):
        prof = read("source", "perfprof.c")
        self.assertIn("static volatile uint32_t s_hud_max[PP_COUNT];", prof)
        self.assertIn("s_hud_max[i] = s_max[i];", prof)

    def test_bench_scenarios_read_the_peaks(self):
        order = ["pl", "occ", "en", "wp", "dclr", "sh", "sort", "blit", "proj", "pick", "hud", "pcopy", "bgsub",
                 "bgbot", "vwait", "cpu", "frame"]
        for name in ("perf_stress_bench.json", "perf_stress_bench_sw_shadows.json", "perf_stress_climb.json"):
            sc = json.loads(read("scenarios", name))
            self.assertEqual(sc["state"]["symbols"]["mx"], "s_hud_max", name)
            for stage in self.NAMES:
                field = sc["state"]["fields"][stage + "_max"]
                self.assertEqual(field["symbol"], "mx")
                self.assertEqual(field["offset"], order.index(stage) * 4, f"{name} {stage}")

    def test_climb_scenario_crosses_rebases_with_the_horde(self):
        sc = json.loads(read("scenarios", "perf_stress_climb.json"))
        pokes = [s["poke"][0]["value"] // 256 for s in sc["steps"] if "poke" in s]
        self.assertTrue(pokes)
        for y in pokes:
            self.assertIn(y, (790, 764))
        self.assertLess(764, 768, "the second poke must cross STRIP_REBASE_TOP_PX")
        self.assertGreater(790, 768)
        self.assertGreaterEqual(sc["assertions"]["state_changes"][0]["min_value"], 1536)

    def test_summary_prints_the_peaks(self):
        text = read("tools", "perf_bench_summary.py")
        self.assertIn('st + "_max"', text)


if __name__ == "__main__":
    unittest.main()
