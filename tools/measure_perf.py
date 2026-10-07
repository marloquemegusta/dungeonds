#!/usr/bin/env python3
"""Deterministic performance profiler for DungeonDS using DeSmuME ABI."""

import ctypes
import json
import os
import sys
from pathlib import Path

BUTTON_BITS = {
    "A": 1 << 0,
    "B": 1 << 1,
    "SELECT": 1 << 2,
    "START": 1 << 3,
    "RIGHT": 1 << 4,
    "LEFT": 1 << 5,
    "UP": 1 << 6,
    "DOWN": 1 << 7,
    "R": 1 << 8,
    "L": 1 << 9,
    "X": 1 << 10,
    "Y": 1 << 11,
}

def configure(lib):
    lib.desmume_init.restype = ctypes.c_int
    lib.desmume_open.argtypes = [ctypes.c_char_p]
    lib.desmume_open.restype = ctypes.c_int
    lib.desmume_resume.argtypes = []
    lib.desmume_cycle.argtypes = [ctypes.c_int]
    lib.desmume_input_keypad_update.argtypes = [ctypes.c_uint16]
    lib.desmume_free.argtypes = []
    lib.desmume_memory_read_long.argtypes = [ctypes.c_uint32]
    lib.desmume_memory_read_long.restype = ctypes.c_uint32

