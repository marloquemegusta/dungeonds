#!/usr/bin/env python3
"""Compares two character packages (reference from the browser lab vs fast exporter).

usage: python compare_packages.py <ref_dir> <new_dir> [--diff <out.png>] [--cell N]

Checks: settings.json numeric fields, FIT-like scalars, anchors/bounds (nds_shadow_anchor.h), packed shadow masks,
shadow.png alpha agreement, spritesheet alpha IoU and RGB error on opaque pixels (mean, p99, worst cell).
Writes an optional diff sheet: reference | new | |difference| x4, 4x NEAREST.
"""
import argparse
import json
import os
import re
import sys

import numpy as np
from PIL import Image


def load_rgba(path):
    return np.array(Image.open(path).convert("RGBA")).astype(np.int32)


def num_fields(a, b):
    rows = []
    keys = ["measuredExtent", "fitExtent", "normScale", "stride3dMeters", "strideRatio", "stridePixels",
            "fitZoom", "cameraElevationDegrees", "legibilityPivot", "speedFixed8_8", "ticksPerFrame"]
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            rows.append((k, va, vb, abs(va - vb)))
        else:
            rows.append((k, va, vb, None))
    for k in ["anchor"]:
        d = np.abs(np.array(a[k]) - np.array(b[k])).max() if a.get(k) and b.get(k) else None
        rows.append((k, a.get(k), b.get(k), d))
    for k in ["dirGroundAnchors", "dirBounds", "shadowBounds", "dirMuzzle"]:
        if a.get(k) is None or b.get(k) is None:
            rows.append((k, a.get(k) is not None, b.get(k) is not None, None))
            continue
        d = np.abs(np.array(a[k], dtype=np.float64) - np.array(b[k], dtype=np.float64)).max()
        rows.append((k, "ref", "new", float(d)))
    return rows


