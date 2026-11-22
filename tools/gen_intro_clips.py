#!/usr/bin/env python3
"""Genera los bucles de video de las 3 tarjetas de introduccion del ARPG (DESIGN-ARPG.md 7, source/intro.c).

Cada clip es la pantalla inferior (256x192) de la ROM ARPG normal (variante por defecto), ~2 s a 30 imagenes por segundo
(captura cada 2 frames de DeSmuME), guardada SIN PERDIDA en nitrofiles/intro/<nombre>.bin:
  pelear     el heroe (invulnerable) en la primera sala de la catedral da el combo de punetazos (L) a la horda; se ven los orbes
  lapiz      el heroe lanza el Rayo con el lapiz (mantener el toque y soltar) contra la horda; el orbe de mana baja
  campamento el heroe anda por el campamento nocturno junto a la hoguera, el jergon y el arcon
Los escenarios (scenarios/intro_clip_<nombre>.json, solo evidencia) llevan a la ROM del titulo -> Nueva partida (toque en 128,66) ->
START salta la intro -> campamento; para la catedral se coloca al heroe en la puerta (px=32768, py=29696) y se pulsa A.

Uso (desde la raiz del worktree; antes: build-project.ps1 -ProjectPath . sin -Variant):
    python tools/gen_intro_clips.py                    # los 3 clips
    python tools/gen_intro_clips.py --only lapiz       # uno solo
    python tools/gen_intro_clips.py --reuse            # no vuelve a ejecutar el emulador (usa artifacts/intro_clips)
    python tools/gen_intro_clips.py --verify-bin nitrofiles/intro/lapiz.bin

Formato .bin (little endian; el descodificador es video_step() en source/intro.c):
    u16 magic 0x4956 | u16 n | u32 max_rec | u32 max_dec | u32 off[n + 2]
    registro 0 = imagen completa (96 KB de pixeles, comprimida con LZ10 de la BIOS); 1..n-1 = delta con la anterior;
    n = delta de la ultima a la 0 (cierra el bucle). Un delta es: s8 dx, s8 dy (nueva[i] = vieja[i + dy*256 + dx],
    compensacion del scroll) + palabras u16 (tipo << 14 | cuenta): 0 saltar, 1 literales, 2 repetir un pixel.
    Si el registro empieza por 0x10 esta comprimido con LZ10 (swiDecompressLZSSWram); dx esta en [-6, 6],
    asi que no hay ambiguedad. Pixeles BGR555 con el bit 15 puesto.
Regla 5 de AGENTS.md: los golpes y el rayo han de conectar de verdad (la horda rodea al heroe antes de la captura).
"""
import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts")
OUT_DIR = ROOT / "nitrofiles" / "intro"
WORK_DIR = ROOT / "artifacts" / "intro_clips"
W, H = 256, 192
NPIX = W * H
MAGIC = 0x4956
ELF = "../.ds-game-dev/build/out/dungeonds.elf"


def fields():
    return {
        "px": {"symbol": "pl", "offset": 0, "type": "s32"}, "py": {"symbol": "pl", "offset": 4, "type": "s32"},
        "hp": {"symbol": "gps", "offset": 0, "type": "s32"}, "god": {"symbol": "gps", "offset": 20, "type": "s32"},
        "mana": {"symbol": "gps", "offset": 24, "type": "s32"},
    }


def scenario(name, description, steps):
    return {"name": name, "description": description, "suite": False, "evidence_only": True,
            "state": {"elf": ELF, "symbols": {"pl": "s_player", "gps": "g_player_state"}, "default_symbol": "pl", "fields": fields()},
            "steps": steps}


def to_game(extra_hold=None):
    """Titulo -> Nueva partida -> START (salta la intro) -> campamento."""
    return [{"frames": 60}, {"tap": {"x": 128, "y": 66}, "frames": 6}, {"release": True, "frames": 40},
            {"button_down": "START", "frames": 4}, {"button_up": "START", "frames": 60}]


