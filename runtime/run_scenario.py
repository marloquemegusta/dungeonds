#!/usr/bin/env python3
"""Run deterministic DS input scenarios against the headless DeSmuME ABI."""

import ctypes
import hashlib
import json
import os
import struct
import sys
import zlib
from pathlib import Path


WIDTH = 256
HEIGHT = 384
RGB_SIZE = WIDTH * HEIGHT * 3
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
    "TOUCH": 1 << 12,
}


def png_bytes(rgb: bytes) -> bytes:
    rows = b"".join(b"\x00" + rgb[y * WIDTH * 3:(y + 1) * WIDTH * 3] for y in range(HEIGHT))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def configure(lib):
    lib.desmume_init.restype = ctypes.c_int
    lib.desmume_open.argtypes = [ctypes.c_char_p]
    lib.desmume_open.restype = ctypes.c_int
    lib.desmume_resume.argtypes = []
    lib.desmume_cycle.argtypes = [ctypes.c_int]
    lib.desmume_screenshot.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
    lib.desmume_input_set_touch_pos.argtypes = [ctypes.c_uint16, ctypes.c_uint16]
    lib.desmume_input_release_touch.argtypes = []
    lib.desmume_input_keypad_update.argtypes = [ctypes.c_uint16]
    lib.desmume_input_keypad_get.restype = ctypes.c_uint16
    lib.desmume_memory_read_long.argtypes = [ctypes.c_uint32]
    lib.desmume_memory_read_long.restype = ctypes.c_uint32
    lib.desmume_free.argtypes = []


def map_symbol_address(map_path: Path, symbol: str) -> int:
    """Resolve a linked BSS symbol from the BlocksDS GNU ld map."""
    sections = {f".{kind}.{symbol}" for kind in ("bss", "data", "rodata")}
    lines = map_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.split()[0:1] and line.split()[0] in sections:
            fields = line.split()
            if len(fields) >= 2 and fields[1].startswith("0x"):
                return int(fields[1], 16)
        if not line.split() or line.split()[0] not in sections:
            continue
        fields = line.split()
        if len(fields) >= 2 and fields[1].startswith("0x"):
            return int(fields[1], 16)
        if index + 1 < len(lines):
            fields = lines[index + 1].split()
            if fields and fields[0].startswith("0x"):
                return int(fields[0], 16)
    raise ValueError(f"BSS symbol {symbol!r} not found in {map_path}")


def read_state(lib, bases: dict, fields: dict, default_symbol: str) -> dict:
    values = {}
    for name, spec in fields.items():
        if isinstance(spec, dict):
            symbol, offset = spec["symbol"], spec["offset"]
        else:
            symbol, offset = default_symbol, spec
        value = int(lib.desmume_memory_read_long(bases[symbol] + int(offset)))
        values[name] = value - 0x100000000 if value & 0x80000000 else value
    return values


def check_state_assertion(samples: dict, assertion: dict) -> dict:
    before = samples[assertion["from"]][assertion["field"]]
    after = samples[assertion["to"]][assertion["field"]]
    delta = after - before
    if "min_abs_delta" in assertion:
        passed = abs(delta) >= int(assertion["min_abs_delta"])
    elif "min_delta" in assertion:
        passed = delta >= int(assertion["min_delta"])
    elif "max_delta" in assertion:
        passed = delta <= int(assertion["max_delta"])
    elif "max_abs_delta" in assertion:
        passed = abs(delta) <= int(assertion["max_abs_delta"])
    elif "equals" in assertion:
        passed = after == int(assertion["equals"])
    elif "min_value" in assertion:
        passed = after >= int(assertion["min_value"])
    elif "max_value" in assertion:
        passed = after <= int(assertion["max_value"])
    else:
        raise ValueError(f"unsupported state assertion: {assertion}")
    return {"from": assertion["from"], "to": assertion["to"],
            "field": assertion["field"], "before": before, "after": after,
            "delta": delta, "passed": passed}


