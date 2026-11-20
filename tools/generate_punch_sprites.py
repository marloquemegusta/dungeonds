"""Empaqueta los clips del combo (assets/sprites/characters/corazon_punch_{a,b}/, corazon_gancho/) a
nitrofiles/punch/<golpe>_d<dir>.bin y genera source/punch_sprites.c con la fila de pies por golpe y direccion.

Formato de cada bin (little endian): cabecera PunchBinHeader (include/punch.h) y detras los pixeles BGR555
recortados a su bounding box por fila con pitch par, y los bloques de tramos opacos que lee blit_stride.
"""
import json
import os
import re
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPR = ROOT / "assets/sprites/characters"
OUT = ROOT / "nitrofiles/punch"
DIRS = ["0_S", "1_SW", "2_W", "3_NW", "4_N", "5_NE", "6_E", "7_SE"]
MOVES = ["punch_a", "punch_b", "gancho"]
N_FRAMES = 8
MAGIC = 0x48434E50  # 'PNCH'
ALPHA = 77          # umbral c2 (characters.json defaults.legibility)


def load_frame(clip, d, f, w, h):
    p = SPR / f"corazon_{clip}" / "frames" / DIRS[d] / f"{f}.png"
    im = Image.open(p).convert("RGBA")
    assert im.size == (w, h), (p, im.size, (w, h))
    buf = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = im.getpixel((x, y))
            if a >= ALPHA:
                buf[y][x] = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) | 0x8000
    return buf


def encode(buf, w, h, pix):
    xs = [x for y in range(h) for x in range(w) if buf[y][x]]
    ys = [y for y in range(h) for x in range(w) if buf[y][x]]
    off = len(pix)
    if not xs:
        return (0, 0, 0, 0), off
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    for y in range(y0, y1 + 1):
        pix.extend(buf[y][x0:x1 + 1])
        if bw & 1:
            pix.append(0)                       # pitch par: cada fila empieza en palabra de 32 bits
    return (x0, y0, bw, bh), off


def encode_runs(buf, w, h, runs):
    xs = [x for y in range(h) for x in range(w) if buf[y][x]]
    ys = [y for y in range(h) for x in range(w) if buf[y][x]]
    off = len(runs)
    if not xs:
        runs.extend([0, 0])
        return off
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    bh = y1 - y0 + 1
    rows = []
    for y in range(y0, y1 + 1):
        rr, x = [], x0
        while x <= x1:
            if buf[y][x]:
                s = x
                while x <= x1 and buf[y][x]:
                    x += 1
                rr.append((s - x0) | ((x - s) << 8))
            else:
                x += 1
        rows.append(rr)
    block, pos = [], bh + 1
    for rr in rows:
        block.append(pos)
        pos += len(rr)
    block.append(pos)
    for rr in rows:
        block.extend(rr)
    if len(block) & 1:
        block.append(0)
    runs.extend(block)
    return off


def build(move):
    settings = json.loads((SPR / f"corazon_{move}" / "settings.json").read_text(encoding="utf-8"))
    w, h = [int(v) for v in settings["frameSize"].split("x")]
    assert w == h == 48, (move, w, h)
    anchors = settings["dirGroundAnchors"]
    OUT.mkdir(parents=True, exist_ok=True)
    max_bin = 0
    for d in range(8):
        pix, runs = [], []
        bounds, poff, roff = [], [], []
        for f in range(N_FRAMES):
            buf = load_frame(move, d, f, w, h)
            b, po = encode(buf, w, h, pix)
            ro = encode_runs(buf, w, h, runs)
            bounds.append(b); poff.append(po); roff.append(ro)
        pix_bytes = len(pix) * 2
        runs_bytes = len(runs) * 2
        head = struct.pack("<3I", MAGIC, pix_bytes, runs_bytes)
        for b in bounds:
            head += struct.pack("<4B", *b)
        for o in poff:
            head += struct.pack("<I", o)
        for o in roff:
            head += struct.pack("<I", o)
        data = head + struct.pack("<%dH" % len(pix), *pix) + struct.pack("<%dH" % len(runs), *runs)
        (OUT / f"{move}_d{d}.bin").write_bytes(data)
        max_bin = max(max_bin, len(data))
    return anchors, max_bin


def main():
    lines = ['// Generado por tools/generate_punch_sprites.py: no editar a mano.\n',
             '#include "punch.h"\n\n']
    max_all = 0
    lines.append("// Fila de pies dentro de la celda 48x48 del lab, por golpe y direccion (S, SW, W, NW, N, NE, E, SE).\n")
    lines.append("const uint8_t g_punch_ground_anchor[PUNCH_NUM_MOVES][PUNCH_NUM_DIRS] = {\n")
    for move in MOVES:
        anchors, max_bin = build(move)
        max_all = max(max_all, max_bin)
        lines.append("    { " + ", ".join(str(a) for a in anchors) + " }, // %s\n" % move)
    lines.append("};\n")
    out = ROOT / "source/punch_sprites.c"
    out.write_text("".join(lines), encoding="utf-8", newline="\n")
    print(f"OK: 24 bins, max={max_all} B")


if __name__ == "__main__":
    main()
