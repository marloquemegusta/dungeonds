"""Ambientes por sala del poster ARPG v2: composicion disenada (en vez de plantas al azar) y luz en dos capas.
Lee el bloque `ambiente` de cada sala en poster_arpg.json (lo escribe gen_ambientes_arpg.py).
Todo lo de la luz es aproximable en la DS con un tinte de paleta por sala mas halos de sprite; lo que no, se anota en
DESIGN-ARPG.md «Identidad visual por sala»."""
import numpy as np

BLOCK_H, FLOOR_W = 384, 208
WALL = 24
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float64) / 16.0


def reserved(rd, nb):
    """Rectangulos vedados (k, x0, y0, x1, y1) en px locales del bloque: altar y cofre estampados por el motor, y el paso de las puertas."""
    out = []
    if rd["altar"]:
        out.append((0, 28, 262, 72, 330))
    if rd["chest"]:
        out.append((nb - 1, 72, 44, 136, 100))
    for d in rd["doors"]:
        if d["side"] in "LR":
            kb = (d["screen"] - 1) // 2
            out.append((kb, 0, 206, 52, 244) if d["side"] == "L" else (kb, FLOOR_W - 52, 206, FLOOR_W, 244))
    return out


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


SHIFTS = [(0, 0)] + [(dx, dy) for dx in (-8, 8, -16, 16, -24, 24, -32, 32, -48, 48) for dy in (0, -8, 8, -16, 16)]


def pieces_for_block(kit, amb, k, rd, nb, enemies, rep):
    """Piezas de la composicion para el bloque k, apartadas de enemigos y de lo vedado. Cuenta movidas y quitadas en rep."""
    res = [r for r in reserved(rd, nb) if r[0] == k]
    ens = [(x, y) for (x, y, kk) in enemies if kk == k]
    if __import__("os").environ.get("POSTER_DEBUG"):
        print("   k", k, "reservado", [r[1:] for r in res], "enemigos", ens)
    taken = []
    out = []
    for it in amb.get("composicion", []):
        if it["k"] != k:
            continue
        lay = kit.layout(it["piece"])
        w, h = lay["w"], lay["h"]
        base = 14 if not it["piece"].startswith("vela") else h
        oys, oxs = np.nonzero(lay["op"])
        bx0, bx1, by1 = (int(oxs.min()), int(oxs.max()) + 1, int(oys.max()) + 1) if len(oxs) else (0, w, h)
        done = False
        for dx, dy in SHIFTS:
            x, y = it["x"] + dx, it["y"] + dy
            if x + bx0 < 0 or x + bx1 > FLOOR_W or y < 0 or y + h > BLOCK_H:
                continue
            rect = (x + bx0, y + by1 - base, x + bx1, y + by1)
            if not it.get("en_pasillo") and any(_hit(rect, r[1:]) for r in res):
                continue
            if any(_hit(rect, (ex - 13, ey - 10, ex + 13, ey + 6)) for ex, ey in ens):
                continue
            if any(_hit(rect, t) for t in taken):
                continue
            taken.append(rect)
            if (dx, dy) != (0, 0):
                rep["movidas"] += 1
                if __import__("os").environ.get("POSTER_DEBUG"):
                    print("   movida", it["piece"], it["k"], it["x"], it["y"], "->", x, y)
            out.append({"piece": it["piece"], "lx": x, "ly": y, "mirror": 0})
            done = True
            break
        if not done:
            rep["quitadas"] += 1
            if __import__("os").environ.get("POSTER_DEBUG"):
                print("   quitada", it["piece"], it["k"], it["x"], it["y"], "w,h", w, h)
    return out


