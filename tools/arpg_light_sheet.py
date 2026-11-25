#!/usr/bin/env python3
"""Hoja de contacto de UNA luz de sala del ARPG (sin ROM): suelo horneado con el tinte de la luz + heroe, un enemigo y
dos props con su sombra dura. 4x NEAREST. Lee scratch/arpg_luz/<luz>/ (lo que deja arpg_light_pack.py).

uso: python tools/arpg_light_sheet.py <luz> [out_dir]   (por defecto walkthroughs/arpg-luz-sala/assets/)
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arpg_light_chars as alc          # noqa: E402

ENEMY_ORDER = [("monja", "exvoto"), ("monaguillo", "monaguillo"), ("bebe", "exvoto_bebe"), ("cireneo", "cireneo"),
               ("ojo", "ojo"), ("abanderado", "abanderado"), ("parroco", "exvoto_parroco_run")]
W, H, SCALE = 256, 128, 4
FLOOR_CROP = (128, 336)       # esquina de un trozo de suelo limpio del kit horneado (sin piezas)


def shade(canvas, mask_xy):
    ys, xs = mask_xy
    canvas[ys, xs, :3] = canvas[ys, xs, :3] // 2


def paste_shadow(canvas, shadow_img, ox, oy):
    """Sombra dura: oscurece al 50 % el suelo bajo los pixeles de la mascara (como la DS)."""
    a = np.asarray(shadow_img.convert("RGBA"))
    m = (a[..., 3] > 127) if a[..., 3].max() > 0 and a[..., 3].min() < 255 else (a[..., :3].max(axis=2) > 127)
    ys, xs = np.nonzero(m)
    ys += oy; xs += ox
    ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
    shade(canvas, (ys[ok], xs[ok]))


def paste_sprite(canvas, img, ox, oy):
    a = np.asarray(img.convert("RGBA"))
    h, w = a.shape[:2]
    for y in range(h):
        for x in range(w):
            if a[y, x, 3] >= 128 and 0 <= oy + y < H and 0 <= ox + x < W:
                canvas[oy + y, ox + x, :3] = a[y, x, :3]


def char_frame(base, name, d, f):
    s = json.loads((base / "chars" / name / "settings.json").read_text(encoding="utf-8"))
    fw, fh = (int(v) for v in s["frameSize"].split("x"))
    ax, ay = s["anchor"]
    sheet = Image.open(base / "chars" / name / "spritesheet.png").convert("RGBA")
    spr = sheet.crop((f * fw, d * fh, (f + 1) * fw, (d + 1) * fh))
    shp = base / "chars" / name / "shadow.png"
    shd, sw, sh = None, 0, 0
    if shp.exists() and "shadowSize" in s:
        sw, sh = s["shadowSize"]
        shd = Image.open(shp).convert("RGBA").crop((f * sw, d * sh, (f + 1) * sw, (d + 1) * sh))
    return spr, (ax, ay), shd, (sw // 2, sh // 2)


def main():
    light_id = sys.argv[1]
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "walkthroughs/arpg-luz-sala/assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = alc.load_lights()
    light = next(l for l in doc["luces"] if l["id"] == light_id)
    base = ROOT / "scratch/arpg_luz" / light_id
    prev = Image.open(base / "kit_preview.png").convert("RGBA")
    canvas = np.asarray(prev.crop((FLOOR_CROP[0], FLOOR_CROP[1], FLOOR_CROP[0] + W, FLOOR_CROP[1] + H))).copy()

    types = alc.room_enemies(light["rooms"])
    enemy = next(n for t, n in ENEMY_ORDER if t in types)
    # props: los dos con mas sombra (sin velas ni lapidas)
    cand = []
    for sub in ("props", "kit_props"):            # props de sala y, si faltan, piezas del kit (misma luz)
        for p in sorted((base / sub).iterdir()):
            if not (p / "color.png").exists() or p.name in ("vela", "verja", "lapida_pie", "capullo") or any(c[2] == p.name for c in cand):
                continue
            sh = np.asarray(Image.open(p / "shadow.png").convert("L")) > 127 if (p / "shadow.png").exists() else np.zeros((1, 1))
            cand.append((int(sub == "props") * 100000 + int(sh.sum()), sub, p.name))
    props = [(sub, n) for _, sub, n in sorted(cand, reverse=True)[:2]]

    items = []      # (baseline_y, sprite, ox, oy, shadow, sox, soy)
    spr, (ax, ay), shd, (cx, cy) = char_frame(base, "corazon", 0, 0)
    items.append((108, spr, 100 - ax, 108 - ay, shd, 100 - cx, 108 - cy))
    spr, (ax, ay), shd, (cx, cy) = char_frame(base, enemy, 0, 0)
    items.append((108, spr, 156 - ax, 108 - ay, shd, 156 - cx, 108 - cy))
    for i, (sub, n) in enumerate(props):
        pd = base / sub / n
        meta = json.loads((pd / "meta.json").read_text(encoding="utf-8"))
        col = Image.open(pd / "color.png").convert("RGBA")
        px, py = (24 if i == 0 else 196) - col.width // 2, 104 - col.height
        dx, dy = meta.get("shadow_offset_px", [0, 0])
        shd = Image.open(pd / "shadow.png") if (pd / "shadow.png").exists() else None
        items.append((104, col, px, py, shd, px + dx, py + dy))
    for it in items:
        if it[4] is not None:
            paste_shadow(canvas, it[4], it[5], it[6])
    for it in sorted(items, key=lambda t: t[0]):
        paste_sprite(canvas, it[1], it[2], it[3])
    im = Image.fromarray(canvas).convert("RGB").resize((W * SCALE, H * SCALE), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    txt = f"{light['id']}  {light['nombre']}  | heroe, {enemy}, {props[0][1]}, {props[1][1]}"
    dr.rectangle((0, 0, im.width, 18), fill=(0, 0, 0))
    dr.text((6, 3), txt, fill=(235, 235, 235))
    out = out_dir / f"{light_id}.png"
    im.save(out)
    print(out, enemy, props)


if __name__ == "__main__":
    main()
