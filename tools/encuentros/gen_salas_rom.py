"""Lleva la colocacion del poster (tools/poster/salas/sala_NN.py) a la ROM del ARPG.

Lee ADD (props) y GRUPOS (enemigos) de las 16 salas y escribe:
  - source/encounters_act1_salas.h        (piezas, rects de colision y miembros de cada bloque de cada sala)
  - tools/encuentros/salas_rom_piezas.json (piezas de cada sala con su posicion exacta; el baker de kit hornea de ahi un
                                            archivo por sala, nitrofiles/rooms/sala_NN.rmk, con las estampas en esa fase)

Uso: python tools/encuentros/gen_salas_rom.py
Despues: python tools/bake_cathedral_kit.py --floor assets/environment/cathedral/floor/rombos_tripo --mode catedral

Cada pieza del poster se coloca con su esquina de lienzo en el tile mas cercano (la estampa se hornea en la fase de suelo de ese
tile, asi que no hay aproximacion de fase). Solo se descarta lo que la ROM no admite: pieza que tapa una puerta, un enemigo, el
cofre o el altar, que cruza el pasillo central, que solapa los tiles de otra o que no tiene render. Lo descartado se cuenta.
"""
import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "poster"))
import bake_cathedral_kit as B  # noqa: E402
import gen_ambientes_arpg as GA  # noqa: E402

SALAS_DIR = ROOT / "tools/poster/salas"
ROM_C = ROOT / "source/encounters_act1.c"
OUT_H = ROOT / "source/encounters_act1_salas.h"
OUT_JSON = ROOT / "tools/encuentros/salas_rom_piezas.json"
RENDER = ROOT / "assets/environment/cathedral/props/render"

# ---------------------------------------------------------------------------------------------------------------------------
# TABLA DE TRADUCCION: reposo del poster -> estado de la ROM (ENC_S_*). PRAY = la monja de cera reza y cura; GUARD = de guardia
# en su puesto; los demas son los reposos de feat/arpg-reposos (rest_assign): el grupo nace dormido y despierta por radio o golpe.
REPOSO_A_ESTADO = {
    "reza": "ENC_S_PRAY",
    "quieto": "ENC_S_GUARD",
    "gatea": "ENC_S_CRAWL",
    "vaiven": "ENC_S_SWAY",
    "barre": "ENC_S_SWEEP",
    "pasea": "ENC_S_STROLL",
    "escondido": "ENC_S_HIDDEN",
    "patrulla": "ENC_S_PATROL",
}
# Tipo del poster -> ENC_E_* de la ROM (None = no se lleva: el jefe de la Cripta sigue siendo el de la ROM).
TIPO_A_ENC = {"bebe": "ENC_E_BEBE", "monaguillo": "ENC_E_MONAGUILLO", "monja": "ENC_E_EXVOTO", "ojo": "ENC_E_OJO",
              "cireneo": "ENC_E_CIRENEO", "parroco": "ENC_E_PARROCO", "smonja": "ENC_E_MONJA", "abanderado": None}
# ---------------------------------------------------------------------------------------------------------------------------

# pieza del poster -> id del kit (STRIP_PIECE_*). Las que no estan, no se llevan (altar: es el fixture de viaje de la ROM;
# nada mas: todas las piezas de las 16 salas ya tienen render).
PIEZA_ENUM = {
    "columna_entera": "COLUMNA_ENTERA", "banco_entero": "BANCO_ENTERO", "relicario": "RELICARIO", "vela": "VELA",
    "santo": "SANTO", "santo_der": "SANTO_DER", "sacos": "SACOS", "sacos_b": "SACOS_B", "sacos_remate": "SACOS_REMATE",
    "sacos_remate_der": "SACOS_REMATE_DER", "alambre": "ALAMBRE", "columna": "COLUMNA_ROTA",
    "banco_roto": "BANCO_ROTO", "banco_volcado": "BANCO_VOLCADO", "capullo": "CAPULLO", "cepo": "CEPO",
    "lapida_pie": "LAPIDA_PIE", "candelabro_pie": "CANDELABRO_PIE", "calaveras_pila": "CALAVERAS_PILA",
    "huesos_monton": "HUESOS_MONTON", "reclinatorio": "RECLINATORIO", "catre": "CATRE", "biombo": "BIOMBO",
    "palangana": "PALANGANA", "osario_estante": "OSARIO_ESTANTE", "osario_lado": "OSARIO_LADO", "sarcofago": "SARCOFAGO",
    "brasero": "BRASERO", "sarcofago_lado": "SARCOFAGO_LADO", "altar_pie": "ALTAR_PIE",
}
ESPEJO = {"santo": "santo_der", "santo_der": "santo", "sacos_remate": "sacos_remate_der", "sacos_remate_der": "sacos_remate"}
DECOR = {"sacos": "ENC_R_SACOS", "sacos_b": "ENC_R_SACOS", "sacos_remate": "ENC_R_SACOS", "sacos_remate_der": "ENC_R_SACOS",
         "alambre": "ENC_R_ALAMBRE"}
