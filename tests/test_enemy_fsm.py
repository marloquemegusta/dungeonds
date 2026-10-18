import unittest
import math

# Fixed point 8.8 definitions matching C engine
FIXED_SHIFT = 8

def to_fixed(v):
    return int(v) << FIXED_SHIFT

def to_int(v):
    return int(v) >> FIXED_SHIFT

# Enemy tuning constants (mirrors C gameplay.c / gameplay.h)
CHARGER_TUNING = {
    "max_hp": 60,
    "speed": 163,             # 8.8 fixed (~90% player speed 181)
    "contact_damage": 15,
    "attack_cooldown": 30,
    "preferred_dist_min": 0,
    "preferred_dist_max": 16,
    "los_range": 160,
    "alert_duration": 20,
    "search_duration": 90,
    "los_lost_limit": 180,
}

SHOOTER_TUNING = {
    "max_hp": 20,
    "speed": 120,
    "contact_damage": 5,
    "attack_cooldown": 60,
    "preferred_dist_min": 40,
    "preferred_dist_max": 80,
    "los_range": 180,
    "alert_duration": 25,
    "search_duration": 90,
    "los_lost_limit": 180,
    "position_duration": 35,
    "aim_duration": 25,
    "burst_count": 3,
    "burst_interval": 10,
    "projectile_speed": 384,
    "projectile_damage": 8,
}

class MockPlayer:
    def __init__(self, x=380, y=227, hp=100, armor=0):
        self.x = to_fixed(x)
        self.y = to_fixed(y)
        self.vx = 0
        self.vy = 0
        self.hp = hp
        self.max_hp = 100
        self.armor = armor
        self.is_dead = False

    def apply_damage(self, damage):
        if self.is_dead or damage <= 0:
            return
        absorbed = 0
        if self.armor > 0:
            absorbed = damage // 3
            if absorbed > self.armor:
                absorbed = self.armor
            self.armor -= absorbed
        hp_dmg = damage - absorbed
        self.hp -= hp_dmg
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True


class MockChargerFSM:
    def __init__(self, x, y):
        self.x = to_fixed(x)
        self.y = to_fixed(y)
        self.state = "IDLE"
        self.state_timer = 0
        self.last_seen_x = 0
        self.last_seen_y = 0
        self.los_lost_timer = 0
        self.tuning = CHARGER_TUNING

    def update(self, player, has_los):
        wx = to_int(self.x)
        wy = to_int(self.y)
        px = to_int(player.x)
        py = to_int(player.y)

        dx = px - wx
        dy = py - wy
        dist_sq = dx * dx + dy * dy

        if self.state == "IDLE":
            if has_los and not player.is_dead:
                self.state = "ALERT"
                self.state_timer = self.tuning["alert_duration"]
                self.last_seen_x = player.x
                self.last_seen_y = player.y
                self.los_lost_timer = 0

        elif self.state == "ALERT":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "CHASE"

        elif self.state == "CHASE":
            if player.is_dead:
                self.state = "IDLE"
                return

            if has_los:
                self.last_seen_x = player.x
                self.last_seen_y = player.y
                self.los_lost_timer = 0
            else:
                self.los_lost_timer += 1
                if self.los_lost_timer >= self.tuning["los_lost_limit"]:
                    self.state = "SEARCH"
                    self.state_timer = self.tuning["search_duration"]
                    return

            melee_r = self.tuning["preferred_dist_max"]
            if dist_sq <= melee_r * melee_r:
                player.apply_damage(self.tuning["contact_damage"])
                self.state = "ATTACK"
                self.state_timer = self.tuning["attack_cooldown"]
            else:
                dist = math.isqrt(dist_sq) if dist_sq > 0 else 1
                spd = self.tuning["speed"]
                self.x += (dx * spd) // dist
                self.y += (dy * spd) // dist

        elif self.state == "ATTACK":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "CHASE"

        elif self.state == "SEARCH":
            if has_los and not player.is_dead:
                self.state = "ALERT"
                self.state_timer = self.tuning["alert_duration"] // 2
                self.last_seen_x = player.x
                self.last_seen_y = player.y
                self.los_lost_timer = 0
                return

            sx = to_int(self.last_seen_x - self.x)
            sy = to_int(self.last_seen_y - self.y)
            s_dist = math.isqrt(sx * sx + sy * sy)
            self.state_timer -= 1
            if s_dist <= 8 or self.state_timer <= 0:
                self.state = "IDLE"
            else:
                spd = self.tuning["speed"]
                self.x += (sx * spd) // s_dist
                self.y += (sy * spd) // s_dist


