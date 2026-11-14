#!/usr/bin/env python3
"""Generates the headless scenarios of the Ojo del Tribunal collimated gaze (DESIGN.md 6.10 "Mirada colimada").

They stage their scene through the sandbox mailbox (build variant "sandbox", see tools/sandbox_scenes.py) and
read the player (g_player_state, g_nav_state) and the Ojo (g_enemies[0]) by symbol.

Rule 5 (AGENTS.md): before writing anything this tool replays the game's own line-of-sight test
(source/los.c, Bresenham over the 4 px collision cells of source/arena_dungeon_01.c) on the staged points and
refuses to generate a scenario whose geometry does not do what its name says:
  * open-field scenarios need a clear line between the Ojo and the player;
  * column scenarios need the line to be blocked (or clear where the player starts and blocked where it ends),
    with the blocking cells really inside the pillar x352-383, y520-535;
  * the sniper kill needs the Ojo on the beam row, east of the muzzle.

Run:  python tools/ojo_scenes.py
Then: build with -Variant sandbox and run the scenarios against that ROM.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox_scenes as sb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

OJO_TYPE = sb.SHOOTER                 # the Ojo is the shooter type (SANDBOX_ENEMY_SHOOTER = 2)
ST_TRACK, ST_LOCK, ST_SENTENCE, ST_COOLDOWN = 7, 8, 9, 10          # ENEMY_STATE_* (include/gameplay.h)
TRACK_FRAMES, LOCK_FRAMES, SIGHT_RANGE = 40, 20, 140               # OJO_* (include/gameplay.h)
PILLAR = (352, 383, 520, 535)         # x0, x1, y0, y1 of the pillar in the collision grid (world px)
ENEMY_STRIDE = 116                   # sizeof(Enemy), asserted in source/main.c
ST_DORMANT = 12
HERO_VY_PER_FRAME = 163 / 256         # 326 8.8 speed halved on the 2:1 ground (source/main.c GROUND_Y_SHIFT)

# ---------------------------------------------------------------------------
# The game's collision grid and line of sight, mirrored
# ---------------------------------------------------------------------------
_arena = (ROOT / "source" / "arena_dungeon_01.c").read_text(encoding="utf-8")
_bytes = [int(x, 0) for x in re.findall(r"0x[0-9a-fA-F]+|\d+", re.search(r"s_collision\[9216\] = \{(.*?)\};", _arena, re.S).group(1))]
CW = CH = 192


def cell(cx, cy):
    if not (0 <= cx < CW and 0 <= cy < CH):
        return 3
    i = cy * CW + cx
    return (_bytes[i >> 2] >> ((i & 3) * 2)) & 3


def los(x0, y0, x1, y1):
    """source/los.c: returns (clear, first blocking cell or None)."""
    c0x, c0y, c1x, c1y = x0 // 4, y0 // 4, x1 // 4, y1 // 4
    adx, ady = c1x - c0x, c1y - c0y
    ax, ay = abs(adx), abs(ady)
    sx, sy = (-1 if adx < 0 else 1), (-1 if ady < 0 else 1)
    err = (ax if ax > ay else -ay) // 2
    x, y = c0x, c0y
    while True:
        if x == c1x and y == c1y:
            return True, None
        if cell(x, y) == 3:
            return False, (x * 4, y * 4)
        e2 = err
        if e2 > -ax:
            err -= ay
            x += sx
        if e2 < ay:
            err += ax
            y += sy


def ground_dist(a, b):
    return math.hypot(b[0] - a[0], 2 * (b[1] - a[1]))


def inside_pillar(p):
    return PILLAR[0] <= p[0] <= PILLAR[1] and PILLAR[2] <= p[1] <= PILLAR[3]


def require_clear(ojo, hero, what):
    ok, blocked = los(*ojo, *hero)
    if not ok:
        raise ValueError(f"{what}: the line {ojo} -> {hero} is blocked at {blocked}")
    d = ground_dist(ojo, hero)
    if d > SIGHT_RANGE:
        raise ValueError(f"{what}: {d:.0f} ground px is beyond the Ojo's sight range {SIGHT_RANGE}")


def require_blocked_by_pillar(ojo, hero, what):
    ok, blocked = los(*ojo, *hero)
    if ok:
        raise ValueError(f"{what}: the line {ojo} -> {hero} is clear, the pillar is not in between")
    if not inside_pillar(blocked):
        raise ValueError(f"{what}: the line {ojo} -> {hero} is blocked at {blocked}, which is not the pillar {PILLAR}")


# ---------------------------------------------------------------------------
# Scenario skeleton
# ---------------------------------------------------------------------------
def fields():
    f = {k: dict(v) for k, v in sb.FIELDS.items()}
    f.update({
        "en0_x": {"symbol": "enemies", "offset": 0, "type": "s32"},
        "en0_y": {"symbol": "enemies", "offset": 4, "type": "s32"},
        "en0_active": {"symbol": "enemies", "offset": 24, "type": "s32"},
        "en0_hp": {"symbol": "enemies", "offset": 28, "type": "s32"},
        "en0_type": {"symbol": "enemies", "offset": 40, "type": "u8"},
        "en0_state": {"symbol": "enemies", "offset": 41, "type": "u8"},
        "en1_state": {"symbol": "enemies", "offset": ENEMY_STRIDE + 41, "type": "u8"},
        "en1_y": {"symbol": "enemies", "offset": ENEMY_STRIDE + 4, "type": "s32"},
        "en0_timer": {"symbol": "enemies", "offset": 44, "type": "s32"},
        "player_hp": {"symbol": "player", "offset": 0, "type": "s32"},
        "player_iframes": {"symbol": "player", "offset": 16, "type": "s32"},
        "nav_y": {"symbol": "nav", "offset": 4, "type": "s32"},
    })
    return f


def scenario(name, description, steps, assertions):
    return {
        "name": name,
        "description": description,
        "tags": ["ojo-tribunal"],
        "state": {
            "symbols": {"sb": "g_sandbox", "enemies": "g_enemies", "player": "g_player_state", "nav": "g_nav_state"},
            "default_symbol": "sb",
            "fields": fields(),
        },
        "steps": steps,
        "assertions": assertions,
    }


def stage(hero, ojo, weapon="sniper", style=0):
    """Mortal hero (hits count), AI alive, one Ojo."""
    return sb.setup_steps(hero, weapon, style, [(OJO_TYPE, *ojo)], flags=sb.FLAG_CLEAR)[:-1]   # no idle capture: the AI is running


def wait_state(state, timeout, **extra):
    step = {"wait_until": {"field": "en0_state", "equals": state, "timeout_frames": timeout}}
    step.update(extra)
    return step


# ---------------------------------------------------------------------------
# (a) Open field: the shot hits a standing hero
# ---------------------------------------------------------------------------
def open_field():
    hero, ojo = (384, 724), (300, 724)
    require_clear(ojo, hero, "open field")
    steps = stage(hero, ojo) + [
        wait_state(ST_TRACK, 60, state_capture="siguiendo"),
        {"frames": 6, "capture": "01_banda_ancha_siguiendo", "state_capture": "siguiendo_6"},
        wait_state(ST_LOCK, 60, state_capture="fijada"),
        {"frames": 14, "capture": "02_linea_fina_fija", "state_capture": "fijada_14"},
        wait_state(ST_SENTENCE, 60, state_capture="haz"),
        {"frames": 2, "capture": "03_haz_de_sentencia"},                    # the beam lasts 6 frames
        {"frames": 6, "capture": "04_llamarada"},
        wait_state(ST_COOLDOWN, 60, state_capture="despues"),
    ]
    assertions = {
        "screen_changes": [
            {"from": "01_banda_ancha_siguiendo", "to": "02_linea_fina_fija", "min_changed_pixels": 10},
            {"from": "02_linea_fina_fija", "to": "03_haz_de_sentencia", "min_changed_pixels": 10},
        ],
        "state_changes": [
            {"at": "siguiendo", "field": "en0_timer", "min_value": TRACK_FRAMES - 2},   # TRACK just began
            {"at": "siguiendo", "field": "player_hp", "equals": 5},
            {"at": "siguiendo_6", "field": "en0_state", "equals": ST_TRACK},
            {"at": "fijada", "field": "en0_timer", "min_value": LOCK_FRAMES - 2},      # LOCK just began
            {"at": "fijada", "field": "player_hp", "equals": 5},                       # the lock does not hurt
            {"at": "fijada_14", "field": "en0_state", "equals": ST_LOCK},
            {"at": "fijada_14", "field": "player_hp", "equals": 5},
            {"at": "haz", "field": "player_hp", "equals": 4},                          # the shot cost exactly one hit
            {"at": "despues", "field": "player_hp", "equals": 4},                      # and only one
            {"at": "despues", "field": "en0_state", "equals": ST_COOLDOWN},
        ],
    }
    return scenario(
        "enemy_ojo_sentencia_alcanza_al_heroe_quieto",
        "Ojo 84 ground px west of a still, mortal hero in the open south hall (clear line, verified with the game's los "
        "test in tools/ojo_scenes.py). It stops and the green band follows the hero for 40 frames (TRACK), the line "
        "freezes for 20 (LOCK) and the mouth beam costs exactly 1 hit (5 -> 4) when it falls.",
        steps, assertions)


# ---------------------------------------------------------------------------
# (b) Full cycle from the search walk
# ---------------------------------------------------------------------------
def full_cycle():
    hero, ojo = (384, 724), (284, 652)
    ok, blocked = los(*ojo, *hero)
    if not ok:
        raise ValueError(f"full cycle: the line {ojo} -> {hero} is blocked at {blocked}")
    d = ground_dist(ojo, hero)
    if not (SIGHT_RANGE < d < SIGHT_RANGE + 60):
        raise ValueError(f"full cycle: start distance {d:.0f} must be just beyond the sight range {SIGHT_RANGE} so it walks first")
    steps = stage(hero, ojo) + [
        {"frames": 1, "state_capture": "inicio"},
        {"frames": 20, "capture": "00_busca_andando"},
        wait_state(ST_TRACK, 240, state_capture="fichado"),
        {"frames": 8, "capture": "01_banda_ancha_siguiendo"},
        wait_state(ST_LOCK, 60, state_capture="fijada"),
        {"frames": 14, "capture": "02_linea_fina_fija"},
        wait_state(ST_SENTENCE, 60, state_capture="haz"),
        {"frames": 2, "capture": "03_haz_de_sentencia"},
        {"frames": 10, "capture": "04_llamarada"},
        wait_state(ST_COOLDOWN, 60, state_capture="despues"),
    ]
    assertions = {
        "screen_changes": [
            {"from": "00_busca_andando", "to": "01_banda_ancha_siguiendo", "min_changed_pixels": 10},
            {"from": "01_banda_ancha_siguiendo", "to": "03_haz_de_sentencia", "min_changed_pixels": 10},
        ],
        "state_changes": [
            {"at": "inicio", "field": "en0_state", "equals": 0},        # CHASE: it starts searching
            {"at": "fichado", "field": "player_hp", "equals": 5},
            {"at": "fijada", "field": "player_hp", "equals": 5},
            {"at": "haz", "field": "en0_state", "equals": ST_SENTENCE},
            {"at": "haz", "field": "player_hp", "equals": 4},
            {"at": "despues", "field": "en0_state", "equals": ST_COOLDOWN},
            {"at": "despues", "field": "player_hp", "equals": 4},
        ],
    }
    return scenario(
        "enemy_ojo_andar_mirar_sentenciar",
        "Evidence of the whole cycle: the Ojo starts about 175 ground px west-north-west of a still hero in the open south "
        "hall (clear line), walks searching (CHASE), stops and follows him with the green band (TRACK), freezes the line "
        "(LOCK) and fires from the mouth (SENTENCE, one hit) before the cooldown.",
        steps, assertions)


# ---------------------------------------------------------------------------
# (c) The hero leaves the locked line
# ---------------------------------------------------------------------------
def dodge_by_leaving_the_line():
    hero, ojo = (384, 724), (300, 724)
    require_clear(ojo, hero, "dodge")
    steps = stage(hero, ojo) + [
        wait_state(ST_LOCK, 120, state_capture="fijada"),
        {"frames": 2, "capture": "01_linea_fija_con_el_heroe_encima"},
        {"button_down": "UP", "frames": 20, "capture": "02_heroe_fuera_de_la_linea", "state_capture": "esquiva"},
        {"button_up": "UP", "frames": 1},
        wait_state(ST_SENTENCE, 20, state_capture="haz"),
        {"frames": 8, "capture": "03_haz_esquivado"},
        wait_state(ST_COOLDOWN, 60, state_capture="despues"),
    ]
    assertions = {
        "screen_changes": [{"from": "01_linea_fija_con_el_heroe_encima", "to": "03_haz_esquivado", "min_changed_pixels": 10}],
        "state_changes": [
            {"at": "fijada", "field": "en0_timer", "min_value": LOCK_FRAMES - 2},
            {"at": "esquiva", "field": "nav_y", "max_value": 182272},        # 712 px in 8.8: >= 12 px north of the line
            {"at": "esquiva", "field": "en0_state", "min_value": ST_LOCK},   # locked or already firing: it never went back to tracking
            {"at": "haz", "field": "player_hp", "equals": 5},                # the beam fired and missed
            {"at": "despues", "field": "player_hp", "equals": 5},
            {"at": "despues", "field": "en0_state", "equals": ST_COOLDOWN},
        ],
    }
    return scenario(
        "enemy_ojo_esquiva_saliendo_de_la_linea",
        "Ojo 84 ground px west of the hero on open floor. Once the line freezes (LOCK) the hero walks north: 20 UP frames "
        "move about 12 screen px = 24 ground px, well beyond the 8 px half-width of the beam on the locked row. The "
        "sentence is visible and misses (5 hp); it never goes back to tracking.",
        steps, assertions)


def hero_walks_into_the_flare():
    hero, ojo = (384, 724), (300, 724)
    require_clear(ojo, hero, "walk into the flare")
    steps = stage(hero, ojo) + [
        wait_state(ST_LOCK, 120, state_capture="fijada"),
        {"button_down": "UP", "frames": 20, "state_capture": "fuera"},
        {"button_up": "UP", "frames": 1},
        wait_state(ST_SENTENCE, 20, state_capture="haz"),
        {"frames": 2, "capture": "01_llamarada_con_el_heroe_fuera", "state_capture": "fuera_de_la_linea"},
        {"button_down": "DOWN", "frames": 20, "capture": "02_heroe_entra_en_la_llamarada", "state_capture": "dentro"},
        {"button_up": "DOWN", "frames": 1},
        wait_state(ST_COOLDOWN, 60, state_capture="despues"),
    ]
    assertions = {
        "screen_changes": [{"from": "01_llamarada_con_el_heroe_fuera", "to": "02_heroe_entra_en_la_llamarada", "min_changed_pixels": 10}],
        "state_changes": [
            {"at": "fuera", "field": "nav_y", "max_value": 182272},            # >= 12 px north of the line: off it
            {"at": "haz", "field": "player_hp", "equals": 5},                  # the shot started and he was not on the line
            {"at": "fuera_de_la_linea", "field": "player_hp", "equals": 5},
            {"at": "fuera_de_la_linea", "field": "en0_state", "equals": ST_SENTENCE},
            {"at": "dentro", "field": "en0_state", "equals": ST_SENTENCE},     # still flaring: it hurts him now
            {"at": "dentro", "field": "player_hp", "equals": 4},               # one hit (i-frames cover the rest)
            {"at": "despues", "field": "player_hp", "equals": 4},
        ],
    }
    return scenario(
        "enemy_ojo_heroe_entra_en_la_llamarada",
        "Ojo 84 ground px west of the hero on open floor. The hero leaves the locked row (20 UP frames = about 24 ground "
        "px off it), the shot starts and misses him (5 hp). While the flare still burns he walks back DOWN into the row "
        "(20 frames, 8 ground px half-width crossed after about 12) and takes exactly one hit (4 hp): the beam is a "
        "temporary wall during impact and flare.",
        steps, assertions)


# ---------------------------------------------------------------------------
# (f) The beam and an actor that is NOT its target: painter order by ground depth
# ---------------------------------------------------------------------------
BEAM_GROUND_Y = 724                   # the locked line runs along this row: Ojo and hero stand on it
ACTOR_X = 350                         # between the Ojo's hand (x ~ 325) and the hero (384)


def depth_actor_scene(name, actor_y, description, front):
    hero, ojo = (384, 724), (300, 724)
    require_clear(ojo, hero, name)
    # The sleeping charger (a DORMANT enemy stands still and is drawn) overlaps the beam on screen: its feet are within
    # a sprite height below the beam's screen row (mouth ~ 21 px above the ground row) and its body covers that row.
    beam_screen_y = BEAM_GROUND_Y - 21
    if not (actor_y - 32 < beam_screen_y < actor_y):
        raise ValueError(f"{name}: the actor at feet y={actor_y} does not cover the beam's screen row {beam_screen_y}")
    if front and not actor_y < BEAM_GROUND_Y - 4:
        raise ValueError(f"{name}: an actor in front of the beam must have its feet further away than the beam's ground row")
    if not front and not actor_y > BEAM_GROUND_Y + 4:
        raise ValueError(f"{name}: an actor behind the beam must have its feet nearer than the beam's ground row")
    steps = sb.setup_steps(hero, "sniper", 0, [(OJO_TYPE, *ojo), (sb.CHARGER, ACTOR_X, actor_y)],
                           flags=sb.FLAG_CLEAR | sb.FLAG_GOD)[:-1]
    for st in steps:
        for pk in st.get("poke", []):
            if pk["field"] == "e1_flags":
                pk["value"] = 1                                   # SANDBOX_ENEMY_FLAG_ASLEEP: it stays where it is
    steps += [
        wait_state(ST_SENTENCE, 200, state_capture="haz"),
        {"frames": 6, "capture": "01_llamarada_" + ("sobre_el_actor_mas_lejano" if front else "tras_el_actor_mas_cercano"),
         "state_capture": "llamarada"},
        {"frames": 2, "capture": "02_llamarada_siguiente_frame"},
    ]
    assertions = {
        "screen_changes": [{"from": steps[-2]["capture"], "to": "02_llamarada_siguiente_frame", "min_changed_pixels": 1}],
        "state_changes": [
            {"at": "llamarada", "field": "en0_state", "equals": ST_SENTENCE},
            {"at": "llamarada", "field": "en1_state", "equals": ST_DORMANT},     # the actor did not move
            {"at": "llamarada", "field": "en1_y", "equals": actor_y * 256},
        ],
    }
    return scenario(name, description, steps, assertions)


def beam_in_front_of_actor():
    return depth_actor_scene(
        "enemy_ojo_llamarada_pasa_delante_de_un_actor_mas_lejano", 716,
        "Ojo at (300,724), hero at (384,724) on the same ground row (god mode). A sleeping charger at (350,716) stands 8 ground "
        "px FURTHER from the camera than the beam's row 724 and its sprite covers the beam's screen row: the flare must be "
        "painted over its body. Capture only (pixels are inspected by eye); the assertions check the staging.",
        True)


def beam_behind_an_actor():
    return depth_actor_scene(
        "enemy_ojo_llamarada_pasa_detras_de_un_actor_mas_cercano", 730,
        "Ojo at (300,724), hero at (384,724) on the same ground row (god mode). A sleeping charger at (350,730) stands 6 ground "
        "px NEARER to the camera than the beam's row 724 and its sprite covers the beam's screen row: the charger must be "
        "painted over the flare. Capture only (pixels are inspected by eye); the assertions check the staging.",
        False)


# ---------------------------------------------------------------------------
# (d) Pillar between Ojo and hero
# ---------------------------------------------------------------------------
PILLAR_OJO = (300, 528)               # level with the pillar's rows, west of it
PILLAR_HERO = (420, 550)              # east of it, just clear of its south face
PILLAR_HIDDEN = (420, 528)            # level with the pillar's middle, east of it: the pillar is in the line


def pillar_cuts_the_gaze():
    require_blocked_by_pillar(PILLAR_OJO, PILLAR_HIDDEN, "hidden hero")
    d = ground_dist(PILLAR_OJO, PILLAR_HIDDEN)
    if d > SIGHT_RANGE:
        raise ValueError(f"hidden hero: {d:.0f} ground px is beyond the Ojo's sight range {SIGHT_RANGE}")
    steps = stage(PILLAR_HIDDEN, PILLAR_OJO) + [
        {"frames": 12, "capture": "01_heroe_oculto_tras_la_columna", "state_capture": "a_los_12"},
        {"frames": 13, "capture": "02_sigue_sin_fijarlo", "state_capture": "a_los_25"},
    ]
    assertions = {
        "state_changes": [
            {"at": "a_los_12", "field": "en0_state", "max_value": 1},         # CHASE / ATTACK: not tracking
            {"at": "a_los_25", "field": "en0_state", "max_value": 1},
            {"at": "a_los_25", "field": "player_hp", "equals": 5},
        ],
    }
    return scenario(
        "enemy_ojo_columna_corta_la_mirada",
        "Ojo at (300,528) and a hero at (420,528), 120 ground px away (inside the sight range) with the pillar x352-383,"
        "y520-535 exactly in the line (checked with the game's los test). For 25 frames the Ojo never starts tracking "
        "(state CHASE) and the hero is not hurt: a column cuts the gaze.",
        steps, assertions)


def pillar_hides_the_hero_during_the_aim():
    walk = 20
    require_clear(PILLAR_OJO, PILLAR_HERO, "pillar scenario start")
    lo = round(PILLAR_HERO[1] - walk * HERO_VY_PER_FRAME * 1.15)
    hi = round(PILLAR_HERO[1] - walk * HERO_VY_PER_FRAME * 0.85)
    for y in range(lo, hi + 1):
        require_blocked_by_pillar(PILLAR_OJO, (PILLAR_HERO[0], y), f"pillar scenario end y={y}")
    steps = stage(PILLAR_HERO, PILLAR_OJO) + [
        wait_state(ST_LOCK, 120, state_capture="fijada"),
        {"frames": 2, "capture": "01_linea_fija_heroe_a_la_vista"},
        {"button_down": "UP", "frames": walk, "capture": "02_heroe_tras_la_columna", "state_capture": "oculto"},
        {"button_up": "UP", "frames": 1},
        wait_state(ST_SENTENCE, 20, state_capture="haz"),
        {"frames": 8, "capture": "03_haz_sin_heroe"},
        wait_state(ST_COOLDOWN, 60, state_capture="despues"),
    ]
    assertions = {
        "screen_changes": [{"from": "01_linea_fija_heroe_a_la_vista", "to": "02_heroe_tras_la_columna", "min_changed_pixels": 10}],
        "state_changes": [
            {"at": "fijada", "field": "player_hp", "equals": 5},
            {"at": "oculto", "field": "en0_state", "min_value": ST_LOCK},
            {"at": "haz", "field": "player_hp", "equals": 5},                 # fired at the old point, he is not there
            {"at": "despues", "field": "player_hp", "equals": 5},
            {"at": "despues", "field": "en0_state", "equals": ST_COOLDOWN},
        ],
    }
    return scenario(
        "enemy_ojo_heroe_tras_la_columna_no_recibe_el_haz",
        "Ojo at (300,528) level with the pillar x352-383,y520-535; hero at (420,550) east of it with a clear line "
        "(checked with the game's los test). When the line freezes the hero walks north 20 frames to about y537, where "
        "the line from the Ojo crosses the pillar (checked for the whole range of possible end positions). The sentence "
        "still fires, at the frozen point, and he is not hurt (5 hp).",
        steps, assertions)


# ---------------------------------------------------------------------------
# (e) The Ojo dies before the shot
# ---------------------------------------------------------------------------
def ojo_dies_before_the_shot():
    hero, ojo = (40, 724), (110, 724)
    require_clear(ojo, hero, "kill scenario")
    sb.check_beam(hero, 110, [(OJO_TYPE, *ojo)])          # the sniper beam row crosses the Ojo (rule 5)
    steps = stage(hero, ojo, weapon="sniper", style=2)
    steps += [
        {"poke": [{"field": "en0_hp", "value": 100}], "frames": 1},       # one sniper hit (150) kills it
        wait_state(ST_TRACK, 120, state_capture="siguiendo"),
        {"frames": 3, "capture": "01_banda_siguiendo_antes_del_disparo"},
        {"tap": sb.touch_at(hero, ojo[0], ojo[1] + sb.MUZZLE_DY, sb.MUZZLE_H), "frames": 30, "capture": "02_francotirador_cargado"},
        {"release": True, "frames": 6, "capture": "03_ojo_abatido", "state_capture": "abatido"},
        {"frames": 80, "capture": "04_sin_sentencia", "state_capture": "despues"},
    ]
    assertions = {
        "screen_changes": [{"from": "01_banda_siguiendo_antes_del_disparo", "to": "03_ojo_abatido", "min_changed_pixels": 20}],
        "state_changes": [
            {"at": "siguiendo", "field": "en0_state", "equals": ST_TRACK},
            {"at": "siguiendo", "field": "en0_active", "equals": 1},
            {"at": "abatido", "field": "en0_active", "equals": 0},             # dead before the 60 frames ran out
            {"at": "despues", "field": "en0_active", "equals": 0},
            {"at": "despues", "field": "player_hp", "equals": 5},              # no beam ever hurt him
        ],
    }
    return scenario(
        "enemy_ojo_muerto_antes_de_la_sentencia",
        "Ojo 70 px east of a still, mortal hero on the same row (open floor, clear line). Its hp is set to 100 so one "
        "sniper hit kills it. While the band follows the hero (TRACK, 60 frames to the shot) the sniper is charged (30 "
        "frames) and released along the row that crosses the Ojo, which dies before the sentence: no beam, 5 hp.",
        steps, assertions)


# ---------------------------------------------------------------------------
# DeSmuME A/B only (AGENTS.md rule 6): cost per frame with two shooter-type enemies working on the hero
# ---------------------------------------------------------------------------
def perf_two_ojos():
    """Two shooter-type enemies 84 px either side of an invulnerable hero in the open south hall. On this branch both
    Ojos aim (two bands, TRACK/LOCK); on the baseline the two laser shooters aim and fire. ROM: sandbox variant with
    PERF_PROFILE=1. Samples 20 windows of 60 frames of the profiler averages (tools/perf_bench_summary.py)."""
    hero, ojos = (384, 724), [(300, 724), (468, 724)]
    for o in ojos:
        require_clear(o, hero, "perf scene")
    f = {k: dict(v, symbol="sb") for k, v in sb.FIELDS.items()}
    stages = {"pl": 0, "en": 8, "wp": 12, "dclr": 16, "sh": 20, "sort": 24, "blit": 28, "proj": 32, "pick": 36, "hud": 40,
              "bgsub": 48, "bgbot": 52, "vwait": 56, "cpu": 60, "frame": 64}
    for k, off in stages.items():
        f[k] = {"symbol": "avg", "offset": off, "type": "u32"}
        f[k + "_max"] = {"symbol": "mx", "offset": off, "type": "u32"}
    f["fps10"] = {"symbol": "fps", "offset": 0, "type": "u32"}
    f["alive"] = {"symbol": "strip", "offset": 8, "type": "s32"}
    steps = sb.setup_steps(hero, "sniper", 0, [(OJO_TYPE, *o) for o in ojos], flags=sb.FLAG_CLEAR | sb.FLAG_GOD)[:-1]
    steps.append({"frames": 240})                       # let the first cycle settle
    steps += [{"frames": 60, "state_capture": f"w{n:02d}"} for n in range(1, 21)]
    return {
        "name": "perf_ojo_dos_mirando",
        "description": "DeSmuME A/B only, never a certification (AGENTS.md rule 6). Two shooter-type enemies 84 px either side of a "
                       "god-mode hero in the open south hall (clear lines, checked in tools/ojo_scenes.py). ROM: sandbox + PERF_PROFILE=1. "
                       "20 windows of 60 frames of the profiler averages; summarise with tools/perf_bench_summary.py.",
        "tags": ["ojo-tribunal", "perf"],
        "state": {"symbols": {"sb": "g_sandbox", "avg": "s_hud_avg", "fps": "s_hud_fps10", "strip": "g_strip_debug", "mx": "s_hud_max"},
                  "default_symbol": "sb", "fields": f},
        "steps": steps,
        "assertions": {"state_changes": [{"at": "w10", "field": "fps10", "min_value": 1}]},
    }


def main():
    out = ROOT / "scenarios"
    scenes = [open_field(), full_cycle(), dodge_by_leaving_the_line(), hero_walks_into_the_flare(), beam_in_front_of_actor(), beam_behind_an_actor(), pillar_cuts_the_gaze(),
              pillar_hides_the_hero_during_the_aim(), ojo_dies_before_the_shot(), perf_two_ojos()]
    for sc in scenes:
        path = out / f"{sc['name']}.json"
        path.write_text(json.dumps(sc, indent=2) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
