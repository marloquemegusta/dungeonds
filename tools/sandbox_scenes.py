#!/usr/bin/env python3
"""Generates the weapon-showcase scenarios that stage their scene through the sandbox mailbox.

The sandbox (include/sandbox.h, build variant "sandbox") lets a scenario place the player, pick
the weapon and effects style and spawn parked enemies at exact positions. This tool turns a
compact scene description into scenarios/sandbox_<weapon>_<style>.json.

Run:  python tools/sandbox_scenes.py
Then: build with -Variant sandbox and run the scenarios against that ROM (walkthroughs/weapon-previews).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Mailbox layout (include/sandbox.h): the offsets are asserted in source/sandbox.c.
MAX_ENEMIES = 16
FIELDS = {
    "seq": {"offset": 0, "type": "u32"},
    "ack": {"offset": 4, "type": "u32"},
    "player_x": {"offset": 8, "type": "s16"},
    "player_y": {"offset": 10, "type": "s16"},
    "weapon": {"offset": 12, "type": "u8"},
    "style": {"offset": 13, "type": "u8"},
    "enemy_count": {"offset": 14, "type": "u8"},
    "flags": {"offset": 15, "type": "u8"},
}
for _i in range(MAX_ENEMIES):
    _base = 16 + 6 * _i
    FIELDS[f"e{_i}_type"] = {"offset": _base, "type": "u8"}
    FIELDS[f"e{_i}_flags"] = {"offset": _base + 1, "type": "u8"}
    FIELDS[f"e{_i}_x"] = {"offset": _base + 2, "type": "s16"}
    FIELDS[f"e{_i}_y"] = {"offset": _base + 4, "type": "s16"}

FLAG_CLEAR, FLAG_FREEZE_AI, FLAG_GOD = 1, 2, 4
# Sniper aura look (g_aura_style) lives in flag bits 3-4 (include/sandbox.h): K = 0 (default), C = 1, V = 2.
AURA_SHIFT = 3
AURA_CODE = {"K": 0, "C": 1, "V": 2}
CHARGER, SHOOTER = 1, 2
WEAPON = {"shotgun": 0, "sniper": 1, "grenade": 2}
STYLE = "ABC"

WORLD_W, WORLD_H = 768, 768
SCREEN_W, SCREEN_H = 256, 192
# Hero facing east (g_character_muzzle[CHAR_HERO][DIR_EAST][0]): the muzzle is 16 px ahead of and 1 px below
# the feet and 18 px above the ground. Shots fly at that height, so a stylus touch is read as a point at
# MUZZLE_H: to aim the muzzle straight at ground point (x, y), touch (x, y + MUZZLE_DY) shifted up MUZZLE_H.
MUZZLE_DY = 1
MUZZLE_H = 18


def camera(player_x, player_y):
    """Mirror of update_camera() in source/main.c for the lower screen."""
    x = min(max(player_x - SCREEN_W // 2, 0), WORLD_W - SCREEN_W)
    y = min(max(player_y - SCREEN_H // 2, SCREEN_H // 2), WORLD_H - SCREEN_H // 2)
    return x, y


def touch_at(player, wx, wy, height=0):
    """Lower-screen pixel that touches world point (wx, wy), `height` px above the ground."""
    cx, cy = camera(*player)
    sx, sy = wx - cx, wy - cy - height
    if not (0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H):
        raise ValueError(f"touch ({sx},{sy}) for world ({wx},{wy}) is outside the lower screen")
    return {"x": sx, "y": sy}


def setup_steps(player, weapon, style, enemies, flags=FLAG_CLEAR | FLAG_FREEZE_AI | FLAG_GOD, seq=1, boot=30):
    """One `poke` list (single frame), ending with seq, then wait for the game's ack."""
    pokes = [
        {"field": "player_x", "value": player[0]},
        {"field": "player_y", "value": player[1]},
        {"field": "weapon", "value": WEAPON[weapon]},
        {"field": "style", "value": style},
        {"field": "flags", "value": flags},
        {"field": "enemy_count", "value": len(enemies)},
    ]
    for i, (kind, x, y) in enumerate(enemies):
        pokes += [{"field": f"e{i}_type", "value": kind},
                  {"field": f"e{i}_flags", "value": 0},
                  {"field": f"e{i}_x", "value": x},
                  {"field": f"e{i}_y", "value": y}]
    pokes.append({"field": "seq", "value": seq})      # last: the game applies the request next frame
    steps = [
        # Let the game finish booting first: crt0 zeroes .bss, which would erase pokes made at frame 0.
        {"frames": boot},
        {"poke": pokes, "frames": 1},
        {"wait_until": {"field": "ack", "equals": seq, "timeout_frames": 30}},
        {"frames": 20, "capture": f"00_staged_{seq}" if seq > 1 else "00_staged"},
    ]
    return steps if boot else steps[1:]