def light_maps(amb, cfg, rd, nb, Ht, sprites, M):
    """(mult HxWx3 float, add HxWx3 float, mult_back) de la sala. mult = tinte multiplicativo (profundidad x acento) con caida
    suave al fondo y a los bordes; add = halos calidos y pozos de vidriera. Cuantizado y tramado como la DS lo aproximaria."""
    L = amb["luz"]
    dep = cfg["luz_profundidad"][str(L["nivel"])]
    ac = L["acento"]
    f = ac["fuerza"]
    col = np.array(dep["tinte"], np.float64) / 255.0 * dep["brillo"] * ((1 - f) + f * np.array(ac["tinte"], np.float64) / 255.0)
    W = 256
    ys = np.arange(Ht, dtype=np.float64)[:, None]
    xs = np.arange(W, dtype=np.float64)[None, :]
    t_back = np.clip(1.0 - (ys - M) / float(Ht - M), 0, 1)
    e = np.abs(xs - (W - 1) / 2.0) / ((W - 1) / 2.0)
    gain = (1.0 - L["fondo"] * t_back ** 1.3) * (1.0 - L["caida"] * e ** 2)
    yy, xx = np.mgrid[0:Ht, 0:W]
    bay = BAYER[yy % 4, xx % 4]
    q = 12.0
    gain = np.floor(gain * q + bay) / q
    mult = gain[:, :, None] * col[None, None, :]
    add = np.zeros_like(mult)
    halos = list(L.get("halos", []))
    for s in sprites:
        p = s.get("piece")
        h, w = s["op"].shape
        if p == "vela":
            halos.append({"px": s["x0"] + w / 2.0, "py": s["y0"] + 5, "r": cfg["halo_velas"]["r"], "color": cfg["halo_velas"]["color"],
                          "fuerza": cfg["halo_velas"]["fuerza"]})
        elif p == "altar":
            halos.append({"px": s["x0"] + w / 2.0, "py": s["y0"] + 8, "r": cfg["halo_altar"]["r"], "color": cfg["halo_altar"]["color"],
                          "fuerza": cfg["halo_altar"]["fuerza"]})
    pool = np.zeros((Ht, W), np.float64)
    keep = np.ones((Ht, W), np.float64)
    hc = np.zeros(3)
    tot = np.zeros((Ht, W), np.float64)
    for hh in halos:
        if "px" in hh:
            cx, cy = hh["px"], hh["py"]
        else:
            cx = WALL + hh["x"]
            cy = M + (nb - 1 - hh["k"]) * BLOCK_H + hh["y"]
        d = np.sqrt(((xx - cx) / 1.0) ** 2 + ((yy - cy) * 1.6) ** 2) / hh["r"]     # elipse: el suelo esta en perspectiva 2:1
        I = np.clip(1.0 - d, 0, 1) ** 1.6 * hh["fuerza"]
        keep *= (1.0 - I)
        add += I[:, :, None] * (np.array(hh["color"], np.float64) / 255.0)[None, None, :]
        tot = 1 - (1 - tot) * (1 - I)
    if halos:
        tq = np.floor(tot * 6.0 + bay) / 6.0                 # 6 anillos tramados: un halo de sprite en la DS
        scale = np.where(tot > 1e-6, tq / np.maximum(tot, 1e-6), 0.0)
        add *= scale[:, :, None]
        mult = mult + (1.0 - mult) * (np.minimum(tq * 1.6, 1.0))[:, :, None] * 0.7
    if L.get("vidrieras"):
        for cx, cy, r, c in ((128, M + 300, 70, (200, 165, 90)), (128, M + 560, 70, (175, 112, 112)),
                             (128, M + 820, 70, (112, 135, 178))):
            d = np.sqrt(((xx - cx) / 1.0) ** 2 + ((yy - cy) * 2.2) ** 2) / r
            I = np.clip(1.0 - d, 0, 1) ** 1.1 * 0.30
            I = np.floor(I * 8.0 + bay) / 8.0
            add += I[:, :, None] * (np.array(c, np.float64) / 255.0)[None, None, :]
    return mult, add


def apply(rgb, mult, add):
    out = rgb.astype(np.float64) * mult + add * 255.0
    return np.clip(out, 0, 255).astype(np.uint8)
