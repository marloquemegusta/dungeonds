#!/usr/bin/env python3
"""Re-renderiza los props de cada ambiente del poster v3 con el pipeline del campamento nocturno
(tools/props/props_camp_night.py + props_camp_light.py + prop_shadows.py): mismo lab, mismo procesado a sprite de
1 bit de alfa, y la sombra proyectada por el mismo codigo, solo que con la luz de cada ambiente. No copia el
pipeline: lo importa y le cambia la luz (clave del lab y direccion de la sombra).

La direccion de la luz se da en pantalla (ar, ad): ar = a la derecha, ad = hacia el espectador, desde el prop HACIA la
fuente. Para el lab y la sombra se convierte en una «posicion de hoguera» falsa a la que apuntan props_camp_light
(fire_dir_xz) y prop_shadows (camp_pos), asi que la sombra sale al lado contrario, como en el campamento.

Salida: tools/poster/render_amb/<ambiente>/<variante>/<pieza>/{color,shadow}.png + meta.json (mismo formato que
assets/environment/cathedral/props/render). Los GLB se leen de la carpeta principal del repo (derivados no versionados).

uso: python tools/poster/props_ambiente.py [--skip-lab] [ambiente[:variante] ...]
"""
import json, math, os, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "props"))
import prerender_props as pr          # noqa: E402
import prop_shadows as ps             # noqa: E402
import props_camp_light as cl         # noqa: E402

OUT = os.path.join(HERE, "render_amb")
MAIN_PROPS = os.environ.get("DS_MAIN_PROPS", "C:/codexlocal/dungeonds/assets/environment/cathedral/props")   # glb y fbx
GLB_PIECES = ("banco_roto", "columna", "columna_entera", "relicario", "altar", "cofre_cerrado", "sacos", "sacos_b",
              "sacos_remate", "sacos_remate_der", "alambre", "camp_hoguera")
# props tematicos (rama claude/props-tematicos-84feb8, commit f3a49652): sus GLB estan en el worktree de esa rama (no versionados)
TEMATICOS = ("candelabro_pie", "huesos_monton", "catre", "calaveras_pila", "sarcofago", "capullo", "exvoto", "biombo",
             "osario_estante", "osario_lado", "palangana", "brasero", "cepo", "lapida_pie", "reclinatorio")
EXTRA_PROPS = os.environ.get("DS_TEMATICOS_PROPS", "C:/codexlocal/dungeonds/.claude/worktrees/props-tematicos-84feb8/assets/environment/cathedral/props")
GLB_PIECES = GLB_PIECES + TEMATICOS


def load_props():
    """props.json mas las piezas nuevas de cada sala (tools/poster/salas/props_NN.json, mismo formato: variantes giradas)."""
    import glob
    props = json.load(open(os.path.join(ROOT, "tools/props/props.json"), encoding="utf-8"))
    for f in sorted(glob.glob(os.path.join(HERE, "salas", "props_*.json"))):
        props.update(json.load(open(f, encoding="utf-8")))
    return props


SALA_PIECES = tuple(n for n in load_props() if n not in GLB_PIECES and load_props()[n].get("glb_from"))
GLB_PIECES = GLB_PIECES + SALA_PIECES
# que piezas nuevas lleva cada juego de luz (ambiente:variante)
TEMA_POR_SET = {"techo:c": ("osario_estante", "osario_lado", "huesos_monton", "calaveras_pila"),
                "sinluz:c": ("osario_estante", "huesos_monton", "calaveras_pila"),
                "cera:l": ("catre", "biombo", "palangana", "candelabro_pie", "reclinatorio", "exvoto"),
                "cera:r": ("catre", "biombo", "palangana", "candelabro_pie", "reclinatorio", "exvoto"),
                "farol:l": ("cepo", "capullo"), "farol:r": ("cepo", "capullo"),
                "hoguera:l": ("sarcofago", "lapida_pie", "brasero"), "hoguera:r": ("sarcofago", "lapida_pie", "brasero")}


