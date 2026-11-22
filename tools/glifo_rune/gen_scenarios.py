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


def build(name, redil, zarza):
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
    for i, (dx, dy) in enumerate(ENEMIES):
        stage += pk(**{"e%dx" % i: (TARGET[0] + dx) << 8, "e%dy" % i: (TARGET[1] + dy) << 8,
                       "e%dst" % i: 0, "e%dstun" % i: STUN_FRAMES, "e%dhp" % i: 400, "e%dburn" % i: 0})
    steps += [{"poke": stage, "frames": 3, "state_capture": "pre", "capture": "pre"},
              {"tap": {"x": TAP[0], "y": TAP[1]}, "frames": 8},
              {"release": True, "frames": 215, "capture_sequence": name, "capture_every": 3},
              {"frames": 2, "state_capture": "post"}]
    return {
        "name": name,
        "description": "Evidencia del Glifo (%s): cuatro enemigos quietos dentro de la runa, ciclo completo desde la ROM real. "
                       "Solo capturas." % name,
        "suite": False, "evidence_only": True,
        "steps": steps,
        "state": {"elf": "../.ds-game-dev/build/out/dungeonds-arpg-todo.elf",
                  "symbols": {"pl": "s_player", "arpg": "g_arpg", "en": "g_enemies", "gps": "g_player_state"},
                  "default_symbol": "pl", "fields": FIELDS},
    }


def main():
    for name, redil, zarza in (("glifo_sello", 0, 0), ("glifo_sello_redil", 1, 0),
                               ("glifo_sello_zarza", 0, 1), ("glifo_sello_redil_zarza", 1, 1)):
        with open(os.path.join(ROOT, "scenarios", name + ".json"), "w", newline="\n", encoding="utf-8") as f:
            json.dump(build(name, redil, zarza), f, indent=1)
            f.write("\n")
        print(name)


if __name__ == "__main__":
    main()