class MockShooterFSM:
    def __init__(self, x, y):
        self.x = to_fixed(x)
        self.y = to_fixed(y)
        self.state = "IDLE"
        self.state_timer = 0
        self.last_seen_x = 0
        self.last_seen_y = 0
        self.los_lost_timer = 0
        self.strafe_dir = 1
        self.burst_shots_left = 0
        self.burst_interval_timer = 0
        self.fired_projectiles = []
        self.tuning = SHOOTER_TUNING

    def update(self, player, has_los):
        wx = to_int(self.x)
        wy = to_int(self.y)
        px = to_int(player.x)
        py = to_int(player.y)

        dx = px - wx
        dy = py - wy
        dist = math.isqrt(dx * dx + dy * dy) if (dx * dx + dy * dy) > 0 else 1

        if self.state == "IDLE":
            if has_los and not player.is_dead:
                self.state = "ALERT"
                self.state_timer = self.tuning["alert_duration"]
                self.last_seen_x = player.x
                self.last_seen_y = player.y
                self.los_lost_timer = 0

        elif self.state == "ALERT":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "POSITION"
                self.state_timer = self.tuning["position_duration"]

        elif self.state == "POSITION":
            if player.is_dead:
                self.state = "IDLE"
                return

            if has_los:
                self.last_seen_x = player.x
                self.last_seen_y = player.y
                self.los_lost_timer = 0
            else:
                self.los_lost_timer += 1
                if self.los_lost_timer >= self.tuning["los_lost_limit"]:
                    self.state = "SEARCH"
                    self.state_timer = self.tuning["search_duration"]
                    return

            d_min = self.tuning["preferred_dist_min"]
            d_max = self.tuning["preferred_dist_max"]
            spd = self.tuning["speed"]

            if dist < d_min:
                # Retreat away
                self.last_move = "RETREAT"
                self.x -= (dx * spd) // dist
                self.y -= (dy * spd) // dist
            elif dist > d_max:
                # Advance toward
                self.last_move = "ADVANCE"
                self.x += (dx * spd) // dist
                self.y += (dy * spd) // dist
            else:
                # Strafe laterally
                self.last_move = "STRAFE"
                sx = -dy * self.strafe_dir
                sy =  dx * self.strafe_dir
                s_dist = math.isqrt(sx * sx + sy * sy) if (sx * sx + sy * sy) > 0 else 1
                self.x += (sx * spd) // s_dist
                self.y += (sy * spd) // s_dist

            self.state_timer -= 1
            if self.state_timer <= 0 and self.los_lost_timer == 0:
                self.state = "AIM"
                self.state_timer = self.tuning["aim_duration"]

        elif self.state == "AIM":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "BURST"
                self.burst_shots_left = self.tuning["burst_count"]
                self.burst_interval_timer = 0

        elif self.state == "BURST":
            if self.burst_interval_timer <= 0 and self.burst_shots_left > 0:
                # Linear lead prediction calculation
                proj_spd = self.tuning["projectile_speed"]
                travel_frames = min(20, max(0, (dist * 256) // proj_spd))
                pred_px = player.x + ((player.vx * travel_frames) >> 8)
                pred_py = player.y + ((player.vy * travel_frames) >> 8)

                t_dx = to_int(pred_px - self.x)
                t_dy = to_int(pred_py - self.y)
                t_dist = math.isqrt(t_dx * t_dx + t_dy * t_dy) if (t_dx * t_dx + t_dy * t_dy) > 0 else 1
                pvx = (t_dx * proj_spd) // t_dist
                pvy = (t_dy * proj_spd) // t_dist

                self.fired_projectiles.append({
                    "x": self.x, "y": self.y,
                    "vx": pvx, "vy": pvy,
                    "damage": self.tuning["projectile_damage"]
                })
                self.burst_shots_left -= 1
                self.burst_interval_timer = self.tuning["burst_interval"]
            else:
                self.burst_interval_timer -= 1

            if self.burst_shots_left <= 0:
                self.state = "COOLDOWN"
                self.state_timer = self.tuning["attack_cooldown"]

        elif self.state == "COOLDOWN":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "POSITION"
                self.state_timer = self.tuning["position_duration"]

        elif self.state == "SEARCH":
            if has_los and not player.is_dead:
                self.state = "ALERT"
                self.state_timer = self.tuning["alert_duration"] // 2
                self.last_seen_x = player.x
                self.last_seen_y = player.y
                self.los_lost_timer = 0
                return

            sx = to_int(self.last_seen_x - self.x)
            sy = to_int(self.last_seen_y - self.y)
            s_dist = math.isqrt(sx * sx + sy * sy)
            self.state_timer -= 1
            if s_dist <= 8 or self.state_timer <= 0:
                self.state = "IDLE"
            else:
                spd = self.tuning["speed"]
                self.x += (sx * spd) // s_dist
                self.y += (sy * spd) // s_dist


class TestEnemyFSMContract(unittest.TestCase):
    def test_charger_idle_to_alert_on_los(self):
        player = MockPlayer(100, 100)
        charger = MockChargerFSM(150, 100)

        # Without LOS -> stays IDLE
        charger.update(player, has_los=False)
        self.assertEqual(charger.state, "IDLE")

        # With LOS -> transitions to ALERT
        charger.update(player, has_los=True)
        self.assertEqual(charger.state, "ALERT")
        self.assertEqual(charger.state_timer, CHARGER_TUNING["alert_duration"])
        self.assertEqual(charger.last_seen_x, player.x)
        self.assertEqual(charger.last_seen_y, player.y)

    def test_charger_alert_to_chase(self):
        player = MockPlayer(100, 100)
        charger = MockChargerFSM(150, 100)
        charger.state = "ALERT"
        charger.state_timer = 2

        charger.update(player, has_los=True)
        self.assertEqual(charger.state, "ALERT")
        self.assertEqual(charger.state_timer, 1)

        charger.update(player, has_los=True)
        self.assertEqual(charger.state, "CHASE")

    def test_charger_chase_and_melee_attack(self):
        player = MockPlayer(100, 100)
        charger = MockChargerFSM(110, 100) # within 16px melee range
        charger.state = "CHASE"

        initial_hp = player.hp
        charger.update(player, has_los=True)
        self.assertEqual(charger.state, "ATTACK")
        self.assertEqual(charger.state_timer, CHARGER_TUNING["attack_cooldown"])
        self.assertEqual(player.hp, initial_hp - CHARGER_TUNING["contact_damage"])

    def test_charger_attack_cooldown_to_chase(self):
        player = MockPlayer(100, 100)
        charger = MockChargerFSM(110, 100)
        charger.state = "ATTACK"
        charger.state_timer = 1

        charger.update(player, has_los=True)
        self.assertEqual(charger.state, "CHASE")

    def test_charger_los_lost_to_search_and_idle(self):
        player = MockPlayer(100, 100)
        charger = MockChargerFSM(200, 200)
        charger.state = "CHASE"
        charger.last_seen_x = to_fixed(150)
        charger.last_seen_y = to_fixed(150)

        # 179 frames of lost LOS -> remains in CHASE
        for _ in range(179):
            charger.update(player, has_los=False)
            self.assertEqual(charger.state, "CHASE")

        # 180th frame -> switches to SEARCH
        charger.update(player, has_los=False)
        self.assertEqual(charger.state, "SEARCH")
        self.assertEqual(charger.state_timer, CHARGER_TUNING["search_duration"])

        # When search timer expires -> transitions to IDLE
        charger.state_timer = 1
        charger.update(player, has_los=False)
        self.assertEqual(charger.state, "IDLE")

    def test_shooter_distance_maintenance(self):
        player = MockPlayer(100, 100)
        shooter = MockShooterFSM(100, 100)
        shooter.state = "POSITION"
        shooter.state_timer = 100

        # Too close: dist = 20px (< preferred_dist_min=40) -> RETREAT
        shooter.x = to_fixed(120)
        shooter.y = to_fixed(100)
        shooter.update(player, has_los=True)
        self.assertEqual(shooter.last_move, "RETREAT")
        self.assertGreater(shooter.x, to_fixed(120))

        # Too far: dist = 120px (> preferred_dist_max=80) -> ADVANCE
        shooter.x = to_fixed(220)
        shooter.y = to_fixed(100)
        shooter.update(player, has_los=True)
        self.assertEqual(shooter.last_move, "ADVANCE")
        self.assertLess(shooter.x, to_fixed(220))

        # In band: dist = 60px ([40, 80]) -> STRAFE
        shooter.x = to_fixed(160)
        shooter.y = to_fixed(100)
        shooter.update(player, has_los=True)
        self.assertEqual(shooter.last_move, "STRAFE")

    def test_shooter_aim_burst_cooldown_cycle(self):
        player = MockPlayer(100, 100)
        player.vx = to_fixed(1) # moving right 1 px/frame
        shooter = MockShooterFSM(160, 100)
        shooter.state = "POSITION"
        shooter.state_timer = 1

        # POSITION -> AIM
        shooter.update(player, has_los=True)
        self.assertEqual(shooter.state, "AIM")
        self.assertEqual(shooter.state_timer, SHOOTER_TUNING["aim_duration"])

        # AIM -> BURST
        shooter.state_timer = 1
        shooter.update(player, has_los=True)
        self.assertEqual(shooter.state, "BURST")

        # First shot fired on BURST execution
        shooter.update(player, has_los=True)
        self.assertEqual(len(shooter.fired_projectiles), 1)
        self.assertEqual(shooter.burst_shots_left, 2)

        # 2nd shot after burst interval (10 frames + trigger)
        for _ in range(SHOOTER_TUNING["burst_interval"] + 1):
            shooter.update(player, has_los=True)
        self.assertEqual(len(shooter.fired_projectiles), 2)
        self.assertEqual(shooter.burst_shots_left, 1)

        # 3rd shot after burst interval
        for _ in range(SHOOTER_TUNING["burst_interval"] + 1):
            shooter.update(player, has_los=True)
        self.assertEqual(len(shooter.fired_projectiles), 3)
        self.assertEqual(shooter.burst_shots_left, 0)
        self.assertEqual(shooter.state, "COOLDOWN")
        self.assertEqual(shooter.state_timer, SHOOTER_TUNING["attack_cooldown"])

        # Check projectile properties
        proj = shooter.fired_projectiles[0]
        self.assertEqual(proj["damage"], SHOOTER_TUNING["projectile_damage"])
        self.assertEqual(len(shooter.fired_projectiles), 3)

        # COOLDOWN -> POSITION
        shooter.state_timer = 1
        shooter.update(player, has_los=True)
        self.assertEqual(shooter.state, "POSITION")


if __name__ == "__main__":
    unittest.main()
