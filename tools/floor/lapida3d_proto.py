#!/usr/bin/env python3
"""Prototipo de UNA lapida de suelo; color.png = composicion prerenderizada entera.

Hueco PRIMERO (boolean DIFFERENCE con el volumen de la lapida) y despues la lapida colocada dentro,
sin union. Se generan DOS variantes para comparar:
  - hundida (sink = +0.08 m bajo el tope de las losas)
  - elevada (sink = -0.015 m, 1,5 cm sobre el tope, con su sombra proyectada)

Render con el MISMO pipeline/ajustes que floor/rombos_tripo (glb_loader_minimal flipY=false, neutral,
30, contraste 1,2, saturacion 1,0): pasada base sin sombra (borde exacto) + delta de la pasada con
sombra solo dentro del hueco. Recorte 128x96 alineado al damero -> color.png.

Usage: python tools/floor/lapida3d_proto.py
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "props"))
import rombos as R  # noqa: E402
import rombos_tripo as RT  # noqa: E402
from prop_shadows import read_glb, camera_basis  # noqa: E402

ROOT = R.ROOT
BLENDER_SCRIPT = HERE / "lapida3d_proto_blender.py"
LAPIDA_GLB = ROOT / "assets/environment/cathedral/props/glb/lapida_cruz_v2.glb"
PROP_RENDER = ROOT / "assets/environment/cathedral/props/render"
FLOOR_PNG = ROOT / "assets/environment/cathedral/floor/rombos_tripo/floor_512x256.png"
OUT_SHEET = ROOT / "walkthroughs/v032-escenario/assets/lapida3d_proto.png"
TARGET_W_M = 2 * (32.0 / 17.9)
CAM_AZ, CAM_EL = 135.0, 30.0
CX0, CX1, CY0, CY1 = 512, 640, 240, 336
PASTE = (0, CY0 - 224)


def lapida_scale():
    verts, _ = read_glb(str(LAPIDA_GLB))
    right, _up = camera_basis(CAM_AZ, CAM_EL)
    w = float((verts @ right).max() - (verts @ right).min())
    return TARGET_W_M / w


def render(glb, work, name, shadows):
    settings = json.loads(R.PROPS_SETTINGS.read_text(encoding="utf-8"))
    settings.update({"width": 1152, "cameraElevationDegrees": 30, "shadows": shadows,
                     "waitTextures": True, "waitTexturesMs": 8000})
    cfg = work / f"{name}_settings.json"
    cfg.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    out = work / f"{name}_pkg"
    if out.exists():
        shutil.rmtree(out)
    subprocess.run(["node", str(R.LAB_SCRIPT), str(glb), str(cfg), str(out)], check=True)
    return np.array(Image.open(out / "world.png").convert("RGB"))[CY0:CY1, CX0:CX1].astype(np.float32)


def floor_palette():
    fj = json.loads((FLOOR_PNG.parent / "floor.json").read_text(encoding="utf-8"))
    pal5 = np.array([[(int(h, 16) & 31), ((int(h, 16) >> 5) & 31), ((int(h, 16) >> 10) & 31)]
                     for h in fj["palette"]], dtype=float)
    return pal5, np.round(pal5 * 255 / 31).astype(np.uint8)


def snap(comp):
    pal5, pal8 = floor_palette()
    c5 = np.round(comp.astype(float) * 31 / 255).reshape(-1, 3)
    d = ((c5[:, None, :] - pal5[None, :, :]) ** 2).sum(2)
    return pal8[d.argmin(1)].reshape(comp.shape)


def tiles_unique(arr8):
    h, w = arr8.shape[:2]
    uniq, nonempty = set(), 0
    for ty in range(h // 8):
        for tx in range(w // 8):
            t = arr8[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
            if t.any():
                nonempty += 1
                uniq.add(t.tobytes())
    return len(uniq), nonempty


def build(work, scale, sink, tag, ref, plate_png):
    glb = work / f"lapida3d_{tag}.glb"
    subprocess.run([str(R.BLENDER_EXE), "-b", "--factory-startup", "--python-exit-code", "1",
                    "-P", str(BLENDER_SCRIPT), "--", "--manifest", str(work / "manifest.json"),
                    "--lapida", str(LAPIDA_GLB), "--scale", f"{scale:.6f}",
                    "--sink", f"{sink:.4f}", "--plate-texture", str(plate_png),
                    "--out", str(glb)], check=True)
    info = json.loads(Path(str(glb) + ".compose.json").read_text(encoding="utf-8"))
    base = render(glb, work, f"base_{tag}", False)
    shadow = render(glb, work, f"shadow_{tag}", True)
    mask = np.abs(base - ref).max(2) > 8          # hueco/lapida
    delta = shadow - base
    keep = mask | (np.abs(delta).max(2) > 6)       # + sombra proyectada sobre las losas (variante elevada)
    comp = base.copy()
    comp[keep] += delta[keep]
    comp = snap(np.clip(np.round(comp), 0, 255).astype(np.float32)).astype(np.uint8)
    return comp, info, mask


def save_comp(comp, info, sink, folder):
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray(comp).save(folder / "color.png")
    uq, ne = tiles_unique(comp)
    meta = {"piece": folder.name, "kind": "composicion", "size_px": [comp.shape[1], comp.shape[0]],
            "content_px": [comp.shape[1], comp.shape[0]], "paste_offset_px": list(PASTE),
            "sink_m": sink, "lapida_footprint_m": info["lapida_footprint_m"], "joint_m": info["joint_m"],
            "tiles_8x8_nonempty": ne, "tiles_8x8_unique": uq,
            "note": "hueco cortado (difference) y lapida colocada despues; borde = damero real"}
    (folder / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def ring_diff(comp, ref):
    ring = np.zeros(comp.shape[:2], bool)
    ring[:8, :] = ring[-8:, :] = ring[:, :8] = ring[:, -8:] = True
    lum = lambda x: (x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722)
    return float(np.abs(lum(comp.astype(float)) - lum(ref))[ring].mean())


def overview(floor_img, comp, marine):
    canvas = floor_img.copy()
    bx, by = PASTE[0] + 128, PASTE[1]
    canvas.paste(Image.fromarray(comp), (bx, by))
    R.paste_sprite_anchored(canvas, marine, bx + 150, by + 110, 20, 33)
    return canvas, bx, by


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, default=ROOT / ".scratch_lapida3d")
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    manifest, entries = RT.prepare_textures(a.scratch, 10.0)
    losa = next(e for e in entries if e["name"] == "losa_a")
    aimg = np.array(Image.open(losa["a_png"]).convert("RGB")).astype(np.float32)
    Image.fromarray(np.clip(aimg * 1.02, 0, 255).astype(np.uint8)).save(a.scratch / "plate_lighter.png")
    plate_png = (a.scratch / "plate_lighter.png").resolve()

    floor_img = Image.open(FLOOR_PNG).convert("RGBA")
    floor_rgb = np.array(floor_img.convert("RGB"))
    ref = floor_rgb[PASTE[1]:PASTE[1] + (CY1 - CY0), PASTE[0]:PASTE[0] + (CX1 - CX0)].astype(np.float32)
    marine = Image.open(R.MARINE_PATH).convert("RGBA").crop((0, 0, 40, 40))

    scale = lapida_scale()
    sunk, info_s, mask_s = build(a.scratch, scale, 0.06, "sunk", ref, plate_png)
    elev, info_e, mask_e = build(a.scratch, scale, -0.015, "elev", ref, plate_png)

    # luminancia media del fondo del hueco (placa, sin la lapida) frente al damero
    h, w = sunk.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    center = (np.abs(xx - w / 2) < 34) & (np.abs(yy - h / 2) < 18)
    sel = mask_s & ~center
    lum = lambda x: (x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722)
    plate_lum = float(lum(sunk.astype(float))[sel].mean())
    dam_lum = float(lum(ref)[sel].mean())

    ms = save_comp(sunk, info_s, 0.06, PROP_RENDER / "lapida3d_cruz2_h")
    me = save_comp(elev, info_e, -0.015, PROP_RENDER / "lapida3d_cruz2_h_elevada")

    # hoja: vista hundida, vista elevada, borde 4x y diferencia absoluta
    c_s, bxs, bys = overview(floor_img, sunk, marine)
    c_e, bxe, bye = overview(floor_img, elev, marine)
    ov_s = c_s.crop((bxs + 16, bys - 8, bxs + 16 + 192, bys - 8 + 112)).convert("RGB")
    ov_e = c_e.crop((bxe + 16, bye - 8, bxe + 16 + 192, bye - 8 + 112)).convert("RGB")
    ov_s = ov_s.resize((ov_s.width * 2, ov_s.height * 2), Image.NEAREST)
    ov_e = ov_e.resize((ov_e.width * 2, ov_e.height * 2), Image.NEAREST)
    seam = c_s.crop((bxs + 16, bys - 8, bxs + 16 + 96, bys - 8 + 48)).convert("RGB")
    seam4 = seam.resize((seam.width * 4, seam.height * 4), Image.NEAREST)
    diff = np.clip(np.abs(sunk.astype(float) - ref).max(2) * 10, 0, 255).astype(np.uint8)
    diff_rgb = Image.fromarray(diff, "L").convert("RGB").resize((sunk.shape[1] * 2, sunk.shape[0] * 2), Image.NEAREST)

    m = 6
    col_x2 = m + ov_s.width + m
    col_x3 = col_x2 + ov_e.width + m
    W = col_x3 + max(seam4.width, diff_rgb.width) + m
    H = max(ov_s.height, seam4.height + m + diff_rgb.height) + 2 * m
    sheet = Image.new("RGB", (W, H), (0, 0, 0))
    sheet.paste(ov_s, (m, m))
    sheet.paste(ov_e, (col_x2, m))
    sheet.paste(seam4, (col_x3, m))
    sheet.paste(diff_rgb, (col_x3, m + seam4.height + m))
    OUT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_SHEET)
    thumb = sheet.copy()
    thumb.thumbnail((800, 800), Image.NEAREST)
    thumb_path = OUT_SHEET.with_name("lapida3d_proto_small.png")
    thumb.save(thumb_path)
    print(json.dumps({
        "sunk": {"color_px": list(sunk.shape[1::-1]), "tiles_unique": ms["tiles_8x8_unique"],
                 "ring_lum_diff": round(ring_diff(sunk, ref), 2)},
        "elev": {"color_px": list(elev.shape[1::-1]), "tiles_unique": me["tiles_8x8_unique"],
                 "ring_lum_diff": round(ring_diff(elev, ref), 2)},
        "hole_bg_lum": round(plate_lum, 2), "damero_bg_lum": round(dam_lum, 2),
        "hole_bg_minus_damero": round(plate_lum - dam_lum, 2),
        "sheet_px": list(sheet.size), "thumb": str(thumb_path)}, indent=2))


if __name__ == "__main__":
    main()
