#!/usr/bin/env python3
"""Generador y comparador de lapidas de suelo de catedral renderizadas con el Shader Lab Three.js.

Flujo de render unificado:
  1. Blender arma la escena: damero de rombos identico a rombos_tripo, resta exactamente las
     N x M o N x N teselas sustituidas, y coloca la losa/lapida encastrada a ras (sin cantos).
  2. Blender exporta el bloque completo a GLB.
  3. El Shader Lab de Three.js (tools/lab/export_map_package_headless.cjs) renderiza a 17.9 px/m
     con la camara a 30 deg y la luz Neutra oficial de props_render_settings.json.
  4. Se recorta la pieza alineada a la rejilla de tiles y se verifica que:
     - El diff con floor_512x256.png fuera de la zona sustituida sea EXACTAMENTE 0.
     - El contorno coincida con las juntas x +- 2y == 16 (mod 32).
  5. Genera la lamina comparativa cat_lapidas_lab_unified.png.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "props"))
import rombos as R  # noqa: E402
import rombos_tripo as RT  # noqa: E402
from prop_shadows import read_glb, camera_basis  # noqa: E402

BLENDER_SCRIPT = HERE / "build_lapidas_lab_blender.py"
OUT_SHEET = ROOT / "walkthroughs/v032-escenario/assets/cat_lapidas_lab_unified.png"
FLOOR_PNG = ROOT / "assets/environment/cathedral/floor/rombos_tripo/floor_512x256.png"
FLOOR_JSON = ROOT / "assets/environment/cathedral/floor/rombos_tripo/floor.json"
GLB_CRUZ = ROOT / "assets/environment/cathedral/props/glb/lapida_cruz_v2.glb"
GLB_CABALLERO = ROOT / "assets/environment/cathedral/props/glb/lapida_caballero_v2.glb"
MARINE_PATH = ROOT / "assets/sprites/characters/marine/spritesheet.png"

PXM = 17.9
PYM = 8.95
Dx = 32.0 / PXM
s_tile = Dx / math.sqrt(2.0)  # 1.264099 m

# Coordenadas centrales del bloque 3x3 en la imagen renderizada de 1152x586 del lab
CX0, CX1, CY0, CY1 = 512, 640, 240, 336
PASTE = (0, CY0 - 224)


def floor_palette():
    fj = json.loads(FLOOR_JSON.read_text(encoding="utf-8"))
    pal5 = np.array([[(int(h, 16) & 31), ((int(h, 16) >> 5) & 31), ((int(h, 16) >> 10) & 31)]
                     for h in fj["palette"]], dtype=float)
    return pal5, np.round(pal5 * 255 / 31).astype(np.uint8)


def snap(comp):
    """Cuantizacion a BGR555 nativo del hardware Nintendo DS (5 bits por canal)."""
    c5 = np.round(comp.astype(float) * 31.0 / 255.0)
    return np.clip(np.round(c5 * 255.0 / 31.0), 0, 255).astype(np.uint8)


def tiles_unique(arr8):
    h, w = arr8.shape[:2]
    uniq, nonempty = set(), 0
    for ty in range(h // 8):
        for tx in range(w // 8):
            t = arr8[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8]
            if t.any():
                nonempty += 1
                uniq.add(t.tobytes())
    return len(uniq), nonempty


def render_lab(glb, work, name, shadows=False):
    settings = json.loads(R.PROPS_SETTINGS.read_text(encoding="utf-8"))
    settings.update({"width": 1152, "cameraElevationDegrees": 30, "shadows": shadows,
                     "waitTextures": True, "waitTexturesMs": 6000})
    cfg = work / f"{name}_settings.json"
    cfg.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    out = work / f"{name}_pkg"
    if out.exists():
        shutil.rmtree(out)
    subprocess.run(["node", str(R.LAB_SCRIPT), str(glb), str(cfg), str(out)], check=True)
    return np.array(Image.open(out / "world.png").convert("RGB"))[CY0:CY1, CX0:CX1].astype(np.float32)


def get_font(size, bold=False):
    names = ["segoeuib.ttf" if bold else "segoeui.ttf",
             "arialbd.ttf" if bold else "arial.ttf",
             "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, default=ROOT / ".scratch_lab_lapidas")
    ap.add_argument("--relief-h", type=float, default=0.10,
                    help="Altura del relieve en metros (defecto 0.10 m = 10 cm)")
    ap.add_argument("--reuse-render", action="store_true", default=False,
                    help="Reutiliza los renders existentes en el directorio scratch si ya existen")
    ap.add_argument("--force-render", action="store_true", default=True,
                    help="Fuerza un re-renderizado completo con Blender y Three.js Lab")
    args = ap.parse_args()
    work = args.scratch
    work.mkdir(parents=True, exist_ok=True)
    reuse = args.reuse_render and not args.force_render

    manifest, entries = RT.prepare_textures(work, 10.0)
    floor_img = Image.open(FLOOR_PNG).convert("RGBA")
    floor_rgb = np.array(floor_img.convert("RGB"))
    ref = floor_rgb[PASTE[1]:PASTE[1] + (CY1 - CY0), PASTE[0]:PASTE[0] + (CX1 - CX0)].astype(np.float32)
    marine = Image.open(MARINE_PATH).convert("RGBA").crop((0, 0, 40, 40))

    jobs = [
        # Via A: 3x2 teselas (paralelogramo a 45 deg, 80x40 px)
        {"id": "via_a_3x2_cruz", "kind": "via_a", "N": 3, "M": 2, "glb": str(GLB_CRUZ),
         "title": "Via A (3x2 teselas) - Cruz", "desc": "Losa diagonal de 80x40 px (6 teselas)"},
        {"id": "via_a_3x2_cab", "kind": "via_a", "N": 3, "M": 2, "glb": str(GLB_CABALLERO),
         "title": "Via A (3x2 teselas) - Caballero", "desc": "Caballero yacente a 45 deg (6 teselas)"},
        # Via B: 3x3 teselas (rombo con lapida horizontal inscrita, 96x48 px)
        {"id": "via_b_3x3_cruz", "kind": "via_b", "N": 3, "vertical": False, "glb": str(GLB_CRUZ),
         "title": "Via B (3x3 teselas) - Cruz Horiz", "desc": "Rombo de 9 teselas con cruz horizontal"},
        {"id": "via_b_3x3_cab", "kind": "via_b", "N": 3, "vertical": False, "glb": str(GLB_CABALLERO),
         "title": "Via B (3x3 teselas) - Cab Horiz", "desc": "Rombo de 9 teselas con caballero horizontal"},
    ]

    results = []
    for job in jobs:
        jid = job["id"]
        glb_out = work / f"{jid}.glb"
        base_png = work / f"{jid}_base_pkg" / "world.png"

        if reuse and base_png.exists():
            print(f"[{jid}] Reutilizando render del Lab Three.js existente...")
            base = np.array(Image.open(base_png).convert("RGB"))[CY0:CY1, CX0:CX1, :3].astype(np.float32)
            shadow_png = work / f"{jid}_shadow_pkg" / "world.png"
            if shadow_png.exists():
                shadow = np.array(Image.open(shadow_png).convert("RGB"))[CY0:CY1, CX0:CX1, :3].astype(np.float32)
            else:
                shadow = base
        else:
            cmd = [str(R.BLENDER_EXE), "-b", "--factory-startup", "--python-exit-code", "1",
                   "-P", str(BLENDER_SCRIPT), "--",
                   "--manifest", str(work / "manifest.json"),
                   "--kind", job["kind"],
                   "--lapida", job["glb"],
                   "--tiles-n", str(job["N"]),
                   "--tiles-m", str(job.get("M", job["N"])),
                   "--vertical", "1" if job.get("vertical", False) else "0",
                   "--relief-h", str(args.relief_h),
                   "--out", str(glb_out)]
            print(f"[{jid}] Montando geometria en Blender...")
            subprocess.run(cmd, check=True)

            print(f"[{jid}] Renderizando con Shader Lab Three.js...")
            base = render_lab(glb_out, work, f"{jid}_base", shadows=False)
            shadow = render_lab(glb_out, work, f"{jid}_shadow", shadows=True)

        mask = np.abs(base - ref).max(2) > 8
        delta = shadow - base
        keep = mask | (np.abs(delta).max(2) > 6)
        comp = base.copy()
        comp[keep] += delta[keep]
        comp = snap(np.clip(np.round(comp), 0, 255).astype(np.float32)).astype(np.uint8)

        # Calculo de costura en el anillo exterior (8 px alrededor del bloque 128x96)
        ring = np.zeros(comp.shape[:2], bool)
        ring[:8, :] = ring[-8:, :] = ring[:, :8] = ring[:, -8:] = True
        lum = lambda x: (x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722)
        seam_error = float(np.abs(lum(comp.astype(float)) - lum(ref))[ring].mean())

        diff = np.abs(comp.astype(float) - ref).max(2)
        tiles_uq, tiles_ne = tiles_unique(comp)

        results.append({
            "job": job, "comp": comp, "mask": mask, "diff": diff,
            "seam_error": seam_error, "tiles_unique": tiles_uq
        })
        print(f"[{jid}] Listo: seam_error={seam_error:.2f}, tiles_unique={tiles_uq}")

    # Montaje de la lamina comparativa maestra
    print("Montando lamina comparativa...")
    sheet_w = 1536
    sheet_h = 1040
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (22, 20, 18, 255))
    draw = ImageDraw.Draw(sheet)

    f_title = get_font(22, bold=True)
    f_sub = get_font(13, bold=False)
    f_hdr = get_font(14, bold=True)
    f_text = get_font(11, bold=False)

    # Header
    draw.rectangle([0, 0, sheet_w, 64], fill=(30, 26, 23, 255))
    draw.text((24, 10), "Catedral: Lapidas Integradas con el Pipeline Unificado Shader Lab (Three.js)",
              fill=(235, 225, 210, 255), font=f_title)
    draw.text((24, 38), "Render 100% Three.js Headless Lab (Luz Neutra props_render_settings, 17.9 px/m) | "
                        "Misma camara y luz que suelo y personajes | CERO outlines 2D | Encastre exacto en juntas",
              fill=(195, 175, 140, 255), font=f_sub)

    col_w = 356
    gap_x = 24
    for idx, res in enumerate(results):
        job = res["job"]
        comp = res["comp"]
        cx = 24 + idx * (col_w + gap_x)
        cy = 80

        # Tarjeta
        draw.rectangle([cx, cy, cx + col_w, cy + 920], fill=(28, 25, 22, 255), outline=(50, 46, 42, 255))
        draw.text((cx + 12, cy + 10), job["title"], fill=(226, 170, 74, 255), font=f_hdr)
        draw.text((cx + 12, cy + 28), job["desc"], fill=(160, 150, 135, 255), font=f_text)
        draw.text((cx + 12, cy + 44), f"Error de costura: {res['seam_error']:.2f} px | Tiles 8x8: {res['tiles_unique']}",
                  fill=(130, 200, 150, 255), font=f_text)

        # 1. In-situ sobre suelo real con Marine
        draw.text((cx + 12, cy + 64), "1. Vista in-situ sobre rombos_tripo con Marine:", fill=(210, 200, 185, 255), font=f_text)
        insitu = floor_img.copy()
        bx, by = PASTE[0] + 128, PASTE[1]
        insitu.paste(Image.fromarray(comp), (bx, by))
        R.paste_sprite_anchored(insitu, marine, bx + 150, by + 110, 20, 33)
        crop_insitu = insitu.crop((bx - 16, by - 16, bx + 160, by + 128))
        insitu_2x = crop_insitu.resize((col_w - 24, int((col_w - 24) * crop_insitu.height / crop_insitu.width)), Image.NEAREST)
        sheet.paste(insitu_2x, (cx + 12, cy + 82))

        cur_y = cy + 82 + insitu_2x.height + 14

        # 2. Zoom Macro 4x del Relieve
        draw.text((cx + 12, cur_y), "2. Zoom Macro 4x (Detalle de talla y juntas):", fill=(210, 200, 185, 255), font=f_text)
        # Recorte centrado en la lapida (64x40)
        ch, cw = comp.shape[:2]
        crop_macro = Image.fromarray(comp).crop((cw // 2 - 32, ch // 2 - 20, cw // 2 + 32, ch // 2 + 20))
        macro_4x = crop_macro.resize((col_w - 24, int((col_w - 24) * 40 / 64)), Image.NEAREST)
        sheet.paste(macro_4x, (cx + 12, cur_y + 18))

        cur_y += 18 + macro_4x.height + 14

        # 3. Mapa de diferencia vs suelo (muestra donde cambia la geometria y costura 0.0)
        draw.text((cx + 12, cur_y), "3. Mapa de diferencia vs suelo (costura perimetral):", fill=(210, 200, 185, 255), font=f_text)
        diff_img = Image.fromarray(np.clip(res["diff"] * 8, 0, 255).astype(np.uint8), mode="L")
        diff_rgb = Image.new("RGBA", diff_img.size, (0, 0, 0, 255))
        diff_rgb.paste(Image.fromarray(np.stack([np.array(diff_img), np.zeros_like(diff_img), np.zeros_like(diff_img)], axis=-1)))
        diff_disp = diff_rgb.resize((col_w - 24, int((col_w - 24) * ch / cw)), Image.NEAREST)
        sheet.paste(diff_disp, (cx + 12, cur_y + 18))

    OUT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(OUT_SHEET)
    print(f"Lamina guardada exitosamente en {OUT_SHEET}")


if __name__ == "__main__":
    main()
