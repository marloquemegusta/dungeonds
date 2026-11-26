#!/usr/bin/env python3
"""Renderiza los props de UNA luz de sala del ARPG (tools/arpg_light_rooms.json) con el lab rapido de props.

Los props de una luz son los de la composicion de sus salas en el poster v3 (salas/sala_NN.py + poster_arpg.json).
Salida: scratch/arpg_luz/<luz>/props/<pieza>/{color,shadow,footprint,depth}.png + meta.json (mismo formato que
assets/environment/cathedral/props/render), con la sombra dura proyectada por prop_shadows.py a lo largo de la luz.
Los GLB (derivados no versionados) se leen de la carpeta principal del repo.

uso: python tools/arpg_light_props.py <luz> [--jobs N] [--only a,b] [--list]
"""
import argparse, importlib.util, json, math, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = ROOT.parents[1] if ROOT.parent.name == ".worktrees" else ROOT
sys.path.insert(0, str(ROOT / "tools/props"))
sys.path.insert(0, str(ROOT / "tools/poster"))
import prerender_props as pr          # noqa: E402
import prop_shadows as ps             # noqa: E402
import glb_yaw                        # noqa: E402

FAST = ROOT / "tools/lab/fast/export_prop_fast.cjs"
MAIN_GLB = MAIN_ROOT / "assets/environment/cathedral/props/glb"
KIT_PIECES = ["columna_entera", "banco_entero", "banco_roto", "relicario", "vela", "santo", "sacos", "verja", "columna",
              "sacos_b", "sacos_remate", "sacos_remate_der", "alambre", "santo_der"]   # DEFAULT_PROPS del kit sin lapidas (PNG) ni compuestos
ALIAS = {"camp_n_hoguera": "camp_hoguera"}      # variante nocturna del campamento: mismo modelo


def load_doc():
    return json.loads((ROOT / "tools/arpg_light_rooms.json").read_text(encoding="utf-8"))


def lab_light(l):
    return {"preset": "custom", "key": l["key"], "fill": l["fill"], "rim": l["rim"], "world": l["world"],
            "keyColor": l["keyColor"], "fillColor": l["fillColor"], "rimColor": l["rimColor"],
            "fromDeg": l["desde_deg"], "elevation": l["elevacion_deg"], "shadowElevation": l["sombra_elevacion_deg"]}


def light_xz(deg):
    a = math.radians(deg); u, d = math.sin(a), -math.cos(a)
    return [(d - u) / math.sqrt(2), -(u + d) / math.sqrt(2)]


def load_props():
    props = json.loads((ROOT / "tools/props/props.json").read_text(encoding="utf-8"))
    for f in sorted((ROOT / "tools/poster/salas").glob("props_*.json")):
        props.update(json.loads(f.read_text(encoding="utf-8")))
    # altar_pie (estampa de sala de pie, tools/encuentros/gen_salas_rom.py PIEZA_ALIAS) es el altar del poster con otro nombre
    props["altar_pie"] = {**props["altar"], "glb": "altar"}
    return props


def room_props(rooms):
    d = json.loads((ROOT / "tools/poster/poster_arpg.json").read_text(encoding="utf-8"))["salas"]
    extra = {8: ["vela"], 12: ["vela"], 4: ["vela"], 5: ["vela"], 15: ["camp_n_hoguera"]}   # fuentes de luz de poster_arpg_v3.EXTRA
    out = set()
    for r in rooms:
        spec = importlib.util.spec_from_file_location(f"sala{r}", ROOT / f"tools/poster/salas/sala_{r:02d}.py")
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        drop = set(m.DROP)
        out |= {it["piece"] for it in d[r]["ambiente"]["composicion"] if it["piece"] not in drop}
        out |= {a[0].rstrip("~") for a in m.ADD}
        out |= {a[0].rstrip("~") for a in getattr(m, "EXTRA", [])}
        out |= set(extra.get(r, []))
    return sorted(out)


def stage_glbs(stage, names, props):
    gdir = stage / "glb"; gdir.mkdir(parents=True, exist_ok=True)
    missing = []
    for n in names:
        base = ALIAS.get(n, props[n].get("glb_from", props[n].get("glb", n)))
        src = MAIN_GLB / (base + ".glb")
        if not src.exists():
            missing.append(n); continue
        dst = gdir / (n + ".glb")
        if "glb_from" in props[n] and props[n]["yaw"] and n != base:
            glb_yaw.main(str(src), str(dst), props[n]["yaw"])
        else:
            dst.write_bytes(src.read_bytes())
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("light"); ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--kit", action="store_true", help="piezas del kit de la catedral (config del kit, sin flags de poster) en props_kit/")
    a = ap.parse_args()
    doc = load_doc()
    light = next(l for l in doc["luces"] if l["id"] == a.light)
    props = load_props()
    names = a.only.split(",") if a.only else (KIT_PIECES if a.kit else room_props(light["rooms"]))
    if a.list:
        print(names); return
    base = ROOT / "scratch/arpg_luz" / light["id"]
    sub = "kit_props" if a.kit else "props"
    out = base / sub; raw = base / (sub + "_raw"); stage = base / (sub + "_stage")
    for d in (out, raw):
        d.mkdir(parents=True, exist_ok=True)
    missing = stage_glbs(stage, names, props)
    names = [n for n in names if n not in missing]
    if missing:
        print("SIN GLB:", missing)
    settings = json.loads((ROOT / "tools/props/props_render_settings.json").read_text(encoding="utf-8"))
    settings["lighting"] = lab_light(light)
    spath = raw / "settings.json"; spath.write_text(json.dumps(settings), encoding="utf-8")
    leg = settings.get("legibility", "anterior")
    sel = 90 - light["sombra_elevacion_deg"]       # prop_shadows: angulo respecto a la vertical
    cfgs = {}
    for n in names:
        c = dict(props[n]); c["glb"] = n
        # Con la luz rasante de las salas oscuras (cripta, monjarana) la sombra no cabe en el margen de 8 px: sin esto se
        # descartaba en silencio y las piezas sueltas de la sala salian sin sombra. Las del kit (estatuas, columnas) siguen
        # con el margen de 8 px: con sombra larga la monjarana pasa del limite de 440 tiles por ventana.
        if n not in KIT_PIECES:
            c["shadow_free_margin"] = True
        if not a.kit:
            c["poster_shadow"] = True
        c["light_xz"] = light_xz(light["desde_deg"])
        c["shadow_elevation"] = sel
        cfgs[n] = c
    pr.PROPS = str(stage)
    ps.GLB_DIR = str(stage / "glb")
    tmp_json = raw / "props_light.json"; tmp_json.write_text(json.dumps(cfgs), encoding="utf-8")
    ps.PROPS_JSON = str(tmp_json); ps.RENDER = str(out)

    def lab(n):
        d = raw / n
        r = subprocess.run(["node", str(FAST), str(stage / "glb" / (n + ".glb")), str(spath), str(d), "--legibility", leg],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(n + ": " + (r.stderr or r.stdout)[-400:])
        return str(d)
    with ThreadPoolExecutor(a.jobs) as ex:
        dirs = dict(zip(names, ex.map(lab, names)))
    for n in names:
        m = pr.process(n, cfgs[n], dirs[n], str(out), leg)
        try:
            ps.process(n)
        except Exception as e:
            print("  sin sombra", n, str(e)[:120])
        print(light["id"], n, m["size_px"], flush=True)


if __name__ == "__main__":
    main()
