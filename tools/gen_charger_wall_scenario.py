"""Generates scenarios/charger_walks_around_wall.json.

tests/host/nav_path_tool.c picks, with the real baked collision grid, a floor node the spawn
cannot see (a wall corner in between) and prints the node path to it. This script turns that
path into D-pad steps for the player, so the chargers have to go around the corner to reach
the player (DESIGN.md 4.4 requirement: the straight-line chase used to get stuck there).

usage: python.exe tools/gen_charger_wall_scenario.py   (needs gcc on PATH)
"""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_PX = 16
PLAYER_SPEED = 326 / 256          # px/frame, marine speedFixed8_8 (settings.json)

with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / "nav_path.exe"
    subprocess.run(["gcc", "-std=gnu11", "-O1", "-I", str(ROOT / "tests/host/stubs"), "-I", str(ROOT / "include"),
                    str(ROOT / "tests/host/nav_path_tool.c"), str(ROOT / "source/collision.c"),
                    str(ROOT / "source/navfield.c"), str(ROOT / "source/diablo_dungeon.c"),
                    str(ROOT / "source/los.c"), "-o", str(exe), "-lm"], check=True)
    out = subprocess.run([str(exe), "60"], capture_output=True, text=True, check=True).stdout.splitlines()

target = out[0].split()
steps_nodes = [tuple(int(v) for v in line.split()[1:]) for line in out[1:] if line.startswith("STEP")]

# Orthogonal moves only (the corner rule guarantees both orthogonal neighbours are walkable).
# Screen Y is half-speed on the ground (2:1 projection). Fractions of frames carry over.
moves = []
carry = {"x": 0.0, "y": 0.0}
for sdx, sdy in steps_nodes:
    for axis, delta, key_neg, key_pos, speed in (("x", sdx, "LEFT", "RIGHT", PLAYER_SPEED),
                                                  ("y", sdy, "UP", "DOWN", PLAYER_SPEED / 2)):
        if delta == 0:
            continue
        frames = abs(delta) * NODE_PX / speed + carry[axis]
        whole = int(round(frames))
        carry[axis] = frames - whole
        moves.append((key_pos if delta > 0 else key_neg, max(whole, 1)))

steps = [{"frames": 20, "capture": "00_start"}]
for key, frames in moves:
    steps.append({"button_down": key, "frames": frames})
    steps.append({"button_up": key, "frames": 1})
steps.append({"frames": 15, "capture": "01_arrived"})
steps.append({"frames": 120, "capture": "02_chasers_arrive"})

scenario = {"name": "charger_walks_around_wall", "target_world_px": [int(target[1]), int(target[2])],
            "steps": steps,
            "assertions": {"screen_changes": [{"from": "00_start", "to": "02_chasers_arrive", "min_changed_pixels": 300}]}}
(ROOT / "scenarios" / "charger_walks_around_wall.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8", newline="\n")
print("target", target[1:3], "moves", len(moves), "total frames", sum(f for _, f in moves))
