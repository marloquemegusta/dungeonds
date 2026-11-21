#!/usr/bin/env python3
"""Hornea el heroe (andar) del campamento con la luz de la hoguera desde 8 azimuts (DESIGN.md 7.5).

Para cada azimut a (0..7 = S, SW, W, NW, N, NE, E, SE: donde esta el heroe RESPECTO al fuego) llama al lab rapido
(tools/lab/fast/export_character_fast.cjs, --light camp-fire --lightAzimuth a) con los mismos parametros que
tools/rebuild_all.py usa para 'corazon', en .scratch_camp_hero/ (ignorado por git), y empaqueta:

    nitrofiles/camp/hero_a<a>.bin

Formato (little endian), legible por fotogramas desde NitroFS (camp_hero.c):
    u32 magic 'CHRO' (0x4F524843), u32 nrec (= 64: dir*8 + frame), u8 ground_anchor[8], u8 pad[0]
    64 x record { u8 bounds[4] (x,y,w,h del sprite recortado), u8 sbounds[4] (idem de la sombra en el lienzo 80x80),
                  u32 off (desde el inicio del fichero), u16 pix_bytes, u16 runs_bytes, u16 mask_bytes, u16 pad }
    a partir de 'off', por fotograma y contiguos: pixeles BGR555 (pitch par, filas recortadas, bit 15 = opaco),
    runs (mismo formato que blit_stride: (bh+1) offsets de fila en halfwords + x | len << 8), mascara de sombra
    (nibbles de 4 bits, 15 = sombra, recortada a sbounds, fila a fila sin relleno).
La conversion de color y los runs son los de tools/generate_player_sprites_c.py (modo c2: a >= 77, redondeo).

Uso:  python tools/camp/bake_camp_hero.py [--azimuths 0,1,..] [--sheet ruta.png] [--jobs N] [--keep]
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAR_DIR = os.path.join(ROOT, "assets", "sprites", "characters", "corazon")
MODEL = os.path.join(ROOT, "assets", "models", "characters", "corazon", "corazon_walk.fbx")
EXPORTER = os.path.join(ROOT, "tools", "lab", "fast", "export_character_fast.cjs")
TMP = os.path.join(ROOT, ".scratch_camp_hero")
OUT = os.path.join(ROOT, "nitrofiles", "camp")
SPRITE = 40
SHADOW = 80
NDIR, NFRM = 8, 8
MAGIC = 0x4F524843
REC_MAX = 4096            # camp_hero.h CAMP_HERO_REC_MAX
AZ_NAMES = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


def export(a, tmp_dir):
    """Un azimut con el lab rapido. Mismos parametros que rebuild_all.py para 'corazon' (characters.json)."""
    cfg = json.load(open(os.path.join(ROOT, "assets", "sprites", "characters", "characters.json"), encoding="utf-8"))["characters"]["corazon"]
    out = os.path.join(tmp_dir, f"a{a}")
    shutil.rmtree(out, ignore_errors=True)
    cmd = ["node", EXPORTER, MODEL, out,
           "--template", os.path.join(CHAR_DIR, "settings.json"),
           "--anim", cfg["anim"], "--resolution", str(cfg["resolution"]),
           "--fitZoom", str(cfg["fitZoom"]),
           "--muzzleBone", cfg["muzzleBone"], "--muzzleForward", str(cfg["muzzleForward"]),
           "--legibility", "c2", "--noCHeader",
           "--light", "camp-fire", "--lightAzimuth", str(a)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"azimut {a}: el lab fallo\n{r.stdout}\n{r.stderr}")
    for line in (r.stdout + r.stderr).splitlines():
        if "WARNING" in line:
            print(f"  [a{a}] {line}")
    return out


def convert_frame(cell):
    """Celda RGBA 40x40 -> (bounds, pixeles u16 recortados, runs u16)."""
    w = h = SPRITE
    buf = [0] * (w * h)
    mnx, mxx, mny, mxy = w, -1, h, -1
    px = cell.load()
    for y in range(h):
        for x in range(w):
            r, g, b, al = px[x, y]
            if al < 77:
                continue
            val = ((r * 31 + 127) // 255) | (((g * 31 + 127) // 255) << 5) | (((b * 31 + 127) // 255) << 10) | 0x8000
            buf[y * w + x] = val
            mnx, mxx, mny, mxy = min(mnx, x), max(mxx, x), min(mny, y), max(mxy, y)
    if mxx < mnx:
        return (0, 0, 0, 0), [], []
    bw, bh = mxx - mnx + 1, mxy - mny + 1
    pix = []
    for y in range(mny, mxy + 1):
        pix.extend(buf[y * w + mnx:y * w + mxx + 1])
        if bw & 1:
            pix.append(0)
    rows = []
    for y in range(mny, mxy + 1):
        rr, x = [], mnx
        while x <= mxx:
            if buf[y * w + x] & 0x8000:
                x0 = x
                while x <= mxx and buf[y * w + x] & 0x8000:
                    x += 1
                rr.append((x0 - mnx) | ((x - x0) << 8))
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
    return (mnx, mny, bw, bh), pix, block


def convert_mask(shadow_atlas, d, f, sb):
    """Mascara de sombra recortada a sb = (x, y, w, h): nibbles (15 = sombra), fila a fila."""
    x0, y0, bw, bh = sb
    px = shadow_atlas.load()
    nib = []
    for y in range(y0, y0 + bh):
        for x in range(x0, x0 + bw):
            nib.append(15 if px[f * SHADOW + x, d * SHADOW + y][3] > 0 else 0)
    out = bytearray()
    for i in range(0, len(nib), 2):
        out.append(nib[i] | ((nib[i + 1] if i + 1 < len(nib) else 0) << 4))
    return bytes(out)


def pack(a, src):
    st = json.load(open(os.path.join(src, "settings.json"), encoding="utf-8"))
    assert st["framesPerDirection"] == NFRM and str(st["frameSize"]) == f"{SPRITE}x{SPRITE}", st["frameSize"]
    sheet = Image.open(os.path.join(src, "spritesheet.png")).convert("RGBA")
    shadow = Image.open(os.path.join(src, "shadow.png")).convert("RGBA")
    assert shadow.size == (NFRM * SHADOW, NDIR * SHADOW), shadow.size
    anchors = [int(v) for v in st["dirGroundAnchors"]]
    recs, blobs = [], []
    for d in range(NDIR):
        for f in range(NFRM):
            cell = sheet.crop((f * SPRITE, d * SPRITE, (f + 1) * SPRITE, (d + 1) * SPRITE))
            bounds, pix, runs = convert_frame(cell)
            sb = tuple(int(v) for v in st["shadowBounds"][d][f])
            mask = convert_mask(shadow, d, f, sb)
            pb = struct.pack(f"<{len(pix)}H", *pix)
            rb = struct.pack(f"<{len(runs)}H", *runs)
            rec = pb + rb
            rec += b"\0" * (-len(rec) % 4)
            mask_off = len(rec)
            rec += mask
            rec += b"\0" * (-len(rec) % 4)
            assert len(rec) <= REC_MAX, (a, d, f, len(rec))
            recs.append((bounds, sb, len(pb), len(rb), len(mask)))
            blobs.append(rec)
    head_size = 16 + 20 * len(recs)
    off = head_size
    header = struct.pack("<II8B", MAGIC, len(recs), *anchors)
    for (bounds, sb, pbl, rbl, mbl), rec in zip(recs, blobs):
        header += struct.pack("<4B4BIHHHH", *bounds, *sb, off, pbl, rbl, mbl, 0)
        off += len(rec)
    assert len(header) == head_size
    path = os.path.join(OUT, f"hero_a{a}.bin")
    with open(path, "wb") as fh:
        fh.write(header)
        for rec in blobs:
            fh.write(rec)
    return path, max(len(r) for r in blobs), anchors


def contact_sheet(srcs, path, scale=4):
    """Hoja de contacto: columnas = azimut de la luz, filas = direccion de cara (frame 0 de andar). Sprite sobre fondo
    neutro con su sombra (mascara) debajo; 4x NEAREST."""
    cw = SHADOW
    sheet = Image.new("RGBA", (len(srcs) * cw, NDIR * cw), (70, 66, 60, 255))
    for ci, (a, src) in enumerate(sorted(srcs.items())):
        sp = Image.open(os.path.join(src, "spritesheet.png")).convert("RGBA")
        sh = Image.open(os.path.join(src, "shadow.png")).convert("RGBA")
        st = json.load(open(os.path.join(src, "settings.json"), encoding="utf-8"))
        for d in range(NDIR):
            f = 0
            cell = Image.new("RGBA", (cw, cw), (70, 66, 60, 255))
            m = sh.crop((f * SHADOW, d * SHADOW, (f + 1) * SHADOW, (d + 1) * SHADOW))
            dark = Image.new("RGBA", (cw, cw), (20, 20, 24, 255))
            cell = Image.composite(Image.blend(cell, dark, 0.5), cell, m.split()[3].point(lambda v: 255 if v else 0))
            anchor = st["anchor"]
            spr = sp.crop((f * SPRITE, d * SPRITE, (f + 1) * SPRITE, (d + 1) * SPRITE))
            # el ancla del sprite (anchor) coincide con el centro del lienzo de sombra
            cell.alpha_composite(spr, (cw // 2 - anchor[0], cw // 2 - anchor[1]))
            sheet.paste(cell, (ci * cw, d * cw))
    sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--azimuths", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--sheet", help="PNG de la hoja de contacto (columnas: azimut de luz; filas: direccion de cara)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--keep", action="store_true", help="conserva .scratch_camp_hero/")
    args = ap.parse_args()
    azs = [int(v) for v in args.azimuths.split(",")]
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        srcs = dict(zip(azs, ex.map(lambda a: export(a, TMP), azs)))
    for a in azs:
        path, rmax, anchors = pack(a, srcs[a])
        print(f"azimut {a} ({AZ_NAMES[a]}): {os.path.relpath(path, ROOT)} {os.path.getsize(path)} bytes, fotograma max {rmax}, anclas {anchors}")
    if args.sheet:
        contact_sheet(srcs, args.sheet)
        print("hoja de contacto:", args.sheet)
    if not args.keep:
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
