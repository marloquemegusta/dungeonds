"""Tema visual de los vídeos: cajas de piedra roja + marco dorado de la ROM y Palatino a 1 bit.

Fuente de verdad en Python. Lee kit/theme.json (generado por build_kit.py), que también consume
devlog/src/theme (Remotion). Todo se compone a resolución nativa de la DS y se amplía NEAREST.

    from theme import render_box
    img = render_box(["Simón Requena tocaba", "la campana de Valdenoche"], highlight={"Valdenoche"})
"""
import json
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
_T = None


def load_theme():
    global _T
    if _T is None:
        with open(os.path.join(HERE, "kit", "theme.json"), encoding="utf-8") as f:
            _T = json.load(f)
        _T["_stone"] = _hex_rgba(_T["stone"], 64, 64, 6)
        _T["_bar"] = _hex_rgba(_T["bar_px"], 16, 5, 8)
        _T["_corner"] = _hex_rgba(_T["corner"], 14, 14, 8)
    return _T


def _hex_rgba(s, w, h, n):
    out = []
    for i in range(w * h):
        c = s[i * n:(i + 1) * n]
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        a = int(c[6:8], 16) if n == 8 else 255
        out.append((r, g, b, a))
    return out


def color(name):
    t = load_theme()
    c = t["colors"][name]
    return (c[0], c[1], c[2], 255)


def _glyph(t, ch, style):
    g = t["font"][style]
    return g.get(ch) or g.get("?")


def text_width(t, text, style="regular"):
    return sum(_glyph(t, c, style)["a"] for c in text)


def _words(lines):
    """lines: list[str | list[(texto, color)]] -> lista de líneas de palabras [(palabra, color|None)]."""
    out = []
    for ln in lines:
        if isinstance(ln, str):
            out.append([(w, None) for w in ln.split(" ") if w])
        else:
            ws = []
            for txt, col in ln:
                ws.extend((w, col) for w in txt.split(" ") if w)
            out.append(ws)
    return out


def wrap(text, max_w, style="regular"):
    """Reparto equilibrado de un texto en líneas que caben en max_w px nativos."""
    t = load_theme()
    words = text.split(" ")
    sp = text_width(t, " ", style)

    def build(mw):
        lines, cur, cw = [], [], 0
        for w in words:
            ww = text_width(t, w, style)
            if cur and cw + sp + ww > mw:
                lines.append(" ".join(cur))
                cur, cw = [], 0
            cw = ww if not cur else cw + sp + ww
            cur.append(w)
        lines.append(" ".join(cur))
        return lines
    n = len(build(max_w))
    lo, hi = 40, max_w
    while hi - lo > 2:
        mid = (lo + hi) // 2
        if len(build(mid)) == n:
            hi = mid
        else:
            lo = mid
    return build(hi)


def render_box_native(lines, highlight=None, style="regular", base_color="ivory", fixed_w=0, min_h=None, box=True):
    """Caja (o texto suelto con box=False) a resolución nativa. Devuelve Image RGBA.

    lines: list[str | list[(texto, nombre_color)]]
    highlight: palabra(s) en oro: str, set/list de str o de índices globales de palabra.
    """
    t = load_theme()
    pad, line_h, bar = t["pad"], t["line"], t["bar"]
    wl = _words(lines)
    hl = highlight if isinstance(highlight, (set, list, tuple)) else ({highlight} if highlight is not None else set())
    sp = text_width(t, " ", style)
    widths = [sum(text_width(t, w, style) for w, _ in ln) + sp * (len(ln) - 1) for ln in wl]
    wmax = max(widths) if widths else 0
    pw = fixed_w or (wmax + 2 * pad + 2)
    pw += pw % 2
    ph = len(wl) * line_h + 2 * pad - 2
    if min_h is None:
        min_h = t["min_box_h"] // t["scale"]
    ph = max(ph, min_h)
    if not box:
        pw, ph = wmax + 2, len(wl) * line_h
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    px = im.load()
    if box:
        _panel(t, px, pw, ph)
    dark = color("dark")
    y0 = (ph - len(wl) * line_h) // 2 if box else 0
    gi = 0
    for li, ln in enumerate(wl):
        x = (pw - widths[li]) // 2
        base = y0 + li * line_h + t["ascent"]
        for w, col in ln:
            c = color(col) if col else color("gold" if (gi in hl or w.strip("«»¿?¡!.,;:”“\"'") in hl or w in hl) else base_color)
            gi += 1
            for ch in w:
                g = _glyph(t, ch, style)
                for dx, dy, cc in ((1, 1, dark), (0, 0, c)):
                    for ry, row in enumerate(g["d"]):
                        for rx, v in enumerate(row):
                            if v == "1":
                                xx, yy = x + g["x"] + rx + dx, base + g["y"] + ry + dy
                                if 0 <= xx < pw and 0 <= yy < ph:
                                    px[xx, yy] = cc
                x += g["a"]
            x += sp
    return im


def _panel(t, px, w, h):
    stone, bar, corner = t["_stone"], t["_bar"], t["_corner"]
    B = t["bar"]
    for y in range(h):
        for x in range(w):
            px[x, y] = stone[(y & 63) * 64 + (x & 63)]
    for d in range(B):
        for x in range(w):
            px[x, d] = bar[d * 16 + (x & 15)]
            px[x, h - 1 - d] = bar[d * 16 + (x & 15)]
        for y in range(h):
            px[d, y] = bar[d * 16 + (y & 15)]
            px[w - 1 - d, y] = bar[d * 16 + (y & 15)]
    inner = tuple(t["inner_line"]) + (255,)
    for x in range(B, w - B):
        px[x, B] = inner
    for y in range(B, h - B):
        px[B, y] = inner
    for cy in range(14):
        for cx in range(14):
            c = corner[cy * 14 + cx]
            if c[3]:
                px[cx, cy] = c
                px[w - 1 - cx, cy] = c
                px[cx, h - 1 - cy] = c
                px[w - 1 - cx, h - 1 - cy] = c


def render_box(text_lines, highlight=None, style="regular", **kw):
    """Igual que render_box_native pero ampliada x escala (NEAREST): lista para componer en 1080x1920."""
    t = load_theme()
    im = render_box_native(text_lines, highlight, style, **kw)
    s = t["scale"]
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def progress_bar(fraction, native_w):
    """Barra de progreso del devlog: marco oscuro con relleno de barra dorada (nativo)."""
    t = load_theme()
    h = 8
    im = Image.new("RGBA", (native_w, h), (0, 0, 0, 0))
    px = im.load()
    gold = color("gold")
    bar = t["_bar"]
    for y in range(h):
        for x in range(native_w):
            edge = y in (0, h - 1) or x in (0, native_w - 1)
            px[x, y] = gold if edge else tuple(t["inner_line"]) + (255,)
    for x in range(1, 1 + int((native_w - 2) * fraction)):
        for y in range(1, h - 1):
            px[x, y] = bar[min(y - 1, 4) * 16 + (x & 15)]
    return im
