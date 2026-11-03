import json
import re
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "assets" / "arenas" / "arenas.json").read_text(encoding="utf-8"))
FOOTPRINT = ((0, 0), (-16, 0), (16, 0), (0, -12), (0, 12), (-12, -8), (-12, 8), (12, -8), (12, 8))
ENEMY_CODE = {"charger": 1, "shooter": 2}


def load_arena(path):
    text = path.read_text(encoding="utf-8")
    field = lambda name: int(re.search(rf"\.{name} = (\d+)", text).group(1))
    packed = np.array([int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]{2}\b", text.split("s_collision[")[1].split("};")[0])], dtype=np.uint8)
    cw, ch = field("collision_w"), field("collision_h")
    idx = np.arange(cw * ch, dtype=np.uint32)
    grid = ((packed[idx >> 2] >> ((idx & 3) * 2)) & 3).reshape((ch, cw))
    enemies = [(int(t), int(x), int(y)) for t, x, y in re.findall(r"\{ ARENA_ENEMY_\w+ ?,? ?", "")] if False else []
    body = text.split("s_enemies[] = {")[1].split("};")[0]
    for code, x, y in re.findall(r"\{ ARENA_ENEMY_(CHARGER|SHOOTER), (\d+), (\d+) \}", body):
        enemies.append((code.lower(), int(x), int(y)))
    return {"world": (field("world_w"), field("world_h")), "player": (field("player_x"), field("player_y")),
            "grid": grid, "enemies": enemies, "num_enemies": field("num_enemies")}


def clear_for_body(grid, x, y):
    return all(grid[(y + dy) // 4, (x + dx) // 4] & 1 == 0 for dx, dy in FOOTPRINT)


class ArenaDataTest(unittest.TestCase):
    """The baked arenas (source/arena_*.c) agree with assets/arenas/arenas.json and DESIGN.md 4.6."""

    def setUp(self):
        self.files = sorted((ROOT / "source").glob("arena_*.c"))
        self.assertTrue(self.files, "no baked arenas")

    def test_start_and_spawn_points_are_clear_for_the_body(self):
        for path in self.files:
            arena = load_arena(path)
            with self.subTest(arena=path.name):
                self.assertTrue(clear_for_body(arena["grid"], *arena["player"]), "player start")
                for kind, x, y in arena["enemies"]:
                    self.assertTrue(clear_for_body(arena["grid"], x, y), f"{kind} spawn ({x},{y})")
                self.assertEqual(len(arena["enemies"]), arena["num_enemies"])
                self.assertLessEqual(arena["num_enemies"], 10)       # MAX_GAMEPLAY_ENEMIES

    def test_arenas_follow_the_design(self):
        names = [a["name"] for a in SPEC["arenas"]]
        baked = {p.stem: p for p in self.files}
        for spec in SPEC["arenas"]:
            stem = spec["name"]
            if stem not in baked:
                continue                                              # not baked yet (legacy only)
            arena = load_arena(baked[stem])
            with self.subTest(arena=stem):
                self.assertEqual(arena["world"], tuple(SPEC["image"]))
                self.assertEqual(arena["player"], tuple(spec["player_start"]))
                self.assertEqual(sorted(arena["enemies"]), sorted((e["type"], *e["at"]) for e in spec["enemies"]))
        composition = [{t: sum(1 for e in a["enemies"] if e["type"] == t) for t in ENEMY_CODE} for a in SPEC["arenas"]]
        # DESIGN.md 4.6: chargers -> shooters -> shooters far + 1 charger -> dense mix.
        self.assertEqual(composition, [{"charger": 3, "shooter": 0}, {"charger": 0, "shooter": 3},
                                       {"charger": 1, "shooter": 3}, {"charger": 3, "shooter": 4}])
        self.assertEqual(names, ["arena_01", "arena_02", "arena_03", "arena_04"])


if __name__ == "__main__":
    unittest.main()
