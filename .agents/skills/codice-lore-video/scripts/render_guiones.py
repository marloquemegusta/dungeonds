#!/usr/bin/env python3
"""Render vertical lore videos (1080x1920) straight from a markdown guiones file.

Uso: python render_guiones.py --guiones <md> [--solo 01,03] [--sin-voz] [--prefijo lore01]
"""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
ELEVEN_EXE = shutil.which("elevenlabs") or shutil.which("elevenlabs.exe") or "elevenlabs"

VOICE_ID = "5egO01tkUjEzu7xSSE8M"
MODEL_ID = "eleven_multilingual_v2"
STABILITY, SIMILARITY, STYLE, SPEED = "0.28", "0.80", "0.60", "1.0"

CHAR_SETTINGS = ("0.65", "0.85", "0.15", "1.0")   # estable: con mas emocion la voz pierde el acento y alarga palabras
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
DIR_INDEX = {d: i for i, d in enumerate(DIRS)}  # file prefix index
TURN_ORDER = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]
MOSAIC_DEFAULT = ["corazon_disparo", "exvoto_walk", "cireneo_walk", "ojo_walk"]
OUTRO_TEXT = "Próximamente en tu Nintendo DS."
LEAD_IN, PAUSE_PHRASE, PAUSE_PART = 0.10, 0.45, 0.85
BGM = os.path.join(ROOT, "assets", "music", "cathedral_battle_loop.wav")

FONT_REG = "C\\:/Windows/Fonts/pala.ttf"
FONT_BOLD = "C\\:/Windows/Fonts/palab.ttf"
FONT_ITAL = "C\\:/Windows/Fonts/palai.ttf"


CUT_SEQ = ["S", "SE", "SW", "E", "W", "S", "NE", "SW", "SE", "NW", "S", "W", "E", "N"]
CUT_CLOSE_DIR = "S"
PUSH_Z = (1.0, 1.12)     # empuje lento de cada corte
CLOSE_Z = (1.65, 1.80)   # primer plano [cerca]
FPS = 30


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def get_duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path], text=True).strip()
    return float(out)


