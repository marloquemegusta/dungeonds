import unittest

# Mirror of C fixed point and tuning constants
FIXED_SHIFT = 8


def to_fixed(v):
    return int(v) << FIXED_SHIFT


def to_int(v):
    return int(v) >> FIXED_SHIFT


PLAYER_MAX_HP = 100
PLAYER_MAX_ARMOR = 100

ENEMY_CHARGER_HP = 60
ENEMY_SHOOTER_HP = 20

WEAPON_MAX_AMMO = {
    "pistol": 0,
    "shotgun": 50,
    "gatling": 200,
    "heavy": 20,
}

WEAPON_PICKUP_AMMO = {
    "pistol": 0,
    "shotgun": 10,
    "gatling": 40,
    "heavy": 5,
}


class LcgRng:
    def __init__(self, seed: int = 123456789):
        self.state = seed if seed != 0 else 1

    def next(self) -> int:
        self.state = (self.state * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.state

    def range(self, min_val: int, max_val: int) -> int:
        if min_val >= max_val:
            return min_val
        r = self.next()
        return min_val + (r % (max_val - min_val + 1))


class PlayerState:
    def __init__(self):
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.armor = 0
        self.max_armor = PLAYER_MAX_ARMOR
        self.is_dead = False
        self.ammo = {
            "pistol": 0,
            "shotgun": 12,
            "gatling": 50,
            "heavy": 5,
        }

    def apply_damage(self, damage: int):
        if self.is_dead or damage <= 0:
            return

        absorbed = 0
        if self.armor > 0:
            absorbed = damage // 3
            if absorbed > self.armor:
                absorbed = self.armor
            self.armor -= absorbed

        hp_damage = damage - absorbed
        self.hp -= hp_damage
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True

    def collect_pickup(self, ptype: str, amount: int = 0) -> bool:
        if self.is_dead:
            return False

        if ptype == "health":
            if self.hp >= self.max_hp:
                return False
            gain = amount if amount > 0 else 25
            self.hp = min(self.max_hp, self.hp + gain)
            return True

        if ptype == "armor":
            if self.armor >= self.max_armor:
                return False
            gain = amount if amount > 0 else 25
            self.armor = min(self.max_armor, self.armor + gain)
            return True

        if ptype in WEAPON_MAX_AMMO:
            max_cap = WEAPON_MAX_AMMO[ptype]
            if max_cap == 0 or self.ammo[ptype] >= max_cap:
                return False
            gain = amount if amount > 0 else WEAPON_PICKUP_AMMO[ptype]
            self.ammo[ptype] = min(max_cap, self.ammo[ptype] + gain)
            return True

        return False


class TestGameplayContract(unittest.TestCase):
    def test_initial_player_state(self):
        player = PlayerState()
        self.assertEqual(player.hp, 100)
        self.assertEqual(player.armor, 0)
        self.assertFalse(player.is_dead)

    def test_unarmored_damage(self):
        player = PlayerState()
        player.apply_damage(30)
        self.assertEqual(player.hp, 70)
        self.assertEqual(player.armor, 0)
        self.assertFalse(player.is_dead)

    def test_armored_damage_doom_absorption(self):
        player = PlayerState()
        player.armor = 60
        # 30 damage: absorbed = 30 // 3 = 10. Armor becomes 50. HP damage = 20. HP becomes 80.
        player.apply_damage(30)
        self.assertEqual(player.armor, 50)
        self.assertEqual(player.hp, 80)

    def test_armor_clamp_absorption(self):
        player = PlayerState()
        player.armor = 5
        # 30 damage: absorbed = 10, but armor only has 5.
        # absorbed is clamped to 5. Armor becomes 0. HP damage = 30 - 5 = 25. HP becomes 75.
        player.apply_damage(30)
        self.assertEqual(player.armor, 0)
        self.assertEqual(player.hp, 75)

    def test_death_transition(self):
        player = PlayerState()
        player.apply_damage(150)
        self.assertEqual(player.hp, 0)
        self.assertTrue(player.is_dead)
        # Post-death damage is ignored
        player.apply_damage(50)
        self.assertEqual(player.hp, 0)

    def test_health_pickup(self):
        player = PlayerState()
        # Cannot pick up at 100 HP
        self.assertFalse(player.collect_pickup("health", 25))
        # Damaged to 70 HP
        player.hp = 70
        self.assertTrue(player.collect_pickup("health", 25))
        self.assertEqual(player.hp, 95)
        # Cap at max HP
        self.assertTrue(player.collect_pickup("health", 25))
        self.assertEqual(player.hp, 100)

    def test_armor_pickup(self):
        player = PlayerState()
        self.assertEqual(player.armor, 0)
        self.assertTrue(player.collect_pickup("armor", 50))
        self.assertEqual(player.armor, 50)
        self.assertTrue(player.collect_pickup("armor", 60))
        self.assertEqual(player.armor, 100)  # clamped at max 100
        self.assertFalse(player.collect_pickup("armor", 10))  # rejected when full

    def test_ammo_pickup(self):
        player = PlayerState()
        self.assertEqual(player.ammo["shotgun"], 12)
        self.assertTrue(player.collect_pickup("shotgun", 10))
        self.assertEqual(player.ammo["shotgun"], 22)
        # Fill up to max
        player.ammo["shotgun"] = 50
        self.assertFalse(player.collect_pickup("shotgun", 10))

    def test_lcg_rng_deterministic(self):
        rng1 = LcgRng(42)
        seq1 = [rng1.range(1, 100) for _ in range(10)]
        rng2 = LcgRng(42)
        seq2 = [rng2.range(1, 100) for _ in range(10)]
        self.assertEqual(seq1, seq2)


if __name__ == "__main__":
    unittest.main()
