#!/usr/bin/env python3
"""Builds the weapon-preview GIFs from the sandbox scenario captures.

For each scenarios/sandbox_<weapon>_<style>.json it reads the captures that the DeSmuME runner left in
test_output/<scenario name>/ (in the order of the scenario steps) and writes the lower screen (crop
0,192,256,384) scaled x2 with NEAREST to walkthroughs/weapon-previews/assets/sbx_<weapon>_<style>.gif.

Timing: a `capture_sequence` frame lasts capture_every * 1000/60 ms, rounded to 10 ms, minimum 20 ms.
Single `capture` frames last STATIC_MS; the last frame of the GIF lasts LAST_MS. Gaps in the frame numbers
are not filled.

Run:  python tools/sandbox_gifs.py --all
      python tools/sandbox_gifs.py sandbox_grenade_A sandbox_shotgun_B [--max-kb 4000]
"""
import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "scenarios"
CAPTURES = ROOT / "test_output"
ASSETS = ROOT / "walkthroughs" / "weapon-previews" / "assets"

COLLIM_ASSETS = ROOT / "walkthroughs" / "sniper-collimation" / "assets"
CROP = (0, 192, 256, 384)      # lower screen of a 256x384 capture
SCALE = 2
STATIC_MS = 600
LAST_MS = 900
MIN_FRAME_MS = 20
FRAME_RE = re.compile(r"^sandbox_(grenade|shotgun|sniper)_((?:collim_)?[ABC])$")
WEAPON_LABEL = {"grenade": "GRANADA", "shotgun": "ESCOPETA", "sniper": "FRANCOTIRADOR"}


def frame_ms(capture_every):
    """Duration of one sequence frame: capture_every game frames at 60 fps, 10 ms steps, min 20 ms."""
    ms = int(round(capture_every * 1000 / 60 / 10)) * 10
    return max(MIN_FRAME_MS, ms)


def plan_frames(scenario, capture_dir):
    """(png path, duration ms) pairs in step order, plus the names of captures that are missing."""
    items, missing = [], []
    for step in scenario.get("steps", []):
        if "capture_sequence" in step:
            prefix = step["capture_sequence"]
            ms = frame_ms(step.get("capture_every", 1))
            files = sorted(capture_dir.glob(f"{prefix}_[0-9][0-9][0-9][0-9].png"))
            if not files:
                missing.append(f"{prefix}_NNNN.png")
            items += [(p, ms) for p in files]
        elif "capture" in step:
            png = capture_dir / f"{step['capture']}.png"
            if png.exists():
                items.append((png, STATIC_MS))
            else:
                missing.append(png.name)
    return items, missing


def load_font():
    try:
        return ImageFont.truetype("arial.ttf", 12)
    except OSError:
        return ImageFont.load_default(size=12)


def load_frame(png, label_text, font):
    img = Image.open(png).convert("RGB")
    if img.size != (256, 384):
        raise ValueError(f"{png.name} mide {img.size}, se esperaba 256x384")
    img = img.crop(CROP)
    img = img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)
    draw = ImageDraw.Draw(img)
    x, y, pad = 4, 4, 3
    box = draw.textbbox((x + pad, y + pad), label_text, font=font)
    draw.rectangle((x, y, box[2] + pad, box[3] + pad), fill=(0, 0, 0))
    draw.text((x + pad, y + pad), label_text, font=font, fill=(255, 255, 255))
    return img


def save_gif(frames, durations, out, max_bytes):
    """Saves with the full palette; if over max_bytes, retries with quantize(colors=64)."""
    colors = None
    for colors in (None, 64):
        seq = frames if colors is None else [f.quantize(colors=colors) for f in frames]
        seq[0].save(out, save_all=True, append_images=seq[1:], duration=durations, loop=0, optimize=True)
        size = out.stat().st_size
        if size <= max_bytes:
            break
    return colors, size


def build(path, max_kb):
    scenario = json.loads(path.read_text(encoding="utf-8"))
    name = scenario.get("name", path.stem)
    match = FRAME_RE.match(name)
    if not match:
        raise ValueError(f"nombre de escenario no reconocido: {name}")
    weapon, style = match.groups()

    capture_dir = CAPTURES / name
    if not capture_dir.is_dir():
        raise FileNotFoundError(f"no hay capturas en {capture_dir}")
    items, missing = plan_frames(scenario, capture_dir)
    for item in missing:
        print(f"  aviso {name}: falta {item}", file=sys.stderr)
    if not items:
        raise ValueError("sin fotogramas")

    label_text = f"{WEAPON_LABEL[weapon]} {style.replace('collim_', '')} COLIMADO"
    font = load_font()
    frames = [load_frame(png, label_text, font) for png, _ in items]
    durations = [ms for _, ms in items]
    durations[-1] = LAST_MS

    ASSETS.mkdir(parents=True, exist_ok=True)
    out_dir = COLLIM_ASSETS if style.startswith("collim_") else ASSETS
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"sbx_{weapon}_{style}.gif"
    colors, size = save_gif(frames, durations, out, max_kb * 1024)
    if size > max_kb * 1024:
        print(f"  aviso {out.name}: sigue superando {max_kb} KB con 64 colores", file=sys.stderr)

    total_s = sum(durations) / 1000
    palette = "" if colors is None else ", paleta 64"
    print(f"{out.name}: {len(frames)} fotogramas, {total_s:.2f} s, {size / 1024:.0f} KB{palette}")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenarios", nargs="*", help="nombres (sandbox_grenade_A) o rutas a .json")
    parser.add_argument("--all", action="store_true", help="todos los scenarios/sandbox_*.json")
    parser.add_argument("--max-kb", type=int, default=4000, help="tamano maximo por GIF (por defecto 4000)")
    args = parser.parse_args(argv)

    if args.all:
        paths = sorted(p for p in SCENARIOS.glob("sandbox_*.json") if "_aura_" not in p.name and "_collim_" not in p.name)
    else:
        paths = []
        for arg in args.scenarios:
            p = Path(arg)
            if p.suffix != ".json":
                p = SCENARIOS / f"{arg if arg.startswith('sandbox_') else 'sandbox_' + arg}.json"
            paths.append(p)
    if not paths:
        parser.error("indica escenarios o --all")

    failed = 0
    for path in paths:
        try:
            build(path, args.max_kb)
        except (OSError, ValueError, KeyError) as exc:
            print(f"ERROR {path.name}: {exc}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
