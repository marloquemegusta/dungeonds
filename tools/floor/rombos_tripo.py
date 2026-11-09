#!/usr/bin/env python3
"""Damero de rombos con las losas de Tripo (lote 3): mismo pipeline que tools/floor/rombos.py,
pero las losas son los FBX de assets/environment/cathedral/floor_tiles/ en vez de losas procedurales.

Piedra A: textura original de cada losa. Piedra B: la misma textura recoloreada (mas gris y mas
oscura) hasta que su L* medio quede ~DELTA por debajo de A. Dos variantes:
  - rombos_tripo   : DELTA_L 10 (poco contraste, pedido)
  - rombos_tripo_b : DELTA_L 16 (contraste A/B algo mayor)

Salidas en assets/environment/cathedral/floor/<variant>/:
  tiles.png, floor.json, floor_512x256.png, floor_512x256_x3.png, revision_x3.png, stats.json

Usage:
  python tools/floor/rombos_tripo.py [--variant rombos_tripo|rombos_tripo_b|all] --scratch <dir> [--seed N]
"""
import argparse
import glob
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rombos as R  # noqa: E402  (helpers del pipeline de rombos)

FBM_ROOT = R.ROOT / "assets/environment/cathedral/floor_tiles"
BLENDER_SCRIPT = HERE / "rombos_tripo_blender.py"
OUT_ROOT = R.ROOT / "assets/environment/cathedral/floor"
TEX_SIZE = 512
TEX_BLUR = 4.0              # radio (px a 512) que quita el ruido de la piedra antes del render
DESAT = 0.85
TILE_CAP = 120
COLOR_CAP = 32

# name, id del zip de Tripo (assets/inbox/tripo_convert_<id>*), rol en el damero.
# La lisa ocupa el resto del bloque; las especiales son ESPECIALES_POR_BLOQUE celdas por bloque
# de 128 px (sorteadas con la semilla). Mas especiales por bloque disparan las tiles unicas.
SLABS = [
    ("losa_a", "d9f88a50", "lisa"),
    ("losa_grieta", "ea230fcd", "especial"),
    ("losa_rota", "3f00608c", "especial"),
    ("losa_cera", "799f9815", "especial"),
    ("losa_sangre", "d2e57143", "especial"),
]
ESPECIALES_POR_BLOQUE = 2
VARIANTS = {"rombos_tripo": 10.0, "rombos_tripo_b": 16.0}
reuse_render = False   # fijados desde la linea de comandos en main()
colors = 24
W_LUMA = np.array([0.2126, 0.7152, 0.0722])


