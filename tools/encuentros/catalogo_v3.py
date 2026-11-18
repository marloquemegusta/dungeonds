"""Catálogo de salas v3 del acto I (DESIGN.md 6.13.8, encuentros tácticos, 2026-11-17).

Rehace el catálogo v2 con los papeles nuevos: el Ojo clava desde su puesto en la mitad de arriba con más alcance que el
rayo base, los Exvotos bajan a flanquear y son el recurso del remate, el Cireneo guarda al Ojo y la entrada queda despejada.

Genera tools/encuentros/acto1_v3.json (propuesta; la ROM sigue leyendo acto1_v2.json hasta implementar la IA nueva) y
walkthroughs/encuentros-tacticos/catalogo-salas-v3.html (esquemas para revisar en el móvil; no son capturas de la ROM).
Coordenadas locales: lx 0..208 (suelo), ly 0..384 (0 = barrera de arriba, 384 = entrada).
Estados nuevos de los enemigos: post (Ojo quieto en su puesto), guard (Cireneo que guarda al Ojo más cercano),
flank (Exvoto que se agrupa fuera del alcance del héroe y entra por los lados).
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogo_v2 as v2  # noqa: E402  (reutiliza el ajuste de piezas a fases legales y pares simétricos)

PIECE = {"banco_grupo4": (72, 84), "columna_entera": (24, 24), "santo": (28, 28)}
OJO_RANGE = 320       # [TUNABLE-PLACEHOLDER] alcance del Ojo (antes ~140; rayo base del héroe 160, máximo 416). 320 cubre todo el suelo desde un puesto central: con 256 quedan bolsas seguras de 60x60 a 90x90 px en las esquinas de abajo (tools/encuentros/audit_ojo_v3.py)
HERO_RANGE = 160      # rayo base del héroe (DESIGN.md 6.12.10)
ENTRY = (104, 348)    # el héroe al cerrarse la barrera de atrás (36 px dentro de la sala)
STATE = {"exvoto": "flank", "ojo": "post", "cireneo": "guard"}


def ex(*pts):
    return [["exvoto", x, y] for x, y in pts]


ROOMS = [
    {
        "id": "atrio", "name": "El atrio", "nuevo": True, "fija": True,
        "pregunta": "¿Te acercas a rematar?",
        "idea": "Primer encuentro del acto, siempre el mismo. Solo Exvotos y espacio abierto: el primer disparo los deja "
                "tambaleándose y brillando, y con L te lanzas a rematarlos. Es la lección del remate.",
        "resolver": "Un disparo, acercarse, L. Descubrir que el remate te hace invulnerable y te deja el rayo cargado.",
        "antes": "Sala nueva. Es la única sin Ojo: enseña el remate antes de meter presión.",
        "pieces": [("santo", 8, 96), ("santo", 172, 96)],
        "obstacles": [],
        "tiers": {"unica": ex((40, 60), (104, 40), (168, 60), (70, 140), (138, 140))},
        "escala": {"unica": "5 Exvotos. Una sola población: siempre es el primer encuentro."},
    },
    {
        "id": "procesion", "name": "La procesión",
        "pregunta": "¿Cruzas el pasillo que vigila el Ojo?",
        "idea": "Los bancos suben a media sala y son cobertura baja: agachado tras ellos el Ojo no te da. El pasillo central es "
                "la línea del Ojo, y en media y dura también la carga del Cireneo. Parte de los Exvotos baja por arriba y otros "
                "empiezan a los lados de la entrada, así que no hay una sola fila que barrer.",
        "resolver": "Avanzar agachado tras un bloque de bancos, rematar a los que te rodean y cruzar el pasillo cuando el Ojo no te tiene fijado.",
        "antes": "Los Exvotos bajaban en fila por el pasillo hacia el rayo: era la sala perfecta para quedarse en la entrada. Los bancos de abajo daban cobertura junto a la entrada.",
        "pieces": [("banco_grupo4", 0, 130), ("banco_grupo4", 136, 130), ("columna_entera", 36, 24), ("columna_entera", 148, 24)],
        "obstacles": [],
        "tiers": {
            "ligera": [["ojo", 104, 100]] + ex((24, 40), (60, 60), (148, 60), (184, 40), (20, 250), (188, 250)),
            "media": [["ojo", 104, 100], ["cireneo", 104, 124]] + ex((24, 40), (60, 60), (148, 60), (184, 40), (20, 240), (188, 240), (36, 280), (172, 280)),
            "dura": [["ojo", 40, 104], ["ojo", 168, 104], ["cireneo", 104, 120]]
                    + ex((24, 30), (60, 50), (104, 40), (148, 50), (184, 30), (20, 236), (188, 236), (36, 276), (172, 276), (104, 70)),
        },
        "escala": {"ligera": "1 Ojo al final del pasillo y 6 Exvotos (2 ya a los lados de la entrada).",
                   "media": "El Ojo con un Cireneo delante que te carga por el pasillo, y 8 Exvotos.",
                   "dura": "2 Ojos, uno sobre cada bloque de bancos (ya no hay un lado seguro), el Cireneo y 10 Exvotos."},
    },
    {
        "id": "trinchera", "name": "La trinchera", "nuevo": True,
        "pregunta": "¿Avanzas de saco en saco?",
        "idea": "Tres tramos de sacos que salen de las paredes a distintas alturas, alternando lado: son escalones de cobertura baja "
                "hasta el Ojo. El centro queda abierto, sin embudo. Agachado tras un saco el Ojo no te da, pero los Exvotos vienen "
                "a rodearlo para sacarte.",
        "resolver": "Saltar de un saco al siguiente cuando el Ojo suelta la mirada, y rematar al Exvoto que rodea tu saco para salir con el rayo cargado.",
        "antes": "Sustituye a «el embudo»: su único paso ponía a los Exvotos en fila hacia ti y lo mejor era esperar debajo del paso.",
        "pieces": [],
        "obstacles": [{"kind": "sacos", "x": 0, "y": 230, "w": 64, "h": 24},
                      {"kind": "sacos", "x": 144, "y": 170, "w": 64, "h": 24},
                      {"kind": "sacos", "x": 0, "y": 112, "w": 64, "h": 24}],
        "tiers": {
            "ligera": [["ojo", 150, 100]] + ex((30, 40), (80, 30), (130, 30), (180, 50), (60, 80), (180, 120)),
            "media": [["ojo", 56, 100], ["ojo", 150, 100], ["cireneo", 104, 130]] + ex((30, 40), (80, 30), (130, 30), (180, 50), (100, 70), (180, 140), (24, 200), (190, 240)),
            "dura": [["ojo", 56, 100], ["ojo", 150, 100], ["cireneo", 60, 140], ["cireneo", 150, 136]]
                    + ex((30, 40), (70, 30), (104, 50), (140, 30), (180, 50), (100, 80), (180, 140), (24, 200), (190, 240), (104, 160)),
        },
        "escala": {"ligera": "1 Ojo arriba a la derecha y 6 Exvotos.",
                   "media": "2 Ojos (un saco ya no cubre de los dos), un Cireneo guardándolos y 8 Exvotos.",
                   "dura": "2 Ojos, 2 Cireneos (uno por Ojo) y 10 Exvotos."},
    },
    {
        "id": "balcon", "name": "El balcón",
        "pregunta": "¿Subes al balcón bajo dos miradas?",
        "idea": "Los Ojos están en el balcón de arriba, entre las estatuas. Las columnas bajan a media sala y son tu cobertura para "
                "subir (paran todos los disparos). Una de las dos es la rota. Los Exvotos bajan por los lados de las columnas a sacarte.",
        "resolver": "Llegar a una columna, aguantar la mirada detrás, rematar a los que vienen y subir al balcón. El Cireneo que embiste contra la columna se queda aturdido: remátalo.",
        "antes": "Las estatuas estaban junto a la entrada: te quedabas detrás de una sin subir nunca. Ahora la cobertura está a medio camino.",
        "pieces": [("columna_entera", 36, 150), ("columna_entera", 148, 260), ("santo", 8, 40), ("santo", 172, 40)],
        "obstacles": [],
        "tiers": {
            "ligera": [["ojo", 104, 96]] + ex((30, 90), (178, 90), (60, 40), (148, 40), (20, 150), (188, 150)),
            "media": [["ojo", 60, 100], ["ojo", 148, 100]] + ex((30, 90), (178, 90), (104, 40), (104, 130), (20, 150), (188, 150), (104, 70)),
            "dura": [["ojo", 60, 100], ["ojo", 148, 100], ["cireneo", 104, 128]]
                    + ex((30, 90), (178, 90), (80, 40), (128, 40), (20, 150), (188, 150), (104, 70), (20, 220), (188, 220)),
        },
        "escala": {"ligera": "1 Ojo en el centro del balcón y 6 Exvotos.",
                   "media": "2 Ojos cruzando las miradas (una columna ya no cubre de los dos) y 7 Exvotos.",
                   "dura": "2 Ojos, un Cireneo entre ellos que te persigue de columna en columna y 9 Exvotos."},
    },
    {
        "id": "pinza", "name": "La pinza",
        "pregunta": "¿Sales del centro antes de que se cierre?",
        "idea": "Entras por el centro y hay Exvotos a los dos lados de la entrada. El centro es la línea del Ojo, que espera arriba. "
                "Las estatuas de los lados te cubren del Ojo, pero hay que abrirse paso hasta ellas.",
        "resolver": "Romper un lado (los remates te hacen invulnerable dentro del grupo), ponerse tras la estatua de ese lado y desde ahí ir a por el Ojo.",
        "antes": "Ya obligaba a moverse, pero el Ojo solo salía en dura: en ligera y media bastaba con retroceder hasta la barrera y matar a los dos grupos según llegaban.",
        "pieces": [("santo", 8, 150), ("santo", 172, 150), ("banco_grupo4", 0, 10), ("banco_grupo4", 136, 10)],
        "obstacles": [],
        "tiers": {
            "ligera": [["ojo", 104, 100]] + ex((20, 240), (44, 270), (20, 300), (188, 240), (164, 270), (188, 300)),
            "media": [["ojo", 104, 100], ["cireneo", 104, 124]] + ex((20, 230), (44, 260), (20, 290), (40, 320), (188, 230), (164, 260), (188, 290), (168, 320)),
            "dura": [["ojo", 60, 100], ["ojo", 148, 100], ["cireneo", 104, 124]]
                    + ex((20, 220), (44, 250), (20, 280), (44, 310), (24, 336), (188, 220), (164, 250), (188, 280), (164, 310), (184, 336)),
        },
        "escala": {"ligera": "3 y 3 Exvotos y 1 Ojo que vigila el centro.",
                   "media": "4 y 4, y un Cireneo que baja por el centro mientras rompes un lado.",
                   "dura": "5 y 5, el Cireneo y 2 Ojos: ninguna estatua cubre de los dos."},
    },
    {
        "id": "claro", "name": "El claro",
        "pregunta": "¿Encadenas remates para no parar nunca?",
        "idea": "Sin cobertura: solo dos estatuas en las esquinas de arriba. Muchos Exvotos y un Ojo. Aquí tu cobertura es el "
                "remate: mientras rematas eres invulnerable y sales con el rayo cargado para el siguiente.",
        "resolver": "Disparar, rematar, disparar cargado, rematar: no quedarse quieto ni un segundo bajo la mirada del Ojo.",
        "antes": "Era solo la multitud en abierto: retroceder y disparar a lo que llegaba. Ahora el Ojo te castiga si te paras y los remates son la forma de aguantar.",
        "pieces": [("santo", 8, 20), ("santo", 172, 20)],
        "obstacles": [],
        "tiers": {
            "ligera": [["ojo", 104, 96]] + ex((40, 60), (80, 40), (128, 40), (168, 60), (30, 140), (178, 140), (70, 180), (138, 180)),
            "media": [["ojo", 104, 96]] + ex((30, 50), (70, 40), (110, 30), (150, 40), (190, 50), (30, 140), (178, 140), (70, 180), (138, 180), (20, 230), (188, 230)),
            "dura": [["ojo", 60, 100], ["ojo", 148, 100], ["cireneo", 104, 40]]
                    + ex((30, 50), (70, 40), (110, 30), (150, 40), (190, 50), (30, 140), (178, 140), (70, 180), (138, 180), (104, 160), (20, 230), (188, 230)),
        },
        "escala": {"ligera": "1 Ojo y 8 Exvotos.",
                   "media": "1 Ojo y 11 Exvotos (2 ya a los lados de la entrada).",
                   "dura": "2 Ojos, un Cireneo y 12 Exvotos."},
    },
    {
        "id": "alambrada", "name": "La alambrada",
        "pregunta": "¿Peleas dentro del zigzag?",
        "idea": "Dos tramos de alambre de espino con los huecos alternados hacen un zigzag. El alambre para los cuerpos y deja "
                "pasar los disparos: el Ojo, desde arriba, te dispara a través de él. Los Exvotos vienen por el zigzag y por los dos "
                "huecos a la vez.",
        "resolver": "Disparar a través del alambre a los que rodean y avanzar por los huecos. El Cireneo que embiste por un tramo recto acaba en el alambre, aturdido: remátalo.",
        "antes": "En ligera no había Ojo y el zigzag llevaba a los Exvotos hasta ti de uno en uno. Ahora el Ojo está en todas y los Exvotos empiezan a los dos lados.",
        "pieces": [("columna_entera", 150, 40)],
        "obstacles": [{"kind": "alambre", "x": 0, "y": 150, "w": 128, "h": 12}, {"kind": "alambre", "x": 80, "y": 240, "w": 128, "h": 12}],
        "tiers": {
            "ligera": [["ojo", 60, 100]] + ex((30, 50), (110, 40), (180, 70), (150, 190), (40, 200), (180, 200)),
            "media": [["ojo", 60, 100], ["cireneo", 150, 196]] + ex((30, 50), (110, 40), (180, 70), (100, 120), (40, 200), (60, 196), (180, 120)),
            "dura": [["ojo", 60, 100], ["ojo", 150, 100], ["cireneo", 150, 196]]
                    + ex((30, 50), (80, 40), (130, 40), (180, 70), (100, 120), (40, 200), (60, 196), (180, 120), (30, 290)),
        },
        "escala": {"ligera": "1 Ojo tras el alambre y 6 Exvotos.",
                   "media": "El Ojo, un Cireneo dentro del zigzag y 7 Exvotos.",
                   "dura": "2 Ojos, el Cireneo y 9 Exvotos (uno ya por debajo del alambre)."},
    },
]

for _r in ROOMS:
    _r["pieces"] = v2.snap_room(_r["id"], _r["pieces"])

COL = {"exvoto": "#d8c8a2", "cireneo": "#a0503c", "ojo": "#6f5a8c"}


def ojo_ok(enemies):
    """Regla 1: algún Ojo alcanza al héroe en cuanto se cierra la barrera de atrás."""
    ojos = [(x, y) for k, x, y in enemies if k == "ojo"]
    if not ojos:
        return None
    return min(math.hypot(x - ENTRY[0], y - ENTRY[1]) for x, y in ojos) <= OJO_RANGE


def svg(room, enemies):
    W, H = 208 + 24, 384
    o = ['<svg viewBox="-12 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (W, H),
         '<defs><clipPath id="c"><rect x="0" y="0" width="208" height="384"/></clipPath></defs>',
         '<rect x="-12" y="0" width="%d" height="%d" fill="#4a4741"/>' % (W, H),
         '<rect x="0" y="0" width="208" height="384" fill="#6b675f"/>',
         '<rect x="0" y="0" width="208" height="5" fill="#2b2926"/>',
         '<line x1="0" y1="%d" x2="208" y2="%d" stroke="#2b2926" stroke-width="3" stroke-dasharray="6 4"/>' % (ENTRY[1] + 12, ENTRY[1] + 12),
         '<line x1="0" y1="192" x2="208" y2="192" stroke="#8d897f" stroke-width="1" stroke-dasharray="2 4"/>']
    o.append('<g clip-path="url(#c)">')
    for kind, x, y in enemies:
        if kind == "ojo":
            o.append('<circle cx="%d" cy="%d" r="%d" fill="#6f5a8c" fill-opacity=".10" stroke="#8f78b0" stroke-opacity=".6" stroke-dasharray="5 4"/>' % (x, y, OJO_RANGE))
    o.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="#7fb0d4" stroke-opacity=".8" stroke-width="1.5" stroke-dasharray="3 3"/>' % (ENTRY[0], ENTRY[1], HERO_RANGE))
    o.append('</g>')
    for kind, x, y in room["pieces"]:
        w, h = PIECE[kind]
        if kind == "banco_grupo4":
            for i in range(4):
                o.append('<rect x="%d" y="%d" width="%d" height="12" fill="#7a5a3a" stroke="#4e3826"/>' % (x + 4, y + i * 21, w - 8))
        elif kind == "columna_entera":
            o.append('<circle cx="%d" cy="%d" r="12" fill="#bdb6a6" stroke="#857e70" stroke-width="2"/>' % (x + 12, y + 12))
        elif kind == "santo":
            o.append('<rect x="%d" y="%d" width="28" height="28" fill="#a9a395" stroke="#7d776a" stroke-width="2"/>'
                     '<circle cx="%d" cy="%d" r="6" fill="#d0cabb"/>' % (x, y, x + 14, y + 12))
    for ob in room["obstacles"]:
        if ob["kind"] == "sacos":
            o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="4" fill="#8a6f4a" stroke="#5c4930" stroke-width="2"/>' % (ob["x"], ob["y"], ob["w"], ob["h"]))
        else:
            y = ob["y"] + ob["h"] // 2
            o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2c2a27" stroke-width="5"/>'
                     '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#9a948a" stroke-width="2" stroke-dasharray="4 3"/>' % (ob["x"], y, ob["x"] + ob["w"], y, ob["x"], y, ob["x"] + ob["w"], y))
    for kind, x, y in enemies:
        c = COL[kind]
        if kind == "exvoto":
            o.append('<circle cx="%d" cy="%d" r="6" fill="%s" stroke="#3a3328" stroke-width="1.5"/>' % (x, y, c))
        elif kind == "cireneo":
            o.append('<polygon points="%d,%d %d,%d %d,%d" fill="%s" stroke="#2a1a14" stroke-width="1.5"/>' % (x, y - 10, x - 9, y + 7, x + 9, y + 7, c))
        else:
            o.append('<ellipse cx="%d" cy="%d" rx="10" ry="6" fill="#e2dccd" stroke="%s" stroke-width="3"/><circle cx="%d" cy="%d" r="3" fill="%s"/>' % (x, y, c, x, y, c))
    o.append('<circle cx="%d" cy="%d" r="6" fill="#4f7894" stroke="#203342" stroke-width="2"/>' % ENTRY)
    o.append('</svg>')
    return "".join(o)


def count(enemies):
    n = {}
    for e in enemies:
        n[e[0]] = n.get(e[0], 0) + 1
    names = {"exvoto": ("Exvoto", "Exvotos"), "cireneo": ("Cireneo", "Cireneos"), "ojo": ("Ojo", "Ojos")}
    order = ["ojo", "cireneo", "exvoto"]
    return " · ".join("%d %s" % (n[k], names[k][n[k] != 1]) for k in order if k in n)


def main():
    data = json.load(open(os.path.join(ROOT, "tools/encuentros/acto1_v2.json"), encoding="utf-8"))
    data["_doc"] = ("Acto I v3 (DESIGN.md 6.13.8, 2026-11-17), PROPUESTA: la ROM sigue leyendo acto1_v2.json hasta implementar la IA "
                    "nueva. Coordenadas como en v2. Estados: post (Ojo en su puesto), guard (Cireneo que guarda al Ojo mas cercano), "
                    "flank (Exvoto que flanquea). 'fija' = encuentro fijo (el atrio abre el acto). Generado por catalogo_v3.py.")
    data["ojo_range"] = OJO_RANGE
    plantas = {}
    for r in ROOMS:
        p = {"pieces": [{"piece": k, "x": x, "y": y} for k, x, y in r["pieces"]], "obstacles": r["obstacles"]}
        if r.get("fija"):
            p["fija"] = True
        for t, en in r["tiers"].items():
            p[t] = {"enemies": [[k, x, y, STATE[k]] for k, x, y in en]}
        plantas[r["id"]] = p
    data["plantas"] = plantas
    with open(os.path.join(ROOT, "tools/encuentros/acto1_v3.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    css = """:root{--bg:#f6f3ee;--fg:#222;--mut:#6a6358;--line:#b9a98f;--card:#fff;--ok:#3f6b4a;--bad:#8a3a30}
@media(prefers-color-scheme:dark){:root{--bg:#1b1a18;--fg:#ddd;--mut:#a39b8e;--line:#5a5246;--card:#26241f;--ok:#8fbf98;--bad:#d9867a}}
body{font-family:system-ui,sans-serif;max-width:860px;margin:auto;padding:16px;background:var(--bg);color:var(--fg);line-height:1.45}
h1{font-size:1.5em}h2{margin-top:2em;border-top:2px solid var(--line);padding-top:.6em}.q{font-size:1.1em;font-style:italic}
.tag{font-size:.7em;font-weight:600;padding:2px 6px;border-radius:4px;background:var(--line);color:var(--bg);vertical-align:middle;margin-left:6px}
.antes{color:var(--mut);font-size:.95em;border-left:3px solid var(--line);padding-left:10px}
.tiers{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.tiers.one{grid-template-columns:minmax(0,1fr) 2fr}
.tiers svg{width:100%;height:auto;display:block;border-radius:4px}
.t{font-size:13px}.t b{display:block}.ok{color:var(--ok)}.bad{color:var(--bad)}
.ley{font-size:14px}.ley span{display:inline-block;margin-right:12px}
.box{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 14px}
@media(max-width:520px){.tiers{grid-template-columns:repeat(3,1fr);gap:4px}.t{font-size:11.5px}}"""
    h = ['<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Salas del acto I</title><style>', css, '</style>',
         '<h1>Salas del acto I, v3 (propuesta)</h1>',
         '<p>Esquemas para decidir, no capturas de la ROM. Cada sala hace <b>una pregunta</b>; sus tres poblaciones (ligera en los encuentros 1-4, media en el 5-8, dura en el 9-12) son la misma pregunta cada vez más dura.</p>',
         '<div class="box"><b>Reglas nuevas</b> (DESIGN 6.13.8)<ol>',
         '<li><b>Desde que puedes dar a un Exvoto, un Ojo puede darte a ti.</b> Su alcance pasa de ~140 a %d px (tu rayo inicial llega a %d).</li>' % (OJO_RANGE, HERO_RANGE),
         '<li><b>Los Ojos se quedan en su puesto, en la mitad de arriba.</b> La cobertura buena está en medio y arriba; la entrada queda despejada.</li>',
         '<li><b>Exvotos que bajan a flanquear</b> (se reúnen fuera de tu alcance y entran juntos, por los lados) y <b>un Cireneo guardando a los Ojos</b>.</li>',
         '<li><b>Sin embudos</b> que pongan a la horda en fila delante del rayo.</li></ol>',
         '<p><b>Decidido (18-nov):</b> el Ojo está ya desde las ligeras (antes entraba en la segunda mitad del acto), porque es lo que te obliga a subir. La excepción es <b>el atrio</b>, el primer encuentro del acto, que enseña el remate sin presión.</p></div>',
         '<p class="ley"><b>Leyenda:</b> <span>● Exvoto</span><span style="color:#a0503c">▲ Cireneo</span><span style="color:#8f78b0">◉ Ojo y su alcance (círculo morado)</span>'
         '<span style="color:#7fb0d4">● tú al entrar y tu alcance inicial (círculo azul)</span><span>línea negra arriba = rastrillo</span><span>discontinua abajo = barrera de atrás</span>'
         '<span>punteada = corte entre las dos pantallas (aprox.)</span><span>pardo = sacos (cobertura baja)</span><span>alambre = discontinua gris</span><span>círculo gris = columna</span><span>cuadrado gris = estatua</span><span>listones = bancos (cobertura baja)</span></p>']
    for r in ROOMS:
        tag = ' <span class="tag">nueva</span>' if r.get("nuevo") else ' <span class="tag">rehecha</span>'
        h += ['<h2>%s%s</h2>' % (r["name"], tag), '<p class="q">%s</p>' % r["pregunta"], '<p>%s</p>' % r["idea"],
              '<p><b>Cómo se resuelve:</b> %s</p>' % r["resolver"], '<p class="antes"><b>Antes:</b> %s</p>' % r["antes"]]
        tiers = list(r["tiers"].keys())
        h.append('<div class="tiers%s">' % (" one" if len(tiers) == 1 else ""))
        for t in tiers:
            en = r["tiers"][t]
            ok = ojo_ok(en)
            chk = "" if ok is None else ('<span class="ok">✓ el Ojo te alcanza al entrar</span>' if ok else '<span class="bad">✗ el Ojo no te alcanza al entrar</span>')
            label = "Única" if t == "unica" else t.capitalize()
            h.append('<div>%s<div class="t"><b>%s · %s</b>%s<br>%s</div></div>' % (svg(r, en), label, count(en), r["escala"][t], chk))
        h.append('</div>')
    h += ['<h2>Qué se queda igual</h2>',
          '<ul><li>Pasillo con relicario lateral tras cada sala, pasillo dorado y jefe (el Abanderado con su escolta).</li>',
          '<li>Planta por azar con espejo, nunca dos veces seguidas; la dificultad la marca la posición en el acto.</li>',
          '<li>Vidas: Exvoto 2 disparos (el primero lo deja tambaleándose), Ojo 3, Cireneo 4.</li></ul>']
    out_dir = os.path.join(ROOT, "walkthroughs/encuentros-tacticos")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "catalogo-salas-v3.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(h))
    for r in ROOMS:
        for t, en in r["tiers"].items():
            ok = ojo_ok(en)
            if ok is False:
                print("REGLA 1 FALLA: %s %s" % (r["id"], t))
    print(out)


if __name__ == "__main__":
    main()
