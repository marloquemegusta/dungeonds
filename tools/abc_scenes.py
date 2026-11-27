#!/usr/bin/env python3
"""Generates scenarios/abc_<element>.json: one staged scene per upgrade-system visual (DESIGN.md 6.12), shot three
times (design variant A, B, C) on the cathedral-sandbox ROM. Only the hero and the enemies the effect needs are
spawned (sandbox mailbox, AI frozen, god mode); nothing else exists in the scene.

Run:  python tools/abc_scenes.py     (then tools/abc_gif.py <element> --run)
Build: build-project.ps1 -Variant cathedral-sandbox
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Hero stands at (HX, HY); the camera keeps him at bottom-screen (128, 133), so world (x, y) -> screen (x - 72, y - 1627).
HX, HY = 200, 1760
CAM_X, CAM_Y = HX - 128, HY - 133
MUZZLE_H = 21                       # the stylus aims at the muzzle height: touch = screen point of the row, 21 px up
EXVOTO, MONAGUILLO = 3, 5            # human-sized enemies (hit ellipse rx 15); the charger is a 60 px sprite
ENEMY_SIZE = 124                     # sizeof(Enemy) on the ARM build (short enums: type and state are 1 byte each)

RELIC = dict(SED_CENIZA=1, LANZA=2, AUTO_FE=4, LLAMA_VOTIVA=8, CILICIO=16, PROCESION=32, MARTIRIO=64,
             FLAGELADO=128, LLAGA=256, VIATICO=512)

FIELDS = {
    "seq": {"offset": 0, "type": "u32"}, "ack": {"offset": 4, "type": "u32"},
    "player_x": {"offset": 8, "type": "s16"}, "player_y": {"offset": 10, "type": "s16"},
    "weapon": {"offset": 12, "type": "u8"}, "style": {"offset": 13, "type": "u8"},
    "enemy_count": {"offset": 14, "type": "u8"}, "flags": {"offset": 15, "type": "u8"},
    "apply_seq": {"symbol": "u", "offset": 0, "type": "u32"},
    "relic_mask": {"symbol": "u", "offset": 8, "type": "u16"},
    "dv": {"symbol": "u", "offset": 18, "type": "u8"},
    "owned": {"symbol": "u", "offset": 22, "type": "u16"},
    "hp": {"symbol": "p", "offset": 0, "type": "s32"},
    "dbg": {"symbol": "a", "offset": 0, "type": "u8"},
    "lk": {"symbol": "lk", "offset": 0, "type": "u8"},        # g_laser_look (weapons.c): 0 = current laser, 1..3 = A / B / C
}
for i in range(16):
    b = 16 + 6 * i
    FIELDS[f"e{i}_type"] = {"offset": b, "type": "u8"}
    FIELDS[f"e{i}_flags"] = {"offset": b + 1, "type": "u8"}
    FIELDS[f"e{i}_x"] = {"offset": b + 2, "type": "s16"}
    FIELDS[f"e{i}_y"] = {"offset": b + 4, "type": "s16"}
for i in range(6):
    o = i * ENEMY_SIZE
    FIELDS[f"en{i}_hp"] = {"symbol": "en", "offset": o + 28, "type": "s32"}
    FIELDS[f"en{i}_burn"] = {"symbol": "en", "offset": o + 116, "type": "u8"}
    FIELDS[f"en{i}_timer"] = {"symbol": "en", "offset": o + 120, "type": "u16"}


def touch(wx, wy=HY):
    """Bottom-screen pixel that aims the muzzle at ground point (wx, wy)."""
    return {"x": wx - CAM_X, "y": wy - CAM_Y - MUZZLE_H}


def pokes(**kw):
    return [{"field": k, "value": v} for k, v in kw.items()]


def stage(vi, relics, enemies, hero_hp=None, extra=(), flags=39, hero=None, dv=None):
    """Variant switch + clean restage of the whole scene (the mailbox clears every enemy and effect)."""
    dvv = vi if dv is None else dv           # design variant (laser: always 0, the look is g_laser_look)
    p = [{"field": "relic_mask", "value": relics}, {"field": "dv", "value": dvv}, {"field": "apply_seq", "value": vi + 1}]
    s = [{"poke": p, "frames": 3}]
    hx, hy = hero if hero else (HX, HY)
    q = pokes(player_x=hx, player_y=hy, weapon=1, style=dvv, flags=flags, enemy_count=len(enemies))
    for i, (t, x, y) in enumerate(enemies):
        q += pokes(**{f"e{i}_type": t, f"e{i}_flags": 0, f"e{i}_x": x, f"e{i}_y": y})
    q.append({"field": "seq", "value": vi + 1})
    s += [{"poke": q, "frames": 1}, {"wait_until": {"field": "ack", "equals": vi + 1, "timeout_frames": 30}}, {"frames": 6}]
    post = pokes(hp=hero_hp) if hero_hp is not None else []
    post += list(extra)
    if post:
        s.append({"poke": post, "frames": 1, "state_capture": f"staged{vi}"})
    return s


def sw(vi, relics, enemies, hero_hp=None, extra=(), body=()):
    return stage(vi, relics, enemies, hero_hp, extra) + [dict(s) for s in body] + [{"release": True, "frames": 12}]


def seq(vi, name, frames, every=2, **kw):
    return {"frames": frames, "capture_sequence": f"v{vi}_{name}", "capture_every": every, **kw}


def tough(n, burn=0, layers=()):
    """Enemies that survive anything the scene does to them, optionally burning (layers per enemy)."""
    out = []
    for i in range(n):
        out += pokes(**{f"en{i}_hp": 2000})
        b = layers[i] if layers else burn
        if b:
            out += pokes(**{f"en{i}_burn": b, f"en{i}_timer": 900})
    return out


def build(el):
    steps = [{"frames": 30}]
    for vi in VARIANTS.get(el, (0, 1, 2)):
        if el == "burn":
            en = [(EXVOTO, 236, 1742), (MONAGUILLO, 262, 1760), (EXVOTO, 238, 1778)]
            body = [seq(vi, "1burn", 50)]
            steps += sw(vi, 0, en, extra=tough(3, layers=(1, 2, 4)), body=body)
        elif el == "votiva":
            en = [(EXVOTO, 234, HY), (MONAGUILLO, 258, HY), (EXVOTO, 282, HY)]
            body = [{"tap": touch(292), "frames": 4}, seq(vi, "1charge", 56)]
            steps += sw(vi, RELIC["LLAMA_VOTIVA"], en, extra=tough(3), body=body)
        elif el == "laser":
            # Charged ray looks (g_laser_look): vi 0 = the current look, 1 / 2 / 3 = A / B / C. The hero stands at x = LHX and
            # shoots east along y = HY; the east wall of the cathedral strip starts at x ~ 467 (94 px away, inside the 110 px
            # range). Lanza de Longinos makes the beam pierce the three quiet enemies in line on that row (x + 30 / 52 / 74)
            # so it reaches the wall. Rest 0.3 s, press and hold 0.8 s to charge, hold 0.8 s armed, release, 0.8 s of shot.
            en = [(EXVOTO, LHX + 30, HY), (MONAGUILLO, LHX + 52, HY), (EXVOTO, LHX + 74, HY)]
            aim = {"x": LHX + 100 - min(LHX - 128, 258), "y": LASER_AIM_Y}      # camera x clamps at 258 (world 514 wide)
            body = [{"poke": pokes(lk=vi), "frames": 1}, seq(vi, "1rest", 18),
                    {"tap": aim, "frames": 2}, seq(vi, "2charge", 40), seq(vi, "3ready", 20, every=1),
                    seq(vi, "4hold", 40), {"release": True, "frames": 1, "capture_sequence": f"v{vi}_5shot", "capture_every": 1},
                    seq(vi, "6shot", 23, every=1), seq(vi, "7fade", 30)]
            steps += stage(vi, RELIC["LANZA"], en, extra=tough(3), dv=0, hero=(LHX, HY)) + body + [{"release": True, "frames": 12}]
        elif el == "flagelado":
            en = [(EXVOTO, 160, 1760), (MONAGUILLO, 240, 1760), (EXVOTO, 176, 1778), (MONAGUILLO, 224, 1778)]
            body = [seq(vi, "1pre", 6), {"poke": pokes(dbg=2), "frames": 2, "capture_sequence": f"v{vi}_2wave", "capture_every": 1},
                    seq(vi, "3after", 40)]
            steps += sw(vi, RELIC["FLAGELADO"], en, extra=tough(4), body=body)
        elif el == "martirio":
            en = [(EXVOTO, 264, HY), (MONAGUILLO, 250, 1774), (EXVOTO, 278, 1774)]     # neighbours 14 px south: inside the blast, under the beam
            ex = tough(3)[1:]          # the target (slot 0) keeps its own hp, set right before the shot
            body = [{"tap": touch(264), "frames": 2}, seq(vi, "1charge", 22),
                    {"poke": pokes(en0_hp=100, en0_burn=3, en0_timer=900), "frames": 6, "capture_sequence": f"v{vi}_2burn", "capture_every": 2},
                    {"release": True, "frames": 2, "capture_sequence": f"v{vi}_3shot", "capture_every": 1},
                    seq(vi, "4blast", 16, every=1), seq(vi, "5after", 28)]
            steps += sw(vi, RELIC["MARTIRIO"], en, extra=ex, body=body)
        elif el == "autofe":
            # A: sparks at the impact point. B / C: the burn is consumed; they start from burn A (B) / burn B (C), forced
            # with the debug bits 64 / 128 so the fire before the shot already is the one that gets consumed.
            en = [(EXVOTO, 252, HY), (MONAGUILLO, 288, HY)]
            body = [{"tap": touch(252), "frames": 2}, seq(vi, "1charge", 26),
                    {"release": True, "frames": 1, "capture_sequence": f"v{vi}_2shot", "capture_every": 1},
                    seq(vi, "3shot", 16, every=1), seq(vi, "4after", 28)]
            steps += sw(vi, RELIC["AUTO_FE"], en, extra=tough(2, burn=4) + pokes(dbg=128 if vi == 2 else 64), body=body)
        elif el == "llaga":
            # Llaga Abierta looks (DESIGN.md 6.12.11): A floor heartbeat ring, B hero tint + blood drops, C screen vignette.
            # The hero stands still at 1 heart (the strongest state); no shot is needed, the looks run all the time.
            en = [(EXVOTO, 250, HY)]
            # Staged at 4, 3, 2 and 1 hearts so the scaling is visible (A renders like B; only B and C are shot).
            body = [seq(vi, "1hp4", 40), {"poke": pokes(hp=3), "frames": 1}, seq(vi, "2hp3", 40),
                    {"poke": pokes(hp=2), "frames": 1}, seq(vi, "3hp2", 40), {"poke": pokes(hp=1), "frames": 1}, seq(vi, "4hp1", 56)]
            steps += sw(vi, RELIC["LLAGA"], en, hero_hp=4, extra=tough(1), body=body)
        elif el == "viatico":
            # The siphon is forced with the debug hook (the real one is a 8 % / 16 % roll on a beam kill): it starts
            # 44 px to the right of the hero, at the height of a torso, and flows into the chest.
            # Real flow: a beam kill with the steal forced (dbg bit 16). The victim (1 hp) hangs inert for ~0.3 s while the
            # thread / wisp leaves its body, then dies as usual.
            en = [(EXVOTO, 252, HY)]
            body = [{"tap": touch(252), "frames": 2}, seq(vi, "1charge", 26),
                    {"release": True, "frames": 1, "capture_sequence": f"v{vi}_2shot", "capture_every": 1},
                    seq(vi, "3siphon", 40, every=1)]
            steps += sw(vi, RELIC["VIATICO"], en, hero_hp=3, extra=pokes(en0_hp=1, dbg=16), body=body)
    return {
        "name": f"abc_{el}", "suite": False, "evidence_only": True,
        "description": f"Design variants A/B/C of '{el}' on a staged scene (cathedral-sandbox ROM; see tools/abc_scenes.py).",
        "state": {"symbols": {"sb": "g_sandbox", "u": "g_upg_debug", "p": "g_player_state", "a": "g_abc_debug", "en": "g_enemies", "lk": "g_laser_look"},
                  "default_symbol": "sb", "fields": FIELDS},
        "steps": steps,
    }


# Variants shot per element (the others were dropped in DESIGN.md 6.12.12).
LHX, LASER_AIM_Y = 370, 78           # laser scene: hero x; stylus row = muzzle row on the lower screen (hero feet at y 99, chest 21 up)
VARIANTS = {"autofe": (0, 2), "burn": (0, 1), "llaga": (1, 2), "viatico": (0, 2), "laser": (0, 1, 2, 3)}
ELEMENTS = ["burn", "votiva", "flagelado", "martirio", "autofe", "llaga", "viatico", "laser"]

if __name__ == "__main__":
    for el in ELEMENTS:
        (ROOT / "scenarios" / f"abc_{el}.json").write_text(json.dumps(build(el), indent=1) + "\n", newline="")
        print("wrote", f"scenarios/abc_{el}.json")
