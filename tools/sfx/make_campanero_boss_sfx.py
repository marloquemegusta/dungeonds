#!/usr/bin/env python3
"""Builds the Campanero boss sounds (intro and defeat) from the free bank already in assets/sfx/baked/.
Host tool (numpy float is fine here). Output: 16.384 Hz mono 16-bit WAV in assets/sfx/baked/.
After running, run tools/gen_voice_lengths.py to refresh include/sfx_voice_len.h."""
import os
import wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAKED = os.path.join(ROOT, "assets", "sfx", "baked")
SR = 16384


def load(name):
    with wave.open(os.path.join(BAKED, name + ".wav"), "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0


def pitch(x, ratio):
    """Resample: ratio < 1 is lower and longer."""
    n = int(len(x) / ratio)
    return np.interp(np.arange(n) * ratio, np.arange(len(x)), x)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")


def fade_tail(x, secs):
    n = min(len(x), int(secs * SR))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n) ** 2
    return x


def place(mix, x, t, gain=1.0):
    i = int(t * SR)
    end = min(len(mix), i + len(x))
    mix[i:end] += x[: end - i] * gain


def save(name, x):
    x = x / max(1e-9, np.max(np.abs(x))) * 0.9
    pcm = np.round(x * 32767).astype(np.int16)
    with wave.open(os.path.join(BAKED, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(name, len(pcm), "samples", round(len(pcm) / SR, 2), "s")


bong, h0, h2 = load("lab_bong"), load("lab_bell_h0"), load("lab_bell_h2")
creak, g1, g4 = load("lab_creak"), load("lab_glass1"), load("lab_glass4")


def intro():
    m = np.zeros(int(2.8 * SR))
    # 1) deep toll: bell an octave and a bit down + the body thump
    place(m, pitch(h0, 0.62), 0.0, 0.9)
    place(m, pitch(bong, 0.5), 0.0, 0.8)
    # 2) second toll that cracks: two copies slightly detuned beat against each other, plus a glass fleck
    place(m, pitch(h2, 0.66), 1.0, 0.8)
    place(m, pitch(h2, 0.60), 1.02, 0.7)
    place(m, lowpass(pitch(g1, 0.8), 3), 1.05, 0.25)
    # 3) dragging creak, muffled, under the dying hum
    place(m, lowpass(pitch(creak, 0.55), 5), 1.7, 0.7)
    return fade_tail(m, 0.5)


def defeat():
    m = np.zeros(int(2.6 * SR))
    # toll that breaks: one last heavy stroke...
    place(m, pitch(h0, 0.55), 0.0, 0.9)
    place(m, pitch(bong, 0.45), 0.0, 0.8)
    # ...shards of glass falling as the crack runs through it
    place(m, pitch(g4, 0.85), 0.55, 0.55)
    place(m, pitch(g1, 1.1), 0.75, 0.45)
    place(m, pitch(g1, 0.9), 1.0, 0.3)
    # decaying hum: the bell tail dropped very low and smoothed
    hum = lowpass(pitch(h0, 0.4), 4)
    hum = hum * np.linspace(1, 0, len(hum)) ** 1.5
    place(m, hum, 0.6, 0.6)
    return fade_tail(m, 0.8)


save("campanero_intro", intro())
save("campanero_derrota", defeat())