def set_button(lib, keypad: int, name: str, pressed: bool) -> int:
    try:
        bit = BUTTON_BITS[name.upper()]
    except KeyError as error:
        raise ValueError(f"unknown button: {name}") from error
    keypad = keypad | bit if pressed else keypad & ~bit
    lib.desmume_input_keypad_update(keypad)
    return keypad


def capture(lib, path: Path) -> tuple[str, bytes]:
    raw = (ctypes.c_ubyte * RGB_SIZE)()
    lib.desmume_screenshot(raw)
    rgb = bytes(raw)
    path.write_bytes(png_bytes(rgb))
    return hashlib.sha256(rgb).hexdigest(), rgb


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: run_scenario.py ROM.nds SCENARIO.json OUTPUT_DIR LIBRARY.so", file=sys.stderr)
        return 2
    rom = Path(sys.argv[1])
    scenario_path = Path(sys.argv[2])
    output = Path(sys.argv[3])
    lib_path = Path(sys.argv[4])
    scenario = json.loads(scenario_path.read_text(encoding="utf-8-sig"))
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("ALSOFT_DRIVERS", "null")
    lib = ctypes.CDLL(str(lib_path))
    configure(lib)
    if lib.desmume_init() != 0 or lib.desmume_open(str(rom).encode()) != 1:
        raise RuntimeError("DeSmuME failed to initialize or open ROM")
    lib.desmume_resume()

    events = []
    captures = {}
    capture_pixels = {}
    state_samples = {}
    state_config = scenario.get("state")
    if state_config:
        map_path = (scenario_path.parent.parent / state_config["map_path"]
                    if "map_path" in state_config else
                    scenario_path.parent.parent / ".ds-game-dev" / "build" / "build" / "game-blocksds.map")
        symbols = state_config["symbols"] if "symbols" in state_config else {"state": state_config["symbol"]}
        state_bases = {name: map_symbol_address(map_path, symbol) for name, symbol in symbols.items()}
        default_symbol = state_config.get("default_symbol", "state")
    keypad = 0
    try:
        for index, step in enumerate(scenario["steps"]):
            if "button_down" in step:
                keypad = set_button(lib, keypad, step["button_down"], True)
                events.append({"step": index, "action": "button_down", "button": step["button_down"]})
            if "button_up" in step:
                keypad = set_button(lib, keypad, step["button_up"], False)
                # DeSmuME keeps the previous keypad state until it has seen a
                # complete frame with the released mask. Materialize that
                # release before the step's normal frame budget so chord
                # guards in the ROM (notably sandbox entry) can observe it.
                for _ in range(4):
                    lib.desmume_input_keypad_update(0)
                    lib.desmume_cycle(0)
                events.append({"step": index, "action": "button_up", "button": step["button_up"]})
            if "tap" in step or "touch" in step:
                point = step.get("tap") or step.get("touch")
                lib.desmume_input_set_touch_pos(point["x"], point["y"])
                keypad |= BUTTON_BITS["TOUCH"]
                lib.desmume_input_keypad_update(keypad)
                events.append({"step": index, "action": "tap", "x": point["x"], "y": point["y"]})
            if "spawn_batch" in step:
                batch = step["spawn_batch"]
                count = max(0, int(batch["count"]))
                columns = max(1, int(batch.get("columns", 1)))
                start_x = int(batch.get("x", 128))
                start_y = int(batch.get("y", 40))
                spacing_x = int(batch.get("spacing_x", 12))
                spacing_y = int(batch.get("spacing_y", 12))
                for spawn_index in range(count):
                    col = spawn_index % columns
                    row = spawn_index // columns
                    x = max(2, min(253, start_x + col * spacing_x))
                    y = max(2, min(143, start_y + row * spacing_y))
                    lib.desmume_input_set_touch_pos(x, y)
                    spawn_keypad = keypad | BUTTON_BITS["R"]
                    for _ in range(2):
                        lib.desmume_input_keypad_update(spawn_keypad)
                        lib.desmume_cycle(0)
                        lib.desmume_input_keypad_update(spawn_keypad)
                    lib.desmume_input_keypad_update(keypad)
                    lib.desmume_input_release_touch()
                    lib.desmume_cycle(0)
                events.append({"step": index, "action": "spawn_batch", "count": count,
                               "columns": columns, "start": {"x": start_x, "y": start_y}})
            if "drag" in step:
                drag = step["drag"]
                start = drag["from"]
                end = drag["to"]
                drag_frames = max(1, int(drag.get("frames", 1)))
                for frame in range(drag_frames):
                    ratio = frame / max(1, drag_frames - 1)
                    x = round(start["x"] + (end["x"] - start["x"]) * ratio)
                    y = round(start["y"] + (end["y"] - start["y"]) * ratio)
                    lib.desmume_input_set_touch_pos(x, y)
                    lib.desmume_cycle(0)
                events.append({"step": index, "action": "drag", "from": start, "to": end,
                               "frames": drag_frames})
            if "release" in step:
                lib.desmume_input_release_touch()
                keypad &= ~BUTTON_BITS["TOUCH"]
                lib.desmume_input_keypad_update(keypad)
                events.append({"step": index, "action": "release"})
            capture_seq = step.get("capture_sequence")
            capture_every = max(1, int(step.get("capture_every", 1)))
            frame_count = step.get("frames", 1)
            if "seq_indices" not in locals():
                seq_indices = {}
            if capture_seq and capture_seq not in seq_indices:
                seq_indices[capture_seq] = 0
            for f in range(frame_count):
                lib.desmume_input_keypad_update(keypad)
                lib.desmume_cycle(0)
                if capture_seq and (f % capture_every == 0):
                    cname = f"{capture_seq}_{seq_indices[capture_seq]:04d}"
                    capture(lib, output / f"{cname}.png")
                    seq_indices[capture_seq] += 1
            events.append({"step": index, "action": "frame_advance", "frames": frame_count,
                           "keypad": int(lib.desmume_input_keypad_get())})
            if "capture" in step:
                name = step["capture"]
                digest, _ = capture(lib, output / f"{name}.png")
                captures[name] = {"sha256": digest, "path": f"{name}.png"}
                capture_pixels[name] = _
            if "state_capture" in step:
                if not state_config:
                    raise ValueError("state_capture requires scenario.state")
                name = step["state_capture"]
                state_samples[name] = read_state(lib, state_bases, state_config["fields"], default_symbol)
                events.append({"step": index, "action": "state_capture", "name": name,
                               "state": state_samples[name]})
    finally:
        lib.desmume_free()

    assertions = scenario["assertions"]
    checks = assertions.get("screen_changes")
    if checks is None:
        checks = [assertions["screen_changed"]] if "screen_changed" in assertions else []
    screen_results = []
    for check in checks:
        first = captures[check["from"]]
        second = captures[check["to"]]
        changed_pixels = sum(a != b for a, b in zip(
            capture_pixels[check["from"]], capture_pixels[check["to"]],
        )) // 3
        min_changed = check.get("min_changed_pixels", 1)
        screen_results.append({
            "from": check["from"], "to": check["to"],
            "changed": first["sha256"] != second["sha256"] and changed_pixels >= min_changed,
            "changed_pixels": changed_pixels, "min_changed_pixels": min_changed,
        })
    changed = all(result["changed"] for result in screen_results)
    state_results = [check_state_assertion(state_samples, check)
                     for check in assertions.get("state_changes", [])]
    state_changed = all(result["passed"] for result in state_results)
    first_result = screen_results[0] if screen_results else None
    assertion_manifest = {"screen_changed": changed,
                          "screen_changes": screen_results,
                          "state_changed": state_changed,
                          "state_changes": state_results,
                          "state_samples": state_samples}
    if first_result:
        assertion_manifest["changed_pixels"] = first_result["changed_pixels"]
        assertion_manifest["min_changed_pixels"] = first_result["min_changed_pixels"]
    manifest = {
        "scenario": scenario_path.name,
        "captures": captures,
        "events": events,
        "assertions": assertion_manifest,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with (output / "events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    if not changed or not state_changed:
        print("DSM_SCENARIO_RESULT=FAIL reason=assertion_failed", flush=True)
        return 1
    print(f"DSM_SCENARIO_RESULT=PASS captures={len(captures)} events={len(events)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
