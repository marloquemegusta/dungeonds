#!/usr/bin/env python3
"""Generates scenarios/cobertura_baja_agachado.json: the hero crouches behind a bench group and an Ojo fires its beam
across it (DESIGN.md 6.9, "Agacharse tras coberturas bajas"). Runs on dungeonds-cathedral-sandbox.nds
(build-project.ps1 -Variant cathedral-sandbox): the stable seed 0xC0DE1234 puts a banco_grupo4 at world (280, 832)
(tests/test_strip_layout_parity.py plan: block 2, x_tile 35, y_tile 8).

Geometry (checked against the stamp's footprint runs in source/strip_kit.c, value 2 = low cover):
  bench rows (solid cells of 4 px, value 2) x 288..351 and y 848..863, 872..887, 896..911, 920..935 (8 px gaps between rows).
  The hero stands at x = 281 (the body radius 6 keeps him 7 px from the face at x = 288) in the first row, y 862 -> 854.
  The Ojo stands east of the group at (372, 854): the beam runs west along y ~ 854 and crosses 64 px of bench cells
  (x 288..351) before it reaches him. Ground distance 91 px < OJO_SIGHT_RANGE (140), no wall in between.

Run:  python tools/cobertura_scenes.py     then     run-scenario.ps1 -ScenarioPath scenarios/cobertura_baja_agachado.json
      -RomPath dungeonds-cathedral-sandbox.nds -ProjectPath <worktree>
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENEMY_SIZE = 124                       # sizeof(Enemy) on the ARM build
OJO = 2
HX, HY0, HY1 = 281, 862, 854           # hero: start and where the staged Ojo finds him
OX, OY = 372, 854                      # Ojo
FLAGS = 1 | 32                         # clear the enemies, no gems; the AI runs and the hero is NOT invulnerable
ST_TRACK, ST_LOCK, ST_SENTENCE, ST_COOLDOWN = 7, 8, 9, 10

FIELDS = {
    "seq": {"offset": 0, "type": "u32"}, "ack": {"offset": 4, "type": "u32"},
    "player_x": {"offset": 8, "type": "s16"}, "player_y": {"offset": 10, "type": "s16"},
    "weapon": {"offset": 12, "type": "u8"}, "style": {"offset": 13, "type": "u8"},
    "enemy_count": {"offset": 14, "type": "u8"}, "flags": {"offset": 15, "type": "u8"},
    "e0_type": {"offset": 16, "type": "u8"}, "e0_flags": {"offset": 17, "type": "u8"},
    "e0_x": {"offset": 18, "type": "s16"}, "e0_y": {"offset": 20, "type": "s16"},
    "en0_state": {"symbol": "enemies", "offset": 41, "type": "u8"},
    "en0_hp": {"symbol": "enemies", "offset": 28, "type": "s32"},
    "player_hp": {"symbol": "player", "offset": 0, "type": "s32"},
    "crouched": {"symbol": "crouch", "offset": 0, "type": "s32"},
    "nav_x": {"symbol": "nav", "offset": 0, "type": "s32"}, "nav_y": {"symbol": "nav", "offset": 4, "type": "s32"},
}


def pokes(**kw):
    return [{"field": k, "value": v} for k, v in kw.items()]


def stage(hy, enemies):
    p = pokes(player_x=HX, player_y=hy, weapon=0, style=0, flags=FLAGS, enemy_count=len(enemies))
    for i, (t, x, y) in enumerate(enemies):
        p += pokes(**{f"e{i}_type": t, f"e{i}_flags": 0, f"e{i}_x": x, f"e{i}_y": y})
    return p


def seq(name, frames, every=3, **kw):
    return {"frames": frames, "capture_sequence": name, "capture_every": every, **kw}


steps = [
    {"frames": 1000},                   # the strip settles (same wait as cathedral_bench_collision.json)
    # 1. staged hugging the west face of the first bench, no enemy: he crouches after the 6-frame debounce
    {"poke": stage(HY1 + 8, []) + pokes(seq=1), "frames": 1},
    {"wait_until": {"field": "ack", "equals": 1, "timeout_frames": 30}},
    {"frames": 3},                      # the strip bands under the teleport finish drawing
    # The bench is east of him (x 288): he crouches only while the cross pushes RIGHT, toward it (DESIGN.md 6.13.6).
    {"button_down": "RIGHT", **seq("s1_agacha", 24, state_capture="quieto")},
    # 2. pushes UP too (diagonal toward the bench): walks north along the face, crouched and slow
    {"button_down": "UP", **seq("s2_andar", 30, state_capture="andando")},
    {"button_up": "UP", **seq("s3_quieto", 18)},
    # 2b. parallel: from the south end of the face he pushes only UP (along the bench, away from it): he stands
    {"poke": stage(HY0, []) + pokes(seq=3), "frames": 1},
    {"wait_until": {"field": "ack", "equals": 3, "timeout_frames": 30}},
    {"frames": 3},
    {"button_up": "RIGHT", "frames": 0},
    {"button_down": "UP", **seq("s2b_paralelo", 14, state_capture="paralelo")},
    {"button_up": "UP", "frames": 0},
    {"button_down": "RIGHT", "frames": 0},
    # 3. the Ojo appears across the bench and aims: track -> lock -> the beam crosses the bench and misses
    {"poke": stage(HY1, [(OJO, OX, OY)]) + pokes(seq=4), "frames": 1},
    {"wait_until": {"field": "ack", "equals": 4, "timeout_frames": 30}},
    seq("s4_mira", 30),
    # crouched and still pushing RIGHT: the Ojo waits at the start of its aim (TRACK) and never fires at him
    seq("s5_espera", 200, every=20, state_capture="espera_cubierto"),
    # 4. next gaze: the stylus touches (he stands up to aim) and the same beam hits him
    {"button_up": "RIGHT", "frames": 0},  # letting go of the cross too: a held push would crouch him again after the tap
    {"tap": {"x": 217, "y": 112}, **seq("s6_levanta", 24, state_capture="de_pie")},
    {"wait_until": {"field": "en0_state", "equals": ST_SENTENCE, "timeout_frames": 200}},
    seq("s7_haz2", 36, state_capture="haz2_fin"),
    {"release": True, "frames": 40, "capture_sequence": "s8_suelta", "capture_every": 3},
]

scenario = {
    "name": "cobertura_baja_agachado",
    "description": "cathedral-sandbox ROM (seed 0xC0DE1234, banco_grupo4 at world 280,832; see tools/cobertura_scenes.py). The hero "
                   "hugs the west face of the first bench row (x 281, y 862 -> 854). He crouches only while he pushes RIGHT toward the "
                   "bench (pose, then crouched walk at half speed, also diagonal up-right); pushing only UP along the face he stands. "
                   "An Ojo at (372,854) beams west along y ~854 across 64 px of low-cover cells (x 288..351): crouched he takes no "
                   "damage. On the next gaze the stylus touches, he stands up and the same line hits him (5 -> 4 hp).",
    "tags": ["coberturas", "ojo-tribunal"],
    "state": {"symbols": {"sb": "g_sandbox", "enemies": "g_enemies", "player": "g_player_state", "crouch": "g_hero_crouched", "nav": "g_nav_state"},
              "default_symbol": "sb", "fields": FIELDS},
    "steps": steps,
    "assertions": {
        "state_changes": [
            {"at": "quieto", "field": "crouched", "equals": 1},
            {"at": "andando", "field": "crouched", "equals": 1},
            {"at": "paralelo", "field": "crouched", "equals": 0},
            {"at": "espera_cubierto", "field": "crouched", "equals": 1},
            {"at": "espera_cubierto", "field": "en0_state", "equals": ST_TRACK},
            {"at": "espera_cubierto", "field": "player_hp", "equals": 5},
            {"at": "de_pie", "field": "crouched", "equals": 0},
            {"at": "haz2_fin", "field": "player_hp", "equals": 4},
        ]
    },
}

out = ROOT / "scenarios" / "cobertura_baja_agachado.json"
out.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8", newline="\n")
print("wrote", out)
