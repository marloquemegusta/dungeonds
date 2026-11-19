#!/usr/bin/env python3
"""Genera los bucles de video de las tarjetas de introduccion (DESIGN.md 6.3, source/intro.c).

Cada clip es la pantalla inferior (256x192) de la ROM, ~2 s a 30 imagenes por segundo, capturada de DeSmuME y
guardada SIN PERDIDA en nitrofiles/intro/<nombre>.bin. `catedral` se graba con la variante `encuentros`; apuntar,
cobertura, remate y corazon se montan en el sandbox con tools/clip_scene.py (escena exacta: heroe, enemigos, vida,
planos) sobre `cathedral-sandbox` (remate: `remate-sandbox`, donde L es el remate y no cambia de arma).

Compilar los sandbox: build-project.ps1 -ProjectPath . -Variant cathedral-sandbox  (y -Variant remate-sandbox para el remate).
El Makefile de la plantilla ya no activa ENCOUNTERS_PROTO en las variantes sandbox (antes habia que pasar -Define -UENCOUNTERS_PROTO).

Flujo:  1) escribe scenarios/intro_clip_<nombre>.json   2) ejecuta cada escenario con run-scenario.ps1 sobre la
ROM `encuentros` (heroe invulnerable con g_enc_debug.dbg_god)   3) toma la mitad inferior de las capturas,
elige el tramo del bucle y lo codifica.

Uso (desde la raiz del repo / worktree):
    powershell -NonInteractive -ExecutionPolicy Bypass -File <skill>/scripts\build-project.ps1 -ProjectPath . -Variant encuentros
    python tools/gen_intro_clips.py                 # los 5 clips
    python tools/gen_intro_clips.py --only remate   # uno solo
    python tools/gen_intro_clips.py --reuse         # no vuelve a ejecutar el emulador (usa las capturas de artifacts/intro_clips)
    python tools/gen_intro_clips.py --verify-bin nitrofiles/intro/remate.bin   # descodifica y compara con las capturas

Formato .bin (little endian; el descodificador es video_step() en source/intro.c):
    u16 magic 0x4956 | u16 n | u32 max_rec | u32 max_dec | u32 off[n + 2]
    registro 0 = imagen completa (96 KB de pixeles, comprimida con LZ10 de la BIOS); 1..n-1 = delta con la anterior;
    n = delta de la ultima a la 0 (cierra el bucle). Un delta es: s8 dx, s8 dy (nueva[i] = vieja[i + dy*256 + dx],
    compensacion del scroll) + palabras u16 (tipo << 14 | cuenta): 0 saltar, 1 literales, 2 repetir un pixel.
    Si el registro empieza por 0x10 esta comprimido con LZ10 (swiDecompressLZSSWram); dx esta en [-6, 6],
    asi que no hay ambiguedad. Pixeles BGR555 con el bit 15 puesto.
Regla 5 de AGENTS.md: los escenarios colocan a cada enemigo y al heroe donde el efecto de verdad ocurre.
"""
import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox_scenes as sb  # noqa: E402
from clip_scene import ClipScene, Enemy, in_frame, to_screen  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts")
VARIANT = "encuentros"
OUT_DIR = ROOT / "nitrofiles" / "intro"
WORK_DIR = ROOT / "artifacts" / "intro_clips"
W, H = 256, 192
NPIX = W * H
MAGIC = 0x4956
LOOP_TARGET = 60            # imagenes por bucle: 2 s a 30 imagenes por segundo
SLOT = 124                  # sizeof(Enemy) en la ROM encuentros
ELF = "../.ds-game-dev/build/out/dungeonds-encuentros.elf"
STRIP_START = (256, 1792)   # donde nace el heroe (ROM encuentros y cathedral-sandbox)
MUZZLE_H = sb.MUZZLE_H      # el rayo sale 21 px sobre los pies