def srgb_to_lin(c8):
    c = c8.astype(float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb8(l):
    l = np.clip(l, 0.0, 1.0)
    e = np.where(l <= 0.0031308, 12.92 * l, 1.055 * np.power(l, 1 / 2.4) - 0.055)
    return np.clip(np.round(e * 255), 0, 255).astype(np.uint8)


def lstar_mean(rgb8):
    y = srgb_to_lin(rgb8) @ W_LUMA
    f = np.where(y > 0.008856, np.cbrt(y), 7.787 * y + 16 / 116)
    return float((116 * f - 16).mean())


def recolor_b(rgb8, k):
    """Desatura un poco (hacia la luma) y multiplica la luminancia lineal por k."""
    lin = srgb_to_lin(rgb8)
    y = lin @ W_LUMA
    lin2 = (DESAT * lin + (1 - DESAT) * y[..., None]) * k
    return lin_to_srgb8(lin2)


def find_k(rgb8, target_lstar):
    lo, hi = 0.02, 1.5
    for _ in range(40):
        mid = (lo + hi) / 2
        if lstar_mean(recolor_b(rgb8, mid)) < target_lstar:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def find_color_png(name):
    hits = glob.glob(str(FBM_ROOT / f"{name}.fbm" / "Color_*.png"))
    if len(hits) != 1:
        raise RuntimeError(f"{name}: {len(hits)} texturas Color_*.png (se espera 1)")
    return Path(hits[0])


def prepare_textures(work, delta):
    """Texturas A (originales a 512) y B (recoloreadas a L* - delta) para cada losa."""
    work.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, zip_id, rol in SLABS:
        src = find_color_png(name)
        img = Image.open(src).convert("RGB")
        if img.size != (2048, 2048):
            raise RuntimeError(f"{name}: textura {img.size}, se esperaba 2048")
        small = img.resize((TEX_SIZE, TEX_SIZE), Image.LANCZOS)
        a8 = np.array(small.filter(ImageFilter.GaussianBlur(TEX_BLUR)) if TEX_BLUR > 0 else small)
        a_path = work / f"{name}_A.png"
        Image.fromarray(a8).save(a_path)
        lA = lstar_mean(a8)
        k = find_k(a8, lA - delta)
        b8 = recolor_b(a8, k)
        b_path = work / f"{name}_B.png"
        Image.fromarray(b8).save(b_path)
        entries.append({
            "name": name, "zip_id": zip_id, "rol": rol,
            "fbx": str(FBM_ROOT / f"{name}.fbx"), "color_src": str(src),
            "a_png": str(a_path.resolve()), "b_png": str(b_path.resolve()),
            "lstar_A": round(lA, 2), "lstar_B": round(lstar_mean(b8), 2), "k_B": round(k, 4),
        })
    manifest = work / "manifest.json"
    manifest.write_text(json.dumps({"slabs": entries, "especiales_por_bloque": ESPECIALES_POR_BLOQUE},
                                   indent=2), encoding="utf-8")
    return manifest, entries


def run_blender(manifest, seed, glb_out):
    cmd = [str(R.BLENDER_EXE), "-b", "--factory-startup", "--python-exit-code", "1",
           "-P", str(BLENDER_SCRIPT), "--",
           "--manifest", str(manifest), "--seed", str(seed), "--out", str(glb_out)]
    subprocess.run(cmd, check=True)
    return json.loads(Path(str(glb_out) + ".placement.json").read_text(encoding="utf-8"))


def lab_render(glb_rot, lab_cfg_path, lab_out):
    props = json.loads(R.PROPS_SETTINGS.read_text(encoding="utf-8"))
    settings = dict(props)
    settings.update({"width": 1152, "cameraElevationDegrees": 30, "shadows": False,
                     "waitTextures": True})
    lab_cfg_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    if lab_out.exists():
        shutil.rmtree(lab_out)
    subprocess.run(["node", str(R.LAB_SCRIPT), str(glb_rot), str(lab_cfg_path), str(lab_out)], check=True)
    return Image.open(lab_out / "world.png").convert("RGB")


def measure_contrast(central_rgb):
    """L* medio en el centro de cada rombo A y B (parche 7x7 dentro del rombo)."""
    lab_vals = {"A": [], "B": []}
    for iy in range(8):
        for ix in range(4):
            for fam, cx, cy in (("A", ix * 32 + 16, iy * 16 + 8), ("B", ix * 32, iy * 16)):
                x0, y0 = (cx - 3) % 128, (cy - 3) % 128
                patch = np.take(np.take(central_rgb, range(y0, y0 + 7), axis=0, mode="wrap"),
                                range(x0, x0 + 7), axis=1, mode="wrap")
                lab_vals[fam].append(lstar_mean(patch))
    return round(float(np.mean(lab_vals["A"])), 2), round(float(np.mean(lab_vals["B"])), 2)


def process_variant(variant, delta, scratch, seed):
    print(f"\n==== {variant} (delta L* {delta}) ====")
    work = scratch / variant
    work.mkdir(parents=True, exist_ok=True)
    out_dir = OUT_ROOT / variant
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest, entries = prepare_textures(work, delta)
    print("  texturas:", [(e["name"], e["lstar_A"], e["lstar_B"]) for e in entries])

    glb_raw = work / f"{variant}_tripo.glb"
    glb_rot = work / f"{variant}_tripo_rot.glb"
    world_png = work / f"{variant}_lab_pkg" / "world.png"
    if reuse_render and world_png.exists() and glb_rot.exists():
        print("  [1-3/4] Reutilizando el render del lab previo (--reuse-render)")
        placement = json.loads(Path(str(glb_raw) + ".placement.json").read_text(encoding="utf-8"))
        world = Image.open(world_png).convert("RGB")
    else:
        print("  [1/4] Blender: importar FBX, girar 45 deg, montar 3x3 y exportar GLB")
        placement = run_blender(manifest, seed, glb_raw)

        print("  [2/4] Girar GLB -45 deg en Y")
        R.rotate_glb_y(glb_raw, glb_rot, -45)

        print("  [3/4] Render en el lab (headless)")
        world = lab_render(glb_rot, work / f"{variant}_lab_settings.json", work / f"{variant}_lab_pkg")
    world_arr = np.array(world)
    central_rgb = world_arr[96:480, 384:768][128:256, 128:256]
    mean_a_render, mean_b_render = measure_contrast(central_rgb)

    print("  [4/4] Cuantizar a BGR555, deduplicar tiles (tope %d)" % TILE_CAP)
    lab_idx, centers5 = R.quantize_bgr555(central_rgb, max_colors=colors)
    pal_hex = [R.bgr555_hex(c) for c in centers5]
    rgb_pal = R.to8(centers5)
    tiles, fmap = R.deduplicate_tiles(lab_idx, centers5, max_target_tiles=TILE_CAP)
    if len(tiles) > TILE_CAP:
        raise RuntimeError(f"{variant}: {len(tiles)} tiles unicos > tope {TILE_CAP}")
    rebuilt_idx = R.rebuild_from_tiles(tiles, fmap)
    rebuilt_rgb = rgb_pal[rebuilt_idx]

    atlas = np.zeros((8, 8 * len(tiles), 3), dtype=np.uint8)
    for i, t in enumerate(tiles):
        atlas[:, i * 8:(i + 1) * 8] = rgb_pal[t]
    Image.fromarray(atlas).save(out_dir / "tiles.png")

    floor_json = {"palette": pal_hex, "tiles": [t.reshape(-1).tolist() for t in tiles],
                  "floor_map": fmap, "period_tiles": [16, 16]}
    (out_dir / "floor.json").write_text(json.dumps(floor_json, separators=(",", ":")), encoding="utf-8")

    # Reconstruccion SOLO desde el JSON
    j = json.loads((out_dir / "floor.json").read_text(encoding="utf-8"))
    pal_back = np.array([[(int(h, 16) & 31), (int(h, 16) >> 5) & 31, (int(h, 16) >> 10) & 31] for h in j["palette"]])
    tiles_back = [np.array(t, dtype=np.uint8).reshape(8, 8) for t in j["tiles"]]
    idx_back = R.rebuild_from_tiles(tiles_back, j["floor_map"])
    rgb_from_json = R.to8(pal_back)[idx_back]
    json_exact = bool(np.array_equal(rgb_from_json, rebuilt_rgb))

    tile_512x256 = np.tile(rgb_from_json, (2, 4, 1))
    img_512x256 = Image.fromarray(tile_512x256)
    img_512x256.save(out_dir / "floor_512x256.png")
    img_512x256.resize((512 * 3, 256 * 3), Image.NEAREST).save(out_dir / "floor_512x256_x3.png")

    seam_y = float(np.abs(tile_512x256[128].astype(float) - tile_512x256[127].astype(float)).mean())
    seam_x = float(np.abs(tile_512x256[:, 128].astype(float) - tile_512x256[:, 127].astype(float)).mean())

    base_revision = Image.fromarray(np.tile(rgb_from_json, (2, 2, 1))).convert("RGBA").crop((0, 0, 256, 192))
    marine = Image.open(R.MARINE_PATH).convert("RGBA").crop((0, 0, 40, 40))
    banco = Image.open(R.BANCO_PATH).convert("RGBA")
    santo = Image.open(R.SANTO_PATH).convert("RGBA")
    R.paste_sprite_anchored(base_revision, banco, 56, 120, banco.width // 2, banco.height)
    R.paste_sprite_anchored(base_revision, santo, 200, 130, santo.width // 2, santo.height)
    R.paste_sprite_anchored(base_revision, marine, 128, 140, 20, 33)
    base_revision.convert("RGB").resize((256 * 3, 192 * 3), Image.NEAREST).save(out_dir / "revision_x3.png")

    slabs_stats = []
    for e in entries:
        pl = placement["slabs"][e["name"]]
        slabs_stats.append({
            "losa": e["name"], "zip_id": e["zip_id"], "rol": e["rol"],
            "celdas_bloque_central": placement["counts_bloque_central"][e["name"]],
            "lstar_A_textura": e["lstar_A"], "lstar_B_textura": e["lstar_B"], "k_B": e["k_B"],
            "caras_fbx_a_decimate": [pl["faces_in"], pl["faces_out"]],
            "dims_fbx_m_xyz": pl["dims_fbx"],
        })

    stats = {
        "variant": variant,
        "tiles_unicos": len(tiles),
        "tope_tiles": TILE_CAP,
        "colores": len(pal_hex),
        "tope_colores": COLOR_CAP,
        "delta_lstar_objetivo_textura": delta,
        "lstar_medio_render_A_B": [mean_a_render, mean_b_render],
        "delta_lstar_medido_render": round(mean_a_render - mean_b_render, 2),
        "costura_exacta": bool(seam_x < 8.2 and seam_y < 8.2),
        "discontinuidad_costura_media_8bit": round(max(seam_x, seam_y), 3),
        "reconstruccion_exacta": json_exact,
        "px_m_horizontal": 17.9,
        "px_m_profundidad": 8.95,
        "rombo_ancho_px": 32,
        "rombo_alto_px": 16,
        "seed": seed,
        "losas": slabs_stats,
        "mean_rgb_reconstruido": [round(float(c), 1) for c in rgb_from_json.mean((0, 1))],
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("tiles_unicos", "colores", "costura_exacta",
                                            "reconstruccion_exacta", "delta_lstar_medido_render")}, indent=2))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=(*VARIANTS, "all"), default="all")
    ap.add_argument("--scratch", type=Path, default=R.ROOT / ".scratch_rombos_tripo")
    ap.add_argument("--seed", type=int, default=20261108)
    ap.add_argument("--colors", type=int, default=24, help="colores del suelo antes de BGR555 (tope 32)")
    ap.add_argument("--reuse-render", action="store_true", help="reutiliza el world.png del lab si existe")
    args = ap.parse_args()
    global reuse_render, colors
    reuse_render, colors = args.reuse_render, args.colors
    names = list(VARIANTS) if args.variant == "all" else [args.variant]
    for v in names:
        process_variant(v, VARIANTS[v], args.scratch, args.seed)


if __name__ == "__main__":
    main()
