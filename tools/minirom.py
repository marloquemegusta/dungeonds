#!/usr/bin/env python3
"""Mini ROM: minirom/<nombre>.json -> a ROM that boots straight into one encounter (TECHNICAL.md 3.6c).

    python tools/minirom.py minirom/abanderado.json [--solo-compilar]

Validates the JSON, writes include/minirom_gen/<nombre>.h and scenarios/minirom_<nombre>.json, records which nitrofiles/
the scenario opens (build-partial-rom.ps1 -Record), adds extra_archivos/animaciones to that contract and verifies the
partial ROM. Never uploads: prints the command. Needs the skill with -Define/-WriteContract (DS_SKILL_DIR).
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SKILL = r"C:\codexlocal\skills\agentic-ds-dev"
DEV_SKILL = r"C:\codexlocal\skills\agentic-ds-dev-minirom"

DEFAULTS = {
    "enemigos": "como_en_el_juego",
    "heroe": {"equipo": "todo", "mecanicas": []},
    "pruebas": {"invulnerable": False, "enemigos_inmortales": False, "reaparecen": False, "vida_jefe": 0},
    "depuracion": [],
    "animaciones": "auto",
    "extra_archivos": [],
}


def fail(msg):
    print("MINIROM=FAIL " + msg)
    sys.exit(1)


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as f:
        return f.read()


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def enum_names(prefix):
    return set(re.findall(r"\b(%s[A-Z0-9_]+)\b" % prefix, read("include/encounters_act1.h")))


def check_type(d, key, kind, where):
    if not isinstance(d.get(key), kind) or (kind is int and isinstance(d.get(key), bool)):
        fail("%s.%s debe ser %s" % (where, key, kind.__name__))


def validate(spec):
    for k in ("nombre", "sala"):
        if not isinstance(spec.get(k), str) or not spec[k]:
            fail("falta '%s' (texto)" % k)
    if not re.fullmatch(r"[a-z0-9_-]+", spec["nombre"]):
        fail("'nombre' solo admite a-z 0-9 _ -")
    unknown = set(spec) - set(DEFAULTS) - {"nombre", "sala"}
    if unknown:
        fail("campos desconocidos: " + ", ".join(sorted(unknown)))
    for k, v in DEFAULTS.items():
        spec.setdefault(k, json.loads(json.dumps(v)))
    for k in ("heroe", "pruebas"):
        if not isinstance(spec[k], dict):
            fail("'%s' debe ser un objeto" % k)
        extra = set(spec[k]) - set(DEFAULTS[k])
        if extra:
            fail("%s: campos desconocidos %s" % (k, sorted(extra)))
        for kk, vv in DEFAULTS[k].items():
            spec[k].setdefault(kk, vv)
    h, p = spec["heroe"], spec["pruebas"]
    if h["equipo"] not in ("inicial", "todo"):
        fail("heroe.equipo: 'inicial' o 'todo'")
    mechs = set(re.findall(r"#define ARPG_MECH_([A-Z0-9_]+)\s+\d+", read("include/arpg_inv.h"))) - {"NONE", "COUNT"}
    if not isinstance(h["mecanicas"], list):
        fail("heroe.mecanicas debe ser una lista")
    for m in h["mecanicas"]:
        if not isinstance(m, str) or m.upper() not in mechs:
            fail("mecanica desconocida %r (validas: %s)" % (m, ", ".join(sorted(mechs))))
    for k in ("invulnerable", "enemigos_inmortales", "reaparecen"):
        check_type(p, k, bool, "pruebas")
    check_type(p, "vida_jefe", int, "pruebas")
    if p["vida_jefe"] < 0:
        fail("pruebas.vida_jefe no puede ser negativo")
    en = spec["enemigos"]
    types, states = enum_names("ENC_E_"), enum_names("ENC_S_")
    if en != "como_en_el_juego":
        if not isinstance(en, list):
            fail("'enemigos': \"como_en_el_juego\" o una lista")
        for i, e in enumerate(en):
            if not isinstance(e, dict) or not {"tipo", "dx", "dy"} <= set(e) or set(e) - {"tipo", "dx", "dy", "estado"}:
                fail("enemigos[%d]: campos tipo, dx, dy y estado (opcional)" % i)
            if "ENC_E_" + str(e["tipo"]).upper() not in types:
                fail("enemigos[%d].tipo %r: no existe ENC_E_%s (validos: %s)" % (
                    i, e["tipo"], str(e["tipo"]).upper(), ", ".join(sorted(t[6:].lower() for t in types))))
            e.setdefault("estado", "awake")
            if "ENC_S_" + str(e["estado"]).upper() not in states:
                fail("enemigos[%d].estado %r (validos: %s)" % (i, e["estado"], ", ".join(sorted(s[6:].lower() for s in states))))
            if not all(isinstance(e[k], int) and not isinstance(e[k], bool) for k in ("dx", "dy")):
                fail("enemigos[%d]: dx/dy enteros" % i)
        if len(en) > 16:
            fail("maximo 16 enemigos en la lista")
    for k in ("depuracion", "extra_archivos"):
        if not isinstance(spec[k], list) or not all(isinstance(x, str) for x in spec[k]):
            fail("'%s' debe ser una lista de textos" % k)
    if spec["animaciones"] != "auto" and not (isinstance(spec["animaciones"], list) and all(isinstance(x, str) for x in spec["animaciones"])):
        fail("'animaciones': \"auto\" o lista de rutas de nitrofiles/")
    for x in spec["extra_archivos"] + (spec["animaciones"] if isinstance(spec["animaciones"], list) else []):
        if not os.path.exists(os.path.join(ROOT, "nitrofiles", x.rstrip("/"))) and "*" not in x:
            fail("no existe nitrofiles/" + x)
    return spec


def spec_ident(name):
    return name.replace("-", "_")


def c_bool(v):
    return "1" if v else "0"


def gen_header(spec):
    h, p, en = spec["heroe"], spec["pruebas"], spec["enemigos"]
    pruebas = spec["sala"].lower() == "pruebas"
    lines = [
        "// GENERADO por tools/minirom.py desde minirom/%s.json. No editar." % spec["nombre"],
        "#define MR_SALA_PRUEBAS %s" % c_bool(pruebas),
        '#define MR_SALA "%s"' % ("" if pruebas else spec["sala"].replace("\\", "\\\\").replace('"', '\\"')),
        "#define MR_EQUIPO_TODO %s" % c_bool(h["equipo"] == "todo"),
        "#define MR_INVULNERABLE %s" % c_bool(p["invulnerable"]),
        "#define MR_INMORTALES %s" % c_bool(p["enemigos_inmortales"]),
        "#define MR_REAPARECEN %s" % c_bool(p["reaparecen"]),
        "#define MR_VIDA_JEFE %d" % p["vida_jefe"],
    ]
    mech = ["ARPG_MECH_" + m.upper() for m in h["mecanicas"]]
    lines.append("#define MR_N_MECANICAS %d" % len(mech))
    lines.append("static const uint8_t MR_MECANICAS[] = { %s };" % ", ".join(mech or ["0"]))
    items = []
    if en != "como_en_el_juego":
        items = ["{ ENC_E_%s, ENC_S_%s, %d, %d }" % (e["tipo"].upper(), e["estado"].upper(), e["dx"], e["dy"]) for e in en]
    lines.append("#define MR_N_ENEMIGOS %d" % len(items))
    lines.append("static const MiniromEnemy MR_ENEMIGOS[] = { %s };" % ", ".join(items or ["{ 0, 0, 0, 0 }"]))
    return "\n".join(lines) + "\n"


def gen_scenario(spec):
    n, p, en = spec["nombre"], spec["pruebas"], spec["enemigos"]
    listed = en != "como_en_el_juego"
    sym = {"dbg": "g_minirom_dbg", "gps": "g_player_state", "en": "g_enemies"}
    fields = {
        "room": {"offset": 0, "type": "s16"}, "enemies": {"offset": 2, "type": "s16"},
        "enemy_hp": {"offset": 4, "type": "s32"}, "restarts": {"offset": 12, "type": "u16"},
        "error": {"offset": 14, "type": "u8"}, "room_ok": {"offset": 15, "type": "u8"},
        "frames": {"offset": 20, "type": "u32"}, "boss_hp": {"offset": 16, "type": "s32"}, "frozen": {"offset": 24, "type": "u8"},
        "hero_hp": {"symbol": "gps", "offset": 0, "type": "s32"},
        "tp_boss": {"offset": 25, "type": "u8"}, "hero_x": {"offset": 68, "type": "s16"}, "hero_y": {"offset": 70, "type": "s16"},
    }
    # Walk towards the first listed enemy (screen dy < 0 is north); towards the north otherwise.
    for i in range(min(4, len(en)) if listed else 0):
        for k, off, t in (("x", 0, "s16"), ("y", 2, "s16"), ("alive", 5, "u8"), ("drift", 6, "s16"), ("shift", 8, "s16")):
            fields["e%d_%s" % (i, k)] = {"offset": 28 + 10 * i + off, "type": t}
    key = "UP"
    if listed and en:
        dx, dy = en[0]["dx"], en[0]["dy"]
        key = ("UP" if dy < 0 else "DOWN") if abs(dy) >= abs(dx) else ("LEFT" if dx < 0 else "RIGHT")
    steps = [{"wait_until": {"field": "frames", "min_value": 12, "timeout_frames": 900}, "capture": "00a_colocados", "state_capture": "00a_colocados"},
             {"wait_until": {"field": "frames", "min_value": 150, "timeout_frames": 900}, "capture": "00_arranque", "state_capture": "00_arranque"},
             {"button_down": key, "frames": 150 if not listed else 40, "capture": "01_andando", "state_capture": "01_andando"},
             {"frames": 5, "wait_until": {"field": "frozen", "equals": 0, "timeout_frames": 1500}},     # boss intro
             {"frames": 200 if not listed else 60, "capture": "02_cerca", "state_capture": "02_cerca"},
             {"poke": [{"field": "tp_boss", "value": 1}], "frames": 20},        # next to the boss, if the room has one
             {"button_up": key, "frames": 30, "capture": "03_junto", "state_capture": "03_junto"}]
    for i in range(14):                                               # basic attack: L
        steps.append({"button_down": "L", "frames": 2})
        steps.append({"button_up": "L", "frames": 14})
    tx, ty = {"UP": (128, 40), "DOWN": (128, 150), "LEFT": (30, 100), "RIGHT": (226, 100)}[key]
    for i in range(4):                                       # Rayo: hold the stylus towards the enemy, release to fire
        steps.append({"touch": {"x": tx, "y": ty}, "frames": 60})
        steps.append({"release": True, "frames": 20})
    if p["reaparecen"] and listed:        # kill the listed enemies by emptying their life (slots 0..n-1 after a fresh start)
        steps.append({"poke": [{"symbol": "en", "offset": 124 * i + 28, "type": "s32", "value": 0} for i in range(len(en))], "frames": 30})
    steps.append({"frames": 20, "capture": "04_golpes", "state_capture": "04_golpes"})
    if p["reaparecen"] and listed:
        steps.append({"frames": 5, "wait_until": {"field": "enemies", "equals": len(en), "timeout_frames": 1500},      # 120 game frames after each death
                      "capture": "05_reaparecen", "state_capture": "05_reaparecen"})
    steps.append({"poke": [{"field": "hero_hp", "value": 0}], "frames": 60, "capture": "06_muerte", "state_capture": "06_muerte"})
    steps.append({"frames": 5, "wait_until": {"field": "restarts", "min_value": 1, "timeout_frames": 900}})     # the room restarts by itself
    steps.append({"frames": 120, "capture": "07_reinicio", "state_capture": "07_reinicio"})
    early = []
    for i in range(min(4, len(en)) if listed else 0):
        early += [{"at": "00a_colocados", "field": "e%d_alive" % i, "equals": 1},
                  {"at": "00a_colocados", "field": "e%d_shift" % i, "max_value": 24},    # free spot near the requested one
                  {"at": "00a_colocados", "field": "e%d_drift" % i, "max_value": 24}]    # has not wandered off yet
    changes = early + [
        {"at": "00_arranque", "field": "error", "equals": 0},
        {"at": "00_arranque", "field": "room_ok", "equals": 1},
        {"at": "00_arranque", "field": "enemies", "equals": len(en)} if listed else
        {"at": "00_arranque", "field": "enemies", "min_value": 1},
        {"from": "00_arranque", "to": "04_golpes", "field": "enemy_hp", "max_delta": -1},
        {"at": "07_reinicio", "field": "room_ok", "equals": 1},
        {"at": "07_reinicio", "field": "restarts", "min_value": 1},
    ]
    # Boss rooms (the Cripta, or a listed Abanderado/Campanero): the boss itself must lose life (the scenario stands next to it).
    boss = spec["sala"].lower() == "cripta" or (listed and any(e["tipo"].lower() in ("abanderado", "campanero") for e in en))
    if boss:
        changes.append({"at": "00_arranque", "field": "boss_hp", "min_value": 1})
        changes.append({"from": "00_arranque", "to": "04_golpes", "field": "boss_hp", "max_delta": -1})
    if p["reaparecen"] and listed:
        changes.append({"at": "04_golpes", "field": "enemies", "max_value": len(en) - 1})       # something died first
        changes.append({"at": "05_reaparecen", "field": "enemies", "equals": len(en)})
    return {
        "name": "minirom_" + n,
        "description": "Mini ROM %s: arranca en %s, anda hacia el enemigo, pega (L), muere (hp a 0) y reaparece en la misma sala." % (n, spec["sala"]),
        "suite": False,
        "state": {"elf": "../.ds-game-dev/build/out/dungeonds-mini-%s.elf" % n, "symbols": sym, "default_symbol": "dbg", "fields": fields},
        "steps": steps,
        "assertions": {
            "screen_changes": [{"from": "00_arranque", "to": "03_junto", "min_changed_pixels": 200}],
            "state_changes": changes,
        },
    }


def run_ps(script, args):
    skill = os.environ.get("DS_SKILL_DIR") or DEFAULT_SKILL
    path = os.path.join(skill, "scripts", script)
    if script == "build-partial-rom.ps1" and "WriteContract" not in open(path, encoding="utf-8-sig").read():
        skill = DEV_SKILL
        path = os.path.join(skill, "scripts", script)
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", path, "-ProjectPath", ROOT] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in proc.stdout:
        print(line, end="")
        out.append(line)
    proc.wait()
    return proc.returncode, "".join(out), skill


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json")
    ap.add_argument("--solo-compilar", action="store_true", help="solo cabecera, escenario y compilacion (sin grabar ni verificar)")
    a = ap.parse_args()
    with open(a.json, encoding="utf-8") as f:
        try:
            spec = json.load(f)
        except ValueError as e:
            fail("JSON invalido: %s" % e)
    spec = validate(spec)
    n = spec["nombre"]
    write("include/minirom_gen/%s.h" % spec_ident(n), gen_header(spec))
    write("scenarios/minirom_%s.json" % n, json.dumps(gen_scenario(spec), indent=2) + "\n")
    variant = "mini-" + n
    defines = ["MINIROM=1", "MINIROM_SPEC=" + spec_ident(n), "SKIP_TITLE=1"] + [d if "=" in d else d + "=1" for d in spec["depuracion"]]
    dstr = ",".join(defines)
    rom_name = "dungeonds-mini-%s.nds" % n

    if a.solo_compilar:
        code, out, _ = run_ps("build-project.ps1", ["-Variant", variant, "-Define", dstr, "-OutputRom", rom_name])
        m = re.search(r"DS_BUILD=PASS rom=(.+?) variant", out)
        if code or not m:
            fail("la compilacion fallo")
        print("MINIROM=PASS rom=%s (solo compilar)" % m.group(1))
        return
    contract = ".ds-game-dev/partial/%s.txt" % variant
    scen = "scenarios/minirom_%s.json" % n
    code, out, skill = run_ps("build-partial-rom.ps1", ["-Variant", variant, "-Define", dstr, "-Record",
                                                        "-WriteContract", contract, "-Scenarios", scen])
    if code or "PARTIAL_RECORD_CONTRACT" not in out:
        fail("la grabacion fallo (ver arriba)")
    # The hero's punches (and the Glifo prayer) load per direction when used: a run never opens them all, a player does.
    extra = ["punch/gancho_*", "punch/punch_*", "punch/pray_*"] + list(spec["extra_archivos"]) + (spec["animaciones"] if isinstance(spec["animaciones"], list) else [])
    if extra:
        with open(os.path.join(ROOT, contract), "a", encoding="utf-8", newline="") as f:
            f.write("".join("archivo: %s\n" % x for x in extra))
    code, out, _ = run_ps("build-partial-rom.ps1", ["-Variant", variant, "-Define", dstr, "-Contract", variant,
                                                    "-Scenarios", scen, "-OutputRom", rom_name])
    m = re.search(r"PARTIAL_VERIFY=PASS .*?rom=(.+?) size_mb=([\d.,]+)", out)
    if code or not m:
        fail("la verificacion de la ROM parcial no paso")
    if "DSM_SCENARIO_RESULT=PASS" not in out:
        fail("el escenario scenarios/minirom_%s.json no paso en la ROM (ver arriba)" % n)
    rom, size = m.group(1), m.group(2).replace(",", ".")
    print("MINIROM=PASS rom=%s size_mb=%s full_mb~56" % (rom, size))
    print("Subir (solo con confirmacion): powershell -NonInteractive -ExecutionPolicy Bypass -File %s\\scripts\\upload-rom.ps1 "
          "-ProjectPath %s -RomPath %s -ConfirmUpload" % (skill, ROOT, rom))


if __name__ == "__main__":
    main()
