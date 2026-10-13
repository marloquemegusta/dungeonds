#!/usr/bin/env python3
"""Restore charger contour pixels removed during WH40K sprite harmonization."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "player_sprite.c"
BASE_REF = "d793f6c"
FRAME_RE = re.compile(r"(// Frame \d+\s*\{)(.*?)(\s*\})", re.S)
PIXEL_RE = re.compile(r"0x[0-9A-Fa-f]{4}")


def charger_frames(text: str) -> tuple[int, int, list[re.Match[str]]]:
    start = text.index("const uint16_t g_charger_frames")
    end = text.index("const uint8_t g_charger_shadow_masks", start)
    section = text[start:end]
    frames = list(FRAME_RE.finditer(section))
    if len(frames) != 64 or any(len(PIXEL_RE.findall(frame.group(2))) != 48 * 40 for frame in frames):
        raise ValueError("Unexpected charger sprite layout")
    return start, end, frames


def warm_bgr555(pixel: int) -> int:
    r = pixel & 0x1F
    g = (pixel >> 5) & 0x1F
    b = (pixel >> 10) & 0x1F
    r = min(31, (r * 23) // 20 + 3)
    g = min(31, (g * 23) // 20 + 3)
    b = min(31, (b * 22) // 20 + 2)
    return 0x8000 | r | (g << 5) | (b << 10)


def main() -> None:
    with SOURCE.open("r", encoding="utf-8", newline="") as handle:
        current = handle.read()
    baseline = subprocess.run(
        ["git", "show", f"{BASE_REF}:source/player_sprite.c"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    start, end, current_frames = charger_frames(current)
    _, _, baseline_frames = charger_frames(baseline)
    section = current[start:end]
    restored = 0
    replacements = []
    for current_frame, baseline_frame in zip(current_frames, baseline_frames, strict=True):
        current_pixels = [int(x, 16) for x in PIXEL_RE.findall(current_frame.group(2))]
        baseline_pixels = [int(x, 16) for x in PIXEL_RE.findall(baseline_frame.group(2))]
        values = []
        for pixel, original in zip(current_pixels, baseline_pixels, strict=True):
            if not (pixel & 0x8000) and (original & 0x8000):
                pixel = warm_bgr555(original)
                restored += 1
            values.append(pixel)
        tokens = iter(f"0x{value:04X}" for value in values)
        body = PIXEL_RE.sub(lambda _: next(tokens), current_frame.group(2))
        replacements.append((current_frame.span(), current_frame.group(1) + body + current_frame.group(3)))

    for (begin, finish), replacement in reversed(replacements):
        section = section[:begin] + replacement + section[finish:]
    with SOURCE.open("w", encoding="utf-8", newline="") as handle:
        handle.write(current[:start] + section + current[end:])
    print(f"CHARGER_CONTOUR_RESTORED={restored}")


if __name__ == "__main__":
    main()