def to_cathedral(up_frames):
    """Campamento -> puerta -> sala 1, heroe invulnerable, andando hacia la horda `up_frames` frames."""
    return [{"poke": [{"field": "px", "value": 32768}, {"field": "py", "value": 29696}], "frames": 20},
            {"button_down": "A", "frames": 4}, {"button_up": "A", "frames": 120},
            {"poke": [{"field": "god", "value": 1}], "frames": 2},
            {"button_down": "UP", "frames": up_frames}, {"button_up": "UP", "frames": 1, "state_capture": "antes"}]


# --- Los 3 clips (tarjetas en el orden de source/intro.c). loop = (inicio, longitud) sobre las imagenes capturadas -------------
def clip_pelear():
    steps = to_game() + to_cathedral(600)
    for i in range(34):                                   # combo: L 3 frames pulsado, 7 suelto; se captura desde que la horda llega
        cap = {"capture_sequence": "c0", "capture_every": 2} if i >= 8 else {}
        steps.append({"button_down": "L", "frames": 3, **cap})
        steps.append({"button_up": "L", "frames": 7, "state_capture": f"l{i}", **cap})
    return scenario("intro_clip_pelear", "ARPG: el heroe, rodeado en la sala 1, da el combo de punetazos (L) a la horda.", steps), (48, 60)


def clip_lapiz():
    steps = to_game() + to_cathedral(585)
    for i in range(3):                                    # el Rayo tarda 48 frames en armarse (aim_min_frames)
        steps.append({"tap": {"x": 128, "y": 60}, "frames": 54, "capture_sequence": "c0", "capture_every": 2})      # mantener: apunta y carga
        steps.append({"release": True, "frames": 20, "capture_sequence": "c0", "capture_every": 2, "state_capture": f"r{i}"})   # suelta: Rayo
    return scenario("intro_clip_lapiz", "ARPG: el heroe lanza el Rayo con el lapiz contra la horda; baja el orbe de mana.", steps), (0, 60)


def clip_campamento():
    steps = to_game()
    for btn, n in (("LEFT", 30), ("RIGHT", 60), ("LEFT", 30)):      # ida y vuelta: acaba donde empieza (bucle limpio)
        steps.append({"button_down": btn, "frames": n, "capture_sequence": "c0", "capture_every": 2})
    steps.append({"button_up": "LEFT", "frames": 2, "state_capture": "fin"})
    return scenario("intro_clip_campamento", "ARPG: el heroe anda por el campamento nocturno.", steps), (0, 60)


CLIPS = {"pelear": clip_pelear, "lapiz": clip_lapiz, "campamento": clip_campamento}


# --- Emulador --------------------------------------------------------------------------------------------------
def run_scenario(name, scen_path):
    out = WORK_DIR / name
    if out.exists():
        for p in out.glob("*"):
            p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SKILL_SCRIPTS / "run-scenario.ps1"),
           "-ProjectPath", str(ROOT), "-ScenarioPath", str(scen_path), "-OutputPath", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:])
    if r.returncode not in (0, 1):
        raise SystemExit(f"run-scenario fallo ({r.returncode}): {r.stderr[-400:]}")
    return out


def print_samples(out):
    """Imprime el estado de cada state_capture (mana, hp, posicion del heroe)."""
    ev = out / "events.jsonl"
    if not ev.exists():
        return
    for line in ev.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("action") == "state_capture":
            print(f"  [{d['name']}] f{d['frame']} {d['state']}")


def load_frames(out):
    """Mitad inferior de las capturas c*_NNNN.png, en orden, como BGR555 con el bit 15 puesto."""
    files = sorted(out.glob("c[0-9]_*.png"))
    frames = []
    for p in files:
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)[192:384]
        if (a & 7).any():
            raise SystemExit(f"{p.name}: canales que no son multiplos de 8; la captura no es BGR555 exacta")
        r, g, b = (a[:, :, 0] >> 3).astype(np.uint16), (a[:, :, 1] >> 3).astype(np.uint16), (a[:, :, 2] >> 3).astype(np.uint16)
        frames.append((0x8000 | (b << 10) | (g << 5) | r).reshape(-1))
    return files, frames


