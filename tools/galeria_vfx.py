#!/usr/bin/env python3
"""Galeria de VFX finales: escenarios de auras / rayo base (galeria_*.json) y GIFs de una sola variante."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import abc_scenes as S
S.CAM_Y = S.HY - 95   # measured: the hero's feet are at screen y ~95 on the current ROM (the old 133 left the beam 38 px low)

AUR = {"aura_E": (S.RELIC["CILICIO"], 0), "aura_H": (S.RELIC["SED_CENIZA"], 0),
       "aura_G": (S.RELIC["VIATICO"], 0), "aura_L": (S.RELIC["FLAGELADO"], 1), "rayo_base": (0, 0)}

def build(name):
    mask, dbg = AUR[name]
    en = [(S.EXVOTO, 262, S.HY)]
    ex = S.tough(1)
    if dbg:
        ex += [{"field": "aura_dbg", "value": dbg}]
    body = [{"tap": S.touch(262), "frames": 2}, S.seq(0, "1charge", 100),
            {"release": True, "frames": 1, "capture_sequence": "v0_2shot", "capture_every": 1},
            S.seq(0, "3shot", 16, every=1), S.seq(0, "4after", 20)]
    steps = [{"frames": 30}] + S.sw(0, mask, en, extra=ex, body=body)
    f = dict(S.FIELDS); f["aura_dbg"] = {"symbol": "ad", "offset": 0, "type": "u32"}
    return {"name": f"galeria_{name}", "suite": False, "evidence_only": True,
            "description": f"Galeria VFX: {name} (cathedral-sandbox).",
            "state": {"symbols": {"sb": "g_sandbox", "u": "g_upg_debug", "p": "g_player_state", "a": "g_abc_debug",
                                  "en": "g_enemies", "ad": "g_aura_debug_mask"},
                      "default_symbol": "sb", "fields": f}, "steps": steps}

def longcharge(d):
    for st in d["steps"]:
        if str(st.get("capture_sequence", "")).endswith("1charge") and el_not_votiva(d):
            st["frames"] = 100
    return d

def el_not_votiva(d):
    return "votiva" not in d["name"]

if __name__ == "__main__":
    for n in AUR:
        (S.ROOT / "scenarios" / f"galeria_{n}.json").write_text(json.dumps(build(n), indent=1) + "\n", newline="")

    # abc elements with a shot, regenerated with the corrected camera
    for el in ("votiva", "martirio", "autofe", "viatico"):
        (S.ROOT / "scenarios" / f"galeria_abc_{el}.json").write_text(json.dumps(longcharge(S.build(el)), indent=1) + chr(10), newline="")
