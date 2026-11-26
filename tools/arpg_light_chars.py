#!/usr/bin/env python3
"""Renderiza los personajes de UNA luz de sala del ARPG (tools/arpg_light_rooms.json) con el lab rapido.

Cada personaje sale a scratch/arpg_luz/<luz>/chars/<nombre>/ con el mismo encuadre que el dia (fitZoom, fitExtent y
normScale del settings.json de assets/sprites/characters/<nombre>), solo cambia la luz (--lightJson). Los modelos no
versionados se buscan tambien en la carpeta principal del repo. Los que no tienen modelo en characters.json
(Super Monja, arañas) los resuelve build_arpg_light_packs.py con el tinte medido sobre el heroe.

uso: python tools/arpg_light_chars.py <luz> [--jobs N] [--only a,b] [--list]
"""
import argparse, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = ROOT.parents[1] if ROOT.parent.name == ".worktrees" else ROOT
CHARS = ROOT / "assets/sprites/characters"
EXPORT = ROOT / "tools/lab/fast/export_character_fast.cjs"

# Clip del juego (chars_meta de generate_player_sprites_c.py) -> entrada de characters.json que lo renderiza.
HERO = ["corazon", "corazon_disparo", "corazon_pray", "corazon_punch_a", "corazon_punch_b", "corazon_gancho", "corazon_agachado_andar"]
# Tipo de enemigo de GRUPOS de tools/poster/salas/sala_NN.py -> entradas de characters.json
ENEMY_CHARS = {
    "monja": ["exvoto", "exvoto_pray_stand", "exvoto_pray_kneel", "exvoto_stand_up"],
    "bebe": ["exvoto_bebe"],
    "monaguillo": ["monaguillo"],
    "cireneo": ["cireneo", "cireneo_charge", "cireneo_telegraph"],
    "ojo": ["ojo", "ojo_look", "ojo_sentence"],
    "parroco": ["exvoto_parroco_run"],
    "abanderado": ["abanderado", "abanderado_point"],
}


def load_lights():
    return json.loads((ROOT / "tools/arpg_light_rooms.json").read_text(encoding="utf-8"))


NEUTRO = {"key": "#fff0d9", "fill": "#cbd8ff", "rim": "#dce8ff"}


def mezcla(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def lab_light(l):
    """Personajes: la intensidad escala TODAS las luces (key/fill/rim/world del preset neutral del dia) y la luz de la sala
    solo pone color y direccion de la sombra de suelo; el sombreado conserva la direccion del dia (shadeDay) para que
    el peregrino se lea de frente. char_gain (opcional) sustituye a la intensidad (claustros: sol por encima del dia)."""
    g = l.get("char_gain", l["intensidad"])
    mx = l.get("char_tint_mix", 0.5)  # cuanto del color de la sala pasa al personaje (0 = neutral del dia)
    return {"key": round(3.2 * g, 3), "fill": round(0.65 * g, 3), "rim": round(0.4 * g, 3), "world": round(0.25 * g, 3),
            "keyColor": mezcla(NEUTRO["key"], l["keyColor"], mx), "fillColor": mezcla(NEUTRO["fill"], l["fillColor"], mx),
            "rimColor": mezcla(NEUTRO["rim"], l["rimColor"], mx), "shadeDay": True,
            "fromDeg": l["desde_deg"], "elevation": l["elevacion_deg"], "shadowElevation": l["sombra_elevacion_deg"]}


def room_enemies(rooms):
    import importlib.util
    types = set()
    for r in rooms:
        spec = importlib.util.spec_from_file_location(f"sala{r}", ROOT / f"tools/poster/salas/sala_{r:02d}.py")
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        for g in getattr(m, "GRUPOS", []):
            for mi in g.get("miembros", []):
                types.add(mi[0])
    return types


def resolve(rel):
    for base in (ROOT, MAIN_ROOT):
        p = base / rel
        if p.exists() and p.stat().st_size > 2000:      # un puntero de LFS pesa ~130 bytes
            return p
    raise FileNotFoundError(rel)


def chars_for(light):
    names = list(HERO)
    for t in sorted(room_enemies(light["rooms"])):
        names += ENEMY_CHARS.get(t, [])
    return names


def build_cmd(name, cfg, defaults, out_dir, light_json):
    day = json.loads((CHARS / name / "settings.json").read_text(encoding="utf-8"))
    cmd = ["node", str(EXPORT), str(resolve(cfg["model"])), str(out_dir), "--template", str(resolve(cfg["template"])),
           "--anim", str(cfg["anim"]), "--resolution", str(cfg["resolution"]),
           ]
    for key, flag in (("fitZoom", "--fitZoom"), ("fitExtent", "--fitExtent"), ("normScale", "--normScale")):
        if key in day:                      # monaguillo no guarda normScale: el lab lo recalcula igual que en el dia
            cmd += [flag, repr(day[key]) if key != "fitZoom" else str(day[key])]
    for key, flag in (("muzzleBone", "--muzzleBone"), ("muzzleForward", "--muzzleForward")):
        v = cfg.get(key, defaults.get(key))
        if v is not None:
            cmd += [flag, str(v)]
    cmd += ["--light", "neutral", "--lightJson", str(light_json)]
    outline = cfg.get("outlineMode", cfg.get("outline", defaults.get("outlineMode", defaults.get("outline"))))
    if outline:
        cmd += ["--outline", str(outline)]
    if cfg.get("saturation", defaults.get("saturation")) is not None:
        cmd += ["--saturation", str(cfg.get("saturation", defaults.get("saturation")))]
    cmd += ["--legibility", str(cfg.get("legibility", defaults.get("legibility", "c2")))]
    return cmd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("light"); ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only"); ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    doc = load_lights()
    light = next(l for l in doc["luces"] if l["id"] == a.light)
    manifest = json.loads((CHARS / "characters.json").read_text(encoding="utf-8"))
    names = a.only.split(",") if a.only else chars_for(light)
    if a.list:
        print(names); return
    out_root = ROOT / "scratch/arpg_luz" / light["id"] / "chars"
    out_root.mkdir(parents=True, exist_ok=True)
    light_json = out_root.parent / "lab_light.json"
    light_json.write_text(json.dumps(lab_light(light)), encoding="utf-8")

    def work(n):
        t0 = time.time()
        r = subprocess.run(build_cmd(n, manifest["characters"][n], manifest.get("defaults", {}), out_root / n, light_json),
                           cwd=str(ROOT), capture_output=True, text=True)
        return n, r.returncode, time.time() - t0, (r.stderr or r.stdout)[-400:]
    with ThreadPoolExecutor(a.jobs) as ex:
        for n, rc, dt, tail in ex.map(work, names):
            print(("ok " if rc == 0 else "FAIL ") + n, "%.1fs" % dt, "" if rc == 0 else tail, flush=True)


if __name__ == "__main__":
    main()