def parse_header(path):
    """Extracts the numeric arrays from nds_shadow_anchor.h (bounds and masks)."""
    txt = open(path, encoding="utf8").read()
    bounds = [int(x) for t in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", txt) for x in t]
    masks = [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", txt)]
    return np.array(bounds), np.array(masks, dtype=np.int32)


def sheet_stats(ref, new, cell):
    ra, na = ref[:, :, 3] > 0, new[:, :, 3] > 0
    inter = np.logical_and(ra, na).sum()
    union = np.logical_or(ra, na).sum()
    iou = inter / union if union else 1.0
    both = np.logical_and(ra, na) & (ref[:, :, 3] == 255) & (new[:, :, 3] == 255)
    err = np.abs(ref[:, :, :3] - new[:, :, :3]).max(axis=2)
    mean = err[both].mean() if both.any() else 0.0
    p99 = np.percentile(err[both], 99) if both.any() else 0.0
    H, W = ra.shape
    worst = 0.0
    worst_cell = None
    for cy in range(0, H, cell):
        for cx in range(0, W, cell):
            m = both[cy:cy + cell, cx:cx + cell]
            if not m.any():
                continue
            v = err[cy:cy + cell, cx:cx + cell][m].mean()
            if v > worst:
                worst, worst_cell = v, (cx // cell, cy // cell)
    return iou, mean, p99, worst, worst_cell


def diff_sheet(ref, new, out):
    err = np.clip(np.abs(ref[:, :, :3] - new[:, :, :3]) * 4, 0, 255).astype(np.uint8)
    def bg(a):
        rgb = a[:, :, :3].astype(np.uint8)
        alpha = a[:, :, 3:4] / 255.0
        return (rgb * alpha + 32 * (1 - alpha)).astype(np.uint8)
    sheet = np.concatenate([bg(ref), np.full((ref.shape[0], 2, 3), 255, np.uint8), bg(new),
                            np.full((ref.shape[0], 2, 3), 255, np.uint8), err], axis=1)
    im = Image.fromarray(sheet, "RGB")
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    im.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("new")
    ap.add_argument("--diff")
    ap.add_argument("--cell", type=int, default=40)
    args = ap.parse_args()

    sa = json.load(open(os.path.join(args.ref, "settings.json"), encoding="utf8"))
    sb = json.load(open(os.path.join(args.new, "settings.json"), encoding="utf8"))
    print(f"== settings ({os.path.basename(args.ref)} vs {os.path.basename(args.new)})")
    print(f"{'field':24s} {'ref':>22s} {'new':>22s} {'maxAbsDiff':>12s}")
    for k, va, vb, d in num_fields(sa, sb):
        print(f"{k:24s} {str(va)[:22]:>22s} {str(vb)[:22]:>22s} {'' if d is None else f'{d:.3e}':>12s}")

    print("\n== nds_shadow_anchor.h")
    hb_ref, mk_ref = parse_header(os.path.join(args.ref, "nds_shadow_anchor.h"))
    hb_new, mk_new = parse_header(os.path.join(args.new, "nds_shadow_anchor.h"))
    if hb_ref.shape == hb_new.shape:
        d = np.abs(hb_ref - hb_new)
        print(f"bounds entries {hb_ref.size}: max diff {d.max()}, entries differing {(d.sum(axis=1) > 0).sum() if d.ndim > 1 else (d > 0).sum()}")
    else:
        print(f"bounds shape mismatch {hb_ref.shape} vs {hb_new.shape}")
    if mk_ref.shape == mk_new.shape and mk_ref.size:
        lo_r, hi_r = mk_ref & 0x0f, mk_ref >> 4
        lo_n, hi_n = mk_new & 0x0f, mk_new >> 4
        # nibble-level agreement of the packed coverage masks
        nib_ref = np.stack([lo_r, hi_r], axis=1).ravel() > 0
        nib_new = np.stack([lo_n, hi_n], axis=1).ravel() > 0
        inter = np.logical_and(nib_ref, nib_new).sum()
        union = np.logical_or(nib_ref, nib_new).sum()
        print(f"shadow mask pixels: ref {nib_ref.sum()}, new {nib_new.sum()}, IoU {inter / union if union else 1:.4f}, "
              f"differing pixels {(nib_ref != nib_new).sum()} of {nib_ref.size}")
    else:
        print(f"mask bytes shape mismatch {mk_ref.shape} vs {mk_new.shape}")

    print("\n== shadow.png")
    sr, sn = os.path.join(args.ref, "shadow.png"), os.path.join(args.new, "shadow.png")
    if os.path.exists(sr) and os.path.exists(sn):
        a, b = load_rgba(sr), load_rgba(sn)
        if a.shape == b.shape:
            ma, mb = a[:, :, 3] > 0, b[:, :, 3] > 0
            diff = (ma != mb).sum()
            print(f"size {a.shape[1]}x{a.shape[0]}, mask pixels ref {ma.sum()} new {mb.sum()}, differing {diff} ({100.0 * diff / ma.size:.3f}%)")
        else:
            print(f"size mismatch {a.shape} vs {b.shape}")

    print("\n== spritesheet.png")
    pr, pn = os.path.join(args.ref, "spritesheet.png"), os.path.join(args.new, "spritesheet.png")
    if os.path.exists(pr) and os.path.exists(pn):
        a, b = load_rgba(pr), load_rgba(pn)
        if a.shape != b.shape:
            print(f"size mismatch {a.shape} vs {b.shape}")
        else:
            iou, mean, p99, worst, wc = sheet_stats(a, b, args.cell)
            print(f"alpha IoU {iou:.4f} | opaque RGB error mean {mean:.2f}, p99 {p99:.1f} | worst cell {worst:.2f} at {wc}")
            if args.diff:
                diff_sheet(a, b, args.diff)
                print(f"diff sheet: {args.diff}")
    else:
        print("missing spritesheet in one side")
    return 0


if __name__ == "__main__":
    sys.exit(main())
