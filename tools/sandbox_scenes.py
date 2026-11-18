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
# Sniper charge aura look in flag bits 3-4 (include/sandbox.h, g_aura_style): 0 = L (flames), 1 = G, 2 = E, 3 = H.
AURA_LOOKS = ("L", "G", "E", "H")
FLAG_AURA_SHIFT = 3
CHARGER, SHOOTER, EXVOTO = 1, 2, 3          # SANDBOX_ENEMY_* (include/sandbox.h)
WEAPON = {"shotgun": 0, "sniper": 1, "grenade": 2}
STYLE = "ABC"

WORLD_W, WORLD_H = 768, 768
SCREEN_W, SCREEN_H = 256, 192
# Hero facing east (g_character_muzzle[CHAR_HERO][DIR_EAST][0] = {2, 0, 21}): the muzzle sits on the chest,
# 2 px from the feet (gx) and 21 px above the ground. Shots fly at that height, so a stylus touch is read as a
# point at MUZZLE_H: to aim the muzzle at ground point (x, y), touch (x, y + MUZZLE_DY) shifted up MUZZLE_H.
MUZZLE_DY = 0
MUZZLE_H = 21


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


def check_beam(player, aim_x, enemies):
    """Rule 5 guard for the sniper: the beam leaves the muzzle (over the feet, facing east) as a horizontal line
    at MUZZLE_H along the touched row. Every enemy must stand on that row, east of the muzzle and not past the
    aim point, so the beam really crosses it. Raises if a scene would aim at open floor."""
    muzzle_x, row = player[0], player[1] + MUZZLE_DY
    for _kind, x, y in enemies:
        if y != row or not muzzle_x < x:
            raise ValueError(f"enemy at ({x},{y}) is off the beam (row y={row}, east of muzzle x={muzzle_x})")
    return enemies


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
    # more than 190 px of floor shows to the east). The muzzle is over the feet (gx 0).
    player = (60, 724)
    # Muzzle at x 60: charger 60 px away (full blast), shooter 110 px (falloff), charger 165 px (weak).
    enemies = [(CHARGER, 120, 724), (SHOOTER, 170, 716), (CHARGER, 225, 730)]
    steps = setup_steps(player, "shotgun", style, enemies)
    steps += [
        {"tap": touch_at(player, 120, 724 + MUZZLE_DY, MUZZLE_H), "frames": 44, "capture_sequence": "shot", "capture_every": 1},
        {"release": True, "frames": 30, "capture": "after"},
    ]
    sc = scenario(f"sandbox_shotgun_{STYLE[style]}", steps)
    sc["assertions"]["screen_changes"][0]["to"] = "after"
    return sc


# Sniper hit sweep (fix/sniper-hit-side). One parked Exvoto (EXVOTO) facing south (sandbox ordinal 0 = DIR_SOUTH,
# 100 hp, one sniper hit (150) kills it) at ENEMY, the hero 70 px to its west or east. The stylus touches the
# enemy's column at SWEEP_UP px above its feet, so the beam crosses the sprite at that screen height
# (the touch is read at muzzle height). Ground-plane hit test (old): only up 13..23 hit; body volume
# (new, include/hitvolume.h): every row of the sprite, up -4..32.
ENEMY = (110, 724)
SWEEP_UP = (-14, 0, 4, 8, 12, 16, 20, 24, 28, 32, 46)
HIT_ROWS = (4, 8, 12, 16, 20, 24, 28)          # clearly on the sprite: must kill
MISS_ROWS = (-14, 46)                          # clearly off the sprite: must not hurt
ENEMY_HP_OFFSET = 28                           # offsetof(Enemy, hp) in g_enemies[0]
ENEMY_FULL_HP = 100                            # Exvoto hp (weapons.c: the sniper hit, 150, kills it)


def sniper_sweep_scene(side):
    player = {"west": (40, 724), "east": (180, 724)}[side]
    steps, assertions = [], []
    for n, up in enumerate(SWEEP_UP, start=1):
        steps += setup_steps(player, "sniper", 0, [(EXVOTO, *ENEMY)], seq=n, boot=30 if n == 1 else 0)
        steps += [
            {"tap": touch_at(player, ENEMY[0], ENEMY[1], up), "frames": 34},
            {"release": True, "frames": 12, "state_capture": f"up{up}"},
            {"frames": 50},                    # sniper cooldown before the next staging
        ]
        if up in HIT_ROWS:
            assertions.append({"at": f"up{up}", "field": "e0_hp", "max_value": 0})
        elif up in MISS_ROWS:
            assertions.append({"at": f"up{up}", "field": "e0_hp", "min_value": ENEMY_FULL_HP})
    fields = {k: dict(v) for k, v in FIELDS.items()}
    fields["e0_hp"] = {"symbol": "enemies", "offset": ENEMY_HP_OFFSET, "type": "s32"}
    return {
        "name": f"sniper_hit_sweep_{side}",
        "state": {"symbols": {"sb": "g_sandbox", "enemies": "g_enemies"}, "default_symbol": "sb", "fields": fields},
        "steps": steps,
        "assertions": {"state_changes": assertions},
    }


