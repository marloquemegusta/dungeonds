#!/usr/bin/env python
"""Hornea la runa del Glifo (variante A, «Sello litúrgico») para la ROM.
    python tools/glifo_rune/bake_glifo_rune.py
Estructura por capas (DESIGN.md 7.7, auras componibles):
  - base: Sello A (doble anillo, inscripción, crismón, cruces cardinales). Siempre.
  - transformación Redil: la MISMA geometría retorcida en remolino (ángulo += K*(1-r)); se hornea como máscara propia
    con su orden de apertura. Una futura aura que deforme la runa añade otra máscara aquí.
  - capa aditiva Zarza: puntos de emisión de lenguas de llama sobre los píxeles de la grieta, horneados por máscara
    (valen igual sobre la base que sobre la retorcida) y marca de «llamarada» al detonar (flag GLIFO_FL_FLARE).
  - pozo de luz del Redil (disco + 8 fotogramas de brazos) y ruta de las motas en espiral.
Reutiliza la geometría de tools/glifo_mockup/glifo_mockup.py. Escribe source/glifo_rune_data.c e
include/glifo_rune_data.h (newline LF)."""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "glifo_mockup"))
import glifo_mockup as gm  # noqa: E402

CX, CY = gm.CX, gm.CY
TWIST_K = 1.7          # radianes de giro en el centro respecto al borde (remolino del Redil)
N_EMIT = 32            # puntos de emisión de lenguas de la Zarza por máscara

_orig_strokes = gm.strokes_for


def _subdivide(pts, step=0.04):
    out = [pts[0]]
    for i in range(1, len(pts)):
        (u0, v0), (u1, v1) = pts[i - 1], pts[i]
        n = max(1, int(math.hypot(u1 - u0, v1 - v0) / step))
        for k in range(1, n + 1):
            out.append((u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * k / n))
    return out


def _swirl(p):
    r = math.hypot(p[0], p[1])
    a = math.atan2(p[1], p[0]) + TWIST_K * max(0.0, 1.0 - r)
    return (r * math.cos(a), r * math.sin(a))


def strokes_swirl(variant, aura):
    base = _orig_strokes(variant, "x")
    return [([_swirl(p) for p in _subdivide(pts)], g, j, pb, br) for pts, g, j, pb, br in base]


def build(mask):
    gm.strokes_for = strokes_swirl if mask == "twist" else _orig_strokes
    r = gm.Rune("A", "x" if mask == "base" else "swirl")
    gm.strokes_for = _orig_strokes
    return r


def bake_rune(rune):
    shards = set(rune.shards)
    items = []
    for i in range(rune.n):
        o = int(round(float(rune.order[i]) * 255))
        rn = float(rune.rn[i])
        cl = int(round(255 * (1.1 - min(rn, 1.1)) / 1.1))
        br = float(rune.br[i])
        brc = 0 if br < 0.6 else (1 if br < 1.06 else 2)
        flags = brc
        if int(rune.kind[i]) == 1:
            flags |= 4
        if i in shards:
            flags |= 8
        if int(rune.kind[i]) == 0 and gm.hsh(rune.x[i], rune.y[i], 11) < 0.12:
            flags |= 16
        dx, dy = int(rune.x[i]) - CX, int(rune.y[i]) - CY
        assert -127 <= dx <= 127 and -127 <= dy <= 127
        items.append((o, dx, dy, cl, flags))
    items.sort(key=lambda t: (t[0], t[2], t[1]))
    return items


def bake_emit(items):
    cr = [(dx, dy) for o, dx, dy, cl, fl in items if not (fl & 4)]
    step = len(cr) / float(N_EMIT)
    out = []
    for i in range(N_EMIT):
        out.append(cr[int(i * step + gm.hsh(i, 3, 7) * step * 0.9)])
    return out


