#!/usr/bin/env python3
"""ARPG balance harness. Writes scenarios for the autopilot of the variant arpg-bot, runs them in parallel on the real ROM
through the skill's scenario runner, and prints the results against the balance targets of DESIGN-ARPG.md ("Objetivos de
balance"), with PASS/FAIL per target. Each batch appends one line to walkthroughs/arpg-bot/balance_log.md.

  python tools/arpg_balance.py                          # default batch (see DEFAULT_CONFIG), jobs 3
  python tools/arpg_balance.py --config mi_prueba.json  # your own batch
  python tools/arpg_balance.py --label "ojo 80%" --set hp_pct.SHOOTER=80 --set ray_cost=15   # quick overrides on the default batch
  python tools/arpg_balance.py --emit-scenarios         # rewrites scenarios/arpg_bot_{torpe,normal,bueno}.json and exits
  python tools/arpg_balance.py --dry                    # writes the scenarios of the batch and prints them, runs nothing

Config (JSON):
  {
    "label": "text for the log",
    "overrides": {                      # runtime balance knobs (struct g_bal, include/arpg_balance.h), written before play
        "hp_pct": {"EXVOTO": 120},      # per enemy type: hp_pct, dmg, xp (names: CHARGER OJO...: see TYPES)
        "ray_cost": 15, "xp_curve_pm": 1450, ...   # scalar knobs: see BAL_SCALARS
        # a knob that is not listed keeps the game's own value (0 = no override); a value of 0 cannot be set (use 1)
    },
    "knobs": {"kite_dist": 60},         # overrides of the bot profile (include/arpg_bot.h ArpgBotDebug), applied after it
    "fast": true,                       # the bot skips the drawing (about 2x faster in the emulator)
    "runs": [
        {"mode": "campaign", "profile": "normal", "seeds": [1]},                 # bajadas + camp + sleep until the boss dies
        {"mode": "bajada", "level": 3, "profile": "normal", "seeds": [1]},       # one bajada at level 3, ends when it retreats or dies
        {"mode": "boss", "level": 5, "profile": "normal", "seeds": [1]}          # same, never retreats (measures the boss)
    ]
  }
Modes: campaign (bot mode 1), bajada (bot mode 2), boss (bot mode 0). Optional per run: "frames" (timeout), "max_bajadas",
"god", "captures" (a capture every N frames, 0 = none), "name".
Test tool: it only reads the stats of the variant arpg-bot (build it first: build-project.ps1 -Variant arpg-bot).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = r"C:\codexlocal\skills\agentic-ds-dev\scripts"
ELF = os.path.join(ROOT, ".ds-game-dev", "build", "out", "dungeonds-arpg-bot.elf").replace("\\", "/")
ROM = os.path.join(ROOT, "dungeonds-arpg-bot.nds")
LOG = os.path.join(ROOT, "walkthroughs", "arpg-bot", "balance_log.md")

PROFILES = {"normal": 0, "torpe": 1, "bueno": 2, "manual": 3}
MODES = {"boss": 0, "campaign": 1, "bajada": 2}
TYPES = {"NONE": 0, "CHARGER": 1, "CIRENEO": 1, "SHOOTER": 2, "OJO": 2, "EXVOTO": 3, "ABANDERADO": 4, "MONAGUILLO": 5,
         "BEBE": 6, "PARROCO": 7, "MONJA": 8, "CAMPANERO": 9}
ROOM_NAMES = ["Nave 1", "Nave 2", "Nave 3", "Nave 4", "Gal cofre", "Gal secreto", "Claustro bajo", "Claustro alto", "Enfermeria", "Osario",
              "Cap parroco", "Gal Misa", "Gal prisionero", "Cap llave", "Gal monjarana", "Cripta"]
DEEP_NAMES = {0: "-", 1: "Nave 1", 2: "Nave 2", 3: "Nave 3", 4: "Nave 4", 5: "Cripta"}
TYPE_NAMES = {v: k for k, v in TYPES.items() if k not in ("CIRENEO", "OJO")}
TYPE_NAMES.update({1: "Cireneo", 2: "Ojo"})
CAUSES = {0: "-", 1: "muere", 2: "vuelve", 3: "jefe", 4: "tiempo"}
RESULTS = {0: "en curso", 1: "jefe vencido", 2: "muerto", 3: "tiempo", 4: "tope de bajadas", 5: "vuelve al campamento"}

# ArpgBalance (include/arpg_balance.h): arrays of 10 u16 by enemy type, then u16 scalars at these offsets.
# Every field is an OVERRIDE: 0 = the game's own value (so an empty override = the shipping numbers).
BAL_ARRAYS = {"hp_pct": 0, "dmg": 20, "xp": 40}
BAL_SCALARS = {"hero_hp_base": 60, "hero_hp_level": 62, "hero_mana_base": 64, "hero_mana_level": 66, "ray_cost": 68,
               "ray_damage": 70, "punch_a": 72, "punch_b": 74, "punch_hook": 76, "remate_hp_chance": 78, "remate_hp": 80,
               "remate_mana_chance": 82, "remate_mana": 84, "xp_curve_pm": 86, "group_pct": 88, "mana_regen_frames": 90,
               "boss_hp_pct0": 92, "heal_pickup": 94, "tier2_hp_pct": 96, "tier2_dmg_pct": 98}
# ArpgBotDebug (include/arpg_bot.h).
DBG = {"profile": (0, "u8"), "reaction": (2, "u8"), "aim_err": (3, "u8"), "miss_pct": (4, "u8"), "remate_miss_pct": (5, "u8"),
       "panic_pct": (6, "u8"), "punch_jitter": (7, "u8"), "seed": (8, "u16"), "timeout_frames": (10, "u16"), "god": (12, "u8"),
       "goal_room": (13, "u8"), "ojo_delay": (14, "u8"), "go": (16, "u8"), "mode": (17, "u8"), "start_level": (18, "u8"),
       "fast": (19, "u8"), "retreat_pct": (20, "u8"), "kite_dist": (21, "u8"), "mana_reserve": (22, "u8"),
       "max_bajadas": (23, "u8"), "campaign_frames": (24, "u32")}

# ArpgBotStats (include/arpg_bot.h): name -> (offset, type)
STATS = {"result": (0, "u8"), "room": (1, "u8"), "rooms_cleared": (2, "u8"), "hp": (3, "u8"), "hp_min": (4, "u8"),
         "max_hp": (5, "u8"), "mana": (6, "u8"), "level": (7, "u8"), "frames": (8, "u32"), "xp": (12, "u16"),
         "death_room": (14, "u8"), "killer": (15, "u8"), "mana_empty_frames": (16, "u16"), "shots": (18, "u16"),
         "punches": (20, "u16"), "remates_done": (22, "u16"), "remates_missed": (24, "u16"), "orbs": (26, "u16"),
         "stuck_events": (28, "u16"), "kills": (30, "u16"), "rule": (32, "u8"), "awake": (33, "u8"),
         "hero_x": (34, "s16"), "hero_y": (36, "s16"), "goal_x": (38, "s16"), "goal_y": (40, "s16"),
         "give_ups": (42, "u16"), "damage_total": (44, "u16"), "hits": (46, "u16"), "visited": (144, "u16"),
         "max_alive": (164, "u8"), "near_type": (166, "u8"), "near_state": (167, "u8"), "max_awake": (165, "u8"), "bajadas": (168, "u8"), "boss_result": (169, "u8"), "max_level": (170, "u8"), "phase": (171, "u8"),
         "dungeon_frames": (172, "u32"), "camp_frames": (176, "u32"), "mana_spent": (180, "u32"), "screens": (184, "u32"),
         "first_visit_frames": (448, "u32"), "repeat_frames": (452, "u32"), "rooms_seen": (456, "u16"), "script_skips": (458, "u16")}
for _i in range(16):
    STATS["bf%d" % _i] = (188 + 4 * _i, "u32")          # frames of each bajada
    STATS["rf%d" % _i] = (252 + 4 * _i, "u32")          # frames in each room (all bajadas)
    STATS["bd%d" % _i] = (316 + 2 * _i, "u16")          # life lost in each bajada
    STATS["bp%d" % _i] = (348 + _i, "u8")               # deepest room of each bajada
    STATS["bl%d" % _i] = (364 + _i, "u8")               # level at the start of each bajada
    STATS["bc%d" % _i] = (380 + _i, "u8")               # cause of the end of each bajada
    STATS["bs%d" % _i] = (396 + _i, "u8")               # screens of each bajada
    STATS["rs%d" % _i] = (412 + _i, "u8")               # screens in each room
    STATS["rd%d" % _i] = (80 + 2 * _i, "u16")           # life lost in each room
for _i in range(8):
    STATS["lm%d" % _i] = (428 + 2 * _i, "u16")          # game second in which level 2..9 was reached
for _i in range(9):
    STATS["dt%d" % _i] = (146 + 2 * _i, "u16")          # life lost per enemy type

DEFAULT_CONFIG = {
    "label": "base",
    "overrides": {},
    "knobs": {},
    "fast": True,
    "runs": [
        {"mode": "campaign", "profile": "normal", "seeds": [1]},
        {"mode": "bajada", "level": 1, "profile": "normal", "seeds": [1]},
        {"mode": "bajada", "level": 3, "profile": "normal", "seeds": [1]},
        {"mode": "boss", "level": 5, "profile": "normal", "seeds": [1]},
    ],
}

# Targets: DESIGN-ARPG.md, "Objetivos de balance". (low, high) in the unit of each row.
T_ZONE = (60, 75)          # minutes: whole zone 1, first time, normal profile (user, 2026-11-24: includes re-crossing cleared rooms)
T_BAJADAS = (3, 4)         # bajadas of that campaign
T_BAJADA_MIN = (10, 20)    # minutes of one bajada
T_PACE = (12, 25)          # seconds per screen (user, 2026-11-24, after watching the bot video: ~18 s is the right pace)
T_REACH_L1 = 2             # level 1 reaches up to Nave 2
T_REACH_L3 = 4             # level 3 reaches up to Nave 4
T_BOSS_L5 = 50             # % of the seeds in which level 5 beats the boss
T_TORPE_X = (1.5, 2.0)     # torpe time / normal time
T_BUENO_MIN = (30, 40)     # minutes: whole zone, bueno profile
ZONE_SCREENS = 70          # screens of the whole zone 1 (the bot explores the side rooms too; main path = 26)
MAIN_SCREENS = 26


def seen_count(s):
    return bin(s["rooms_seen"]).count("1")


def repeat_pct(s):
    tot = s["first_visit_frames"] + s["repeat_frames"]
    return 100.0 * s["repeat_frames"] / tot if tot else 0.0


def poke(symbol, offset, typ, value):
    return {"symbol": symbol, "offset": offset, "type": typ, "value": int(value)}


def bal_pokes(overrides):
    out = []
    for key, val in overrides.items():
        if key in BAL_ARRAYS:
            for tname, v in val.items():
                t = TYPES[tname.upper()] if not str(tname).isdigit() else int(tname)
                out.append(poke("bal", BAL_ARRAYS[key] + 2 * t, "u16", v))
        elif key in BAL_SCALARS:
            out.append(poke("bal", BAL_SCALARS[key], "u16", val))
        else:
            raise SystemExit("unknown balance knob %r (arrays %s, scalars %s)" % (key, sorted(BAL_ARRAYS), sorted(BAL_SCALARS)))
    return out


def make_scenario(name, run, seed, cfg):
    mode = MODES[run["mode"]]
    frames = int(run.get("frames") or (324000 if mode == 1 else 36000))
    dbg_a = [poke("dbg", *DBG["profile"][:1], "u8", PROFILES[run.get("profile", "normal")]),
             poke("dbg", DBG["seed"][0], "u16", seed)]
    dbg_b = []
    for k, v in cfg.get("knobs", {}).items():
        dbg_b.append(poke("dbg", DBG[k][0], DBG[k][1], v))
    for k, v in run.get("knobs", {}).items():
        dbg_b.append(poke("dbg", DBG[k][0], DBG[k][1], v))
    dbg_b += [poke("dbg", DBG["mode"][0], "u8", mode),
              poke("dbg", DBG["start_level"][0], "u8", run.get("level", 1)),
              poke("dbg", DBG["fast"][0], "u8", 1 if (cfg.get("fast", True) and not run.get("captures")) else 0)]
    if mode == 1:
        dbg_b.append(poke("dbg", DBG["campaign_frames"][0], "u32", frames))
        if run.get("max_bajadas"):
            dbg_b.append(poke("dbg", DBG["max_bajadas"][0], "u8", run["max_bajadas"]))
    else:
        dbg_b.append(poke("dbg", DBG["timeout_frames"][0], "u16", min(frames, 65535)))
    if run.get("start_room") is not None:                  # debug: start the bajada in this room id (11 = Cripta) at full life
        dbg_b.append(poke("enc", 20, "u8", int(run["start_room"]) + 1))
    if run.get("god"):
        dbg_b.append(poke("dbg", DBG["god"][0], "u8", 1))
    go = poke("dbg", DBG["go"][0], "u8", 1)
    wait = {"field": "result", "min_value": 1, "timeout_frames": frames + frames // 8 + 1200}      # the bot clock lags the emulator a little (fades, hit stop)
    step_wait = {"wait_until": wait}
    if run.get("captures"):
        step_wait["capture_sequence"] = name
        step_wait["capture_every"] = int(run["captures"])
    fields = {n: {"symbol": "stats", "offset": o, "type": t} for n, (o, t) in STATS.items()}
    return {
        "name": name,
        "description": "Autopilot del ARPG (variante arpg-bot): %s, perfil %s, nivel %d, semilla %d. Generado por tools/arpg_balance.py."
                       % (run["mode"], run.get("profile", "normal"), run.get("level", 1), seed),
        "suite": False,
        "evidence_only": True,
        "state": {"elf": ELF, "symbols": {"stats": "g_arpg_bot_stats", "dbg": "g_arpg_bot_debug", "bal": "g_bal", "enc": "g_enc_debug"},
                  "default_symbol": "stats", "fields": fields},
        "steps": [{"frames": 30},
                  {"poke": dbg_a, "frames": 4},
                  {"poke": bal_pokes(cfg.get("overrides", {})) + dbg_b + [go], "frames": 2},
                  step_wait,
                  {"frames": 30, "state_capture": "end"}],
    }


def run_name(run, seed, idx):
    if run.get("name"):
        return "%s_s%d" % (run["name"], seed)
    lvl = "_n%d" % run["level"] if run.get("level", 1) > 1 or run["mode"] != "campaign" else ""
    return "r%d_%s_%s%s_s%d" % (idx, run["mode"], run.get("profile", "normal"), lvl, seed)


def read_stats(out_dir):
    for dirpath, _, files in os.walk(out_dir):
        for fn in sorted(files):
            if fn.endswith(".json") and fn != "scenario.json":
                try:
                    data = json.load(open(os.path.join(dirpath, fn), encoding="utf-8"))
                except Exception:
                    continue
                found = find_sample(data)
                if found:
                    return found
    return None


def find_sample(node):
    if isinstance(node, dict):
        if isinstance(node.get("frames"), int) and "result" in node and "bajadas" in node:
            return node
        for v in node.values():
            r = find_sample(v)
            if r:
                return r
    elif isinstance(node, list):
        for v in node:
            r = find_sample(v)
            if r:
                return r
    return None


def execute(job):
    name, scen, out_dir = job["name"], job["scenario"], job["out"]
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "scenario_%s.json" % name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scen, f)
    t0 = time.time()
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", os.path.join(SKILL, "run-scenario.ps1"),
           "-ScenarioPath", path, "-ProjectPath", ROOT, "-RomPath", ROM, "-OutputPath", out_dir]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.time() - t0
    m = re.search(r"wall_ms=(\d+)", proc.stdout or "")
    emu_frames = re.search(r"frames=(\d+)", proc.stdout or "")
    return {"job": job, "stats": read_stats(out_dir), "wall_s": wall, "emu_wall_s": int(m.group(1)) / 1000.0 if m else None,
            "emu_frames": int(emu_frames.group(1)) if emu_frames else None, "tail": (proc.stdout or "")[-400:]}


# ---------------------------------------------------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------------------------------------------------
def mean(xs):
    return sum(xs) / len(xs) if xs else None


def verdict(value, low=None, high=None):
    if value is None:
        return "SIN DATOS"
    if low is not None and value < low:
        return "FAIL (bajo)"
    if high is not None and value > high:
        return "FAIL (alto)"
    return "PASS"


def fmt(x, nd=1):
    return "-" if x is None else ("%.*f" % (nd, x))


def evaluate(results):
    """results: list of {job, stats, ...}. Returns the rows of the targets table and the detail lines."""
    groups = {}
    for r in results:
        j = r["job"]
        if r["stats"]:
            groups.setdefault((j["mode"], j["profile"], j["level"]), []).append(r["stats"])
    rows, notes = [], []

    camp = {p: groups.get(("campaign", p, 1)) for p in ("normal", "torpe", "bueno")}
    # pace: seconds per screen walked inside the cathedral
    paces = {}
    for p, lst in camp.items():
        if lst:
            paces[p] = mean([s["dungeon_frames"] / 60.0 / s["screens"] for s in lst if s["screens"] > 0])
    normal = camp["normal"]
    if normal:
        pace = paces.get("normal")
        rows.append(("Ritmo (s por pantalla, normal)", "%d-%d" % T_PACE, fmt(pace), verdict(pace, *T_PACE)))
        done = [s for s in normal if s["result"] == 1]
        minutes = mean([s["frames"] / 3600.0 for s in normal])
        # whole zone = what the bot played (main path) + the 20 screens of the side rooms at the same pace
        est = None
        if pace is not None and done:
            est = mean([s["frames"] / 3600.0 for s in done])
            if min(seen_count(s) for s in done) < 15:         # side rooms skipped: add them at the same pace
                est += (ZONE_SCREENS - MAIN_SCREENS) * pace / 60.0
        rows.append(("Zona 1 entera, 1a vez (min)", "%d-%d" % T_ZONE, fmt(est), verdict(est, *T_ZONE) if done else "SIN DATOS (no vence al jefe)"))
        rows.append(("  salas vistas (de 16)", "16", fmt(mean([seen_count(s) for s in normal]), 1), "info"))
        rows.append(("  tiempo en salas ya despejadas (%)", "-", fmt(mean([repeat_pct(s) for s in normal])), "info"))
        rows.append(("  tiempo total medido (min)", "-", fmt(minutes) + (" (jefe vencido)" if done else " (sin jefe: %s)" % ", ".join(RESULTS.get(s["result"], "?") for s in normal)), "info"))
        nb = mean([s["bajadas"] for s in normal])
        rows.append(("Bajadas de la campaña", "%d-%d" % T_BAJADAS, fmt(nb), verdict(nb, *T_BAJADAS)))
        bm = []
        for s in normal:
            for b in range(min(s["bajadas"], 16)):
                bm.append(s["bf%d" % b] / 3600.0)
        rows.append(("Una bajada (min, media)", "%d-%d" % T_BAJADA_MIN, fmt(mean(bm)), verdict(mean(bm), *T_BAJADA_MIN)))
        for s in normal:
            lv = [("N%d=%ds" % (i + 2, s["lm%d" % i])) for i in range(8) if s["lm%d" % i] > 0]
            notes.append("campaña normal: %.1f min en total, %.0f%% en salas ya despejadas, salas vistas %d/16; nivel final %d (%s); %d bajadas: %s" % (
                s["frames"] / 3600.0, repeat_pct(s), seen_count(s), s["max_level"], " ".join(lv) or "sin subidas",
                s["bajadas"], "; ".join("%s niv%d %s %.0fmin dmg%d" % (DEEP_NAMES.get(s["bp%d" % b], "?"), s["bl%d" % b], CAUSES.get(s["bc%d" % b], "?"),
                                                             s["bf%d" % b] / 3600.0, s["bd%d" % b]) for b in range(min(s["bajadas"], 16)))))
    if camp["torpe"] and normal:
        t = mean([s["frames"] / 3600.0 for s in camp["torpe"]])
        n = mean([s["frames"] / 3600.0 for s in normal])
        ok = all(s["result"] == 1 for s in camp["torpe"])
        rows.append(("Torpe / normal (x tiempo)", "%.1f-%.1f" % T_TORPE_X, fmt(t / n, 2) + ("" if ok else " (no completa)"),
                     verdict(t / n, *T_TORPE_X) if ok else "FAIL (no completa)"))
    if camp["bueno"]:
        done = [s for s in camp["bueno"] if s["result"] == 1]
        pace = paces.get("bueno")
        est = (mean([s["frames"] / 3600.0 for s in done]) + (ZONE_SCREENS - MAIN_SCREENS) * pace / 60.0) if (done and pace) else None
        rows.append(("Bueno, zona entera (min, estimado)", "%d-%d" % T_BUENO_MIN, fmt(est), verdict(est, *T_BUENO_MIN) if done else "SIN DATOS (no vence al jefe)"))

    for lvl, target in ((1, T_REACH_L1), (3, T_REACH_L3)):
        lst = groups.get(("bajada", "normal", lvl))
        if lst:
            deep = mean([s["bp0"] for s in lst])
            rows.append(("Nivel %d: llega hasta (sala)" % lvl, DEEP_NAMES[target], "%s (%s)" % (fmt(deep), ", ".join(DEEP_NAMES.get(s["bp0"], "?") for s in lst)),
                         verdict(deep, target - 0.5, target + 0.5)))
            for s in lst:
                notes.append("nivel %d: %s tras %.1f min, vida min %d/%d, %d pantallas, %s" % (
                    lvl, RESULTS.get(s["result"], "?"), s["frames"] / 3600.0, s["hp_min"], s["max_hp"], s["screens"],
                    "muere en " + (ROOM_NAMES[s["death_room"]] if s["death_room"] < len(ROOM_NAMES) else "?") if s["result"] == 2 else "se retira en " + DEEP_NAMES.get(s["bp0"], "?")))
    lst = groups.get(("boss", "normal", 5))
    if lst:
        wins = 100.0 * sum(1 for s in lst if s["boss_result"] == 1) / len(lst)
        rows.append(("Nivel 5: vence al jefe (% semillas)", ">=%d" % T_BOSS_L5, "%s (%d sem.)" % (fmt(wins, 0), len(lst)), verdict(wins, T_BOSS_L5)))
        for s in lst:
            notes.append("nivel 5 al jefe: %s en %s tras %.1f min (vida min %d/%d)" % (
                RESULTS.get(s["result"], "?"), ROOM_NAMES[s["room"]] if s["room"] < len(ROOM_NAMES) else "?", s["frames"] / 3600.0, s["hp_min"], s["max_hp"]))
    for r in results:                       # per pass: damage per room, pace per room, deaths and killer, level-up minutes
        st, j = r["stats"], r["job"]
        if not st:
            continue
        dmg = ", ".join("%s %d" % (ROOM_NAMES[i], st["rd%d" % i]) for i in range(16) if st["rd%d" % i])
        pace = ", ".join("%s %.0f" % (ROOM_NAMES[i], st["rf%d" % i] / 60.0 / st["rs%d" % i]) for i in range(16) if st["rs%d" % i] > 0 and st["rf%d" % i])
        killer = TYPE_NAMES.get(st["killer"], "?")
        lv = " ".join("N%d=%.1fmin" % (i + 2, st["lm%d" % i] / 60.0) for i in range(8) if st["lm%d" % i] > 0)
        notes.append("[%s] dano por sala: %s | s por pantalla por sala: %s | %s | niveles: %s" % (
            j["name"], dmg or "-", pace or "-",
            ("muere en %s (ultimo golpe: %s)" % (ROOM_NAMES[st["death_room"]] if st["death_room"] < 16 else "?", killer)) if st["death_room"] < 16 else "sin muertes",
            lv or "-"))
        if j["mode"] == "campaign":
            notes.append("[%s] tiempo total %.1f min (dentro %.1f, campamento %.1f); primera vez %.1f min, repetido %.1f min (%.0f%%); salas vistas %d/16; pasos del guion saltados %d; muertes en: %s" % (
                j["name"], st["frames"] / 3600.0, st["dungeon_frames"] / 3600.0, st["camp_frames"] / 3600.0, st["first_visit_frames"] / 3600.0,
                st["repeat_frames"] / 3600.0, repeat_pct(st), seen_count(st), st["script_skips"], ROOM_NAMES[st["death_room"]] if st["death_room"] < 16 else "-"))
        if st["screens"] > 0:
            notes.append("[%s] %.1f s por pantalla (dentro de la catedral), %d pantallas, %d bajadas, dano total %d, golpes %d, kills %d" % (
                j["name"], st["dungeon_frames"] / 60.0 / st["screens"], st["screens"], st["bajadas"], st["damage_total"], st["hits"], st["kills"]))
    return rows, notes


def print_table(rows):
    w0 = max([len(r[0]) for r in rows] + [10])
    print("%-*s  %-10s  %-26s  %s" % (w0, "objetivo", "meta", "medido", "veredicto"))
    for r in rows:
        print("%-*s  %-10s  %-26s  %s" % (w0, r[0], r[1], r[2], r[3]))


def append_log(cfg, rows, results, wall):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new = not os.path.exists(LOG)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ov = json.dumps(cfg.get("overrides", {}), separators=(",", ":")) if cfg.get("overrides") else "sin cambios"
    kn = json.dumps(cfg.get("knobs", {}), separators=(",", ":")) if cfg.get("knobs") else ""
    res = "; ".join("%s: %s [%s]" % (r[0].strip(), r[2], r[3]) for r in rows if r[3] != "info")
    camp = [r["stats"] for r in results if r["stats"] and r["job"]["mode"] == "campaign"]
    if camp:
        res += " | campana: " + "; ".join("%.1f min en total, %.0f%% en salas ya despejadas, salas vistas %d/16, resultado %s" % (
            c["frames"] / 3600.0, repeat_pct(c), seen_count(c), RESULTS.get(c["result"], "?")) for c in camp)
    runs = ", ".join("%s %s n%d x%d" % (r["mode"], r.get("profile", "normal"), r.get("level", 1), len(r["seeds"])) for r in cfg["runs"])
    with open(LOG, "a", encoding="utf-8") as f:
        if new:
            f.write("# Registro de lotes de balance (tools/arpg_balance.py)\n\nUna linea por lote: fecha, etiqueta, cambios sobre los valores por defecto, "
                    "perfil del bot, pasadas y resultados contra los objetivos de DESIGN-ARPG.md.\n\n")
        f.write("- %s | %s | cambios: %s%s | pasadas: %s | %.0f s de reloj | %s\n" % (now, cfg.get("label", ""), ov, (" | bot: " + kn) if kn else "", runs, wall, res))


def apply_sets(cfg, sets):
    for s in sets or []:
        key, val = s.split("=", 1)
        val = int(val)
        if "." in key:
            arr, t = key.split(".", 1)
            cfg.setdefault("overrides", {}).setdefault(arr, {})[t] = val
        else:
            cfg.setdefault("overrides", {})[key] = val


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="JSON of the batch (see the top of this file); default: DEFAULT_CONFIG")
    ap.add_argument("--label", help="label of the batch for the log")
    ap.add_argument("--set", action="append", help="balance override, e.g. hp_pct.SHOOTER=80 or ray_cost=15 (repeatable)")
    ap.add_argument("--jobs", type=int, default=3, help="emulators in parallel (default 3)")
    ap.add_argument("--out", help="folder of the runs (default build/balance/<timestamp>)")
    ap.add_argument("--dry", action="store_true", help="write the scenarios and run nothing")
    ap.add_argument("--no-log", action="store_true", help="do not append to balance_log.md")
    ap.add_argument("--emit-scenarios", action="store_true", help="write scenarios/arpg_bot_{torpe,normal,bueno}.json and exit")
    args = ap.parse_args()

    if args.emit_scenarios:
        for p in ("torpe", "normal", "bueno"):
            run = {"mode": "boss", "profile": p, "level": 1, "frames": 36000, "captures": 1800}
            scen = make_scenario("arpg_bot_%s" % p, run, 1, {"fast": False})
            scen["description"] = ("Autopilot del ARPG (variante arpg-bot), perfil %s, semilla 1, nivel 1: una bajada sin retirada hasta vencer al jefe, "
                                   "morir o 36000 frames; capturas cada 1800 frames y estadisticas al final." % p)
            scen["state"]["elf"] = "../.ds-game-dev/build/out/dungeonds-arpg-bot.elf"
            with open(os.path.join(ROOT, "scenarios", "arpg_bot_%s.json" % p), "w", encoding="utf-8") as f:
                json.dump(scen, f, indent=2)
                f.write("\n")
            print("escrito scenarios/arpg_bot_%s.json" % p)
        return 0

    cfg = json.load(open(args.config, encoding="utf-8")) if args.config else json.loads(json.dumps(DEFAULT_CONFIG))
    if args.label:
        cfg["label"] = args.label
    apply_sets(cfg, args.set)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(ROOT, "build", "balance", stamp)
    jobs = []
    for idx, run in enumerate(cfg["runs"]):
        for seed in run["seeds"]:
            name = run_name(run, seed, idx)
            jdir = os.path.abspath(os.path.join(out, name))
            scen = make_scenario(name, run, seed, cfg)
            scen["state"]["elf"] = os.path.relpath(ELF, jdir).replace("\\", "/")      # the runner resolves it from the scenario folder
            jobs.append({"name": name, "mode": run["mode"], "profile": run.get("profile", "normal"), "level": run.get("level", 1),
                         "seed": seed, "scenario": scen, "out": jdir})
    if args.dry:
        for j in jobs:
            os.makedirs(j["out"], exist_ok=True)
            p = os.path.join(j["out"], "scenario_%s.json" % j["name"])
            with open(p, "w", encoding="utf-8") as f:
                json.dump(j["scenario"], f, indent=1)
            print("escrito", p)
        return 0

    print("lote %r: %d pasadas, %d en paralelo, salida %s" % (cfg.get("label", ""), len(jobs), args.jobs, out), flush=True)
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(execute, jobs):
            results.append(r)
            j, s = r["job"], r["stats"]
            if s:
                fps = (s["frames"] / r["wall_s"]) if r["wall_s"] > 0 else 0
                print("  %-28s %-13s %5.1f min de juego en %5.0f s de reloj (%4.0f fps) bajadas=%d nivel=%d" % (
                    j["name"], RESULTS.get(s["result"], "?"), s["frames"] / 3600.0, r["wall_s"], fps, s["bajadas"], s["level"]), flush=True)
            else:
                print("  %-28s SIN DATOS (la pasada fallo): %s" % (j["name"], r["tail"].strip().replace("\n", " | ")), flush=True)
    wall = time.time() - t0
    rows, notes = evaluate(results)
    print()
    print_table(rows)
    if notes:
        print()
        for n in notes:
            print("  " + n)
    print("\nreloj total del lote: %.0f s" % wall)
    if not args.no_log and rows:
        append_log(cfg, rows, results, wall)
        print("anotado en", os.path.relpath(LOG, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