def sniper_fire_scene(look=None):
    """Sniper fire (DESIGN.md 6.10: fuego, flames aura): the touch is held 70 frames (every frame captured) so
    the GIF shows the whole charge, the READY state and the hold. The stylus is then released and the shot is
    captured frame by frame after the release. Same stage as the sniper sweep: three enemies on the beam row,
    all on screen, so the beam must pierce all of them. READY comes after aim_min_frames (24) aim frames.
    With `look` ("L", "G", "E" or "H") the scene is sandbox_sniper_fire_aura_<look>: the same stage with the aura
    look set in the flag bits; without it the flags stay as before (look L)."""
    player = (40, 724)
    enemies = check_beam(player, 110, [(SHOOTER, 110, 724), (CHARGER, 170, 724), (SHOOTER, 230, 724)])
    aura = AURA_LOOKS.index(look) if look else 0
    flags = FLAG_CLEAR | FLAG_FREEZE_AI | FLAG_GOD | (aura << FLAG_AURA_SHIFT)
    steps = setup_steps(player, "sniper", 2, enemies, flags=flags)     # the sniper always draws fuego (C)
    steps += [
        {"tap": touch_at(player, 110, 724 + MUZZLE_DY, MUZZLE_H), "frames": 70, "capture_sequence": "charge", "capture_every": 1},
        {"frames": 1, "capture": "aim"},
        {"release": True, "frames": 14, "capture_sequence": "shot", "capture_every": 1},
        {"frames": 30, "capture": "after"},
    ]
    return scenario(f"sandbox_sniper_fire_aura_{look}" if look else "sandbox_sniper_fire", steps)


# ---- Exvotos praying in front of a real devout piece (DESIGN.md 6.10, feat/exvoto) ---------------------------
# Needs the cathedral-sandbox ROM (CATHEDRAL_AI=1: the AI runs). NOTE: the relicario this once targeted (window px 248,682) no longer exists after the props-v2 kit; its stable seed (0xC0DE1234) put the relicario of the first window at
# window px (248, 682) with a footprint of half-extent 16 x 6 (dumped from strip_devout_in_band() on the host).
# The Exvotos stand where horde.c seat_exvoto() would seat them (1 cell of 4 px outside the footprint, south arc
# first, then alternating sides) and face the piece with the same 8-direction quantisation the AI uses.
RELICARIO = (248, 682, 16, 6)                  # centre x, centre y, half width, half height (window px)
STATE = {"CHASE": 0, "DEAD": 13, "PRAY": 15, "RISE": 16}
FLAG_PRAY, FLAG_KNEEL, FLAG_DIR_SHIFT = 2, 4, 3
CHAR = {"walk": 3, "pray_stand": 4, "pray_kneel": 5, "stand_up": 6}
ENEMY_SIZE = 88                                # sizeof(Enemy), asserted in source/main.c
# offsetof(Enemy, ...) in g_enemies[i]
ENEMY_FIELDS = {"x": (0, "s32"), "y": (4, "s32"), "dir": (8, "s32"), "frame": (12, "s32"), "char": (20, "s32"),
                "active": (24, "s32"), "hp": (28, "s32"), "state": (41, "u8")}
_RING_COS = [256, 251, 237, 213, 181, 142, 98, 50, 0, -50, -98, -142, -181, -213, -237, -251,
             -256, -251, -237, -213, -181, -142, -98, -50, 0, 50, 98, 142, 181, 213, 237, 251]
_RING_SIN = [0, 50, 98, 142, 181, 213, 237, 251, 256, 251, 237, 213, 181, 142, 98, 50,
             0, -50, -98, -142, -181, -213, -237, -251, -256, -251, -237, -213, -181, -142, -98, -50]


def dir_from_vector(dx, dy):
    """enemy_ai.c dir_from_vector(): 0 S, 1 SW, 2 W, 3 NW, 4 N, 5 NE, 6 E, 7 SE."""
    ax, ay = abs(dx), abs(dy)
    sdx, sdy = dx, dy
    if ax * 2 < ay:
        sdx = 0
    elif ay * 2 < ax:
        sdy = 0
    else:
        sdx, sdy = (-1 if dx < 0 else 1), (-1 if dy < 0 else 1)
    if sdx == 0:
        return 0 if sdy >= 0 else 4
    if sdy == 0:
        return 2 if sdx < 0 else 6
    if sdx < 0:
        return 1 if sdy > 0 else 3
    return 5 if sdy < 0 else 7