def fields():
    f = {
        "woken": {"offset": 4, "type": "u8"}, "alive": {"offset": 61, "type": "u8"},
        "dbg_auto_pick": {"symbol": "dbg", "offset": 1, "type": "u8"},
        "dbg_god": {"symbol": "dbg", "offset": 2, "type": "u8"},
        "dbg_force_plant": {"symbol": "dbg", "offset": 10, "type": "u8"},
        "dbg_force_tier": {"symbol": "dbg", "offset": 11, "type": "u8"},
        "dbg_restart": {"symbol": "dbg", "offset": 12, "type": "u8"},
        "dbg_up4": {"symbol": "dbg", "offset": 17, "type": "u8"},     # el heroe empieza este numero de pasos de 4 px mas arriba
        "relicarios": {"offset": 10, "type": "u16"}, "dones": {"offset": 6, "type": "u8"},
        "hero_x": {"symbol": "nav", "offset": 0, "type": "s32"},
        "hero_y": {"symbol": "nav", "offset": 4, "type": "s32"},
        "relic_x": {"symbol": "stats", "offset": 136, "type": "s16"},   # dbg_relic_x: relicario que ve el heroe (px de suelo)
        "relic_y": {"symbol": "stats", "offset": 138, "type": "s16"},
    }
    for slot in range(16):
        f[f"a{slot}"] = {"symbol": "en", "offset": slot * SLOT + 24, "type": "s32"}
    return f


def scenario(name, description, steps):
    return {
        "name": name,
        "description": description,
        "suite": False,
        "evidence_only": True,
        "state": {"elf": ELF,
                  "symbols": {"stats": "g_enc_stats", "dbg": "g_enc_debug", "nav": "g_nav_state", "en": "g_enemies"},
                  "default_symbol": "stats", "fields": fields()},
        "steps": steps,
    }


def kill_others(keep, n=16):
    return [{"field": f"a{i}", "value": 0} for i in range(n) if i != keep]


def start(plant, tier, keep=None):
    """Reinicia el primer encuentro con una planta y tier forzados (g_enc_debug)."""
    steps = [{"frames": 20},
             {"poke": [{"field": "dbg_god", "value": 1}, {"field": "dbg_auto_pick", "value": 1}], "frames": 2},
             {"poke": [{"field": "dbg_force_plant", "value": plant}, {"field": "dbg_force_tier", "value": tier},
                       {"field": "dbg_restart", "value": 1}], "frames": 40}]
    if keep is not None:
        steps.append({"poke": kill_others(keep), "frames": 1})
    return steps


# --- Los 5 clips (tarjetas en el orden de source/intro.c) ----------------------------------------------------
# loop: "search" = busca el salto menos visible (bucles ciclicos); (inicio, longitud) = tramo fijo de la accion.
def clip_catedral():
    steps = start(1, 1)
    steps += [
        # entra por el borde hasta despertar la sala (la reja cae a su espalda) y sigue andando: la horda llega a la pantalla
        {"button_down": "UP", "wait_until": {"field": "woken", "min_value": 1, "timeout_frames": 1200}},
        {"button_down": "UP", "frames": 120, "capture_sequence": "c0", "capture_every": 2},
        {"button_up": "UP", "frames": 1},
    ]
    return scenario("intro_clip_catedral", "Heroe entra en la sala (procesion ligera); la reja cae a su espalda.", steps), "search"


def clip_apuntar():
    """cathedral-sandbox: Exvoto quieto; 1 el heroe anda, 2 apunta con el lapiz (el rayo se ve moverse), 3 carga, 4 dispara."""
    ex = (400, 1792)
    sc = ClipScene("apuntar", hero=(300, 1792), enemies=[Enemy("exvoto", *ex)], weapon="sniper",
                   description="Sandbox: Exvoto quieto; el heroe anda, apunta con el lapiz, carga y dispara.")
    sc.walk(["RIGHT"], 30, expect=(338, 1792), tol=14, show=[("exvoto", ex)])
    sc.sweep((ex[0], ex[1] - 34), ex, 30, expect=(338, 1792), tol=14, show=[("exvoto", ex)])
    sc.hold(28, show=[("exvoto", ex)])
    sc.fire(40, show=[("exvoto", ex)])
    return sc.scenario(), (0, 61, 3), "cathedral-sandbox"