def scenario(name, steps):
    return {
        "name": name,
        "state": {
            "symbols": {"sb": "g_sandbox"},
            "default_symbol": "sb",
            "fields": {k: dict(v) for k, v in FIELDS.items()},
        },
        "steps": steps,
        "assertions": {"screen_changes": [{"from": "00_staged", "to": "aim", "min_changed_pixels": 20}]},
    }


def grenade_scene(style):
    player = (360, 724)
    centre = (420, 700)
    # Offsets from the blast centre; ground distance is sqrt(dx^2 + (2*dy)^2), radius 56.
    # (0,0) kills a charger; (22,4) kills a shooter; (-30,-10) hurts a charger (d=36) but it survives;
    # (40,12) kills a shooter near the rim (d=46); (75,0) stands outside the radius (75 > 56).
    layout = [(CHARGER, 0, 0), (SHOOTER, 22, 4), (CHARGER, -30, -10), (SHOOTER, 40, 12), (CHARGER, 75, 0)]
    enemies = [(k, centre[0] + dx, centre[1] + dy) for k, dx, dy in layout]
    steps = setup_steps(player, "grenade", style, enemies)
    steps += [
        {"tap": touch_at(player, *centre), "frames": 10, "capture": "aim"},
        # One capture per game frame (60 fps GIFs): the whole flight and fuse, the blast, then the smoke.
        {"release": True, "frames": 86, "capture_sequence": "fuse", "capture_every": 1},
        {"frames": 40, "capture_sequence": "blast", "capture_every": 1},
        {"frames": 60, "capture_sequence": "smoke", "capture_every": 2},
    ]
    return scenario(f"sandbox_grenade_{STYLE[style]}", steps)


def shotgun_scene(style):
    # The player stands near the west wall (x < 128 clamps the camera, so the hero is off-centre and
    # more than 190 px of floor shows to the east). The muzzle is 16 px ahead of the feet.
    player = (60, 724)
    # Charger 60 px from the muzzle (full blast), shooter ~100 px (falloff), charger ~150 px (weak).
    enemies = [(CHARGER, 120, 724), (SHOOTER, 170, 716), (CHARGER, 225, 730)]
    steps = setup_steps(player, "shotgun", style, enemies)
    steps += [
        {"tap": touch_at(player, 120, 724 + MUZZLE_DY, MUZZLE_H), "frames": 44, "capture_sequence": "shot", "capture_every": 1},
        {"release": True, "frames": 30, "capture": "after"},
    ]
    sc = scenario(f"sandbox_shotgun_{STYLE[style]}", steps)
    sc["assertions"]["screen_changes"][0]["to"] = "after"
    return sc


def sniper_scene(style):
    player = (40, 724)
    # Three enemies on one line east of the player, all on screen: the beam must pierce all of them.
    enemies = [(SHOOTER, 110, 724), (CHARGER, 170, 724), (SHOOTER, 230, 724)]
    steps = setup_steps(player, "sniper", style, enemies)
    steps += [
        {"tap": touch_at(player, 110, 724 + MUZZLE_DY, MUZZLE_H), "frames": 40, "capture_sequence": "aimline", "capture_every": 2},
        {"frames": 1, "capture": "aim"},
        {"release": True, "frames": 44, "capture_sequence": "shot", "capture_every": 1},
        {"frames": 30, "capture": "after"},
    ]
    return scenario(f"sandbox_sniper_{STYLE[style]}", steps)


def sniper_collimation_scene(style):
    """Sniper laser collimation (DESIGN.md 4.9): same stage as sniper_scene, one capture per game frame.

    The touch is held 50 frames (charge, then READY hold: aim_min_frames is 24), then released for the shot.
    """
    player = (40, 724)
    enemies = [(SHOOTER, 110, 724), (CHARGER, 170, 724), (SHOOTER, 230, 724)]
    steps = setup_steps(player, "sniper", style, enemies)
    steps += [
        {"tap": touch_at(player, 110, 724 + MUZZLE_DY, MUZZLE_H), "frames": 50, "capture_sequence": "charge", "capture_every": 1},
        {"frames": 1, "capture": "aim"},
        {"release": True, "frames": 14, "capture_sequence": "shot", "capture_every": 1},
        {"frames": 30, "capture": "after"},
    ]
    return scenario(f"sandbox_sniper_collim_{STYLE[style]}", steps)


