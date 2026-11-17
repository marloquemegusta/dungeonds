#!/usr/bin/env python3
"""Genera scenarios/encuentros_v2_gifs.json: dos escenas montadas para GIF (variante `encuentros`, heroe invulnerable).

1. exvoto: procesion ligera, un solo Exvoto en el pasillo; el heroe carga el rayo apuntando al pasillo y el Exvoto
   se aparta de la linea (frames `exvoto_NNNN`).
2. cireneo: balcon dura, un solo Cireneo que embiste de lado contra una estatua y queda aturdido (frames `cireneo_NNNN`).
   La embestida se arma con pokes sobre g_enemies (posicion, estado CHARGE y direccion): el aturdimiento es el del juego.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SLOT = 124                  # sizeof(Enemy)


def enemy_field(slot, name, offset, typ="s32"):
    return name, {"symbol": "en", "offset": slot * SLOT + offset, "type": typ}


fields = {
    "woken": {"offset": 4, "type": "u8"}, "alive": {"offset": 61, "type": "u8"},
    "dbg_auto_pick": {"symbol": "dbg", "offset": 1, "type": "u8"}, "dbg_god": {"symbol": "dbg", "offset": 2, "type": "u8"},
    "dbg_force_plant": {"symbol": "dbg", "offset": 10, "type": "u8"}, "dbg_force_tier": {"symbol": "dbg", "offset": 11, "type": "u8"},
    "dbg_restart": {"symbol": "dbg", "offset": 12, "type": "u8"},
    "hero_x": {"symbol": "nav", "offset": 0, "type": "s32"}, "hero_y": {"symbol": "nav", "offset": 4, "type": "s32"},
}
for slot in range(16):
    fields[f"a{slot}"] = {"symbol": "en", "offset": slot * SLOT + 24, "type": "s32"}      # active
for slot in (2, 6):
    for nm, off, t in (("x", 0, "s32"), ("y", 4, "s32"), ("state", 41, "u8"), ("timer", 44, "s32"), ("hit", 48, "s32"),
                       ("adx", 52, "s32"), ("ady", 56, "s32"), ("hp", 28, "s32")):
        fields[f"s{slot}_{nm}"] = {"symbol": "en", "offset": slot * SLOT + off, "type": t}


def kill_others(keep, n):
    return [{"field": f"a{i}", "value": 0} for i in range(n) if i != keep]


steps = [{"frames": 20}, {"poke": [{"field": "dbg_god", "value": 1}, {"field": "dbg_auto_pick", "value": 1}], "frames": 2}]

# --- 1. Exvoto que esquiva el rayo ---------------------------------------------------------------------------
steps += [
    {"poke": [{"field": "dbg_force_plant", "value": 1}, {"field": "dbg_force_tier", "value": 1}, {"field": "dbg_restart", "value": 1}],
     "frames": 40},
    {"poke": kill_others(6, 8), "frames": 1},                      # procesion ligera: el Exvoto de (94,250) es el slot 6
    {"button_down": "UP", "wait_until": {"field": "woken", "min_value": 1, "timeout_frames": 1200}},
    {"button_up": "UP", "frames": 1},
    {"tap": {"x": 128, "y": 40}, "frames": 3, "capture_sequence": "exvoto", "capture_every": 3},
    {"frames": 120, "capture_sequence": "exvoto_b", "capture_every": 3},
    {"release": True, "frames": 40, "capture_sequence": "exvoto_c", "capture_every": 3, "state_capture": "exvoto_fin"},
]

# --- 2. Cireneo que embiste contra la estatua ------------------------------------------------------------------
TOP = 1152                                   # y de mundo del borde de arriba del bloque 1 tras un reinicio
steps += [
    {"poke": [{"field": "dbg_force_plant", "value": 3}, {"field": "dbg_force_tier", "value": 3}, {"field": "dbg_restart", "value": 1}],
     "frames": 40},
    {"poke": kill_others(2, 11), "frames": 1},                     # balcon dura: el Cireneo es el slot 2
    {"button_down": "UP", "wait_until": {"field": "woken", "min_value": 1, "timeout_frames": 1200}},
    {"button_up": "UP", "frames": 1},
    {"poke": [{"field": "s2_x", "value": (152 + 140) * 256}, {"field": "s2_y", "value": (TOP + 326) * 256},
              {"field": "s2_state", "value": 4}, {"field": "s2_timer", "value": 45}, {"field": "s2_hit", "value": 0},
              {"field": "s2_adx", "value": -256}, {"field": "s2_ady", "value": 0}],
     "frames": 3, "capture_sequence": "cireneo", "capture_every": 3, "state_capture": "cireneo_ini"},
    {"frames": 150, "capture_sequence": "cireneo_b", "capture_every": 3, "state_capture": "cireneo_fin"},
]

sc = {
    "name": "encuentros_v2_gifs",
    "description": "Dos escenas montadas para GIF (variante encuentros): Exvoto esquivando el rayo y Cireneo embistiendo contra una estatua.",
    "suite": False, "evidence_only": True,
    "state": {"elf": "../.ds-game-dev/build/out/dungeonds-encuentros.elf",
              "symbols": {"stats": "g_enc_stats", "dbg": "g_enc_debug", "nav": "g_nav_state", "en": "g_enemies"},
              "default_symbol": "stats", "fields": fields},
    "steps": steps,
    "assertions": {"state_changes": [{"at": "cireneo_fin", "field": "woken", "min_value": 1}]},
}
with open(os.path.join(ROOT, "scenarios", "encuentros_v2_gifs.json"), "w", newline="\n") as f:
    json.dump(sc, f, indent=2)
    f.write("\n")
print(len(steps), "pasos")