def slugify(name):
    s = unicodedata.normalize("NFKD", name.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


# ---------------------------------------------------------------- parsing
def parse_guiones(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    videos, cur, part = [], None, None
    voices = {"narrador": VOICE_ID}
    in_voces = False
    head_re = re.compile(r"^##\s+(\d{2})\s*·\s*(.+?)\s*—\s*(.+?)\s*$")
    for ln in lines:
        s = ln.strip()
        if ln.startswith("## "):
            in_voces = s.lower() == "## voces"
            m = head_re.match(ln)
            if m:
                cur = {"num": m.group(1), "header": m.group(2), "name": m.group(3), "parts": []}
                videos.append(cur)
            else:
                cur = None
            part = None
            continue
        if s == "---":
            cur, part = None, None
            in_voces = False
            continue
        if in_voces:
            mv = re.match(r"^-\s*([^:]+?)\s*:\s*(\S+)", ln)
            if mv:
                voices[mv.group(1).strip().lower()] = mv.group(2).strip()
            continue
        if cur is None:
            continue
        if ln.startswith("### "):
            fields = [x.strip() for x in ln[4:].split("·")]
            kind = fields[0].lower()
            if kind.startswith("parte"):
                anims = [a.strip() for a in fields[1].split("+")]
                part = {"type": "char", "anim": anims[0], "anim_b": anims[1] if len(anims) > 1 else None,
                        "dir": fields[2].strip(), "phrases": [], "mods": parse_mods(fields[3:]),
                        "cuts": None}
                if part["dir"].lower().startswith("cortes"):
                    lst = [x.strip().upper() for x in part_dir_list(fields[2])]
                    for x in lst:
                        if x not in DIR_INDEX:
                            sys.exit(f"Direccion desconocida en cortes: {x}")
                    part["dir"] = "cortes"
                    part["cuts"] = lst or None
            elif kind.startswith("ficha"):
                rect = None
                if len(fields) > 2:
                    rect = [int(v) for v in fields[2].split(",")]
                part = {"type": "card", "png": fields[1], "rect": rect, "phrases": []}
            else:
                part = None
                continue
            cur["parts"].append(part)
            continue
        if part is not None and ln.startswith("- "):
            txt, stage = strip_tag(ln[2:].strip())
            part["phrases"].append({"text": txt, "voices": None, "cerca": bool(stage and stage["cerca"]),
                                    "stage": stage})
        elif part is not None and ln.startswith(">"):
            rest = ln[1:].strip()
            stage = None
            mt = TAG_RE.match(rest)
            if mt:  # etiqueta de plano antes de los nombres: > [S] Jimena + Aldonza: «...»
                stage = parse_stage(mt.group(1))
                rest = rest[mt.end():]
            mq = re.match(r"^([^:]+?)\s*:\s*(.+?)\s*$", rest)
            if mq:
                txt, stage2 = strip_tag(mq.group(2).strip())
                stage = stage2 or stage
                txt = txt.strip("«»\"“”").strip()
                names = [x.strip() for x in mq.group(1).split("+")]
                part["phrases"].append({"text": txt, "voices": names, "cerca": bool(stage and stage["cerca"]),
                                        "stage": stage})
    return videos, voices


def part_dir_list(field):
    """'cortes S,SE,W' -> ['S','SE','W']."""
    rest = field.strip()[len("cortes"):]
    return [x for x in re.split(r"[,\s]+", rest) if x]


TAG_RE = re.compile(r"^\[([^\]]*)\]\s*")
POS_X = ("izq", "der", "fuera-izq", "fuera-der")
POS_Y = ("arriba", "abajo", "fuera-arriba", "fuera-abajo")


def parse_motion(s):
    """'centro>fuera-izq' -> (desde, hasta); 'izq' -> (izq, None). Cada extremo = lista de atomos ('izq+arriba')."""
    if not s:
        return None
    ends = [e.strip().lower() for e in s.split(">")]
    if len(ends) > 2 or not all(ends):
        sys.exit(f"Posicion no valida: {s}")
    out = []
    for e in ends:
        atoms = [a.strip() for a in e.split("+")]
        for a in atoms:
            if a != "centro" and a not in POS_X + POS_Y:
                sys.exit(f"Posicion desconocida: {a}")
        out.append(atoms)
    return (out[0], out[1] if len(out) > 1 else None)


def parse_stage(inner):
    """Contenido de [..]: fichas separadas por ' · ' (ver guiones.md). Devuelve el plano o sale con error."""
    st = {"cerca": False, "dir": None, "all": None, "A": None, "B": None, "staged": False, "lejos": False, "paso": None}
    for tok in [t.strip() for t in inner.split("·") if t.strip()]:
        if tok.lower() == "cerca":
            st["cerca"] = True
            continue
        if tok.lower() in ("natural", "lento"):
            st["paso"] = tok.lower()
            continue
        if tok.lower() == "lejos":
            st["lejos"] = True
            continue
        m = re.match(r"^(?:([AB])\s+)?([A-Za-z]{1,2})(?:\s+(\S.*))?$", tok)
        if not m or m.group(2).upper() not in DIR_INDEX:
            sys.exit(f"Ficha de plano desconocida: [{tok}]")
        spec = {"dir": m.group(2).upper(), "motion": parse_motion(m.group(3))}
        if m.group(1):
            st[m.group(1)] = spec
        else:
            st["all"] = spec
            st["dir"] = spec["dir"]
    st["staged"] = bool(st["A"] or st["B"] or (st["all"] and st["all"]["motion"]))
    return st


def strip_tag(text):
    """Quita el marcador [..] inicial; devuelve (texto, plano|None)."""
    m = TAG_RE.match(text)
    if m:
        return text[m.end():], parse_stage(m.group(1))
    return text, None


def parse_mods(fields):
    mods = {"lento": 1.0, "inverso": False, "una_vez": False, "ida_vuelta": False,
            "escala_b": 0.93, "separacion": 120}
    for f in fields:
        f = f.strip().lower()
        if f.startswith("lento"):
            mods["lento"] = float(f.split()[1].replace(",", "."))
        elif f == "inverso":
            mods["inverso"] = True
        elif f == "una vez":
            mods["una_vez"] = True
        elif f.startswith("escala b"):
            mods["escala_b"] = float(f.split()[2].replace(",", "."))
        elif f.startswith("separaci"):
            mods["separacion"] = int(f.split()[1])
        elif f == "ida y vuelta":
            mods["ida_vuelta"] = True
        elif f:
            sys.exit(f"Modificador desconocido: {f}")
    return mods


# ---------------------------------------------------------------- images
def extract_frames_on_black(src_gif):
    im = Image.open(src_gif)
    frames, durs = [], []
    try:
        while True:
            bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
            bg.alpha_composite(im.convert("RGBA"))
            rgb = bg.convert("RGB")
            px = rgb.load()
            for yy in range(rgb.height):
                for xx in range(rgb.width):
                    r, g, b = px[xx, yy]
                    if r <= 24 and g <= 24 and b <= 30:
                        px[xx, yy] = (0, 0, 0)
            frames.append(rgb)
            durs.append(im.info.get("duration", 130) or 130)
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return frames, durs


def save_gif(frames, durs, dst):
    frames[0].save(dst, save_all=True, append_images=frames[1:], duration=durs, loop=0)


def anim_dir(anim):
    return os.path.join(ROOT, "assets", "sprites", "bestiary", anim, "dirs")


def dir_gif(anim, d):
    return os.path.join(anim_dir(anim), f"{DIR_INDEX[d]}_{d}.gif")


def apply_mods(frames, durs, mods):
    frames, durs = list(frames), list(durs)
    if mods["inverso"]:
        frames.reverse()
        durs.reverse()
    if mods["ida_vuelta"] and len(frames) > 2:
        frames += frames[-2:0:-1]
        durs += durs[-2:0:-1]
    if mods["lento"] != 1.0:
        durs = [max(20, int(round(x * mods["lento"]))) for x in durs]
    return frames, durs


DUO_W = 206          # 1080 / 5.25: lienzo de la pareja a la escala de un solo personaje
DUO_SLOW = 1.15      # B anda un 15 % más lento
DUO_OFFSET_S = 0.4   # desfase de paso del segundo personaje


def feet_line(frames):
    """Fila más baja con píxeles no negros en todos los fotogramas (la línea del suelo)."""
    low = 0
    for fr in frames:
        bb = fr.point(lambda v: 255 if v > 0 else 0).convert("L").getbbox()
        if bb:
            low = max(low, bb[3])
    return low or frames[0].height


def compose_duo(fa, fb, escala, sep, feet_a, feet_b):
    """B (más bajo, detrás) y A (delante), centros de celda a +-sep/2 px de vídeo del centro."""
    off = int(round(sep / 5.25))
    w = int(round(160 * escala))
    c = Image.new("RGB", (DUO_W, 160), (0, 0, 0))
    bb = fb.resize((w, w), Image.NEAREST)
    # B va a la derecha, A a la izquierda; pies de B sobre la misma fila que los de A
    by = feet_a - int(round(feet_b * escala))
    c.paste(bb, (DUO_W // 2 + off - w // 2, by))
    ax = DUO_W // 2 - off - 80
    mask = fa.point(lambda v: 255 if v > 0 else 0).convert("L")
    c.paste(fa, (ax, 0), mask)
    return c


def char_frames(part, d):
    """Fotogramas (y duraciones) de la parte en la direccion d; lienzo doble si es pareja."""
    f, du = apply_mods(*extract_frames_on_black(dir_gif(part["anim"], d)), part["mods"])
    if part.get("anim_b"):
        fb, _ = apply_mods(*extract_frames_on_black(dir_gif(part["anim_b"], d)), part["mods"])
        k = max(1, int(round(DUO_OFFSET_S * 1000 / (sum(du) / len(du))))) % len(fb)
        fa_feet, fb_feet = feet_line(f), feet_line(fb)
        # B marcha ~15 % más lento: su fotograma avanza cada DUO_SLOW veces la duración de A
        out, tt = [], 0.0
        for i, a in enumerate(f):
            bi = (k + int(tt / (DUO_SLOW * du[0]))) % len(fb)
            out.append(compose_duo(a, fb[bi], part["mods"]["escala_b"], part["mods"]["separacion"],
                                   fa_feet, fb_feet))
            tt += du[i]
        f = out
    return f, du


def build_char_gif(part, dst):
    dirs = TURN_ORDER if part["dir"].lower() == "girando" else [part["dir"].upper()]
    frames, durs = [], []
    for d in dirs:
        f, du = char_frames(part, d)
        frames += f
        durs += du
    save_gif(frames, durs, dst)


def pick_cut_dirs(part, n, state):
    """Direcciones de los n cortes de una parte (nunca la misma dos veces seguidas);
    state continua entre partes del mismo video."""
    seq = part["cuts"] or CUT_SEQ
    out = []
    for j in range(n):
        st = part["_stage"][j]
        if st and st["staged"]:
            d = (st["A"] or st["all"] or st["B"])["dir"]
        elif st and st["dir"]:
            d = st["dir"]
        elif part["_cerca"][j] and not part["cuts"]:
            d = CUT_CLOSE_DIR
            if d == state["last"]:
                d = next(x for x in CUT_SEQ if x != state["last"])
        else:
            d = seq[state["i"] % len(seq)]
            state["i"] += 1
            guard = 0
            while d == state["last"] and len(set(seq)) > 1 and guard < len(seq):
                d = seq[state["i"] % len(seq)]
                state["i"] += 1
                guard += 1
        out.append(d)
        state["last"] = d
    return out


def build_shot(part, d, dur, close, dst):
    """Video sin perdida (840x840, o 1080x840 en pareja) de un corte: una direccion fija con empuje lento.

    Se amplia primero con vecino mas cercano y el zoom se hace con muestreo bicubico de ventana
    fraccionaria: movimiento suave sin saltos de pixel, y la ventana nunca sale de la caja."""
    frames, durs = char_frames(part, d)
    W, H = (1080, 840) if part.get("anim_b") else (840, 840)
    sx, sy = W / frames[0].width, H / frames[0].height
    big = [fr.resize((W, H), Image.NEAREST) for fr in frames]
    bb = None
    for fr in frames:
        b = fr.point(lambda v: 255 if v > 0 else 0).convert("L").getbbox()
        if b:
            bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
    bb = bb or (0, 0, frames[0].width, frames[0].height)
    ax = (bb[0] + bb[2]) / 2 * sx
    ay = (bb[1] + (bb[3] - bb[1]) * (0.26 if close else 0.38)) * sy
    z0, z1 = CLOSE_Z if close else PUSH_Z
    total = sum(durs)
    nfr = int(dur * FPS) + 3
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "rgb24", dst]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(nfr):
        t_ms = k * 1000.0 / FPS
        tm = min(t_ms, total - 1e-6) if part["mods"]["una_vez"] else t_ms % total
        idx, acc = 0, 0
        for idx, du in enumerate(durs):
            acc += du
            if tm < acc:
                break
        u = min(1.0, k / max(1.0, dur * FPS))
        z = z0 + (z1 - z0) * u
        hw, hh = W / (2 * z), H / (2 * z)
        cx = min(max(ax, hw), W - hw)
        cy = min(max(ay, hh), H - hh)
        box = (cx - hw, cy - hh, cx + hw, cy + hh)
        im = big[idx].transform((W, H), Image.EXTENT, box, resample=Image.BICUBIC)
        pr.stdin.write(im.tobytes())
    pr.stdin.close()
    if pr.wait():
        sys.exit("ffmpeg fallo al crear un corte")


# ---------------------------------------------------------------- planos escenificados
STAGE_SCALE = 5.25     # escala pantalla/sprite de un personaje (840 / 160)
STAGE_W, STAGE_H = 1080, 840
STAGE_MARGIN = 70      # margen de izq/der/arriba/abajo respecto al borde
STAGE_WIDE = 0.6       # plano general: escala de los planos con trayecto/posiciones (cerca = 1.0)
STAGE_GROUND_Y = 0.80  # fila del suelo por defecto (fraccion del alto)
STAGE_FADE = 40        # px de fundido arriba y abajo de la caja
RATE_MIN, RATE_MAX = 0.15, 1.6   # ritmo de paso; bajo 0.3 la marcha va a camara lenta
STAGE_ZOOM = (1.0, 1.05)   # empuje suave solo en planos quietos
# Avance del cuerpo por fotograma de animacion (px de celda 160x160, a 1x) para que el pie apoyado no patine.
# Medido barriendo la velocidad y buscando donde el pie apoyado queda quieto en pantalla (E 3.9, S 3.9, SE 3.0,
# SW 3.6); coincide con la velocidad del juego (speedFixed8_8 89/256 px/tick x 11 ticks/fotograma = 3.82).
# W/N/NE/NW no se pueden medir bien (pie tapado o ruido) y se copian por simetria. exvoto_walk_b es el mismo rig.
STRIDE_PX_FRAME = {"E": 3.85, "W": 3.85, "S": 3.85, "N": 3.85, "SE": 3.3, "SW": 3.3, "NE": 3.3, "NW": 3.3}
PASO = "lento"   # 'lento': el trayecto dura todo el plano (ritmo bajo); 'natural': ritmo 1.0 y llega antes
_FRAMES = {}


def load_dir(anim, d, mods):
    key = (anim, d, mods["inverso"], mods["ida_vuelta"], mods["lento"])
    if key not in _FRAMES:
        _FRAMES[key] = apply_mods(*extract_frames_on_black(dir_gif(anim, d)), mods)
    return _FRAMES[key]


def sprite_mask(im):
    r, g, b = im.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > 0 else 0)


def build_staged_shot(part, st, dur, dst):
    """Plano escenificado 1080x840: cada figura con su direccion y su trayecto; lo que sale del lienzo se recorta."""
    W, H = STAGE_W, STAGE_H
    mods = part["mods"]
    sep = mods["separacion"]
    duo = bool(part.get("anim_b"))
    figs = []
    k0 = 1.0 if st["cerca"] else STAGE_WIDE
    for name, anim, slot, scale in (("A", part["anim"], W // 2, STAGE_SCALE * k0),
                                    ("B", part.get("anim_b"), W // 2, STAGE_SCALE * k0 * mods["escala_b"])):
        if not anim:
            continue
        spec = st[name] or st["all"] or {"dir": st["dir"] or "S", "motion": None}
        frames, durs = load_dir(anim, spec["dir"], mods)
        bbs = [im.point(lambda v: 255 if v > 0 else 0).convert("L").getbbox() for im in frames]
        bbs = [b for b in bbs if b]
        feet = max(b[3] for b in bbs)
        top = min(b[1] for b in bbs)
        halfw = max(max(abs(b[0] - 80), abs(b[2] - 80)) for b in bbs) * scale
        figs.append({"name": name, "anim": anim, "spec": spec, "grouped": not st[name], "slot": slot,
                     "scale": scale, "off": slot - W // 2, "frames": frames, "durs": durs, "feet": feet,
                     "halfw": halfw, "height": (feet - top) * scale, "order": len(figs)})
    # huecos del duo: lado a lado sin solaparse (separacion minima = suma de semianchos)
    if duo:
        spacing = max(2 * sep * k0, 0.95 * (figs[0]["halfw"] + figs[1]["halfw"]))
        figs[0]["slot"], figs[1]["slot"] = W / 2 - spacing / 2, W / 2 + spacing / 2
        for f in figs:
            f["off"] = f["slot"] - W / 2
    y_def = STAGE_GROUND_Y * H
    group = [f for f in figs if f["grouped"] and f["spec"]["motion"]]
    gw = max([f["halfw"] + abs(f["off"]) for f in group] or [0])
    gh = max([f["height"] for f in group] or [0])

    def endpoint(f, atoms):
        # figura con ficha propia: sus medidas; ficha comun: las del grupo, desplazado a su hueco
        hw, hh, off = (gw, gh, f["off"]) if f["grouped"] else (f["halfw"], f["height"], 0)
        x, y = f["slot"], y_def
        for a in atoms:
            if a == "izq":
                x = hw + STAGE_MARGIN + off
            elif a == "der":
                x = W - hw - STAGE_MARGIN + off
            elif a == "fuera-izq":
                x = -(hw + 10) + off
            elif a == "fuera-der":
                x = W + hw + 10 + off
            elif a == "arriba":
                y = hh + STAGE_MARGIN
            elif a == "abajo":
                y = H - STAGE_MARGIN
            elif a == "fuera-arriba":
                y = -10
            elif a == "fuera-abajo":
                y = H + hh + 10
        return x, y

    any_move = False
    for f in figs:
        mo = f["spec"]["motion"]
        p0 = endpoint(f, mo[0]) if mo else (f["slot"], y_def)
        p1 = endpoint(f, mo[1]) if mo and mo[1] else p0
        f["p0"], f["p1"] = p0, p1
        dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        cyc = sum(f["durs"]) / 1000.0
        f["rate_idle"] = 1.0 / (DUO_SLOW if (duo and f["name"] == "B") else 1.0)
        f["rate"], f["t_move"], f["t_start"] = f["rate_idle"], 0.0, 0.0
        if dist >= 1.0:
            any_move = True
            mean_s = cyc / len(f["frames"])  # duracion media de un fotograma
            nominal = STRIDE_PX_FRAME[f["spec"]["dir"]] * f["scale"] / mean_s  # px/s en pantalla con rate 1
            natural = (st["paso"] or PASO) == "natural"
            r = (dist / dur) / nominal
            if natural:
                f["rate"] = f["rate_idle"]
                f["t_move"] = dist / (nominal * f["rate"])
                if f["t_move"] > dur:   # no llega a ritmo natural: acelera lo justo
                    f["rate"] = min(RATE_MAX, r)
                    f["t_move"] = dist / (nominal * f["rate"])
                    if f["t_move"] > dur:
                        print(f"  AVISO: {f['name']} no llega a su posicion en {dur:.1f}s (necesita rate {r:.2f})")
                if mo[1] and any(a.startswith("fuera-") for a in mo[1]) and f["t_move"] < dur:
                    f["t_start"] = dur - f["t_move"]  # salida: sale justo al final del plano
            elif r < RATE_MIN:
                f["rate"], f["t_move"] = RATE_MIN, dist / (nominal * RATE_MIN)
            elif r > RATE_MAX:
                f["rate"], f["t_move"] = RATE_MAX, dist / (nominal * RATE_MAX)
                print(f"  AVISO: {f['name']} no llega a su posicion en {dur:.1f}s (necesita rate {r:.2f})")
            else:
                f["rate"], f["t_move"] = r, dur
            print(f"    {f['name']} {f['spec']['dir']}: {dist:.0f}px, rate {f['rate']:.2f}, "
                  f"anda {min(f['t_move'], dur):.1f}s de {dur:.1f}s")
    # fotogramas ampliados (vecino mas cercano) con su mascara
    for f in figs:
        sz = int(round(160 * f["scale"]))
        f["big"] = [(im.resize((sz, sz), Image.NEAREST), sprite_mask(im).resize((sz, sz), Image.NEAREST))
                    for im in f["frames"]]
        f["sz"] = sz
        f["phase"] = DUO_OFFSET_S * 1000 if duo and f["name"] == "B" else 0.0
    zoom = (1.0, 1.0) if any_move else STAGE_ZOOM
    nfr = int(dur * FPS) + 3
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "rgb24", dst]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    dt = 1000.0 / FPS
    ramp = Image.new("L", (1, H), 255)
    for yy in range(STAGE_FADE):
        v = int(255 * (yy + 0.5) / STAGE_FADE)
        ramp.putpixel((0, yy), v)
        ramp.putpixel((0, H - 1 - yy), v)
    fade_mask = ramp.resize((W, H), Image.NEAREST).convert("RGB")
    for k in range(nfr):
        t = k / FPS
        cur = []
        for f in figs:
            moving = f["t_move"] > 0 and f["t_start"] <= t < f["t_start"] + f["t_move"]
            u = min(1.0, max(0.0, (t - f["t_start"]) / f["t_move"])) if f["t_move"] > 0 else 0.0
            px = f["p0"][0] + (f["p1"][0] - f["p0"][0]) * u
            py = f["p0"][1] + (f["p1"][1] - f["p0"][1]) * u
            total = sum(f["durs"])
            tm = f["phase"] % total
            acc, idx = 0, 0
            for idx, du in enumerate(f["durs"]):
                acc += du
                if tm < acc:
                    break
            f["phase"] += dt * (f["rate"] if moving else f["rate_idle"])
            cur.append((py, f["order"], f, px, idx))
        cur.sort(key=lambda c: (c[0], c[1]))  # el mas cercano a camara (pies mas abajo) delante
        canvas = Image.new("RGB", (W, H), (0, 0, 0))
        for py, _, f, px, idx in cur:
            spr, msk = f["big"][idx]
            canvas.paste(spr, (int(round(px - f["sz"] / 2)), int(round(py - f["feet"] * f["scale"]))), msk)
        canvas = ImageChops.multiply(canvas, fade_mask)
        if zoom[1] != 1.0:
            u = min(1.0, k / max(1.0, dur * FPS))
            z = zoom[0] + (zoom[1] - zoom[0]) * u
            hw, hh = W / (2 * z), H / (2 * z)
            cx, cy = W / 2, min(max(H * 0.55, hh), H - hh)
            canvas = canvas.transform((W, H), Image.EXTENT, (cx - hw, cy - hh, cx + hw, cy + hh),
                                      resample=Image.BICUBIC)
        pr.stdin.write(canvas.tobytes())
    pr.stdin.close()
    if pr.wait():
        sys.exit("ffmpeg fallo al crear un plano escenificado")


def build_mosaic(dst):
    lists = [extract_frames_on_black(dir_gif(a, "S")) for a in MOSAIC_DEFAULT]
    n = max(len(f) for f, _ in lists)
    durs = max(lists, key=lambda x: len(x[0]))[1]
    pos = [(0, 0), (160, 0), (0, 160), (160, 160)]
    out = []
    for i in range(n):
        c = Image.new("RGB", (320, 320), (0, 0, 0))
        for idx, (fr, _) in enumerate(lists):
            c.paste(fr[i % len(fr)], pos[idx])
        out.append(c)
    save_gif(out, durs, dst)


# ---------------------------------------------------------------- audio
def tts_cached(text, voice_id, settings):
    # "archivo:<ruta>" en la tabla de voces = audio ya grabado (p. ej. una muestra recortada)
    if voice_id.startswith("archivo:"):
        return os.path.join(ROOT, voice_id[len("archivo:"):].strip())
    cache = os.path.join(ROOT, "scratch", "codice-video", "voz")
    os.makedirs(cache, exist_ok=True)
    stab, sim, sty, spd = settings
    key = "|".join([voice_id, MODEL_ID, stab, sim, sty, spd, text])
    p = os.path.join(cache, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".mp3")
    if not os.path.exists(p):
        run([ELEVEN_EXE, "text-to-speech", "convert", "--voice-id", voice_id,
             "--model-id", MODEL_ID, "--voice-settings.stability", stab,
             "--voice-settings.similarity-boost", sim, "--voice-settings.style", sty,
             "--voice-settings.speed", spd, "--text", text, "-o", p])
    return p


def phrase_audio(ph, sin_voz, wdir, idx, voices):
    """Return path of an mp3/wav with the phrase and its duration."""
    text = ph["text"]
    if ph["voices"] and not sin_voz:
        files = [tts_cached(text, voices[n.lower()], CHAR_SETTINGS) for n in ph["voices"]]
        if len(files) == 1:
            return files[0], get_duration(files[0])
        p = os.path.join(wdir, f"vo_{idx:03d}_mix.wav")
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for f in files:
            cmd += ["-i", f]
        # cada voz a la misma sonoridad antes de mezclar, para que ninguna tape a la otra
        pre = "".join(f"[{k}:a]loudnorm=I=-18:TP=-2:LRA=11,aresample=44100[n{k}];" for k in range(len(files)))
        ins = "".join(f"[n{k}]" for k in range(len(files)))
        cmd += ["-filter_complex", f"{pre}{ins}amix=inputs={len(files)}:duration=longest:normalize=1",
                "-ar", "44100", "-ac", "1", p]
        run(cmd)
        return p, get_duration(p)
    if sin_voz:
        dur = max(1.2, len(text.split()) * 0.42)
        p = os.path.join(wdir, f"vo_{idx:03d}.wav")
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-t", f"{dur:.3f}", p, "-loglevel", "error"])
        return p, dur
    p = tts_cached(text, voices["narrador"], (STABILITY, SIMILARITY, STYLE, SPEED))
    return p, get_duration(p)


# ---------------------------------------------------------------- subtitles
def _wrap2(words, maxc):
    """Wrap words into <=2 balanced lines. Returns list of lines."""
    full = " ".join(words)
    if len(full) <= maxc or len(words) < 2:
        return [full]
    best, best_cost = None, None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        cost = max(len(l1), len(l2)) + (0 if max(len(l1), len(l2)) <= maxc else 100)
        if len(words[i - 1].strip(",.;:…")) <= 3:
            cost += 6
        if len(words[i:]) == 1 and len(l2) <= 6:
            cost += 8
        if best_cost is None or cost < best_cost:
            best, best_cost = [l1, l2], cost
    return best


def split_subs(text, maxc=32):
    words = text.split()
    nl, cur = 0, 0
    for w in words:
        if cur and cur + 1 + len(w) > maxc:
            nl += 1
            cur = len(w)
        else:
            cur = cur + 1 + len(w) if cur else len(w)
    nl += 1 if cur else 0
    k = max(1, -(-nl // 2))
    n = len(words)
    target = len(text) / k
    INF = 10 ** 9

    def chunk_cost(i, j, last):
        ws = words[i:j]
        ln = len(" ".join(ws))
        lines = _wrap2(ws, maxc)
        if len(lines) > 2 or max(len(x) for x in lines) > maxc + 3:
            return INF
        c = (ln - target) ** 2
        end = ws[-1]
        if not last:
            if end[-1] in ",.:;…":
                c -= 30
            elif len(end) <= 3:
                c += 120
        return c

    dp = [[INF] * (n + 1) for _ in range(k + 1)]
    prv = [[0] * (n + 1) for _ in range(k + 1)]
    dp[0][0] = 0
    for c in range(1, k + 1):
        for j in range(1, n + 1):
            for i in range(c - 1, j):
                if dp[c - 1][i] >= INF:
                    continue
                v = dp[c - 1][i] + chunk_cost(i, j, j == n)
                if v < dp[c][j]:
                    dp[c][j], prv[c][j] = v, i
    if dp[k][n] >= INF:  # fallback: greedy pairs
        lines, cur = [], ""
        for w in words:
            if cur and len(cur) + 1 + len(w) > maxc:
                lines.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}" if cur else w
        lines.append(cur)
        return ["\\N".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    cuts, j = [], n
    for c in range(k, 0, -1):
        cuts.append((prv[c][j], j))
        j = prv[c][j]
    cuts.reverse()
    return ["\\N".join(_wrap2(words[i:j], maxc)) for i, j in cuts]


def fmt_ass(sec):
    h, m, s = int(sec // 3600), int((sec % 3600) // 60), sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Palatino Linotype,54,&H00E0ECF2,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,600,1
Style: Quote,Palatino Linotype,54,&H00A8C8E6,&H000000FF,&H00000000,&H80000000,-1,-1,0,0,100,100,0,0,1,3,1,2,60,60,600,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ---------------------------------------------------------------- render
def render_video(video, prefijo, sin_voz, md_dir, voices):
    num, header, name = video["num"], video["header"], video["name"]
    slug = slugify(name)
    suffix = "_sinvoz" if sin_voz else ""
    wdir = os.path.join(ROOT, "scratch", "codice-video", f"{prefijo}_{num}{suffix}")
    shutil.rmtree(wdir, ignore_errors=True)
    os.makedirs(wdir, exist_ok=True)

    parts = list(video["parts"]) + [{"type": "outro", "phrases": [{"text": OUTRO_TEXT, "voices": None}]}]

    # audio + timing
    t = LEAD_IN
    seg_start = {}
    sub_events = []
    wavs = []
    lead = os.path.join(wdir, "sil_lead.wav")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{LEAD_IN:.3f}",
         lead, "-loglevel", "error"])
    wavs.append(lead)
    k = 0
    phrase_start = {}
    for i, p in enumerate(parts):
        n = len(p["phrases"])
        for j, ph in enumerate(p["phrases"]):
            phrase_start[(i, j)] = 0.0 if (i, j) == (0, 0) else t
            text = ph["text"]
            is_q = bool(ph["voices"])
            src, dur = phrase_audio(ph, sin_voz, wdir, k, voices)
            nxt_q = j + 1 < n and bool(p["phrases"][j + 1]["voices"])
            if is_q:
                pause = 0.8
            elif nxt_q:
                pause = 0.9
            else:
                pause = PAUSE_PART if j == n - 1 else PAUSE_PHRASE
            seg_start.setdefault(i, t)
            chunks = split_subs(text)
            if is_q:
                chunks[0] = "«" + chunks[0]
                chunks[-1] = chunks[-1] + "»"
            total = sum(len(c.replace("\\N", " ")) for c in chunks) or 1
            ct = t
            for ci, c in enumerate(chunks):
                cd = dur * len(c.replace("\\N", " ")) / total
                sub_events.append((ct, ct + cd + (0.15 if ci == len(chunks) - 1 else 0.0), c, "Quote" if is_q else "Sub"))
                ct += cd
            wav = os.path.join(wdir, f"vo_{k:03d}_p.wav")
            run(["ffmpeg", "-y", "-i", src, "-af", f"apad=pad_dur={pause:.3f}",
                 "-ar", "44100", "-ac", "1", wav, "-loglevel", "error"])
            wavs.append(wav)
            t += dur + pause
            k += 1
    total_dur = t
    seg_start[0] = 0.0
    starts = [seg_start[i] for i in range(len(parts))]
    durs = [starts[i + 1] - starts[i] for i in range(len(parts) - 1)] + [total_dur - starts[-1]]

    with open(os.path.join(wdir, "vo_concat.txt"), "w", encoding="utf-8") as f:
        for w in wavs:
            f.write(f"file '{os.path.basename(w)}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "vo_concat.txt", "-c", "copy",
         "vo_full.wav", "-loglevel", "error"], cwd=wdir)

    with open(os.path.join(wdir, "subtitles.ass"), "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        for st, en, txt, sty in sub_events:
            f.write(f"Dialogue: 0,{fmt_ass(st)},{fmt_ass(en)},{sty},,0,0,0,,{txt}\n")

    def textfile(fname, text):
        with open(os.path.join(wdir, fname), "w", encoding="utf-8") as f:
            f.write(text)
        return fname

    hdr_f = textfile("hdr.txt", header)
    name_f = textfile("name.txt", name)
    pro_f = textfile("pro.txt", "PRÓXIMAMENTE")
    dsd_f = textfile("dsd.txt", "en tu Nintendo DS")

    # name font size: shrink long names so they fit in 1000 px
    name_size = 68
    try:
        while name_size > 34 and ImageFont.truetype("C:/Windows/Fonts/palab.ttf", name_size).getlength(name) > 1000:
            name_size -= 2
    except OSError:
        pass

    # segmentos visuales: una parte = un segmento, salvo "cortes" (un segmento por frase)
    segments, cut_state = [], {"last": None, "i": 0}
    for i, p in enumerate(parts):
        if p["type"] == "char" and p.get("dir") == "cortes":
            nph = len(p["phrases"])
            p["_cerca"] = [bool(ph.get("cerca")) for ph in p["phrases"]]
            p["_stage"] = [ph.get("stage") for ph in p["phrases"]]
            dirs_c = pick_cut_dirs(p, nph, cut_state)
            part_end = starts[i + 1] if i + 1 < len(parts) else total_dur
            for j in range(nph):
                st = phrase_start[(i, j)]
                en = phrase_start[(i, j + 1)] if j + 1 < nph else part_end
                fn = f"part{i}_cut{j}.mkv"
                stg = p["_stage"][j]
                staged = bool(stg and stg["staged"])
                if staged:
                    build_staged_shot(p, stg, en - st, os.path.join(wdir, fn))
                else:
                    build_shot(p, dirs_c[j], en - st, p["_cerca"][j], os.path.join(wdir, fn))
                segments.append({"p": p, "fn": fn, "still": False, "d": en - st, "first": j == 0, "cut": True,
                                 "wide": staged or bool(p.get("anim_b")),
                                 "label": dirs_c[j] + (" cerca" if p["_cerca"][j] else "") + (" escenificado" if staged else "")})
            print(f"  parte {i}: cortes " + ", ".join(x["label"] for x in segments if x["p"] is p))
        elif p["type"] == "char":
            fn = f"part{i}.gif"
            build_char_gif(p, os.path.join(wdir, fn))
            segments.append({"p": p, "fn": fn, "still": False, "d": durs[i], "first": True, "cut": False})
        elif p["type"] == "card":
            fn = f"part{i}.png"
            im = Image.open(os.path.join(ROOT, p["png"])).convert("RGB")
            if p["rect"]:
                ImageDraw.Draw(im).rectangle(p["rect"], fill=(0, 0, 0))
            im.save(os.path.join(wdir, fn))
            segments.append({"p": p, "fn": fn, "still": True, "d": durs[i], "first": True, "cut": False})
        else:
            fn = f"part{i}.gif"
            build_mosaic(os.path.join(wdir, fn))
            segments.append({"p": p, "fn": fn, "still": False, "d": durs[i], "first": True, "cut": False})
    first_part = parts[0]

    def hold(p):
        return "tpad=stop_mode=clone:stop_duration=120," if p.get("mods", {}).get("una_vez") else ""

    chains = []
    for i, sg in enumerate(segments):
        p, d = sg["p"], sg["d"]
        # el primer plano entra sin fundido: un primer fotograma negro hace que la gente pase el vídeo;
        # los cortes dentro de una parte son corte seco
        fade = "" if (p is first_part or not sg["first"]) else "fade=t=in:st=0:d=0.35,"
        if p["type"] == "char":
            sc = ("scale=1080:840:flags=neighbor,pad=1080:1920:0:340:black" if sg.get("wide", p.get("anim_b"))
                  else "scale=840:840:flags=neighbor,pad=1080:1920:120:340:black")
            c = (f"[{i}:v]fps=30,{hold(p)}{sc},"
                 f"drawtext=fontfile='{FONT_REG}':textfile='{hdr_f}':fontsize=36:fontcolor=0x9A9184:x=(w-text_w)/2:y=165,"
                 f"drawtext=fontfile='{FONT_BOLD}':textfile='{name_f}':fontsize={name_size}:fontcolor=0xEDE5D5:x=(w-text_w)/2:y=220,"
                 f"{fade}trim=duration={d:.3f},setpts=PTS-STARTPTS[v{i}]")
        elif p["type"] == "card":
            c = (f"[{i}:v]fps=30,scale=768:1152:flags=neighbor,pad=1080:1920:156:250:black,"
                 f"{fade}trim=duration={d:.3f},setpts=PTS-STARTPTS[v{i}]")
        else:
            c = (f"[{i}:v]fps=30,scale=800:800:flags=neighbor,pad=1080:1920:140:190:black,"
                 f"drawtext=fontfile='{FONT_BOLD}':textfile='{pro_f}':fontsize=56:fontcolor=0xEDE5D5:x=(w-text_w)/2:y=1030,"
                 f"drawtext=fontfile='{FONT_ITAL}':textfile='{dsd_f}':fontsize=42:fontcolor=0xB8AFA0:x=(w-text_w)/2:y=1105,"
                 f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.1, d - 1.2):.3f}:d=1.2,"
                 f"trim=duration={d:.3f},setpts=PTS-STARTPTS[v{i}]")
        chains.append(c)
    n = len(segments)
    vlabels = "".join(f"[v{i}]" for i in range(n))
    a_vo, a_bg = n, n + 1
    fc = ";\n".join(chains) + (
        f";\n{vlabels}concat=n={n}:v=1:a=0,ass='subtitles.ass',format=yuv420p[vout];\n"
        f"[{a_vo}:a]volume=1.15[vo];\n"
        f"[{a_bg}:a]volume=0.09,afade=t=in:st=0:d=1.5,afade=t=out:st={max(0.1, total_dur - 2.5):.3f}:d=2.5[bg];\n"
        f"[vo][bg]amix=inputs=2:duration=first:normalize=0,atrim=0:{total_dur:.3f}[aout]")
    with open(os.path.join(wdir, "filter.txt"), "w", encoding="utf-8") as f:
        f.write(fc)

    out_dir = os.path.join(ROOT, "assets", "videos")
    os.makedirs(out_dir, exist_ok=True)
    mp4 = os.path.join(out_dir, f"{prefijo}_{num}_{slug}{suffix}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for sg in segments:
        once = sg["p"].get("mods", {}).get("una_vez", False)
        if sg["cut"]:
            cmd += ["-i", sg["fn"]]
        else:
            cmd += (["-loop", "1"] if sg["still"] else ["-ignore_loop", "1" if once else "0"]) + ["-i", sg["fn"]]
    cmd += ["-i", "vo_full.wav", "-stream_loop", "-1", "-i", BGM,
            "-filter_complex_script", "filter.txt", "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_dur:.3f}", mp4]
    run(cmd, cwd=wdir)

    # preview strip
    strip_dir = os.path.join(md_dir, "assets")
    os.makedirs(strip_dir, exist_ok=True)
    strip = os.path.join(strip_dir, f"{prefijo}_{num}_{slug}{suffix}_tira.png")
    times = [0.5 + (total_dur - 0.5 - 1.6) * i / 5 for i in range(6)]
    tiles = []
    for i, ts in enumerate(times):
        fp = os.path.join(wdir, f"strip_{i}.png")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ts:.3f}", "-i", mp4,
             "-frames:v", "1", "-vf", "scale=270:480", fp])
        tiles.append(Image.open(fp).convert("RGB"))
    sheet = Image.new("RGB", (270 * 6, 480), (0, 0, 0))
    for i, im in enumerate(tiles):
        sheet.paste(im, (270 * i, 0))
    sheet.save(strip)
    print(f"[{num}] {name}: {total_dur:.1f}s")
    print("MP4:", mp4)
    print("TIRA:", strip)


def main():
    ap = argparse.ArgumentParser(description="Render vídeos de lore desde guiones.md")
    ap.add_argument("--guiones", required=True)
    ap.add_argument("--solo", default="", help="números separados por coma, p.ej. 01,03")
    ap.add_argument("--sin-voz", action="store_true", help="audio silencioso, sin gastar ElevenLabs")
    ap.add_argument("--prefijo", default=None)
    ap.add_argument("--paso", choices=["lento", "natural"], default="natural",
                    help="planos con trayecto: lento = dura todo el plano; natural = ritmo 1.0, llega antes")
    args = ap.parse_args()

    global PASO
    PASO = args.paso
    md = os.path.abspath(args.guiones)
    md_dir = os.path.dirname(md)
    prefijo = args.prefijo
    if not prefijo:
        m = re.fullmatch(r"lore-lote-(\w+)", os.path.basename(md_dir))
        prefijo = f"lore{m.group(1)}" if m else "lore"
    videos, voices = parse_guiones(md)
    if args.solo:
        want = {s.strip().zfill(2) for s in args.solo.split(",") if s.strip()}
        videos = [v for v in videos if v["num"] in want]
    if not videos:
        sys.exit("No hay vídeos que renderizar")
    if not args.sin_voz:  # comprobar voces ANTES de gastar creditos
        missing = sorted({n for v in videos for p in v["parts"] for ph in p["phrases"]
                          for n in (ph["voices"] or []) if n.lower() not in voices
                          or voices[n.lower()].upper() in ("TEST", "PENDIENTE")})
        if missing:
            sys.exit("Faltan voice_id en '## Voces' para: " + ", ".join(missing) + ". No se ha llamado a ElevenLabs.")
    for v in videos:
        render_video(v, prefijo, args.sin_voz, md_dir, voices)


if __name__ == "__main__":
    main()
