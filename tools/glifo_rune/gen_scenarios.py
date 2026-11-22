#!/usr/bin/env python3
"""Genera los escenarios de evidencia del Glifo (scenarios/glifo_<combinacion>.json), uno por combinacion de auras:
sello, sello+redil, sello+zarza y sello+redil+zarza. Los cuatro son evidence_only (capturas, sin aserciones).

Camino: campamento -> puerta (A) -> primer pasillo de la catedral; con la ROM `arpg-todo` el heroe ya lleva el tomo del
Glifo (hueco 1) y las reliquias Redil (engarce 0) y Zarza (engarce 1) de la escuela Glifo. Cada escenario fija por poke la
combinacion (mecanica de cada engarce), pone cuatro enemigos aturdidos (stun_timer alto: inertes, sin IA, vulnerables) dentro de la elipse de la
runa (geometria: ver ENEMIES) y lanza el Glifo con el stylus.

    python tools/glifo_rune/gen_scenarios.py
    build-project.ps1 -Variant arpg-todo ; run-scenario.ps1 -RomPath dungeonds-arpg-todo.nds -Scenario scenarios/glifo_<x>.json
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

ENEMY_SIZE = 124                     # sizeof(Enemy) en ARM (enums de 1 byte)
MECH_REDIL, MECH_ZARZA, MECH_NONE = 17, 7, 255
OFF_MECH_G0, OFF_MECH_G1 = 381, 395  # g_arpg.inv.socket[GLIFO][0|1].mech
OFF_G2 = 406                         # g_arpg.inv.socket[GLIFO][2] (ArpgInvItem de 14 B): kind +0, nlines +4, line_kind[0] +5, line_val[0] +8
LINE_RADIUS = 9                      # ARPG_LINE_RADIUS
STUN_FRAMES = 3000                   # stun_timer: el enemigo se queda inerte (sin IA) pero vulnerable y sin ser invulnerable como REMATE

HERO = (256, 1792)                   # el heroe nace aqui al salir del campamento; la camara lo deja en la pantalla (128, 118)
TARGET = (256, 1722)                 # centro de la runa: 70 px al norte (alcance 140)
TAP = (128, 48)                      # pantalla inferior: 118 - 70
# Cuatro enemigos dentro de la elipse de suelo (80x40): (dx/40)^2 + (dy/20)^2 < 1, repartidos para que el arrastre se vea.
ENEMIES = [(-34, 4), (36, 0), (-6, -12), (12, 16)]

FIELDS = {
    "px": {"symbol": "pl", "offset": 0, "type": "s32"},
    "py": {"symbol": "pl", "offset": 4, "type": "s32"},
    "spell": {"symbol": "arpg", "offset": 18, "type": "u16"},
    "mech0": {"symbol": "arpg", "offset": OFF_MECH_G0, "type": "u8"},
    "mech1": {"symbol": "arpg", "offset": OFF_MECH_G1, "type": "u8"},
    "god": {"symbol": "gps", "offset": 20, "type": "s32"},
    "mana": {"symbol": "gps", "offset": 24, "type": "s32"},
    "g2_kind": {"symbol": "arpg", "offset": OFF_G2, "type": "u8"},
    "g2_school": {"symbol": "arpg", "offset": OFF_G2 + 1, "type": "u8"},
    "g2_mech": {"symbol": "arpg", "offset": OFF_G2 + 3, "type": "u8"},
    "z_active": {"symbol": "zones", "offset": 0, "type": "s32"},
    "z_r": {"symbol": "zones", "offset": 12, "type": "s32"},
    "z_t": {"symbol": "zones", "offset": 20, "type": "s32"},
    "z_det": {"symbol": "zones", "offset": 28, "type": "s32"},
    "z_end": {"symbol": "zones", "offset": 32, "type": "s32"},
    "g2_nlines": {"symbol": "arpg", "offset": OFF_G2 + 4, "type": "u8"},
    "g2_line0": {"symbol": "arpg", "offset": OFF_G2 + 5, "type": "u8"},
    "g2_val0": {"symbol": "arpg", "offset": OFF_G2 + 8, "type": "u16"},
}
for i in range(6):
    o = i * ENEMY_SIZE
    FIELDS["e%dx" % i] = {"symbol": "en", "offset": o, "type": "s32"}
    FIELDS["e%dy" % i] = {"symbol": "en", "offset": o + 4, "type": "s32"}
    FIELDS["e%dhp" % i] = {"symbol": "en", "offset": o + 28, "type": "s32"}
    FIELDS["e%dst" % i] = {"symbol": "en", "offset": o + 41, "type": "u8"}
    FIELDS["e%dstun" % i] = {"symbol": "en", "offset": o + 76, "type": "s32"}
    FIELDS["e%dburn" % i] = {"symbol": "en", "offset": o + 116, "type": "u8"}


def pk(**kw):
    return [{"field": k, "value": v} for k, v in kw.items()]


def build(name, redil, zarza, radius_pct=0, walk=False, far=False):
    steps = [
        {"frames": 60},
        {"tap": {"x": 128, "y": 66}, "frames": 6}, {"release": True, "frames": 40},
        {"button_down": "START", "frames": 4}, {"button_up": "START", "frames": 40},
        {"tap": {"x": 128, "y": 155}, "frames": 6}, {"release": True, "frames": 60},
        # campamento: rodear la hoguera por la derecha y subir hasta la puerta (el paso es lento en el campamento)
        {"button_down": "RIGHT", "frames": 100}, {"button_up": "RIGHT", "frames": 2},
        {"button_down": "UP", "frames": 1000}, {"button_up": "UP", "frames": 2},
        {"button_down": "LEFT", "frames": 100}, {"button_up": "LEFT", "frames": 2},
        {"button_down": "UP", "frames": 120}, {"button_up": "UP", "frames": 2},
        {"button_down": "A", "frames": 4}, {"button_up": "A", "frames": 150},
    ]
    stage = pk(god=1, mana=200, spell=1,
               mech0=MECH_REDIL if redil else MECH_NONE, mech1=MECH_ZARZA if zarza else MECH_NONE)
    if radius_pct:   # una linea de Radio en el tercer engarce del Glifo: la runa y la zona crecen
        stage += pk(g2_kind=1, g2_school=2, g2_mech=MECH_NONE, g2_nlines=1, g2_line0=LINE_RADIUS, g2_val0=radius_pct)
    k = 100 + radius_pct
    for i, (dx, dy) in enumerate(ENEMIES):
        dx, dy = dx * k // 100, dy * k // 100       # los enemigos siguen dentro de la elipse agrandada
        stage += pk(**{"e%dx" % i: (TARGET[0] + dx) << 8, "e%dy" % i: (TARGET[1] + dy) << 8,
                       "e%dst" % i: 0, "e%dstun" % i: STUN_FRAMES, "e%dhp" % i: 400, "e%dburn" % i: 0})
    steps += [{"poke": stage, "frames": 3, "state_capture": "pre", "capture": "pre"},
              {"tap": {"x": TAP[0], "y": TAP[1]}, "frames": 8},
              ]
    if far:    # Glifo sin alcance: stylus en una esquina lejana (>140 px) mientras el heroe anda con la cruceta, luego suelta
        steps += [{"tap": {"x": 250, "y": 12}, "frames": 2},
                  {"button_down": "DOWN", "frames": 60, "capture_sequence": name, "capture_every": 6},
                  {"button_up": "DOWN", "frames": 1},
                  {"release": True, "frames": 215, "capture_sequence": name + "_b", "capture_every": 6},
                  {"frames": 2, "state_capture": "post"}]
    elif walk:   # reza andando: tras soltar el stylus el heroe baja hacia la camara (se le ven las manos) a velocidad normal
        steps += [{"release": True, "frames": 2},
                  {"button_down": "DOWN", "frames": 44, "capture_sequence": name, "capture_every": 1},
                  {"button_up": "DOWN", "frames": 150},
                  {"frames": 2, "state_capture": "post"}]
    else:
        steps += [{"release": True, "frames": 215, "capture_sequence": name, "capture_every": 3},
                  {"frames": 2, "state_capture": "post"}]
    return {
        "name": name,
        "description": "Evidencia del Glifo (%s): cuatro enemigos quietos dentro de la runa, ciclo completo desde la ROM real. "
                       "Solo capturas." % name,
        "suite": False, "evidence_only": True,
        "steps": steps,
        "state": {"elf": "../.ds-game-dev/build/out/dungeonds-arpg-todo.elf",
                  "symbols": {"pl": "s_player", "arpg": "g_arpg", "en": "g_enemies", "gps": "g_player_state", "zones": "s_zones"},
                  "default_symbol": "pl", "fields": FIELDS},
    }


def build_muro():
    """Solo suelo: (a) stylus sobre el muro lateral (pantalla x 8 = mundo 136, dentro del muro 128..152): no hay glifo ni se gasta
    mana; (b) stylus sobre el suelo pegado al muro (pantalla x 40 = mundo 168, runa de 40 px que llega a x 128): la runa se corta
    en el borde del muro."""
    steps = [st for st in build("x", 0, 0)["steps"]]
    steps = steps[:next(i for i, st in enumerate(steps) if "poke" in st)]
    steps += [{"poke": pk(god=1, mana=200, spell=1, mech0=MECH_NONE, mech1=MECH_NONE), "frames": 3, "state_capture": "pre", "capture": "pre"},
              {"tap": {"x": 8, "y": 100}, "frames": 8}, {"release": True, "frames": 60, "capture": "muro"},
              {"frames": 2, "state_capture": "tras_muro"},
              {"tap": {"x": 40, "y": 100}, "frames": 8},
              {"release": True, "frames": 100, "capture_sequence": "glifo_muro", "capture_every": 6},
              {"frames": 2, "state_capture": "tras_suelo"}]
    return {
        "name": "glifo_muro",
        "description": "Solo suelo (DESIGN.md 7, Glifo): sobre el muro no se lanza ni se gasta mana; junto al muro la runa se recorta en su borde.",
        "suite": False,
        "steps": steps,
        "assertions": {"state_changes": [
            {"at": "tras_muro", "field": "z_active", "equals": 0},
            {"at": "tras_muro", "field": "mana", "equals": 200},
            {"at": "tras_suelo", "field": "z_active", "equals": 1},
            {"at": "tras_suelo", "field": "mana", "max_value": 199}]},
        "state": {"elf": "../.ds-game-dev/build/out/dungeonds-arpg-todo.elf",
                  "symbols": {"pl": "s_player", "arpg": "g_arpg", "en": "g_enemies", "gps": "g_player_state", "zones": "s_zones"},
                  "default_symbol": "pl", "fields": FIELDS},
    }


NL = chr(10)


def build_preview():
    """Previsualizacion: el stylus se apoya en suelo ~40 frames y se mueve (centro del pasillo, pegado al muro lateral, de vuelta);
    se suelta sobre suelo y el sello real se abre tras el rezo. Solo capturas."""
    steps = [st for st in build("x", 0, 0)["steps"]]
    steps = steps[:next(i for i, st in enumerate(steps) if "poke" in st)]
    steps += [{"poke": pk(god=1, mana=200, spell=1, mech0=MECH_NONE, mech1=MECH_NONE), "frames": 3, "state_capture": "pre", "capture": "pre"},
              {"tap": {"x": 128, "y": 60}, "frames": 10, "capture_sequence": "glifo_preview", "capture_every": 2},
              {"tap": {"x": 100, "y": 70}, "frames": 6, "capture_sequence": "glifo_preview_b", "capture_every": 2},
              {"tap": {"x": 60, "y": 90}, "frames": 8, "capture_sequence": "glifo_preview_c", "capture_every": 2},
              {"tap": {"x": 40, "y": 100}, "frames": 10, "capture_sequence": "glifo_preview_d", "capture_every": 2},
              {"tap": {"x": 90, "y": 80}, "frames": 8, "capture_sequence": "glifo_preview_e", "capture_every": 2},
              {"tap": {"x": 128, "y": 60}, "frames": 8, "capture_sequence": "glifo_preview_f", "capture_every": 2},
              {"release": True, "frames": 150, "capture_sequence": "glifo_preview_g", "capture_every": 2},
              {"frames": 2, "state_capture": "post"}]
    return {
        "name": "glifo_preview",
        "description": "Evidencia de la previsualizacion tenue del Glifo (DESIGN.md 7): runa quieta y tenue bajo el stylus, recortada en el muro; "
                       "al soltar rezo y sello real. Solo capturas.",
        "suite": False, "evidence_only": True,
        "steps": steps,
        "state": {"elf": "../.ds-game-dev/build/out/dungeonds-arpg-todo.elf",
                  "symbols": {"pl": "s_player", "arpg": "g_arpg", "en": "g_enemies", "gps": "g_player_state", "zones": "s_zones"},
                  "default_symbol": "pl", "fields": FIELDS},
    }


def main():
    with open(os.path.join(ROOT, "scenarios", "glifo_preview.json"), "w", newline=NL, encoding="utf-8") as f:
        json.dump(build_preview(), f, indent=1)
        f.write(NL)
    with open(os.path.join(ROOT, "scenarios", "glifo_muro.json"), "w", newline="\n", encoding="utf-8") as f:
        json.dump(build_muro(), f, indent=1)
        f.write("\n")
    for name, redil, zarza, rad in (("glifo_sello", 0, 0, 0), ("glifo_sello_redil", 1, 0, 0),
                                    ("glifo_sello_zarza", 0, 1, 0), ("glifo_sello_redil_zarza", 1, 1, 0),
                                    ("glifo_sello_radio", 0, 0, 100), ("glifo_sello_radio_redil_zarza", 1, 1, 60),
                                    ("glifo_reza_andando", 0, 0, 0), ("glifo_lejos", 0, 0, 0)):
        with open(os.path.join(ROOT, "scenarios", name + ".json"), "w", newline="\n", encoding="utf-8") as f:
            json.dump(build(name, redil, zarza, rad, walk=name == "glifo_reza_andando", far=name == "glifo_lejos"), f, indent=1)
            f.write("\n")
        print(name)


if __name__ == "__main__":
    main()