# el altar del poster (decorado de pie) no es el altar de viaje de la ROM (fixture): su estampa se llama altar_pie
PIEZA_ALIAS = {"altar": "altar_pie"}


def _salas_con_puerta_arriba():
    """Ids de las salas con una puerta DU(...) en la tabla s_rooms de encounters_act1.c (el pasillo central solo rige en ellas)."""
    src = (ROOT / "source" / "encounters_act1.c").read_text(encoding="utf-8")
    tabla = src.split("static const RoomDef s_rooms[ENC_ROOM_COUNT] = {", 1)[1].split("\n};", 1)[0]
    fichas = tabla.split("{ .name =")[1:]
    return {i for i, f in enumerate(fichas) if "DU(" in f}


SALAS_CON_PUERTA_ARRIBA = _salas_con_puerta_arriba()
PESO_BAJO = {"banco_entero": 0.5, "banco_roto": 0.5, "banco_volcado": 0.5}
FLOOR_X, FLOOR_W, BLOCK_H = 152, 208, 384
X0_T, X1_T, BLOCK_T = 19, 45, 48          # tiles de suelo util y alto del bloque
MAX_POR_BLOQUE = 40
DEBUG = "--debug" in sys.argv
SHIFTS = [(0, 0)] + [(dx, dy) for dx in (-8, 8, -16, 16, -24, 24, -32, 32, -48, 48) for dy in (0, -8, 8, -16, 16)]


def peso(p):
    return PESO_BAJO.get(p, 3)


def load_sala(n):
    f = SALAS_DIR / f"sala_{n:02d}.py"
    sp = importlib.util.spec_from_file_location(f"salas_rom_{n:02d}", f)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def parse_rooms():
    """[dict(blocks, altar, chest, doors, crypt, gate)] de s_rooms[] de la ROM."""
    s = ROM_C.read_text(encoding="utf-8")
    body = s.split("s_rooms[ENC_ROOM_COUNT] = {", 1)[1].split("\n};", 1)[0]
    rooms = []
    for e in re.split(r"\n    \{ \.name", body)[1:]:
        blocks = int(re.search(r"\.blocks = (\d+)", e).group(1))
        doors = [("L", int(a)) for a, _ in re.findall(r"DL\((\d+), (\d+)\)", e)] + \
                [("R", int(a)) for a, _ in re.findall(r"DR\((\d+), (\d+)\)", e)]
        rooms.append(dict(blocks=blocks, altar=".altar = 1" in e, chest=".chest = 1" in e, doors=doors,
                          crypt="RT_CRIPTA" in e, gate="chapel_gate = 1" in e))
    return rooms


def reserved(rd):
    out = []
    if rd["altar"]:
        out.append((0, 28, 262, 72, 330))
    if rd["chest"]:
        out.append((rd["blocks"] - 1, 72, 44, 136, 100))
    for side, screen in rd["doors"]:
        kb = (screen - 1) // 2
        out.append((kb, 0, 206, 52, 244) if side == "L" else (kb, FLOOR_W - 52, 206, FLOOR_W, 244))
        # paso de la puerta lateral: el hueco del muro ocupa y 96..352 del bloque
        out.append((kb, 0, 96, 12, 352) if side == "L" else (kb, FLOOR_W - 12, 96, FLOOR_W, 352))
    return out


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


_LAY = {}


