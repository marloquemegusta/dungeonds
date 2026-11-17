#!/usr/bin/env python3
"""Genera scenarios/encuentros_guia.json: una captura de la ROM real (variante `encuentros`) por cada una de las
18 combinaciones planta x tier, con el primer encuentro forzado (g_enc_debug.force_plant / force_tier + restart).

Por combinacion: (a) heroe recien cruzando el borde de abajo del encuentro, enemigos en su sitio inicial;
(b) unos 3 s despues de despertar, heroe quieto; (c) si hay wave2, justo cuando entra (se mata la primera
oleada con la depuracion L+R+X). Nombres: <planta>_<tier>_a|b|c.png
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLANTAS = list(json.load(open(os.path.join(ROOT, "tools", "encuentros", "acto1_v2.json"), encoding="utf-8"))["plantas"])
DATA = json.load(open(os.path.join(ROOT, "tools", "encuentros", "acto1_v2.json"), encoding="utf-8"))["plantas"]
TIERS = ["ligera", "media", "dura"]

fields = {
    "woken": {"offset": 4, "type": "u8"}, "cleared": {"offset": 5, "type": "u8"},
    "alive": {"offset": 61, "type": "u8"}, "blocked": {"offset": 188, "type": "u8"}, "plant": {"offset": 2, "type": "u8"}, "tier": {"offset": 3, "type": "u8"},
    "dbg_auto_pick": {"symbol": "dbg", "offset": 1, "type": "u8"}, "dbg_god": {"symbol": "dbg", "offset": 2, "type": "u8"},
    "dbg_force_plant": {"symbol": "dbg", "offset": 10, "type": "u8"}, "dbg_force_tier": {"symbol": "dbg", "offset": 11, "type": "u8"},
    "dbg_restart": {"symbol": "dbg", "offset": 12, "type": "u8"}, "dbg_cam_up": {"symbol": "dbg", "offset": 13, "type": "u8"},
    "hero_x": {"symbol": "nav", "offset": 0, "type": "s32"}, "hero_y": {"symbol": "nav", "offset": 4, "type": "s32"},
}

steps = [{"frames": 20}, {"poke": [{"field": "dbg_god", "value": 1}, {"field": "dbg_auto_pick", "value": 1}, {"field": "dbg_cam_up", "value": 56}], "frames": 2}]
names = []
ONLY = os.environ.get("GUIA_ONLY")          # depuracion: "planta_tier"
for pi, planta in enumerate(PLANTAS):
    for ti, tier in enumerate(TIERS):
        if ONLY and ONLY != f"{planta}_{tier}": continue
        tag = f"{planta}_{tier}"
        names.append(tag)
        steps.append({"poke": [{"field": "dbg_force_plant", "value": pi + 1}, {"field": "dbg_force_tier", "value": ti + 1},
                               {"field": "dbg_restart", "value": 1}], "frames": 30,
                      "state_capture": f"{tag}_ini"})
        steps.append({"frames": 60, "state_capture": f"{tag}_ini2"})
        steps.append({"button_down": "UP", "wait_until": {"field": "woken", "min_value": 1, "timeout_frames": 1200}})
        steps.append({"button_up": "UP", "frames": 2, "capture": f"{tag}_a", "state_capture": f"{tag}_a"})
        steps.append({"frames": 180, "capture": f"{tag}_b", "state_capture": f"{tag}_b"})
        if DATA[planta][tier].get("wave2"):
            steps.append({"button_down": "L", "frames": 1})
            steps.append({"button_down": "R", "frames": 1})
            steps.append({"button_down": "X", "frames": 3})
            steps.append({"button_up": "X", "frames": 1})
            steps.append({"button_up": "R", "frames": 1})
            steps.append({"button_up": "L", "frames": 14, "capture": f"{tag}_c", "state_capture": f"{tag}_c"})

sc = {
    "name": "encuentros_guia",
    "description": "Guia de plantas (variante encuentros): una captura por combinacion planta x tier con el primer encuentro forzado (g_enc_debug.force_plant/force_tier + restart). Capturas _a (entrada), _b (3 s tras despertar), _c (wave2).",
    "suite": False, "evidence_only": True,
    "state": {"elf": "../.ds-game-dev/build/out/dungeonds-encuentros.elf",
              "symbols": {"stats": "g_enc_stats", "dbg": "g_enc_debug", "nav": "g_nav_state"},
              "default_symbol": "stats", "fields": fields},
    "steps": steps,
    "assertions": {"state_changes": [{"at": f"{names[-1]}_b", "field": "woken", "min_value": 1}]},
}
with open(os.path.join(ROOT, "scenarios", "encuentros_guia.json"), "w", newline="\n") as f:
    json.dump(sc, f, indent=2)
    f.write("\n")
print(len(steps), "pasos,", len(names), "combinaciones")
