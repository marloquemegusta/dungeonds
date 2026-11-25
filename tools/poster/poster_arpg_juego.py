"""Poster del ARPG con la CAMARA DEL JUEGO (v1): las 16 salas en su posicion real del plano, proyeccion plana (x = X,
y = -Y), sprites tal cual salen de la ROM (sin cizalla ni giro), muros laterales de pie. Se invoca desde poster_arpg.py.

Poblacion: portada de encounters_act1.c (grupos por bloque con hash(seed de sala), cuadricula 4x3, jefe de la Cripta).
Las posiciones son deterministas (no hay azar que fijar). No se portan: lapidas (dependen de candidatos del strip)
ni el empujon alrededor de props de position_is_free.

COLOCACION A MANO (DESIGN-ARPG.md §12). Si salas/sala_NN.py define GRUPOS, la sala se pinta con esos grupos y no con la
rejilla 4x3 de la ROM; los props no se apartan de nadie (solo se avisa por consola si un enemigo pisa un prop o columna):
    GRUPOS = [{"nombre": "Rebano", "formacion": "enjambre", "k": 0,
               "miembros": [("bebe", x, y, "gatea"), ("monja", x, y, "reza"), ...],
               "ruta": None}]          # "ruta": lista de (x, y) solo si hay miembros en "patrulla"
  x, y = pies del enemigo, mismo sistema que ADD (x de suelo 0..207; y local del bloque k, 0 = norte del bloque; k=0 es el tramo de entrada).
  tipo: bebe, monaguillo, monja, ojo, cireneo, parroco, smonja, abanderado.
  reposo: gatea, vaiven, reza, barre, pasea, quieto, escondido, patrulla.
  formacion: enjambre, muralla, puesto, embestida, cruzado, emboscada, patrulla (texto libre; solo se rotula).
Vista de revision: ver run() (poster_arpg.py --v3 --sala N --revision)."""
import json, os, re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import poster_arpg as P
import poster_acto1 as p1
import romsprites as R

ROOT = P.ROOT
M32 = 0xFFFFFFFF
LEVEL_LIFT = 160          # px extra por salto "arriba": el muro del fondo (152) no pisa la sala de encima
BG = (14, 12, 18)

# ENC_E_* -> CHAR_* (enemy_type_of + enemy_type_char_id); la Monja de cera reza (pose en pie / de rodillas)
CHAR = {"EXVOTO": 3, "CIRENEO": 1, "OJO": 2, "ABANDERADO": 7, "MONAGUILLO": 8, "BEBE": 10, "PARROCO": 12, "MONJA": 13}
PRAY_STAND, PRAY_KNEEL = 4, 5
NAMES = {1: "Cireneo", 2: "Ojo del Tribunal", 3: "Exvoto", 4: "Monja de cera (reza)", 5: "Monja de cera (reza)",
         7: "Abanderado", 8: "Monaguillo", 10: "Bebe", 12: "Parroco", 13: "Super Monja"}
LEG_CHAR = {5: 4}         # miniatura de la leyenda


def read_tables():
    src = (ROOT / "source/encounters_act1.c").read_text(encoding="utf-8")
    kinds_enum = re.search(r"enum \{ (RK_BEBE = 0.*?) \};", src, re.S).group(1)
    rk = re.findall(r"RK_(\w+)", kinds_enum)
    kinds = {}
    for name, enc, guard in re.findall(r"\[RK_(\w+)\]\s*=\s*\{ ENC_E_(\w+), (\d) \}", src):
        kinds[name] = (enc, int(guard))
    groups = []
    for name, nave, parts in re.findall(r'\[G_(\w+)\]\s*=\s*\{ "[^"]*",\s*(\d+),\s*\d+,\s*\{(.*)\} \},?', src):
        groups.append({"id": name, "nave": int(nave),
                       "parts": [(k, int(c)) for k, c in re.findall(r"\{ RK_(\w+), (\d+) \}", parts)]})
    tabs = (ROOT / "source/encounters_act1_tables.h").read_text(encoding="utf-8")
    body = tabs[tabs.index("s_boss_enemies[]"):]
    body = body[:body.index("};")]
    boss = [(e, int(x), int(y)) for e, x, y in re.findall(r"\{ ENC_E_(\w+), \w+, (\d+), (\d+) \}", body)]
    # el regex anterior captura (tipo, x, y)
    return rk, kinds, groups, boss


