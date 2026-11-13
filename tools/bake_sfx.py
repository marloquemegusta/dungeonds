#!/usr/bin/env python3
"""Bake 16.384 Hz mono WAVs in assets/sfx/baked/ into C 8-bit PCM arrays."""

import os
import wave
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKED_DIR = os.path.join(REPO_ROOT, "assets", "sfx", "baked")
OUT_H = os.path.join(REPO_ROOT, "include", "sfx_bank.h")
OUT_C = os.path.join(REPO_ROOT, "source", "sfx_bank.c")

SFX_ORDER = [
    ("SFX_HEART_CHARGE", "heart_charge.wav"),
    ("SFX_HEART_FIRE", "heart_fire.wav"),
    ("SFX_ENEMY_HIT", "enemy_hit.wav"),
    ("SFX_ENEMY_DEATH", "enemy_death.wav"),
    ("SFX_PLAYER_HURT", "player_hurt.wav"),
]

TARGET_SR = 16384
MAX_TOTAL_BYTES = 64 * 1024  # 64 KB hard budget for base SFX


def load_pcm8(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sr != TARGET_SR:
        raise ValueError(f"{path}: expected {TARGET_SR} Hz, got {sr} Hz")
    if ch != 1 or sw != 2:
        raise ValueError(f"{path}: expected mono 16-bit WAV, got ch={ch} sw={sw}")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    pcm8 = np.clip(np.round(x * 127.0), -127, 127).astype(np.int8)
    return pcm8


def main():
    clips = []
    total_bytes = 0
    for enum_name, fname in SFX_ORDER:
        path = os.path.join(BAKED_DIR, fname)
        pcm8 = load_pcm8(path)
        total_bytes += len(pcm8)
        clips.append((enum_name, fname, pcm8))

    if total_bytes > MAX_TOTAL_BYTES:
        raise RuntimeError(f"SFX bank {total_bytes} bytes exceeds {MAX_TOTAL_BYTES} byte budget")

    h_lines = [
        "#ifndef SFX_BANK_H",
        "#define SFX_BANK_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define SFX_SAMPLE_RATE {TARGET_SR}",
        "",
        "typedef enum {",
    ]
    for enum_name, _, _ in clips:
        h_lines.append(f"    {enum_name},")
    h_lines.extend([
        "    SFX_COUNT",
        "} SfxId;",
        "",
        "typedef struct {",
        "    const int8_t *data;",
        "    uint32_t length;",
        "} SfxClip;",
        "",
        "extern const SfxClip g_sfx_bank[SFX_COUNT];",
        "",
        "#endif /* SFX_BANK_H */",
        "",
    ])

    c_lines = [
        '#include "sfx_bank.h"',
        "",
    ]
    for enum_name, fname, pcm8 in clips:
        sym = f"s_pcm_{enum_name.lower()}"
        c_lines.append(f"/* {fname}: {len(pcm8)} bytes ({len(pcm8) * 1000 // TARGET_SR} ms) */")
        c_lines.append(f"static const int8_t {sym}[] __attribute__((aligned(4))) = {{")
        vals = [str(int(v)) for v in pcm8]
        for i in range(0, len(vals), 16):
            c_lines.append("    " + ", ".join(vals[i : i + 16]) + ",")
        c_lines.append("};")
        c_lines.append("")

    c_lines.append("const SfxClip g_sfx_bank[SFX_COUNT] = {")
    for enum_name, _, pcm8 in clips:
        sym = f"s_pcm_{enum_name.lower()}"
        c_lines.append(f"    [{enum_name}] = {{ {sym}, {len(pcm8)}u }},")
    c_lines.append("};")
    c_lines.append("")

    with open(OUT_H, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(h_lines))
    with open(OUT_C, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(c_lines))

    print(f"Baked {len(clips)} SFX -> {total_bytes} bytes ({total_bytes / 1024.0:.1f} KB)")


if __name__ == "__main__":
    main()
