#!/usr/bin/env python3
"""Batch generate all 6 variants for w05 and v04 looks."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAKE = ROOT / "tools/floor/make_proc_floor.py"
PROC = ROOT / "assets/models/environment/floor_proc"


def main():
    looks = ["w05", "v04"]
    variants = list(range(6))
    total = len(looks) * len(variants)
    count = 0

    print(f"=== Starting batch generation of {total} GLB models ===")
    start_time = time.time()

    for look in looks:
        for v in variants:
            count += 1
            glb = PROC / f"floor_band_{look}_v{v}.glb"
            print(f"\n[{count}/{total}] Generating {look.upper()} variant {v} -> {glb.name}...")
            t0 = time.time()
            cmd = [sys.executable, str(MAKE), "--look", look, "--variant", str(v)]
            res = subprocess.run(cmd, cwd=ROOT)
            if res.returncode != 0:
                print(f"FAILED on {look} v{v} with exit code {res.returncode}")
                sys.exit(res.returncode)
            elapsed = time.time() - t0
            print(f"  Done in {elapsed:.1f}s")

    total_time = time.time() - start_time
    print(f"\n=== All {total} models generated successfully in {total_time:.1f}s ===")


if __name__ == "__main__":
    main()
