#!/usr/bin/env python3
"""Genera los tres escenarios del bot de encuentros (scenarios/encuentros_bot_*.json).

El juego sube `cap_seq` cada 600 frames, 45 frames despues de despertar un encuentro y 30 despues de limpiarlo
(enc_stats_frame en encounters_act1.c); cada paso espera un valor mas y captura. Al acabar el acto (victoria,
muerte o 30000 frames) `cap_seq` salta a 255 y los pasos que quedan pasan de golpe.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
N_CAPTURES = 110
ENC = 12

fields = {
    "state": {"offset": 0, "type": "u8"}, "current": {"offset": 1, "type": "u8"}, "plant": {"offset": 2, "type": "u8"},
    "tier": {"offset": 3, "type": "u8"}, "woken": {"offset": 4, "type": "u8"}, "cleared": {"offset": 5, "type": "u8"},
    "dones": {"offset": 6, "type": "u8"}, "deaths": {"offset": 7, "type": "u8"},
    "wake_frames": {"offset": 8, "type": "u16"}, "relicarios": {"offset": 10, "type": "u16"},
    "alive": {"offset": 61, "type": "u8"},
    "act_frames": {"offset": 88, "type": "u32"}, "clock": {"offset": 92, "type": "u32"},
    "result": {"offset": 96, "type": "u8"}, "death_enc": {"offset": 97, "type": "u8"},
    "cap_seq": {"offset": 98, "type": "u8"}, "hp": {"offset": 99, "type": "u8"}, "max_hp": {"offset": 100, "type": "u8"},
    "bot_rule": {"offset": 101, "type": "u8"}, "stuck_events": {"offset": 102, "type": "u16"},
    "shots": {"offset": 104, "type": "u16"}, "hits_total": {"offset": 106, "type": "u16"},
    "boss_frames": {"offset": 120, "type": "u16"}, "relic_mask": {"offset": 122, "type": "u16"},
    "relic_seen": {"offset": 124, "type": "u16"}, "relic_shootable": {"offset": 126, "type": "u16"},
    "hp_min": {"offset": 132, "type": "u8"},
    "relic_norange": {"offset": 128, "type": "u16"}, "relic_nolos": {"offset": 130, "type": "u16"},
}
for k in range(ENC):
    fields[f"clear_{k}"] = {"offset": 12 + 2 * k, "type": "u16"}
    fields[f"hits_{k}"] = {"offset": 36 + k, "type": "u8"}
    fields[f"plant_{k}"] = {"offset": 48 + k, "type": "u8"}
    fields[f"hpend_{k}"] = {"offset": 64 + k, "type": "u8"}
    fields[f"tier_{k}"] = {"offset": 76 + k, "type": "u8"}
    fields[f"donesat_{k}"] = {"offset": 108 + k, "type": "u8"}
for name, off, typ in (("dbg_start_dones", 0, "u8"), ("dbg_auto_pick", 1, "u8"), ("dbg_god", 2, "u8"),
                       ("dbg_no_dones", 3, "u8"), ("dbg_seed", 4, "u16"), ("dbg_reaction", 6, "u8"), ("dbg_aim_err", 7, "u8"), ("dbg_ojo_delay", 8, "u8"), ("dbg_miss_pct", 9, "u8"), ("dbg_boss_hp", 14, "u16")):
    fields[name] = {"symbol": "dbg", "offset": off, "type": typ}
for i in range(16):
    fields[f"boss_hp_{i}"] = {"offset": 144 + 2 * i, "type": "u16"}
fields.update({"boss_hits": {"offset": 176, "type": "u16"}, "mona_hits": {"offset": 178, "type": "u16"},
               "boss_shots": {"offset": 180, "type": "u16"}, "mona_alive": {"offset": 182, "type": "u8"},
               "mona_alive_max": {"offset": 183, "type": "u8"}, "boss_hp_now": {"offset": 184, "type": "u16"},
               "mona_kills": {"offset": 186, "type": "u16"}})
fields["hero_x"] = {"symbol": "nav", "offset": 0, "type": "s32"}
fields["hero_y"] = {"symbol": "nav", "offset": 4, "type": "s32"}


HUMANO = (30, 12, 20, 0)     # reaccion, error de apuntado, retraso al Ojo, % de cargas no esquivadas
TORPE = (30, 12, 40, 25)


def profile_pokes(p):
    return [{"field": "dbg_reaction", "value": p[0]}, {"field": "dbg_aim_err", "value": p[1]},
            {"field": "dbg_ojo_delay", "value": p[2]}, {"field": "dbg_miss_pct", "value": p[3]}]


def scenario(name, description, pokes, profile=HUMANO):
    steps = [{"poke": [{"field": "dbg_seed", "value": 1}] + profile_pokes(profile) + pokes, "frames": 3, "capture": "00_inicio",
              "state_capture": "start"}]
    for j in range(1, N_CAPTURES + 1):
        steps.append({"wait_until": {"field": "cap_seq", "min_value": j, "timeout_frames": 42000},
                      "capture": f"c{j:03d}", "state_capture": f"c{j:03d}"})
    steps.append({"wait_until": {"field": "result", "min_value": 1, "timeout_frames": 42000},
                  "frames": 5, "capture": "zz_final", "state_capture": "final"})
    return {
        "name": name, "description": description, "suite": False, "evidence_only": True,
        "state": {"elf": "../.ds-game-dev/build/out/dungeonds-encuentros-bot.elf",
                  "symbols": {"stats": "g_enc_stats", "dbg": "g_enc_debug", "nav": "g_nav_state"},
                  "default_symbol": "stats", "fields": fields},
        "steps": steps,
        "assertions": {"state_changes": [{"at": "final", "field": "result", "min_value": 1}]},
    }


out = {
    "encuentros_bot_natural": scenario(
        "encuentros_bot_natural",
        "Bot de prueba (variante encuentros-bot) jugando el acto I con la progresion normal: Dones de los relicarios al azar con semilla 1. Corre hasta victoria, muerte o 30000 frames.",
        []),
    "encuentros_bot_sin_mejoras": scenario(
        "encuentros_bot_sin_mejoras",
        "Igual que el natural pero sin coger Dones (g_enc_debug.no_dones): el suelo de dificultad.",
        [{"field": "dbg_no_dones", "value": 1}]),
    "encuentros_bot_fuerte": scenario(
        "encuentros_bot_fuerte",
        "Igual que el natural pero empezando con 10 Dones aplicados (al azar, semilla 1).",
        [{"field": "dbg_start_dones", "value": 10}]),
    "encuentros_bot_natural_torpe": scenario(
        "encuentros_bot_natural_torpe",
        "Natural con el bot torpe: reaccion 30 frames, error de apuntado 12 px, 40 frames hasta ver la mirada del Ojo y 25 % de cargas del Cireneo sin esquivar.",
        [], TORPE),
    "encuentros_bot_sin_mejoras_torpe": scenario(
        "encuentros_bot_sin_mejoras_torpe",
        "Sin Dones con el bot torpe (ver natural_torpe).",
        [{"field": "dbg_no_dones", "value": 1}], TORPE),
}


def gif_pinza():
    """Capturas cada 4 frames del encuentro 8 (pinza, tier media) de la corrida natural, desde que despierta."""
    sc = scenario("encuentros_bot_gif_pinza", "Corrida natural; capturas cada 4 frames desde que despierta el encuentro 8 (pinza media) hasta que se abre la barrera.", [])
    sc["steps"] = [sc["steps"][0],
                   {"wait_until": {"field": "woken", "min_value": 8, "timeout_frames": 42000}, "frames": 0},
                   {"frames": 800, "capture_sequence": "g", "capture_every": 4},
                   {"frames": 2, "state_capture": "final"}]
    sc["assertions"] = {"state_changes": [{"at": "final", "field": "woken", "min_value": 8}]}
    return sc


out["encuentros_bot_gif_pinza"] = gif_pinza()


def jefe_diag():
    """Diagnostico del jefe sin Dones: vida del jefe, impactos y Monaguillos cada 300 frames desde que despierta."""
    sc = scenario("encuentros_bot_jefe_diag", "Sin Dones; desde que despierta el jefe vuelca el estado cada 300 frames (g_enc_stats.boss_*, mona_*).",
                  [{"field": "dbg_no_dones", "value": 1}])
    steps = [sc["steps"][0], {"wait_until": {"field": "woken", "min_value": 13, "timeout_frames": 42000}, "frames": 0}]
    for i in range(32):
        steps.append({"frames": 300, "state_capture": f"b{i:02d}", "capture": f"b{i:02d}"})
    sc["steps"] = steps
    sc["assertions"] = {"state_changes": [{"at": "b31", "field": "woken", "min_value": 13}]}
    return sc


out["encuentros_bot_jefe_diag"] = jefe_diag()
for name, sc in out.items():
    with open(os.path.join(ROOT, "scenarios", name + ".json"), "w", newline="\n") as f:
        json.dump(sc, f, indent=2)
        f.write("\n")
    print(name, len(sc["steps"]), "pasos")