def to_rgb(f):
    r, g, b = f & 31, (f >> 5) & 31, (f >> 10) & 31
    return (np.stack([r, g, b], axis=-1).reshape(H, W, 3) * 8).astype(np.uint8)


# --- Seleccion del tramo del bucle -------------------------------------------------------------------------
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def dissolve(last, first, steps):
    """`steps` imagenes intermedias de `last` a `first` por tramado ordenado (Bayer 4x4): la k-esima toma k/(steps+1) de los pixeles de
    `first`. Los pixeles se eligen por posicion fija, asi que cada imagen es un dither estable (y comprime bien con los deltas)."""
    thr = np.tile(BAYER4, (H // 4, W // 4)).reshape(-1)
    return [np.where(thr < round(16 * (k + 1) / (steps + 1)), first, last) for k in range(steps)]


def pick_window(frames, loop):
    n = len(frames)
    if loop[0] == "trim":                       # ("trim", min, max): empieza en 0, la longitud con la imagen final mas parecida a la 0
        best = min(((int(np.count_nonzero(frames[L - 1] != frames[0])), L) for L in range(loop[1], min(loop[2], n) + 1)))
        print(f"  bucle (trim): longitud={best[1]} pixeles distintos entre la ultima y la primera={best[0]}")
        return 0, best[1]
    if loop != "search":
        s, length = loop[0], loop[1]
        length = min(length, n - s)
        return s, length
    best = None
    for length in range(LOOP_TARGET - 6, LOOP_TARGET + 5):
        for s in range(0, n - length):
            # el salto del bucle es de f[s+length-1] a f[s]: es invisible si f[s] ~ f[s+length] (lo que vendria despues)
            d = np.count_nonzero(frames[s] != frames[s + length])
            if best is None or d < best[0]:
                best = (d, s, length)
    print(f"  bucle: inicio={best[1]} longitud={best[2]} pixeles distintos en el salto={best[0]}")
    return best[1], best[2]


# --- LZ10 (el formato de swiDecompressLZSSWram de la BIOS) -----------------------------------------------------
def lz10_compress(data: bytes) -> bytes:
    n = len(data)
    out = bytearray(struct.pack("<I", 0x10 | (n << 8)))
    heads = {}
    pos = 0
    flags_pos = None
    bit = 0
    while pos < n:
        if bit == 0:
            flags_pos = len(out)
            out.append(0)
        best_len, best_disp = 0, 0
        if pos + 3 <= n:
            key = data[pos:pos + 3]
            chain = heads.get(key, ())
            for cand in reversed(chain[-48:]):
                disp = pos - cand
                if disp > 4096:
                    break
                ln = 3
                while ln < 18 and pos + ln < n and data[cand + ln] == data[pos + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_disp = ln, disp
                    if ln == 18:
                        break
        step = best_len if best_len >= 3 else 1
        if best_len >= 3:
            out[flags_pos] |= 0x80 >> bit
            d = best_disp - 1
            out += bytes(((best_len - 3) << 4 | (d >> 8), d & 0xff))
        else:
            out.append(data[pos])
        for k in range(pos, min(pos + step, n - 2)):
            heads.setdefault(data[k:k + 3], []).append(k)
        pos += step
        bit = (bit + 1) & 7
    while len(out) & 3:
        out.append(0)
    return bytes(out)


def lz10_decompress(blob: bytes) -> bytes:
    assert blob[0] == 0x10
    size = struct.unpack_from("<I", blob, 0)[0] >> 8
    out = bytearray()
    i = 4
    while len(out) < size:
        flags = blob[i]; i += 1
        for b in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> b):
                x, y = blob[i], blob[i + 1]; i += 2
                ln, disp = (x >> 4) + 3, (((x & 15) << 8) | y) + 1
                for _ in range(ln):
                    out.append(out[-disp])
            else:
                out.append(blob[i]); i += 1
    return bytes(out)


# --- Codificacion ------------------------------------------------------------------------------------------
def predict(prev, dx, dy):
    off = dy * W + dx
    p = prev.copy()
    if off > 0:
        p[:NPIX - off] = prev[off:]
    elif off < 0:
        p[-off:] = prev[:NPIX + off]
    return p


def ops_for(pred, cur):
    """Palabras u16 que convierten `pred` en `cur`."""
    diff = np.flatnonzero(pred != cur)
    words = []
    if diff.size == 0:
        return words
    pos = 0
    # agrupa los pixeles distintos en segmentos separados por mas de 2 iguales (un salto cuesta 1 palabra)
    breaks = np.flatnonzero(np.diff(diff) > 2)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [diff.size - 1]))
    for a, b in zip(starts, ends):
        lo, hi = int(diff[a]), int(diff[b]) + 1
        skip = lo - pos
        while skip > 0:
            n = min(skip, 0x3fff)
            words.append((0 << 14) | n)
            skip -= n
        i = lo
        seg = cur
        lit_start = i
        while i < hi:
            j = i + 1
            while j < hi and seg[j] == seg[i]:
                j += 1
            if j - i >= 4:                     # tramo uniforme: repetir
                if lit_start < i:
                    _emit_lit(words, seg, lit_start, i)
                k = i
                while k < j:
                    n = min(j - k, 0x3fff)
                    words += [(2 << 14) | n, int(seg[i])]
                    k += n
                lit_start = j
            i = j
        if lit_start < hi:
            _emit_lit(words, seg, lit_start, hi)
        pos = hi
    return words


