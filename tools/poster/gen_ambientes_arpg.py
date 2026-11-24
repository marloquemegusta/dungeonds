"""Escribe el bloque `ambiente` de cada sala en tools/poster/poster_arpg.json (funcion, luz en dos capas y composicion).
Es el sitio donde se disena el ambiente de las salas «sobre papel»: reglas simples, no azar suelto. El JSON resultante es
lo que lee el poster (poster_arpg_ambiente.py); se puede retocar a mano o volver a generar con
    python tools/poster/gen_ambientes_arpg.py

Convenciones: x e y en px locales del bloque (suelo de 208 de ancho, bloque de 384 de alto, y hacia abajo = hacia la entrada);
k = bloque de la sala (0 = el de la entrada). Anchos de pieza = los del kit (kit.layout)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FW = 208
W = {"banco_entero": 72, "banco_roto": 72, "banco_volcado": 80, "banco_grupo4": 72, "columna": 64, "columna_entera": 48,
     "santo": 40, "santo_der": 40, "sacos": 64, "sacos_b": 64, "sacos_remate": 64, "sacos_remate_der": 64, "alambre": 32,
     "vela": 16, "relicario": 48, "altar": 24}
SWAP = {"santo": "santo_der", "santo_der": "santo"}

# Capa (a): gradiente por profundidad de toda la demo (nivel 1 = vidriera calida y clara, nivel 5 = fria y oscura)
PROFUNDIDAD = {
    "1": {"tinte": [255, 226, 176], "brillo": 1.3},
    "2": {"tinte": [246, 222, 190], "brillo": 1.12},
    "3": {"tinte": [220, 212, 204], "brillo": 0.88},
    "4": {"tinte": [192, 196, 210], "brillo": 0.76},
    "5": {"tinte": [150, 160, 190], "brillo": 0.52},
}
# Capa (b): acento por funcion
AC = {
    "ninguno": ([255, 255, 255], 0.0),
    "osario": ([170, 210, 150], 0.50),
    "enfermeria": ([226, 238, 252], 0.45),
    "velas": ([255, 205, 140], 0.45),
    "claustro": ([200, 218, 248], 0.40),
    "cripta": ([130, 140, 175], 0.35),
    "prision": ([196, 204, 214], 0.30),
    "salon": ([214, 196, 216], 0.28),
    "tesoro": ([240, 226, 190], 0.25),
}


class Rng:
    def __init__(self, seed):
        self.s = (seed * 2654435761 + 12345) & 0xFFFFFFFF

    def r(self):
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) / float(1 << 24)


class Comp:
    def __init__(self):
        self.items = []

    def add(self, piece, k, x, y, **kw):
        self.items.append({"piece": piece, "k": k, "x": int(x), "y": int(y), **kw})

    def pair(self, piece, k, x, y, **kw):
        """Pieza a la izquierda en x y su simetrica a la derecha (santo <-> santo_der)."""
        self.add(piece, k, x, y, **kw)
        self.add(SWAP.get(piece, piece), k, FW - x - W[piece], y, **kw)


def nave(room, nb, desorden):
    c = Comp()
    rng = Rng(room + 7)
    rows = [12, 100, 172, 240, 312]
    p_skip = [0.0, 0.12, 0.25, 0.38][desorden]
    p_rot = [0.0, 0.16, 0.42, 0.66][desorden]
    p_vol = [0.0, 0.04, 0.14, 0.24][desorden]
    for k in range(nb):
        far = k == nb - 1
        for y in rows:
            if far and y == 12:
                continue                                   # el fondo lo ocupan las estatuas
            for side in (0, 1):
                if desorden and rng.r() < p_skip:
                    continue
                roll = rng.r()
                piece = "banco_volcado" if roll < p_vol else "banco_roto" if roll < p_vol + p_rot else "banco_entero"
                if desorden == 0:
                    piece = "banco_entero"
                jit = int((rng.r() - 0.5) * 2 * 5 * desorden)
                jy = int((rng.r() - 0.5) * 2 * 3 * desorden)
                w = W[piece]
                x = 8 + jit if side == 0 else FW - 8 - w - jit
                c.add(piece, k, x, y + jy)
        if far:
            c.pair("santo", k, 8, 8)
    if desorden >= 2:                                      # el desorden crece: columna caida y barricada de sacos
        c.add("columna", nb - 1, 0, 120)
    if desorden >= 3:
        c.add("sacos", 1, 8, 196)
        c.add("sacos_remate_der", 1, FW - 8 - 64, 270)
        c.add("columna", 0, FW - 64, 60)
    return c.items


def claustro(nb, cofre=False):
    c = Comp()
    for k in range(nb):
        for y in (0, 128, 256):
            c.pair("columna_entera", k, 0, y)
    return c.items


def capilla(velas_centro=(104, 96)):
    c = Comp()
    c.add("altar", 0, 92, 8, en_pasillo=True)
    c.pair("relicario", 0, 14, 14)
    import math
    cx, cy = velas_centro
    for i in range(7):                                     # semicirculo de velas delante del cofre
        a = math.pi * i / 6.0
        c.add("vela", 0, cx + 50 * math.cos(a) - 8, cy + 30 * math.sin(a) - 4, en_pasillo=True)
    for y in (208, 268):                                   # reclinatorios: bancos cortos a los lados
        c.pair("banco_entero", 0, 8, y)
    return c.items


def build():
    S = {}
    # --- Naves (nivel 1..4)
    for i, d in enumerate((0, 1, 2, 3)):
        S[i] = dict(funcion="nave de la catedral" + ("; los bancos se rompen cada vez mas" if i else ""),
                    pendiente="", acento="ninguno", caida=0.30 + 0.05 * i, fondo=0.25 + 0.05 * i,
                    nivel=i + 1, comp=nave(i, 3, d), resumen="bancos simetricos, cada vez mas rotos" if i else "bancos simetricos intactos")
    S[0]["extra_luz"] = {"vidrieras": True}
    # --- Galerias del cofre y del secreto (nivel 1)
    c = Comp()
    c.pair("columna_entera", 0, 0, 20)
    c.pair("santo", 0, 24, 190)
    S[4] = dict(funcion="galeria del cofre: tesoro a la vista", pendiente="", acento="tesoro", caida=0.30, fondo=0.2, nivel=1,
                comp=c.items, resumen="columnas y estatuas flanquean cofre")
    c = Comp()
    c.add("sacos", 0, 8, 196)
    c.add("sacos_b", 0, 8, 232)
    c.add("columna", 0, 136, 20)
    for x in (0, 32, 144, 176):
        c.add("alambre", 0, x, 270)
    S[5] = dict(funcion="galeria del secreto: escondrijo tras sacos", pendiente="", acento="prision", caida=0.40, fondo=0.3, nivel=1,
                comp=c.items, resumen="sacos, alambrada, columna caida")
    # --- Claustros
    S[6] = dict(funcion="claustro bajo: arcada abierta al exterior", pendiente="", acento="claustro", caida=0.12, fondo=0.1, nivel=1,
                comp=claustro(3), resumen="arcada de columnas, centro despejado")
    S[7] = dict(funcion="claustro alto: arcada y cofre al fondo", pendiente="", acento="claustro", caida=0.12, fondo=0.1, nivel=2,
                comp=claustro(3), resumen="arcada de columnas, centro despejado")
    # --- Enfermeria y osario (pendientes de props nuevos)
    c = Comp()
    for k in range(3):
        for y, x in ((60, 8), (150, 120), (240, 8), (330, 120)):
            c.add("banco_roto" if (k + y) % 2 else "banco_volcado", k, x + (k * 6) % 20, y)
        c.add("sacos", k, 140, 20 + k * 6) if k != 2 else None
    S[8] = dict(funcion="enfermeria: filas de catres contra los muros", pendiente="",
                acento="enfermeria", caida=0.28, fondo=0.2, nivel=2, comp=c.items, resumen="bancos rotos como camillas, sacos")
    c = Comp()
    for k in range(3):
        sx = (8, 120, 60)[k]
        c.add("sacos", k, sx, 40 + k * 10)
        c.add("sacos_b", k, sx, 76 + k * 10)
        c.add("banco_volcado", k, (120, 20, 100)[k], 110 + k * 14)
        c.add("sacos_remate_der", k, (136, 8, 120)[k], 300)
        c.add("banco_roto", k, (10, 110, 30)[k], 230)
        c.add("alambre", k, (150, 40, 90)[k], 190)
        c.add("alambre", k, (176, 8, 140)[k], 150)
    S[9] = dict(funcion="osario: los muertos del hospital, apilados hasta el cofre", pendiente="",
                acento="osario", caida=0.42, fondo=0.3, nivel=3, comp=c.items, resumen="nichos de huesos en los muros, cada vez mas llenos hacia el cofre")
    # --- Capillas
    S[10] = dict(funcion="capilla del parroco: altar, velas y reclinatorios", pendiente="", acento="velas", caida=0.38, fondo=0.25, nivel=3,
                 comp=capilla(), resumen="altar, velas en semicirculo, reclinatorios",
                 halos=[{"x": 104, "y": 20, "k": 0, "r": 70, "color": [200, 150, 90], "fuerza": 0.45}])
    c = Comp()
    c.add("altar", 0, 92, 8, en_pasillo=True)
    c.pair("relicario", 0, 14, 14)
    import math
    for i in range(7):
        a = math.pi * i / 6.0
        c.add("vela", 0, 104 + 50 * math.cos(a) - 8, 84 + 26 * math.sin(a) - 4, en_pasillo=True)
    S[13] = dict(funcion="capilla con llave: reliquia tras la reja", pendiente="", acento="velas", caida=0.38, fondo=0.25, nivel=4,
                 comp=c.items, resumen="altar y velas tras la reja", halos=[])
    # --- Galeria de la Misa
    c = Comp()
    for y in (100, 172, 240):
        c.pair("banco_entero", 0, 8, y)
    c.add("altar", 1, 92, 8, en_pasillo=True)
    c.pair("relicario", 1, 14, 14)
    for yy in (60, 100, 140, 180, 220, 260, 300):
        c.pair("vela", 1, 4, yy, en_pasillo=False)
    S[11] = dict(funcion="galeria de la Misa: la nave en pequeno ante el altar", pendiente="", acento="velas", caida=0.36, fondo=0.25, nivel=3,
                 comp=c.items, resumen="bancos, altar, hileras de velas")
    # --- Prisionero y monjarana
    c = Comp()
    for k in range(2):
        for y in (100, 214):
            for x in (0, 32):
                c.add("alambre", k, x, y)
            for x in (144, 176):
                c.add("alambre", k, x, y)
        c.pair("columna", k, 0, 20 + 0)
    c.add("sacos", 0, 8, 300)
    S[12] = dict(funcion="galeria del prisionero: celdas de alambre", pendiente="", acento="prision", caida=0.40, fondo=0.3, nivel=3,
                 comp=c.items, resumen="celdas de alambrada, columnas rotas")
    c = Comp()
    for k in range(2):
        for y in (40, 168, 296):
            c.pair("santo", k, 6, y)
    c.pair("columna_entera", 1, 0, 8)
    S[14] = dict(funcion="galeria de la monjarana: salon de estatuas", pendiente="", acento="salon", caida=0.36, fondo=0.28, nivel=4,
                 comp=c.items, resumen="estatuas en hilera, centro despejado")
    # --- Cripta
    c = Comp()
    for y in (24, 240):
        c.pair("columna_entera", 0, 0, y)
    c.pair("santo", 0, 26, 150)
    S[15] = dict(funcion="cripta: arena del jefe a la luz de antorchas", pendiente="antorchas de pared sin pieza propia (solo halo)",
                 acento="cripta", caida=0.55, fondo=0.35, nivel=5, comp=c.items, resumen="despejada, estatuas flanquean jefe",
                 halos=[{"x": 10, "y": 60, "k": 0, "r": 58, "color": [205, 138, 72], "fuerza": 0.48},
                        {"x": 198, "y": 60, "k": 0, "r": 58, "color": [205, 138, 72], "fuerza": 0.48},
                        {"x": 10, "y": 250, "k": 0, "r": 58, "color": [205, 138, 72], "fuerza": 0.48},
                        {"x": 198, "y": 250, "k": 0, "r": 58, "color": [205, 138, 72], "fuerza": 0.48}])
    return S


def main():
    path = HERE / "poster_arpg.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["_ambiente_doc"] = ("Bloque `ambiente` por sala (lo escribe gen_ambientes_arpg.py): funcion, luz {nivel, acento{tinte,fuerza}, caida, fondo, halos} "
                            "y composicion [{piece,k,x,y,en_pasillo}] con x,y locales del bloque k (0 = entrada); luz_profundidad = capa (a) por nivel.")
    cfg["luz_profundidad"] = PROFUNDIDAD
    cfg["halo_velas"] = {"r": 40, "color": [200, 150, 85], "fuerza": 0.42}
    cfg["halo_altar"] = {"r": 56, "color": [205, 160, 100], "fuerza": 0.35}
    S = build()
    for sala in cfg["salas"]:
        s = S[sala["id"]]
        tinte, fuerza = AC[s["acento"]]
        halos = s.get("halos", [])
        sala["ambiente"] = {
            "funcion": s["funcion"],
            "pendiente": s["pendiente"],
            "resumen": s["resumen"],
            "luz": {"nivel": s["nivel"], "acento": {"nombre": s["acento"], "tinte": tinte, "fuerza": fuerza},
                    "caida": s["caida"], "fondo": s["fondo"], "halos": halos, **s.get("extra_luz", {})},
            "composicion": s["comp"],
        }
    path.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("escrito", path, {i: len(S[i]["comp"]) for i in sorted(S)})


if __name__ == "__main__":
    main()