def read_perf(lib, addr):
    magic = lib.desmume_memory_read_long(addr)
    if magic != 0x50455246:
        return None
    return {
        "frame": lib.desmume_memory_read_long(addr + 4),
        "cpu_ticks": lib.desmume_memory_read_long(addr + 8),
        "cpu_budget": lib.desmume_memory_read_long(addr + 12),
        "cpu_percent": lib.desmume_memory_read_long(addr + 16),
        "vcount": lib.desmume_memory_read_long(addr + 20),
        "vblanks": lib.desmume_memory_read_long(addr + 24),
        "fps": lib.desmume_memory_read_long(addr + 28),
        "logic_ticks": lib.desmume_memory_read_long(addr + 32),
        "top_render_ticks": lib.desmume_memory_read_long(addr + 36),
        "bot_render_ticks": lib.desmume_memory_read_long(addr + 40),
        "present_ticks": lib.desmume_memory_read_long(addr + 44),
        "floor_ticks": lib.desmume_memory_read_long(addr + 48),
        "shadow_ticks": lib.desmume_memory_read_long(addr + 52),
        "blit_ticks": lib.desmume_memory_read_long(addr + 56),
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: measure_perf.py ROM.nds LIBDESMUME.so [PERF_ADDR_HEX]", file=sys.stderr)
        return 2

    rom = Path(sys.argv[1])
    lib_path = Path(sys.argv[2])
    perf_addr = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x02199224

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("ALSOFT_DRIVERS", "null")

    lib = ctypes.CDLL(str(lib_path))
    configure(lib)
    if lib.desmume_init() != 0 or lib.desmume_open(str(rom).encode()) != 1:
        raise RuntimeError("DeSmuME failed to initialize or open ROM")
    lib.desmume_resume()

    records = []

    # Scenario sequence of 240 frames total:
    # 1. 30 frames idle (Hero)
    # 2. 60 frames walking UP/RIGHT (Hero)
    # 3. 2 frames switch button (X), 8 frames settling
    # 4. 60 frames sprinting DOWN/LEFT (Charger)
    # 5. 2 frames switch button (X), 8 frames settling
    # 6. 70 frames free walking in various directions
    script = [
        (30, 0, "Idle (Hero)"),
        (60, BUTTON_BITS["UP"] | BUTTON_BITS["RIGHT"], "Walking NE (Hero)"),
        (2, BUTTON_BITS["X"], "Press X (Switch to Charger)"),
        (8, 0, "Post-Switch Idle (Charger)"),
        (60, BUTTON_BITS["DOWN"] | BUTTON_BITS["LEFT"], "Charging SW (Charger)"),
        (2, BUTTON_BITS["X"], "Press X (Switch to Hero)"),
        (8, 0, "Post-Switch Idle (Hero)"),
        (70, BUTTON_BITS["DOWN"], "Walking South (Hero)")
    ]

    try:
        # Initial boot warmup frames
        for _ in range(5):
            lib.desmume_cycle(0)

        for frames, keypad, phase_name in script:
            lib.desmume_input_keypad_update(keypad)
            for f in range(frames):
                lib.desmume_cycle(0)
                perf = read_perf(lib, perf_addr)
                if perf:
                    perf["phase"] = phase_name
                    records.append(perf)
    finally:
        lib.desmume_free()

    if not records:
        print("[ERROR] No perf records captured! Magic mismatch or invalid address.")
        return 1

    total_frames = len(records)
    frames_at_60 = sum(1 for r in records if r["fps"] == 60 and r["vblanks"] == 1)
    frames_dropped = total_frames - frames_at_60

    cpu_percents = [r["cpu_percent"] for r in records]
    cpu_ticks = [r["cpu_ticks"] for r in records]
    vcounts = [r["vcount"] for r in records]
    top_ticks = [r["top_render_ticks"] for r in records]
    bot_ticks = [r["bot_render_ticks"] for r in records]
    present_ticks = [r["present_ticks"] for r in records]

    floor_ticks = [r["floor_ticks"] for r in records]
    shadow_ticks = [r["shadow_ticks"] for r in records]
    blit_ticks = [r["blit_ticks"] for r in records]

    # Convert ticks to microseconds (33.514 MHz: 1 tick = 1000000 / 33513982 = 0.029838 us)
    tick_to_us = 1000000.0 / 33513982.0

    print("=================================================================")
    print(f"  DungeonDS PERFORMANCE BENCHMARK REPORT ({total_frames} frames)")
    print("=================================================================")
    print(f"Total simulated frames : {total_frames}")
    print(f"Frames running at 60 FPS: {frames_at_60} / {total_frames} ({frames_at_60*100.0/total_frames:.1f}%)")
    print(f"Frames dropped (<60 FPS): {frames_dropped}")
    print("-----------------------------------------------------------------")
    print("CPU Load Metrics (% of 60 FPS frame budget [16.71 ms / 560,190 cyc]):")
    print(f"  Average CPU Load : {sum(cpu_percents)/len(cpu_percents):.2f}% ({sum(cpu_ticks)/len(cpu_ticks)*tick_to_us:.1f} us)")
    print(f"  Min CPU Load     : {min(cpu_percents)}% ({min(cpu_ticks)*tick_to_us:.1f} us)")
    print(f"  Max CPU Load     : {max(cpu_percents)}% ({max(cpu_ticks)*tick_to_us:.1f} us)")
    print("-----------------------------------------------------------------")
    print("Raster Scanline when CPU Rendering finished (Display: 0-191, VBlank: 192-262):")
    print(f"  Average VCount   : line {sum(vcounts)/len(vcounts):.1f} / 262")
    print(f"  Max VCount line  : line {max(vcounts)} / 262")
    print("-----------------------------------------------------------------")
    print("Subsystem Breakdown (Average per frame across both screens):")
    print(f"  Floor Window Copy  : {sum(floor_ticks)/len(floor_ticks)*tick_to_us:8.1f} us ({sum(floor_ticks)*100.0/sum(cpu_ticks):4.1f}% of frame CPU)")
    print(f"  Shadow Mask Blit   : {sum(shadow_ticks)/len(shadow_ticks)*tick_to_us:8.1f} us ({sum(shadow_ticks)*100.0/sum(cpu_ticks):4.1f}% of frame CPU)")
    print(f"  Sprites / Objects  : {sum(blit_ticks)/len(blit_ticks)*tick_to_us:8.1f} us ({sum(blit_ticks)*100.0/sum(cpu_ticks):4.1f}% of frame CPU)")
    print(f"  DMA & Present Wait : {sum(present_ticks)/len(present_ticks)*tick_to_us:8.1f} us")
    print("-----------------------------------------------------------------")
    print("Screens Comparison (Average per frame):")
    print(f"  Top Screen Render  : {sum(top_ticks)/len(top_ticks)*tick_to_us:8.1f} us ({sum(top_ticks)*100.0/sum(cpu_ticks):4.1f}% of frame CPU)")
    print(f"  Bot Screen Render  : {sum(bot_ticks)/len(bot_ticks)*tick_to_us:8.1f} us ({sum(bot_ticks)*100.0/sum(cpu_ticks):4.1f}% of frame CPU)")
    print("-----------------------------------------------------------------")
    print("Metrics by Gameplay Phase:")
    phases = {}
    for r in records:
        phases.setdefault(r["phase"], []).append(r)
    for p_name, p_recs in phases.items():
        avg_cpu = sum(r["cpu_percent"] for r in p_recs) / len(p_recs)
        max_cpu = max(r["cpu_percent"] for r in p_recs)
        all_60 = all(r["fps"] == 60 for r in p_recs)
        print(f"  [{p_name:<30}] FPS: {'60' if all_60 else 'DROPPED'} | Avg CPU: {avg_cpu:4.1f}% | Peak CPU: {max_cpu:3d}%")
    print("=================================================================")

    # Dump json summary
    summary = {
        "total_frames": total_frames,
        "frames_at_60": frames_at_60,
        "fps_stable_60": (frames_dropped == 0),
        "avg_cpu_percent": round(sum(cpu_percents)/len(cpu_percents), 2),
        "max_cpu_percent": max(cpu_percents),
        "min_cpu_percent": min(cpu_percents),
        "avg_vcount": round(sum(vcounts)/len(vcounts), 1),
        "max_vcount": max(vcounts),
    }
    Path("build/perf_summary.json").write_text(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