def layout(name, mirror=0):
    """Geometria de la estampa de sala (la misma que hornea el baker: espejo y recorte): mascara de tiles ocupados, bbox opaca
    y huella en su lienzo, y `ox`, `oy` = donde queda la esquina del color.png respecto de la esquina del lienzo."""
    key = (name, mirror)
    if key not in _LAY:
        lay = B.room_layout(name, mirror)
        W, H = lay["w"], lay["h"]
        op = lay["rgba"][:, :, 3] >= 128
        occ = op | (lay["shadow"] if lay["shadow"] is not None else False)
        ys, xs = np.nonzero(op)
        mask = occ.reshape(H // 8, 8, W // 8, 8).any(axis=(1, 3))
        for x, y, n in lay["foot_runs"]:
            mask[y // 2, x // 2:(x + n - 1) // 2 + 1] = True
        for x, y, n, _ in lay["depth_runs"]:
            mask[y // 8, x // 8:(x + n - 1) // 8 + 1] = True
        ch = H + lay["ty0"] * 8 - lay["oy"] if name in B.COMPOSITE_NAMES else Image.open(RENDER / name / "color.png").size[1]
        _LAY[key] = {"w": W, "h": H, "ox": lay["ox"], "oy": lay["oy"], "ch": ch, "bx0": int(xs.min()), "bx1": int(xs.max()) + 1,
                     "by1": int(ys.max()) + 1, "mask": mask, "foot_runs": list(lay["foot_runs"]), "value": lay["value"]}
    return _LAY[key]


def poster_composicion(rd, add, groups, sobre_pasos=(), sala=-1):
    """Replica pieces_for_block del poster: desplaza o quita lo que choca con enemigos, puertas, cofre, altar y otras piezas.
    add = [(pieza, espejo, k, x, y)] con x, y = esquina del color.png. Devuelve [(pieza, espejo, k, cx, cy)] con (cx, cy) la
    esquina del LIENZO de la estampa, en px locales del bloque."""
    res = reserved(rd)
    out = []
    for k in range(rd["blocks"]):
        ens = [(m[1], m[2]) for g in groups if g["k"] == k for m in g["miembros"]]
        rk = [r[1:] for r in res if r[0] == k]
        taken = []
        for (piece, mir, kk, x0, y0) in add:
            if kk != k:
                continue
            lay = layout(piece, mir)
            h = lay["ch"]
            base = 14 if piece != "vela" else h
            for dx, dy in SHIFTS:
                x, y = x0 + dx, y0 + dy
                cx, cy = x - lay["ox"], y - lay["oy"]
                if cx + lay["bx0"] < 0 or cx + lay["bx1"] > FLOOR_W or y < 0 or y + h > BLOCK_H:
                    continue
                rect = (cx + lay["bx0"], cy + lay["by1"] - base, cx + lay["bx1"], cy + lay["by1"])
                libre = (sala, piece, mir, k) in sobre_pasos
                if (not libre and any(hit(rect, r) for r in rk)) or any(hit(rect, (ex - 13, ey - 10, ex + 13, ey + 6)) for ex, ey in ens):
                    continue
                if any(hit(rect, t) for t in taken):
                    continue
                taken.append(rect)
                out.append((piece, mir, k, cx, cy))
                break
    return out


# tiles de desplazamiento a probar alrededor del tile mas cercano al lienzo del poster (de menos a mas)
SNAP = sorted(((dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)), key=lambda d: (d[0] ** 2 + d[1] ** 2, abs(d[0]), d[1]))


def main():
    rooms = parse_rooms()
    assert len(rooms) == 16, len(rooms)
    V2 = {n: s["comp"] for n, s in GA.build().items()}

    sobre_pasos = set()       # (sala, pieza, espejo, k) de las EXTRA: pueden ir sobre los pasos reservados (el cofre)
    comp, grupos = {}, {}
    informe = defaultdict(lambda: defaultdict(int))
    for n in range(16):
        m = load_sala(n)
        rd = rooms[n]
        grupos[n] = list(m.GRUPOS)
        add = []
        # lo que la composicion v2 deja sin quitar (DROP) tambien es poster: sala 10, relicarios del fondo
        drop = set(getattr(m, "DROP", []))
        v2 = [(i["piece"], i["k"], i["x"], i["y"]) for i in V2[n] if i["piece"] not in drop and i["piece"] != "altar"]
        extra = set((PIEZA_ALIAS.get(p.rstrip("~"), p.rstrip("~")), int(p.endswith("~")), k, x, y)
                    for (p, k, x, y) in getattr(m, "EXTRA", []))
        for (p, k, x, y) in list(m.ADD) + list(getattr(m, "EXTRA", [])) + v2:
            mir = int(p.endswith("~"))
            p = p.rstrip("~")
            p = PIEZA_ALIAS.get(p, p)
            if mir and p in ESPEJO:                       # el kit ya trae su pareja (santo_der...): no hace falta estampa en espejo
                p, mir = ESPEJO[p], 0
            if p not in PIEZA_ENUM:
                informe[n]["sin_pieza_en_la_ROM:" + p] += 1
                continue
            if not B.has_art(p):
                informe[n]["sin_render:" + p] += 1
                continue
            add.append((p, mir, k, x, y))
            if (p, mir, k, x, y) in extra:
                sobre_pasos.add((n, p, mir, k))
        comp[n] = poster_composicion(rd, add, grupos[n], sobre_pasos, n)
        informe[n]["poster"] = len(add)
        informe[n]["tras_poster"] = len(comp[n])

    # posicion exacta por pieza: el tile mas cercano que cumple las reglas de la ROM
    final = defaultdict(list)       # (n, k) -> [(pieza, espejo, lx, ly)]
    for n in range(16):
        rd = rooms[n]
        res = reserved(rd)
        ocupado = defaultdict(set)                      # k -> tiles (x, y) con pixeles de pieza
        ordenadas = sorted(enumerate(comp[n]), key=lambda t: (-peso(t[1][0]), t[0]))
        for _, (p, mir, k, cx, cy) in ordenadas:
            lay = layout(p, mir)
            wt, ht = lay["w"] // 8, lay["h"] // 8
            tiles = [(x, y) for y in range(ht) for x in range(wt) if lay["mask"][y, x]]
            ens = [(m[1], m[2]) for g in grupos[n] if g["k"] == k for m in g["miembros"]]
            base = 14 if p != "vela" else lay["ch"]
            motivo, puesto = "", None
            for dx, dy in SNAP:
                xt, yt = (cx + FLOOR_X + 4) // 8 + dx, (cy + 4) // 8 + dy
                if xt < X0_T or xt + wt > X1_T or yt < 0 or yt + ht > BLOCK_T:
                    motivo = motivo or "fuera_del_suelo"
                    continue
                lx, ly = xt * 8 - FLOOR_X, yt * 8
                rect = (lx + lay["bx0"], ly + lay["by1"] - base, lx + lay["bx1"], ly + lay["by1"])
                if ((n, p, mir, k) not in sobre_pasos and any(hit(rect, r[1:]) for r in res if r[0] == k)) or \
                        any(hit(rect, (ex - 13, ey - 10, ex + 13, ey + 6)) for ex, ey in ens):
                    motivo = motivo or "tapa_puerta_o_enemigo"
                    continue
                if any((xt + x, yt + y) in ocupado[k] for x, y in tiles):
                    motivo = motivo or "solapa"
                    continue
                if lay["value"] != 0 and lay["foot_runs"] and n in SALAS_CON_PUERTA_ARRIBA:       # pasillo central (stamp_blocks_aisle): solo en las salas con salida hacia arriba
                    lo = min(lx + x * 4 for x, y, c in lay["foot_runs"])
                    hi = max(lx + (x + c) * 4 for x, y, c in lay["foot_runs"])
                    if hi > FLOOR_W // 2 - 16 and lo < FLOOR_W // 2 + 16:
                        motivo = motivo or "cruza_pasillo"
                        continue
                if len(final[(n, k)]) >= MAX_POR_BLOQUE:
                    motivo = "tope_bloque"
                    break
                puesto = (xt, yt, lx, ly)
                break
            if puesto is None:
                informe[n][motivo + ":" + p] += 1
                if DEBUG: print("  descartada", n, k, p, mir, motivo, "lienzo", cx, cy)
                continue
            xt, yt, lx, ly = puesto
            ocupado[k] |= {(xt + x, yt + y) for x, y in tiles}
            final[(n, k)].append((p, mir, lx, ly))
        informe[n]["colocadas"] = sum(len(v) for (nn, _), v in final.items() if nn == n)

    # escritura
    salas_json = {}
    L = ["// Generado por tools/encuentros/gen_salas_rom.py desde tools/poster/salas/sala_NN.py. No editar a mano.",
         "// Colocacion del poster por sala y bloque: piezas (en el tile exacto; sus estampas van en nitrofiles/rooms/sala_NN.rmk),",
         "// rects de colision de sacos / alambre y miembros de cada grupo. Se incluye desde encounters_act1.c tras encounters_act1_tables.h.", "",
         "typedef struct { uint8_t type, state; int16_t x, y; } RoomMember;     // ENC_E_*, ENC_S_*; x, y = pies, locales al bloque",
         "typedef struct {",
         "    const EncPieceDef *pieces; uint8_t n_pieces;",
         "    const EncRectDef *rects; uint8_t n_rects;",
         "    const RoomMember *members; uint8_t n_members;",
         "} RoomLayout;", ""]
    celdas = {}
    miembros_total = 0
    for n in range(16):
        rd = rooms[n]
        lista = []
        for k in range(rd["blocks"]):
            ps = sorted(final[(n, k)], key=lambda t: (t[0], t[1], t[3], t[2]))
            rects = []
            for (p, mir, lx, ly) in ps:
                lista.append({"piece": p, "k": k, "lx": lx, "ly": ly, "mirror": mir})
                if p in DECOR:
                    fr = layout(p, mir)["foot_runs"]
                    x0 = min(x for x, y, c in fr) * 4
                    x1 = max(x + c for x, y, c in fr) * 4
                    y0 = min(y for x, y, c in fr) * 4
                    y1 = (max(y for x, y, c in fr) + 1) * 4
                    rects.append((DECOR[p], lx + x0, ly + y0, x1 - x0, y1 - y0))
            mem = []
            if not rd["crypt"]:                         # la cripta: el jefe y su escolta salen de la definicion del jefe
                for g in grupos[n]:
                    if g["k"] != k:
                        continue
                    for (tipo, x, y, rep) in g["miembros"]:
                        enc = TIPO_A_ENC[tipo]
                        if enc is None:
                            continue
                        mem.append((enc, REPOSO_A_ESTADO[rep], x, y))
            tag = "s_r%02d_b%d" % (n, k)
            if ps:
                L.append("static const EncPieceDef %s_p[] = {" % tag)
                for (p, mir, lx, ly) in ps:
                    L.append("    { STRIP_PIECE_%s%s, %d, %d }," % (PIEZA_ENUM[p], " | STRIP_PIECE_MIRROR" if mir else "", lx, ly))
                L.append("};")
            if rects:
                L.append("static const EncRectDef %s_r[] = {" % tag)
                for r in rects:
                    L.append("    { %s, %d, %d, %d, %d }," % r)
                L.append("};")
            if mem:
                L.append("static const RoomMember %s_m[] = {" % tag)
                for m in mem:
                    L.append("    { %s, %s, %d, %d }," % m)
                L.append("};")
            miembros_total += len(mem)
            celdas[(n, k)] = (bool(ps), bool(rects), bool(mem))
        salas_json[str(n)] = lista
    L.append("")
    L.append("#define ENC_ARR_OR_0(a) (a), (uint8_t)(sizeof(a) / sizeof((a)[0]))")
    L.append("// [sala][bloque]: valid = 1 cuando el poster manda en ese bloque (piezas y rects aunque esten vacios; miembros si los hay)")
    L.append("static const struct { uint8_t valid; RoomLayout l; } s_room_layouts[ENC_ROOM_COUNT][ENC_STAGES] = {")
    for n in range(16):
        L.append("    { // sala %d" % n)
        for k in range(3):
            if (n, k) not in celdas:
                L.append("        { 0 },")
                continue
            hp, hr, hm = celdas[(n, k)]
            tag = "s_r%02d_b%d" % (n, k)
            L.append("        { 1, { %s, %s, %s } }," % ("ENC_ARR_OR_0(%s_p)" % tag if hp else "0, 0",
                                                      "ENC_ARR_OR_0(%s_r)" % tag if hr else "0, 0",
                                                      "ENC_ARR_OR_0(%s_m)" % tag if hm else "0, 0"))
        L.append("    },")
    L.append("};")
    L.append("")
    OUT_H.write_text("\n".join(L), encoding="utf-8", newline="\n")
    OUT_JSON.write_text(json.dumps({"salas": salas_json}, indent=1), encoding="utf-8", newline="\n")

    for n in range(16):
        print("sala %02d" % n, dict(informe[n]))
    por_bloque = max(len(v) for v in final.values())
    print("miembros llevados:", miembros_total, "piezas:", sum(len(v) for v in salas_json.values()), "max por bloque:", por_bloque)


if __name__ == "__main__":
    main()
