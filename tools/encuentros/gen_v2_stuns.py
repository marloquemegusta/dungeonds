#!/usr/bin/env python3
"""Genera scenarios/encuentros_v2_stuns.json: comprueba que un Cireneo que embiste contra un banco, un saco, un alambre o una
estatua queda aturdido (ENEMY_STATE_STUNNED = 6). La embestida se arma con pokes sobre g_enemies (posicion, estado CHARGE y
direccion); el aturdimiento lo decide el juego (sweep_position falla contra el cuerpo bloqueante)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SLOT = 124
TOP = 1152
# nombre, planta (1..6), tier (1..3), slot del Cireneo, x local, y local de salida, direccion (dx, dy) 8.8 en metrica de suelo
CASES = [
    ("banco", 1, 2, 10, 115, 150, (-256, 0)),
    ("saco", 2, 3, 2, 80, 300, (0, -128)),
    ("alambre", 6, 3, 2, 70, 235, (0, -128)),
    ("estatua", 3, 3, 2, 140, 326, (-256, 0)),
]
fields = {
    "woken": {"offset": 4, "type": "u8"},
    "dbg_auto_pick": {"symbol": "dbg", "offset": 1, "type": "u8"}, "dbg_god": {"symbol": "dbg", "offset": 2, "type": "u8"},
    "dbg_force_plant": {"symbol": "dbg", "offset": 10, "type": "u8"}, "dbg_force_tier": {"symbol": "dbg", "offset": 11, "type": "u8"},
    "dbg_restart": {"symbol": "dbg", "offset": 12, "type": "u8"},
}
steps = [{"frames": 20}, {"poke": [{"field": "dbg_god", "value": 1}, {"field": "dbg_auto_pick", "value": 1}], "frames": 2}]
checks = []
for name, plant, tier, slot, lx, ly, (adx, ady) in CASES:
    for nm, off, t in (("x", 0, "s32"), ("y", 4, "s32"), ("state", 41, "u8"), ("timer", 44, "s32"), ("hit", 48, "s32"),
                       ("adx", 52, "s32"), ("ady", 56, "s32")):
        fields[f"{name}_{nm}"] = {"symbol": "en", "offset": slot * SLOT + off, "type": t}
    steps += [
        {"poke": [{"field": "dbg_force_plant", "value": plant}, {"field": "dbg_force_tier", "value": tier},
                  {"field": "dbg_restart", "value": 1}], "frames": 40},
        {"button_down": "UP", "wait_until": {"field": "woken", "min_value": 1, "timeout_frames": 1200}},
        {"button_up": "UP", "frames": 1},
        {"poke": [{"field": f"{name}_x", "value": (152 + lx) * 256}, {"field": f"{name}_y", "value": (TOP + ly) * 256},
                  {"field": f"{name}_state", "value": 4}, {"field": f"{name}_timer", "value": 45},
                  {"field": f"{name}_hit", "value": 0}, {"field": f"{name}_adx", "value": adx},
                  {"field": f"{name}_ady", "value": ady}], "frames": 0},
        {"frames": 50, "capture": f"{name}_stun", "state_capture": f"{name}_t50"},
    ]
    checks.append({"at": f"{name}_t50", "field": f"{name}_state", "equals": 6})
sc = {"name": "encuentros_v2_stuns", "description": "El Cireneo que embiste contra banco, saco, alambre y estatua queda aturdido.",
      "suite": False, "evidence_only": True,
      "state": {"elf": "../.ds-game-dev/build/out/dungeonds-encuentros.elf",
                "symbols": {"stats": "g_enc_stats", "dbg": "g_enc_debug", "en": "g_enemies"},
                "default_symbol": "stats", "fields": fields},
      "steps": steps, "assertions": {"state_changes": checks}}
with open(os.path.join(ROOT, "scenarios", "encuentros_v2_stuns.json"), "w", newline="\n") as f:
    json.dump(sc, f, indent=2)
    f.write("\n")
print(len(steps), "pasos")
