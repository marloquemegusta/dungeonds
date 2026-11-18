"""Compara las ejecuciones (remates) de la ronda 2: por enemigo, una fila por modelo (Sonnet, DeepSeek) y columnas A | B | C.

  python tools/characters/remate_ronda2_compare.py

Lee los fotogramas 1x RGBA de walkthroughs/remate-exvoto/assets/ronda2/<prefijo><enemigo>_<X>/f*.png, los centra en una celda
común por enemigo sobre #3d3b38, amplía 4x NEAREST, compone una GIF por enemigo con UNA paleta global (120 ms por fotograma (a petición del usuario), el
último se sostiene) y escribe walkthroughs/remate-exvoto/remate_ronda2.html con todo dentro (para el móvil).
"""
import base64
import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "walkthroughs" / "remate-exvoto" / "assets" / "ronda2"
OUT_HTML = ROOT / "walkthroughs" / "remate-exvoto" / "remate_ronda2.html"
BG = (0x3D, 0x3B, 0x38)
SCALE = 4
FRAME_MS = 120
HOLD_MS = 1000
LABEL_H = 18
ROWS = [("Sonnet", ""), ("DeepSeek", "ds_")]
OPTS = "ABC"


def load(folder):
    fs = sorted(folder.glob("f*.png")) if folder.is_dir() else []
    return [Image.open(f).convert("RGBA") for f in fs]


def font():
    for p in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, 14)
    return ImageFont.load_default()


def compose(enemy):
    seqs = {(m, o): load(R2 / ("%s%s_%s" % (pre, enemy, o))) for m, pre in ROWS for o in OPTS}
    present = [m for m, _ in ROWS if any(seqs[(m, o)] for o in OPTS)]
    cell = max([im.size[0] for s in seqs.values() for im in s] + [im.size[1] for s in seqs.values() for im in s] + [64])
    n = max([len(s) for s in seqs.values()] + [1])
    cw, ch = cell * SCALE, cell * SCALE
    W, H = cw * 3, (ch + LABEL_H) * len(present)
    f = font()
    frames = []
    for i in range(n):
        canvas = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(canvas)
        for r, m in enumerate(present):
            y0 = r * (ch + LABEL_H)
            for c, o in enumerate(OPTS):
                x0 = c * cw
                d.text((x0 + 6, y0 + 1), "%s %s" % (o, m), fill=(220, 214, 200), font=f)
                s = seqs[(m, o)]
                if not s:
                    d.text((x0 + 6, y0 + LABEL_H + ch // 2), "sin entrega", fill=(150, 140, 130), font=f)
                    continue
                im = s[min(i, len(s) - 1)]
                cellim = Image.new("RGBA", (cell, cell), BG + (255,))
                cellim.alpha_composite(im, ((cell - im.size[0]) // 2, cell - im.size[1]))
                canvas.paste(cellim.convert("RGB").resize((cw, ch), Image.NEAREST), (x0, y0 + LABEL_H))
            d.line([(0, y0), (W, y0)], fill=(90, 86, 80))
        frames.append(canvas)
    # Una sola paleta para toda la animación: se cuantiza un mosaico con todos los fotogramas y se aplica a cada uno.
    mosaic = Image.new("RGB", (W, H * len(frames)))
    for i, fr in enumerate(frames):
        mosaic.paste(fr, (0, i * H))
    pal = mosaic.quantize(colors=255, method=Image.MEDIANCUT)
    q = [fr.quantize(palette=pal, dither=Image.NONE) for fr in frames]
    durs = [FRAME_MS] * (len(q) - 1) + [HOLD_MS]
    out = R2 / ("comparativa_%s.gif" % enemy)
    q[0].save(out, save_all=True, append_images=q[1:], duration=durs, loop=0, disposal=1)
    return out, present, cell, n


def b64(p, mime):
    return "data:%s;base64,%s" % (mime, base64.b64encode(Path(p).read_bytes()).decode())


TEXT = {
    "exvoto": {
        "A": "Lo agarra de cada brazo, tira hacia los lados y lo parte en vertical; las mitades caen a cada lado.",
        "B": "Lo abraza contra el pecho y el fuego del Corazón lo derrite hasta un charco con el velo encima.",
        "C": "Tercera opción de cada agente (cada modelo propuso la suya; ver notas).",
    },
    "cireneo": {
        "A": "Le arranca la cruz de la espalda y lo atraviesa con ella contra el suelo.",
        "B": "Lo tumba boca abajo y le deja caer encima su propia cruz.",
        "C": "Tercera opción de cada agente (cada modelo propuso la suya; ver notas).",
    },
}


def main(notes=None):
    notes = notes or {}
    css = """:root{--bg:#f6f3ee;--fg:#222;--mut:#6a6358;--line:#b9a98f}
@media(prefers-color-scheme:dark){:root{--bg:#1b1a18;--fg:#ddd;--mut:#a39b8e;--line:#5a5246}}
body{font-family:system-ui,sans-serif;max-width:980px;margin:auto;padding:16px;background:var(--bg);color:var(--fg);line-height:1.45}
h2{margin-top:1.8em;border-top:2px solid var(--line);padding-top:.6em}
img.g{width:100%;image-rendering:pixelated;border-radius:6px;display:block}
.mut{color:var(--mut);font-size:.92em}li{margin:.25em 0}"""
    h = ['<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Remates, ronda 2</title><style>', css, '</style>',
         '<h1>Remates, ronda 2</h1>',
         '<p>Por enemigo, una fila por modelo (arriba Sonnet, abajo DeepSeek) y tres opciones A | B | C. Vista diagonal del juego, ampliada 4× sin suavizar. '
         'Renders de prueba, no capturas de la ROM.</p>']
    for enemy, title in (("exvoto", "Exvoto"), ("cireneo", "Cireneo")):
        out, present, cell, n = compose(enemy)
        h += ['<h2>%s</h2>' % title, '<ul>'] + ['<li><b>%s.</b> %s</li>' % (o, TEXT[enemy][o]) for o in OPTS] + ['</ul>',
              '<img class=g src="%s" alt="Comparativa %s">' % (b64(out, "image/gif"), title),
              '<p class=mut>Celda %d×%d, %d fotogramas (~%.1f s).</p>' % (cell, cell, n, n * FRAME_MS / 1000)]
        if enemy in notes:
            h.append(notes[enemy])
    OUT_HTML.write_text("".join(h), encoding="utf-8", newline="\n")
    print(OUT_HTML)


if __name__ == "__main__":
    main()