def clip_relicario():
    """ROM `encuentros` (el juego real): el heroe, junto al primer relicario del pasillo (260, 984), lo rompe a tiros con el rayo
    y aparece la oferta de Don. dbg_up4 (EncDebug.start_up4) lo coloca en (256, 1040) al reiniciar; se vacian los enemigos de la sala
    para que la escena sea solo heroe y relicario. Camara de encuentros: x fija (cam_x = 128), cam_y = py - 132."""
    hero, rel = (256, 1040), (260, 984)
    if not in_frame(hero, rel, margin_x=20, margin_top=50):
        raise ValueError(f"[relicario] el relicario {rel} cae fuera del encuadre con el heroe en {hero}: pantalla {to_screen(hero, rel)}")
    sx, sy = to_screen(hero, rel, 12)                           # el rayo cruza el relicario a 12 px del suelo
    steps = [{"frames": 20}, {"poke": [{"field": "dbg_god", "value": 1}], "frames": 2},
             {"poke": [{"field": "dbg_up4", "value": (STRIP_START[1] - hero[1]) // 4}, {"field": "dbg_restart", "value": 1}], "frames": 60},
             {"poke": kill_others(-1), "frames": 2, "state_capture": "antes"},
             {"frames": 18, "capture_sequence": "c0", "capture_every": 2},                                   # 1: el relicario a la vista
             {"tap": {"x": sx, "y": sy}, "frames": 40, "capture_sequence": "c1", "capture_every": 2},       # 2: apunta (carga)
             {"release": True, "frames": 22, "capture_sequence": "c2", "capture_every": 2},                 # 3: dispara y lo rompe
             {"frames": 42, "capture_sequence": "c3", "capture_every": 2, "state_capture": "oferta"}]       # 4: la oferta de Don
    scen = scenario("intro_clip_relicario", "Encuentros: el heroe rompe a tiros el relicario del pasillo y aparece la oferta de Don.", steps)
    scen["assertions"] = {"state_changes": [
        {"at": "antes", "field": "relicarios", "equals": 0}, {"at": "oferta", "field": "relicarios", "min_value": 1},
        {"at": "oferta", "field": "dones", "min_value": 1},                                                 # se ofrece el Don
        {"at": "antes", "field": "hero_y", "min_value": (hero[1] - 4) * 256}, {"at": "antes", "field": "hero_y", "max_value": (hero[1] + 4) * 256}]}
    scen["evidence_only"] = False
    return scen, (0, 61, 3)


def clip_cobertura():
    """cathedral-sandbox, SIN modo dios: un Ojo (SHOOTER; la IA corre) al norte del bloque de bancos (280,1408) apunta hacia el sur
    con su banda; el heroe, al sur del bloque, se pega a la cara sur, se agacha solo y anda agachado a lo largo detras.
    Cubierto, el Ojo no gasta su rayo (ojo_hero_covered, enemy_ai.c) y el heroe no pierde vida (aserciones hp == 5).
    Huella del banco: x 288..351, y 1424..1511."""
    oj = (320, 1416)
    sc = ClipScene("cobertura", hero=(320, 1519), enemies=[Enemy("shooter", *oj)], weapon="sniper", god=False, freeze_ai=False,
                   description="Sandbox: un Ojo apunta desde el norte a traves de un bloque de bancos; el heroe, agachado detras, no recibe dano.")
    show = [("ojo", oj, 22), ("banco", (320, 1468))]          # el Ojo se ve de cuerpo casi entero (margen superior 22 px)
    sc.wait(8, expect=(320, 1519), tol=2, show=show)
    sc.walk(["UP"], 14, expect=(320, 1515), tol=4, show=show)
    sc.walk(["LEFT"], 50, expect=(296, 1515), tol=8, show=show)
    sc.walk(["RIGHT"], 50, expect=(320, 1515), tol=8, show=show)
    for c in ("c0_fin", "c1_fin", "c2_fin", "c3_fin"):
        sc.assert_at(c, "hp", equals=5)                        # ni un punto de vida perdido, sin god
    for c in ("c2_fin", "c3_fin"):
        sc.assert_at(c, "crouched", equals=1)
    sc.assert_at("c0_fin", "crouched", equals=0)
    return sc.scenario(), (0, 61, 3), "cathedral-sandbox"


def clip_remate():
    """remate-sandbox: REAL. Un Exvoto quieto a 70 px con 250 PV (los de la ROM por encuentros; el sandbox lo crea con 100 y el
    rayo, 150, lo mataria: se le pone hp y max_hp = 250 justo tras colocarlo y antes de disparar). El disparo real lo deja a 100
    PV (<= 50 %) y tambaleando (gameplay.c); el heroe se acerca y pulsa L (remate)."""
    ex = (330, 1792)
    sc = ClipScene("remate", hero=(260, 1792), enemies=[Enemy("exvoto", *ex)], weapon="sniper", every=2,
                   description="Sandbox: un tiro deja al Exvoto tambaleando; el heroe se acerca, pulsa L y lo remata.")
    sc.poke(en0_hp=250, en0_maxhp=250)                       # vida de la ROM por encuentros
    show = [("exvoto", ex)]
    sc.aim(ex, 24, expect=(260, 1792), tol=3, show=show)
    sc.fire(6, show=show)
    sc.sample("tras_tiro")
    sc.assert_at("tras_tiro", "en0_state", equals=18)            # WOBBLE: el tiro lo dejo tambaleando (de verdad)
    sc.assert_at("tras_tiro", "en0_hp", equals=100)
    sc.walk(["RIGHT"], 16, expect=(280, 1792), tol=6, show=show)
    sc.stop()
    sc.press("L", 88, hold=4, show=show)
    sc.sample("fin")
    sc.assert_at("fin", "en0_active", equals=0)                  # el remate lo mato
    return sc.scenario(), (0, 61, 3), "remate-sandbox"   # VID_MAX_N de intro.c = 64


def clip_corazon():
    """cathedral-sandbox: heroe con 2 de 5 de vida; mata a un Exvoto quieto (g_pickup_force_drop fuerza el corazon),
    anda hasta el corazon, lo pisa y los Sagrados Corazones del HUD suben."""
    ex = (320, 1792)
    sc = ClipScene("corazon", hero=(260, 1792), enemies=[Enemy("exvoto", *ex)], weapon="sniper", hp=2,
                   description="Sandbox: heroe con 2 de 5 de vida; mata a un Exvoto, suelta un corazon, lo pisa y se cura.")
    show = [("exvoto", ex)]
    sc.sweep((ex[0], ex[1] - 30), ex, 28, expect=(260, 1792), tol=2, show=show)
    sc.poke(force_drop=1)                                   # el siguiente enemigo que muera suelta corazon
    sc.fire(20, show=show)
    sc.walk(["RIGHT"], 44, expect=(315, 1792), tol=12, show=[("corazon", ex)])
    sc.walk(["LEFT"], 44, expect=(262, 1792), tol=12, show=[("corazon", ex)])     # vuelve hacia donde empezo: el corte del bucle se nota menos
    return sc.scenario(), (0, 61, 3), "cathedral-sandbox"


CLIPS = {"catedral": clip_catedral, "apuntar": clip_apuntar, "cobertura": clip_cobertura, "remate": clip_remate, "relicario": clip_relicario,
         "corazon": clip_corazon}


# --- Emulador --------------------------------------------------------------------------------------------------
def run_scenario(name, scen_path, variant=VARIANT):
    out = WORK_DIR / name
    if out.exists():
        for p in out.glob("*"):
            p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    rom = ROOT / f"dungeonds-{variant}.nds"
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SKILL_SCRIPTS / "run-scenario.ps1"),
           "-ProjectPath", str(ROOT), "-RomPath", str(rom), "-ScenarioPath", str(scen_path), "-OutputPath", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:])
    if r.returncode not in (0, 1):
        raise SystemExit(f"run-scenario fallo ({r.returncode}): {r.stderr[-400:]}")
    return out


def print_samples(out):
    """Imprime hero_x/hero_y/crouched/hp y el enemigo 0 de cada state_capture (para calibrar coordenadas, regla 11)."""
    ev = out / "events.jsonl"
    if not ev.exists():
        return
    for line in ev.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("action") == "state_capture":
            st = d["state"]
            print(f"  [{d['name']}] f{d['frame']} hero=({st['hero_x'] / 256:.1f},{st['hero_y'] / 256:.1f}) crouched={st.get('crouched')} "
                  f"hp={st.get('hp')} en0=({st.get('en0_x', 0) / 256:.0f},{st.get('en0_y', 0) / 256:.0f}) active={st.get('en0_active')} "
                  f"hp0={st.get('en0_hp')} state0={st.get('en0_state')}")


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
        variant = made[2] if len(made) > 2 else VARIANT
        scen_path = ROOT / "scenarios" / f"intro_clip_{name}.json"
        scen_path.write_text(json.dumps(scen, indent=2) + "\n", encoding="utf-8")
        print(f"[{name}] {scen_path.name}")
        out = WORK_DIR / name if args.reuse else run_scenario(name, scen_path, variant)
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