# Sniper hit sweep (fix/sniper-hit-side). One parked shooter facing south (sandbox ordinal 0 = DIR_SOUTH,
# 20 hp, one sniper hit kills it) at ENEMY, the hero 70 px to its west or east. The stylus touches the
# enemy's column at SWEEP_UP px above its feet, so the beam crosses the sprite at that screen height
# (the touch is read at muzzle height). Ground-plane hit test (old): only up 13..23 hit; body volume
# (new, include/hitvolume.h): every row of the sprite, up -4..32.
ENEMY = (110, 724)
SWEEP_UP = (-14, 0, 4, 8, 12, 16, 20, 24, 28, 32, 46)
HIT_ROWS = (4, 8, 12, 16, 20, 24, 28)          # clearly on the sprite: must kill
MISS_ROWS = (-14, 46)                          # clearly off the sprite: must not hurt
ENEMY_HP_OFFSET = 28                           # offsetof(Enemy, hp) in g_enemies[0]


def sniper_sweep_scene(side):
    player = {"west": (40, 724), "east": (180, 724)}[side]
    steps, assertions = [], []
    for n, up in enumerate(SWEEP_UP, start=1):
        steps += setup_steps(player, "sniper", 0, [(SHOOTER, *ENEMY)], seq=n, boot=30 if n == 1 else 0)
        steps += [
            {"tap": touch_at(player, ENEMY[0], ENEMY[1], up), "frames": 34},
            {"release": True, "frames": 12, "state_capture": f"up{up}"},
            {"frames": 50},                    # sniper cooldown before the next staging
        ]
        if up in HIT_ROWS:
            assertions.append({"at": f"up{up}", "field": "e0_hp", "max_value": 0})
        elif up in MISS_ROWS:
            assertions.append({"at": f"up{up}", "field": "e0_hp", "min_value": 20})
    fields = {k: dict(v) for k, v in FIELDS.items()}
    fields["e0_hp"] = {"symbol": "enemies", "offset": ENEMY_HP_OFFSET, "type": "s32"}
    return {
        "name": f"sniper_hit_sweep_{side}",
        "state": {"symbols": {"sb": "g_sandbox", "enemies": "g_enemies"}, "default_symbol": "sb", "fields": fields},
        "steps": steps,
        "assertions": {"state_changes": assertions},
    }


def sniper_aura_scene(look):
    """Sniper charge aura look K (lightning rays, default), C (bolt crown) or V (vertical sparks).

    Same stage as sniper_scene, but the touch is held ~70 frames (every frame captured) so the GIF shows
    the whole charge, the READY state and the hold, then the shot.
    """
    player = (40, 724)
    enemies = [(SHOOTER, 110, 724), (CHARGER, 170, 724), (SHOOTER, 230, 724)]
    flags = FLAG_CLEAR | FLAG_FREEZE_AI | FLAG_GOD | (AURA_CODE[look] << AURA_SHIFT)
    steps = setup_steps(player, "sniper", 0, enemies, flags=flags)
    steps += [
        {"tap": touch_at(player, 110, 724 + MUZZLE_DY, MUZZLE_H), "frames": 70, "capture_sequence": "charge", "capture_every": 1},
        {"frames": 1, "capture": "aim"},
        {"release": True, "frames": 14, "capture_sequence": "shot", "capture_every": 1},
        {"frames": 30, "capture": "after"},
    ]
    return scenario(f"sandbox_sniper_aura_{look}", steps)


def main():
    out = ROOT / "scenarios"
    out.mkdir(exist_ok=True)
    builds = [(style, build) for style in range(3) for build in (grenade_scene, shotgun_scene, sniper_scene)]
    builds += [(look, sniper_aura_scene) for look in ("K", "C", "V")]
    builds += [(style, sniper_collimation_scene) for style in range(3)]
    builds += [(side, sniper_sweep_scene) for side in ("west", "east")]
    for arg, build in builds:
        sc = build(arg)
        path = out / f"{sc['name']}.json"
        path.write_text(json.dumps(sc, indent=2) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
