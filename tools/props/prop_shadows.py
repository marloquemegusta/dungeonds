#!/usr/bin/env python3
"""Sombra proyectada de cada pieza sobre el suelo, con la luz key del lab (preset neutral).

usage: python tools/props/prop_shadows.py [piezas...]
       (por defecto, las piezas no lapida de tools/props/props.json)

Geometria: el GLB de props/glb (ya girado y apoyado en el suelo por prep_props.py) se proyecta con la
camara del lab (ortografica, elevacion 30; azimut 135 en el marco del GLB, calibrado contra las siluetas
de los render del lab: IoU 0.94-0.99 en banco_roto, santo, relicario y vela). La escala y el encuadre son
los de color.png (ancho = target_width, base en el borde inferior, centrada). Cada triangulo se proyecta
sobre el plano del suelo a lo largo de la direccion de la luz y el resultado se rasteriza en el mismo
encuadre.

Direccion de la luz: la MISMA key que ilumina los cuerpos en el lab. applyBlenderLighting fija la
key en (0.4096, 0.5736, -0.7094) = dungeonLightPosition(55, 30), y generateCharacterShadows usa esa
misma direccion (SPRITE_KEY_ROT). Antes el azimut se deducia de la sombra horneada del marine con un
ancla equivocada (20,33 del sprite en vez del (40,40) de la celda de 80 px), lo que daba ~100.75
grados y dejaba las sombras de las piezas apuntando hacia la luz. Elevacion y azimut van en la
convencion de dungeonLightPosition.

Salida, por pieza:
  render/<pieza>/shadow.png  modo L, 255 = sombra, binaria; lienzo ampliado (multiplo de 8).
  render/<pieza>/meta.json   shadow_offset_px [dx, dy]: origen del lienzo de shadow.png respecto al de
                             color.png (dx, dy <= 0). color.png queda en (-dx, -dy) dentro de shadow.png.
                             shadow_canvas_px [w, h]: tamano de shadow.png.
La sombra no se pinta donde la pieza es opaca. Las lapidas no llevan sombra.
"""
import argparse
import json
import math
import os
import struct

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROPS = os.path.join(ROOT, "assets/environment/cathedral/props")
RENDER = os.path.join(PROPS, "render")
GLB_DIR = os.path.join(PROPS, "glb")
PROPS_JSON = os.path.join(ROOT, "tools/props/props.json")

CAM_AZIMUTH = 135.0           # en el marco del GLB; ver la calibracion en la cabecera
CAM_ELEVATION = 30.0          # props_render_settings.json, cameraElevationDegrees
KEY_ELEVATION = 55.0          # applyBlenderLighting del lab (SPRITE_KEY_ROT[0]), key de los cuerpos
KEY_AZIMUTH = 30.0            # applyBlenderLighting del lab (SPRITE_KEY_ROT[1])
SUPERSAMPLE = 4
COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    """Posiciones y triangulos (GLB sin transformaciones de nodo, como los que genera prep_props.py)."""
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    doc = json.loads(data[20:20 + jlen])
    bin_off = 20 + jlen
    blen = struct.unpack("<I", data[bin_off:bin_off + 4])[0]
    binary = data[bin_off + 8: bin_off + 8 + blen]
    if any(k in n for n in doc["nodes"] for k in ("matrix", "translation", "rotation", "scale")):
        raise ValueError(f"{path}: transformaciones de nodo no soportadas")

    def accessor(i):
        a = doc["accessors"][i]
        bv = doc["bufferViews"][a["bufferView"]]
        n = NCOMP[a["type"]]
        fmt = COMP[a["componentType"]]
        size = struct.calcsize("<" + fmt)
        stride = bv.get("byteStride", size * n)
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        out = np.empty((a["count"], n), dtype=np.float64)
        for k in range(a["count"]):
            out[k] = struct.unpack_from("<" + fmt * n, binary, off + k * stride)
        return out

    verts, tris, base = [], [], 0
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            v = accessor(prim["attributes"]["POSITION"])
            t = accessor(prim["indices"]).astype(np.int64).reshape(-1, 3)
            verts.append(v); tris.append(t + base); base += len(v)
    return np.concatenate(verts), np.concatenate(tris)