def group_of_block(rd, room, k, groups):
    t = rd["type"]
    names = [g["id"] for g in groups]
    if t == "CRIPTA":
        return None
    if t == "MISA":
        return "MISA" if k == rd["special"] else None
    if t == "MONJARANA":
        return "MONJARANA" if k == rd["special"] else None
    if t == "PARROQUIA":
        return "PARROQUIA"
    seed = P.room_seed(room)
    normal = [g for g in groups if g["id"] not in ("PARROQUIA", "MISA", "MONJARANA")]
    prev = None
    for b in range(k + 1):
        cand = [g["id"] for g in normal if g["nave"] == rd["nave"] and g["id"] != prev]
        prev = cand[P.hash32(seed ^ ((b * 0x45D9F3B) & M32) ^ 0x47525031) % len(cand)]
    return prev


def group_kinds(g):
    spread = (1, 6, 8)
    kinds = [None] * 12
    total = 0
    for kind, cnt in g["parts"]:
        if kind != "OJO":
            continue
        for c in range(cnt):
            if total >= 12:
                break
            slot = spread[c % 3]
            while kinds[slot] is not None:
                slot = (slot + 1) % 12
            kinds[slot] = "OJO"
            total += 1
    for kind, cnt in g["parts"]:
        if kind == "OJO":
            continue
        for c in range(cnt):
            if total >= 12:
                break
            slot = 0
            while kinds[slot] is not None:
                slot += 1
            kinds[slot] = kind
            total += 1
    return kinds


def group_slot(seed, k, i):
    col, row = i & 3, i >> 2
    h = P.hash32(seed ^ ((k * 0x9E3779B9) & M32) ^ ((i * 0x119DE1F3) & M32) ^ 0x534C4F54)
    x = 28 + col * 48 + (h % 9) - 4
    y = 84 + row * 66 + ((h >> 8) % 9) - 4
    return min(max(x, 12 - 0), P.FLOOR_W - 12), y


TIPO_CHAR = {"bebe": 10, "monaguillo": 8, "monja": PRAY_STAND, "ojo": 2, "cireneo": 1, "parroco": 12, "smonja": 13,
             "abanderado": 7}
ESTATICOS = ("quieto", "reza", "escondido")


_GCACHE = {}


def load_groups(room):
    if room not in _GCACHE:
        _GCACHE[room] = _load_groups(room)
    return _GCACHE[room]


def _load_groups(room):
    """GRUPOS de salas/sala_NN.py o None (entonces vale la poblacion de la ROM)."""
    import importlib.util
    f = Path(__file__).with_name("salas") / f"sala_{room:02d}.py"
    if not f.exists():
        return None
    sp = importlib.util.spec_from_file_location(f"grupos_{room:02d}", f)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return getattr(m, "GRUPOS", None)


def hand_members(room):
    """[(grupo, tipo, x, y, reposo, k, char_id)] de los GRUPOS a mano, o None."""
    gr = load_groups(room)
    if gr is None:
        return None
    out = []
    for g in gr:
        for tipo, x, y, rep in g["miembros"]:
            cid = TIPO_CHAR[tipo]
            if tipo == "monja" and rep == "reza":
                cid = PRAY_KNEEL
            out.append((g, tipo, x, y, rep, g["k"], cid))
    return out


def room_enemies(room, rd, tabs):
    """Lista de (char_id, x_local_suelo, y_local_bloque, bloque k, ordinal) de la sala."""
    rk, kinds, groups, boss = tabs
    out = []
    hm = hand_members(room)
    if hm is not None:
        return [(cid, x, y, k, i) for i, (g, t, x, y, rep, k, cid) in enumerate(hm)]
    if rd["type"] == "CRIPTA":
        for enc, x, y in boss:
            out.append((CHAR[enc], x, y, rd["special"], 0))
        return out
    seed = P.room_seed(room)
    for k in range(rd["blocks"]):
        gid = group_of_block(rd, room, k, groups)
        if gid is None:
            continue
        g = next(g for g in groups if g["id"] == gid)
        for i, kind in enumerate(group_kinds(g)):
            if kind is None:
                continue
            enc, guard = kinds[kind]
            x, y = group_slot(seed, k, i)
            cid = CHAR[enc]
            if guard == 2:
                cid = PRAY_KNEEL if (i & 1) else PRAY_STAND
            out.append((cid, x, y, k, i))
    return out


