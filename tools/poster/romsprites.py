"""Lector de los sprites de la ROM (hero + enemigos) para los posters. Lee las mismas tablas y .bin que el juego:
source/player_sprite.c (offsets, bounds, anclas, sombras) y nitrofiles/chars/<clip>.bin (CHR1). Sin render ni cizalla."""
import re
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "source/player_sprite.c"
_text = None
_cache = {}


def _src():
    global _text
    if _text is None:
        _text = SRC.read_text(encoding="utf-8", errors="replace")
    return _text


def _ints(body):
    return [int(v, 0) for v in re.findall(r"0x[0-9A-Fa-f]+|\d+", body)]


def _table(name):
    """Enteros del array C `name[...] = { ... };`."""
    t = _src()
    m = re.search(r"\b" + re.escape(name) + r"\s*(\[[^=]*?\])+\s*(__attribute__\(\([^)]*\)\))?\s*=\s*\{", t)
    if not m:
        return None
    i = m.end()
    j = t.index("};", i)
    return _ints(t[i:j])


def char_clips():
    """Nombre del clip de cada CHAR_* (orden de g_character_frame_offsets)."""
    if "clips" not in _cache:
        t = _src()
        m = re.search(r"g_character_frame_offsets\[NUM_CHARACTERS\]\)\[PLAYER_NUM_FRAMES\]\s*=\s*\{(.*?)\};", t, re.S)
        _cache["clips"] = re.findall(r"g_(\w+)_frame_offsets", m.group(1))
    return _cache["clips"]


def char_cells():
    """(cell_w, cell_h, shadow_w, shadow_h) de cada CHAR_*, de g_characters."""
    if "cells" not in _cache:
        t = _src()
        m = re.search(r"g_characters\[NUM_CHARACTERS\]\s*=\s*\{(.*?)\n\};", t, re.S)
        out = []
        for ln in m.group(1).splitlines():
            q = re.search(r'\{\s*"[^"]*",\s*\d+,\s*\d+,\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)', ln)
            if q:
                out.append(tuple(int(x) for x in q.groups()))
        _cache["cells"] = out
    return _cache["cells"]


def anchors():
    if "anch" not in _cache:
        t = _src()
        m = re.search(r"g_character_ground_anchors\[NUM_CHARACTERS\]\[PLAYER_NUM_DIRS\]\s*=\s*\{(.*?)\n\};", t, re.S)
        v = _ints(m.group(1))
        _cache["anch"] = [v[i:i + 8] for i in range(0, len(v), 8)]
    return _cache["anch"]


def _bin(clip):
    p = ROOT / "nitrofiles/chars" / f"{clip}.bin"
    d = p.read_bytes()
    assert d[:4] == b"CHR1", p
    nf, nr, nm = struct.unpack("<III", d[4:16])
    pad = lambda n: (n + 3) & ~3
    fr = np.frombuffer(d[16:16 + nf], "<u2")
    mk = np.frombuffer(d[16 + pad(nf) + pad(nr):16 + pad(nf) + pad(nr) + nm], np.uint8)
    return fr, mk


def _clip_data(clip):
    if clip in _cache:
        return _cache[clip]
    off = np.array(_table(f"g_{clip}_frame_offsets")).reshape(8, -1)
    bnd = np.array(_table(f"g_{clip}_frame_bounds")).reshape(8, -1, 4)
    soff = np.array(_table(f"g_{clip}_shadow_offsets")).reshape(8, -1)
    sbnd = np.array(_table(f"g_{clip}_shadow_bounds")).reshape(8, -1, 4)
    if not (ROOT / "nitrofiles/chars" / f"{clip}.bin").exists():     # clips que van dentro del programa (heroe, campanero)
        t = _src()
        i = t.index(f"g_{clip}_frames[]")
        j = t.index("};", i)
        fr = np.array(_ints(t[t.index("{", i) + 1:j]), np.uint16)
        i = t.index(f"g_{clip}_shadow_masks[]")
        j = t.index("};", i)
        mk = np.array(_ints(t[t.index("{", i) + 1:j]), np.uint8)
    else:
        fr, mk = _bin(clip)
    _cache[clip] = (off, bnd, soff, sbnd, fr, mk)
    return _cache[clip]


def bgr555_rgb(v):
    v = np.asarray(v, np.int32)
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    return np.stack([(r * 255 + 15) // 31, (g * 255 + 15) // 31, (b * 255 + 15) // 31], -1).astype(np.uint8)


def sprite(char_id, d=0, f=0):
    """RGBA de la celda del personaje (cell_w x cell_h) y fila de pies (ancla); el pie esta en (cell_w//2, ancla)."""
    clip = char_clips()[char_id]
    off, bnd, _, _, fr, _ = _clip_data(clip)
    cw, ch = char_cells()[char_id][:2]
    bx, by, bw, bh = (int(x) for x in bnd[d][f])
    out = np.zeros((ch, cw, 4), np.uint8)
    if bw and bh:
        pitch = (bw + 1) & ~1
        o = int(off[d][f])
        px = fr[o:o + pitch * bh].reshape(bh, pitch)[:, :bw]
        rgb = bgr555_rgb(px)
        op = (px & 0x8000) != 0
        out[by:by + bh, bx:bx + bw, :3] = rgb
        out[by:by + bh, bx:bx + bw, 3] = np.where(op, 255, 0)
    return out, anchors()[char_id][d]


def shadow(char_id, d=0, f=0):
    """Mascara booleana del lienzo de sombra (shadow_w x shadow_h) centrada en el pie."""
    clip = char_clips()[char_id]
    _, _, soff, sbnd, _, mk = _clip_data(clip)
    sw, sh = char_cells()[char_id][2:]
    out = np.zeros((sh, sw), bool)
    if len(mk) == 0:
        return out
    bx, by, bw, bh = (int(x) for x in sbnd[d][f])
    o = int(soff[d][f])
    nbit = bw * bh
    bits = np.unpackbits(mk[o:o + (nbit + 7) // 8], bitorder="little")[:nbit].reshape(bh, bw).astype(bool)
    out[by:by + bh, bx:bx + bw] = bits
    return out
