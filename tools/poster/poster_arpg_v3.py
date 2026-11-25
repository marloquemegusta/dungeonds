"""Poster v3 del ARPG: seis ambientes de luz y sombra con el pipeline del campamento nocturno.

Render real (lab de props con la luz del ambiente, via props_ambiente.py + prop_shadows.py): los props con GLB local.
Luz horneada de suelo y muros: las bandas de tools/camp/bake_camp_arena.py (BAND_L, BAND_WARM, MOON_TINT, FIRE_TINT,
SATURATION_KEEP, tramado Bayer 4x4, caida f^1.9 en distancia isometrica) con fuentes por sala.
Aproximacion: enemigos, heroe y los props sin GLB (banco_entero, banco_volcado, santo): se tiñen con la banda de luz
del punto donde pisan y su sombra es la silueta cizallada hacia el lado contrario a la fuente.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import poster_arpg as P
import poster_acto1 as p1
import props_ambiente as PA

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "camp"))
import bake_camp_arena as BC          # noqa: E402  (constantes de banda y tintes del campamento)

bk = p1.bk
OUT = Path(PA.OUT)
M, BH, WALL = P.M, P.BLOCK_H, P.WALL
GAIN = 1.7
EMISIVAS = ("vela", "camp_n_hoguera")
REALES = set(PA.GLB_PIECES)

ROOM_AMB = {0: "cielo", 1: "cielo", 2: "cielo", 3: "cielo", 6: "dia", 7: "dia", 8: "cera", 10: "cera", 11: "cera", 13: "cera",
            12: "farol", 4: "farol", 5: "farol", 9: "techo", 14: "sinluz", 15: "hoguera"}
NOMBRE = {"cielo": "Cielo mudo", "dia": "Intemperie (dia)", "noche": "Intemperie (noche)", "cera": "Cera",
          "farol": "Faroles del Tribunal", "sinluz": "Sin luz", "hoguera": "Hogueras de la Columna", "techo": "Luz del techo"}
CIELO_NIVEL = {0: 0.64, 1: 0.47, 2: 0.33, 3: 0.20}
# amb = luz de fondo; src = (radio iso, fuerza); cold/warm = tintes (frio sin fuente / de la fuente); ref = L de referencia del lab
AM = {
    "cielo": dict(cold=np.array([0.86, 0.90, 1.00]), warm=np.array([0.86, 0.90, 1.00]), ref=0.5, pg=1.5, tag="c", dir=(0.85, 0.5), slen=0.9),
    "dia": dict(cold=np.array([1.0, 0.93, 0.78]), warm=np.array([1.0, 0.93, 0.78]), ref=0.8, pg=1.7, tag="c", dir=(0.5, 0.35), slen=0.45),
    "noche": dict(cold=BC.MOON_TINT, warm=BC.MOON_TINT, ref=0.2, pg=1.1, tag="c", dir=(0.4, 0.3), slen=0.14),
    "cera": dict(cold=np.array([0.62, 0.52, 0.56]), warm=BC.FIRE_TINT, ref=0.5, tag="lr", slen=0.6, src=(125, 0.95)),
    "farol": dict(cold=np.array([0.55, 0.62, 0.80]), warm=np.array([0.92, 0.97, 1.0]), ref=0.5, pg=1.8, tag="lr", slen=0.9, src=(98, 0.9)),
    "sinluz": dict(cold=BC.MOON_TINT, warm=BC.MOON_TINT, ref=0.1, pg=1.7, tag="c", dir=None, slen=0.0, src=(130, 0.32)),
    "hoguera": dict(cold=BC.MOON_TINT, warm=BC.FIRE_TINT, ref=0.5, tag="lr", slen=0.7, src=(290, 1.0)),
    # luz cenital desde el techo de la catedral: props horneados con la luz neutra de los personajes; la sala solo pone
    # tono (tint) e intensidad (L, 0.59 = luz plena de los sprites) por igual a suelo, props y personajes
    "techo": dict(cold=np.ones(3), warm=np.ones(3), ref=0.59, tag="c", dir=None, slen=0.0),
}
TECHO_SOMBRA_MAX = 8              # alcance maximo (px) de la sombra proyectada de piezas bajo techo (= margen izquierdo del lienzo)
TECHO_DIR, TECHO_LEN = (-0.8, 0.3), 0.35     # sombra corta comun de los personajes bajo techo
TECHO = {9: dict(L=0.34, tint=np.array([0.80, 0.86, 1.00]))}      # Osario: penumbra fria
# Piezas que v3 anade a la composicion de v2 (k, x, y locales del bloque): fuentes de luz dibujadas.
EXTRA = {
    8: [("vela", 0, 40, 150), ("vela", 0, 160, 130), ("vela", 1, 40, 200), ("vela", 1, 150, 90), ("vela", 2, 60, 120), ("vela", 2, 150, 260)],
    12: [("vela", 0, 96, 190), ("vela", 1, 96, 190)],            # farol: falta pieza, se dibuja la vela
    4: [("vela", 0, 96, 24)], 5: [("vela", 0, 96, 24)],
    15: [("camp_n_hoguera", 0, 84, 240)],
}
PINES = {}
# Props tematicos (commit f3a49652 de claude/props-tematicos-84feb8) por sala: se quitan los provisionales de v2 y se anaden
# las piezas nuevas (piece, k, x, y), x/y locales del bloque. Los pasos y el centro de combate se respetan (pieces_for_block).
_TEM = {
    8: dict(drop={"banco_roto", "banco_volcado"}, add=[
        ("catre", 0, 6, 60), ("catre", 0, 136, 150), ("biombo", 0, 8, 240), ("palangana", 0, 150, 250),
        ("catre", 1, 136, 60), ("catre", 1, 6, 150), ("biombo", 1, 140, 230), ("palangana", 1, 20, 300),
        ("catre", 2, 6, 70), ("catre", 2, 136, 170), ("biombo", 2, 10, 260), ("palangana", 2, 160, 100)]),
    10: dict(drop={"banco_entero"}, add=[("reclinatorio", 0, 8, 208), ("reclinatorio", 0, 156, 208), ("reclinatorio", 0, 8, 268),
                                         ("reclinatorio", 0, 156, 268), ("candelabro_pie", 0, 60, 10), ("candelabro_pie", 0, 126, 10),
                                         ("exvoto", 0, 30, 40), ("exvoto", 0, 128, 40)]),
    13: dict(drop=set(), add=[("candelabro_pie", 0, 60, 10), ("candelabro_pie", 0, 126, 10), ("reclinatorio", 0, 10, 208),
                              ("reclinatorio", 0, 154, 208), ("exvoto", 0, 30, 50), ("exvoto", 0, 128, 50)]),
    11: dict(drop={"banco_entero"}, add=[("reclinatorio", 0, 8, 100), ("reclinatorio", 0, 156, 100), ("reclinatorio", 0, 8, 172),
                                         ("reclinatorio", 0, 124, 172), ("reclinatorio", 0, 8, 240), ("reclinatorio", 0, 156, 240),
                                         ("candelabro_pie", 1, 60, 10), ("candelabro_pie", 1, 126, 10)]),
    15: dict(drop={"columna_entera", "santo", "santo_der"}, add=[
        ("brasero", 0, 6, 24), ("brasero", 0, 162, 24), ("brasero", 0, 6, 240), ("brasero", 0, 162, 240),
        ("sarcofago", 0, 0, 120), ("sarcofago", 0, 136, 120), ("lapida_pie", 0, 8, 190), ("lapida_pie", 0, 168, 190)]),
    12: dict(drop=set(), add=[("cepo", 0, 8, 160), ("cepo", 1, 148, 160), ("capullo", 1, 100, 40), ("capullo", 1, 8, 40)]),
    5: dict(drop=set(), add=[("capullo", 0, 150, 200), ("capullo", 0, 20, 120)]),
    4: dict(drop=set(), add=[("cepo", 0, 150, 150), ("capullo", 0, 30, 120)]),
}
FUENTES_DEBILES = {"brasero": 0.4, "candelabro_pie": 0.6}
COLGADOS = {}   # props colgados del muro norte: (pieza, x_centro, elev) con elev = px entre su base y el pie del muro; sin sombra de suelo
# Cada sala tiene su archivo salas/sala_NN.py (AMB, LUZ, DROP, ADD y EXTRA opcional) que manda sobre lo de arriba.
import importlib.util as _ilu                    # noqa: E402
for _n in range(16):
    _f = Path(__file__).with_name("salas") / f"sala_{_n:02d}.py"
    if not _f.exists():
        continue
    _sp = _ilu.spec_from_file_location(f"sala_{_n:02d}", _f)
    _m = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_m)
    if _m.AMB:
        ROOM_AMB[_n] = _m.AMB
    if _m.LUZ:
        TECHO[_n] = dict(L=_m.LUZ["L"], tint=np.array(_m.LUZ["tint"], float))
    _TEM[_n] = dict(drop=set(_m.DROP), add=list(_m.ADD))
    EXTRA[_n] = list(getattr(_m, "EXTRA", []))
    COLGADOS[_n] = list(getattr(_m, "COLGADOS", []))


def to555(rgb):
    r, g, b = (rgb[..., 0].astype(np.uint16) >> 3), (rgb[..., 1].astype(np.uint16) >> 3), (rgb[..., 2].astype(np.uint16) >> 3)
    return (r | (g << 5) | (b << 10) | 0x8000).astype(np.uint16)


def shear_shadow(op, g, slen, wide, tall):
    """Silueta (mascara op de una pieza) cizallada sobre el suelo en la direccion g (pantalla) con longitud slen*altura."""
    h, w = op.shape
    ys, xs = np.nonzero(op)
    foot = ys.max() if len(ys) else h - 1
    hh = (foot - ys).astype(np.float64)
    X = np.round(xs + g[0] * hh * slen).astype(int)
    Y = np.round(foot + g[1] * hh * slen).astype(int)
    out = np.zeros((tall, wide), bool)
    ok = (X >= 0) & (X < wide) & (Y >= 0) & (Y < tall)
    out[Y[ok], X[ok]] = True
    # rellena huecos del cizallado (cada fila origen deja columnas sueltas)
    out |= np.roll(out, 1, 1) & np.roll(out, -1, 1)
    out |= np.roll(out, 1, 0) & np.roll(out, -1, 0)
    return out


def contact_shadow(op, sh, amb):
    """Luz del techo: la sombra horneada cae casi entera bajo la pieza y no se ve. Anade una proyeccion corta comun
    (misma regla que los personajes, TECHO_DIR): la silueta cizallada hacia la izquierda y 1 px abajo, hasta el margen del lienzo."""
    if amb != "techo" or not op.any():
        return sh
    h, w = op.shape
    ys = np.nonzero(op.any(1))[0]
    hh = (ys.max() - np.arange(h))[:, None] * np.ones((1, w), int)
    out = sh.copy()
    for s_ in range(1, TECHO_SOMBRA_MAX + 1):
        m = op & (hh >= s_ * 2)
        for dy in (0, 1):
            sm = np.zeros_like(op)
            if dy:
                sm[1:, :w - s_] = m[:-1, s_:]
            else:
                sm[:, :w - s_] = m[:, s_:]
            out |= sm
    return out & ~op


class AmbKit:
    """Kit con las piezas del ambiente: «pieza@tag» = render real en render_amb/<ambiente>/<tag>/ si existe; si no, la pieza del juego."""

    def __init__(self, kit, amb):
        self.kit, self.amb, self._c = kit, amb, {}

    def __getattr__(self, k):
        return getattr(self.kit, k)

    def layout(self, name):
        if name not in self._c:
            self._c[name] = self._make(name)
        return self._c[name]

    def _make(self, name):
        if name.split("@")[0].endswith("~"):                 # «pieza~»: la misma pieza en espejo (estantes del muro izquierdo)
            lay = self.layout(name.replace("~", "", 1))
            return {**lay, **{k: lay[k][:, ::-1].copy() for k in ("pix", "op", "sh")}}
        base, _, tag = name.partition("@")
        folder = OUT / self.amb / tag / base if tag else None
        if folder is not None and (folder / "color.png").exists():
            for f in ("depth.png", "footprint.png"):
                if not (folder / f).exists():
                    src = ROOT / "assets/environment/cathedral/props/render" / base / f
                    (folder / f).write_bytes(src.read_bytes())
            old = bk.PROP_DIR
            bk.PROP_DIR = OUT / self.amb / tag
            try:
                lay = bk.source_layout(base)
            finally:
                bk.PROP_DIR = old
            op = lay["rgba"][:, :, 3] >= 128
            rgb = lay["rgba"][:, :, :3]
            if self.amb == "noche" and base.startswith("columna"):
                # el albedo de la columna es pardo-dorado y la luz fria del lab no lo apaga: de noche el fuste va a gris azulado
                lum = (rgb[..., 0] * 0.30 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11)[..., None]
                cold = np.array([0.80, 0.90, 1.25])
                rgb = np.clip(rgb * 0.15 + lum * cold * 0.85 * 1.0, 0, 255).astype(np.uint8)
            return {"w": lay["w"], "h": lay["h"], "pix": to555(rgb), "op": op,
                    "sh": contact_shadow(op, (lay["shadow"] if lay["shadow"] is not None else np.zeros(op.shape, bool)) & ~op, self.amb),
                    "anchor": lay["foot_anchor_y_px"], "real": True, "emisiva": False,
                    "ox": lay.get("ox", 0), "oy": lay.get("oy", 0)}   # sombra con margen a la izquierda/arriba (noche): place() resta el margen
        lay = self.kit.layout(base)
        if base in EMISIVAS or not tag:
            return {**lay, "real": False, "emisiva": True}
        # aproximacion: silueta del sprite del juego cizallada hacia el lado contrario a la fuente
        spec = AM[self.amb]
        g = (0.95, 0.30) if tag == "l" else (-0.95, 0.30) if tag == "r" else spec["dir"]
        h, w = lay["op"].shape
        if g is None or spec["slen"] <= 0:
            # luz del techo: sin direccion propia, la pieza lleva la sombra a 1 bpp que ya dibuja la ROM (la de prop_shadows)
            sh = contact_shadow(lay["op"], lay["sh"] & ~lay["op"], self.amb) if self.amb == "techo" else np.zeros_like(lay["sh"])
            return {**lay, "real": False, "emisiva": False, "sh": sh}
        ext = int(h * spec["slen"] * 1.0)
        W2 = w + (-(-ext // 8) * 8 if g[0] > 0 else 0)
        H2 = h + (-(-int(ext * abs(g[1])) // 8) * 8)
        op2 = np.zeros((H2, W2), bool)
        pix2 = np.zeros((H2, W2), np.uint16)
        op2[:h, :w] = lay["op"]
        pix2[:h, :w] = lay["pix"]
        sh = shear_shadow(lay["op"], g, spec["slen"], W2, H2) & ~op2
        return {"w": W2, "h": H2, "pix": pix2, "op": op2, "sh": sh, "anchor": lay["anchor"], "real": False, "emisiva": False}


def source_points(items, nb, amb, ex_lamps=()):
    """Fuentes de luz de la sala en px de imagen (x, y): velas, altar y hoguera de la composicion."""
    pts = []
    for it in items:
        base = it["piece"].partition("@")[0]
        if base == "vela" or (amb == "cera" and base == "altar") or base == "camp_n_hoguera" or base in FUENTES_DEBILES:
            lay_w = 16 if base == "vela" else 24 if base == "altar" else 40
            pts.append((WALL + it["x"] + lay_w / 2.0, M + (nb - 1 - it["k"]) * BH + it["y"] + (6 if base == "vela" else 14),
                        FUENTES_DEBILES.get(base, 1.0)))
    return pts


def light_grids(amb, room, Ht, nb, srcs, hero=None):
    """(Lq, tint) por pixel de la imagen de sala: luz escalar, banda del campamento y tinte frio/calido."""
    W = 256
    yy, xx = np.mgrid[0:Ht, 0:W].astype(np.float64)
    spec = AM[amb]
    t_back = np.clip(1.0 - (yy - M) / float(Ht - M), 0, 1)
    edge = np.minimum.reduce([xx, (W - 1) - xx, (yy - M) * 0.55 + 8, (Ht - 1 - yy) * 0.55 + 8])
    vign = np.clip(edge / 40.0, 0, 1)
    vign = vign * vign * (3 - 2 * vign)
    if amb == "cielo":
        amb_l = CIELO_NIVEL[room] * (1.0 - 0.58 * t_back ** 1.15) * (0.88 + 0.12 * vign)
    elif amb == "dia":
        amb_l = 0.86 * (0.90 + 0.10 * vign)
    elif amb == "noche":
        amb_l = 0.21 * (0.85 + 0.15 * vign)
    elif amb == "cera":
        amb_l = 0.03 + 0.025 * vign
    elif amb == "farol":
        amb_l = 0.11 + 0.04 * vign
    elif amb == "sinluz":
        amb_l = 0.17 + 0.05 * vign
    elif amb == "techo":
        amb_l = TECHO[room]["L"] * (0.82 + 0.18 * vign)
    else:
        amb_l = 0.125 + 0.09 * vign - 0.06 * (1 - vign)            # campamento: bordes casi negros
    src = np.zeros((Ht, W))
    pts = list(srcs) + ([hero] if (amb == "sinluz" and hero) else [])
    if amb == "techo":                                      # luz del techo: las velas se dibujan, no alumbran (por ahora)
        pts = []
    R, K = spec.get("src", (0, 0))
    for pt in pts:
        sx, sy = pt[0], pt[1]
        R, K = spec.get("src", (0, 0))
        R = R * (pt[2] if len(pt) > 2 else 1.0)
        d = np.sqrt((xx - sx) ** 2 + (2 * (yy - sy)) ** 2)
        if amb == "farol":
            f = np.where(d <= R, K * (1.0 - 0.30 * (d / R) ** 2), 0.0)     # cono duro: borde cortado
        else:
            fl = np.clip(1.0 - d / R, 0, 1)
            f = K * fl ** 1.9 + (0.35 * np.exp(-(d / 22.0) ** 2) if amb in ("hoguera", "cera") else 0.0)
        src = 1.0 - (1.0 - src) * (1.0 - np.clip(f, 0, 1))
    L = np.clip(amb_l + src, 0, 1)
    warm = np.clip(src / np.maximum(L, 1e-3), 0, 1)
    bf = np.interp(L, BC.BAND_L, np.arange(BC.N_BANDS))
    band = np.clip(np.floor(bf + BC.BAYER_T[yy.astype(int) % 4, xx.astype(int) % 4]), 0, BC.N_BANDS - 1).astype(int)
    Lq = BC.BAND_L[band]
    if amb == "techo":                                      # luz cenital uniforme: sin bandas ni tramado
        Lq = L
    tint = spec["cold"][None, None, :] * (1 - warm)[:, :, None] + spec["warm"][None, None, :] * warm[:, :, None]
    if amb == "techo":
        tint = np.broadcast_to(TECHO[room]["tint"], (Ht, W, 3)).copy()
    return Lq, tint


def relight(rgb, Lq, tint):
    f = rgb.astype(np.float64) / 255.0 * tint * (Lq * GAIN)[:, :, None]
    lum = (0.30 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2])[..., None]
    f = lum + (f - lum) * BC.SATURATION_KEEP
    return np.clip(f * 255.0, 0, 255).astype(np.uint8)


def limit_palette(rgb, alpha, colors=176):
    im = Image.fromarray(rgb).quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    a = np.asarray(im)
    a = (a >> 3) << 3
    return np.where(alpha[:, :, None], a, 0).astype(np.uint8)


def tag_for(amb, x, y, k, nb, pts):
    spec = AM[amb]
    if spec["tag"] != "lr":
        return spec["tag"]
    if not pts:
        return "l"
    px, py = WALL + x, M + (nb - 1 - k) * BH + y
    sx, sy = min(pts, key=lambda s: (s[0] - px) ** 2 + (2 * (s[1] - py)) ** 2)[:2]
    return "l" if sx <= px else "r"


def build(kit, plan, room, rd, cfg, hole, ends, gcfg, enemies, variant):
    """Sala de v3: composicion de v2 mas las fuentes de luz; suelo y muros horneados por banda; props con render real."""
    amb = variant if room in (6, 7) else ROOM_AMB[room]
    ab = cfg["ambiente"]
    nb = rd["blocks"]
    Ht = nb * BH + M
    tem = _TEM.get(room, {"drop": set(), "add": []})
    items = [dict(it) for it in ab["composicion"] if it["piece"] not in tem["drop"]]
    if room in (6, 7):                                      # la columna entera mide 160 de alto: no cabe en y=256
        for it in items:
            if it["piece"] == "columna_entera" and it["y"] > 200:
                it["y"] = 216
    for (piece, k, x, y) in tem["add"]:
        items.append({"piece": piece, "k": k, "x": x, "y": y})
    for (piece, k, x, y) in EXTRA.get(room, []):
        items.append({"piece": piece, "k": k, "x": x, "y": y, "en_pasillo": True})
    srcs = source_points(items, nb, amb)
    for it in items:
        base = it["piece"]
        if base in EMISIVAS:
            continue
        t = tag_for(amb, it["x"], it["y"], it["k"], nb, srcs)
        it["piece"] = f"{base}@{t}"
    ab3 = {"composicion": items}
    akit = AmbKit(kit, amb)
    rep = {"movidas": 0, "quitadas": 0}
    full = np.zeros((Ht, P.VIEW_W), np.uint16)
    floor = np.zeros_like(full)
    alpha = np.zeros((Ht, P.VIEW_W), bool)
    alpha[M:] = True
    sprites = []
    for k in range(nb):
        row0 = M + (nb - 1 - k) * BH
        canvas = kit.floor_block.copy()
        w = kit.wall != 0
        canvas[w] = kit.wall[w]
        fl = canvas.copy()
        pieces = P.amb_mod.pieces_for_block(akit, ab3, k, rd, nb, enemies, rep)
        sp = []
        p1.place(akit, canvas, pieces, floor555=fl, sprites=sp)
        full[row0:row0 + BH] = canvas
        floor[row0:row0 + BH] = fl
        for s in sp:
            s["y0"] += row0
            s["ay"] += row0
            sprites.append(s)
    if rd["altar"]:
        t = tag_for(amb, 36, 280, 0, nb, srcs)
        lay = akit.layout(f"altar@{t}")
        row0 = M + (nb - 1) * BH
        s = P.stamp_layout(full, floor, lay, P.FLOOR_X + 48 - P.VIEW_X0 - lay["w"] // 2, row0 + 316 - lay["anchor"])
        sprites.append({**s, "piece": f"altar@{t}"})
    if rd["chest"]:
        t = tag_for(amb, 104, 90, nb - 1, nb, srcs)
        lay = akit.layout(f"cofre_cerrado@{t}")
        sprites.append({**P.stamp_layout(full, floor, lay, P.FLOOR_X + P.FLOOR_W // 2 - P.VIEW_X0 - lay["w"] // 2, M + 90 - lay["anchor"]),
                        "piece": f"cofre_cerrado@{t}"})
    for d in rd["doors"]:
        if d["side"] == "U":
            continue
        kb = (d["screen"] - 1) // 2
        r0 = M + (nb - 1 - kb) * BH - 24
        pix, op = hole
        if d["side"] == "R":
            pix, op, c0 = pix[:, ::-1], op[:, ::-1], P.VIEW_W - WALL
        else:
            c0 = 0
        sl = (slice(r0, r0 + pix.shape[0]), slice(c0, c0 + WALL))
        full[sl] = np.where(op, pix, 0)
        floor[sl] = np.where(op, pix, 0)
        alpha[sl] = op
    hero = (WALL + P.FLOOR_W // 2, M + (nb - 1) * BH + BH - 40) if room in (9, 14) else None
    # fuentes extra: halo de los sprites emisivos ya colocados (posicion real, tras apartar enemigos)
    pts = []
    for s in sprites:
        base = s["piece"].partition("@")[0]
        if base == "vela" or base == "camp_n_hoguera" or base in FUENTES_DEBILES or (amb == "cera" and base == "altar"):
            h, w = s["op"].shape
            pts.append((s["x0"] + w / 2.0, s["y0"] + (6 if base == "vela" else h * 0.4), FUENTES_DEBILES.get(base, 1.0)))
    Lq, tint = light_grids(amb, room, Ht, nb, pts, hero)
    rgb_f = relight(p1.to_rgb(floor), Lq, tint)
    rgb_f = limit_palette(rgb_f, alpha)
    rgb_base = p1.to_rgb(full)
    rgb_u = relight(rgb_base, Lq, tint)                     # props sin GLB: tintados con la banda de su sitio (aproximacion)
    ref = AM[amb]["ref"]
    for s in sprites:
        base, _, tag = s["piece"].partition("@")
        h, w = s["op"].shape
        x0, y0 = s["x0"], s["y0"]
        ya, yb, xa, xb = max(0, y0), min(Ht, y0 + h), max(0, x0), min(256, x0 + w)
        sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
        reg = (slice(ya, yb), slice(xa, xb))
        op = s["op"][sub]
        fy = min(Ht - 1, max(0, int(s["ay"])))
        fx = min(255, max(0, int(s["ax"])))
        if base in EMISIVAS:
            rgb_u[reg][op] = rgb_base[reg][op]
        elif amb == "techo":
            pass                                               # luz neutra como los personajes: rgb_u ya lleva la luz de la sala
        elif base in REALES:                                   # render real: ya lleva su luz; solo se atenua con la distancia
            c = float(np.clip(Lq[fy, fx] / ref, 0.12, 1.25)) * AM[amb].get("pg", 1.0)
            rgb_u[reg][op] = np.clip(rgb_base[reg][op].astype(np.float64) * c, 0, 255).astype(np.uint8)
    plane = np.dstack([rgb_f, np.where(alpha, 255, 0).astype(np.uint8)])
    has_up = any(d["side"] == "U" for d in rd["doors"])
    pix, op = ends[1 if has_up else 0]
    Lb, tb = float(Lq[M + 2].mean()), tint[M + 2].mean(0)
    brgb = relight(p1.to_rgb(pix), np.full(pix.shape[:2], Lb), np.broadcast_to(tb, pix.shape[:2] + (3,)))
    back = np.dstack([brgb, np.where(op, 255, 0).astype(np.uint8)])
    for (piece, cx, elev) in COLGADOS.get(room, []):            # props de pared: se estampan en el muro (back), sin sombra en el suelo
        lay = akit.layout(f"{piece}@{tag_for(amb, cx, 0, nb - 1, nb, srcs)}")
        lo = lay["op"]
        rows, cols = np.where(lo)
        bh = back.shape[0]
        y0 = bh - elev - (rows.max() + 1)
        x0 = cx - (cols.min() + cols.max() + 1) // 2
        srgb = relight(p1.to_rgb(lay["pix"]), np.full(lo.shape, Lb), np.broadcast_to(tb, lo.shape + (3,)))
        hh, ww = lo.shape
        sh = np.zeros((bh, 256), bool); sh[max(0, y0 + 2):y0 + 2 + hh, max(0, x0 + 1):x0 + 1 + ww] = lo[max(0, -(y0 + 2)):bh - y0 - 2, max(0, -(x0 + 1)):256 - x0 - 1]
        back[..., :3][sh & (back[..., 3] > 0)] = (back[..., :3][sh & (back[..., 3] > 0)] * 0.72).astype(np.uint8)   # sombra pequena sobre el muro
        ys, xs = slice(max(0, y0), min(bh, y0 + hh)), slice(max(0, x0), min(256, x0 + ww))
        m = lo[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]
        back[ys, xs, :3][m] = srgb[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0][m]
        back[ys, xs, 3][m] = 255
    sky = None
    if room in (6, 7) and not has_up:
        sky = make_sky(amb == "noche", 256, 96)
    return {"plane": plane, "rgb": rgb_u, "sprites": sprites, "back": back, "Ht": Ht, "info": [], "luz": {}, "mult": None, "rep": rep,
            "v3": {"Lq": Lq, "tint": tint, "amb": amb, "pts": pts, "hero": hero}, "sky": sky, "amb_label": NOMBRE[amb]}


def make_sky(noche, w, h):
    yy = np.linspace(0, 1, h)[:, None, None]
    if noche:
        top, bot = np.array([10, 14, 28]), np.array([34, 44, 72])
    else:
        top, bot = np.array([110, 142, 180]), np.array([206, 214, 212])
    img = (top * (1 - yy) + bot * yy) * np.ones((h, w, 3))
    rng = np.random.default_rng(7)
    img = img.astype(np.uint8)
    if noche:
        for _ in range(26):
            img[rng.integers(0, h - 20), rng.integers(0, w)] = (150, 160, 190)
        cx, cy = 200, 30
        for yy_ in range(-9, 10):
            for xx_ in range(-9, 10):
                if xx_ * xx_ + yy_ * yy_ <= 64 and not ((xx_ + 4) ** 2 + (yy_ - 2) ** 2 <= 56):
                    img[cy + yy_, cx + xx_] = (206, 212, 224)
    else:
        for (cx, cy, rw) in ((60, 30, 34), (170, 52, 26)):
            for xx_ in range(-rw, rw):
                for yy_ in range(-5, 6):
                    if (xx_ / rw) ** 2 + (yy_ / 5.0) ** 2 <= 1:
                        img[cy + yy_, cx + xx_] = (226, 228, 224)
        for yy_ in range(-8, 9):
            for xx_ in range(-8, 9):
                if xx_ * xx_ + yy_ * yy_ <= 64:
                    img[24 + yy_, 214 + xx_] = (238, 224, 176)
    img = ((img >> 3) << 3)
    return np.dstack([img, np.full((h, w, 1), 255, np.uint8)])


# ------------------------------------------------------------ enemigos y heroe
def sprite_factor(b, fx, fy):
    v = b["v3"]
    Lq, tint = v["Lq"], v["tint"]
    y = int(min(max(fy - 4, 0), Lq.shape[0] - 1))
    x = int(min(max(fx, 0), 255))
    return tint[y, x] * (Lq[y, x] * GAIN)


def tint_sprite(spr, factor):
    out = spr.copy()
    f = spr[:, :, :3].astype(np.float64) / 255.0 * factor
    lum = (0.30 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2])[..., None]
    f = lum + (f - lum) * BC.SATURATION_KEEP
    out[:, :, :3] = (np.clip(f * 255.0, 0, 255).astype(np.uint8) >> 3) << 3
    return out


def shadow_dir(b, fx, fy):
    """(g, longitud) de la sombra de un personaje en (fx, fy) de imagen de sala: lado contrario a la fuente mas cercana."""
    v = b["v3"]
    spec = AM[v["amb"]]
    if v["amb"] == "techo":
        return TECHO_DIR, TECHO_LEN
    if spec["slen"] <= 0:
        return None, 0.0
    if spec["tag"] == "c":
        return spec["dir"], spec["slen"]
    pts = v["pts"]
    if not pts:
        return (0.95, 0.3), spec["slen"]
    sx, sy = min(pts, key=lambda s: (s[0] - fx) ** 2 + (2 * (s[1] - fy)) ** 2)[:2]
    dx, dy = fx - sx, (fy - sy)
    n = max(np.hypot(dx, dy), 1.0)
    dist = np.hypot(dx, 2 * dy)
    ln = float(np.clip(dist / 150.0, 0.25, 1.0)) * spec["slen"] if v["amb"] == "cera" else spec["slen"]
    return (dx / n, dy / n * 0.5 + 0.12), ln


def cast_shadow(canvas, spr, anc, fx, fy, g, ln):
    """Oscurece al 50 % (como la DS) la silueta del sprite cizallada sobre el suelo."""
    if g is None:
        return
    h, w = spr.shape[:2]
    op = spr[:, :, 3] > 0
    ys, xs = np.nonzero(op)
    hh = np.maximum(anc - ys, 0).astype(np.float64)
    X = np.round(fx + (xs - w // 2) + g[0] * hh * ln).astype(int)
    Y = np.round(fy + g[1] * hh * ln).astype(int)
    for xx_, yy_ in set(zip(X.tolist(), Y.tolist())):
        if 0 <= xx_ < canvas.width and 0 <= yy_ < canvas.height:
            r, g_, b_ = canvas.getpixel((xx_, yy_))[:3]
            canvas.putpixel((xx_, yy_), (r // 2, g_ // 2, b_ // 2, 255))