FOOT = (-13, -10, 13, 6)     # huella de un enemigo respecto a sus pies (la misma que usa pieces_for_block)


def avisos_solape(r, rd, b, ens):
    """Avisa por consola si un enemigo colocado a mano pisa la huella de un prop o columna (no se mueve nada)."""
    nb, BH = rd["blocks"], P.BLOCK_H
    for cid, lx, ly, k, i in ens:
        fx, fy = P.WALL + lx, P.M + (nb - 1 - k) * BH + ly
        er = (fx + FOOT[0], fy + FOOT[1], fx + FOOT[2], fy + FOOT[3])
        for s in b["sprites"]:
            ys, xs = np.nonzero(s["op"])
            if not len(xs):
                continue
            pr = (s["x0"] + int(xs.min()), s["ay"] - 10, s["x0"] + int(xs.max()) + 1, s["ay"])
            if er[0] < pr[2] and pr[0] < er[2] and er[1] < pr[3] and pr[1] < er[3]:
                print(f"AVISO solape sala {r}: {NAMES.get(cid, cid)} k={k} en ({lx},{ly}) pisa {s.get('piece', '?').partition('@')[0]}")
    if os.environ.get("POSTER_DEBUG"):
        for s in b["sprites"]:
            kk = nb - 1 - (int(s["ay"]) - P.M) // BH
            ys, xs = np.nonzero(s["op"])
            ry = P.M + (nb - 1 - kk) * BH
            print(f"  prop {s.get('piece', '?').partition('@')[0]:18s} k={kk} visible x={s['x0'] + int(xs.min()) - P.WALL}..{s['x0'] + int(xs.max()) - P.WALL} y={s['y0'] + int(ys.min()) - ry}..{s['y0'] + int(ys.max()) - ry}")
            continue
            print(f"  prop {s.get('piece', '?').partition('@')[0]:18s} k={kk} pies x={int(s['ax']) - P.WALL} y={(int(s['ay']) - P.M) % BH}")


GRUPO_COL = [(190, 120, 100), (110, 160, 190), (150, 190, 110), (190, 170, 100), (170, 120, 190)]


def _ell(d, cx, cy, rx, ry, col, dash=False, w=1):
    if not dash:
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=col, width=w)
        return
    n = 48
    for j in range(0, n, 2):
        a0, a1 = 2 * np.pi * j / n, 2 * np.pi * (j + 1) / n
        d.line((cx + rx * np.cos(a0), cy + ry * np.sin(a0), cx + rx * np.cos(a1), cy + ry * np.sin(a1)), fill=col, width=w)


def dibuja_revision(d, r, rd, bx, by):
    """Capa de revision bajo los sprites (para que las piezas altas sigan tapando): aviso 96 px, deambular 40 px, revelado 48 px, rutas."""
    nb, BH = rd["blocks"], P.BLOCK_H
    def foot(k, x, y):
        return bx + P.WALL + x, by + P.M + (nb - 1 - k) * BH + y
    gs = []
    for g, t, x, y, rep, k, cid in (hand_members(r) or []):
        if g not in gs:
            gs.append(g)
    for gi, g in enumerate(gs):
        col = GRUPO_COL[gi % len(GRUPO_COL)]
        ms = [m for m in (hand_members(r) or []) if m[0] is g]
        cx = sum(m[2] for m in ms) // len(ms)
        cy = sum(m[3] for m in ms) // len(ms)
        fx, fy = foot(g["k"], cx, cy)
        _ell(d, fx, fy, 96, 48, col + (200,), dash=True)
        for _, t, x, y, rep, k, cid in ms:
            mx, my = foot(k, x, y)
            if rep not in ESTATICOS:
                _ell(d, mx, my, 40, 20, col + (150,))
            if rep == "escondido":
                _ell(d, mx, my, 48, 24, (220, 90, 90, 220))
                d.rectangle((mx - 12, my - 36, mx + 12, my + 2), outline=(240, 240, 240, 255))
        if g.get("ruta"):
            pts = [foot(g["k"], x, y) for x, y in g["ruta"]]
            d.line(pts + [pts[0]], fill=(240, 220, 120, 230), width=1)
            for q in pts:
                d.ellipse((q[0] - 2, q[1] - 2, q[0] + 2, q[1] + 2), fill=(240, 220, 120, 255))


