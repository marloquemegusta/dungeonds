import json
import re
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "assets" / "arenas" / "arenas.json").read_text(encoding="utf-8"))
FOOTPRINT = ((0, 0), (-16, 0), (16, 0), (0, -12), (0, 12), (-12, -8), (-12, 8), (12, -8), (12, 8))
ENEMY_CODE = {"charger": 1, "shooter": 2}
NUM_PACKS = 9
MAX_PACK_SIZE = 10           # MAX_GAMEPLAY_ENEMIES: a pack is spawned at once
PACK_RADIUS = 180            # px, members stay this close to the pack centre (a pack lives in one room)
PACK_MIN_START_DISTANCE = 300  # ground metric sqrt(dx^2 + 4 dy^2) from the player start


def load_arena(path):
    text = path.read_text(encoding="utf-8")
    field = lambda name: int(re.search(rf"\.{name} = (\d+)", text).group(1))
    packed = np.array([int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]{2}\b", text.split("s_collision[")[1].split("};")[0])], dtype=np.uint8)
    cw, ch = field("collision_w"), field("collision_h")
    idx = np.arange(cw * ch, dtype=np.uint32)
    grid = ((packed[idx >> 2] >> ((idx & 3) * 2)) & 3).reshape((ch, cw))
    enemies = []
    body = text.split("s_enemies[] = {")[1].split("};")[0]
    for code, pack, x, y in re.findall(r"\{ ARENA_ENEMY_(CHARGER|SHOOTER), (\d+), (\d+), (\d+) \}", body):
        enemies.append((code.lower(), int(pack), int(x), int(y)))
    return {"world": (field("world_w"), field("world_h")), "player": (field("player_x"), field("player_y")),
            "grid": grid, "enemies": enemies, "num_enemies": field("num_enemies")}


def clear_for_body(grid, x, y):
    return all(grid[(y + dy) // 4, (x + dx) // 4] & 1 == 0 for dx, dy in FOOTPRINT)


class ArenaDataTest(unittest.TestCase):
    """The baked arenas (source/arena_*.c) agree with assets/arenas/arenas.json."""

    def setUp(self):
        self.files = sorted((ROOT / "source").glob("arena_*.c"))
        self.assertTrue(self.files, "no baked arenas")

    def test_only_the_dungeon_is_baked(self):
        self.assertEqual([a["name"] for a in SPEC["arenas"]], ["dungeon_01"])
        self.assertEqual([p.name for p in self.files], ["arena_dungeon_01.c"])
        listing = (ROOT / "source" / "arenas.c").read_text(encoding="utf-8")
        self.assertIn("&g_arena_dungeon_01,", listing)
        self.assertIn("const int g_num_arenas = 1;", listing)

    def test_start_and_spawn_points_are_clear_for_the_body(self):
        for path in self.files:
            arena = load_arena(path)
            with self.subTest(arena=path.name):
                self.assertTrue(clear_for_body(arena["grid"], *arena["player"]), "player start")
                for kind, pack, x, y in arena["enemies"]:
                    self.assertTrue(clear_for_body(arena["grid"], x, y), f"{kind} spawn ({x},{y})")
                self.assertEqual(len(arena["enemies"]), arena["num_enemies"])

    def test_arena_follows_the_spec(self):
        baked = {p.stem[len("arena_"):]: p for p in self.files}
        for spec in SPEC["arenas"]:
            arena = load_arena(baked[spec["name"]])
            with self.subTest(arena=spec["name"]):
                self.assertEqual(arena["world"], tuple(SPEC["image"]))
                self.assertEqual(arena["player"], tuple(spec["player_start"]))
                self.assertEqual(sorted(arena["enemies"]),
                                 sorted((e["type"], e["pack"], *e["at"]) for e in spec["enemies"]))

    def test_packs(self):
        spec = SPEC["arenas"][0]
        px, py = spec["player_start"]
        packs = {}
        for e in spec["enemies"]:
            self.assertIn(e["type"], ENEMY_CODE)
            packs.setdefault(e["pack"], []).append(e)
        self.assertEqual(sorted(packs), list(range(NUM_PACKS)))
        composition = {p: tuple(sum(1 for e in members if e["type"] == t) for t in ("charger", "shooter"))
                       for p, members in packs.items()}
        self.assertEqual(composition, {0: (1, 2), 1: (2, 1), 2: (3, 0), 3: (2, 2), 4: (1, 3), 5: (4, 0), 6: (2, 3), 7: (3, 2), 8: (1, 4)})
        for p, members in packs.items():
            with self.subTest(pack=p):
                self.assertLessEqual(len(members), MAX_PACK_SIZE)
                cx = sum(e["at"][0] for e in members) / len(members)
                cy = sum(e["at"][1] for e in members) / len(members)
                for e in members:
                    self.assertLessEqual(((e["at"][0] - cx) ** 2 + (e["at"][1] - cy) ** 2) ** 0.5, PACK_RADIUS)
                    ground = ((e["at"][0] - px) ** 2 + 4 * (e["at"][1] - py) ** 2) ** 0.5
                    self.assertGreaterEqual(ground, PACK_MIN_START_DISTANCE, f"{e['type']} {e['at']} too close to the start")


if __name__ == "__main__":
    unittest.main()
