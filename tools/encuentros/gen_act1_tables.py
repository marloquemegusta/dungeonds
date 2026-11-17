"""Genera source/encounters_act1_tables.h desde tools/encuentros/acto1_v2.json (DESIGN.md 6.13.6).

Uso: python tools/encuentros/gen_act1_tables.py
Los datos de diseno viven en el JSON; el C solo lleva la tabla compilada.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tools/encuentros/acto1_v2.json"
OUT = ROOT / "source/encounters_act1_tables.h"
OUT_HP = ROOT / "include/encounters_act1_hp.h"

PIECES = {"columna_entera": "STRIP_PIECE_COLUMNA_ENTERA", "relicario": "STRIP_PIECE_RELICARIO",
          "vela": "STRIP_PIECE_VELA", "banco_grupo4": "STRIP_PIECE_BANCO_GRUPO4",
          "santo": "STRIP_PIECE_SANTO"}
ENEMIES = {"exvoto": "ENC_E_EXVOTO", "cireneo": "ENC_E_CIRENEO", "ojo": "ENC_E_OJO",
           "abanderado": "ENC_E_ABANDERADO", "monaguillo": "ENC_E_MONAGUILLO"}
STATES = {"pray": "ENC_S_PRAY", "dormant": "ENC_S_DORMANT", "awake": "ENC_S_AWAKE"}
KINDS = {"sacos": "ENC_R_SACOS", "alambre": "ENC_R_ALAMBRE"}
TIERS = ["ligera", "media", "dura"]


def enemy_rows(rows, wave=False):
    out = []
    for r in rows:
        state = "ENC_S_AWAKE" if wave else STATES[r[3]]
        out.append("    { %s, %s, %d, %d }," % (ENEMIES[r[0]], state, r[1], r[2]))
    return out


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    L = ["// Generado por tools/encuentros/gen_act1_tables.py desde tools/encuentros/acto1_v2.json. No editar a mano.", ""]
    plant_names = list(d["plantas"])
    for pi, name in enumerate(plant_names):
        p = d["plantas"][name]
        L.append("static const EncPieceDef s_p%d_pieces[] = {  // %s" % (pi, name))
        for pc in p["pieces"]:
            L.append("    { %s, %d, %d }," % (PIECES[pc["piece"]], pc["x"], pc["y"]))
        L.append("};")
        if p["obstacles"]:
            L.append("static const EncRectDef s_p%d_rects[] = {" % pi)
            for o in p["obstacles"]:
                L.append("    { %s, %d, %d, %d, %d }," % (KINDS[o["kind"]], o["x"], o["y"], o["w"], o["h"]))
            L.append("};")
        for ti, tier in enumerate(TIERS):
            pop = p[tier]
            L.append("static const EncEnemyDef s_p%d_t%d[] = {" % (pi, ti))
            L += enemy_rows(pop["enemies"])
            L.append("};")
            if pop.get("wave2"):
                L.append("static const EncEnemyDef s_p%d_t%d_w2[] = {" % (pi, ti))
                L += enemy_rows(pop["wave2"], wave=True)
                L.append("};")
    L.append("")
    L.append("#define ENC_ARR(a) (a), (uint8_t)(sizeof(a) / sizeof((a)[0]))")
    L.append("static const EncPlant s_plants[ENC_PLANT_COUNT] = {")
    for pi, name in enumerate(plant_names):
        p = d["plantas"][name]
        rects = "ENC_ARR(s_p%d_rects)" % pi if p["obstacles"] else "0, 0"
        L.append("    { // %s" % name)
        L.append("        ENC_ARR(s_p%d_pieces), %s," % (pi, rects))
        L.append("        {")
        for ti, tier in enumerate(TIERS):
            pop = p[tier]
            w2 = "ENC_ARR(s_p%d_t%d_w2)" % (pi, ti) if pop.get("wave2") else "0, 0"
            L.append("            { ENC_ARR(s_p%d_t%d), %s }," % (pi, ti, w2))
        L.append("        },")
        L.append("    },")
    L.append("};")
    L.append("")
    L.append("static const EncPieceDef s_corridor_pieces[] = {")
    for pc in d["pasillo"]["pieces"]:
        L.append("    { %s, %d, %d }," % (PIECES[pc["piece"]], pc["x"], pc["y"]))
    L.append("};")
    rt = d["pasillo"]["relic_target"]
    L.append("#define ENC_RELIC_HP %d" % rt["hp"])
    L.append("static const EncEnemyDef s_boss_enemies[] = {")
    L += enemy_rows(d["boss"]["enemies"])
    L.append("};")
    L.append("static const uint8_t s_tier_of[ENC_COUNT] = { %s };" % ", ".join(
        str(TIERS.index(t)) for t in d["act"]["tiers"]))
    L.append("#define ENC_GOLDEN_AFTER %d" % d["act"]["golden_relic_after"])
    L.append("#define ENC_HEAL_EVERY %d" % d["act"]["heal_every"])
    L.append("#define ENC_START_CLEAR_BLOCKS %d" % d["act"]["start_clear_blocks"])
    L.append("")
    OUT.write_text("\n".join(L), encoding="utf-8", newline="\n")
    hp = d["hp"]
    H = ["// Generado por tools/encuentros/gen_act1_tables.py desde tools/encuentros/acto1_v2.json. No editar a mano.",
         "#ifndef ENCOUNTERS_ACT1_HP_H", "#define ENCOUNTERS_ACT1_HP_H",
         "// Vidas del acto I por encuentros (variante `encuentros`): con el rayo base (150) el Exvoto cae en 2 disparos,",
         "// el Ojo y el Cireneo en 3, el Abanderado en 20."]
    for key, name in (("exvoto", "EXVOTO"), ("monaguillo", "MONAGUILLO"), ("cireneo", "CIRENEO"),
                      ("ojo", "OJO"), ("abanderado", "ABANDERADO")):
        H.append("#define ENC_HP_%s %d" % (name, hp[key]))
    H += ["#endif", ""]
    OUT_HP.write_text("\n".join(H), encoding="utf-8", newline="\n")
    print("wrote", OUT, OUT_HP)


if __name__ == "__main__":
    main()
