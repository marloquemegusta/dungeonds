#!/usr/bin/env python3
"""Level-up card art taken from the game itself (DESIGN.md 6.12.8, "Pantalla de elección").

For each of the 17 upgrades a short staged scene runs on the cathedral-sandbox ROM (hero + the effect + only the
enemies it needs; AI frozen, god mode), 16 bottom-screen frames are captured, cropped, enlarged to 76x76, quantised to
one palette per card and packed into nitrofiles/levelup/<id>.bin.

  python tools/levelup_cards/capture_cards.py [--variant 0|1|2] [--only id ...] [--skip-run] [--jobs N]

  stage 1 (run):   scenarios/_cards/<id>.json  ->  .ds-game-dev/card_runs/<id>/c*.png   (needs the sandbox ROM:
                   build-project.ps1 -Variant cathedral-sandbox; --skip-run reuses the frames of the last run)
  stage 2 (crop):  assets/sprites/levelup/ingame/<id>/fNN.png, contact_ingame.png, anim_ingame.gif, then pack_cards.

Frames are sampled with a per-segment cadence (every 4-6 game frames while charging, every frame around the shot) and
played back at 15 fps on the card (menu.c), so the shot reads in slow motion and the whole loop lasts ~1 s.
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import abc_scenes as A                                   # noqa: E402  (staging helpers of the A/B/C review)

SKILL = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts\run-scenario.ps1")
ROM = ROOT / "dungeonds-cathedral-sandbox.nds"
RUNS = ROOT / ".ds-game-dev" / "card_runs"
SCEN = ROOT / "scenarios" / "_cards"
OUT = ROOT / "assets" / "sprites" / "levelup" / "ingame"
NITRO = ROOT / "nitrofiles" / "levelup"
FRAMES = 16
SIZE = 76
BOTTOM_Y = 192
HX, HY = A.HX, A.HY
EX, MO = A.EXVOTO, A.MONAGUILLO
RELIC = A.RELIC
DON = dict(FERVOR=0, PRISA=1, ALCANCE=2, BRASA=3, RESCOLDO=4, PASO=5, VIDA=6)

# Design variant chosen per element in the A/B/C review (DESIGN.md 6.12.12); it overrides --variant for these cards so the
# art on the card is the chosen look. --no-chosen disables it (then --variant applies to every card).
CHOSEN = {"brasa": 0, "rescoldo": 0, "llama_votiva": 1, "flagelado": 0, "martirio": 0, "auto_de_fe": 0,
          "llaga_abierta": 1, "viatico": 0}
USE_CHOSEN = True

ALL = ["fervor", "prisa", "alcance", "brasa", "rescoldo", "paso", "vida", "sed_ceniza", "lanza_longinos", "auto_de_fe",
       "llama_votiva", "aura_cilicio", "paso_procesion", "martirio", "flagelado", "llaga_abierta", "viatico"]

# Crop window on the bottom screen: (x, y, window). The window is scaled to 76x76 (38 -> 2x NEAREST, 76 -> 1x).
# The hero stands at (128, 133) feet in every scene, muzzle row at y 112.
CLOSE = (109, 90, 38)                    # hero-centred 2x: auras, walking, cues around the body
BEAM = (104, 66, 76)                     # 1x, hero on the left, the beam row to the right
CROPS = {
    "fervor": BEAM, "prisa": BEAM, "alcance": (104, 56, 114), "brasa": (132, 66, 76), "rescoldo": (132, 66, 76),
    "paso": CLOSE, "vida": "vida", "sed_ceniza": BEAM, "lanza_longinos": BEAM, "auto_de_fe": BEAM,
    "llama_votiva": BEAM, "aura_cilicio": (90, 66, 76), "paso_procesion": CLOSE, "martirio": (136, 76, 76),
    "flagelado": (90, 66, 76), "llaga_abierta": BEAM, "viatico": (90, 66, 76),
}


def seg(frames, every, **action):   # every=None: advance without capturing
    return dict(frames=frames, every=every, action=action)


def charge_shot(target, hold, shot=6, post_every=6, y=HY, shot_every=1, hold_every=4):
    """Tap, hold `hold` frames, release; then `shot` frames at 1/frame; the rest of the 16 captures at post_every."""
    segs = [seg(hold, hold_every, tap=A.touch(target, y)), seg(shot, shot_every, release=True)]
    used = hold // hold_every + shot // shot_every
    segs.append(seg((FRAMES - used) * post_every, post_every))
    return segs


def build_scene(cid):
    """-> dict(relics, dones, enemies, hp, extra, segs)."""
    en3 = [(EX, 230, HY), (MO, 254, HY), (EX, 278, HY)]
    d = dict(relics=0, dones={}, enemies=[], hp=None, extra=[], segs=[])
    if cid == "fervor":
        d.update(dones=dict(FERVOR=4), enemies=[(EX, 244, HY)], extra=A.pokes(en0_hp=250))
        d["segs"] = charge_shot(244, 28, shot=6, post_every=5)
    elif cid == "prisa":
        d.update(dones=dict(PRISA=4), enemies=en3, extra=A.tough(3))
        # one 16-frame cycle = shortened charge (8 frames) + shot + cooldown: three shots in the loop
        segs = []
        for _ in range(3):
            segs += [seg(4, 4, tap=A.touch(254)), seg(4, 4), seg(2, 1, release=True), seg(6, 6)]
        d["segs"] = segs + [seg(4, 4)]
    elif cid == "alcance":
        d.update(dones=dict(ALCANCE=4), enemies=[(EX, 280, HY)], extra=A.tough(1))
        d["segs"] = charge_shot(280, 28, shot=6, post_every=5)
    elif cid == "brasa":
        # low hp so the fire (x2 at rank 4) burns them down inside the loop
        d.update(dones=dict(BRASA=4), enemies=[(EX, 226, 1750), (MO, 252, HY), (EX, 226, 1774)],
                 extra=A.pokes(en0_hp=40, en0_burn=3, en0_timer=900, en1_hp=52, en1_burn=3, en1_timer=900,
                               en2_hp=46, en2_burn=3, en2_timer=900))
        d["segs"] = [seg(FRAMES * 4, 4)]
    elif cid == "rescoldo":
        d.update(dones=dict(RESCOLDO=4), enemies=[(EX, 226, 1750), (MO, 252, HY), (EX, 226, 1774)],
                 extra=A.tough(3, layers=(9, 8, 9)))
        d["segs"] = [seg(FRAMES * 4, 4)]
    elif cid == "paso":
        d.update(dones=dict(PASO=4))
        d["segs"] = [seg(14, None, button_down="LEFT"), seg(FRAMES * 3, 3)]
    elif cid == "vida":
        d.update(dones=dict(VIDA=4), hp=3)
        d["segs"] = [
            seg(2, 2, poke=A.pokes(hp=1)), seg(4, 2, poke=A.pokes(hp=2)), seg(4, 2, poke=A.pokes(hp=3)),
            seg(4, 2, poke=A.pokes(hp=4)), seg(4, 2, poke=A.pokes(hp=5)), seg(14, 2)]
    elif cid == "sed_ceniza":
        d.update(relics=RELIC["SED_CENIZA"], enemies=[(EX, 230, HY), (MO, 250, HY), (EX, 270, HY)])
        d["segs"] = [seg(20, 4, tap=A.touch(230)), seg(3, 1, release=True), seg(4, 4), seg(12, 4, tap=A.touch(250)),
                     seg(2, 1, release=True), seg(12, 6)]
    elif cid == "lanza_longinos":
        d.update(relics=RELIC["LANZA"], enemies=[(EX, 230, HY), (MO, 252, HY), (EX, 274, HY), (MO, 296, HY)],
                 extra=A.tough(4))
        d["segs"] = charge_shot(262, 28, shot=7, post_every=5)
    elif cid == "auto_de_fe":
        d.update(relics=RELIC["AUTO_FE"], enemies=[(EX, 232, HY), (MO, 262, HY)], extra=A.tough(2, burn=4))
        d["segs"] = charge_shot(232, 28, shot=7, post_every=5)
    elif cid == "llama_votiva":
        d.update(relics=RELIC["LLAMA_VOTIVA"], enemies=en3, extra=A.tough(3))
        d["segs"] = [seg(FRAMES * 3, 3, tap=A.touch(292))]
    elif cid == "aura_cilicio":
        d.update(relics=RELIC["CILICIO"], enemies=[(EX, 224, 1752), (MO, 176, 1768), (EX, 220, 1776)],
                 extra=A.tough(3, burn=3))
        d["segs"] = [seg(FRAMES * 3, 3, tap=A.touch(262))]
    elif cid == "paso_procesion":
        d.update(relics=RELIC["PROCESION"])
        d["segs"] = [seg(FRAMES * 3, 3, tap=A.touch(262), button_down="LEFT")]
    elif cid == "martirio":
        d.update(relics=RELIC["MARTIRIO"], enemies=[(EX, 246, HY), (MO, 232, 1774), (EX, 260, 1774)],
                 extra=A.tough(3)[1:])
        d["segs"] = [seg(4, 4, tap=A.touch(246)), seg(16, 4),
                     seg(6, 2, poke=A.pokes(en0_hp=100, en0_burn=3, en0_timer=900)), seg(2, 1, release=True),
                     seg(5, 1), seg(6, 6)]
    elif cid == "flagelado":
        d.update(relics=RELIC["FLAGELADO"], enemies=[(EX, 160, 1760), (MO, 240, 1760), (EX, 176, 1778), (MO, 224, 1778)],
                 extra=A.tough(4))
        d["segs"] = [seg(2, 2), seg(24, 2, poke=A.pokes(dbg=2)), seg(6, 2)]
    elif cid == "llaga_abierta":
        d.update(relics=RELIC["LLAGA"], enemies=[(EX, 250, HY)], hp=2, extra=A.tough(1))
        d["segs"] = charge_shot(250, 36, shot=7, post_every=5, hold_every=6)
    elif cid == "viatico":
        d.update(relics=RELIC["VIATICO"], enemies=[(EX, 230, 1770), (MO, 172, 1770)], hp=3, extra=A.tough(2))
        d["segs"] = [seg(2, 2), seg(28, 2, poke=A.pokes(dbg=1)), seg(2, 2)]
    else:
        raise KeyError(cid)
    n = sum(s["frames"] // s["every"] for s in d["segs"] if s["every"])
    if n != FRAMES:
        raise ValueError("%s: %d captures planned, need %d" % (cid, n, FRAMES))
    return d


def scenario(cid, variant):
    if USE_CHOSEN:
        variant = CHOSEN.get(cid, variant)
    d = build_scene(cid)
    steps = [{"frames": 30}]
    st = A.stage(variant, d["relics"], d["enemies"], d["hp"], d["extra"])
    if d["dones"]:
        ranks = [{"field": "don%d" % DON[k], "value": v} for k, v in d["dones"].items()]
        st[0]["poke"][-1:-1] = ranks                       # before apply_seq, which commits them
    steps += st
    for i, s in enumerate(d["segs"]):
        step = {"frames": s["frames"]}
        if s["every"]:
            step.update(capture_sequence="c%02d" % i, capture_every=s["every"])
        a = dict(s["action"])
        if "tap" in a:
            step["tap"] = a["tap"]
        if "button_down" in a:
            step["button_down"] = a["button_down"]
        if "poke" in a:
            step["poke"] = a["poke"]
        if "release" in a:
            step["release"] = True
        steps.append(step)
    steps.append({"release": True, "frames": 2})
    fields = dict(A.FIELDS)
    for k, v in DON.items():
        fields["don%d" % v] = {"symbol": "u", "offset": 10 + v, "type": "u8"}
    return {
        "name": "card_" + cid, "suite": False, "evidence_only": True,
        "description": "Staged capture of the '%s' level-up card (tools/levelup_cards/capture_cards.py)." % cid,
        "state": {"symbols": {"sb": "g_sandbox", "u": "g_upg_debug", "p": "g_player_state", "a": "g_abc_debug",
                              "en": "g_enemies"}, "default_symbol": "sb", "fields": fields},
        "steps": steps,
    }


def run_card(cid, variant):
    SCEN.mkdir(parents=True, exist_ok=True)
    path = SCEN / (cid + ".json")
    path.write_text(json.dumps(scenario(cid, variant), indent=1) + "\n", newline="")
    out = RUNS / cid
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SKILL),
           "-ProjectPath", str(ROOT), "-ScenarioPath", str(path), "-RomPath", str(ROM), "-OutputPath", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    ok = "PASS" in r.stdout
    print("%-16s %s" % (cid, "ok" if ok else "FAILED\n" + r.stdout[-800:] + r.stderr[-400:]), flush=True)
    return ok


def captured(cid):
    files = [p for p in (RUNS / cid).glob("c*_*.png") if re.search(r"_\d{4}\.png$", p.name)]
    files.sort(key=lambda p: p.name)
    return files


def crop_frame(path, crop):
    shot = Image.open(path).convert("RGB")
    if crop == "vida":        # HUD hearts (1x) over the hero's chest (2x): both are plain pixels of the same frame
        out = Image.new("RGB", (SIZE, SIZE))
        out.paste(shot.crop((108, BOTTOM_Y + 4, 184, BOTTOM_Y + 26)), (0, 0))
        out.paste(shot.crop((109, BOTTOM_Y + 92, 147, BOTTOM_Y + 119)).resize((SIZE, 54), Image.NEAREST), (0, 22))
        return out
    x, y, w = crop
    im = shot.crop((x, BOTTOM_Y + y, x + w, BOTTOM_Y + y + w))
    if w == SIZE:
        return im
    if SIZE % w == 0:
        return im.resize((SIZE, SIZE), Image.NEAREST)
    return im.resize((SIZE, SIZE), Image.BOX)


def quantise(frames):
    """One <=255-colour palette for the whole card; index 0 stays black (pure black is the only 0)."""
    n = len(frames)
    sheet = Image.new("RGB", (SIZE, SIZE * n))
    for i, f in enumerate(frames):
        sheet.paste(f, (0, i * SIZE))
    # RGB555 first (what the DS shows), then median cut to 255 colours.
    arr = (np.array(sheet) >> 3 << 3).astype(np.uint8)
    sheet = Image.fromarray(arr)
    pal = sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for f in frames:
        a = (np.array(f) >> 3 << 3).astype(np.uint8)
        out.append(Image.fromarray(a).quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB"))
    return out


def vignette(im):
    """Darkens only the outer rim (a few percent) so the effect pops; never touches the middle."""
    a = np.array(im).astype(np.float32)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    d = np.maximum(abs(xx - SIZE / 2), abs(yy - SIZE / 2)) / (SIZE / 2)
    k = 1.0 - 0.25 * np.clip((d - 0.75) / 0.25, 0, 1)
    return Image.fromarray((a * k[..., None]).astype(np.uint8))


def process(cid):
    files = captured(cid)
    if len(files) != FRAMES:
        raise SystemExit("%s: %d captured frames, expected %d" % (cid, len(files), FRAMES))
    frames = [vignette(crop_frame(f, CROPS[cid])) for f in files]
    frames = quantise(frames)
    d = OUT / cid
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("f*.png"):
        f.unlink()
    for i, f in enumerate(frames):
        f.save(d / ("f%02d.png" % i))
    return frames


def pack(cid, frames):
    import struct
    flat = np.stack([np.array(f) for f in frames]).reshape(-1, 3)
    codes = (flat[:, 0].astype(np.uint32) << 16) | (flat[:, 1].astype(np.uint32) << 8) | flat[:, 2]
    uniq = sorted(set(int(c) for c in np.unique(codes)) - {0})
    if len(uniq) > 255:
        raise ValueError("%s: %d colours" % (cid, len(uniq)))
    lut = {0: 0}
    for i, c in enumerate(uniq):
        lut[c] = i + 1
    pal = [0x8000] * 256
    for c, i in lut.items():
        r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
        pal[i] = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) | 0x8000
    idx = np.array([lut[int(c)] for c in codes], dtype=np.uint8)
    data = struct.pack("<H2B", 0x4C43, len(frames), SIZE) + struct.pack("<256H", *pal) + idx.tobytes()
    NITRO.mkdir(parents=True, exist_ok=True)
    (NITRO / (cid + ".bin")).write_bytes(data)
    return len(data)


def sheets(done):
    """contact_ingame.png (one row of 16 frames per card, 2x) and anim_ingame.gif (all cards, 4x, 60 ms)."""
    base = OUT.parent
    cell = SIZE // 2
    sheet = Image.new("RGB", (FRAMES * cell, len(done) * cell), (20, 18, 16))
    for r, cid in enumerate(done):
        for i in range(FRAMES):
            f = Image.open(OUT / cid / ("f%02d.png" % i)).resize((cell, cell), Image.NEAREST)
            sheet.paste(f, (i * cell, r * cell))
    sheet.save(base / "contact_ingame.png")
    cols = 6
    rows = (len(done) + cols - 1) // cols
    s = 2
    cw = SIZE * s + 4
    gif = []
    for i in range(FRAMES):
        canvas = Image.new("RGB", (cols * cw, rows * cw), (20, 18, 16))
        for k, cid in enumerate(done):
            f = Image.open(OUT / cid / ("f%02d.png" % i)).resize((SIZE * s, SIZE * s), Image.NEAREST)
            canvas.paste(f, ((k % cols) * cw + 2, (k // cols) * cw + 2))
        gif.append(canvas)
    pal = gif[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [g.quantize(palette=pal, dither=Image.Dither.NONE) for g in gif]
    q[0].save(base / "anim_ingame.gif", save_all=True, append_images=q[1:], duration=60, loop=0, disposal=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", type=int, default=0, choices=(0, 1, 2))
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--skip-run", action="store_true")
    ap.add_argument("--no-chosen", action="store_true", help="ignore the CHOSEN per-card variants")
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    global USE_CHOSEN
    USE_CHOSEN = not a.no_chosen
    ids = a.only or ALL
    if not a.skip_run:
        with ThreadPoolExecutor(a.jobs) as ex:
            res = list(ex.map(lambda c: run_card(c, a.variant), ids))
        if not all(res):
            sys.exit(1)
    total = 0
    for cid in ids:
        total += pack(cid, process(cid))
    done = [c for c in ALL if (OUT / c / "f00.png").exists()]
    sheets(done)
    print("packed %d cards, %.0f KB each-ish (x3 folders)" % (len(ids), total / len(ids) / 1024))


if __name__ == "__main__":
    main()