def stage_props():
    """Carpeta con los GLB de las piezas viejas (repo principal) y de las tematicas (worktree de su rama)."""
    import shutil
    dst = os.path.join(OUT, "_props")
    os.makedirs(os.path.join(dst, "glb"), exist_ok=True)
    for n in GLB_PIECES:
        d = os.path.join(dst, "glb", n + ".glb")
        for base in (MAIN_PROPS, EXTRA_PROPS):
            src = os.path.join(base, "glb", n + ".glb")
            if os.path.exists(src):
                if not os.path.exists(d) or os.path.getsize(d) != os.path.getsize(src):
                    shutil.copyfile(src, d + f".{os.getpid()}.tmp")
                    os.replace(d + f".{os.getpid()}.tmp", d)
                break
    # piezas giradas sin Blender (props.json: glb_from + yaw): el giro se hornea en el GLB con glb_yaw.py
    import glb_yaw
    props = load_props()
    for n in GLB_PIECES:
        f = props.get(n, {}).get("glb_from")
        if f:
            tmp = os.path.join(dst, "glb", f"{n}.{os.getpid()}.tmp")
            glb_yaw.main(os.path.join(dst, "glb", f + ".glb"), tmp, props[n]["yaw"])
            os.replace(tmp, os.path.join(dst, "glb", n + ".glb"))   # atomico: otro proceso puede estar leyendolo
    return dst
# piezas sin GLB local (banco_entero, banco_volcado, santo, vela): se aproximan sobre su sprite del juego (poster_arpg_v3)

# Luz del lab por ambiente (colores apagados, DESIGN 6.10). dir = (ar, ad) hacia la fuente; elev = elevacion de la luz.
AMBIENTES = {
    # techo: la luz neutra del lab, la misma con la que se hornean los personajes y los props del juego (DESIGN-ARPG 11);
    # el tono e intensidad de cada sala se aplican despues, igual a props, suelo y personajes
    "techo": {"v": {"c": dict(neutral=True)}},
    "cielo": {"v": {"c": dict(dir=(-0.62, -0.78), elev=30, key=1.9, keyColor="#a9b0bd", fill=0.55, fillColor="#5f6a80", world=0.16)}},
    "dia": {"v": {"c": dict(dir=(-0.40, -0.92), elev=58, key=3.3, keyColor="#e8d4a6", fill=0.55, fillColor="#7f93b8", world=0.20)}},
    "noche": {"v": {"c": dict(dir=(0.30, -0.95), elev=72, key=1.5, keyColor="#8ea4d2", fill=0.50, fillColor="#4f67a0", world=0.12)}},
    "cera": {"v": {"l": dict(dir=(-0.95, 0.30), sh=42, elev=26, key=3.4, keyColor="#d9a468", fill=0.18, fillColor="#5a4a52", world=0.05),
                   "r": dict(dir=(0.95, 0.30), sh=42, elev=26, key=3.4, keyColor="#d9a468", fill=0.18, fillColor="#5a4a52", world=0.05)}},
    "farol": {"v": {"l": dict(dir=(-0.9, -0.2), elev=34, key=5.0, keyColor="#eef0ff", fill=0.06, fillColor="#39414f", world=0.03),
                    "r": dict(dir=(0.9, -0.2), elev=34, key=5.0, keyColor="#eef0ff", fill=0.06, fillColor="#39414f", world=0.03)}},
    "sinluz": {"v": {"c": dict(dir=(0.0, 1.0), elev=80, key=0.5, keyColor="#6a789c", fill=0.30, fillColor="#3b4668", world=0.05)}},
    "hoguera": {"v": {"l": dict(dir=(-0.95, 0.30), elev=34, key=5.0, keyColor="#d9a468", fill=0.5, fillColor="#4f67a0", world=0.15),
                      "r": dict(dir=(0.95, 0.30), elev=34, key=5.0, keyColor="#d9a468", fill=0.5, fillColor="#4f67a0", world=0.15)}},
}


