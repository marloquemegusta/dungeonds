"""Lleva la colocacion del poster (tools/poster/salas/sala_NN.py) a la ROM del ARPG.

Lee ADD (props) y GRUPOS (enemigos) de las 16 salas y escribe:
  - source/encounters_act1_salas.h        (piezas, rects de colision y miembros de cada bloque de cada sala)
  - tools/encuentros/salas_rom_piezas.json (piezas con su posicion legal: el baker de kit deriva de ahi las fases)

Uso: python tools/encuentros/gen_salas_rom.py [--presupuesto N] [--tol PX]
Despues: python tools/bake_cathedral_kit.py --floor assets/environment/cathedral/floor/rombos_tripo --mode catedral

El kit solo hornea unas pocas fases de suelo por pieza (una estampa vale en x_tile = fase + 16 n, y_tile = fase + 16 m), asi que
cada pieza del poster se acerca a la fase legal mas cercana. Se eligen las fases (con un presupuesto de tiles) que mas piezas
del poster sirven; lo que queda lejos de toda fase elegida, tapa una puerta, un enemigo o el pasillo central, o ya no cabe, se
descarta y se cuenta en el informe.
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
import bake_cathedral_kit as B  # noqa: E402

SALAS_DIR = ROOT / "tools/poster/salas"
ROM_C = ROOT / "source/encounters_act1.c"
OUT_H = ROOT / "source/encounters_act1_salas.h"
OUT_JSON = ROOT / "tools/encuentros/salas_rom_piezas.json"
RENDER = ROOT / "assets/environment/cathedral/props/render"

# ---------------------------------------------------------------------------------------------------------------------------
# TABLA DE TRADUCCION: reposo del poster -> estado de la ROM (ENC_S_*). Es el unico sitio donde cambiarla cuando el otro agente
# programe vaiven / barrido / paseo / escondido / patrulla. PRAY = la monja de cera reza y cura; GUARD = se queda en su puesto
# hasta que el heroe se acerca o le pegan (se suelta solo); AWAKE = despierta con la sala y ataca; DORMANT = como AWAKE al despertar.
REPOSO_A_ESTADO = {
    "reza": "ENC_S_PRAY",
    "gatea": "ENC_S_AWAKE",       # el bebe gatea hacia el heroe en cuanto despierta la sala
    "quieto": "ENC_S_GUARD",
    "vaiven": "ENC_S_GUARD",      # sin vaiven todavia: de guardia en su sitio
    "patrulla": "ENC_S_AWAKE",    # sin patrulla todavia: ataca al despertar
    "pasea": "ENC_S_AWAKE",       # Cireneo paseando: sin paseo todavia, ataca al despertar
    "barre": "ENC_S_AWAKE",       # barrido del Ojo: sin barrido todavia (el Ojo ya se queda en su puesto por ser tirador)
    "escondido": "ENC_S_DORMANT",
}
# Tipo del poster -> ENC_E_* de la ROM (None = no se lleva: el jefe de la Cripta sigue siendo el de la ROM).
TIPO_A_ENC = {"bebe": "ENC_E_BEBE", "monaguillo": "ENC_E_MONAGUILLO", "monja": "ENC_E_EXVOTO", "ojo": "ENC_E_OJO",
              "cireneo": "ENC_E_CIRENEO", "parroco": "ENC_E_PARROCO", "smonja": "ENC_E_MONJA", "abanderado": None}
# ---------------------------------------------------------------------------------------------------------------------------

# pieza del poster -> id del kit (STRIP_PIECE_*). Las que no estan, no se llevan (altar: es el fixture de viaje de la ROM;
# sarcofago_lado: sin render).
PIEZA_ENUM = {
    "columna_entera": "COLUMNA_ENTERA", "banco_entero": "BANCO_ENTERO", "relicario": "RELICARIO", "vela": "VELA",
    "santo": "SANTO", "santo_der": "SANTO_DER", "sacos": "SACOS", "sacos_b": "SACOS_B", "sacos_remate": "SACOS_REMATE",
    "sacos_remate_der": "SACOS_REMATE_DER", "alambre": "ALAMBRE", "columna": "COLUMNA_ROTA",
    "banco_roto": "BANCO_ROTO", "banco_volcado": "BANCO_VOLCADO", "capullo": "CAPULLO", "cepo": "CEPO",
    "lapida_pie": "LAPIDA_PIE", "candelabro_pie": "CANDELABRO_PIE", "calaveras_pila": "CALAVERAS_PILA",
    "huesos_monton": "HUESOS_MONTON", "reclinatorio": "RECLINATORIO", "catre": "CATRE", "biombo": "BIOMBO",
    "palangana": "PALANGANA", "osario_estante": "OSARIO_ESTANTE", "osario_lado": "OSARIO_LADO", "sarcofago": "SARCOFAGO",
    "brasero": "BRASERO",
}
ESPEJO = {"santo": "santo_der", "santo_der": "santo", "sacos_remate": "sacos_remate_der", "sacos_remate_der": "sacos_remate"}
DECOR = {"sacos": "ENC_R_SACOS", "sacos_b": "ENC_R_SACOS", "sacos_remate": "ENC_R_SACOS", "sacos_remate_der": "ENC_R_SACOS",
         "alambre": "ENC_R_ALAMBRE"}
PESO_BAJO = {"banco_entero": 0.5, "banco_roto": 0.5, "banco_volcado": 0.5}
FLOOR_X, FLOOR_W, BLOCK_H = 152, 208, 384
X0_T, X1_T, BLOCK_T = 19, 45, 48          # tiles de suelo util y alto del bloque
MAX_POR_BLOQUE = 16
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


def layout(name):
    if name not in _LAY:
        lay = B.piece_layout(name)
        col = np.asarray(Image.open(RENDER / name / "color.png").convert("RGBA"))
        op = col[:, :, 3] >= 128
        ys, xs = np.nonzero(op)
        lay["bx0"], lay["bx1"], lay["by1"] = int(xs.min()), int(xs.max()) + 1, int(ys.max()) + 1
        lay["cw"], lay["ch"] = col.shape[1], col.shape[0]      # color.png (el lienzo del baker puede ser mayor por la sombra)
        _LAY[name] = lay
    return _LAY[name]


def poster_composicion(rd, add, groups):
    """Replica pieces_for_block del poster: desplaza o quita lo que choca con enemigos, puertas, cofre, altar y otras piezas.
    Devuelve [(pieza, k, x, y)] con x,y = esquina del color.png, en px locales del bloque."""
    res = reserved(rd)
    out = []
    for k in range(rd["blocks"]):
        ens = [(m[1], m[2]) for g in groups if g["k"] == k for m in g["miembros"]]
        rk = [r[1:] for r in res if r[0] == k]
        taken = []
        for (piece, kk, x0, y0) in add:
            if kk != k:
                continue
            lay = layout(piece)
            h = lay["ch"]
            base = 14 if piece != "vela" else h
            for dx, dy in SHIFTS:
                x, y = x0 + dx, y0 + dy
                if x + lay["bx0"] < 0 or x + lay["bx1"] > FLOOR_W or y < 0 or y + h > BLOCK_H:
                    continue
                rect = (x + lay["bx0"], y + lay["by1"] - base, x + lay["bx1"], y + lay["by1"])
                if any(hit(rect, r) for r in rk) or any(hit(rect, (ex - 13, ey - 10, ex + 13, ey + 6)) for ex, ey in ens):
                    continue
                if any(hit(rect, t) for t in taken):
                    continue
                taken.append(rect)
                out.append((piece, k, x, y))
                break
    return out


def legal_pos(piece, cx, cy, pc, pr):
    """(error^2, x_tile, y_tile) de la estampa (lienzo) de `piece` en la fase (pc, pr) mas cercana a (cx, cy) px locales."""
    lay = layout(piece)
    wt, ht = lay["w"] // 8, lay["h"] // 8
    best = None
    for xt in range(X0_T, X1_T - wt + 1):
        if (xt - pc) % 16:
            continue
        for yt in range(0, BLOCK_T - ht + 1):
            if (yt - pr) % 16:
                continue
            e = (xt * 8 - FLOOR_X - cx) ** 2 + (yt * 8 - cy) ** 2
            if best is None or e < best[0]:
                best = (e, xt, yt)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--presupuesto", type=int, default=520, help="tiles de kit para las fases de las piezas")
    ap.add_argument("--tol", type=int, default=24, help="distancia maxima (px) a la fase legal mas cercana")
    a = ap.parse_args()
    rooms = parse_rooms()
    assert len(rooms) == 16, len(rooms)

    # 1. composicion del poster por sala
    comp, grupos = {}, {}
    informe = defaultdict(lambda: defaultdict(int))
    for n in range(16):
        m = load_sala(n)
        rd = rooms[n]
        grupos[n] = list(m.GRUPOS)
        add = []
        for (p, k, x, y) in list(m.ADD) + list(getattr(m, "EXTRA", [])):
            mir = p.endswith("~")
            p = p.rstrip("~")
            if mir and p in ESPEJO:
                p = ESPEJO[p]
            if p not in PIEZA_ENUM:
                informe[n]["sin_pieza:" + p] += 1
                continue
            add.append((p, k, x, y))
        comp[n] = poster_composicion(rd, add, grupos[n])
        informe[n]["poster"] = len(add)
        informe[n]["tras_poster"] = len(comp[n])
        if rd["crypt"]:
            informe[n]["cripta_sin_props"] = len(comp[n])
            comp[n] = []

    # 2. fases: greedy por (pieza, fase) con presupuesto de tiles
    place = []
    for n in comp:
        for (p, k, x, y) in comp[n]:
            lay = layout(p)
            place.append((n, k, p, x - lay["ox"], y - lay["oy"]))          # esquina del lienzo
    cand = defaultdict(lambda: defaultdict(list))        # pieza -> fase -> idx de place servidos
    for i, (n, k, p, cx, cy) in enumerate(place):
        for pc in range(16):
            for pr in range(16):
                b = legal_pos(p, cx, cy, pc, pr)
                if b and b[0] ** 0.5 <= a.tol:
                    cand[p][(pc, pr)].append(i)
    elegidas = defaultdict(list)
    servido = set()
    gastado = 0
    while True:
        best = None
        for p, fases in cand.items():
            coste = (layout(p)["w"] // 8) * (layout(p)["h"] // 8)
            for ph, idxs in fases.items():
                if ph in elegidas[p]:
                    continue
                g = sum(peso(place[i][2]) for i in idxs if i not in servido)
                if g <= 0 or gastado + coste > a.presupuesto:
                    continue
                s = g / coste
                if best is None or s > best[0]:
                    best = (s, p, ph, coste)
        if best is None:
            break
        _, p, ph, coste = best
        elegidas[p].append(ph)
        gastado += coste
        servido |= set(cand[p][ph])

    # 3. posicion final por pieza: la fase elegida mas cercana; sin solapes ni enemigos ni puertas
    final = defaultdict(list)       # (n, k) -> [(pieza, lx, ly)]
    for n in comp:
        rd = rooms[n]
        res = reserved(rd)
        ocupado = defaultdict(list)
        ordenadas = sorted(((i, pl) for i, pl in enumerate(place) if pl[0] == n), key=lambda t: (-peso(t[1][2]), t[0]))
        for i, (_, k, p, cx, cy) in ordenadas:
            lay = layout(p)
            mejor = None
            for ph in elegidas.get(p, []):
                b = legal_pos(p, cx, cy, *ph)
                if b and (mejor is None or b[0] < mejor[0]):
                    mejor = b
            if not mejor or mejor[0] ** 0.5 > a.tol:
                informe[n]["lejos_de_fase:" + p] += 1
                continue
            _, xt, yt = mejor
            wt, ht = lay["w"] // 8, lay["h"] // 8
            box = (xt, yt, xt + wt, yt + ht)
            lx, ly = xt * 8 - FLOOR_X, yt * 8
            col_x, col_y = lx + lay["ox"], ly + lay["oy"]
            rect = (col_x + lay["bx0"], col_y + lay["by1"] - 14, col_x + lay["bx1"], col_y + lay["by1"])
            ens = [(m[1], m[2]) for g in grupos[n] if g["k"] == k for m in g["miembros"]]
            if any(hit(rect, r[1:]) for r in res if r[0] == k) or any(hit(rect, (ex - 13, ey - 10, ex + 13, ey + 6)) for ex, ey in ens):
                informe[n]["tapa_puerta_o_enemigo:" + p] += 1
                continue
            if any(hit(box, o) for o in ocupado[k]):
                informe[n]["solapa:" + p] += 1
                continue
            if len(final[(n, k)]) >= MAX_POR_BLOQUE:
                informe[n]["tope_bloque:" + p] += 1
                continue
            # pasillo central: una pieza con colision que cruce el eje (+-16 px) no se coloca (stamp_blocks_aisle)
            if lay["value"] != 0 and lay["foot_runs"]:
                lo = min(lx + x * 4 for x, y, c in lay["foot_runs"])
                hi = max(lx + (x + c) * 4 for x, y, c in lay["foot_runs"])
                if hi > FLOOR_W // 2 - 16 and lo < FLOOR_W // 2 + 16:
                    informe[n]["cruza_pasillo:" + p] += 1
                    continue
            ocupado[k].append(box)
            final[(n, k)].append((p, lx, ly))
        informe[n]["colocadas"] = sum(len(v) for (nn, _), v in final.items() if nn == n)

    # 4. escritura
    piezas_json = []
    L = ["// Generado por tools/encuentros/gen_salas_rom.py desde tools/poster/salas/sala_NN.py. No editar a mano.",
         "// Colocacion del poster por sala y bloque: piezas (ya en posicion legal del kit), rects de colision de sacos / alambre",
         "// y miembros de cada grupo. Se incluye desde encounters_act1.c tras encounters_act1_tables.h.", "",
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
        for k in range(rd["blocks"]):
            if rd["crypt"]:
                continue
            ps = sorted(final[(n, k)], key=lambda t: (t[2], t[1]))
            rects = []
            for (p, lx, ly) in ps:
                piezas_json.append({"piece": p, "lx": lx, "ly": ly})
                if p in DECOR:
                    fr = layout(p)["foot_runs"]
                    x0 = min(x for x, y, c in fr) * 4
                    x1 = max(x + c for x, y, c in fr) * 4
                    y0 = min(y for x, y, c in fr) * 4
                    y1 = (max(y for x, y, c in fr) + 1) * 4
                    rects.append((DECOR[p], lx + x0, ly + y0, x1 - x0, y1 - y0))
            mem = []
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
                for (p, lx, ly) in ps:
                    L.append("    { STRIP_PIECE_%s, %d, %d }," % (PIEZA_ENUM[p], lx, ly))
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
    OUT_JSON.write_text(json.dumps({"piezas": piezas_json, "fases": {p: v for p, v in elegidas.items()}}, indent=1),
                        encoding="utf-8", newline="\n")

    print("fases elegidas (%d tiles de %d):" % (gastado, a.presupuesto))
    for p, v in sorted(elegidas.items()):
        print("  %-16s %s" % (p, v))
    for n in range(16):
        print("sala %02d" % n, dict(informe[n]))
    print("miembros llevados:", miembros_total, "piezas:", len(piezas_json))


if __name__ == "__main__":
    main()