def _emit_lit(words, seg, a, b):
    while a < b:
        n = min(b - a, 0x3fff)
        words.append((1 << 14) | n)
        words += [int(v) for v in seg[a:a + n]]
        a += n


def encode_record(prev, cur):
    best = None
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            if prev is None:
                break
            p = predict(prev, dx, dy)
            cost = np.count_nonzero(p != cur)
            if best is None or cost < best[0]:
                best = (cost, dx, dy, p)
    if prev is None:
        dx = dy = 0
        pred = np.zeros(NPIX, dtype=np.uint16)
    else:
        _, dx, dy, pred = best
    words = ops_for(pred, cur)
    return struct.pack("<bb", dx, dy) + struct.pack(f"<{len(words)}H", *words)


def pack_delta(raw):
    """LZ10 si gana; si no, tal cual (empieza por dx, nunca por 0x10)."""
    z = lz10_compress(raw)
    return z if len(z) < len(raw) else raw


def encode(frames):
    n = len(frames)
    key = lz10_compress(frames[0].astype("<u2").tobytes())      # imagen completa: pixeles tal cual, comprimidos
    raws = [encode_record(frames[t - 1], frames[t]) for t in range(1, n)]
    raws.append(encode_record(frames[n - 1], frames[0]))          # cierra el bucle
    recs = [key] + [pack_delta(r) for r in raws]
    max_dec = max(len(r) for r in raws)
    header_size = 12 + 4 * (n + 2)
    offs, o = [], header_size
    for r in recs:
        offs.append(o)
        o += len(r)
    offs.append(o)
    blob = struct.pack("<HHII", MAGIC, n, max(len(r) for r in recs), max_dec) + struct.pack(f"<{n + 2}I", *offs)
    return blob + b"".join(recs)


