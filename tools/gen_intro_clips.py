#!/usr/bin/env python3
"""Genera los bucles de video de las tarjetas de introduccion (DESIGN.md 6.3, source/intro.c).

Cada clip es la pantalla inferior (256x192) del juego real, ~2 s a 30 imagenes por segundo, capturada de
DeSmuME (una de cada 2 imagenes del juego) y guardada SIN PERDIDA en nitrofiles/intro/<nombre>.bin.

Flujo:  1) escribe scenarios/intro_clip_<nombre>.json   2) ejecuta cada escenario con run-scenario.ps1 sobre la
ROM de la variante `cathedral-horde` (horda real, marea real, buzon sandbox)   3) toma la mitad inferior de las
capturas, elige el tramo del bucle y lo codifica.

Uso (desde la raiz del repo / worktree):
    powershell -NonInteractive -ExecutionPolicy Bypass -File <skill>\\scripts\\build-project.ps1 -ProjectPath . -Variant cathedral-horde
    python tools/gen_intro_clips.py                 # los 4 clips (escenario + emulador + .bin + hojas de contacto)
    python tools/gen_intro_clips.py --only corazon  # uno solo
    python tools/gen_intro_clips.py --reuse         # no vuelve a ejecutar el emulador (usa las capturas de artifacts/intro_clips)
    python tools/gen_intro_clips.py --verify-bin nitrofiles/intro/marea.bin   # descodifica y compara con las capturas

Formato .bin (little endian; el descodificador es video_step() en source/intro.c):
    u16 magic 0x4956 | u16 n | u32 max_rec | u32 max_dec | u32 off[n + 2]
    registro 0 = imagen completa (96 KB de pixeles, comprimida con LZ10 de la BIOS); 1..n-1 = delta con la anterior;
    n = delta de la ultima a la 0 (cierra el bucle). Un delta es: s8 dx, s8 dy (nueva[i] = vieja[i + dy*256 + dx],
    compensacion del scroll) + palabras u16 (tipo << 14 | cuenta): 0 saltar, 1 literales, 2 repetir un pixel.
    Si el registro empieza por 0x10 esta comprimido con LZ10 (swiDecompressLZSSWram); dx esta en [-6, 6], asi
    que no hay ambiguedad. Pixeles BGR555 con el bit 15 puesto.
Regla 5 de AGENTS.md: los escenarios de tiro colocan a los enemigos en la fila exacta del rayo del heroe.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox_scenes as sb  # noqa: E402

SKILL_SCRIPTS = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts")
VARIANT = "cathedral-horde"
OUT_DIR = ROOT / "nitrofiles" / "intro"
WORK_DIR = ROOT / "artifacts" / "intro_clips"
W, H = 256, 192
NPIX = W * H
MAGIC = 0x4956
LOOP_TARGET = 60            # imagenes por bucle: 2 s a 30 imagenes por segundo

STRIP_START = (256, 1792)   # donde nace el heroe en la ROM cathedral-* (strip.c: STRIP_W_PX / 2, STRIP_WIN_H_PX - 256)
HERO_SCREEN_X = 128         # con la camara sin recortar el heroe queda en el centro horizontal
HERO_FEET_Y = 131           # y de pantalla de sus pies en reposo (medido en las capturas de 00_stage)
MUZZLE_H = sb.MUZZLE_H      # el rayo sale 21 px sobre los pies: el lapiz se lee a esa altura
AIM_Y = HERO_FEET_Y - MUZZLE_H


def fields():
    f = {k: dict(v) for k, v in sb.FIELDS.items()}
    f["god"] = {"symbol": "ps", "offset": 20, "type": "s32"}       # PlayerState.god_mode
    f["hp"] = {"symbol": "ps", "offset": 0, "type": "s32"}
    f["force_drop"] = {"symbol": "fd", "offset": 0, "type": "u8"}  # g_pickup_force_drop (solo con SANDBOX)
    return f


def scenario(name, description, steps):
    return {
        "name": name,
        "description": description,
        "evidence_only": True,
        "state": {"symbols": {"sb": "g_sandbox", "ps": "g_player_state", "fd": "g_pickup_force_drop"},
                  "default_symbol": "sb", "fields": fields()},
        "steps": steps,
    }


def stage(player, enemies, extra_pokes=()):
    """Escena del buzon sandbox: heroe invulnerable con el francotirador, enemigos quietos."""
    steps = sb.setup_steps(player, "sniper", 0, enemies, flags=sb.FLAG_CLEAR | sb.FLAG_FREEZE_AI | sb.FLAG_GOD)
    # el buzon deja la vida al maximo: los pokes extra (vida, drop forzado) van despues del ack
    if extra_pokes:
        steps.append({"poke": list(extra_pokes), "frames": 1})
    return steps


# --- Los 4 clips ---------------------------------------------------------------------------------------------
# loop: "search" = busca el salto menos visible (bucles ciclicos); (inicio, longitud) = tramo fijo de la accion.
def clip_catedral():
    player = STRIP_START
    # Horda: Exvotos (la masa lenta) con Cireneos y un Ojo por delante, al norte del heroe y despiertos.
    # Para el catedral no hay fila de rayo que respetar: solo suelo libre (las 4 primeras bandas de la tira estan despejadas).
    ex, ch, oj = sb.EXVOTO, sb.CHARGER, sb.SHOOTER
    horde = [(ex, 216, 1650), (ex, 256, 1640), (ex, 296, 1650), (ex, 236, 1610), (ex, 280, 1605), (ch, 190, 1620),
             (ch, 330, 1625), (ex, 205, 1570), (ex, 255, 1560), (ex, 305, 1575), (ex, 230, 1530), (oj, 270, 1500)]
    steps = sb.setup_steps(player, "sniper", 0, horde, flags=sb.FLAG_CLEAR | sb.FLAG_GOD)
    steps += [
        {"button_down": "UP", "frames": 30},
        {"frames": 200, "capture_sequence": "c1", "capture_every": 2},
    ]
    return scenario("intro_clip_catedral", "Heroe avanzando hacia el norte por la nave con una horda de Exvotos, Cireneos y un Ojo delante.", steps), "search"


def clip_apuntar():
    player = (330, STRIP_START[1])
    # Fila del rayo (regla 5): los tres enemigos al este del cañon y en la misma Y de suelo que el heroe.
    enemies = sb.check_beam(player, 0, [(sb.EXVOTO, player[0] + 30, player[1]),
                                         (sb.EXVOTO, player[0] + 50, player[1]),
                                         (sb.EXVOTO, player[0] + 70, player[1])])
    steps = stage(player, enemies)
    steps += [
        # 1) mover: cruceta a la izquierda (el lapiz aun no toca)
        {"button_down": "LEFT", "frames": 30, "capture_sequence": "c0", "capture_every": 2},
        # 2) apuntar y cargar: el lapiz sobre la fila del rayo (al este) planta al heroe y carga el disparo
        {"button_up": "LEFT", "tap": {"x": HERO_SCREEN_X + 60, "y": AIM_Y}, "frames": 34, "capture_sequence": "c1", "capture_every": 2},
        # 3) soltar: el rayo atraviesa a los tres enemigos de la fila
        {"release": True, "frames": 56, "capture_sequence": "c2", "capture_every": 2},
    ]
    return scenario("intro_clip_apuntar", "Heroe se mueve con la cruceta, apunta y carga el rayo con el lapiz y dispara a tres Exvotos en fila (un rayo mata a cada uno).", steps), (0, LOOP_TARGET)


def clip_marea():
    steps = [
        {"frames": 40},
        {"poke": [{"field": "god", "value": 1}], "frames": 1},
        {"button_down": "DOWN", "frames": 150},        # la marea (300 px debajo al empezar) entra por el borde inferior sobre el ~200
        {"frames": 200, "capture_sequence": "c1", "capture_every": 2},
    ]
    return scenario("intro_clip_marea", "Heroe retrocede hacia el sur mientras la marea real sube por el borde inferior.", steps), "search"


def clip_corazon():
    player = STRIP_START
    enemies = sb.check_beam(player, 0, [(sb.EXVOTO, player[0] + 44, player[1])])
    steps = stage(player, enemies, extra_pokes=[{"field": "hp", "value": 4},
                                                {"field": "force_drop", "value": 1}])
    steps += [
        {"frames": 6},                                   # el HUD redibuja la vida poked (4/5) antes de capturar
        {"frames": 10, "capture_sequence": "c0", "capture_every": 2},
        {"tap": {"x": HERO_SCREEN_X + 60, "y": AIM_Y}, "frames": 30, "capture_sequence": "c1", "capture_every": 2},
        # disparo: el enemigo muere, suelta un Sagrado Corazon y el heroe camina hasta pisarlo
        {"release": True, "button_down": "RIGHT", "frames": 56, "capture_sequence": "c2", "capture_every": 2},
        {"button_up": "RIGHT", "frames": 40, "capture_sequence": "c3", "capture_every": 2},
    ]
    return scenario("intro_clip_corazon", "Un enemigo muere al disparo, suelta un Sagrado Corazon y el heroe (4/5) lo pisa.", steps), (0, LOOP_TARGET)


CLIPS = {"catedral": clip_catedral, "apuntar": clip_apuntar, "marea": clip_marea, "corazon": clip_corazon}


# --- Emulador --------------------------------------------------------------------------------------------------
def run_scenario(name, scen_path):
    out = WORK_DIR / name
    if out.exists():
        for p in out.glob("*"):
            p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    rom = ROOT / f"dungeonds-{VARIANT}.nds"
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SKILL_SCRIPTS / "run-scenario.ps1"),
           "-ProjectPath", str(ROOT), "-RomPath", str(rom), "-ScenarioPath", str(scen_path), "-OutputPath", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:])
    if r.returncode not in (0, 1):
        raise SystemExit(f"run-scenario fallo ({r.returncode}): {r.stderr[-400:]}")
    return out


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
def pick_window(frames, loop):
    n = len(frames)
    if loop != "search":
        s, length = loop
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
        scen, loop = make()
        scen_path = ROOT / "scenarios" / f"intro_clip_{name}.json"
        scen_path.write_text(json.dumps(scen, indent=2) + "\n", encoding="utf-8")
        print(f"[{name}] {scen_path.name}")
        out = WORK_DIR / name if args.reuse else run_scenario(name, scen_path)
        files, frames = load_frames(out)
        print(f"  {len(frames)} imagenes capturadas")
        contact_sheet(frames, WORK_DIR / f"{name}_capturas.png", step=6)
        s, length = pick_window(frames, loop)
        win = frames[s:s + length]
        blob = encode(win)
        verify(blob, win)
        (OUT_DIR / f"{name}.bin").write_bytes(blob)
        contact_sheet(win, WORK_DIR / f"{name}_bucle.png", step=4)
        for k in (0, length // 2, length - 1):
            Image.fromarray(to_rgb(win[k])).save(WORK_DIR / f"{name}_f{k:02d}.png")
        print(f"  -> {OUT_DIR / (name + '.bin')}: {len(blob)} bytes, {length} imagenes (captura {s}..{s + length - 1})")


if __name__ == "__main__":
    main()
