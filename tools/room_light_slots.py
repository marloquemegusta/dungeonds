#!/usr/bin/env python3
"""Prepara los arrays de sprites de source/player_sprite.c para el cargador de luz por sala (source/room_light.c).

1. Quita `const` de las declaraciones g_*_frames/_runs/_shadow_* (.c y include/player_sprite.h): los paquetes de
   nitrofiles/arpg_luz/<luz>.bin las sobrescriben en la pantalla de carga (en la DS .rodata y .data viven en la misma RAM).
2. Agranda los arrays de 1 dimension al maximo de los 12 paquetes (el arte re-iluminado comprime distinto).
3. Escribe source/room_light_slots.c: tabla {destino, bytes maximos} en el orden del paquete.
Idempotente; hay que repetirlo si se regenera source/player_sprite.c con generate_player_sprites_c.py.
"""
import re, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUF = ("_frames", "_frame_offsets", "_frame_bounds", "_runs", "_run_offsets", "_shadow_masks", "_shadow_offsets", "_shadow_bounds")
DECL = re.compile(r"^(const\s+)?(uint16_t|uint32_t|uint8_t)\s+(g_[a-zA-Z0-9_]+)((?:\[[^\]]*\])+)([^=;]*)=\s*\{(.*?)\};", re.M | re.S)
ELS = {"uint8_t": 1, "uint16_t": 2, "uint32_t": 4}


def pack_slot_lens(path):
    p = path.read_bytes()
    m, nt, ns, nst, nsl = struct.unpack_from("<IHHII", p, 0)
    o = 16 + 512 + nt * 64 + 16 * 64 * 2 + ns * 8 + nst * 2
    out = []
    for _ in range(nsl):
        (l,) = struct.unpack_from("<I", p, o); o += 4 + l; out.append(l)
    # stamp_tiles maximo para dimensionar el bufer del cargador
    return out, nt, nst


def main():
    src = ROOT / "source/player_sprite.c"
    text = src.read_bytes().decode("ascii")
    decls = [m for m in DECL.finditer(text)
             if any(m.group(3).endswith(s) for s in SUF) and not m.group(3).startswith("g_character_")]
    names = [m.group(3) for m in decls]
    packs = sorted((ROOT / "nitrofiles/arpg_luz").glob("*.bin"))
    maxl = None; max_tiles = 0; max_st = 0
    for pk in packs:
        lens, nt, nst = pack_slot_lens(pk)
        assert len(lens) == len(names), (pk, len(lens), len(names))
        maxl = lens if maxl is None else [max(a, b) for a, b in zip(maxl, lens)]
        max_tiles = max(max_tiles, nt); max_st = max(max_st, nst)
    rows = []
    edits = []
    for m, ml in zip(decls, maxl):
        ctype, name, dims = m.group(2), m.group(3), m.group(4)
        el = ELS[ctype]
        n_day = len(re.findall(r"0x[0-9a-fA-F]+|-?\d+", m.group(6)))
        if dims == "[]":
            n = max(n_day, (ml + el - 1) // el)
            rows.append((name, n * el))
            new_dims = f"[{n}]"
        else:
            rows.append((name, max(n_day * el, ml)))
            new_dims = dims
        edits.append((m.start(), m.end(), m.group(1) or "", ctype, name, dims, new_dims))
    # aplica de atras adelante
    for st, en, cst, ctype, name, dims, nd in reversed(edits):
        seg = text[st:en]
        seg = seg.replace(f"{cst}{ctype} {name}{dims}", f"{ctype} {name}{nd}", 1)
        text = text[:st] + seg + text[en:]
    src.write_bytes(text.encode("ascii"))
    h = ROOT / "include/player_sprite.h"
    ht = h.read_bytes().decode("utf-8")
    for n in names:
        ht = re.sub(r"extern const (uint\d+_t) " + re.escape(n) + r"\b", r"extern \1 " + n, ht)
    h.write_bytes(ht.encode("utf-8"))
    out = ["// Generado por tools/room_light_slots.py: destinos de los sprites del heroe y tablas de enemigos que sustituye el\n",
           "// paquete de luz de cada sala (orden del paquete = orden de los arrays de source/player_sprite.c).\n",
           "#include \"room_light.h\"\n\n"]
    for n, _ in rows:
        out.append(f"extern uint8_t {n}[];\n")
    out.append("\nconst RoomLightSlot g_room_light_slots[] = {\n")
    for n, b in rows:
        out.append(f"    {{ {n}, {b} }},\n")
    out.append("};\n")
    out.append(f"const uint32_t g_room_light_slot_count = {len(rows)};\n")
    out.append(f"#define ROOM_LIGHT_MAX_TILES_GEN {max_tiles}\n#define ROOM_LIGHT_MAX_STAMP_TILES_GEN {max_st}\n")
    (ROOT / "source/room_light_slots.c").write_bytes("".join(out).encode("ascii"))
    print("slots", len(rows), "max tiles", max_tiles, "max stamp tiles", max_st)


if __name__ == "__main__":
    main()
