#!/usr/bin/env python3
"""Summarise scenarios/perf_stress_bench.json runs (DeSmuME A/B only, never a DS certification).

Usage: python tools/perf_bench_summary.py <result.json> [<baseline result.json>]
Prints per-stage mean over the sampled 60-frame windows, in ms (32.7285 ticks = 1 ms, see note), and the
delta against an optional baseline run.
"""
import json
import sys

TICKS_PER_MS = 32.7285  # profiler timer runs /1024 with Maxmod (walkthroughs/stress-enemies-profiling)
STAGES = ["sh", "blit", "dclr", "en", "proj", "wp", "pl", "sort", "pick", "hud", "bgsub", "bgbot", "cpu"]


def load(path):
    """path: scenario output dir (or its result.json). Reads wNN state_capture events, dropping repeats."""
    import os
    d = path if os.path.isdir(path) else os.path.dirname(path)
    wins, seen = [], set()
    for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
        ev = json.loads(line)
        if ev.get("action") != "state_capture" or not str(ev.get("name", "")).startswith("w"):
            continue
        st = ev["state"]
        key = tuple(st.get(k) for k in STAGES + ["frame"])
        if key in seen:
            continue
        seen.add(key)
        wins.append(st)
    if not wins:
        raise SystemExit(f"no wNN samples in {d}")
    out = {}
    for st in STAGES + ["fps10", "alive", "frame"]:
        vals = [w[st] for w in wins if st in w]
        out[st] = sum(vals) / len(vals) if vals else 0.0
    out["cpu_max_win"] = max(w["cpu"] for w in wins)
    # Per-stage peak over all sampled windows (fields "<stage>_max"; absent in older results).
    for st in STAGES:
        vals = [w[st + "_max"] for w in wins if st + "_max" in w]
        out[st + "_max"] = max(vals) if vals else None
    out["n"] = len(wins)
    return out


def main():
    cur = load(sys.argv[1])
    base = load(sys.argv[2]) if len(sys.argv) > 2 else None
    print(f"windows={cur['n']} alive~{cur['alive']:.0f} fps(emu)={cur['fps10'] / 10:.1f}"
          + (f" (base {base['fps10'] / 10:.1f})" if base else ""))
    has_max = cur.get("cpu_max") is not None
    print(f"{'stage':7} {'ms':>7}" + (f" {'base':>7} {'delta':>7}" if base else "") + (f" {'max':>7}" + (f" {'bmax':>7}" if base else "") if has_max else ""))
    for st in STAGES:
        ms = cur[st] / TICKS_PER_MS
        line = f"{st:7} {ms:7.2f}"
        if base:
            b = base[st] / TICKS_PER_MS
            line += f" {b:7.2f} {ms - b:+7.2f}"
        if has_max:
            line += f" {cur[st + '_max'] / TICKS_PER_MS:7.2f}"
            if base:
                bm = base.get(st + "_max")
                line += f" {bm / TICKS_PER_MS:7.2f}" if bm is not None else f" {'-':>7}"
        print(line)
    print(f"cpu peak window avg: {cur['cpu_max_win'] / TICKS_PER_MS:.2f} ms")


if __name__ == "__main__":
    main()