def seat(piece, step, extra=0):
    """Position of one praying Exvoto on ring step `step` (0..31, 8 = due south) of `piece`, and its facing. `extra` is
    the optional second collision cell (0 or 4 px). The body circle (radius 6) first fits 7 px beside the footprint and
    4 screen rows in front of it (HORDE_EXVOTO_SIDE_PX / FRONT_PX in horde.h)."""
    cx, cy, hw, hh = piece
    x = cx + ((hw + 7 + extra) * _RING_COS[step] >> 8)
    y = cy + ((hh + 4 + extra // 2) * _RING_SIN[step] >> 8)
    if _RING_SIN[step] > 0 and y < cy + hh + 4:      # the front of the piece is a straight row (horde.c)
        y = cy + hh + 4
    return x, y, dir_from_vector(cx - x, cy - y)


def exvoto_pray_scene():
    """Three Exvotos in a south arc in front of the relicario (one standing, two kneeling: no chance involved) and
    a fourth on its north side, 34 ground px from the first. The hero walks north from the south hall: the first
    Exvoto wakes when he is within 96 ground px; the north one is out of his reach and wakes only by the chain
    (48 px). The kneeling ones rise (still), the standing one walks at once; then a sniper shot up the arc kills
    the ones on the line and they melt into a puddle."""
    rel = RELICARIO
    spots = [(seat(rel, 8), 0), (seat(rel, 12), 1), (seat(rel, 4), 1), (seat(rel, 24), 1)]   # ((x, y, dir), kneel)
    enemies = [(x, y, d, kneel) for (x, y, d), kneel in spots]
    # Rule 5 guard: every Exvoto must stand just outside the footprint and look at the piece centre.
    for x, y, d, _ in enemies:
        assert abs(x - rel[0]) <= rel[2] + 18 and abs(y - rel[1]) <= rel[3] + 8, (x, y)
        assert d == dir_from_vector(rel[0] - x, rel[1] - y)
    hero = (250, 800)
    pokes = [{"field": "player_x", "value": hero[0]}, {"field": "player_y", "value": hero[1]},
             {"field": "weapon", "value": WEAPON["sniper"]}, {"field": "style", "value": 0},
             {"field": "flags", "value": FLAG_CLEAR | FLAG_GOD}, {"field": "enemy_count", "value": len(enemies)}]
    for i, (x, y, d, kneel) in enumerate(enemies):
        pokes += [{"field": f"e{i}_type", "value": EXVOTO},
                  {"field": f"e{i}_flags", "value": FLAG_PRAY | (FLAG_KNEEL if kneel else 0) | (d << FLAG_DIR_SHIFT)},
                  {"field": f"e{i}_x", "value": x}, {"field": f"e{i}_y", "value": y}]
    pokes.append({"field": "seq", "value": 1})
    fields = {k: dict(v) for k, v in FIELDS.items()}
    for i in range(len(enemies)):
        for name, (off, typ) in ENEMY_FIELDS.items():
            fields[f"en{i}_{name}"] = {"symbol": "enemies", "offset": i * ENEMY_SIZE + off, "type": typ}
    steps = [
        {"frames": 30},
        {"poke": pokes, "frames": 1},
        {"wait_until": {"field": "ack", "equals": 1, "timeout_frames": 30}},
        {"frames": 12, "capture": "01_rezando", "state_capture": "praying"},
        {"frames": 96, "capture_sequence": "a_reza", "capture_every": 4, "state_capture": "praying_later"},
        {"frames": 1, "capture": "02_rezando_quietos"},
        {"button_down": "UP", "frames": 100, "capture_sequence": "b_acerca", "capture_every": 6},
        {"wait_until": {"field": "en1_state", "equals": STATE["RISE"], "timeout_frames": 400},
         "capture": "03_despiertan", "state_capture": "woken"},
        {"button_up": "UP", "frames": 1},
        {"frames": 60, "capture_sequence": "c_levanta", "capture_every": 2, "state_capture": "rising"},
        {"wait_until": {"field": "en1_state", "equals": STATE["CHASE"], "timeout_frames": 120},
         "capture": "05_andan", "state_capture": "walking"},
        {"frames": 45, "capture_sequence": "d_andan", "capture_every": 3, "state_capture": "advancing"},
        {"frames": 1, "capture": "06_avanzan"},
    ]
    # Sniper up the arc: the touch (read at muzzle height) is straight above the hero, so the beam runs north along his
    # column and crosses the Exvotos that walk down it.
    steps += [{"tap": {"x": 128, "y": 20}, "frames": 40, "capture": "07_apunta"},
              {"release": True, "frames": 6, "capture_sequence": "e_disparo", "capture_every": 1},
              {"frames": 100, "capture_sequence": "f_charco", "capture_every": 2}]
    return {
        "name": "exvoto_reza_despierta_derrite",
        "description": ("ROM cathedral-playground (seed 0xC0DE1234). Three Exvotos pray in a south arc in front of the real relicario "
                        f"(window px {rel[0]},{rel[1]}, footprint half-extent {rel[2]}x{rel[3]}), facing it; a fourth prays on its north side. "
                        "The hero (god mode) walks north: the Exvotos stay still until he is within 96 ground px, the north one wakes "
                        "only by the 48 px chain, the kneeling ones rise (stand_up clip), then everybody walks; a sniper shot kills the "
                        "ones on the line and they melt into a wax puddle."),
        "state": {"symbols": {"sb": "g_sandbox", "enemies": "g_enemies"}, "default_symbol": "sb", "fields": fields},
        "steps": steps,
        "assertions": {"state_changes": [
            {"at": "praying", "field": "en0_state", "equals": STATE["PRAY"]},
            {"at": "praying", "field": "en1_state", "equals": STATE["PRAY"]},
            {"at": "praying", "field": "en2_state", "equals": STATE["PRAY"]},
            {"at": "praying", "field": "en3_state", "equals": STATE["PRAY"]},
            {"at": "praying", "field": "en0_char", "equals": CHAR["pray_stand"]},
            {"at": "praying", "field": "en1_char", "equals": CHAR["pray_kneel"]},
            {"from": "praying", "to": "praying_later", "field": "en0_x", "max_abs_delta": 0},
            {"from": "praying", "to": "praying_later", "field": "en1_y", "max_abs_delta": 0},
            {"at": "woken", "field": "en3_state", "equals": STATE["RISE"]},
            {"at": "woken", "field": "en1_state", "equals": STATE["RISE"]},
            {"at": "woken", "field": "en0_char", "equals": CHAR["walk"]},
            {"at": "woken", "field": "en1_char", "equals": CHAR["stand_up"]},
            {"from": "woken", "to": "rising", "field": "en1_x", "max_abs_delta": 0},
            {"at": "walking", "field": "en1_char", "equals": CHAR["walk"]},
            {"at": "walking", "field": "en1_state", "equals": STATE["CHASE"]},
            {"from": "walking", "to": "advancing", "field": "en0_y", "min_delta": 1},
        ], "screen_changes": [{"from": "02_rezando_quietos", "to": "03_despiertan", "min_changed_pixels": 50},
                              {"from": "06_avanzan", "to": "07_apunta", "min_changed_pixels": 20}]},
    }


# Walk cycles over open floor (no enemies, god mode): start point and key per facing. Each run is 40 frames,
# long enough for two full 8-frame cycles at ticksPerFrame 2, and far from the arena edges.
HERO_WALKS = {
    "east": ((40, 724), "RIGHT"),
    "west": ((180, 724), "LEFT"),
    "south": ((120, 400), "DOWN"),
    "north": ((120, 400), "UP"),
}


def hero_walk_scene(direction="east"):
    """The hero walking over open floor in one direction (no enemies, god mode): the walk animation."""
    player, key = HERO_WALKS[direction]
    steps = setup_steps(player, "sniper", 0, [], flags=FLAG_CLEAR | FLAG_FREEZE_AI | FLAG_GOD)
    steps += [
        {"button_down": key, "frames": 40, "capture_sequence": "walk", "capture_every": 1},
        {"button_up": key, "frames": 4},
    ]
    sc = scenario(f"sandbox_hero_walk_{direction}", steps)
    sc["assertions"] = {}   # no aim capture here: the GIF is the check
    return sc


def main():
    out = ROOT / "scenarios"
    out.mkdir(exist_ok=True)
    scenes = [build(style) for style in range(3) for build in (grenade_scene, shotgun_scene)]
    scenes.append(sniper_fire_scene())
    scenes += [sniper_fire_scene(look) for look in AURA_LOOKS]
    scenes += [sniper_sweep_scene(side) for side in ("west", "east")]
    scenes += [hero_walk_scene(d) for d in HERO_WALKS]
    scenes.append(exvoto_pray_scene())
    for sc in scenes:
        if sc["name"].startswith(("sandbox_grenade_", "sandbox_shotgun_", "sandbox_sniper_fire")):
            sc["suite"] = False                       # variantes de arte y capturas: fuera de la bateria
        if sc["name"].startswith("sandbox_hero_walk_"):
            sc["suite"] = False
            sc["evidence_only"] = True                # solo capturas, sin aserciones
        path = out / f"{sc['name']}.json"
        path.write_text(json.dumps(sc, indent=2) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