def salida_sala(a, canvas, ov, rects, ox, oy, only, rooms, geo):
    """Recorta la unica sala dibujada, la amplia x3 NEAREST y la guarda (limpia y, con --revision, con rotulos)."""
    import unicodedata
    r = next(iter(only))
    x0, y0, x1, y1 = rects[r]
    box = (x0 + ox, y0 + oy - 100, x1 + ox, y1 + oy)
    nm = unicodedata.normalize("NFKD", rooms[r]["name"]).encode("ascii", "ignore").decode().lower().replace(" ", "_")
    fn = f"{r:02d}_{nm}.png"
    S = 3
    base = a.out_sala
    for sub in ("limpia", "revision"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    canvas.crop(box).resize(((box[2] - box[0]) * S, (box[3] - box[1]) * S), Image.NEAREST).convert("RGB").save(base / "limpia" / fn)
    print("limpia   ->", base / "limpia" / fn)
    if ov is not None:
        im = ov.crop(box).resize(((box[2] - box[0]) * S, (box[3] - box[1]) * S), Image.NEAREST).convert("RGB")
        d = ImageDraw.Draw(im)
        f = P.font(16)
        rd = rooms[r]
        nb, BH = rd["blocks"], P.BLOCK_H
        bx, by = geo[r][0] + ox - box[0], geo[r][1] + oy - box[1]
        gs = []
        for g, t, x, y, rep, k, cid in (hand_members(r) or []):
            if g not in gs:
                gs.append(g)
        for gi, g in enumerate(gs):
            ms = [m for m in (hand_members(r) or []) if m[0] is g]
            cx = sum(m[2] for m in ms) // len(ms)
            ty = min(m[3] for m in ms)
            tx_, ty_ = (bx + P.WALL + cx) * S, (by + P.M + (nb - 1 - g["k"]) * BH + ty - 52) * S
            d.text((tx_, ty_), f"{g['nombre']} - {g['formacion']}", fill=GRUPO_COL[gi % len(GRUPO_COL)], font=f, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        im.save(base / "revision" / fn)
        print("revision ->", base / "revision" / fn)


def verja_art():
    t = (ROOT / "source/verja_gfx.c").read_text(encoding="utf-8")
    pal = [int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{4})", t[t.index("g_verja_palette"):t.index("g_verja_pixels")])]
    body = t[t.index("g_verja_pixels"):]
    rows = [[int(v) for v in re.findall(r"\d+", r)] for r in re.findall(r"\{([^{}]*)\}", body[body.index("= {") + 3:])]
    idx = np.array(rows, np.uint8)
    rgb = R.bgr555_rgb(np.array(pal, np.uint16))
    out = np.zeros(idx.shape + (4,), np.uint8)
    out[..., :3] = rgb[idx]
    out[..., 3] = np.where(idx > 0, 255, 0)
    return out


def levels(rooms):
    lv = {0: 0}
    todo = [0]
    while todo:
        r = todo.pop()
        for d in rooms[r]["doors"]:
            if d["dest"] in lv:
                continue
            lv[d["dest"]] = lv[r] + (1 if d["side"] == "U" else 0)
            todo.append(d["dest"])
    return lv


def shade(canvas, mask, fx, fy):
    """Oscurece al 50 % (draw_shadow_mask: (px & 0x7BDE) >> 1) la huella de la sombra centrada en el pie."""
    sh, sw = mask.shape
    x0, y0 = fx - sw // 2, fy - sh // 2
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        X, Y = x0 + x, y0 + y
        if 0 <= X < canvas.width and 0 <= Y < canvas.height:
            r, g, b = canvas.getpixel((X, Y))[:3]
            canvas.putpixel((X, Y), (r // 2, g // 2, b // 2, 255))


def paste_char(canvas, cid, d, f, fx, fy):
    spr, anc = R.sprite(cid, d, f)
    img = Image.fromarray(spr)
    canvas.paste(img, (fx - spr.shape[1] // 2, fy - anc), img)


def run(a, cfg, cfgs, plan, kit, rooms, pos, only):
    tabs = read_tables()
    lvl = levels(rooms)
    hole = P.load_quant(kit, P.bk.HOLE_PNG)
    ends = [P.load_quant(kit, pth) for pth in P.bk.END_PNGS]
    amb = getattr(a, "ambientes", False)
    v3 = getattr(a, "v3", False)
    if v3:
        import poster_arpg_v3 as V3
        amb = True
    def en_list(r):
        if hand_members(r) is not None:                  # colocacion a mano: los props no se apartan de nadie
            return []
        e = [(WALLX + lx, ly, k) for _, lx, ly, k, _ in room_enemies(r, rooms[r], tabs)]
        return e + ([(P.FLOOR_W // 2, P.BLOCK_H - 40, 0)] if r == 0 else [])
    WALLX = 0
    built = {r: V3.build(kit, plan, r, rooms[r], cfgs.get(r, {}), hole, ends, cfg, en_list(r), "noche" if a.noche else "dia") for r in sorted(only)} if v3 else {r: P.build_room(kit, plan, r, rooms[r], cfgs.get(r, {}), hole, ends, cfg if amb else None, en_list(r) if amb else ()) for r in sorted(only)}
    if amb:
        for r, b in built.items():
            print(f"  ambiente sala {r:2d}: props movidos {b['rep']['movidas']}, quitados {b['rep']['quitadas']}")
    BH = P.BLOCK_H
    # geometria en pantalla (antes de desplazar al lienzo): x = X - WALL, y = -Y - lift
    geo = {}
    for r, b in built.items():
        px, py = pos[r]
        nb = rooms[r]["blocks"]
        sx = px - P.WALL
        sy0 = -(py + nb * BH) - P.M - LEVEL_LIFT * lvl[r]
        geo[r] = (sx, sy0)
        print(f"sala {r:2d} {rooms[r]['name']:26s} nivel {lvl[r]} x={px:5d} y={py:5d} bloques={nb}")
    def mkrects():
        return {r: (geo[r][0], geo[r][1] + P.M - 152, geo[r][0] + P.VIEW_W, geo[r][1] + built[r]["Ht"]) for r in built}
    moved = {}
    for _ in range(8):
        rects = mkrects()
        hit = [(i, j) for i in rects for j in rects if j > i and rects[i][0] + 12 < rects[j][2] and rects[j][0] + 12 < rects[i][2]
               and rects[i][1] < rects[j][3] and rects[j][1] < rects[i][3]]
        if not hit:
            break
        for i, j in hit:
            n = j if pos[j][1] > pos[i][1] else i             # la mas al norte sube LEVEL_LIFT mas
            geo[n] = (geo[n][0], geo[n][1] - LEVEL_LIFT)
            moved[n] = moved.get(n, 0) + LEVEL_LIFT
            print(f"SEPARADA: sala {n} sube {LEVEL_LIFT} px para no pisar a la {i if n == j else j} (su hueco al paso queda desalineado)")
            break
    rects = mkrects()

    mx0 = min(v[0] for v in rects.values())
    mx1 = max(v[2] for v in rects.values())
    my0 = min(v[1] for v in rects.values())
    my1 = max(v[3] for v in rects.values())
    MARG_L, MARG_R, TOP, BOT = 700, 700, 560, 60
    ox, oy = MARG_L - mx0, TOP - my0
    W, H = mx1 - mx0 + MARG_L + MARG_R, my1 - my0 + TOP + BOT
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    print("lienzo", canvas.size)
    if os.environ.get("POSTER_RECTS"):                              # cajas de cada sala en el PNG (para revisarlas)
        json.dump({str(k): [v[0] + ox, v[1] + oy, v[2] + ox, v[3] + oy] for k, v in rects.items()},
                  open(os.environ["POSTER_RECTS"], "w"))

    # pasos entre salas (suelo en el hueco lateral)
    for r in built:
        for d in rooms[r]["doors"]:
            if d["side"] == "R" and d["dest"] in built:
                px, py = pos[r]
                cx_, _ = pos[d["dest"]]
                wid = cx_ - (px + P.FLOOR_W)
                Y0 = py + P.door_cy(d) - P.HOLE_H // 2
                rows = np.arange(P.HOLE_Y, P.HOLE_Y + P.HOLE_H)
                img = kit.floor_block[rows][:, 60:60 + wid]
                img = np.dstack([p1.to_rgb(img), np.full(img.shape, 255, np.uint8)])
                canvas.paste(Image.fromarray(img), (px + P.FLOOR_W + ox, -(Y0 + P.HOLE_H) - LEVEL_LIFT * lvl[r] + oy))
    # salas: muro del fondo y plano con props (la camara del juego: se pegan tal cual)
    for r, b in built.items():
        sx, sy0 = geo[r]
        alpha = b["plane"][:, :, 3]
        room_img = Image.fromarray(np.dstack([b["rgb"], alpha]))
        canvas.paste(room_img, (sx + ox, sy0 + oy), room_img)
        back = Image.fromarray(b["back"])
        canvas.paste(back, (sx + ox, sy0 + P.M - back.height + oy), back)
        if b.get("sky") is not None:
            sk = Image.fromarray(b["sky"])
            canvas.paste(sk, (sx + ox, sy0 + P.M - back.height - sk.height + oy), sk)

    # sombras primero (el suelo), luego props y personajes por profundidad
    items = []                          # (clave y de pantalla del pie, rgba, x izq, y sup)
    legend = {}
    stats = {}
    for r, b in built.items():
        sx, sy0 = geo[r]
        rd = rooms[r]
        nb = rd["blocks"]
        base_x, base_y = sx + ox, sy0 + oy
        for s in b["sprites"]:
            rgba = P.cut_sprite(b["rgb"], s)
            items.append((base_y + s["ay"], Image.fromarray(rgba), base_x + s["x0"], base_y + s["y0"]))
        ens = room_enemies(r, rd, tabs)
        cnt = {}
        feet = []
        for cid, lx, ly, k, i in ens:
            fx = base_x + P.WALL + lx
            fy = base_y + P.M + (nb - 1 - k) * BH + ly
            feet.append((cid, fx, fy))
            cnt[cid] = cnt.get(cid, 0) + 1
            legend[LEG_CHAR.get(cid, cid)] = 1
        if v3 and b["v3"]["hero"]:
            feet.append((0, base_x + b["v3"]["hero"][0], base_y + b["v3"]["hero"][1]))
        elif r == 0:
            feet.append((0, base_x + P.WALL + P.FLOOR_W // 2, base_y + P.M + (nb - 1) * BH + BH - 40))
        for cid, fx, fy in feet:
            d = 4 if cid == 0 and r == 0 else 0
            if v3:
                spr0, anc0 = R.sprite(cid, d, 0)
                g, ln = V3.shadow_dir(b, fx - base_x, fy - base_y)
                shade(canvas, R.shadow(cid, d, 0), fx, fy)      # sombra a 1 bpp bajo los pies: la misma que dibuja la ROM
                if g is not None:                                # ademas, con luz direccional (dia/noche, cera...), la proyectada
                    V3.cast_shadow(canvas, spr0, anc0, fx, fy, g, ln)
            else:
                shade(canvas, R.shadow(cid, d, 0), fx, fy)
        for cid, fx, fy in feet:
            d = 4 if cid == 0 and r == 0 else 0
            spr, anc = R.sprite(cid, d, 0)
            if v3:
                spr = V3.tint_sprite(spr, V3.sprite_factor(b, fx - base_x, fy - base_y))
            elif b.get("mult") is not None:
                my = int(min(max(fy - base_y - 4, 0), b["mult"].shape[0] - 1))
                mx = int(min(max(fx - base_x, 0), 255))
                spr = spr.copy()
                spr[:, :, :3] = np.clip(spr[:, :, :3].astype(np.float64) * b["mult"][my, mx], 0, 255).astype(np.uint8)
            items.append((fy, Image.fromarray(spr), fx - spr.shape[1] // 2, fy - anc))
        if rd["gate"]:
            v = Image.fromarray(verja_art())
            gy = base_y + P.M + (nb - 1 - (nb - 1)) * BH + 150
            items.append((gy, v, base_x + P.WALL, gy - v.height))
            vm = v.transpose(Image.FLIP_LEFT_RIGHT)
            items.append((gy, vm, base_x + P.WALL + P.FLOOR_W - vm.width, gy - vm.height))
        stats[r] = (cnt, len(ens))
        if hand_members(r) is not None or os.environ.get("POSTER_DEBUG"):
            avisos_solape(r, rd, b, ens)
    items.sort(key=lambda t: t[0])
    ov = None
    if getattr(a, "revision", False):
        ov = canvas.copy()
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        for r, b in built.items():
            if hand_members(r) is not None:
                dibuja_revision(ImageDraw.Draw(layer), r, rooms[r], geo[r][0] + ox, geo[r][1] + oy)
        ov = Image.alpha_composite(ov, layer)
    for _, img, x, y in items:
        canvas.paste(img, (x, y), img)
        if ov is not None:
            ov.paste(img, (x, y), img)
    if getattr(a, "sala", None) is not None:
        return salida_sala(a, canvas, ov, rects, ox, oy, only, rooms, geo)

    # etiquetas fuera del suelo: insignia sobre el muro del fondo, cartel en el margen con hilo fino
    d = ImageDraw.Draw(canvas)
    f0, f1, f2 = P.font(88), P.font(40), P.font(28)
    d.text((60, 40), "DungeonDS ARPG  -  mapa de la demo (camara del juego)", fill=(205, 195, 170), font=f0)
    BW = 600                                        # ancho del cartel
    def wrap(txt, font):
        out, cur = [], ""
        for w in txt.split(", "):
            t = (cur + ", " + w) if cur else w
            if d.textlength(t, font=font) > BW - 28 and cur:
                out.append(cur + ",")
                cur = w
            else:
                cur = t
        return out + [cur]
    def wrapw(txt, font):
        out, cur = [], ""
        for w in txt.split(" "):
            t = (cur + " " + w) if cur else w
            if d.textlength(t, font=font) > BW - 28 and cur:
                out.append(cur)
                cur = w
            else:
                cur = t
        return out + [cur]
    labels = []
    for r, b in built.items():
        sx, sy0 = geo[r]
        rd = rooms[r]
        cnt, tot = stats[r]
        cx = sx + ox + P.VIEW_W // 2
        # el punto cae en el suelo de su sala: lo mas cerca del centro vertical donde el hilo hacia su cartel no cruza otras salas
        left_side = pos[r][0] <= 0
        ftop, fbot = sy0 + oy + P.M, sy0 + oy + P.M + rd['blocks'] * BH
        xe = (30 + 600) if left_side else (W - 30 - 600)
        xa, xb = min(cx, xe), max(cx, xe)
        blk = [(q[1] + oy, q[3] + oy) for o, q in rects.items() if o != r and q[0] + ox < xb and q[2] + ox > xa]
        mid = (ftop + fbot) // 2
        cands = [y for y in range(ftop + 50, fbot - 49, 8) if all(not (b0 - 12 < y < b1 + 12) for b0, b1 in blk)]
        cy = min(cands, key=lambda y: abs(y - mid)) if cands else mid
        byname = {}
        for c, n in sorted(cnt.items()):
            nm = NAMES[c].split(" (")[0]
            byname[nm] = byname.get(nm, 0) + n
        parts = [f"{n} {nm}" for nm, n in byname.items()]
        sub = (f"{rd['blocks']} bloque{'s' if rd['blocks'] > 1 else ''}, {tot} enemigos" if tot else "sin enemigos")
        extras = ["altar" if rd["altar"] else "", "cofre" if rd["chest"] else "", "reja con llave" if rd["gate"] else ""]
        lines = [(f"{r}  {rd['name']}", f1, (235, 215, 150))]
        if b.get("amb_label"):
            lines.append(("ambiente: " + b["amb_label"], f2, (225, 205, 120)))
        lines += [(t, f2, (190, 185, 170)) for t in [f"nivel {rd['level']} - " + sub]]
        if rd["type"] == "CRIPTA":
            lines.append(("jefe (fase 1): el Abanderado con sus escoltas", f2, (190, 185, 170)))
        lines += [(t, f2, (170, 165, 150)) for t in wrap(", ".join(parts), f2)] if parts else []
        ab = cfgs.get(r, {}).get("ambiente") if amb else None
        if ab:
            lines[2:2] = [(t, f2, (200, 190, 150)) for t in wrapw(ab["funcion"], f2)]
            lines.append(("luz: " + (ab["luz"]["acento"]["nombre"] if ab["luz"]["acento"]["nombre"] != "ninguno" else "solo profundidad") + ", nivel " + str(ab["luz"]["nivel"]), f2, (150, 165, 185)))
            if ab["pendiente"]:
                lines.append((ab["pendiente"], f2, (200, 140, 120)))
        ex = ", ".join(e for e in extras if e)
        if ex:
            lines.append((ex, f2, (150, 175, 160)))
        labels.append([cy, cx, pos[r][0] <= 0, lines, r])
    def hbox_of(lines):
        return 20 + 44 + 34 * (len(lines) - 1)
    for side in (True, False):
        col = sorted([l for l in labels if l[2] == side], key=lambda l: l[0])
        ytop = None
        for l in col:
            want = l[0] - hbox_of(l[3]) // 2
            if ytop is not None and want < ytop:
                want = ytop
            l.append(want)
            ytop = want + hbox_of(l[3]) + 14
        for l in col:
            cy, cx, left, lines, r, top = l
            bx = 30 if left else W - 30 - BW
            bxe = bx + BW if left else bx
            hb = hbox_of(lines)
            d.line((bxe, top + hb // 2, cx, cy), fill=(120, 112, 96), width=2)
            d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(235, 215, 150))
            d.rectangle((bx, top, bx + BW, top + hb), fill=(10, 8, 12), outline=(70, 64, 56))
            y = top + 10
            for t, f, colr in lines:
                d.text((bx + 14, y), t, fill=colr, font=f)
                y += 44 if f is f1 else 34
    # leyenda de enemigos: fila bajo el titulo
    lx, ly = 60, 150
    d.text((lx, ly), "Enemigos de la demo (primer fotograma de la ROM, mirando al sur)", fill=(205, 195, 170), font=f1)
    ly += 70
    for cid in sorted(legend):
        if cid == 5:
            continue
        spr, anc = R.sprite(cid, 0, 0)
        im = Image.fromarray(spr)
        bb = im.getbbox()
        im = im.crop(bb).resize(((bb[2] - bb[0]) * 2, (bb[3] - bb[1]) * 2), Image.NEAREST)
        canvas.paste(im, (lx + (110 - im.width) // 2, ly + 110 - im.height), im)
        nm = NAMES[cid].split(" (")[0]
        d.text((lx + 120, ly + 50), nm, fill=(200, 192, 175), font=f2)
        lx += 110 + int(d.textlength(nm, font=f2)) + 30
    d.text((60, ly + 125), "Posiciones deterministas (seed de sala, igual que la ROM); la demo no tiene oleadas: cada bloque es un grupo fijo", fill=(150, 145, 135), font=f2)

    img = canvas.convert("RGB")
    a.out.mkdir(parents=True, exist_ok=True)
    img.save(a.out / f"{a.name}.png")
    k = a.movil_ancho / img.width       # el poster es muy alto: la version movil se fija por ancho
    mob = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    mob.save(a.out / f"{a.name}_movil.png")
    print("juego", img.size, "->", a.out / f"{a.name}.png", "| movil", mob.size)
