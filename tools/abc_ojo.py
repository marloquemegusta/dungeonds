#!/usr/bin/env python3
"""Generates scenarios/abc_ojo_sentencia.json: the Ojo del Tribunal's "sentencia escrita en el suelo" (A lacre,
B escarcha, C fosforo), one Ojo and the hero alone on the cathedral-sandbox ROM, once per design variant.

Run:  python tools/abc_ojo.py     (then tools/abc_ojo_gif.py --run)
Build: build-project.ps1 -Variant cathedral-sandbox
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abc_scenes as S   # noqa: E402

ROOT = S.ROOT
OJO_TYPE = 2                      # SANDBOX_ENEMY_SHOOTER
HERO = (200, 1760)               # hero feet (the camera keeps him at screen (128, 133))
OJO = (110, 1715)                # 90 px west and 45 px north of him: ~127 ground px (2:1 metric), diagonal
FLAGS = 1 | 2 | 4 | 32           # CLEAR | FREEZE_AI | GOD | NO_GEMS; the AI is released by poking g_sandbox_freeze_ai
STATE = {"TRACK": 7, "LOCK": 8, "SENTENCE": 9, "COOLDOWN": 10}


def fields():
    f = dict(S.FIELDS)
    f["en0_state"] = {"symbol": "en", "offset": 41, "type": "u8"}
    f["en0_timer"] = {"symbol": "en", "offset": 44, "type": "s32"}
    f["px"] = {"symbol": "pl", "offset": 0, "type": "s32"}
    f["py"] = {"symbol": "pl", "offset": 4, "type": "s32"}
    f["fz"] = {"symbol": "fz", "offset": 0, "type": "s32"}
    return f


def build():
    steps = [{"frames": 30}]
    for vi in (0, 1, 2):
        steps += S.stage(vi, 0, [(OJO_TYPE, OJO[0], OJO[1])], flags=FLAGS, hero=HERO)
        steps += [
            {"frames": 24, "capture_sequence": f"v{vi}_0busca", "capture_every": 2},      # frozen in CHASE: it stands and looks
            {"poke": [{"field": "fz", "value": 0}], "frames": 0},
            {"wait_until": {"field": "en0_state", "equals": STATE["TRACK"], "timeout_frames": 400}, "state_capture": f"v{vi}_track0"},
            # TRACK (40 frames): the hero walks up (across the line) for 28 frames, then stands still.
            {"button_down": "UP", "frames": 28, "capture_sequence": f"v{vi}_1trackA", "capture_every": 2, "state_capture": f"v{vi}_trackA"},
            {"button_up": "UP", "frames": 12, "capture_sequence": f"v{vi}_1trackB", "capture_every": 2, "state_capture": f"v{vi}_trackB"},
            {"frames": 20, "capture_sequence": f"v{vi}_2lock", "capture_every": 2, "state_capture": f"v{vi}_lock"},
            {"frames": 31, "capture_sequence": f"v{vi}_3sentencia", "capture_every": 2, "state_capture": f"v{vi}_sentencia"},
            {"frames": 66, "capture_sequence": f"v{vi}_4cicatriz", "capture_every": 2, "state_capture": f"v{vi}_cicatriz"},
            {"release": True, "frames": 2},
        ]
    return {
        "name": "abc_ojo_sentencia", "suite": False, "evidence_only": True,
        "description": "Ojo del Tribunal: sentence written on the floor, design variants A/B/C (cathedral-sandbox ROM; tools/abc_ojo.py).",
        "state": {"symbols": {"sb": "g_sandbox", "u": "g_upg_debug", "p": "g_player_state", "a": "g_abc_debug", "en": "g_enemies", "fz": "g_sandbox_freeze_ai", "pl": "s_player"},
                  "default_symbol": "sb", "fields": fields()},
        "steps": steps,
    }


if __name__ == "__main__":
    (ROOT / "scenarios" / "abc_ojo_sentencia.json").write_text(json.dumps(build(), indent=1) + "\n", newline="")
    print("wrote scenarios/abc_ojo_sentencia.json")
