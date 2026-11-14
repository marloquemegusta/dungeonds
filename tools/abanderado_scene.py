#!/usr/bin/env python3
"""Generates scenarios/abanderado_jefe_ciclo.json to verify the minimal Abanderado boss in DeSmuME."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox_scenes as sb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ABANDERADO_TYPE = 4  # SANDBOX_ENEMY_ABANDERADO
ST_POINT = 11
ST_EMERGE = 12
ENEMY_STRIDE = 116

fields = dict(sb.FIELDS)
fields["en0_active"] = {"symbol": "enemies", "offset": 24, "type": "u8"}
fields["en0_hp"] = {"symbol": "enemies", "offset": 28, "type": "s32"}
fields["en0_state"] = {"symbol": "enemies", "offset": 41, "type": "u8"}
for i in range(1, 3):
    base = i * ENEMY_STRIDE
    fields[f"en{i}_type"] = {"symbol": "enemies", "offset": base + 40, "type": "u8"}
    fields[f"en{i}_active"] = {"symbol": "enemies", "offset": base + 24, "type": "u8"}
    fields[f"en{i}_hp"] = {"symbol": "enemies", "offset": base + 28, "type": "s32"}
    fields[f"en{i}_state"] = {"symbol": "enemies", "offset": base + 41, "type": "u8"}

player = (360, 680)
boss = (448, 680)
aim = sb.touch_at(player, boss[0], boss[1], height=sb.MUZZLE_H)

steps = [
    {"frames": 30},
    {
        "poke": [
            {"field": "player_x", "value": player[0]},
            {"field": "player_y", "value": player[1]},
            {"field": "weapon", "value": sb.WEAPON["sniper"]},
            {"field": "style", "value": 0},
            {"field": "enemy_count", "value": 1},
            {"field": "flags", "value": sb.FLAG_CLEAR | sb.FLAG_GOD},
            {"field": "e0_type", "value": ABANDERADO_TYPE},
            {"field": "e0_flags", "value": 0},
            {"field": "e0_x", "value": boss[0]},
            {"field": "e0_y", "value": boss[1]},
            {"field": "seq", "value": 1},
        ],
        "frames": 1,
    },
    {"wait_until": {"field": "ack", "equals": 1, "timeout_frames": 30}},
    {"wait_until": {"field": "en0_state", "equals": ST_POINT, "timeout_frames": 30}, "state_capture": "apunta"},
    {"frames": 10, "capture": "01_abanderado_apunta"},
    {"frames": 25, "capture": "02_charco_y_monaguillo_emerge", "state_capture": "emerge"},
    # Charge and fire sniper through midpoint while monaguillo emerges (stays invulnerable), hits boss
    {"touch": {"x": aim["x"], "y": aim["y"]}, "frames": 32},
    {"release": True, "frames": 6, "capture": "03_disparo_y_barra_vida", "state_capture": "despues_disparo"},
    {"frames": 25, "capture": "04_monaguillos_caminando", "state_capture": "caminando"},
]

scenario = {
    "name": "abanderado_jefe_ciclo",
    "description": "Stages El Abanderado east of an invulnerable hero: verifies pointing, cream puddle summon, emerging monaguillo invulnerability, health bar, and walking monaguillos.",
    "tags": ["abanderado-jefe"],
    "state": {
        "symbols": {"sb": "g_sandbox", "enemies": "g_enemies"},
        "default_symbol": "sb",
        "fields": fields,
    },
    "steps": steps,
    "assertions": {
        "state_changes": [
            {"at": "apunta", "field": "en0_state", "equals": ST_POINT},
            {"at": "emerge", "field": "en1_active", "equals": 1},
            {"at": "emerge", "field": "en1_state", "equals": ST_EMERGE},
            {"at": "emerge", "field": "en1_hp", "equals": 100},
            {"at": "despues_disparo", "field": "en0_hp", "equals": 1050},
        ]
    },
}

out = ROOT / "scenarios" / "abanderado_jefe_ciclo.json"
out.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
print("Wrote", out)
