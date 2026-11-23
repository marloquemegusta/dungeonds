"""Hostia consagrada (reliquia del Glifo, ARPG) modelada por geometria en Blender.

Disco fino de pan acimo con el canto algo grueso y, hendido en la cara, el Sello
simplificado: un anillo cerca del borde y el crismon grueso (X, trazo vertical y el
bucle de la P). Dibujo de referencia: assets/inbox/hostia_24px_8x_ref1.png
(1024 px, blanco = surco); las cotas de abajo estan en pixeles de esa imagen.

Uso (lo llama tools/render_item_spin.py, que hace los renders del juego):
  blender --background --python tools/make_relic_hostia.py -- [--save ruta.blend]
"""

import math
import sys

import bmesh
import bpy

# --- Dibujo (pixeles de la referencia de 1024, centro 512) -----------------
PX_PER_UNIT = 430.0          # el disco mide 1.0 de radio = 430 px de la referencia
RING_RI, RING_RO = 318.0, 378.0
BAR_W = 92.0                 # grosor de los trazos del crismon
BAR_TOP, BAR_BOT = 250.0, 774.0
X_HALF_LEN = 272.0           # semilongitud de cada brazo de la X
P_CX, P_CY = 512.0 + BAR_W / 2, 322.0   # centro del bucle de la P (pegado al trazo)
P_RO, P_RI = 84.0, 30.0

# --- Volumen ----------------------------------------------------------------
RADIUS = 1.0
THICK = 0.13                 # canto ligeramente grueso
DEPTH = 0.075                # surcos hondos para que se lean a 24 px
EDGE_BEVEL = 0.035

IVORY = (0.58, 0.49, 0.34, 1.0)
GROOVE = (0.26, 0.14, 0.06, 1.0)   # sombra calida dentro del surco


def px(x, y):
    return ((x - 512.0) / PX_PER_UNIT, -(y - 512.0) / PX_PER_UNIT)


def prism(bm, poly, z0, z1):
    """Extruye un poligono 2D (sentido antihorario) entre z0 y z1."""
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    n = len(poly)
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))


def arc_band(bm, cx, cy, ri, ro, a0, a1, z0, z1, seg):
    """Banda de anillo (radios ri..ro, angulos a0..a1 en grados) como prisma cerrado."""
    full = abs(a1 - a0) >= 360.0
    n = seg if full else seg + 1
    angs = [math.radians(a0 + (a1 - a0) * i / seg) for i in range(n)]
    o = [(cx + ro * math.cos(a), cy + ro * math.sin(a)) for a in angs]
    i_ = [(cx + ri * math.cos(a), cy + ri * math.sin(a)) for a in angs]
    if not full:
        prism(bm, o + list(reversed(i_)), z0, z1)
        return
    ob = [bm.verts.new((x, y, z0)) for x, y in o]
    ot = [bm.verts.new((x, y, z1)) for x, y in o]
    ib = [bm.verts.new((x, y, z0)) for x, y in i_]
    it = [bm.verts.new((x, y, z1)) for x, y in i_]
    for k in range(n):
        m = (k + 1) % n
        bm.faces.new((ob[k], ob[m], ot[m], ot[k]))
        bm.faces.new((it[k], it[m], ib[m], ib[k]))
        bm.faces.new((ot[k], ot[m], it[m], it[k]))
        bm.faces.new((ib[k], ib[m], ob[m], ob[k]))


def rect(cx, cy, half_len, half_w, ang_deg):
    a = math.radians(ang_deg)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    return [(cx + sx * half_len * ux + sy * half_w * vx, cy + sx * half_len * uy + sy * half_w * vy)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def material(name, color, rough, spec, tint):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if "Specular Tint" in b.inputs:
        b.inputs["Specular Tint"].default_value = tint
    return m


def build_hostia(collection=None):
    """Crea la hostia centrada en el origen, cara grabada hacia +Z. Devuelve el objeto."""
    scene = bpy.context.scene
    coll = collection or scene.collection
    u = 1.0 / PX_PER_UNIT
    z_top = THICK / 2

    # Disco con el canto redondeado.
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=160, radius1=RADIUS, radius2=RADIUS, depth=THICK)
    me = bpy.data.meshes.new("Hostia")
    bm.to_mesh(me)
    bm.free()
    host = bpy.data.objects.new("Hostia", me)
    coll.objects.link(host)
    ivory = material("Hostia_Marfil", IVORY, 0.62, 0.45, (1.0, 0.82, 0.45, 1.0))
    groove = material("Hostia_Surco", GROOVE, 0.9, 0.2, (1.0, 0.8, 0.5, 1.0))
    me.materials.append(ivory)
    me.materials.append(groove)
    bev = host.modifiers.new("Canto", "BEVEL")
    bev.width = EDGE_BEVEL
    bev.segments = 3
    bev.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = host
    bpy.ops.object.modifier_apply(modifier="Canto")

    # Cortador: anillo + crismon, una sola malla.
    z0, z1 = z_top - DEPTH, z_top + 0.2
    bm = bmesh.new()
    cx, cy = px(512, 512)
    arc_band(bm, cx, cy, RING_RI * u, RING_RO * u, 0, 360, z0, z1, 160)
    # Trazo vertical (la rho).
    top = px(512, BAR_TOP)[1]
    bot = px(512, BAR_BOT)[1]
    prism(bm, rect(0.0, (top + bot) / 2, (top - bot) / 2, BAR_W / 2 * u, 90.0), z0, z1)
    # La X (chi).
    for ang in (45.0, -45.0):
        prism(bm, rect(0.0, 0.0, X_HALF_LEN * u, BAR_W / 2 * u, ang), z0, z1)
    # Bucle de la P, abierto hacia el trazo.
    pcx, pcy = px(P_CX, P_CY)
    arc_band(bm, pcx - 0.01, pcy, P_RI * u, P_RO * u, -90, 90, z0, z1, 32)
    cme = bpy.data.meshes.new("Surcos")
    bm.to_mesh(cme)
    bm.free()
    cutter = bpy.data.objects.new("Surcos", cme)
    coll.objects.link(cutter)
    cme.materials.append(groove)

    boo = host.modifiers.new("Surcos", "BOOLEAN")
    boo.operation = "DIFFERENCE"
    boo.solver = "EXACT"
    boo.use_self = True
    boo.object = cutter
    if hasattr(boo, "material_mode"):
        boo.material_mode = "TRANSFER"
    bpy.ops.object.modifier_apply(modifier="Surcos")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # Arista suave en el borde de los surcos para que coja luz.
    bev = host.modifiers.new("Arista", "BEVEL")
    bev.width = 0.008
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(40)
    bpy.ops.object.modifier_apply(modifier="Arista")
    for p in me.polygons:
        p.use_smooth = False
    return host


build = build_hostia  # punto de entrada que usa tools/render_item_spin.py


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_hostia()
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--save") + 1])