def camera_basis(azimuth, elevation):
    a, e = math.radians(azimuth), math.radians(elevation)
    cam = np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
    fwd = -cam
    right = np.cross(fwd, [0.0, 1.0, 0.0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return right, up


def key_light_direction(elevation, azimuth):
    """Mismo calculo que dungeonLightPosition del lab, normalizado (hacia la luz)."""
    e, t = math.radians(elevation), math.radians(azimuth)
    v = np.array([math.sin(t) * math.sin(e), math.cos(e), -math.cos(t) * math.sin(e)])
    return v / np.linalg.norm(v)


def floor8(v):
    return int(math.floor(v / 8.0)) * 8


def ceil8(v):
    return int(math.ceil(v / 8.0)) * 8


def raster(xy, tris, size, ss=SUPERSAMPLE):
    """Triangulos en coordenadas de lienzo (px) -> mascara binaria (cobertura >= 50 %)."""
    w, h = size
    im = Image.new("L", (w * ss, h * ss), 0)
    draw = ImageDraw.Draw(im)
    q = xy * ss
    for a, b, c in tris:
        draw.polygon([tuple(q[a]), tuple(q[b]), tuple(q[c])], fill=255)
    cov = np.asarray(im, dtype=np.float32).reshape(h, ss, w, ss).mean(axis=(1, 3))
    return cov >= 127.5


LIGHT = key_light_direction(KEY_ELEVATION, KEY_AZIMUTH)


def process(name, dry_run=False):
    if name.startswith("lapida_"):
        raise ValueError(f"{name}: las lapidas no llevan sombra")
    folder = os.path.join(RENDER, name)
    meta_path = os.path.join(folder, "meta.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    color = Image.open(os.path.join(folder, "color.png")).convert("RGBA")
    cw, ch = color.size
    if meta["size_px"] != [cw, ch]:
        raise ValueError(f"{name}: meta.json size_px does not match color.png")
    nw, nh = meta["content_px"]
    ox, oy = (cw - nw) // 2, ch - nh
    alpha = np.asarray(color)[:, :, 3] >= 128

    verts, tris = read_glb(os.path.join(GLB_DIR, name + ".glb"))
    right, up = camera_basis(CAM_AZIMUTH, CAM_ELEVATION)
    scr = np.stack([verts @ right, verts @ up], 1)
    sx0, sx1 = scr[:, 0].min(), scr[:, 0].max()
    sy0, sy1 = scr[:, 1].min(), scr[:, 1].max()
    scale = nw / (sx1 - sx0)
    if abs((sy1 - sy0) * scale - nh) > 1.5:
        raise ValueError(f"{name}: la altura proyectada no encaja con content_px (camara o escala)")

    def canvas(points_scr):
        return np.stack([ox + (points_scr[:, 0] - sx0) * scale, oy + (sy1 - points_scr[:, 1]) * scale], 1)

    # Comprobacion: la silueta proyectada tiene que coincidir con el alfa de color.png.
    obj = raster(canvas(scr), tris, (cw, ch))
    iou = float((obj & alpha).sum() / max((obj | alpha).sum(), 1))

    # Sombra: cada vertice cae a lo largo de la direccion de la luz sobre el plano del suelo (y = min y).
    light = LIGHT
    ground = verts[:, 1].min()
    lift = (verts[:, 1] - ground) / light[1]
    on_ground = verts - lift[:, None] * light[None, :]
    shadow_xy = canvas(np.stack([on_ground @ right, on_ground @ up], 1))

    x_min, y_min = shadow_xy.min(0)
    x_max, y_max = shadow_xy.max(0)
    x0 = floor8(min(0, math.floor(x_min)))
    y0 = floor8(min(0, math.floor(y_min)))
    x1 = ceil8(max(cw, math.ceil(x_max)))
    y1 = ceil8(max(ch, math.ceil(y_max)))
    w, h = x1 - x0, y1 - y0
    shadow = raster(shadow_xy - [x0, y0], tris, (w, h))
    own = np.zeros((h, w), dtype=bool)
    own[-y0:-y0 + ch, -x0:-x0 + cw] = alpha
    shadow &= ~own

    if not dry_run:
        Image.fromarray((shadow * 255).astype(np.uint8), "L").save(os.path.join(folder, "shadow.png"))
        meta["shadow_offset_px"] = [x0, y0]
        meta["shadow_canvas_px"] = [w, h]
        with open(meta_path, "w", encoding="utf-8", newline="") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
    ys, xs = np.nonzero(shadow)
    bbox = (int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + 1 + x0, int(ys.max()) + 1 + y0) if len(xs) else None
    print(f"{name}: silueta/alfa IoU {iou:.3f}; lienzo {w}x{h} offset [{x0}, {y0}]; "
          f"sombra {int(shadow.sum())} px; bbox sombra (en lienzo color) {bbox}")
    return {"name": name, "canvas": [w, h], "offset": [x0, y0], "iou": iou}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="no escribe shadow.png ni meta.json")
    ap.add_argument("pieces", nargs="*")
    a = ap.parse_args()
    names = a.pieces or [n for n in json.load(open(PROPS_JSON, encoding="utf-8")) if not n.startswith("lapida_")]
    for n in names:
        process(n, a.dry_run)


if __name__ == "__main__":
    main()
