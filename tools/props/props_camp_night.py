#!/usr/bin/env python3
"""Night camp props (DESIGN.md 7.5): re-renders the camp pieces lit by the bonfire.

usage: python tools/props/props_camp_night.py [--skip-lab] [piece ...]   (pieces: camp_n_* from props.json)

Each camp_n_* entry of props.json is a variant of an existing GLB ("glb"), rendered into its own folder
render/camp_n_<piece>/ so the cathedral renders (camp_* and the rest) stay untouched. Lighting (lab custom
light, see export_map_package_headless.cjs "lighting"): a low (~34 deg), muted amber key from the bonfire's
azimuth for that prop (props_camp_light.py), a faint cold-blue fill and a dark blue-ish ambient. The key fades
with distance to the fire. The door gets cold moonlight only; the bonfire pile itself is lit from above.
Shadows (prop_shadows.py) point away from the fire. Then run tools/camp/generate_camp_gfx.py.
"""
import json, os, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prerender_props as pr          # noqa: E402
import prop_shadows as ps             # noqa: E402
import props_camp_light as cl         # noqa: E402

# Muted palette (DESIGN.md 6.10): desaturated amber, never pure orange.
AMBER = "#d9a468"
MOON = "#8ea4d2"
FILL = "#4f67a0"

def lighting(name, cfg):
    base = {"fill": 0.5, "rim": 0.0, "world": 0.15, "fillColor": FILL, "rimColor": "#cce7ff"}
    if name == "camp_n_puerta":      # far from the fire: only cold moonlight, high from the left-front
        return {**base, "key": 2.3, "keyColor": MOON, "fill": 0.5, "world": 0.15,
                "keyPos": [-0.55, 0.78, -0.30]}
    if name == "camp_n_hoguera":     # the pile lights itself: warm from above, the ring of stones stays dark
        return {**base, "key": 2.6, "keyColor": AMBER, "world": 0.09, "keyPos": [0.0, 0.93, -0.36]}
    x, y = cfg["camp_pos"]
    k = 5.2 * max(0.50, 1.0 - cl.fire_distance(x, y) / 300.0)
    return {**base, "key": round(k, 2), "keyColor": AMBER, "keyPos": cl.key_pos(x, y, 34.0)}

def main():
    args = sys.argv[1:]
    skip = "--skip-lab" in args
    args = [a for a in args if not a.startswith("--")]
    cfg = json.load(open(pr.ROOT + "/tools/props/props.json", encoding="utf-8"))
    names = args or [n for n in cfg if n.startswith("camp_n_")]
    base = json.load(open(pr.SETTINGS, encoding="utf-8"))
    leg = base.get("legibility", "anterior")
    raw = os.path.join(tempfile.gettempdir(), "props_raw_night")
    os.makedirs(raw, exist_ok=True)

    def render(n):
        st = {**base, "lighting": lighting(n, cfg[n])}
        path = os.path.join(raw, n + "_settings.json")
        with open(path, "w", encoding="utf-8", newline="") as f:
            json.dump(st, f)
        return pr.run_lab(n, raw, path, leg, cfg[n].get("glb"))

    if skip:
        dirs = {n: os.path.join(raw, n) for n in names}
    else:
        with ThreadPoolExecutor(3) as ex:
            dirs = dict(zip(names, ex.map(render, names)))
    for n in names:
        m = pr.process(n, cfg[n], dirs[n], pr.OUT, leg)
        print(n, m["size_px"], "key", lighting(n, cfg[n])["key"])
        ps.process(n)

if __name__ == "__main__":
    main()
