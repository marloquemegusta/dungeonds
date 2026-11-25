#!/usr/bin/env python3
"""Poster del mapa del ARPG (rama proto/arpg): las 16 salas fijas con su escenario real (suelo, muros, huecos laterales,
muro del fondo, altar, cofre y props), colocadas como en el mapa de SELECT del juego (source/arpg_map.c): plano girado
45 grados y aplastado 2:1, sx = (X + Y) * K, sy = (X - Y) * K / 2 con X al este e Y al norte; aqui K = 1.

Uso: python tools/poster/poster_arpg.py [--config tools/poster/poster_arpg.json] [--out DIR] [--name poster_arpg_v0_select]
                                          [--solo 0,4] [--bicubic] [--movil-lado 2000]

Fidelidad: las salas y sus puertas se leen de s_rooms[] de source/encounters_act1.c; la colocacion (map_walk, hueco de 40 px
entre salas, puertas alineadas) copia ese archivo. Planta y espejo de cada bloque salen de la misma semilla que la ROM
(enc_room_seed + pick_hash). Las piezas se estampan como enc_place_piece() (ver poster_acto1.py). Suelo y muros laterales se
transforman al plano; props, altar, cofre y muro del fondo se dibujan erguidos, anclados a su punto de suelo y ordenados por
profundidad. No se dibuja: barreras, rejas, enemigos ni lapidas. Los muros laterales van aplastados sobre el suelo.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import poster_acto1 as p1  # noqa: E402

bk = p1.bk
ROOT = p1.ROOT
BG = (14, 12, 18)
BLOCK_H, VIEW_W = p1.BLOCK_H, p1.VIEW_W
FLOOR_W, FLOOR_X, VIEW_X0 = p1.FLOOR_W, p1.FLOOR_X, p1.VIEW_X0
WALL = FLOOR_X - VIEW_X0           # 24
GAP = 40                           # ENC_MAP_GAP
HOLE_Y, HOLE_H = 96, 256           # ARPG_ROOM_HOLE_Y_PX / H_PX
import poster_arpg_ambiente as amb_mod
M = 32                             # filas de margen arriba del plano de cada sala (el arte del hueco empieza 24 px por encima)
PRESETS = {
    "neutral": {},
    "calido": {"tinte": [255, 232, 200], "vineta": 0.25},
    "frio": {"tinte": [205, 220, 255], "vineta": 0.25},
    "oscuro": {"gradiente": {"abajo": 0.85, "arriba": 0.45}, "vineta": 0.4},
}
SWAP_ROOM_TYPES = ("CRIPTA",)


# ------------------------------------------------------------------ datos del juego (source/encounters_act1.c)
def parse_rooms():
    src = (ROOT / "source/encounters_act1.c").read_text(encoding="utf-8")
    body = src[src.index("s_rooms[ENC_ROOM_COUNT] = {"):]
    body = body[:body.index("\n};")]
    rooms = []
    for ch in body.split("{ .name =")[1:]:
        def num(key, d=0):
            m = re.search(r"\." + key + r" = (\d+)", ch)
            return int(m.group(1)) if m else d
        doors = []
        for side, args in re.findall(r"D([LRU])\(([^)]*)\)", ch):
            a = [int(x) for x in args.split(",")]
            doors.append({"side": side, "screen": a[0] if side != "U" else 0, "dest": a[-1]})
        rooms.append({"name": re.search(r'"([^"]+)"', ch).group(1), "blocks": num("blocks"), "level": num("level"),
                      "type": re.search(r"\.type = RT_(\w+)", ch).group(1), "altar": num("altar"), "chest": num("chest"),
                      "gate": num("chapel_gate"), "nave": num("nave"), "special": num("special_block"), "doors": doors})
    return rooms


def door_cy(d):
    return ((d["screen"] - 1) // 2 + 1) * BLOCK_H - HOLE_Y - HOLE_H // 2


def map_walk(rooms):
    pos, seen = {}, set()

    def walk(r, x, y):
        seen.add(r)
        pos[r] = (x, y)
        for d in rooms[r]["doors"]:
            if d["dest"] in seen:
                continue
            c = rooms[d["dest"]]
            if d["side"] == "U":
                walk(d["dest"], x, y + rooms[r]["blocks"] * BLOCK_H)
                continue
            for cd in c["doors"]:
                if cd["dest"] != r or cd["side"] == "U":
                    continue
                cx = x - (FLOOR_W + GAP) if d["side"] == "L" else x + FLOOR_W + GAP
                walk(d["dest"], cx, y + door_cy(d) - door_cy(cd))
                break
    walk(0, 0, 0)
    return pos


M32 = 0xFFFFFFFF


def hash32(v):
    v &= M32
    v ^= v >> 16
    v = (v * 0x7FEB352D) & M32
    v ^= v >> 15
    v = (v * 0x846CA68B) & M32
    v ^= v >> 16
    return v


def room_seed(room):
    return hash32(0x53414C41 + room * 0x9E3779B9) | 1


def room_plants(room, rd, plan_names):
    """enc_init(): planta y espejo de cada bloque (nunca la misma planta dos veces seguidas)."""
    seed = room_seed(room)

    def ph(slot, salt):
        return hash32(seed ^ ((slot * 0x9E3779B9) & M32) ^ ((salt * 0x85EBCA6B) & M32) ^ 0x454E4331)
    out, prev = [], -1
    for k in range(rd["blocks"]):
        mirror = ph(k, 99) & 1
        boss = rd["type"] == "CRIPTA" and k == 0
        if boss:
            out.append((None, mirror))
            continue
        rng = len(plan_names) - (1 if prev >= 0 else 0)
        p = ph(k, 7) % rng
        if prev >= 0 and p >= prev:
            p += 1
        out.append((plan_names[p], mirror))
        prev = p
    return out


# ------------------------------------------------------------------ arte de muros
def load_quant(kit, path):
    """PNG RGBA -> (rgb555 uint16, alfa bool) cuantizado a la paleta de props como el baker."""
    src = np.asarray(Image.open(path).convert("RGBA"))
    op = src[:, :, 3] >= 128
    rgb = np.where(op[:, :, None], src[:, :, :3], np.array(bk.WALL_BACKDROP_RGB, np.uint8))
    q = bk.quantize_props(Image.fromarray(np.dstack([rgb, np.full(op.shape, 255, np.uint8)])), kit.prop_lab)
    return kit.prop_arr[q], op


def stamp_layout(full, floor, lay, x0, y0):
    """Estampa una pieza suelta (altar, cofre) en el plano de la sala; devuelve el sprite."""
    h, w = lay["op"].shape
    ya, yb, xa, xb = max(0, y0), min(full.shape[0], y0 + h), max(0, x0), min(full.shape[1], x0 + w)
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    dst = (slice(ya, yb), slice(xa, xb))
    shaded = ((full[dst] & 0x7BDE) >> 1) | 0x8000
    full[dst] = np.where(lay["op"][sl], lay["pix"][sl], np.where(lay["sh"][sl], shaded, full[dst]))
    fs = ((floor[dst] & 0x7BDE) >> 1) | 0x8000
    floor[dst] = np.where(lay["sh"][sl], fs, floor[dst])
    return {"x0": x0, "y0": y0, "op": lay["op"], "ax": x0 + w / 2.0, "ay": y0 + lay["anchor"]}


def build_room(kit, plan, room, rd, cfg, hole, ends, gcfg=None, enemies=()):
    """gcfg = config global; con gcfg y cfg['ambiente'] dibuja el ambiente v2 (composicion + luz); si no, la ROM tal cual (v1)."""
    amb = cfg.get("ambiente") if gcfg else None
    rep = {"movidas": 0, "quitadas": 0}
    nb = rd["blocks"]
    Ht = nb * BLOCK_H + M
    full = np.zeros((Ht, VIEW_W), np.uint16)
    floor = np.zeros_like(full)
    alpha = np.zeros((Ht, VIEW_W), bool)
    alpha[M:] = True
    sprites, info = [], []
    names = list(plan["plantas"].keys())
    plants = room_plants(room, rd, names)
    quitar = cfg.get("props_quitar", [])
    for k in range(nb):
        row0 = M + (nb - 1 - k) * BLOCK_H
        canvas = kit.floor_block.copy()
        w = kit.wall != 0
        canvas[w] = kit.wall[w]
        fl = canvas.copy()
        pname, mirror = plants[k]
        if cfg.get("planta") and k == 0:
            pname = cfg["planta"]
        if cfg.get("espejo") is not None:
            mirror = cfg["espejo"]
        pieces = []
        if amb:
            pieces = amb_mod.pieces_for_block(kit, amb, k, rd, nb, enemies, rep)
        elif pname and not rd["gate"]:
            pieces = p1.block_pieces(plan["plantas"][pname]["pieces"], mirror, 3 - k)
        pieces = [p for p in pieces if not any(p["piece"].startswith(q) for q in quitar)]
        if not amb:
            pieces += [{"piece": e["piece"], "lx": e["x"], "ly": e["y"], "mirror": e.get("mirror", 0)}
                       for e in cfg.get("props_extra", [])]
        sp = []
        p1.place(kit, canvas, pieces, floor555=fl, sprites=sp)
        full[row0:row0 + BLOCK_H] = canvas
        floor[row0:row0 + BLOCK_H] = fl
        for s in sp:
            s["y0"] += row0
            s["ay"] += row0
            sprites.append(s)
        info.append(("ambiente", 0) if amb else (pname, mirror) if pname and not rd["gate"] else ("-", mirror))
    if rd["altar"]:
        lay = kit.layout("altar")
        row0 = M + (nb - 1) * BLOCK_H
        sprites.append({**stamp_layout(full, floor, lay, FLOOR_X + 48 - VIEW_X0 - lay["w"] // 2, row0 + 316 - lay["anchor"]), "piece": "altar"})
    if rd["chest"]:
        lay = kit.layout("cofre_cerrado")
        sprites.append(stamp_layout(full, floor, lay, FLOOR_X + FLOOR_W // 2 - VIEW_X0 - lay["w"] // 2, M + 90 - lay["anchor"]))
    # huecos laterales (apply_room_openings): arte de 24x264 desde 24 px por encima del bloque de la puerta; el vacio es transparente
    for d in rd["doors"]:
        if d["side"] == "U":
            continue
        kb = (d["screen"] - 1) // 2
        r0 = M + (nb - 1 - kb) * BLOCK_H - 24
        pix, op = hole
        if d["side"] == "R":
            pix, op, c0 = pix[:, ::-1], op[:, ::-1], VIEW_W - WALL
        else:
            c0 = 0
        sl = (slice(r0, r0 + pix.shape[0]), slice(c0, c0 + WALL))
        full[sl] = np.where(op, pix, 0)
        floor[sl] = np.where(op, pix, 0)
        alpha[sl] = op
    luz = cfg.get("luz") or {}
    luz = {**PRESETS.get(luz.get("preset", "neutral"), {}), **{k: v for k, v in luz.items() if k != "preset"}}
    mult = None
    if amb:
        mult, add = amb_mod.light_maps(amb, gcfg, rd, nb, Ht, sprites, M)
        rgb_f = amb_mod.apply(p1.to_rgb(floor), mult, add)
        rgb_u = amb_mod.apply(p1.to_rgb(full), mult, add)
    else:
        rgb_f = p1.apply_light(p1.to_rgb(floor), luz)
        rgb_u = p1.apply_light(p1.to_rgb(full), luz)
    plane = np.dstack([rgb_f, np.where(alpha, 255, 0).astype(np.uint8)])
    # muro del fondo (variante pasante si hay puerta arriba)
    has_up = any(d["side"] == "U" for d in rd["doors"])
    pix, op = ends[1 if has_up else 0]
    if amb:
        ph = pix.shape[0]
        mrow = mult[M:M + 1]                                  # fila del fondo de la sala: la luz mas baja
        brgb = np.clip(p1.to_rgb(pix).astype(np.float64) * mrow, 0, 255).astype(np.uint8)
    else:
        brgb = p1.apply_light(p1.to_rgb(pix), luz)
    back = np.dstack([brgb, np.where(op, 255, 0).astype(np.uint8)])
    return {"plane": plane, "rgb": rgb_u, "sprites": sprites, "back": back, "Ht": Ht, "info": info, "luz": luz, "mult": mult, "rep": rep}


# ------------------------------------------------------------------ proyeccion de SELECT
def sxy(X, Y):
    return X + Y, (X - Y) / 2.0


def plane_box(BX, Y0, W, Ht):
    bx = BX + Y0
    by = int(np.floor((BX - (Y0 + Ht)) / 2.0)) - 1
    return bx, by, W + Ht + 2, (W + Ht) // 2 + 3


def paste_plane(canvas, rgba, BX, Y0, ox, oy, resample):
    Ht, W = rgba.shape[:2]
    bx, by, w, h = plane_box(BX, Y0, W, Ht)
    coefs = (0.5, 1.0, (bx + 2 * by) / 2.0 - BX, -0.5, 1.0, Ht + Y0 - (bx - 2 * by) / 2.0)
    out = Image.fromarray(rgba).transform((w, h), Image.AFFINE, coefs, resample=resample)
    canvas.paste(out, (bx + ox, by + oy), out)


def paste_upright(canvas, rgba, cx, ay, X, Y, ox, oy):
    """Cada columna cuelga de su punto de suelo (cizalla vertical dx/2 sobre el plano de SELECT)."""
    h, w = rgba.shape[:2]
    out = np.zeros((h + w // 2 + 2, w, 4), np.uint8)
    for c in range(w):
        s = int(round((c - cx) / 2.0 + w / 4.0))
        out[s:s + h, c] = rgba[:, c]
    sx, sy = sxy(X, Y)
    img = Image.fromarray(out)
    canvas.paste(img, (int(round(sx - cx)) + ox, int(round(sy - ay - w / 4.0)) + oy), img)


def cut_sprite(rgb, s):
    h, w = s["op"].shape
    x0, y0 = s["x0"], s["y0"]
    out = np.zeros((h, w, 4), np.uint8)
    ya, yb, xa, xb = max(0, y0), min(rgb.shape[0], y0 + h), max(0, x0), min(rgb.shape[1], x0 + w)
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    out[sub[0], sub[1], :3] = rgb[ya:yb, xa:xb]
    out[sub[0], sub[1], 3] = np.where(s["op"][sub], 255, 0)
    return out


def font(size):
    return p1.font(size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=HERE / "poster_arpg.json")
    ap.add_argument("--out", type=Path, default=ROOT / "walkthroughs/poster-mapa/assets")
    ap.add_argument("--vista", choices=("juego", "select"), default="juego", help="juego = camara del juego (v1); select = vista del mapa de SELECT")
    ap.add_argument("--ambientes", action="store_true", help="v2: composicion y luz por sala (bloque `ambiente` del JSON)")
    ap.add_argument("--v3", action="store_true", help="v3: seis ambientes de luz y sombra con el pipeline del campamento")
    ap.add_argument("--noche", action="store_true", help="con --v3: claustros de noche")
    ap.add_argument("--name", default="")
    ap.add_argument("--solo", default="", help="ids de sala a dibujar, p. ej. 0 o 0,4 (prueba rapida)")
    ap.add_argument("--sala", type=int, default=None, help="una sala sola (rapido): escribe la imagen limpia de esa sala x3 en --out-sala/limpia")
    ap.add_argument("--revision", action="store_true", help="con --sala: ademas la vista de revision de encuentros (avisos, deambular, ocultos, rutas)")
    ap.add_argument("--out-sala", type=Path, default=ROOT / "walkthroughs/arpg-encuentros/assets", help="raiz de limpia/ y revision/")
    ap.add_argument("--bicubic", action="store_true")
    ap.add_argument("--movil-ancho", type=int, default=1400)
    ap.add_argument("--movil-lado", type=int, default=2000)
    a = ap.parse_args()
    a.name = a.name or ("poster_arpg_v3" if a.v3 else "poster_arpg_v2" if a.ambientes else "poster_arpg_v1" if a.vista == "juego" else "poster_arpg_v0_select")
    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    cfgs = {e["id"]: e for e in cfg["salas"]}
    plan = json.loads(p1.PLAN.read_text(encoding="utf-8"))
    kit = p1.Kit()
    rooms = parse_rooms()
    pos = map_walk(rooms)
    only = {int(x) for x in a.solo.split(",") if x} or set(range(len(rooms)))
    if a.sala is not None:
        only = {a.sala}
        a.v3 = True
    if a.vista == "juego":
        import poster_arpg_juego
        return poster_arpg_juego.run(a, cfg, cfgs, plan, kit, rooms, pos, only)
    hole = load_quant(kit, bk.HOLE_PNG)
    ends = [load_quant(kit, pth) for pth in bk.END_PNGS]
    resample = Image.BICUBIC if a.bicubic else Image.NEAREST

    built = {}
    for r in sorted(only):
        built[r] = build_room(kit, plan, r, rooms[r], cfgs.get(r, {}), hole, ends)
        px, py = pos[r]
        print(f"sala {r:2d} {rooms[r]['name']:26s} x={px:5d} y={py:5d} bloques={rooms[r]['blocks']} plantas={[i[0] for i in built[r]['info']]}")
    # choques de suelo entre salas (informativo)
    for i in sorted(only):
        for j in sorted(only):
            if j <= i:
                continue
            (xi, yi), (xj, yj) = pos[i], pos[j]
            if xi < xj + FLOOR_W and xj < xi + FLOOR_W and yi < yj + rooms[j]["blocks"] * BLOCK_H and yj < yi + rooms[i]["blocks"] * BLOCK_H:
                print(f"AVISO: las salas {i} y {j} se solapan en el plano")

    # pasos entre salas: suelo entre los suelos de las dos salas a la altura del hueco
    passages = []
    for r in sorted(only):
        for d in rooms[r]["doors"]:
            if d["side"] == "R" and d["dest"] in only:
                x, y = pos[r]
                cx_, _ = pos[d["dest"]]
                passages.append((x + FLOOR_W, y + door_cy(d) - HOLE_H // 2, cx_ - (x + FLOOR_W)))

    # extension del lienzo
    boxes = []
    for r, b in built.items():
        px, py = pos[r]
        bx, by, w, h = plane_box(px - WALL, py, VIEW_W, b["Ht"])
        boxes.append((bx, by, bx + w, by + h))
        T = py + rooms[r]["blocks"] * BLOCK_H
        sx, sy = sxy(px - WALL, T)
        boxes.append((sx - 4, sy - 160, sx + VIEW_W + 8, sy + VIEW_W / 2 + 40))
    for X, Y0, wid in passages:
        bx, by, w, h = plane_box(X, Y0, wid, HOLE_H)
        boxes.append((bx, by, bx + w, by + h))
    minx = min(b[0] for b in boxes) - 80
    miny = min(b[1] for b in boxes) - 220
    maxx = max(b[2] for b in boxes) + 80
    maxy = max(b[3] for b in boxes) + 80
    ox, oy = -int(minx), -int(miny)
    canvas = Image.new("RGBA", (int(maxx - minx), int(maxy - miny)), BG + (255,))
    print("lienzo", canvas.size)

    for X, Y0, wid in passages:
        rows = np.arange(HOLE_Y, HOLE_Y + HOLE_H)
        img = kit.floor_block[rows][:, 60:60 + wid]
        img = np.dstack([p1.to_rgb(img), np.full(img.shape, 255, np.uint8)])
        paste_plane(canvas, img, X, Y0, ox, oy, resample)
    for r, b in built.items():
        px, py = pos[r]
        paste_plane(canvas, b["plane"], px - WALL, py, ox, oy, resample)

    items = []                                  # (sy de suelo, rgba, cx, ay, X, Y)
    for r, b in built.items():
        px, py = pos[r]
        BX = px - WALL
        Ht = b["Ht"]
        for s in b["sprites"]:
            rgba = cut_sprite(b["rgb"], s)
            X, Y = BX + s["ax"], py + Ht - s["ay"]
            items.append((sxy(X, Y)[1], rgba, rgba.shape[1] / 2.0, s["ay"] - s["y0"], X, Y))
        T = py + rooms[r]["blocks"] * BLOCK_H
        back = b["back"]
        for c0 in range(0, VIEW_W, 8):
            sl = np.ascontiguousarray(back[:, c0:c0 + 8])
            X = BX + c0 + 4
            items.append((sxy(X, T)[1], sl, 4.0, sl.shape[0], X, T))
    items.sort(key=lambda t: t[0])
    for _, rgba, cx, ay, X, Y in items:
        paste_upright(canvas, rgba, cx, ay, X, Y, ox, oy)

    d = ImageDraw.Draw(canvas)
    d.text((60, 40), cfg.get("titulo", "DungeonDS ARPG") + "  -  mapa (vista SELECT)", fill=(205, 195, 170), font=font(52))
    f1, f2 = font(34), font(24)
    for r in built:
        px, py = pos[r]
        rd = rooms[r]
        mid = py + (rd["blocks"] * BLOCK_H) / 2.0
        sx, sy = sxy(px + FLOOR_W / 2.0, mid)
        pl = ", ".join(sorted({i[0] for i in built[r]["info"] if i[0] != "-"})) or "sin props"
        lines = [(f"{r}  {rd['name']}", f1, (235, 215, 150)), (f"nivel {rd['level']}  -  {pl}", f2, (190, 185, 170))]
        wmax = max(d.textlength(t, font=f) for t, f, _ in lines)
        y = sy + oy - 30
        d.rectangle((sx + ox - wmax / 2 - 10, y - 6, sx + ox + wmax / 2 + 10, y + 80), fill=(10, 8, 12))
        for t, f, col in lines:
            d.text((sx + ox - d.textlength(t, font=f) / 2, y), t, fill=col, font=f)
            y += 40
    img = canvas.convert("RGB")
    a.out.mkdir(parents=True, exist_ok=True)
    img.save(a.out / f"{a.name}.png")
    k = a.movil_lado / max(img.size)
    mob = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    mob.save(a.out / f"{a.name}_movil.png")
    print("select", img.size, "->", a.out / f"{a.name}.png", "| movil", mob.size)


if __name__ == "__main__":
    main()
