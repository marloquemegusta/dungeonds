#!/usr/bin/env python3
"""Empaqueta UNA luz de sala del ARPG en nitrofiles/arpg_luz/<luz>.bin (formato LMOD de la demo + trailer LEXT).

uso: python tools/arpg_light_pack.py <luz> [--render] [--keep-going]
  --render   lanza antes los renders (props del kit, props de sala, personajes); sin el, usa lo que haya en scratch/arpg_luz/<luz>/

Entradas (scratch/arpg_luz/<luz>/): kit_props/ props/ chars/ (los genera arpg_light_props.py / arpg_light_chars.py).
Pasos: paleta del kit -> kit.npz (bake_cathedral_kit.py con tinte de suelo/muros) -> personajes completos
(chars_full: los re-iluminados, los de aproximacion por tinte y el resto enlazado al dia) -> generate_player_sprites_c.py
-> bins CHR1 de la luz -> remates RMT1 con tinte -> pack.

Formato (little endian) en el docstring de pack_format() y en DESIGN-ARPG.md §11.
"""
import argparse, json, os, re, shutil, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arpg_light_chars as alc          # noqa: E402

MAGIC = 0x444F4D4C      # 'LMOD'
LEXT = 0x5458454C       # 'LEXT'
K_MAP, K_CHR1, K_RMT1, K_PROP = 1, 2, 3, 4

MUTABLE_SUFFIXES = ("_frames", "_frame_offsets", "_frame_bounds", "_runs", "_run_offsets", "_shadow_masks",
                    "_shadow_offsets", "_shadow_bounds")
ARRAY_RE = re.compile(
    r"^(?:const\s+|PS_CONST\s+)?(uint16_t|uint32_t|uint8_t)\s+(g_[a-zA-Z0-9_]+)((?:\[[^\]]*\])+)\s*(?:__attribute__\(\(.*?\)\)\s*)?=\s*\{(.*?)\};",
    re.MULTILINE | re.DOTALL)
CLIP_OF_DIR = {"cireneo": "charger", "cireneo_charge": "charger_charge", "cireneo_telegraph": "charger_telegraph"}
REMATE_OF = {"monja": "exvoto", "bebe": "exvoto_bebe", "monaguillo": "monaguillo", "cireneo": "cireneo",
             "ojo": "ojo", "parroco": "parroco", "smonja": "smonja"}
SMONJA_DIRS = ["exvoto_super_monja", "exvoto_super_monja_pray_stand", "exvoto_super_monja_pray_kneel", "exvoto_super_monja_stand_up"]
CHARS_DAY = ROOT / "assets/sprites/characters"


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(" ".join(str(c) for c in cmd[:3]) + "\n" + (r.stdout + r.stderr)[-1500:])
    return r.stdout


def parse_c_arrays(c_path):
    out = []
    for m in ARRAY_RE.finditer(c_path.read_text(encoding="utf-8")):
        ctype, name, body = m.group(1), m.group(2), m.group(4)
        if not any(name.endswith(s) for s in MUTABLE_SUFFIXES) or name.startswith("g_character_"):
            continue
        vals = [int(x, 0) for x in re.findall(r"0x[0-9a-fA-F]+|-?\d+", body)]
        out.append((name, np.array(vals, dtype={"uint8_t": np.uint8, "uint16_t": np.uint16, "uint32_t": np.uint32}[ctype]).tobytes()))
    return out


def tint_bgr555_array(u16, tint):
    r = (u16 & 31).astype(np.float32); g = ((u16 >> 5) & 31).astype(np.float32); b = ((u16 >> 10) & 31).astype(np.float32)
    nr = np.clip(np.rint(r * tint[0]), 0, 31).astype(np.uint16)
    ng = np.clip(np.rint(g * tint[1]), 0, 31).astype(np.uint16)
    nb = np.clip(np.rint(b * tint[2]), 0, 31).astype(np.uint16)
    return np.where((u16 & 0x8000) != 0, (u16 & 0x8000) | (nb << 10) | (ng << 5) | nr, u16)


def mean_rgb(png):
    a = np.asarray(Image.open(png).convert("RGBA")).reshape(-1, 4)
    a = a[a[:, 3] > 200][:, :3].astype(np.float64)
    return a.mean(axis=0)


def junction(dst, src):
    if dst.exists():
        return
    run(["cmd", "/c", "mklink", "/J", str(dst), str(src)])