def bake_vortex():
    rx, ry = 7.5, 3.9
    base = []
    for yy in range(-8, 9):
        for xx in range(-12, 13):
            v = (xx / rx) ** 2 + (yy / ry) ** 2
            if v <= 1.0:
                col = 1 if v > 0.72 else 0
            elif v <= 1.5 and yy >= 0:
                col = 2
            else:
                continue
            base.append((xx, yy, col, int(round(math.sqrt(v) * 200))))
    frames = []
    for k in range(8):
        ang0 = k * (2 * math.pi / 3) / 8
        cell = {}
        for a in range(3):
            for i in range(26):
                t = 0.04 + 0.96 * i / 25
                th = ang0 + a * 2 * math.pi / 3 + 3.2 * t
                x = round(rx * 0.92 * t * math.cos(th))
                y = round(ry * 0.92 * t * math.sin(th))
                col = 3 if t < 0.35 else 4 if t < 0.7 else 5
                cell[(x, y)] = (x, y, col, int(round(t * 0.92 * 200)))
        cell[(0, 0)] = (0, 0, 3, 0)
        frames.append(sorted(cell.values(), key=lambda p: p[3]))
    return sorted(base, key=lambda p: p[3]), frames


def bake_spiral():
    paths = []
    for arm in range(3):
        th0 = arm * 2 * math.pi / 3
        pts = []
        L = 58
        for f in range(L + 1):
            r = 0.97 * (1.0 - f / L)
            th = th0 + TWIST_K * (1.0 - r) * 1.2
            pts.append((int(round(r * 40 * math.cos(th))), int(round(r * 20 * math.sin(th))) - 1))
        step = (len(pts) - 1) / 23.0
        paths.append([pts[int(round(i * step))] for i in range(24)])
    return paths


def bake_flame():
    return [int(round(5 * (math.sin(math.pi * age / 16.0) ** 0.8))) for age in range(16)]


def emit_px(name, items, f):
    f.write("const GlifoPx %s[%d] = {\n" % (name, len(items)))
    for i in range(0, len(items), 6):
        f.write("    " + " ".join("{%d,%d,%d,%d,%d}," % (dx, dy, o, cl, fl) for o, dx, dy, cl, fl in items[i:i + 6]) + "\n")
    f.write("};\n")


def emit_pts(name, pts, f):
    f.write("const int8_t %s[GLIFO_EMIT_N][2] = {\n" % name)
    for i in range(0, len(pts), 8):
        f.write("    " + " ".join("{%d,%d}," % p for p in pts[i:i + 8]) + "\n")
    f.write("};\n")


HEADER = """// GENERADO por tools/glifo_rune/bake_glifo_rune.py: no editar a mano.
// Runa A «Sello litúrgico» del Glifo (DESIGN.md 7.7) a radio de suelo 40 (elipse 80x40), relativa al centro.
// Capas: base (siempre) + transformación Redil (misma geometría en remolino) + capa aditiva Zarza (emisores).
#ifndef GLIFO_RUNE_DATA_H
#define GLIFO_RUNE_DATA_H
#include <stdint.h>

// Un píxel de la grieta, ordenados por `order` (orden de apertura 0..255).
// close: orden de cierre (0 = el de fuera, 255 = el del centro).
// flags: bits 0-1 brillo (0 = 0,5; 1 = 1; 2 = 1,12); GLIFO_FL_BRANCH astilla corta; GLIFO_FL_SHARD esquirla de piedra
// levantada; GLIFO_FL_FLARE el píxel arde en la llamarada de la Zarza al detonar.
typedef struct { int8_t dx, dy; uint8_t order, close, flags; } GlifoPx;
#define GLIFO_FL_BRANCH 4
#define GLIFO_FL_SHARD 8
#define GLIFO_FL_FLARE 16

// Pozo de luz del Redil. col: 0 hondo, 1 borde, 2 brillo bajo, 3 marfil, 4 oro, 5 ámbar. rr: 0..245 (200 = borde).
typedef struct { int8_t dx, dy; uint8_t col, rr; } GlifoVx;

#define GLIFO_EMIT_N %(emit)d
#define GLIFO_BASE_N %(nb)d
#define GLIFO_TWIST_N %(nt)d
#define GLIFO_VX_BASE_N %(nv)d
#define GLIFO_VX_FRAMES 8
#define GLIFO_VX_ARM_N %(na)d

extern const GlifoPx g_glifo_base[GLIFO_BASE_N];       // Sello solo (y con Zarza)
extern const GlifoPx g_glifo_twist[GLIFO_TWIST_N];     // la misma runa retorcida por el Redil
extern const int8_t g_glifo_emit_base[GLIFO_EMIT_N][2];   // emisores de lenguas de la Zarza sobre cada máscara
extern const int8_t g_glifo_emit_twist[GLIFO_EMIT_N][2];
extern const GlifoVx g_glifo_vx_base[GLIFO_VX_BASE_N];
extern const GlifoVx g_glifo_vx_arm[GLIFO_VX_FRAMES][GLIFO_VX_ARM_N];   // relleno con rr = 255
extern const int8_t g_glifo_spiral[3][24][2];          // ruta de las motas del Redil: brazo, punto, (dx, dy)
extern const uint8_t g_glifo_flame_h[16];              // altura de la lengua de llama por edad

#endif
"""