def fake_pos(d, dist=200.0):
    """Punto del suelo cuya direccion hacia la hoguera (128, 300) es d = (ar, ad)."""
    return [round(128 - d[0] * dist, 1), round(300 - d[1] * dist / 2.0, 1)]


def lab_light(spec, pos):
    return {"fill": spec["fill"], "rim": 0.0, "world": spec["world"], "fillColor": spec["fillColor"], "rimColor": "#cce7ff",
            "key": spec["key"], "keyColor": spec["keyColor"], "keyPos": cl.key_pos(pos[0], pos[1], spec["elev"])}


def render_set(amb, tag, pieces=GLB_PIECES, skip=False):
    spec = AMBIENTES[amb]["v"][tag]
    neutral = spec.get("neutral", False)
    pos = None if neutral else fake_pos(spec["dir"])
    base = json.load(open(pr.SETTINGS, encoding="utf-8"))
    leg = base.get("legibility", "anterior")
    props = load_props()
    out = os.path.join(OUT, amb, tag)
    os.makedirs(out, exist_ok=True)
    raw = os.path.join(tempfile.gettempdir(), f"props_raw_amb_{amb}_{tag}")
    os.makedirs(raw, exist_ok=True)
    cfgs = {}
    for n in pieces:
        c = dict(props[n])
        c["glb"] = props[n].get("glb", n)
        c["shadow_free_margin"] = True                              # el poster no tiene el margen de 8 px del juego
        if n.startswith("lapida_"):
            c["poster_shadow"] = True                               # el juego no da sombra a las lapidas; el poster si
        if not neutral:
            c["camp_pos"] = pos
            c["shadow_elevation"] = spec.get("sh", max(20, min(80, 90 - spec["elev"])))   # ps: angulo respecto a la vertical
        cfgs[n] = c
    stage = stage_props()
    pr.PROPS = stage                                                # GLB de la carpeta principal y de las tematicas
    ps.GLB_DIR = os.path.join(stage, "glb")
    tmp_json = os.path.join(raw, f"props_amb_{os.getpid()}.json")   # varios procesos a la vez
    json.dump(cfgs, open(tmp_json, "w", encoding="utf-8"))
    ps.PROPS_JSON = tmp_json
    ps.RENDER = out

    def render(n):
        st = base if neutral else {**base, "lighting": lab_light(spec, pos)}
        path = os.path.join(raw, n + "_settings.json")
        json.dump(st, open(path, "w", encoding="utf-8"))
        return pr.run_lab(n, raw, path, leg, cfgs[n]["glb"])

    if skip:
        dirs = {n: os.path.join(raw, n) for n in pieces}
    else:
        with ThreadPoolExecutor(3) as ex:
            dirs = dict(zip(pieces, ex.map(render, pieces)))
    for n in pieces:
        m = pr.process(n, cfgs[n], dirs[n], out, leg)
        try:
            ps.process(n)
        except Exception as e:                                       # sombra que no cabe: la pieza va sin sombra
            print("  sin sombra", n, str(e)[:90])
        print(amb, tag, n, m["size_px"])


def main():
    args = sys.argv[1:]
    skip = "--skip-lab" in args
    only = [a for a in args if not a.startswith("--")]
    todo = []
    for amb, d in AMBIENTES.items():
        for tag in d["v"]:
            if not only or amb in only or f"{amb}:{tag}" in only:
                todo.append((amb, tag))
    sel = tuple(p for p in GLB_PIECES if p in only)
    for amb, tag in todo:
        if sel:
            pieces = sel
        elif "--tematicos" in args:
            pieces = TEMA_POR_SET.get(f"{amb}:{tag}", ())
        else:
            pieces = tuple(p for p in GLB_PIECES if p not in TEMATICOS)
        if pieces:
            render_set(amb, tag, pieces, skip)


if __name__ == "__main__":
    main()