def stage_chars(light, base, types):
    """chars_full: todos los directorios del dia; los re-iluminados (chars/) y los aproximados por tinte sustituyen al dia."""
    full = base / "chars_full"
    if full.exists():
        for p in full.iterdir():
            if os.path.isjunction(str(p)):
                os.rmdir(p)
            elif p.is_dir():
                shutil.rmtree(p)
    full.mkdir(parents=True, exist_ok=True)
    relit = {p.name for p in (base / "chars").iterdir() if p.is_dir()}
    ratio = mean_rgb(base / "chars/corazon/spritesheet.png") / mean_rgb(CHARS_DAY / "corazon/spritesheet.png")
    tint_dirs = []
    if "smonja" in types:
        tint_dirs += SMONJA_DIRS
    for d in sorted(p.name for p in CHARS_DAY.iterdir() if p.is_dir()):
        if d in relit:
            junction(full / d, base / "chars" / d)
        elif d in tint_dirs:
            (full / d).mkdir()
            for f in (CHARS_DAY / d).iterdir():
                if f.is_file() and f.name != "collage.gif":
                    shutil.copy2(f, full / d / f.name)
            sheet = full / d / "spritesheet.png"
            a = np.asarray(Image.open(sheet).convert("RGBA")).astype(np.float32)
            for k in range(3):
                a[..., k] = np.clip(a[..., k] * ratio[k], 0, 255)
            Image.fromarray(a.astype(np.uint8)).save(sheet)
        else:
            junction(full / d, CHARS_DAY / d)
    shutil.copy2(CHARS_DAY / "characters.json", full / "characters.json")
    return full, relit, tint_dirs, [round(float(v), 3) for v in ratio]


def short_name(name):
    """El nombre del trailer son 24 bytes: los clips de la Super Monja (p. ej. exvoto_super_monja_pray_stand) chocarian al truncar."""
    return name.replace("exvoto_super_monja", "smonja") if len(name) > 23 else name


def entry(name, kind, data):
    name = short_name(name)
    pad = (-len(data)) % 4
    return struct.pack("<24sII", name.encode(), kind, len(data)) + data + bytes(pad)


def prop_entry(pdir, name):
    meta = json.loads((pdir / "meta.json").read_text(encoding="utf-8"))
    im = np.asarray(Image.open(pdir / "color.png").convert("RGBA"))
    h, w = im.shape[:2]
    px = ((im[..., 2].astype(np.uint16) >> 3) << 10) | ((im[..., 1].astype(np.uint16) >> 3) << 5) | (im[..., 0].astype(np.uint16) >> 3)
    px = np.where(im[..., 3] >= 128, px | 0x8000, 0).astype(np.uint16)
    dx, dy = meta.get("shadow_offset_px", [0, 0]); sw, sh = meta.get("shadow_canvas_px", [0, 0])
    sbits = b""
    if sw and (pdir / "shadow.png").exists():
        sm = np.asarray(Image.open(pdir / "shadow.png").convert("L")) > 127
        sbits = np.packbits(sm, axis=1, bitorder="little").tobytes()
    data = struct.pack("<HHhhHH", w, h, dx, dy, sw, sh) + px.tobytes() + sbits
    return entry(name, K_PROP, data)


