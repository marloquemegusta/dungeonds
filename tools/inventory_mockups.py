#!/usr/bin/env python3
"""Mockups A/B/C de la pantalla de inventario (proto ARPG). No son evidencia de ROM: solo para elegir.
Genera walkthroughs/arpg-predemo/inventario_abc.html con SVG incrustado (2 pantallas de la DS, 256x192 cada una)."""
import os, html

BG = "#120e0d"; PANEL = "#1e1714"; PANEL2 = "#2a201b"; EDGE = "#6b5a3e"; GOLD = "#c9a56a"
TXT = "#d8c9a8"; DIM = "#8a7c66"; GREEN = "#8bab84"; RED = "#b8705f"
RAR = {"C": "#9a9080", "U": "#6f9a6a", "R": "#6a88b0", "E": "#9170b0", "L": "#d09040"}
SCH = {"rayo": "#d8c27a", "fuego": "#c0705a", "veneno": "#7fa070", "levantar": "#9a7fb0", "pecho": "#b0a090"}
FONT = "font-family:Palatino Linotype,Palatino,Georgia,serif"


def t(x, y, s, size=9, fill=TXT, anchor="start", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" style="{FONT}">{html.escape(s)}</text>')


def rect(x, y, w, h, fill=PANEL, stroke=EDGE, sw=1, rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def item(cx, cy, school, rar, size=22, sel=False):
    """Icono de reliquia: rombo del color de la escuela con marco de rareza."""
    s = size / 2
    col = SCH[school]
    out = rect(cx - s, cy - s, size, size, "#17110f", RAR[rar], 2 if rar in "EL" else 1)
    out += f'<polygon points="{cx},{cy-s+4} {cx+s-4},{cy} {cx},{cy+s-4} {cx-s+4},{cy}" fill="{col}" opacity="0.85"/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="2" fill="#17110f"/>'
    if sel:
        out += rect(cx - s - 2, cy - s - 2, size + 4, size + 4, "none", GOLD, 1.5)
    return out


def socket(cx, cy, school=None, rar="C", size=18, empty=False, sel=False):
    if empty or school is None:
        o = f'<circle cx="{cx}" cy="{cy}" r="{size/2}" fill="#0c0908" stroke="{EDGE}" stroke-width="1" stroke-dasharray="2 2"/>'
        if sel:
            o += f'<circle cx="{cx}" cy="{cy}" r="{size/2+2}" fill="none" stroke="{GOLD}" stroke-width="1.5"/>'
        return o
    s = size / 2
    o = f'<circle cx="{cx}" cy="{cy}" r="{s}" fill="#17110f" stroke="{RAR[rar]}" stroke-width="{2 if rar in "EL" else 1}"/>'
    o += f'<polygon points="{cx},{cy-s+3} {cx+s-3},{cy} {cx},{cy+s-3} {cx-s+3},{cy}" fill="{SCH[school]}" opacity="0.9"/>'
    if sel:
        o += f'<circle cx="{cx}" cy="{cy}" r="{s+2}" fill="none" stroke="{GOLD}" stroke-width="1.5"/>'
    return o


def spell_icon(cx, cy, name, size=26, active=False):
    col = SCH["rayo"] if name == "Rayo" else SCH["levantar"]
    o = rect(cx - size / 2, cy - size / 2, size, size, "#17110f", GOLD if active else EDGE, 1.5 if active else 1, 3)
    o += f'<circle cx="{cx}" cy="{cy}" r="{size/2-6}" fill="none" stroke="{col}" stroke-width="2"/>'
    o += f'<circle cx="{cx}" cy="{cy}" r="3" fill="{col}"/>'
    for a in range(0, 360, 45):
        pass
    return o


def hero(cx, cy, scale=1.0):
    """Silueta del Corazon Abierto (placeholder)."""
    s = scale
    o = f'<ellipse cx="{cx}" cy="{cy+46*s}" rx="{16*s}" ry="{4*s}" fill="#000" opacity="0.4"/>'
    o += f'<path d="M{cx-10*s},{cy+44*s} L{cx-12*s},{cy+4*s} Q{cx},{cy-6*s} {cx+12*s},{cy+4*s} L{cx+10*s},{cy+44*s} Z" fill="#3a2c26" stroke="#5a463a"/>'
    o += f'<circle cx="{cx}" cy="{cy-8*s}" r="{8*s}" fill="#4a3a30" stroke="#5a463a"/>'
    o += f'<path d="M{cx},{cy+10*s} c-4,-6 -9,-1 -4,5 c2,2 4,3 4,3 c0,0 2,-1 4,-3 c5,-6 0,-11 -4,-5z" fill="#a0504a"/>'  # corazon abierto
    return o


def card(x, y, w, h, name, rar, school, lines, mech=None, compare=None, extra=None):
    """Ficha de reliquia con comparacion. compare = lista de (texto, signo)."""
    o = rect(x, y, w, h, PANEL, RAR[rar], 2)
    o += t(x + 8, y + 15, name, 11, RAR[rar], weight="bold")
    o += t(x + 8, y + 27, {"C": "Común", "U": "Poco común", "R": "Rara", "E": "Épica", "L": "Legendaria"}[rar] + " · " + extra[0] if extra else "", 8, DIM)
    yy = y + 42
    if mech:
        o += t(x + 8, yy, mech, 9, GOLD); yy += 13
    for (txt, sgn) in lines:
        col = GREEN if sgn > 0 else RED if sgn < 0 else TXT
        arrow = "▲ " if sgn > 0 else "▼ " if sgn < 0 else "  "
        o += t(x + 8, yy, arrow + txt, 9, col); yy += 12
    if compare:
        o += f'<line x1="{x+6}" y1="{y+h-36}" x2="{x+w-6}" y2="{y+h-36}" stroke="{EDGE}" stroke-dasharray="2 2"/>'
        o += t(x + 8, y + h - 24, "Equipada: " + compare, 8, DIM)
        o += t(x + 8, y + h - 12, "A: engarzar   Y: desguazar (+8 cera)", 8, GOLD)
    return o


def screen(inner, label):
    return (f'<g><rect width="256" height="192" fill="{BG}"/>{inner}'
            f'<rect width="256" height="192" fill="none" stroke="#000" stroke-width="2"/></g>')


def svg(top, bottom):
    return (f'<svg viewBox="0 0 256 392" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:512px;'
            f'image-rendering:pixelated;background:#000;display:block;border-radius:6px">'
            f'<g>{screen(top, "sup")}</g><g transform="translate(0,200)">{screen(bottom, "inf")}</g></svg>')


def bag_grid(x, y, cols, rows, cell, items, sel=None):
    o = ""
    for r in range(rows):
        for c in range(cols):
            cx = x + c * cell + cell / 2; cy = y + r * cell + cell / 2
            o += rect(cx - cell / 2 + 1, cy - cell / 2 + 1, cell - 2, cell - 2, "#17110f", "#3a2e24")
    for i, (sc, rar) in enumerate(items):
        c, r = i % cols, i // cols
        cx = x + c * cell + cell / 2; cy = y + r * cell + cell / 2
        o += item(cx, cy, sc, rar, cell - 6, sel=(sel == i))
    return o


BAG = [("rayo", "U"), ("fuego", "R"), ("veneno", "C"), ("rayo", "E"), ("levantar", "R"), ("pecho", "U"),
       ("fuego", "C"), ("rayo", "C"), ("veneno", "R"), ("pecho", "E"), ("fuego", "L")]

CARD = dict(name="Llama Votiva", rar="E", school="fuego",
            lines=[("Quemadura 110 %", +1), ("Alcance +10 %", +1), ("Coste de maná +6 %", -1)],
            mech="Mecánica: la línea quema", compare="Llama Votiva (Rara) 50 %", extra=("Rayo · Nivel obj. 14",))


# ---------------------------------------------------------------- A: Diablo (muñeco)
def mock_a():
    top = rect(6, 6, 244, 180, PANEL2, EDGE, 1) + card(14, 14, 228, 164, **CARD)
    b = t(128, 13, "Inventario", 10, GOLD, "middle") + t(10, 13, "‹ Volver", 8, DIM) + t(246, 13, "Cera 12", 8, GOLD, "end")
    b += hero(128, 40, 0.9)
    # hechizo izq / der y pecho al centro (como las manos y el pecho de Diablo)
    b += t(50, 30, "Rayo", 9, GOLD, "middle") + spell_icon(50, 48, "Rayo", 24, True)
    for i, (sc, r, e) in enumerate([("rayo", "R", 0), ("fuego", "E", 0), (None, "C", 1)]):
        b += socket(30 + i * 20, 70, sc, r, 16, empty=bool(e), sel=(i == 1))
    b += t(206, 30, "Glifo", 9, GOLD, "middle") + spell_icon(206, 48, "Glifo", 24)
    for i, (sc, r, e) in enumerate([("veneno", "U", 0), (None, "C", 1), (None, "C", 1)]):
        b += socket(186 + i * 20, 70, sc, r, 16, empty=bool(e))
    b += t(128, 100, "Pecho (relicario)", 8, DIM, "middle")
    for i, (sc, r, e) in enumerate([("pecho", "E", 0), (None, "C", 1)]):
        b += socket(118 + i * 20, 111, sc, r, 16, empty=bool(e))
    b += f'<line x1="8" y1="123" x2="248" y2="123" stroke="{EDGE}"/>'
    b += t(10, 132, "Bolsa 11/16", 8, DIM)
    b += bag_grid(16, 135, 8, 2, 28, BAG[:11], sel=3)  # 8x2 de 30 px = 240 x 60 (hasta y=205 -> recorto)
    return svg(top, b.replace('y="145"', 'y="145"'))


# ---------------------------------------------------------------- B: Sacred (pestañas + cuadricula grande)
def mock_b():
    top = rect(6, 6, 244, 180, PANEL2, EDGE, 1)
    top += t(14, 22, "Rayo", 11, GOLD, weight="bold") + t(242, 22, "Nivel 8", 8, DIM, "end")
    top += spell_icon(40, 62, "Rayo", 40, True)
    top += t(76, 50, "Daño 100 → 138", 9, GREEN) + t(76, 62, "Carga 1,2 s → 0,9 s", 9, GREEN) + t(76, 74, "Maná 15 → 16", 9, RED)
    top += t(14, 100, "Engarces del hechizo (3)", 8, DIM)
    for i, (sc, r, e) in enumerate([("rayo", "R", 0), ("fuego", "E", 0), (None, "C", 1)]):
        top += socket(48 + i * 80, 126, sc, r, 28, empty=bool(e), sel=(i == 2))
        top += t(48 + i * 80, 150, ["Alcance +30 %", "Llama Votiva", "(vacío)"][i], 8, TXT if not e else DIM, "middle")
    top += t(128, 176, "Elige una reliquia de la bolsa para engarzarla", 8, DIM, "middle")
    b = ""
    for i, nm in enumerate(["Rayo ●", "Ejecuc.", "Glifo ●", "Levant.", "Pecho"]):
        x = 6 + i * 49
        b += rect(x, 4, 47, 18, PANEL2 if i else PANEL, GOLD if i == 0 else EDGE, 1.5 if i == 0 else 1, 3)
        b += t(x + 23.5, 16, nm, 8, GOLD if i == 0 else DIM, "middle")
    b += t(10, 36, "Bolsa 11/16 · 12 cera", 7, DIM) + t(246, 36, "● equipado (2)  ·  Ejecución: L", 7, DIM, "end")
    b += bag_grid(10, 42, 6, 3, 36, BAG[:11], sel=3)
    b += rect(10, 154, 236, 30, PANEL, EDGE) + t(16, 167, "Llama Votiva (Épica)", 9, RAR["E"]) + t(16, 179, "+Quemadura 110 %  ·  A: engarzar  ·  Y: desguazar", 7, TXT)
    return svg(top, b)


# ---------------------------------------------------------------- C: anillo de engarces (coherente con el radial)
def mock_c():
    import math
    top = rect(6, 6, 244, 180, PANEL2, EDGE, 1) + card(14, 14, 228, 164, **CARD)
    b = t(128, 13, "Rayo", 10, GOLD, "middle") + t(10, 13, "‹", 12, DIM) + t(246, 13, "›", 12, DIM, "end")
    cx, cy, R = 128, 74, 40
    b += f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{EDGE}" stroke-width="1" stroke-dasharray="3 3"/>'
    b += spell_icon(cx, cy, "Rayo", 40, True)
    slots = [("rayo", "R", 0), ("fuego", "E", 0), (None, "C", 1)]
    for i, (sc, r, e) in enumerate(slots):
        a = math.radians(210 - i * 60)   # arco superior
        b += socket(cx + R * math.cos(a), cy - R * math.sin(a), sc, r, 22, empty=bool(e), sel=(i == 2))
    b += t(cx, 124, "Daño 100 → 138 · Carga 1,2 → 0,9 s", 8, GREEN, "middle")
    b += t(10, 138, "Pecho:", 8, DIM)
    for i, (sc, r, e) in enumerate([("pecho", "E", 0), (None, "C", 1)]):
        b += socket(54 + i * 22, 136, sc, r, 16, empty=bool(e))
    b += t(246, 138, "Glifo ○ ○ ○", 8, DIM, "end")
    b += f'<line x1="8" y1="148" x2="248" y2="148" stroke="{EDGE}"/>'
    b += t(10, 158, "Bolsa (desliza)  11/16", 8, DIM)
    for i, (sc, rr) in enumerate(BAG[:8]):
        b += item(22 + i * 30, 175, sc, rr, 24, sel=(i == 3))
    return svg(top, b)


def mock_pausa():
    """Pausa en la mazmorra con acceso al inventario (el juego queda congelado)."""
    b = rect(58, 20, 140, 152, PANEL, EDGE, 1)
    b += t(128, 36, "Pausa", 10, GOLD, "middle")
    for i, (nm, hot) in enumerate([("Continuar", 0), ("Inventario  (7/16)", 1), ("Códice", 0), ("Controles", 0), ("Volver al campamento", 0)]):
        y = 46 + i * 24
        b += rect(66, y, 124, 19, PANEL2 if not hot else "#3a2a20", GOLD if hot else EDGE, 1.5 if hot else 1, 2)
        b += t(128, y + 13, nm, 9, GOLD if hot else TXT, "middle")
    b += t(128, 188, "START abre la pausa · B vuelve", 7, DIM, "middle")
    return svg('<rect width="256" height="192" fill="#0c0a09"/>' + t(128, 100, "(mazmorra congelada)", 9, DIM, "middle"), b)


OPTIONS = [
    ("A", "Muñeco, estilo Diablo", mock_a(),
     "El héroe en el centro. Cada hechizo es una «mano» con sus engarces debajo y el relicario del pecho en el centro, como el equipo de Diablo. Bolsa en rejilla abajo. Todo visible a la vez. Ficha de comparación arriba."),
    ("B", "Pestañas y rejilla grande, estilo Sacred", mock_b(),
     "Pestañas Rayo / Ejecución / Glifo / Levantar / Pecho (● = hechizo equipado; Ejecución va fija en L). Arriba el hechizo elegido con sus engarces grandes y lo que sube o baja; abajo la bolsa en rejilla grande con filtro por escuela. Más espacio para la bolsa, menos «muñeco»."),
    ("C", "Anillo de engarces", mock_c(),
     "El hechizo en el centro con sus engarces orbitando en un anillo (mismo lenguaje que el menú radial); `‹ ›` o `L`/`R` cambian de hechizo. Pecho y Glifo en una fila, bolsa como tira que se desliza. Lo más original y compacto."),
]


def main():
    out = ['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>Inventario ABC</title><style>body{background:#0b0807;color:#d8c9a8;font-family:Georgia,serif;max-width:560px;margin:0 auto;padding:12px}'
           'h1{color:#c9a56a;font-size:20px}h2{color:#c9a56a;margin:26px 0 4px}p{line-height:1.4;font-size:15px}.n{color:#8a7c66;font-size:13px}</style>',
           '<h1>Inventario: tres propuestas</h1>',
           '<p class="n">Mockups (no son capturas de la ROM). Cada uno muestra la pantalla superior (ficha de la reliquia con comparación: verde sube, rojo baja) y la inferior táctil. Colores de rareza: gris común, verde poco común, azul rara, violeta épica, ámbar legendaria; el color del rombo es la escuela.</p>']
    for k, name, s, desc in OPTIONS:
        out.append(f'<h2>{k} · {html.escape(name)}</h2>{s}<p>{html.escape(desc)}</p>')
    out.append('<h2>Acceso desde la mazmorra (todas las opciones)</h2>' + mock_pausa() + '<p>START abre la pausa y ahí hay un botón Inventario. El juego queda congelado mientras lo usas. Mismas funciones que en el campamento: cambiar engarces, equipar y desguazar para hacer hueco (da cera). Se abre la misma pantalla A, B o C que elijas.</p>')
    path = os.path.join(os.path.dirname(__file__), "..", "walkthroughs", "arpg-predemo", "inventario_abc.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(os.path.abspath(path))


if __name__ == "__main__":
    main()