def decode(blob):
    """Descodificador de referencia (identico en logica a video_step() de intro.c): una vuelta completa + cierre."""
    magic, n, max_rec, max_dec = struct.unpack_from("<HHII", blob, 0)
    assert magic == MAGIC
    offs = struct.unpack_from(f"<{n + 2}I", blob, 12)
    fb = np.zeros(NPIX, dtype=np.uint16)
    out = []
    for idx in list(range(0, n + 1)):
        rec = blob[offs[idx]:offs[idx + 1]]
        if idx == 0:
            fb = np.frombuffer(lz10_decompress(rec), dtype="<u2").copy()
            out.append(fb.copy())
            continue
        if rec[0] == 0x10:
            rec = lz10_decompress(rec)
            assert len(rec) <= max_dec
        dx, dy = struct.unpack_from("<bb", rec, 0)
        off = dy * W + dx
        if off > 0:
            fb[:NPIX - off] = fb[off:].copy()
        elif off < 0:
            fb[-off:] = fb[:NPIX + off].copy()
        words = np.frombuffer(rec[2:], dtype="<u2")
        i = pos = 0
        while i < len(words):
            op = int(words[i]); i += 1
            cnt, typ = op & 0x3fff, op >> 14
            if typ == 1:
                fb[pos:pos + cnt] = words[i:i + cnt]; i += cnt
            elif typ == 2:
                fb[pos:pos + cnt] = words[i]; i += 1
            pos += cnt
        out.append(fb.copy())
    return out        # n + 1 imagenes: 0..n-1 y la imagen 0 otra vez (cierre)


def verify(blob, frames):
    dec = decode(blob)
    for t, f in enumerate(frames):
        if not np.array_equal(dec[t], f):
            raise SystemExit(f"verificacion: imagen {t} distinta tras descodificar")
    if not np.array_equal(dec[len(frames)], frames[0]):
        raise SystemExit("verificacion: el registro de cierre no devuelve la imagen 0")


# --- Hojas de contacto -------------------------------------------------------------------------------------
def contact_sheet(frames, path, cols=10, step=4):
    sel = frames[::step]
    rows = (len(sel) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols // 2, H * rows // 2))
    for i, f in enumerate(sel):
        im = Image.fromarray(to_rgb(f)).resize((W // 2, H // 2), Image.Resampling.NEAREST)
        sheet.paste(im, ((i % cols) * W // 2, (i // cols) * H // 2))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(CLIPS))
    ap.add_argument("--reuse", action="store_true", help="no ejecuta el emulador: usa las capturas ya hechas")
    ap.add_argument("--verify-bin", type=Path)
    args = ap.parse_args()
    if args.verify_bin:
        blob = args.verify_bin.read_bytes()
        dec = decode(blob)
        print(f"{args.verify_bin.name}: {len(blob)} bytes, {len(dec) - 1} imagenes por vuelta")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, make in CLIPS.items():
        if args.only and name != args.only:
            continue
        made = make()
        scen, loop = made[0], made[1]
        scen_path = ROOT / "scenarios" / f"intro_clip_{name}.json"
        scen_path.write_text(json.dumps(scen, indent=2) + "\n", encoding="utf-8")
        print(f"[{name}] {scen_path.name}")
        out = WORK_DIR / name if args.reuse else run_scenario(name, scen_path)
        print_samples(out)
        files, frames = load_frames(out)
        print(f"  {len(frames)} imagenes capturadas")
        contact_sheet(frames, WORK_DIR / f"{name}_capturas.png", step=6)
        s, length = pick_window(frames, loop)
        win = frames[s:s + length]
        if isinstance(loop, tuple) and len(loop) > 2:           # (inicio, longitud, n imagenes de disolucion al principio)
            win = win + dissolve(win[-1], win[0], loop[2])
            length = len(win)
            print(f"  fundido: {loop[2]} imagenes de disolucion tramada; total {length}")
        blob = encode(win)
        verify(blob, win)
        (OUT_DIR / f"{name}.bin").write_bytes(blob)
        contact_sheet(win, WORK_DIR / f"{name}_bucle.png", step=4)
        gif = [Image.fromarray(to_rgb(f)).resize((W * 4, H * 4), Image.Resampling.NEAREST) for f in win]
        gif[0].save(WORK_DIR / f"{name}.gif", save_all=True, append_images=gif[1:], duration=40, loop=0, optimize=False)   # 25 fps, 4x NEAREST
        for k in (0, length // 2, length - 1):
            Image.fromarray(to_rgb(win[k])).save(WORK_DIR / f"{name}_f{k:02d}.png")
        print(f"  -> {OUT_DIR / (name + '.bin')}: {len(blob)} bytes, {length} imagenes (captura {s}..{s + length - 1})")


if __name__ == "__main__":
    main()
