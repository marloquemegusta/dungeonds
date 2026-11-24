#!/usr/bin/env python3
"""Poster del acto I: el escenario real (suelo, muros, props) de las 15 salas y sus pasillos, visto con la
camara del juego (vista de 256 px de ancho: 24 px de muro + 208 de suelo + 24 de muro).

Uso: python tools/poster/poster_acto1.py [--config tools/poster/poster_acto1.json] [--out DIR] [--name poster_acto1_v0]

Fidelidad: reutiliza del baker (tools/bake_cathedral_kit.py) las capas de pieza (arte, sombra, huella), el suelo
(floor.json), el muro (muro_izq_128.png) y la paleta de props; la colocacion sigue enc_place_piece() de
source/strip.c (ancla a rejilla de tiles, espejo, descarte por solape de tiles) y enc_block_pieces()
(espejo de santo/sacos, banco roto 1 de cada 4). Las plantas y espejos se fijan en el JSON (en la ROM salen de la
semilla de cada partida). No se dibuja: la barrera/verja (sprites OBJ), las lapidas (hash de bloque), enemigos.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import bake_cathedral_kit as bk  # noqa: E402

VIEW_W, BLOCK_H = 256, 384
VIEW_X0 = 128                      # mundo x del borde izquierdo de la vista
FLOOR_X, FLOOR_W = 152, 208        # include/encounters_act1.h
WALL_L = FLOOR_X - VIEW_X0         # 24 px de muro por lado
PLAN = ROOT / "tools/encuentros/acto1_v2.json"
FLOOR_DIR = ROOT / "assets/environment/cathedral/floor/rombos_tripo"
MIRROR_SWAP = bk.MIRROR_SWAP
BG = (14, 12, 18)


def to_rgb(arr555):
    a = arr555.astype(np.int32)
    return np.stack([(a & 31) * 255 // 31, ((a >> 5) & 31) * 255 // 31, ((a >> 10) & 31) * 255 // 31],
                    axis=-1).astype(np.uint8)


class Kit:
    def __init__(self):
        colors, raw, grid = bk.read_floor(FLOOR_DIR)
        period = np.zeros((128, 128), np.uint16)
        for ty in range(16):
            for tx in range(16):
                cell = grid[ty][tx]
                t = np.array([colors[i] for i in raw[cell["t"]]], np.uint16).reshape(8, 8)
                if cell["h"]: t = t[:, ::-1]
                if cell["v"]: t = t[::-1, :]
                period[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = t
        xs = (VIEW_X0 + np.arange(VIEW_W)) % 128
        self.floor_block = period[np.arange(BLOCK_H)[:, None] % 128, xs[None, :]]
        self.props, self.prop_lab = bk.read_prop_palette()
        self.prop_arr = np.array(self.props, np.uint16)
        self.wall = self._wall()
        self._layouts = {}

    def _wall(self):
        src = np.asarray(Image.open(bk.WALL_PNG).convert("RGBA"))
        op = src[:, :, 3] >= 128
        rgb = np.where(op[:, :, None], src[:, :, :3], np.array(bk.WALL_BACKDROP_RGB, np.uint8))
        q = bk.quantize_props(Image.fromarray(np.dstack([rgb, np.full(op.shape, 255, np.uint8)])), self.prop_lab)
        w = self.prop_arr[q]                                   # 128 x 48 en 555
        out = np.zeros((BLOCK_H, VIEW_W), np.uint16)
        rows = np.arange(BLOCK_H) % 128
        for u in range(WALL_L):
            out[:, u] = w[rows, WALL_L + u]                    # cols 3..5 del muro izquierdo
            out[:, FLOOR_X + FLOOR_W - VIEW_X0 + u] = w[rows, 47 - u]   # espejo del derecho
        return out

    def layout(self, name):
        if name not in self._layouts:
            lay = bk.source_layout(name)
            q = bk.quantize_props(Image.fromarray(lay["rgba"]), self.prop_lab)
            op = lay["rgba"][:, :, 3] >= 128
            sh = lay["shadow"] if lay["shadow"] is not None else np.zeros(op.shape, bool)
            self._layouts[name] = {"w": lay["w"], "h": lay["h"], "pix": self.prop_arr[q], "op": op, "sh": sh & ~op,
                                   "anchor": lay["foot_anchor_y_px"]}
        return self._layouts[name]


def tile_mask(lay):
    h, w = lay["h"] // 8, lay["w"] // 8
    return (lay["op"] | lay["sh"]).reshape(h, 8, w, 8).any(axis=(1, 3))


def block_pieces(plan_pieces, mirror, block, skip_relicario=False):
    """enc_block_pieces(): espejo de piezas asimetricas y banco roto (1 de cada 4, solo fila de fase 0)."""
    out = []
    for i, pc in enumerate(plan_pieces):
        piece = pc["piece"]
        if skip_relicario and piece == "relicario":
            continue
        if (piece == "banco_grupo4" and (((pc["y"] + 4) >> 3) & 15) == 0 and
                (bk.hash32(((block & 0xffffffff) * 0x9e3779b9 & 0xffffffff) ^ (i * 0x85ebca6b & 0xffffffff)
                           ^ 0x42524b4e) & 3) == 0):
            piece = "banco_grupo4_roto"
        if mirror:
            piece = MIRROR_SWAP.get(piece, piece)
        out.append({"piece": piece, "lx": pc["x"], "ly": pc["y"], "mirror": mirror})
    return out


def place(kit, canvas555, pieces, floor555=None, sprites=None):
    """Estampa las piezas como enc_place_piece(): ancla a tile, sin solape de tiles, dentro del suelo.
    Con floor555/sprites (vista select): floor555 recibe solo las sombras (suelo sin props) y sprites
    recoge cada pieza como (x0, y0, mascara opaca, ancla_x, ancla_y) en px del bloque."""
    occupied = set()
    placed = []
    for p in pieces:
        lay = kit.layout(p["piece"])
        mirror = p.get("mirror", 0)
        nominal = FLOOR_X + FLOOR_W - (p["lx"] + lay["w"]) if mirror else FLOOR_X + p["lx"]
        tx, ty = (nominal + 4) // 8, (p["ly"] + 4) // 8
        mask = tile_mask(lay)
        th, tw = mask.shape
        if tx < FLOOR_X // 8 or tx + tw > (FLOOR_X + FLOOR_W) // 8 or ty < 0 or ty + th > BLOCK_H // 8:
            placed.append((p["piece"], None)); continue
        cells = {(tx + c, ty + r) for r in range(th) for c in range(tw) if mask[r, c]}
        if cells & occupied:
            placed.append((p["piece"], None)); continue
        occupied |= cells
        for r in range(th):
            for c in range(tw):
                if not mask[r, c]: continue
                x0, y0 = (tx + c) * 8 - VIEW_X0, (ty + r) * 8
                sl = (slice(r * 8, r * 8 + 8), slice(c * 8, c * 8 + 8))
                dst = canvas555[y0:y0 + 8, x0:x0 + 8]
                shaded = ((dst & 0x7BDE) >> 1) | 0x8000
                tile = np.where(lay["sh"][sl], shaded, dst)
                canvas555[y0:y0 + 8, x0:x0 + 8] = np.where(lay["op"][sl], lay["pix"][sl], tile)
                if floor555 is not None:
                    fd = floor555[y0:y0 + 8, x0:x0 + 8]
                    floor555[y0:y0 + 8, x0:x0 + 8] = np.where(lay["sh"][sl], ((fd & 0x7BDE) >> 1) | 0x8000, fd)
        px0, py0 = tx * 8 - VIEW_X0, ty * 8
        if sprites is not None:
            sprites.append({"piece": p["piece"], "x0": px0, "y0": py0, "op": lay["op"],
                            "ax": px0 + lay["w"] / 2.0, "ay": py0 + lay["anchor"]})
        placed.append((p["piece"], (px0, py0)))
    return placed


def apply_light(img, luz):
    """img: RGB uint8 (h, w, 3). 'neutral' no toca nada. Campos: tinte [r,g,b] 0-255 (multiplicativo),
    gradiente {abajo, arriba} (brillo 0-1 en el borde inferior/superior del bloque), vineta 0-1 (esquinas)."""
    luz = luz or {}
    tint = luz.get("tinte", [255, 255, 255])
    grad = luz.get("gradiente")
    vin = luz.get("vineta", 0)
    if not grad and not vin and tint == [255, 255, 255]:
        return img
    f = img.astype(np.float64) * (np.array(tint, np.float64) / 255.0)
    h, w = img.shape[:2]
    if grad:
        f = f * np.linspace(grad.get("arriba", 1.0), grad.get("abajo", 1.0), h)[:, None, None]
    if vin:
        yy, xx = np.mgrid[0:h, 0:w]
        dist = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / 1.414
        f = f * (1.0 - vin * np.clip(dist, 0, 1) ** 2)[:, :, None]
    return np.clip(f, 0, 255).astype(np.uint8)


def render_block(kit, pieces, luz, extra, quitar):
    canvas = kit.floor_block.copy()
    m = kit.wall != 0
    canvas[m] = kit.wall[m]
    pieces = [p for p in pieces if not any(p["piece"].startswith(q) for q in quitar)]
    pieces += [{"piece": e["piece"], "lx": e["x"], "ly": e["y"], "mirror": e.get("mirror", 0)} for e in extra]
    placed = place(kit, canvas, pieces)
    return apply_light(to_rgb(canvas), luz), placed


def font(size):
    for f in ("consola.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def is_boss(i):
    return i in (4, 9, 14)

# ---------------------------------------------------------------- vista "select" (mapa de SELECT del ARPG)
# source/arpg_map.c (proto/arpg): plano girado 45 grados y aplastado 2:1, sx = (X + Y) * K, sy = (X - Y) * K / 2
# con X al este e Y al norte (px del mundo; los bloques se apilan hacia el norte). Aqui K = 1 (1 px de suelo = 1 px).
def render_block_select(kit, pieces, luz, extra, quitar):
    full = kit.floor_block.copy()
    m = kit.wall != 0
    full[m] = kit.wall[m]
    floor = full.copy()
    pieces = [p for p in pieces if not any(p["piece"].startswith(q) for q in quitar)]
    pieces += [{"piece": e["piece"], "lx": e["x"], "ly": e["y"], "mirror": e.get("mirror", 0)} for e in extra]
    sprites = []
    place(kit, full, pieces, floor555=floor, sprites=sprites)
    return apply_light(to_rgb(floor), luz), apply_light(to_rgb(full), luz), sprites


def sel_xy(X, Y):
    return X + Y, (X - Y) / 2.0


def paste_floor(canvas, img, b, ox, oy, resample):
    """Transforma el bloque b (256x384, origen Y0 = b*384) al plano de SELECT y lo pega en canvas."""
    Y0 = b * BLOCK_H
    bx, by = Y0, int(np.floor(-(Y0 + BLOCK_H) / 2.0)) - 1
    w, h = VIEW_W + BLOCK_H + 2, (VIEW_W + BLOCK_H) // 2 + 3
    src = Image.fromarray(img).convert("RGBA")
    coefs = (0.5, 1.0, (bx + 2 * by) / 2.0, -0.5, 1.0, Y0 + BLOCK_H - (bx - 2 * by) / 2.0)
    out = src.transform((w, h), Image.AFFINE, coefs, resample=resample)
    canvas.paste(out, (bx + ox, by + oy), out)


def paste_sprite(canvas, rgb, spr, Y0, ox, oy):
    """Pieza erguida: cada columna cuelga de su punto de suelo (cizalla vertical dx/2 sobre el plano de SELECT)."""
    op = spr["op"]
    h, w = op.shape
    x0, y0 = spr["x0"], spr["y0"]
    ys, xs = max(0, -y0), max(0, -x0)
    tile = np.zeros((h, w, 4), np.uint8)
    reg = rgb[y0:y0 + h, x0:x0 + w]
    hh, ww = reg.shape[:2]
    tile[:hh, :ww, :3] = reg
    tile[:hh, :ww, 3] = np.where(op[:hh, :ww], 255, 0)
    pad = w // 2 + 2
    out = np.zeros((h + pad, w, 4), np.uint8)
    for c in range(w):
        s = int(round((c - w / 2.0) / 2.0 + w / 4.0))
        out[s:s + h, c] = tile[:, c]
    sx, sy = sel_xy(spr["ax"], Y0 + BLOCK_H - spr["ay"])
    rel = spr["ay"] - y0
    img = Image.fromarray(out)
    canvas.paste(img, (int(round(sx - w / 2.0)) + ox, int(round(sy - rel - w / 4.0)) + oy), img)
    return sy


def compose_select(kit, cfg, plan, only=None, resample=Image.NEAREST):
    entries = {e["stage"]: e for e in cfg["stages"]}
    nb = 30
    ox, oy = 300, int((nb * BLOCK_H) / 2) + 140
    W = VIEW_W + nb * BLOCK_H + 2 + 700
    H = oy + 640 + 200
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    jobs, labels = [], []
    for i in range(15):
        if only and (i + 1) not in only:
            continue
        e = entries[i + 1]
        enc_block = 3 - 2 * i
        if is_boss(i):
            room_pieces, mirror = [], 0
        else:
            mirror = e.get("espejo", 0)
            room_pieces = block_pieces(plan["plantas"][e["planta"]]["pieces"], mirror, enc_block)
        fl, fu, sp = render_block_select(kit, room_pieces, e.get("luz"), e.get("props_extra", []), e.get("props_quitar", []))
        jobs.append((2 * i, fl, fu, sp))
        tier = "jefe" if is_boss(i) else plan["act"]["tiers"][i - (i > 4) - (i > 9)]
        labels.append((2 * i, [f"SALA {i + 1}", "JEFE" if is_boss(i) else e["planta"] + (" (esp.)" if mirror else ""), tier]))
        pe = e.get("pasillo", {})
        cp = block_pieces(plan["pasillo"]["pieces"], i & 1, enc_block - 1, skip_relicario=(i == 14))
        fl, fu, sp = render_block_select(kit, cp, pe.get("luz"), pe.get("props_extra", []), pe.get("props_quitar", []))
        jobs.append((2 * i + 1, fl, fu, sp))
        labels.append((2 * i + 1, [f"pasillo {i + 1}"]))
    for b, fl, fu, sp in jobs:
        paste_floor(canvas, fl, b, ox, oy, resample)
    allspr = []
    for b, fl, fu, sp in jobs:
        for s in sp:
            allspr.append((sel_xy(s["ax"], b * BLOCK_H + BLOCK_H - s["ay"])[1], b, fu, s))
    allspr.sort(key=lambda t: t[0])
    for _, b, fu, s in allspr:
        paste_sprite(canvas, fu, s, b * BLOCK_H, ox, oy)
    d = ImageDraw.Draw(canvas)
    f_mid, f_sm = font(30), font(22)
    d.text((40, 30), cfg.get("titulo", "Acto I") + "  -  vista de mapa (SELECT)", fill=(205, 195, 170), font=font(44))
    for b, lines in labels:
        sx, sy = sel_xy(VIEW_W + 20, b * BLOCK_H + 260)
        for k, t in enumerate(lines):
            d.text((sx + ox, sy + oy + 34 * k), t, fill=(225, 205, 150) if k == 0 else (150, 145, 135),
                   font=f_mid if k == 0 else f_sm)
    bbox = canvas.convert("RGB")
    if only:
        return bbox
    return bbox


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "tools/poster/poster_acto1.json")
    ap.add_argument("--out", type=Path, default=ROOT / "walkthroughs/poster-mapa/assets")
    ap.add_argument("--name", default="poster_acto1_v0")
    ap.add_argument("--mobile-width", type=int, default=1200)
    ap.add_argument("--vista", choices=("columnas", "select"), default="columnas")
    ap.add_argument("--solo", default="", help="vista select: stages a dibujar, p. ej. 1 o 1,2 (prueba rapida)")
    ap.add_argument("--bicubic", action="store_true", help="vista select: remuestreo bicubico del suelo")
    ap.add_argument("--movil-lado", type=int, default=1600, help="vista select: lado mayor de la version movil")
    a = ap.parse_args()
    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    kit = Kit()
    if a.vista == "select":
        only = {int(x) for x in a.solo.split(",") if x}
        name = a.name if a.name != "poster_acto1_v0" else "poster_acto1_v1_select"
        img = compose_select(kit, cfg, plan, only or None, Image.BICUBIC if a.bicubic else Image.NEAREST)
        from PIL import ImageChops
        bb = ImageChops.difference(img, Image.new("RGB", img.size, BG)).getbbox()
        if bb:
            img = img.crop((max(0, bb[0] - 40), max(0, bb[1] - 40), min(img.width, bb[2] + 40), min(img.height, bb[3] + 40)))
        a.out.mkdir(parents=True, exist_ok=True)
        img.save(a.out / f"{name}.png")
        k = a.movil_lado / max(img.size)
        img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS).save(a.out / f"{name}_movil.png")
        print("select", img.size, "->", a.out / f"{name}.png")
        return
    entries = {e["stage"]: e for e in cfg["stages"]}
    LAB_W, MARGIN, TITLE_H = 132, 28, 96
    pitch = VIEW_W + LAB_W
    W = MARGIN * 2 + 3 * pitch - 12
    H = TITLE_H + 10 * BLOCK_H + MARGIN
    poster = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(poster)
    f_big, f_mid, f_sm = font(20), font(14), font(11)
    d.text((MARGIN, 16), cfg.get("titulo", "Acto I"), fill=(205, 195, 170), font=f_big)
    d.text((MARGIN, 44), "de abajo (entrada) a arriba (jefe) - 1:1 en pixeles del juego", fill=(120, 115, 105), font=f_sm)
    report = []
    for col in range(3):
        x0 = MARGIN + col * pitch
        d.text((x0, TITLE_H - 22), f"Tramo {col + 1}  (salas {col * 5 + 1}-{col * 5 + 5})", fill=(170, 160, 140), font=f_mid)
        for j in range(5):
            i = col * 5 + j                        # stage 0-based
            e = entries[i + 1]
            enc_block = 3 - 2 * i                  # bloque de la sala (s_first_block = 3)
            if is_boss(i):
                room_pieces, mirror = [], 0
            else:
                mirror = e.get("espejo", 0)
                room_pieces = block_pieces(plan["plantas"][e["planta"]]["pieces"], mirror, enc_block)
            img, placed = render_block(kit, room_pieces, e.get("luz"), e.get("props_extra", []), e.get("props_quitar", []))
            report.append((i + 1, e["planta"], [n for n, pos in placed if pos is None]))
            y_room = TITLE_H + (9 - 2 * j) * BLOCK_H
            poster.paste(Image.fromarray(img), (x0, y_room))
            tier = "jefe" if is_boss(i) else plan["act"]["tiers"][i - (i > 4) - (i > 9)]
            lbl = [f"SALA {i + 1}", "JEFE (arena vacia)" if is_boss(i) else e["planta"] + (" (esp.)" if mirror else ""), "" if is_boss(i) else tier]
            for k, t in enumerate(lbl):
                d.text((x0 + VIEW_W + 8, y_room + 8 + 18 * k), t, fill=(225, 205, 150) if k == 0 else (150, 145, 135),
                       font=f_mid if k == 0 else f_sm)
            pe = e.get("pasillo", {})              # pasillo encima de la sala (bloque impar de la tira)
            cpieces = block_pieces(plan["pasillo"]["pieces"], i & 1, enc_block - 1, skip_relicario=(i == 14))
            cimg, _ = render_block(kit, cpieces, pe.get("luz"), pe.get("props_extra", []), pe.get("props_quitar", []))
            y_cor = y_room - BLOCK_H
            poster.paste(Image.fromarray(cimg), (x0, y_cor))
            d.text((x0 + VIEW_W + 8, y_cor + 8), f"pasillo {i + 1}", fill=(110, 108, 100), font=f_sm)
    a.out.mkdir(parents=True, exist_ok=True)
    full = a.out / f"{a.name}.png"
    poster.save(full)
    mw = a.mobile_width
    mob = poster.resize((mw, round(H * mw / W)), Image.LANCZOS)
    mob.save(a.out / f"{a.name}_movil.png")
    print("poster", poster.size, "->", full)
    print("movil", mob.size)
    for s, pl, dropped in report:
        print(f"  stage {s:2d} {pl:10s}" + (f" descartadas: {dropped}" if dropped else ""))


if __name__ == "__main__":
    main()
