import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEAPONS_H = (ROOT / "include" / "weapons.h").read_text(encoding="utf-8")
WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
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
    }


def hits_to_kill(hp, damage):
    return -(-hp // damage)


class WeaponsContractTest(unittest.TestCase):
    def test_only_two_weapons_without_ammo(self):
        self.assertIn("WEAPON_SHOTGUN = 0", WEAPONS_H)
        self.assertIn("WEAPON_SNIPER", WEAPONS_H)
        for removed in ("WEAPON_PISTOL", "WEAPON_GATLING", "WEAPON_HEAVY", "max_ammo", "ammo_cost",
                        "spinup_delay", "explosion_radius"):
            self.assertNotIn(removed, WEAPONS_H, removed)
            self.assertNotIn(removed, WEAPONS_C, removed)
        self.assertEqual(set(parse_weapon_table()), {"WEAPON_SHOTGUN", "WEAPON_SNIPER"})

    def test_sniper_point_blank_hits_to_kill(self):
        table = parse_weapon_table()
        hp = parse_enemy_hp()
        sniper = table["WEAPON_SNIPER"]
        self.assertEqual(hits_to_kill(hp["shooter"], sniper["damage_per_hit"]), 1)
        self.assertEqual(hits_to_kill(hp["charger"], sniper["damage_per_hit"]), 2)

    def test_shotgun_point_blank_hits_to_kill(self):
        table = parse_weapon_table()
        hp = parse_enemy_hp()
        shotgun = table["WEAPON_SHOTGUN"]
        full_blast = shotgun["damage_per_hit"] * shotgun["pellets"]
        self.assertGreaterEqual(full_blast, hp["shooter"])
        shots = hits_to_kill(hp["charger"], full_blast)
        self.assertIn(shots, (2, 3))

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
        self.assertIn("draw_line(t, tx, ty, hx, hy", WEAPONS_C)
        self.assertNotIn("buffer[(sy + 1) * SCREEN_W + sx] = edge;", WEAPONS_C)

    def test_fx_are_drawn_on_both_screens(self):
        # DESIGN.md 4.7: aim laser, pellets, trail, flash and sparks show on both screens because
        # render_screen() (run once per screen) calls weapons_render() with its own camera.
        render = MAIN_C.split("static void render_screen")[1].split("static const char s_fps_chars")[0]
        self.assertIn("weapons_render(buffer, cam_x, cam_y);", render)
        self.assertIn("render_screen(s_top_page, s_dirty_top, view_x, view_y - SCREEN_H", MAIN_C)

    def test_feel_hooks(self):
        self.assertIn("g_hitstop_frames", GAMEPLAY_C)
        self.assertIn("weapons_shake_offset", MAIN_C)
        self.assertIn("s_flash.life = 3;", WEAPONS_C)


if __name__ == "__main__":
    unittest.main()