def main():
    base = bake_rune(build("base"))
    twist = bake_rune(build("twist"))
    vbase, varms = bake_vortex()
    nmax = max(len(a) for a in varms)
    spiral = bake_spiral()
    flame = bake_flame()

    with open(os.path.join(ROOT, "include", "glifo_rune_data.h"), "w", newline="") as f:
        f.write(HEADER % dict(emit=N_EMIT, nb=len(base), nt=len(twist), nv=len(vbase), na=nmax))
    with open(os.path.join(ROOT, "source", "glifo_rune_data.c"), "w", newline="") as f:
        f.write('// GENERADO por tools/glifo_rune/bake_glifo_rune.py: no editar a mano.\n#include "glifo_rune_data.h"\n\n')
        emit_px("g_glifo_base", base, f)
        f.write("\n")
        emit_px("g_glifo_twist", twist, f)
        f.write("\n")
        emit_pts("g_glifo_emit_base", bake_emit(base), f)
        f.write("\n")
        emit_pts("g_glifo_emit_twist", bake_emit(twist), f)
        f.write("\nconst GlifoVx g_glifo_vx_base[GLIFO_VX_BASE_N] = {\n")
        for i in range(0, len(vbase), 8):
            f.write("    " + " ".join("{%d,%d,%d,%d}," % p for p in vbase[i:i + 8]) + "\n")
        f.write("};\n\nconst GlifoVx g_glifo_vx_arm[GLIFO_VX_FRAMES][GLIFO_VX_ARM_N] = {\n")
        for fr in varms:
            row = list(fr) + [(0, 0, 3, 255)] * (nmax - len(fr))
            f.write("    {" + " ".join("{%d,%d,%d,%d}," % p for p in row) + "},\n")
        f.write("};\n\nconst int8_t g_glifo_spiral[3][24][2] = {\n")
        for arm in spiral:
            f.write("    {" + " ".join("{%d,%d}," % p for p in arm) + "},\n")
        f.write("};\n\nconst uint8_t g_glifo_flame_h[16] = { " + ", ".join(str(v) for v in flame) + " };\n")
    print("base", len(base), "twist", len(twist), "vortex", len(vbase), nmax)

    # vista previa de las dos máscaras (comprobación visual, no se usa en la ROM)
    try:
        from PIL import Image
        for name, items in (("base", base), ("twist", twist)):
            im = Image.new("RGB", (128, 96), (30, 26, 24))
            for o, dx, dy, cl, fl in items:
                im.putpixel((CX + dx, CY + dy), (230, 200, 150) if not fl & 4 else (200, 150, 90))
            out = os.environ.get("GLIFO_PREVIEW_DIR")
            if out:
                im.resize((512, 384), Image.NEAREST).save(os.path.join(out, "mask_%s.png" % name))
    except Exception as e:  # noqa
        print("preview skipped", e)


if __name__ == "__main__":
    main()
