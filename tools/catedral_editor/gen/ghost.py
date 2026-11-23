# Fija el encuadre del lab a la caja de la escena "vieja": el lab escala por el contorno de la geometria, asi que al
# adelgazar un muro cambiaria la escala (px/m). GHOST_OUT=<json> guarda los vertices extremos de la escena de referencia;
# GHOST_IN=<json> los anade como triangulos de 0,1 mm en la escena nueva y el encuadre (y la escala) no cambian.
import bpy, bmesh, os, json, math
def _extremes(obj):
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    s, c = math.sin(math.radians(30)), math.cos(math.radians(30))
    keys = [lambda v: v.x, lambda v: -v.x, lambda v: s*v.y + c*v.z, lambda v: -(s*v.y + c*v.z),
            lambda v: -s*v.y + c*v.z, lambda v: -(-s*v.y + c*v.z)]
    return [list(max(vs, key=k)) for k in keys]
def apply(obj):
    o = os.environ.get('GHOST_OUT'); i = os.environ.get('GHOST_IN')
    if o:
        json.dump(_extremes(obj), open(o, 'w'))
    if i:
        pts = json.load(open(i))
        bm = bmesh.new(); bm.from_mesh(obj.data)
        for p in pts:
            e = 1e-4
            vs = [bm.verts.new((p[0], p[1], p[2])), bm.verts.new((p[0] + e, p[1], p[2])), bm.verts.new((p[0], p[1] + e, p[2]))]
            bm.faces.new(vs)
        bm.to_mesh(obj.data); bm.free()
