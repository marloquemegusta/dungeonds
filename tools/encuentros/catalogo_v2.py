"""Catálogo de salas v2 del acto I (DESIGN.md 6.13.6, decisiones 2026-11-17).

Genera tools/encuentros/acto1_v2.json (datos para la ROM, mismo formato que acto1.json) y
walkthroughs/encuentros-acto1/catalogo-salas.html (esquemas para revisar en el móvil; no son capturas de la ROM).
Coordenadas locales: lx 0..208 (suelo), ly 0..384 (0 = barrera de arriba, 384 = entrada).
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tamaño aproximado de la huella de cada pieza en el esquema (w, h).
PIECE = {"banco_grupo4": (72, 84), "columna_entera": (24, 24), "santo": (28, 28), "vela": (8, 8)}


def row(kind, xs, y):
    return [[kind, x, y] for x in xs]


BOSS_HP = 5500    # ajustado con el bot natural (12 Dones, reaccion 30, error 12): 8000 -> 56 s, 12000 -> 72 s, 16000 -> 96 s


ROOMS = [
    {
        "id": "procesion", "name": "La procesión",
        "pregunta": "¿Te atreves a ponerte en el pasillo central?",
        "idea": "Dos bloques de bancos a cada lado y un pasillo central. El pasillo es la mejor línea de tiro (el rayo atraviesa la fila) "
                "y también la más peligrosa: por él baja la masa y, en media y dura, la carga del Cireneo. Los Exvotos esquivan el rayo "
                "y se abren hacia los huecos entre bancos, de donde vuelven a salir por los lados.",
        "resolver": "Entrar al pasillo para alinear la fila y disparar, y salirse a un hueco entre bancos antes de que llegue la carga o te rodeen.",
        "pieces": [("banco_grupo4", 0, 40), ("banco_grupo4", 136, 40), ("banco_grupo4", 0, 220), ("banco_grupo4", 136, 220)],
        "obstacles": [],
        "tiers": {
            "ligera": row("exvoto", [94, 114], 70) + row("exvoto", [94, 114], 120) + row("exvoto", [94, 114], 170) + row("exvoto", [94, 114], 250),
            "media": row("exvoto", [94, 114], 60) + row("exvoto", [94, 114], 110) + row("exvoto", [94, 114], 160) + row("exvoto", [94, 114], 250)
                     + row("exvoto", [30, 178], 180) + [["cireneo", 104, 20]],
            "dura": row("exvoto", [94, 114], 60) + row("exvoto", [94, 114], 110) + row("exvoto", [94, 114], 160) + row("exvoto", [94, 114], 250)
                    + row("exvoto", [30, 50, 158, 178], 180) + [["cireneo", 104, 20], ["ojo", 36, 14], ["ojo", 172, 14]],
        },
        "escala": {"ligera": "8 Exvotos en el pasillo. Solo la masa: aprender a alinear y a apartarse.",
                   "media": "10 Exvotos (2 ya en los huecos) y un Cireneo al fondo del pasillo: el pasillo se vuelve una línea de carga.",
                   "dura": "12 Exvotos, el Cireneo y 2 Ojos sobre los bancos que miran al pasillo: ponerse en él cuesta caro."},
    },
    {
        "id": "embudo", "name": "El embudo",
        "pregunta": "¿Cruzas el paso vigilado?",
        "idea": "Una línea de sacos cierra casi todo el ancho y deja un solo paso a la derecha. Los Exvotos bajan por el paso y ahí te "
                "favorece el cuello de botella, pero los Ojos se quedan arriba, detrás de los sacos, y no bajan: para acabar la sala "
                "tienes que cruzar el paso con ellos mirándolo.",
        "resolver": "Limpiar a los que bajan desde abajo, y cruzar el paso en el momento en que los Ojos no te tienen fijado.",
        "pieces": [],
        "obstacles": [{"kind": "sacos", "x": 0, "y": 200, "w": 150, "h": 24}],
        "tiers": {
            "ligera": [["ojo", 60, 40]] + row("exvoto", [40, 90, 140], 110) + row("exvoto", [60, 120, 180], 160),
            "media": [["ojo", 40, 40], ["ojo", 120, 30]] + row("exvoto", [30, 80, 130, 180], 110) + row("exvoto", [50, 110, 170, 190], 165),
            "dura": [["ojo", 40, 40], ["ojo", 120, 30], ["cireneo", 180, 70]] + row("exvoto", [30, 80, 130], 110)
                    + row("exvoto", [30, 80, 130], 140) + row("exvoto", [50, 110, 170, 190], 170),
        },
        "escala": {"ligera": "1 Ojo arriba y 6 Exvotos. Se aprende que el Ojo no viene: hay que ir a por él.",
                   "media": "2 Ojos cruzando sus miradas sobre el paso y 8 Exvotos.",
                   "dura": "2 Ojos, 10 Exvotos y un Cireneo alineado con el paso: cruzar es meterse en su carga (o hacer que se estrelle contra los sacos)."},
    },
    {
        "id": "balcon", "name": "El balcón",
        "pregunta": "¿Aguantas detrás de la estatua cuando te sacan de ella?",
        "idea": "Columnas arriba y estatuas abajo; las dos paran todos los disparos. Los Ojos disparan desde el balcón de arriba y la "
                "cobertura te salva, pero los Exvotos (y en dura el Cireneo) vienen a sacarte de ella.",
        "resolver": "Usar la estatua contra el Ojo, salir a limpiar a los que te rodean y volver. El Cireneo que embiste contra la estatua se queda aturdido.",
        "pieces": [("columna_entera", 36, 90), ("columna_entera", 148, 90), ("santo", 40, 260), ("santo", 140, 260)],
        "obstacles": [],
        "tiers": {
            "ligera": [["ojo", 104, 30]] + row("exvoto", [30, 70, 104, 140, 178], 150) + [["exvoto", 104, 190]],
            "media": [["ojo", 56, 24], ["ojo", 152, 24]] + row("exvoto", [30, 70, 104, 140, 178], 150) + row("exvoto", [80, 128], 195) + [["exvoto", 104, 60]],
            "dura": [["ojo", 56, 24], ["ojo", 152, 24], ["cireneo", 104, 130]] + row("exvoto", [30, 70, 140, 178], 150) + row("exvoto", [60, 104, 148], 195) + [["exvoto", 104, 60]],
        },
        "escala": {"ligera": "1 Ojo y 6 Exvotos: descubrir que la estatua para la mirada.",
                   "media": "2 Ojos (una estatua ya no cubre de los dos) y 8 Exvotos.",
                   "dura": "2 Ojos, 8 Exvotos y un Cireneo en medio que te persigue de una estatua a otra."},
    },
    {
        "id": "pinza", "name": "La pinza",
        "pregunta": "¿Sales del centro antes de que se cierre?",
        "idea": "Entras por el centro y los enemigos están a los dos lados de la entrada. Si te quedas en medio, te cierran por los dos "
                "lados a la vez. Las estatuas de los laterales parten cada grupo.",
        "resolver": "Romper un lado rápido, ponerse de espaldas a la pared de ese lado y tener a todos delante.",
        "pieces": [("santo", 8, 150), ("santo", 172, 150), ("banco_grupo4", 0, 10), ("banco_grupo4", 136, 10)],
        "obstacles": [],
        "tiers": {
            "ligera": row("exvoto", [20, 44], 270) + row("exvoto", [20, 44], 320) + row("exvoto", [164, 188], 270) + row("exvoto", [164, 188], 320),
            "media": row("exvoto", [20, 44], 250) + row("exvoto", [20, 44], 300) + [["exvoto", 32, 345]]
                     + row("exvoto", [164, 188], 250) + row("exvoto", [164, 188], 300) + [["exvoto", 176, 345], ["cireneo", 104, 120]],
            "dura": row("exvoto", [20, 44], 240) + row("exvoto", [20, 44], 285) + row("exvoto", [20, 44], 330)
                    + row("exvoto", [164, 188], 240) + row("exvoto", [164, 188], 285) + row("exvoto", [164, 188], 330)
                    + [["cireneo", 104, 120], ["ojo", 104, 110 - 80]],
        },
        "escala": {"ligera": "4 y 4 Exvotos: la pinza sola.",
                   "media": "5 y 5, y un Cireneo de frente: mientras rompes un lado, el tercer frente llega por el centro.",
                   "dura": "6 y 6, el Cireneo y un Ojo al fondo que vigila el centro: quedarse quieto es morir."},
    },
    {
        "id": "claro", "name": "El claro",
        "pregunta": "¿Aguantas la marea en pequeño?",
        "idea": "Sin bancos: solo dos estatuas arriba. Es la sala de la multitud en abierto; la presión es el número y que los Exvotos "
                "se abren cuando les apuntas. No hay dónde esconderse.",
        "resolver": "Moverse en círculo para estirar la masa, disparar cuando se alinean y no dejarse acorralar contra la entrada.",
        "pieces": [("santo", 8, 20), ("santo", 172, 20)],
        "obstacles": [],
        "tiers": {
            "ligera": row("exvoto", [40, 80, 128, 168], 60) + row("exvoto", [60, 104, 148], 110) + row("exvoto", [40, 104, 168], 160),
            "media": row("exvoto", [30, 70, 110, 150, 190], 50) + row("exvoto", [50, 90, 130, 170], 100) + row("exvoto", [30, 80, 128, 178], 150) + [["exvoto", 104, 190]],
            "dura": row("exvoto", [30, 70, 110, 150, 190], 50) + row("exvoto", [50, 90, 130, 170], 100) + row("exvoto", [30, 80, 128, 178], 150)
                    + [["exvoto", 104, 190], ["cireneo", 104, 20], ["ojo", 40, 16]],
        },
        "escala": {"ligera": "10 Exvotos.",
                   "media": "14 Exvotos.",
                   "dura": "14 Exvotos, un Cireneo y un Ojo sin cobertura posible: hay que ir a matar al Ojo atravesando la masa."},
    },
    {
        "id": "alambrada", "name": "La alambrada",
        "pregunta": "¿Peleas dentro del zigzag?",
        "idea": "Dos tramos de alambre de espino con los huecos alternados hacen un zigzag. El alambre para los cuerpos (el tuyo también) "
                "y deja pasar los disparos. Los Exvotos vienen por el zigzag, los Ojos esperan al fondo y te disparan a través del "
                "alambre. Para llegar a ellos tienes que recorrer el zigzag.",
        "resolver": "Disparar a través del alambre a los que rodean y avanzar por los huecos. El Cireneo que embiste por un tramo recto acaba en el alambre y queda aturdido.",
        "pieces": [("columna_entera", 150, 50)],
        "obstacles": [{"kind": "alambre", "x": 0, "y": 150, "w": 140, "h": 12}, {"kind": "alambre", "x": 68, "y": 250, "w": 140, "h": 12}],
        "tiers": {
            "ligera": row("exvoto", [30, 70, 110], 90) + row("exvoto", [100, 140, 180], 200),
            "media": [["ojo", 100, 30]] + row("exvoto", [30, 70, 110], 90) + row("exvoto", [100, 140, 180], 200) + row("exvoto", [30, 50], 300),
            "dura": [["ojo", 60, 30], ["ojo", 120, 24], ["cireneo", 120, 200]] + row("exvoto", [30, 70, 110], 90) + row("exvoto", [90, 160, 190], 200)
                    + row("exvoto", [30, 50], 300),
        },
        "escala": {"ligera": "6 Exvotos repartidos por el zigzag.",
                   "media": "8 Exvotos y un Ojo al fondo que te dispara a través del alambre.",
                   "dura": "8 Exvotos, 2 Ojos y un Cireneo dentro del zigzag."},
    },
]

COL = {"exvoto": "#d8c8a2", "cireneo": "#a0503c", "ojo": "#6f5a8c"}


def svg(room, enemies):
    W, H = 208 + 24, 384
    o = ['<svg viewBox="-12 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (W, H),
         '<rect x="-12" y="0" width="%d" height="%d" fill="#4a4741"/>' % (W, H),
         '<rect x="0" y="0" width="208" height="384" fill="#6b675f"/>',
         '<rect x="0" y="0" width="208" height="5" fill="#7a2f34"/>']
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
    o.append('<circle cx="104" cy="374" r="6" fill="#4f7894" stroke="#203342" stroke-width="2"/>')
    o.append('</svg>')
    return "".join(o)


def count(enemies):
    n = {}
    for e in enemies:
        n[e[0]] = n.get(e[0], 0) + 1
    names = {"exvoto": ("Exvoto", "Exvotos"), "cireneo": ("Cireneo", "Cireneos"), "ojo": ("Ojo", "Ojos")}
    return " · ".join("%d %s" % (v, names[k][v != 1]) for k, v in n.items())


# Fases legales de cada pieza en el kit horneado (tools/bake_cathedral_kit.py, catedral_phase_map) y su tamano en tiles.
# El kit solo coloca una pieza donde su fase del suelo (x mod 16, y mod 16 tiles) existe; sin ajustar, el runtime la mueve
# hasta media fase (hasta 64 px) y ya no coincide con el catalogo. Aqui se ajusta el catalogo a posiciones legales.
LEGAL = {"banco_grupo4": (9, 13, [(3, 0), (3, 8), (0, 0), (0, 8)]),
         "columna_entera": (6, 16, [(7, 9), (7, 1), (3, 9), (3, 1)]),
         "santo": (5, 9, [(0, 9), (0, 1), (8, 9), (8, 1)])}
FLOOR_X0, FLOOR_X1, BLOCK_TILES = 19, 45, 48     # tiles de suelo util (x) y de alto del bloque


def snap_piece(piece, lx, ly):
    """Posicion legal (lx, ly en px) mas cercana a la nominal; las piezas sin fases propias (vela...) no se tocan."""
    if piece not in LEGAL:
        return lx, ly
    w, h, phases = LEGAL[piece]
    tx, ty = (152 + lx + 4) // 8, (ly + 4) // 8
    best = None
    for pc, pr in phases:
        x_lo, y_lo = tx - ((tx - pc) & 15), ty - ((ty - pr) & 15)
        for ix in (-1, 0, 1):
            for iy in (-1, 0, 1):
                x, y = x_lo + 16 * ix, y_lo + 16 * iy
                if x < FLOOR_X0 or x + w > FLOOR_X1 or y < 0 or y + h > BLOCK_TILES:
                    continue
                c = (x - tx) ** 2 + (y - ty) ** 2
                if best is None or c < best[0]:
                    best = (c, x, y)
    return (best[1] * 8 - 152, best[2] * 8) if best else (lx, ly)


for _r in ROOMS:
    _snapped = []
    for _k, _x, _y in _r["pieces"]:
        _nx, _ny = snap_piece(_k, _x, _y)
        if (_nx, _ny) != (_x, _y):
            print("ajuste %s %s: (%d,%d) -> (%d,%d)" % (_r["id"], _k, _x, _y, _nx, _ny))
        _snapped.append((_k, _nx, _ny))
    _r["pieces"] = _snapped


def main():
    data = json.load(open(os.path.join(ROOT, "tools/encuentros/acto1.json"), encoding="utf-8"))
    data["_doc"] = data["_doc"] + " v2 (2026-11-17): todos presentes desde el principio y despiertos al cruzar el borde (state awake); sin wave2. Generado por catalogo_v2.py."
    plantas = {}
    for r in ROOMS:
        p = {"pieces": [{"piece": k, "x": x, "y": y} for k, x, y in r["pieces"]], "obstacles": r["obstacles"]}
        for t, en in r["tiers"].items():
            p[t] = {"enemies": [[k, x, y, "awake"] for k, x, y in en]}
        plantas[r["id"]] = p
    data["plantas"] = plantas
    data["hp"]["cireneo"] = 600  # 4 disparos del rayo base (150)
    data["hp"]["abanderado"] = BOSS_HP
    # Jefe con escolta (v2): 2 Ojos y 1 Cireneo, ademas de los Monaguillos que invoca. Entran con el bloque, quietos,
    # y se renuevan por arriba (ly 8-24) ~4 s despues de caer (unico sitio con refuerzos, enc_update).
    data["boss"] = {"enemies": [["abanderado", 104, 90, "awake"], ["ojo", 40, 30, "awake"], ["ojo", 168, 30, "awake"],
                                ["cireneo", 104, 150, "awake"]],
                    "escort_respawn_frames": 240,
                    "note": "bloque con barrera arriba; al vencer, texto VICTORIA (prototipo)"}
    data["act"]["golden_relic_after"] = data["act"].get("golden_relic_after", 6)
    with open(os.path.join(ROOT, "tools/encuentros/acto1_v2.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    css = """body{font-family:system-ui,sans-serif;max-width:860px;margin:auto;padding:16px;background:#f6f3ee;color:#222;line-height:1.45}
h2{margin-top:2em;border-top:2px solid #b9a98f;padding-top:.6em}.q{font-size:1.1em;font-style:italic}
.tiers{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.tiers svg{width:100%;height:auto;display:block;border-radius:4px}
.t{font-size:13px}.t b{display:block}.ley span{display:inline-block;margin-right:12px}
@media(prefers-color-scheme:dark){body{background:#1b1a18;color:#ddd}}"""
    h = ['<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Catálogo de salas</title><style>', css, '</style>',
         '<h1>Catálogo de salas del acto I (v2, propuesta)</h1>',
         '<p>Esquemas para decidir, no capturas de la ROM. Cada sala plantea <b>una pregunta</b>, y sus tres poblaciones (ligera en los encuentros 1-4, media en el 5-8 y dura en el 9-12) son la misma pregunta cada vez más dura.</p>',
         '<p>Reglas comunes (decididas tras tu prueba):</p><ul>',
         '<li>Todos los enemigos están en la sala desde el principio y despiertan a la vez cuando entras. No hay segundas oleadas.</li>',
         '<li>Los Exvotos esquivan el rayo cuando les apuntas: los de una fila se abren cada uno a un lado.</li>',
         '<li>El Cireneo te persigue y embiste cuando te tiene alineado; si choca con una pieza, queda aturdido.</li>',
         '<li>Vidas: Exvoto 2 disparos, Ojo 3, Cireneo 4 (solo un poco más; la dificultad la ponen la IA y la colocación).</li></ul>',
         '<p class="ley"><b>Leyenda:</b> <span>● Exvoto</span><span style="color:#a0503c">▲ Cireneo</span><span style="color:#6f5a8c">◉ Ojo</span><span style="color:#4f7894">● héroe al entrar</span> '
         '<span>línea granate = barrera</span><span>pardo = sacos</span><span>línea discontinua = alambre</span><span>círculo gris = columna</span><span>cuadrado gris = estatua</span><span>listones = bancos</span></p>']
    for r in ROOMS:
        h += ['<h2>%s</h2>' % r["name"], '<p class="q">%s</p>' % r["pregunta"], '<p>%s</p>' % r["idea"], '<p><b>Cómo se resuelve:</b> %s</p>' % r["resolver"], '<div class="tiers">']
        for t in ("ligera", "media", "dura"):
            h.append('<div>%s<div class="t"><b>%s · %s</b>%s</div></div>' % (svg(r, r["tiers"][t]), t.capitalize(), count(r["tiers"][t]), r["escala"][t]))
        h.append('</div>')
    h += ['<h2>Jefe: el Abanderado (estación V, fin del acto I)</h2>',
          '<p>Llega con su escolta coreografiada, como decía el diseño: 2 Ojos y un Cireneo que se renuevan desde arriba según caen (este es el único sitio donde entran refuerzos), además de sus Monaguillos. Vida a fijar con la escolta puesta.</p>',
          '<h2>Pendiente de decidir: el Ojo</h2>',
          '<p>Con más presión alrededor (masa que esquiva y Cireneo persiguiendo) el Ojo ya pesa más. Si aun así se queda corto, mi propuesta es que <b>su mirada deje el suelo marcado</b> un segundo y medio: un trazo apagado que quema al pisarlo. Así no basta con dar un paso al lado: te corta el camino.</p>']
    out = os.path.join(ROOT, "walkthroughs/encuentros-acto1/catalogo-salas.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(h))
    print(out)


if __name__ == "__main__":
    main()