def build(light_id, render):
    doc = alc.load_lights()
    light = next(l for l in doc["luces"] if l["id"] == light_id)
    base = ROOT / "scratch/arpg_luz" / light_id
    py = sys.executable
    if render:
        run([py, ROOT / "tools/arpg_light_props.py", light_id, "--kit", "--jobs", "4"])
        run([py, ROOT / "tools/arpg_light_props.py", light_id, "--jobs", "4"])
        run([py, ROOT / "tools/arpg_light_chars.py", light_id, "--jobs", "4"])
    types = alc.room_enemies(light["rooms"])
    tint = [a * light["floor_gain"] for a in light["floor_tint"]]
    tint_arg = ",".join(str(round(t, 4)) for t in tint)

    # 1. paleta del kit + kit
    pal_dir = base / "palette"; pal_dir.mkdir(parents=True, exist_ok=True)
    kit_imgs = [base / "kit_props" / p / "color.png" for p in
                ("columna_entera", "banco_entero", "relicario", "santo", "vela", "verja", "sacos", "sacos_b", "sacos_remate",
                 "alambre", "columna", "banco_roto")]
    run([py, ROOT / "tools/palette/extract_palette.py", "--terrain-colors", "0", "--prop-colors", "190", "--native",
         "--out", pal_dir, *[i for i in kit_imgs if i.exists()]])
    run([py, ROOT / "tools/bake_cathedral_kit.py", "--floor", ROOT / "assets/environment/cathedral/floor/rombos_tripo",
         "--mode", "catedral", "--prop-dir", base / "kit_props", "--prop-palette", pal_dir / "palette.json",
         "--tint", tint_arg, "--out-kit-npz", base / "kit.npz", "--preview", base / "kit_preview.png"])
    kit = np.load(base / "kit.npz")

    # 2. personajes completos -> C + bins CHR1
    full, relit, tint_dirs, ratio = stage_chars(light, base, types)
    out_c = base / "player_sprite.c"; bin_dir = base / "chr_bins"
    if bin_dir.exists():
        shutil.rmtree(bin_dir)
    run([py, ROOT / "tools/generate_player_sprites_c.py", "--src", full, "--out-c", out_c, "--out-bin-dir", bin_dir])
    arrays = parse_c_arrays(out_c)
    day_names = [n for n, _ in parse_c_arrays(ROOT / "source/player_sprite.c")]
    assert [n for n, _ in arrays] == day_names, "los arrays de sprites no coinciden con source/player_sprite.c"

    # 3. extras del trailer
    ext = []
    for nm, key in (("end0", "end_map_0"), ("end1", "end_map_1"), ("hole", "hole_map")):
        a = kit[key].astype(np.uint16)
        ext.append(entry(nm, K_MAP, struct.pack("<HH", a.shape[1], a.shape[0]) + a.tobytes()))
    wanted = set()
    for d in list(relit) + tint_dirs:
        c = CLIP_OF_DIR.get(d, d)
        if (bin_dir / (c + ".bin")).exists() and c not in ("corazon",):
            wanted.add(c)
    n_chr = 0
    for c in sorted(wanted):
        ext.append(entry(c, K_CHR1, (bin_dir / (c + ".bin")).read_bytes())); n_chr += 1
    n_rm = 0
    for t in sorted(types):
        k = REMATE_OF.get(t)
        if not k:
            continue
        for d in range(8):
            src = ROOT / f"nitrofiles/remate/{k}_d{d}.bin"
            if not src.exists():
                continue
            raw = src.read_bytes()
            magic, pb, rb, mb = struct.unpack_from("<IIII", raw, 0)
            assert magic == 0x31544D52, src
            hs = len(raw) - (pb + rb + mb)
            pix = tint_bgr555_array(np.frombuffer(raw, np.uint16, pb // 2, hs).copy(), tint)
            ext.append(entry(f"{k}_d{d}", K_RMT1, raw[:hs] + pix.tobytes() + raw[hs + pb:])); n_rm += 1
    n_pr = 0
    for pdir in sorted((base / "props").iterdir()):
        if (pdir / "color.png").exists():
            ext.append(prop_entry(pdir, pdir.name)); n_pr += 1

    # 4. pack
    pal = kit["palette"].astype(np.uint16); tiles = kit["tiles"].astype(np.uint8)
    fmap = kit["floor_map"].astype(np.uint16); sm = kit["stamp_meta"].astype(np.int32); st = kit["stamp_tiles"].astype(np.uint16)
    out = ROOT / "nitrofiles/arpg_luz" / (light_id + ".bin"); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        f.write(struct.pack("<IHHII", MAGIC, tiles.shape[0], sm.shape[0], st.shape[0], len(arrays)))
        f.write(pal.tobytes()); f.write(tiles.tobytes()); f.write(fmap.tobytes())
        for r in sm:
            f.write(struct.pack("<BBBBBBBB", int(r[3]), int(r[4]), int(r[6]), int(r[0]), int(r[1]), int(r[2]), 0, 0))
        f.write(st.tobytes())
        for _, data in arrays:
            f.write(struct.pack("<I", len(data))); f.write(data)
        f.write(struct.pack("<II", LEXT, len(ext)))
        for e in ext:
            f.write(e)
    info = dict(luz=light_id, bytes=out.stat().st_size, tiles=int(tiles.shape[0]), stamps=int(sm.shape[0]), slots=len(arrays),
                chr1=n_chr, rmt1=n_rm, props=n_pr, relit=len(relit), tint_dirs=tint_dirs, ratio=ratio)
    (base / "pack_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("light"); ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    build(a.light, a.render)
