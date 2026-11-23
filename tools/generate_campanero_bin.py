"""Empaqueta los clips del Campanero de Animas (assets/sprites/characters/campanero*/) a nitrofiles/campanero/campanero.bin
y genera include/campanero_sprite_dims.h con los tamanos maximos de los buffers de streaming.

Por que NitroFS: cinco clips de 8x8 fotogramas a 80x80 no caben en la EWRAM fija (TECHNICAL.md 3.3), asi que el jefe lee de
NitroFS solo el fotograma que toca (source/campanero_sprite.c), como el remate y los punos.

Formato (little endian):
  cabecera: u32 magic 'CAMP', u32 numero de registros (clips * 8 dirs * 8 fotogramas)
  tabla de registros (CAMP_REC_BYTES = 24 cada uno), indice (clip * 8 + dir) * 8 + fotograma:
    u8 bounds[4]   {x, y, w, h} del fotograma recortado dentro de la celda 80x80
    u8 sbounds[4]  {x, y, w, h} de la sombra recortada dentro del lienzo 112x112
    u32 offset     posicion en el fichero de: pixeles | tramos | mascara de sombra (cada parte alineada a 4)
    u16 pix_hw     halfwords de pixeles (pitch par), u16 runs_hw halfwords de tramos
    u16 mask_bytes bytes de la mascara de sombra (1 bit por pixel, flujo continuo de filas, LSB primero, relleno a byte)
    u16 flags      bit 0: los pixeles van comprimidos LZ77 (formato BIOS, tools/lz10.py); la mascara y los tramos van crudos
    u32 lz_bytes   con el bit 0: bytes que ocupan los pixeles comprimidos en el bin (si no, 0; pix_hw sigue siendo el tamano descomprimido)
Clips: 0 idle, 1 walk, 2 toque, 3 tanido, 4 death (el orden de CAMP_CLIP_* en include/campanero_sprite.h).

Compresion por clip (desactivada por defecto, para no engordar la ROM): `--lz campanero_tanido,campanero_death` comprime solo los
pixeles de esos clips (`--lz all` = todos); el registro de cada fotograma dice si va comprimido. El bin comprimido solo
sirve con CAMP_LZ_BODY=1 en la compilacion (campanero_sprite.c): la cabecera de dimensiones lo declara y la compilacion
falla si no coinciden. `--dry` calcula tamanos sin escribir nada.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lz10  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SPR = ROOT / "assets/sprites/characters"
CLIPS = ["campanero", "campanero_walk", "campanero_toque", "campanero_tanido", "campanero_death"]
W = H = 80          # celda del lab (resolution de characters.json)
SHW = 112            # lienzo de sombra del motor (recorte centrado del 160x160 del lab; CharacterConfig.shadow_w)
ALPHA = 77
MAGIC = 0x504D4143  # 'CAMP'
REC = 24


def pitch(bw):
    return bw + (bw & 1)


def load_cell(im, f, d, shift=0):
    """shift: filas que baja el contenido (el ancla de suelo del clip se alinea con la del idle)."""
    buf = [0] * (W * H)
    cell = im.crop((f * W, d * H, (f + 1) * W, (d + 1) * H))
    px = cell.load()
    for y in range(H):
        if not 0 <= y - shift < H:
            continue
        for x in range(W):
            r, g, b, a = px[x, y - shift]
            if a >= ALPHA:
                buf[y * W + x] = ((r * 31 + 127) // 255) | (((g * 31 + 127) // 255) << 5) | (((b * 31 + 127) // 255) << 10) | 0x8000
    return buf


def encode(buf):
    xs = [i % W for i, v in enumerate(buf) if v]
    ys = [i // W for i, v in enumerate(buf) if v]
    if not xs:
        return (0, 0, 0, 0), [], [0, 0]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    pix, rows = [], []
    for y in range(y0, y1 + 1):
        row = buf[y * W + x0:y * W + x1 + 1]
        pix.extend(row)
        if bw & 1:
            pix.append(0)
        rr, x = [], 0
        while x < bw:
            if row[x]:
                s = x
                while x < bw and row[x]:
                    x += 1
                rr.append(s | ((x - s) << 8))
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
    return (x0, y0, bw, bh), pix, block


def parse_header(path):
    text = path.read_text(encoding="utf-8")
    anchors = [int(v) for v in re.search(r"g_\w+_ground_anchors\[8\]\s*=\s*\{([^}]+)\};", text).group(1).split(",") if v.strip()]
    shb_body = re.search(r"g_\w+_shadow_bounds\[8\]\[8\]\[4\]\s*=\s*\{([\s\S]+?)\n\};", text).group(1)
    mask_body = re.search(r"g_\w+_shadow_masks\[8\]\[8\]\[\d+\][^{]+\{([\s\S]+?)\n\};", text).group(1)
    rows = [[int(v) for v in r] for r in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", shb_body)]
    masks = bytes(int(b, 16) for b in re.findall(r"0x[0-9A-Fa-f]{2}", mask_body))
    return anchors, rows, masks


SPECK_MAX = 24   # manchas de sombra de menos pixeles que esto se borran


def drop_specks(grid):
    """Quita las motas sueltas de la sombra: el mesh degenerado de limites de build_campanero.py (invisible en el sprite)
    si proyecta puntos en el pase de sombra del lab. Se quedan solo las manchas (8-vecinos) de SPECK_MAX pixeles o mas."""
    seen, keep = set(), {}
    for start in grid:
        if start in seen:
            continue
        comp, stack = [], [start]
        seen.add(start)
        while stack:
            cx, cy = stack.pop()
            comp.append((cx, cy))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (cx + dx, cy + dy)
                    if q in grid and q not in seen:
                        seen.add(q); stack.append(q)
        if len(comp) >= SPECK_MAX:
            for q in comp:
                keep[q] = grid[q]
    return keep


def shadow_frame(rows, masks, i, src=2 * W, shift=0):
    """Mascara de la sombra del fotograma i recortada al lienzo 112x112 centrado y luego a su bounding box (1 bpp, LSB primero)."""
    off = (src - SHW) // 2
    x, y, w, h = rows[i]
    frame_bytes = src * src // 2
    data = masks[i * frame_bytes:(i + 1) * frame_bytes]
    # lo que cae fuera del lienzo 112x112 (centrado en el de 160x160, con el desplazamiento del clip) se recorta
    x0, x1 = max(x, off), min(x + w, off + SHW)
    y0, y1 = max(y, off - shift), min(y + h, off + SHW - shift)
    if x1 <= x0 or y1 <= y0:
        return (0, 0, 0, 0), b""
    grid = {}
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            p = yy * src + xx
            bb = data[p >> 1]
            v = (bb >> 4) if (p & 1) else (bb & 0x0F)
            assert v in (0, 15), "mascara de sombra no binaria"
            if v:
                grid[(xx, yy)] = 1
    grid = drop_specks(grid)
    if not grid:
        return (0, 0, 0, 0), b""
    x0, x1 = min(k[0] for k in grid), max(k[0] for k in grid) + 1
    y0, y1 = min(k[1] for k in grid), max(k[1] for k in grid) + 1
    nibbles = [grid.get((xx, yy), 0) for yy in range(y0, y1) for xx in range(x0, x1)]
    packed = bytearray()
    for k in range(0, len(nibbles), 8):
        v = 0
        for j, bit in enumerate(nibbles[k:k + 8]):
            v |= bit << j
        packed.append(v)
    nx, ny, w, h = x0 - off, y0 - off + shift, x1 - x0, y1 - y0
    return (nx, ny, w, h), bytes(packed)


def main(lz_clips=(), dry=False):
    recs, blobs = [], []
    anchors0 = None
    mx = dict(pix=0, runs=0, mask=0, lz=0)
    for c, name in enumerate(CLIPS):
        im = Image.open(SPR / name / "spritesheet.png").convert("RGBA")
        anchors, rows, masks = parse_header(SPR / name / "nds_shadow_anchor.h")
        if anchors0 is None:
            anchors0 = anchors
        shifts = [anchors0[d] - anchors[d] for d in range(8)]   # el lab estima el ancla por clip: se alinean con el idle
        if any(shifts):
            print(name, "desplaza filas", shifts)
        for d in range(8):
            for f in range(8):
                b, pix, runs = encode(load_cell(im, f, d, shifts[d]))
                sb, mask = shadow_frame(rows, masks, d * 8 + f, shift=shifts[d])
                packed = None
                if name in lz_clips and pix:
                    raw = struct.pack("<%dH" % len(pix), *pix)
                    packed = lz10.compress(raw)
                    if len(packed) >= len(raw):
                        packed = None        # no compensa: crudo
                    else:
                        mx["lz"] = max(mx["lz"], len(packed))
                recs.append((b, sb, pix, runs, mask, packed))
                mx["pix"] = max(mx["pix"], len(pix) * 2)
                mx["runs"] = max(mx["runs"], len(runs) * 2)
                mx["mask"] = max(mx["mask"], len(mask))
    n = len(recs)
    head_bytes = 8 + n * REC
    out = bytearray(b"\0" * head_bytes)
    struct.pack_into("<II", out, 0, MAGIC, n)

    def pad4():
        while len(out) & 3:
            out.append(0)

    for i, (b, sb, pix, runs, mask, packed) in enumerate(recs):
        pad4()
        off = len(out)
        if packed:
            out += packed
        elif pix:
            out += struct.pack("<%dH" % len(pix), *pix)
        pad4()
        out += struct.pack("<%dH" % len(runs), *runs)
        pad4()
        out += mask
        struct.pack_into("<4B4BIHHHHI", out, 8 + i * REC, *b, *sb, off, len(pix), len(runs), len(mask),
                         1 if packed else 0, len(packed) if packed else 0)
    any_lz = any(r[5] for r in recs)
    if dry:
        print("DRY: bin %d B (lz: %s), mascara max %d" % (len(out), ",".join(sorted(lz_clips)) or "ninguno", mx["mask"]))
        return len(out)
    dest = ROOT / "nitrofiles/campanero"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "campanero.bin").write_bytes(bytes(out))
    # tamanos maximos de buffer: + margen de alineacion
    hdr = ["// Generado por tools/generate_campanero_bin.py: no editar a mano.\n",
           "#ifndef CAMPANERO_SPRITE_DIMS_H\n#define CAMPANERO_SPRITE_DIMS_H\n",
           "#define CAMP_NUM_RECORDS %d\n" % n,
           "#define CAMP_PIX_MAX_BYTES %d\n" % ((mx["pix"] + 3) & ~3),
           "#define CAMP_RUNS_MAX_BYTES %d\n" % ((mx["runs"] + 3) & ~3),
           "#define CAMP_MASK_MAX_BYTES %d\n" % ((mx["mask"] + 3) & ~3),
           "#define CAMP_LZ_MAX_BYTES %d\n" % ((mx["lz"] + 3) & ~3),
           "#define CAMP_BIN_HAS_LZ %d\n" % (1 if any_lz else 0),
           "#define CAMP_FILE_BYTES %d\n" % len(out),
           "#endif\n"]
    (ROOT / "include/campanero_sprite_dims.h").write_text("".join(hdr), encoding="utf-8", newline="\n")
    print("OK: %d registros, bin %d B, max pix %d runs %d mask %d, ancla %s" % (n, len(out), mx["pix"], mx["runs"], mx["mask"], anchors0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lz", default="", help="clips cuyos pixeles se comprimen (coma; 'all' = todos); solo para CAMP_LZ_BODY=1")
    ap.add_argument("--dry", action="store_true", help="solo calcula el tamano, no escribe")
    a = ap.parse_args()
    names = CLIPS if a.lz == "all" else [c for c in a.lz.split(",") if c]
    for c in names:
        assert c in CLIPS, "clip desconocido: %s (validos: %s)" % (c, ", ".join(CLIPS))
    main(set(names), a.dry)
